"""End-to-end smoke test for Mode B Verified RAG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from datasets import Dataset

from app.ingestion.dataset_normalizer import qasper_row_to_document
from app.rag import ClassicalRAG, ExtractiveGenerator
from app.retrieval import SemanticRetriever, iter_qasper_questions
from app.verification import CitationGroundingVerifier, VerifiedRAG


def run_smoke(qasper_path: Path, index_dir: Path, output_path: Path) -> dict:
    dataset = Dataset.from_parquet(str(qasper_path))
    retriever = SemanticRetriever.load(index_dir)
    classical = ClassicalRAG(
        retriever=retriever,
        generator=ExtractiveGenerator(),
    )
    pipeline = VerifiedRAG(
        rag=classical,
        verifier=CitationGroundingVerifier(),
    )

    selected = None
    for raw_row in dataset:
        row = dict(raw_row)
        document = qasper_row_to_document(row)
        questions = list(iter_qasper_questions(row))
        if not questions:
            continue

        question = str(questions[0]["question"]).strip()
        if not question:
            continue

        candidate = pipeline.answer(
            question,
            top_k=3,
            document_id=document.document_id,
        )
        if (
            candidate.verification_status == "verified"
            and candidate.verifications
            and candidate.citations
        ):
            selected = (document.document_id, candidate)
            break

    if selected is None:
        raise RuntimeError("Could not produce a fully verified Mode B smoke answer.")

    document_id, result = selected
    report = {
        "mode": "verified_rag",
        "generator": "extractive_offline_baseline",
        "verifier": "citation_grounding_lexical_baseline",
        "retriever_model": retriever.manifest["embedding_model"],
        "document_id": document_id,
        "result": result.model_dump(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test Mode B end to end.")
    parser.add_argument(
        "--qasper",
        type=Path,
        default=Path("data/external/qasper/validation.parquet"),
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper-bge-small"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/verified_rag_smoke.json"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_smoke(args.qasper, args.index, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
