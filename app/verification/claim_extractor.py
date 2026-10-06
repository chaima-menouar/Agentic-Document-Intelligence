"""Deterministic claim extraction from cited RAG answers."""

from __future__ import annotations

import re

from app.models import ExtractedClaim

_CITATION_RE = re.compile(r"\[S(\d+)\]")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_claim_text(text: str) -> str:
    text = _CITATION_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" \t\n-•")
    return re.sub(r"\s+([.,!?;:])", r"\1", text)


def extract_claims(answer: str) -> list[ExtractedClaim]:
    """Split an answer into factual sentence-level claims.

    Citation labels are removed from claim text but preserved as structured
    metadata. Citation-only fragments are attached to the previous claim.
    """
    normalized = _WHITESPACE_RE.sub(" ", answer).strip()
    if not normalized:
        return []

    raw_parts = _SENTENCE_SPLIT_RE.split(normalized)
    merged: list[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        text_without_citations = _clean_claim_text(part)
        if not text_without_citations and merged:
            merged[-1] = f"{merged[-1]} {part}".strip()
        else:
            merged.append(part)

    claims: list[ExtractedClaim] = []
    for index, part in enumerate(merged, start=1):
        text = _clean_claim_text(part)
        if not text:
            continue
        labels: list[str] = []
        seen: set[str] = set()
        for raw in _CITATION_RE.findall(part):
            label = f"S{int(raw)}"
            if label not in seen:
                seen.add(label)
                labels.append(label)

        claims.append(
            ExtractedClaim(
                claim_id=f"claim_{index:03d}",
                text=text,
                citation_labels=labels,
            )
        )
    return claims
