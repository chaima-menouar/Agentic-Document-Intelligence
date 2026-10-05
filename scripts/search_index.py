"""Search a built semantic FAISS index from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.retrieval.semantic import SemanticRetriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search the semantic retrieval index.")
    parser.add_argument("query", help="Natural-language question or search query.")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper"),
        help="Directory containing index.faiss, chunks.jsonl, and manifest.json.",
    )
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    retriever = SemanticRetriever.load(args.index)
    hits = retriever.search(args.query, top_k=args.top_k)

    payload = [
        {
            "rank": hit.rank,
            "score": round(hit.score, 6),
            "dataset": hit.dataset,
            "document_id": hit.document_id,
            "chunk_id": hit.chunk_id,
            "source_id": hit.source_id,
            "page_number": hit.page_number,
            "section": hit.section,
            "text": hit.text,
        }
        for hit in hits
    ]
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
