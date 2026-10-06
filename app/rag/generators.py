"""Generator interfaces for the RAG layer."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


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



class ExtractiveGenerator:
    """Deterministic no-key fallback for end-to-end RAG smoke tests.

    It extracts a concise sentence from the top retrieved evidence block and
    cites [S1]. This is not a replacement for an LLM; it is a reproducible
    offline baseline that verifies the complete retrieval -> generation ->
    citation plumbing without external credentials.
    """

    def __init__(self, *, max_chars: int = 320) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than zero.")
        self.max_chars = max_chars

    def generate(self, prompt: str) -> str:
        marker = "[S1]"
        start = prompt.find(marker)
        if start < 0:
            return "INSUFFICIENT_EVIDENCE"

        block = prompt[start + len(marker):]
        # The first line is provenance metadata. Evidence text starts after it.
        if "\n" in block:
            block = block.split("\n", 1)[1]
        # Stop before the next evidence block or the final Answer marker.
        for boundary in ("\n\n[S2]", "\n\nAnswer:"):
            if boundary in block:
                block = block.split(boundary, 1)[0]

        text = " ".join(block.split()).strip()
        if not text:
            return "INSUFFICIENT_EVIDENCE"

        sentence = text
        for delimiter in (". ", "? ", "! "):
            if delimiter in sentence:
                sentence = sentence.split(delimiter, 1)[0] + delimiter.strip()
                break
        sentence = sentence[: self.max_chars].rstrip()
        return f"{sentence} [S1]"
