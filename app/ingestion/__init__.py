"""PDF ingestion, dataset normalization, and provenance-preserving chunking."""

from .chunker import chunk_document, normalize_chunk_text
from .dataset_normalizer import (
    clean_text,
    hotpot_row_to_documents,
    pdf_extraction_to_document,
    qasper_row_to_document,
    scifact_record_to_document,
)
from .pdf_extractor import PdfExtractionError, extract_pdf, save_extraction_json

__all__ = [
    "PdfExtractionError",
    "chunk_document",
    "clean_text",
    "extract_pdf",
    "hotpot_row_to_documents",
    "normalize_chunk_text",
    "pdf_extraction_to_document",
    "qasper_row_to_document",
    "save_extraction_json",
    "scifact_record_to_document",
]
