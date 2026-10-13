"""Evaluate V2 hybrid retrieval on QASPER validation evidence."""

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
from app.retrieval import (
    HybridRetriever,
    LocalCrossEncoderReranker,
    SemanticRetriever,
)
from app.retrieval.qasper_eval import (
    evidence_paragraphs,
    iter_qasper_questions,
    match_evidence_source_ids,
    recall_at_k,
)


def evaluate_hybrid(
    qasper_parquet: Path,
    index_dir: Path,
    output_path: Path,
    *,
    top_ks: list[int],
    mode: str = "hybrid_rrf",
    query_batch_size: int = 64,
    limit: int | None = None,
    candidate_multiplier: int = 4,
) -> dict:
    dataset = Dataset.from_parquet(str(qasper_parquet))

    queries: list[str] = []
    question_ids: list[str] = []
    gold_source_ids: list[set[str]] = []
    document_ids: list[str] = []
    unmatched_evidence_questions = 0
    questions_without_text_evidence = 0

    stop = False
    for raw_row in dataset:
        row = dict(raw_row)
        document = qasper_row_to_document(row)

        for question_record in iter_qasper_questions(row):
            evidence = evidence_paragraphs(question_record.get("answers"))
            if not evidence:
                questions_without_text_evidence += 1
                continue

            gold = match_evidence_source_ids(document, evidence)
            if not gold:
                unmatched_evidence_questions += 1
                continue

            queries.append(question_record["question"])
            question_ids.append(question_record["question_id"])
            gold_source_ids.append(gold)
            document_ids.append(document.document_id)

            if limit is not None and len(queries) >= limit:
                stop = True
                break
        if stop:
            break

    if not queries:
        raise RuntimeError("No evaluable QASPER questions with mapped text evidence.")

    dense = SemanticRetriever.load(index_dir)
    if mode == "hybrid_rrf":
        reranker = None
    elif mode == "hybrid_reranked":
        reranker = LocalCrossEncoderReranker()
    else:
        raise ValueError("mode must be 'hybrid_rrf' or 'hybrid_reranked'.")

    retriever = HybridRetriever(
        dense,
        reranker=reranker,
        candidate_multiplier=candidate_multiplier,
    )

    max_k = max(top_ks)
    all_hits = retriever.search_many_scoped(
        queries,
        document_ids,
        top_k=max_k,
        batch_size=query_batch_size,
    )
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
        "benchmark": "QASPER validation V2 hybrid evidence retrieval",
        "retrieval_mode": mode,
        "evaluable_questions": len(queries),
        "questions_without_text_evidence": questions_without_text_evidence,
        "unmatched_evidence_questions": unmatched_evidence_questions,
        "max_k": max_k,
        "candidate_multiplier": candidate_multiplier,
        "limit": limit,
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
    parser = argparse.ArgumentParser(
        description="Evaluate V2 hybrid QASPER retrieval."
    )
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
        default=Path("data/evaluation/qasper_hybrid.json"),
    )
    parser.add_argument(
        "--mode",
        choices=["hybrid_rrf", "hybrid_reranked"],
        default="hybrid_rrf",
    )
    parser.add_argument("--top-k", type=_parse_top_ks, default=[1, 3, 5, 10, 20])
    parser.add_argument("--query-batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--candidate-multiplier", type=int, default=4)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = evaluate_hybrid(
        args.qasper,
        args.index,
        args.output,
        top_ks=args.top_k,
        mode=args.mode,
        query_batch_size=args.query_batch_size,
        limit=args.limit,
        candidate_multiplier=args.candidate_multiplier,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
