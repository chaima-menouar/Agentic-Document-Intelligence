"""Build one canonical retrieval corpus from the collected benchmark data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from datasets import Dataset

from app.ingestion.chunker import chunk_document
from app.ingestion.dataset_normalizer import (
    hotpot_row_to_documents,
    qasper_row_to_document,
    scifact_record_to_document,
)
from app.models import CorpusDocument


def _jsonl_records(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                yield json.loads(line)


def _write_document(
    document: CorpusDocument,
    *,
    documents_file,
    chunks_file,
    seen_ids: set[str],
    document_counts: Counter,
    chunk_counts: Counter,
    chunk_size_words: int,
    overlap_words: int,
) -> None:
    if document.document_id in seen_ids:
        return
    seen_ids.add(document.document_id)

    documents_file.write(document.model_dump_json() + "\n")
    document_counts[document.dataset] += 1

    for chunk in chunk_document(
        document,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
    ):
        chunks_file.write(chunk.model_dump_json() + "\n")
        chunk_counts[chunk.dataset] += 1


def build_corpus(
    input_dir: Path,
    output_dir: Path,
    *,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    documents_path = output_dir / "documents.jsonl"
    chunks_path = output_dir / "chunks.jsonl"

    seen_ids: set[str] = set()
    document_counts: Counter = Counter()
    chunk_counts: Counter = Counter()

    with documents_path.open("w", encoding="utf-8") as documents_file, chunks_path.open(
        "w", encoding="utf-8"
    ) as chunks_file:
        # QASPER papers
        qasper_dir = input_dir / "qasper"
        for parquet_path in sorted(qasper_dir.glob("*.parquet")):
            dataset = Dataset.from_parquet(str(parquet_path))
            for row in dataset:
                _write_document(
                    qasper_row_to_document(dict(row)),
                    documents_file=documents_file,
                    chunks_file=chunks_file,
                    seen_ids=seen_ids,
                    document_counts=document_counts,
                    chunk_counts=chunk_counts,
                    chunk_size_words=chunk_size_words,
                    overlap_words=overlap_words,
                )

        # SciFact corpus
        for record in _jsonl_records(input_dir / "scifact" / "corpus.jsonl"):
            _write_document(
                scifact_record_to_document(record),
                documents_file=documents_file,
                chunks_file=chunks_file,
                seen_ids=seen_ids,
                document_counts=document_counts,
                chunk_counts=chunk_counts,
                chunk_size_words=chunk_size_words,
                overlap_words=overlap_words,
            )

        # HotpotQA context documents. Repeated article titles are deduplicated.
        hotpot_dir = input_dir / "hotpotqa"
        for parquet_path in sorted(hotpot_dir.glob("*.parquet")):
            dataset = Dataset.from_parquet(str(parquet_path))
            for row in dataset:
                for document in hotpot_row_to_documents(dict(row)):
                    _write_document(
                        document,
                        documents_file=documents_file,
                        chunks_file=chunks_file,
                        seen_ids=seen_ids,
                        document_counts=document_counts,
                        chunk_counts=chunk_counts,
                        chunk_size_words=chunk_size_words,
                        overlap_words=overlap_words,
                    )

    manifest = {
        "format_version": 1,
        "chunking": {
            "unit": "words",
            "chunk_size_words": chunk_size_words,
            "overlap_words": overlap_words,
            "crosses_provenance_boundaries": False,
        },
        "documents": dict(sorted(document_counts.items())),
        "chunks": dict(sorted(chunk_counts.items())),
        "document_total": sum(document_counts.values()),
        "chunk_total": sum(chunk_counts.values()),
        "outputs": {
            "documents": documents_path.name,
            "chunks": chunks_path.name,
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize and chunk benchmark corpora.")
    parser.add_argument("--input", type=Path, default=Path("data/external"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/benchmark"),
    )
    parser.add_argument("--chunk-size", type=int, default=220)
    parser.add_argument("--overlap", type=int, default=40)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = build_corpus(
        args.input,
        args.output,
        chunk_size_words=args.chunk_size,
        overlap_words=args.overlap,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
