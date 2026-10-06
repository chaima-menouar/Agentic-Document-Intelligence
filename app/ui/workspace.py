"""Local document workspace used by the Streamlit UI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.ingestion import chunk_document, extract_pdf, pdf_extraction_to_document
from app.retrieval import build_index

BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass(frozen=True)
class ProcessedDocumentSummary:
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceBuildResult:
    workspace_dir: Path
    index_dir: Path
    chunks_path: Path
    documents: tuple[ProcessedDocumentSummary, ...]
    total_chunks: int
    index_manifest: dict


def _safe_pdf_name(name: str, index: int) -> str:
    base = Path(name).name
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return f"{index:03d}_{base}"


def prepare_uploaded_pdfs(
    uploads: Iterable[tuple[str, bytes]],
    workspace_dir: Path,
    *,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
    ocr_fallback: bool = True,
    min_text_chars: int = 40,
    ocr_language: str = "eng",
) -> tuple[Path, tuple[ProcessedDocumentSummary, ...], int]:
    """Persist uploaded PDFs, extract them, and write canonical chunks JSONL."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = workspace_dir / "uploads"
    processed_dir = workspace_dir / "processed"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    chunks_path = processed_dir / "chunks.jsonl"
    summaries: list[ProcessedDocumentSummary] = []
    total_chunks = 0

    with chunks_path.open("w", encoding="utf-8") as chunks_file:
        for index, (filename, payload) in enumerate(uploads, start=1):
            if not payload:
                continue

            pdf_path = uploads_dir / _safe_pdf_name(filename, index)
            pdf_path.write_bytes(payload)

            extraction = extract_pdf(
                pdf_path,
                ocr_fallback=ocr_fallback,
                min_text_chars=min_text_chars,
                ocr_language=ocr_language,
            )
            document = pdf_extraction_to_document(extraction)
            chunks = chunk_document(
                document,
                chunk_size_words=chunk_size_words,
                overlap_words=overlap_words,
            )
            for chunk in chunks:
                chunks_file.write(chunk.model_dump_json() + "\n")

            total_chunks += len(chunks)
            summaries.append(
                ProcessedDocumentSummary(
                    document_id=document.document_id,
                    filename=extraction.filename,
                    page_count=extraction.page_count,
                    chunk_count=len(chunks),
                    warnings=tuple(extraction.quality.warnings),
                )
            )

    if not summaries:
        raise ValueError("No valid PDF uploads were provided.")
    if total_chunks == 0:
        raise ValueError(
            "The uploaded PDFs produced no text chunks. "
            "Scanned PDFs without extractable text are not supported in V1."
        )

    return chunks_path, tuple(summaries), total_chunks


def build_local_workspace(
    uploads: Iterable[tuple[str, bytes]],
    workspace_dir: Path,
    *,
    embedding_model: str = BGE_MODEL,
    query_prefix: str = BGE_QUERY_PREFIX,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
    batch_size: int = 64,
    ocr_fallback: bool = True,
    min_text_chars: int = 40,
    ocr_language: str = "eng",
) -> WorkspaceBuildResult:
    """Create a local multi-PDF semantic workspace and FAISS index."""
    chunks_path, summaries, total_chunks = prepare_uploaded_pdfs(
        uploads,
        workspace_dir,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
        ocr_fallback=ocr_fallback,
        min_text_chars=min_text_chars,
        ocr_language=ocr_language,
    )

    index_dir = workspace_dir / "index"
    manifest = build_index(
        chunks_path,
        index_dir,
        embedding_model=embedding_model,
        dataset_filter="uploaded_pdf",
        batch_size=batch_size,
        query_prefix=query_prefix,
    )
    return WorkspaceBuildResult(
        workspace_dir=workspace_dir,
        index_dir=index_dir,
        chunks_path=chunks_path,
        documents=summaries,
        total_chunks=total_chunks,
        index_manifest=manifest,
    )


def workspace_summary_json(result: WorkspaceBuildResult) -> str:
    """Serialize a lightweight UI-safe summary for debugging/export."""
    payload = {
        "total_chunks": result.total_chunks,
        "embedding_model": result.index_manifest.get("embedding_model"),
        "documents": [
            {
                "document_id": item.document_id,
                "filename": item.filename,
                "page_count": item.page_count,
                "chunk_count": item.chunk_count,
                "warnings": list(item.warnings),
            }
            for item in result.documents
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
