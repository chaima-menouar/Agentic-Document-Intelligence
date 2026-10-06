"""Build a cosine-similarity FAISS index from canonical retrieval chunks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.retrieval.index_builder import build_index
from app.retrieval.semantic import DEFAULT_EMBEDDING_MODEL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a FAISS semantic index.")
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/benchmark/chunks.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/indexes/qasper"),
    )
    parser.add_argument("--dataset", default="qasper")
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--query-prefix",
        default="",
        help="Optional prefix applied only when embedding queries.",
    )
    parser.add_argument("--limit", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = build_index(
        args.chunks,
        args.output,
        embedding_model=args.model,
        dataset_filter=args.dataset or None,
        batch_size=args.batch_size,
        limit=args.limit,
        query_prefix=args.query_prefix,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
