"""Tests for the first project milestone: PDF ingestion and provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from app.ingestion import PdfExtractionError, extract_pdf, pdf_extraction_to_document, save_extraction_json
import app.ingestion.pdf_extractor as pdf_extractor_module


def _make_test_pdf(path: Path) -> None:
    with pymupdf.open() as document:
        first = document.new_page()
        first.insert_text((72, 72), "Agentic Document Intelligence")

        second = document.new_page()
        second.insert_text((72, 72), "Evidence is attached to page two.")

        document.new_page()  # Deliberately empty for the quality check.
        document.save(path)


def test_extract_pdf_preserves_page_provenance(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _make_test_pdf(pdf)

    result = extract_pdf(pdf)

    assert result.filename == "sample.pdf"
    assert result.page_count == 3
    assert result.document_id.startswith("doc_")
    assert result.pages[0].page_number == 1
    assert result.pages[0].page_id == f"{result.document_id}:p0001"
    assert "Agentic Document Intelligence" in result.pages[0].text
    assert result.pages[1].page_id == f"{result.document_id}:p0002"
    assert result.pages[2].is_empty is True
    assert result.quality.empty_pages == [3]


def test_document_id_is_stable_for_same_bytes(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    _make_test_pdf(pdf)

    first = extract_pdf(pdf)
    second = extract_pdf(pdf)

    assert first.document_id == second.document_id
    assert first.source_sha256 == second.source_sha256


def test_json_output_is_readable(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    output = tmp_path / "result.json"
    _make_test_pdf(pdf)

    extraction = extract_pdf(pdf)
    save_extraction_json(extraction, output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["document_id"] == extraction.document_id
    assert payload["page_count"] == 3
    assert payload["pages"][1]["page_number"] == 2


def test_rejects_non_pdf(tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(PdfExtractionError, match="Only PDF files"):
        extract_pdf(text_file)



def test_v2_ocr_fallback_preserves_page_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "scanned-like.pdf"
    _make_test_pdf(pdf)

    def fake_ocr_page(page, *, language="eng", dpi=200):
        return "Recovered scanned page text.", 93.5

    monkeypatch.setattr(pdf_extractor_module, "_ocr_page", fake_ocr_page)

    result = extract_pdf(
        pdf,
        ocr_fallback=True,
        min_text_chars=1,
    )

    page = result.pages[2]
    assert page.page_number == 3
    assert page.page_id == f"{result.document_id}:p0003"
    assert page.text == "Recovered scanned page text."
    assert page.extraction_method == "ocr"
    assert page.ocr_applied is True
    assert page.ocr_confidence == 93.5
    assert result.quality.ocr_pages == [3]
    assert result.quality.empty_pages == []


def test_v2_ocr_metadata_reaches_corpus_segment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "scanned-like.pdf"
    _make_test_pdf(pdf)

    monkeypatch.setattr(
        pdf_extractor_module,
        "_ocr_page",
        lambda page, *, language="eng", dpi=200: ("OCR evidence text.", 88.0),
    )

    extraction = extract_pdf(pdf, ocr_fallback=True, min_text_chars=1)
    document = pdf_extraction_to_document(extraction)
    ocr_segment = next(
        segment for segment in document.segments
        if segment.page_number == 3
    )

    assert ocr_segment.metadata["extraction_method"] == "ocr"
    assert ocr_segment.metadata["ocr_applied"] is True
    assert ocr_segment.metadata["ocr_confidence"] == 88.0
