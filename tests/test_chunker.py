"""Tests for provenance-preserving chunking."""

from __future__ import annotations

import pytest

from app.ingestion.chunker import chunk_document
from app.models import CorpusDocument, SourceSegment


def test_chunking_preserves_source_provenance() -> None:
    document = CorpusDocument(
        dataset="test",
        document_id="doc:test",
        title="Example",
        segments=[
            SourceSegment(
                segment_id="doc:test:p0001",
                text="one two three four five six seven eight nine ten",
                page_number=1,
                section="Intro",
            )
        ],
    )

    chunks = chunk_document(document, chunk_size_words=4, overlap_words=1)

    assert [chunk.text for chunk in chunks] == [
        "one two three four",
        "four five six seven",
        "seven eight nine ten",
    ]
    assert all(chunk.source_id == "doc:test:p0001" for chunk in chunks)
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.section == "Intro" for chunk in chunks)
    assert [chunk.start_word for chunk in chunks] == [0, 3, 6]
    assert [chunk.end_word for chunk in chunks] == [4, 7, 10]


def test_chunking_never_crosses_segments() -> None:
    document = CorpusDocument(
        dataset="test",
        document_id="doc:test",
        segments=[
            SourceSegment(segment_id="s1", text="alpha beta"),
            SourceSegment(segment_id="s2", text="gamma delta"),
        ],
    )

    chunks = chunk_document(document, chunk_size_words=10, overlap_words=0)

    assert len(chunks) == 2
    assert chunks[0].source_id == "s1"
    assert chunks[0].text == "alpha beta"
    assert chunks[1].source_id == "s2"
    assert chunks[1].text == "gamma delta"


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunking_configuration(chunk_size: int, overlap: int) -> None:
    document = CorpusDocument(dataset="test", document_id="doc", segments=[])

    with pytest.raises(ValueError):
        chunk_document(
            document,
            chunk_size_words=chunk_size,
            overlap_words=overlap,
        )
