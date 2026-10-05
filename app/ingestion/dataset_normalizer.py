"""Adapters that normalize heterogeneous datasets into one corpus schema."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

from app.models import CorpusDocument, DocumentExtraction, SourceSegment

_WHITESPACE = re.compile(r"\s+")


def clean_text(value: Any) -> str:
    """Return stable single-spaced text for heterogeneous source values."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value if item is not None)
    return _WHITESPACE.sub(" ", str(value)).strip()


def pdf_extraction_to_document(
    extraction: DocumentExtraction,
    *,
    dataset: str = "uploaded_pdf",
) -> CorpusDocument:
    """Convert page-level PDF extraction into the canonical corpus schema."""
    segments = [
        SourceSegment(
            segment_id=page.page_id,
            text=page.text,
            page_number=page.page_number,
            section=None,
            metadata={"filename": extraction.filename},
        )
        for page in extraction.pages
        if clean_text(page.text)
    ]

    return CorpusDocument(
        dataset=dataset,
        document_id=extraction.document_id,
        title=extraction.filename,
        segments=segments,
        metadata={
            "filename": extraction.filename,
            "source_sha256": extraction.source_sha256,
        },
    )


def _iter_qasper_sections(full_text: Any) -> Iterable[tuple[str | None, list[str]]]:
    """Yield QASPER sections across both Arrow and Python nested layouts."""
    if isinstance(full_text, list):
        for section in full_text:
            if not isinstance(section, dict):
                continue
            name = clean_text(section.get("section_name")) or None
            paragraphs = section.get("paragraphs") or []
            if isinstance(paragraphs, str):
                paragraphs = [paragraphs]
            yield name, [clean_text(p) for p in paragraphs if clean_text(p)]
        return

    if isinstance(full_text, dict):
        names = full_text.get("section_name") or []
        paragraphs_by_section = full_text.get("paragraphs") or []
        if isinstance(names, str):
            names = [names]
        if paragraphs_by_section and isinstance(paragraphs_by_section[0], str):
            paragraphs_by_section = [paragraphs_by_section]

        for index, paragraphs in enumerate(paragraphs_by_section):
            name = clean_text(names[index]) if index < len(names) else ""
            if isinstance(paragraphs, str):
                paragraphs = [paragraphs]
            yield name or None, [clean_text(p) for p in paragraphs if clean_text(p)]


def qasper_row_to_document(row: dict[str, Any]) -> CorpusDocument:
    """Normalize one QASPER paper while keeping section/paragraph provenance."""
    raw_id = clean_text(row.get("id"))
    if not raw_id:
        raise ValueError("QASPER row is missing an id.")

    document_id = f"qasper:{raw_id}"
    segments: list[SourceSegment] = []

    abstract = clean_text(row.get("abstract"))
    if abstract:
        segments.append(
            SourceSegment(
                segment_id=f"{document_id}:abstract",
                text=abstract,
                section="Abstract",
                metadata={"source_kind": "abstract"},
            )
        )

    for section_index, (section_name, paragraphs) in enumerate(
        _iter_qasper_sections(row.get("full_text") or [])
    ):
        for paragraph_index, paragraph in enumerate(paragraphs):
            segments.append(
                SourceSegment(
                    segment_id=(
                        f"{document_id}:s{section_index:03d}:p{paragraph_index:04d}"
                    ),
                    text=paragraph,
                    section=section_name,
                    metadata={
                        "source_kind": "paragraph",
                        "section_index": section_index,
                        "paragraph_index": paragraph_index,
                    },
                )
            )

    return CorpusDocument(
        dataset="qasper",
        document_id=document_id,
        title=clean_text(row.get("title")) or None,
        segments=segments,
        metadata={"source_id": raw_id},
    )


def scifact_record_to_document(record: dict[str, Any]) -> CorpusDocument:
    """Normalize one SciFact abstract with sentence-level evidence provenance."""
    raw_id = record.get("doc_id")
    if raw_id is None:
        raise ValueError("SciFact record is missing doc_id.")

    document_id = f"scifact:{raw_id}"
    abstract = record.get("abstract") or []
    if isinstance(abstract, str):
        abstract = [abstract]

    segments = [
        SourceSegment(
            segment_id=f"{document_id}:sent{index:04d}",
            text=clean_text(sentence),
            section="Abstract",
            metadata={"sentence_index": index, "source_kind": "abstract_sentence"},
        )
        for index, sentence in enumerate(abstract)
        if clean_text(sentence)
    ]

    return CorpusDocument(
        dataset="scifact",
        document_id=document_id,
        title=clean_text(record.get("title")) or None,
        segments=segments,
        metadata={"source_id": str(raw_id)},
    )


def _hotpot_document_id(title: str) -> str:
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    return f"hotpot:{digest}"


def hotpot_row_to_documents(row: dict[str, Any]) -> list[CorpusDocument]:
    """Normalize the context documents contained in one HotpotQA example."""
    context = row.get("context") or {}
    documents: list[CorpusDocument] = []

    if isinstance(context, dict):
        titles = context.get("title") or []
        sentence_groups = context.get("sentences") or []
        pairs = zip(titles, sentence_groups, strict=False)
    elif isinstance(context, list):
        pairs = (
            (item.get("title"), item.get("sentences"))
            for item in context
            if isinstance(item, dict)
        )
    else:
        return documents

    for raw_title, raw_sentences in pairs:
        title = clean_text(raw_title)
        if not title:
            continue
        if isinstance(raw_sentences, str):
            raw_sentences = [raw_sentences]
        sentences = raw_sentences or []
        document_id = _hotpot_document_id(title)
        segments = [
            SourceSegment(
                segment_id=f"{document_id}:sent{index:04d}",
                text=clean_text(sentence),
                section=None,
                metadata={"sentence_index": index, "source_kind": "context_sentence"},
            )
            for index, sentence in enumerate(sentences)
            if clean_text(sentence)
        ]
        documents.append(
            CorpusDocument(
                dataset="hotpotqa",
                document_id=document_id,
                title=title,
                segments=segments,
                metadata={"source_title": title},
            )
        )

    return documents
