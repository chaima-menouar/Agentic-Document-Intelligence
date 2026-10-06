"""Generator interfaces for the RAG layer."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Protocol


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SOURCE_BLOCK_RE = re.compile(
    r"\[S(?P<label>\d+)\]\s+[^\n]*\n(?P<text>.*?)(?=\n\n\[S\d+\]|\n\nAnswer:|\Z)",
    re.DOTALL,
)
_YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

_STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "by",
    "did", "do", "does", "for", "from", "had", "has", "have", "how", "in",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "with",
}


class TextGenerator(Protocol):
    """Minimal interface expected by ClassicalRAG."""

    def generate(self, prompt: str) -> str:
        ...


class OpenAICompatibleGenerator:
    """Tiny dependency-free client for OpenAI-compatible chat endpoints.

    It works with services that expose a /chat/completions-compatible HTTP API,
    including many local inference servers. Secrets are read from environment
    variables and are never stored in the repository.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.model = model or os.getenv("RAG_LLM_MODEL", "")
        self.base_url = (base_url or os.getenv("RAG_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("RAG_LLM_API_KEY", "")
        self.timeout_seconds = timeout_seconds

        if not self.model:
            raise ValueError("Set RAG_LLM_MODEL or pass model explicitly.")
        if not self.base_url:
            raise ValueError("Set RAG_LLM_BASE_URL or pass base_url explicitly.")

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-grounded document assistant. "
                        "Follow the user prompt exactly and never invent evidence."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key
                    else {}
                ),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM endpoint request failed: {exc}") from exc

        try:
            return str(body["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM endpoint returned an unexpected response.") from exc


def _content_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS and len(token) > 1
    }


def _extract_question(prompt: str) -> str:
    marker = "Question:\n"
    start = prompt.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = prompt.find("\n\nEvidence:", start)
    if end < 0:
        return ""
    return prompt[start:end].strip()


def _extract_source_blocks(prompt: str) -> list[tuple[str, str]]:
    evidence_start = prompt.find("Evidence:")
    if evidence_start < 0:
        return []
    evidence_text = prompt[evidence_start + len("Evidence:"):]
    return [
        (match.group("label"), " ".join(match.group("text").split()).strip())
        for match in _SOURCE_BLOCK_RE.finditer(evidence_text)
        if match.group("text").strip()
    ]


def _question_keywords(question: str) -> set[str]:
    tokens = _content_tokens(question)
    lowered = question.lower()
    if "main idea" in lowered or "central idea" in lowered:
        tokens.update({"idea", "central", "purpose", "theme", "overall"})
    return tokens


def _requires_year(question: str) -> bool:
    lowered = question.lower()
    return "what year" in lowered or "which year" in lowered or lowered.startswith("when ")


def _requires_number(question: str) -> bool:
    lowered = question.lower()
    return "how many" in lowered or "how much" in lowered or "number of" in lowered


def _candidate_score(question: str, sentence: str) -> float:
    question_tokens = _question_keywords(question)
    sentence_tokens = _content_tokens(sentence)
    overlap = len(question_tokens & sentence_tokens)

    score = float(overlap * 4)
    word_count = len(_TOKEN_RE.findall(sentence))
    score += min(word_count, 30) / 30

    lowered_q = question.lower()
    lowered_s = sentence.lower()
    if ("main idea" in lowered_q or "central idea" in lowered_q) and (
        "central idea" in lowered_s
        or "main idea" in lowered_s
        or "purpose" in lowered_s
        or "theme" in lowered_s
    ):
        score += 6.0

    if word_count < 4:
        score -= 4.0

    return score


class ExtractiveGenerator:
    """Deterministic, question-aware, no-key fallback for local RAG.

    The baseline ranks sentences across all retrieved evidence blocks by their
    lexical relevance to the question, then returns the best sentence with the
    exact source label that produced it. Small answer-type guards prevent the
    baseline from inventing a year or numeric answer when the evidence does not
    contain one.

    This remains an extractive baseline, not a replacement for an LLM. Its goal
    is a reproducible, useful offline answer while preserving citation and
    verification plumbing without external credentials.
    """

    def __init__(self, *, max_chars: int = 420) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than zero.")
        self.max_chars = max_chars

    def generate(self, prompt: str) -> str:
        question = _extract_question(prompt)
        blocks = _extract_source_blocks(prompt)
        if not question or not blocks:
            return "INSUFFICIENT_EVIDENCE"

        candidates: list[tuple[float, str, str]] = []
        for label, text in blocks:
            sentences = [
                sentence.strip()
                for sentence in _SENTENCE_SPLIT_RE.split(text)
                if sentence.strip()
            ]
            for sentence in sentences:
                if _requires_year(question) and not _YEAR_RE.search(sentence):
                    continue
                if _requires_number(question) and not _NUMBER_RE.search(sentence):
                    continue

                score = _candidate_score(question, sentence)
                if score > 0:
                    candidates.append((score, label, sentence))

        if not candidates:
            return "INSUFFICIENT_EVIDENCE"

        score, label, sentence = max(
            candidates,
            key=lambda item: (item[0], len(item[2])),
        )

        # Require at least one meaningful lexical/semantic cue from the question.
        # The special main-idea expansion in _question_keywords allows a sentence
        # containing "central idea", "purpose", or "theme" to satisfy this guard.
        if score < 4.0:
            return "INSUFFICIENT_EVIDENCE"

        sentence = sentence[: self.max_chars].rstrip()
        return f"{sentence} [S{label}]"
