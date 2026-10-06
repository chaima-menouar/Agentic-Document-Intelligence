"""Reliable page-by-page PDF extraction with optional local OCR fallback."""

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


def _ocr_page(page, *, language: str = "eng", dpi: int = 200) -> tuple[str, float | None]:
    """OCR one PDF page locally with Tesseract.

    The dependency is imported lazily so ordinary text PDFs keep the lightweight
    V1 path. A clear error is returned if OCR was requested but unavailable.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise PdfExtractionError(
            "OCR dependencies are not installed. Install requirements-ocr.txt."
        ) from exc

    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    try:
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT,
        )
    except Exception as exc:
        raise PdfExtractionError(
            "Local OCR failed. Ensure the Tesseract executable and requested "
            f"language '{language}' are installed: {exc}"
        ) from exc

    words: list[str] = []
    confidences: list[float] = []
    for text, raw_conf in zip(data.get("text", []), data.get("conf", []), strict=False):
        text = str(text).strip()
        if not text:
            continue
        words.append(text)
        try:
            confidence = float(raw_conf)
        except (TypeError, ValueError):
            continue
        if confidence >= 0:
            confidences.append(confidence)

    text = _normalize_text(" ".join(words))
    confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else None
    )
    return text, confidence


def extract_pdf(
    pdf_path: str | Path,
    *,
    ocr_fallback: bool = False,
    min_text_chars: int = 40,
    ocr_language: str = "eng",
    ocr_dpi: int = 200,
) -> DocumentExtraction:
    """Extract a PDF page by page while preserving provenance.

    V2 can optionally OCR pages that produce too little embedded text. Text
    extraction remains the default path, so V1 behavior stays reproducible.

    Args:
        pdf_path: Local path to a PDF file.
        ocr_fallback: OCR text-poor pages locally when enabled.
        min_text_chars: Minimum embedded-text characters before OCR is attempted.
        ocr_language: Tesseract language code.
        ocr_dpi: Render resolution used before OCR.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PdfExtractionError(f"PDF does not exist: {path}")
    if not path.is_file():
        raise PdfExtractionError(f"Expected a file, got: {path}")
    if path.suffix.lower() != ".pdf":
        raise PdfExtractionError(f"Only PDF files are supported: {path.name}")
    if min_text_chars < 0:
        raise ValueError("min_text_chars must be non-negative.")
    if ocr_dpi <= 0:
        raise ValueError("ocr_dpi must be greater than zero.")

    source_sha256 = _sha256_file(path)
    document_id = f"doc_{source_sha256[:12]}"
    pages: list[PageExtraction] = []
    empty_pages: list[int] = []
    ocr_pages: list[int] = []

    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise PdfExtractionError(
                    "Password-protected PDFs are not supported."
                )

            for zero_based_index, page in enumerate(document):
                page_number = zero_based_index + 1
                text = _normalize_text(page.get_text("text", sort=True))
                method = "text"
                ocr_applied = False
                ocr_confidence = None

                if ocr_fallback and len(text) < min_text_chars:
                    ocr_text, ocr_confidence = _ocr_page(
                        page,
                        language=ocr_language,
                        dpi=ocr_dpi,
                    )
                    if ocr_text:
                        text = ocr_text
                        method = "ocr"
                        ocr_applied = True
                        ocr_pages.append(page_number)

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
                        extraction_method=method,
                        ocr_applied=ocr_applied,
                        ocr_confidence=ocr_confidence,
                    )
                )
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError(f"Could not extract {path.name}: {exc}") from exc

    warnings: list[str] = []
    if ocr_pages:
        warnings.append(
            f"Local OCR was used on {len(ocr_pages)} page(s): "
            + ", ".join(str(page) for page in ocr_pages)
            + "."
        )
    if empty_pages:
        warnings.append(
            "One or more pages produced no text even after the configured "
            "extraction path."
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
            ocr_pages=ocr_pages,
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
