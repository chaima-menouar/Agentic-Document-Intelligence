"""Tests for local PDF workspace preparation."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from app.ui.workspace import prepare_uploaded_pdfs


def _pdf_bytes(pages: list[str]) -> bytes:
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def test_prepare_uploaded_pdfs_preserves_documents_and_pages(tmp_path: Path) -> None:
    chunks_path, summaries, total_chunks = prepare_uploaded_pdfs(
        [
            ("first.pdf", _pdf_bytes(["alpha evidence", "beta evidence"])),
            ("second.pdf", _pdf_bytes(["gamma evidence"])),
        ],
        tmp_path,
        chunk_size_words=50,
        overlap_words=5,
    )

    assert chunks_path.exists()
    assert len(summaries) == 2
    assert summaries[0].page_count == 2
    assert summaries[1].page_count == 1
    assert total_chunks == 3

    lines = chunks_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert '"page_number":1' in lines[0]
    assert '"page_number":2' in lines[1]


def test_prepare_uploaded_pdfs_rejects_empty_upload_set(tmp_path: Path) -> None:
    try:
        prepare_uploaded_pdfs([], tmp_path)
    except ValueError as exc:
        assert "No valid PDF uploads" in str(exc)
    else:
        raise AssertionError("Expected ValueError for an empty upload set.")
