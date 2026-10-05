"""Typed schemas shared across ingestion and later RAG stages."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageExtraction(BaseModel):
    """Text and provenance for one PDF page."""

    page_number: int = Field(ge=1)
    page_id: str
    text: str
    char_count: int = Field(ge=0)
    is_empty: bool


class ExtractionQuality(BaseModel):
    """Simple quality signals produced during text extraction."""

    empty_pages: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentExtraction(BaseModel):
    """Normalized output of the PDF ingestion milestone."""

    document_id: str
    filename: str
    source_sha256: str
    page_count: int = Field(ge=0)
    pages: list[PageExtraction]
    quality: ExtractionQuality
