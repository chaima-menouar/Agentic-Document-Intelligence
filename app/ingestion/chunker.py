"""Word-window chunking that never crosses provenance boundaries."""

from __future__ import annotations

import re

from app.models import CorpusDocument, TextChunk

_WHITESPACE = re.compile(r"\s+")


def normalize_chunk_text(text: str) -> str:
    """Collapse repeated whitespace while preserving the words themselves."""
    return _WHITESPACE.sub(" ", text).strip()


def chunk_document(
    document: CorpusDocument,
    *,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
) -> list[TextChunk]:
    """Split each source segment into overlapping word windows.

    Chunks never cross source segments. This is important for trustworthy
    citations: a chunk can always be mapped back to one page/section/sentence.
    """

    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be greater than zero.")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative.")
    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words.")

    step = chunk_size_words - overlap_words
    chunks: list[TextChunk] = []
    chunk_index = 1

    for segment in document.segments:
        normalized = normalize_chunk_text(segment.text)
        if not normalized:
            continue

        words = normalized.split(" ")
        for start in range(0, len(words), step):
            end = min(start + chunk_size_words, len(words))
            chunk_words = words[start:end]
            if not chunk_words:
                continue

            chunks.append(
                TextChunk(
                    dataset=document.dataset,
                    document_id=document.document_id,
                    chunk_id=f"{document.document_id}:c{chunk_index:05d}",
                    source_id=segment.segment_id,
                    text=" ".join(chunk_words),
                    page_number=segment.page_number,
                    section=segment.section,
                    start_word=start,
                    end_word=end,
                    word_count=len(chunk_words),
                    metadata=dict(segment.metadata),
                )
            )
            chunk_index += 1

            if end == len(words):
                break

    return chunks
