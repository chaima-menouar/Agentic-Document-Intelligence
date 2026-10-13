"""Transparent V2 evaluation metrics for V1/V2 comparisons."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.models import AnswerCitation

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
_CITATION_RE = re.compile(r"\[([A-Za-z0-9]+)\]")
_STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "by",
    "did", "do", "does", "for", "from", "had", "has", "have", "how", "in",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "with",
}


def content_tokens(text: str) -> set[str]:
    """Return lowercase non-stopword content tokens."""
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS and len(token) > 1
    }


def answer_relevance_proxy(question: str, answer: str) -> float:
    """Question-content coverage by the answer.

    This is an intentionally transparent lexical proxy, not an LLM-as-judge
    metric. A score of 1 means every content token from the question occurs in
    the answer; 0 means none do.
    """
    question_tokens = content_tokens(question)
    if not question_tokens:
        return 0.0
    answer_tokens = content_tokens(answer)
    return len(question_tokens & answer_tokens) / len(question_tokens)


def citation_precision(
    answer_text: str,
    citations: Sequence[AnswerCitation],
) -> float:
    """Fraction of cited labels that map to structured retrieved evidence."""
    used = _CITATION_RE.findall(answer_text)
    if not used:
        return 0.0
    valid = {citation.label for citation in citations}
    return sum(label in valid for label in used) / len(used)


def abstention_correct(
    *,
    abstained: bool,
    should_abstain: bool,
) -> float:
    """Return 1 when answer/abstention behavior matches scenario expectation."""
    return float(abstained == should_abstain)
