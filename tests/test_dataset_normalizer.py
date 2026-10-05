"""Tests for dataset adapters and canonical provenance."""

from __future__ import annotations

from app.ingestion.dataset_normalizer import (
    hotpot_row_to_documents,
    qasper_row_to_document,
    scifact_record_to_document,
)


def test_qasper_normalization_keeps_section_and_paragraph_ids() -> None:
    row = {
        "id": "paper-1",
        "title": "A Paper",
        "abstract": "Abstract text.",
        "full_text": {
            "section_name": ["Introduction", "Method"],
            "paragraphs": [
                ["First paragraph.", "Second paragraph."],
                ["Method paragraph."],
            ],
        },
    }

    document = qasper_row_to_document(row)

    assert document.document_id == "qasper:paper-1"
    assert document.dataset == "qasper"
    assert len(document.segments) == 4
    assert document.segments[1].section == "Introduction"
    assert document.segments[1].segment_id.endswith(":s000:p0000")
    assert document.segments[3].section == "Method"


def test_scifact_normalization_preserves_sentence_index() -> None:
    document = scifact_record_to_document(
        {
            "doc_id": 123,
            "title": "Scientific finding",
            "abstract": ["Sentence zero.", "Sentence one."],
        }
    )

    assert document.document_id == "scifact:123"
    assert len(document.segments) == 2
    assert document.segments[1].metadata["sentence_index"] == 1
    assert document.segments[1].segment_id == "scifact:123:sent0001"


def test_hotpot_normalization_creates_stable_context_documents() -> None:
    row = {
        "context": {
            "title": ["Article A", "Article B"],
            "sentences": [
                ["A first.", "A second."],
                ["B first."],
            ],
        }
    }

    first = hotpot_row_to_documents(row)
    second = hotpot_row_to_documents(row)

    assert len(first) == 2
    assert first[0].document_id == second[0].document_id
    assert first[0].segments[1].metadata["sentence_index"] == 1
    assert first[1].title == "Article B"
