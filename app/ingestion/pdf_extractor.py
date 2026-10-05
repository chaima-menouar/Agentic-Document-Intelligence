"""Reliable page-by-page extraction for text-based PDFs.

Milestone 1 preserves page provenance before any chunking, embeddings, or LLM
work is introduced. Stable identifiers are derived from the PDF bytes so that
the same input document receives the same document/page identifiers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf

from app.models import DocumentExtraction, ExtractionQuality, PageExtraction


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be validated or extracted."""


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_text(text: str) -> str:
    """Normalize line endings and remove outer whitespace without rewriting content."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def extract_pdf(pdf_path: str | Path) -> DocumentExtraction:
    """Extract a text-based PDF page by page while preserving provenance.

    Args:
        pdf_path: Local path to a PDF file.

    Returns:
        A typed document extraction containing stable IDs, page text, and
        lightweight quality warnings.

    Raises:
        PdfExtractionError: If the path is invalid or PyMuPDF cannot read it.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PdfExtractionError(f"PDF does not exist: {path}")
    if not path.is_file():
        raise PdfExtractionError(f"Expected a file, got: {path}")
    if path.suffix.lower() != ".pdf":
        raise PdfExtractionError(f"Only PDF files are supported in V1: {path.name}")

    source_sha256 = _sha256_file(path)
    document_id = f"doc_{source_sha256[:12]}"
    pages: list[PageExtraction] = []
    empty_pages: list[int] = []

    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise PdfExtractionError(
                    "Password-protected PDFs are not supported in V1."
                )

            for zero_based_index, page in enumerate(document):
                page_number = zero_based_index + 1
                text = _normalize_text(page.get_text("text", sort=True))
                is_empty = not bool(text)

                if is_empty:
                    empty_pages.append(page_number)

                pages.append(
                    PageExtraction(
                        page_number=page_number,
                        page_id=f"{document_id}:p{page_number:04d}",
                        text=text,
                        char_count=len(text),
                        is_empty=is_empty,
                    )
                )
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError(f"Could not extract {path.name}: {exc}") from exc

    warnings: list[str] = []
    if empty_pages:
        warnings.append(
            "One or more pages produced no text. The PDF may contain scanned "
            "pages, figures-only pages, or extraction problems."
        )
    if not pages:
        warnings.append("The PDF contains no pages.")

    return DocumentExtraction(
        document_id=document_id,
        filename=path.name,
        source_sha256=source_sha256,
        page_count=len(pages),
        pages=pages,
        quality=ExtractionQuality(
            empty_pages=empty_pages,
            warnings=warnings,
        ),
    )


def save_extraction_json(
    extraction: DocumentExtraction,
    output_path: str | Path,
) -> Path:
    """Write a document extraction as readable UTF-8 JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        extraction.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path
