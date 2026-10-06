"""Run Mode A classical RAG from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.rag import ClassicalRAG, OpenAICompatibleGenerator
from app.retrieval import SemanticRetriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask a cited question over a FAISS index.")
    parser.add_argument("question")
    parser.add_argument("--index", type=Path, default=Path("data/indexes/qasper"))
    parser.add_argument("--document-id")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    retriever = SemanticRetriever.load(args.index)
    generator = OpenAICompatibleGenerator(
        model=args.model,
        base_url=args.base_url,
    )
    rag = ClassicalRAG(retriever=retriever, generator=generator)
    result = rag.answer(
        args.question,
        top_k=args.top_k,
        document_id=args.document_id,
    )
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
