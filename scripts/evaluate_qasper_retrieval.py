"""Evaluate semantic evidence retrieval on the QASPER validation split."""

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
from app.retrieval.qasper_eval import (
    evidence_paragraphs,
    iter_qasper_questions,
    match_evidence_source_ids,
    recall_at_k,
)
from app.retrieval.semantic import SemanticRetriever


def evaluate(
    qasper_parquet: Path,
    index_dir: Path,
    output_path: Path,
    *,
    top_ks: list[int],
    include_title: bool = False,
    query_batch_size: int = 64,
    scope: str = "document",
) -> dict:
    dataset = Dataset.from_parquet(str(qasper_parquet))

    queries: list[str] = []
    question_ids: list[str] = []
    gold_source_ids: list[set[str]] = []
    document_ids: list[str] = []
    unmatched_evidence_questions = 0
    questions_without_text_evidence = 0

    for raw_row in dataset:
        row = dict(raw_row)
        document = qasper_row_to_document(row)
        title = document.title or ""

        for question_record in iter_qasper_questions(row):
            evidence = evidence_paragraphs(question_record.get("answers"))
            if not evidence:
                questions_without_text_evidence += 1
                continue

            gold = match_evidence_source_ids(document, evidence)
            if not gold:
                unmatched_evidence_questions += 1
                continue

            question = question_record["question"]
            query = f"{title}. {question}" if include_title and title else question
            queries.append(query)
            question_ids.append(question_record["question_id"])
            gold_source_ids.append(gold)
            document_ids.append(document.document_id)

    if not queries:
        raise RuntimeError("No evaluable QASPER questions with mapped text evidence.")

    retriever = SemanticRetriever.load(index_dir)
    max_k = max(top_ks)
    if scope == "document":
        all_hits = retriever.search_many_scoped(
            queries,
            document_ids,
            top_k=max_k,
            batch_size=query_batch_size,
        )
    elif scope == "global":
        all_hits = retriever.search_many(
            queries,
            top_k=max_k,
            batch_size=query_batch_size,
        )
    else:
        raise ValueError("scope must be either 'document' or 'global'.")
    ranked_source_ids = [
        [hit.source_id for hit in hits]
        for hits in all_hits
    ]

    metrics = {
        f"recall@{k}": recall_at_k(ranked_source_ids, gold_source_ids, k)
        for k in sorted(set(top_ks))
    }

    reciprocal_ranks: list[float] = []
    for predicted, gold in zip(ranked_source_ids, gold_source_ids, strict=True):
        reciprocal_rank = 0.0
        for rank, source_id in enumerate(predicted, start=1):
            if source_id in gold:
                reciprocal_rank = 1.0 / rank
                break
        reciprocal_ranks.append(reciprocal_rank)

    report = {
        "benchmark": "QASPER validation evidence retrieval",
        "query_mode": "title_plus_question" if include_title else "question_only",
        "retrieval_scope": scope,
        "evaluable_questions": len(queries),
        "questions_without_text_evidence": questions_without_text_evidence,
        "unmatched_evidence_questions": unmatched_evidence_questions,
        "max_k": max_k,
        "metrics": {
            **metrics,
            f"mrr@{max_k}": sum(reciprocal_ranks) / len(reciprocal_ranks),
        },
        "index_manifest": retriever.manifest,
        "sample_question_ids": question_ids[:10],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def _parse_top_ks(value: str) -> list[int]:
    values = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not values or any(item <= 0 for item in values):
        raise argparse.ArgumentTypeError("top-k values must be positive integers.")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate QASPER Recall@k.")
    parser.add_argument(
        "--qasper",
        type=Path,
        default=Path("data/external/qasper/validation.parquet"),
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/qasper_retrieval.json"),
    )
    parser.add_argument("--top-k", type=_parse_top_ks, default=[1, 3, 5, 10, 20])
    parser.add_argument("--include-title", action="store_true")
    parser.add_argument("--query-batch-size", type=int, default=64)
    parser.add_argument(
        "--scope",
        choices=["document", "global"],
        default="document",
        help="Search within the source paper (QASPER standard) or globally.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = evaluate(
        args.qasper,
        args.index,
        args.output,
        top_ks=args.top_k,
        include_title=args.include_title,
        query_batch_size=args.query_batch_size,
        scope=args.scope,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
