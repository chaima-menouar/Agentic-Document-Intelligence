"""Typed schemas shared across ingestion, chunking, and later RAG stages."""

from __future__ import annotations

from typing import Any

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


class SourceSegment(BaseModel):
    """A provenance-preserving source unit before chunking.

    A segment is deliberately smaller than a document and has one stable
    provenance boundary: a PDF page, a QASPER paragraph, a SciFact sentence,
    or a HotpotQA context sentence.
    """

    segment_id: str
    text: str
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorpusDocument(BaseModel):
    """Canonical document representation shared by all input datasets."""

    dataset: str
    document_id: str
    title: str | None = None
    segments: list[SourceSegment]
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    """Retrieval unit with explicit source provenance."""

    dataset: str
    document_id: str
    chunk_id: str
    source_id: str
    text: str
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None
    start_word: int = Field(ge=0)
    end_word: int = Field(ge=0)
    word_count: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)



class AnswerCitation(BaseModel):
    """Citation linking a generated answer back to one retrieved source chunk."""

    label: str
    dataset: str
    document_id: str
    chunk_id: str
    source_id: str
    score: float
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None
    text: str


class RAGAnswer(BaseModel):
    """Mode A output with answer text and inspectable evidence citations."""

    question: str
    answer: str
    status: str
    citations: list[AnswerCitation] = Field(default_factory=list)
    retrieved_chunks: int = Field(ge=0)
    used_citation_labels: list[str] = Field(default_factory=list)



class ExtractedClaim(BaseModel):
    """One factual claim extracted from a generated answer."""

    claim_id: str
    text: str
    citation_labels: list[str] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    """Grounding decision for one extracted claim."""

    claim_id: str
    claim_text: str
    citation_labels: list[str] = Field(default_factory=list)
    evidence_labels: list[str] = Field(default_factory=list)
    status: str
    support_score: float = Field(ge=0.0, le=1.0)
    reason: str


class VerifiedRAGAnswer(BaseModel):
    """Mode B output: a RAG answer plus claim-level verification."""

    question: str
    answer: str
    base_status: str
    verification_status: str
    claims: list[ExtractedClaim] = Field(default_factory=list)
    verifications: list[ClaimVerification] = Field(default_factory=list)
    citations: list[AnswerCitation] = Field(default_factory=list)
    retrieved_chunks: int = Field(ge=0)



class CorrectedRAGAnswer(BaseModel):
    """Mode B corrected output after removing unsupported claims."""

    question: str
    original_answer: str
    final_answer: str
    correction_status: str
    verification_status: str
    claims: list[ExtractedClaim] = Field(default_factory=list)
    verifications: list[ClaimVerification] = Field(default_factory=list)
    citations: list[AnswerCitation] = Field(default_factory=list)
    kept_claim_ids: list[str] = Field(default_factory=list)
    removed_claim_ids: list[str] = Field(default_factory=list)
    retrieved_chunks: int = Field(ge=0)



class AgenticRetrievalStep(BaseModel):
    """One bounded re-retrieval action taken for an unresolved claim."""

    round_index: int = Field(ge=1)
    claim_id: str
    query: str
    retrieved_labels: list[str] = Field(default_factory=list)
    support_score: float = Field(ge=0.0, le=1.0)
    resolved: bool


class AgenticRAGAnswer(BaseModel):
    """Mode C output with bounded re-retrieval audit trail."""

    question: str
    initial_answer: str
    final_answer: str
    status: str
    initial_verification_status: str
    final_verification_status: str
    correction_status: str
    rounds_used: int = Field(ge=0)
    additional_chunks_considered: int = Field(ge=0)
    recovered_claim_ids: list[str] = Field(default_factory=list)
    unresolved_claim_ids: list[str] = Field(default_factory=list)
    steps: list[AgenticRetrievalStep] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)
    verifications: list[ClaimVerification] = Field(default_factory=list)
    citations: list[AnswerCitation] = Field(default_factory=list)
