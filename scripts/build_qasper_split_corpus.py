"""Build a canonical chunk corpus from one QASPER parquet split only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from datasets import Dataset

from app.ingestion.chunker import chunk_document
from app.ingestion.dataset_normalizer import qasper_row_to_document


def build_qasper_split(
    input_parquet: Path,
    output_dir: Path,
    *,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
) -> dict:
    """Normalize and chunk exactly one QASPER split.

    Retrieval evaluation on QASPER is document-scoped, so validation only needs
    validation-paper chunks. Avoiding train/test embeddings makes model
    comparison much faster without changing within-document rankings.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    documents_path = output_dir / "documents.jsonl"
    chunks_path = output_dir / "chunks.jsonl"

    dataset = Dataset.from_parquet(str(input_parquet))
    document_count = 0
    chunk_count = 0

    with documents_path.open("w", encoding="utf-8") as documents_file, chunks_path.open(
        "w", encoding="utf-8"
    ) as chunks_file:
        for row in dataset:
            document = qasper_row_to_document(dict(row))
            documents_file.write(document.model_dump_json() + "\n")
            document_count += 1

            for chunk in chunk_document(
                document,
                chunk_size_words=chunk_size_words,
                overlap_words=overlap_words,
            ):
                chunks_file.write(chunk.model_dump_json() + "\n")
                chunk_count += 1

    manifest = {
        "format_version": 1,
        "dataset": "qasper",
        "source_split": input_parquet.name,
        "chunking": {
            "unit": "words",
            "chunk_size_words": chunk_size_words,
            "overlap_words": overlap_words,
            "crosses_provenance_boundaries": False,
        },
        "document_total": document_count,
        "chunk_total": chunk_count,
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
    parser = argparse.ArgumentParser(description="Build one QASPER split corpus.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/external/qasper/validation.parquet"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/qasper-validation"),
    )
    parser.add_argument("--chunk-size", type=int, default=220)
    parser.add_argument("--overlap", type=int, default=40)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = build_qasper_split(
        args.input,
        args.output,
        chunk_size_words=args.chunk_size,
        overlap_words=args.overlap,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
