"""Compare Classical, Verified, and Agentic RAG on the same questions.

Input JSONL format:
{"question": "...", "document_id": "optional-document-id"}

The script uses the free offline ExtractiveGenerator by default, so it can run
without API keys or paid services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.agent import AgenticVerifiedRAG
from app.evaluation import (
    aggregate_mode_metrics,
    evaluate_agentic_answer,
    evaluate_classical_answer,
    evaluate_verified_answer,
)
from app.rag import ClassicalRAG, ExtractiveGenerator
from app.retrieval import SemanticRetriever
from app.verification import CitationGroundingVerifier, VerifiedRAG


def _read_questions(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            row = json.loads(raw)
            question = str(row.get("question", "")).strip()
            if not question:
                raise ValueError(f"Missing question on line {line_number}.")
            rows.append(
                {
                    "question": question,
                    "document_id": row.get("document_id"),
                }
            )
    if not rows:
        raise ValueError("Evaluation file contains no questions.")
    return rows


def evaluate(
    *,
    index_dir: Path,
    questions_path: Path,
    output_dir: Path,
    top_k: int,
    max_rounds: int,
    additional_top_k: int,
) -> dict:
    retriever = SemanticRetriever.load(index_dir)
    generator = ExtractiveGenerator()
    rag = ClassicalRAG(retriever=retriever, generator=generator)
    verifier = CitationGroundingVerifier()
    verified = VerifiedRAG(rag=rag, verifier=verifier)
    agentic = AgenticVerifiedRAG(
        verified_rag=verified,
        retriever=retriever,
        verifier=verifier,
        max_rounds=max_rounds,
        additional_top_k=additional_top_k,
    )

    questions = _read_questions(questions_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "abc_records.jsonl"
    summary_path = output_dir / "abc_summary.json"

    mode_a_metrics: list[dict[str, float]] = []
    mode_b_metrics: list[dict[str, float]] = []
    mode_c_metrics: list[dict[str, float]] = []

    with records_path.open("w", encoding="utf-8") as handle:
        for item in questions:
            question = item["question"]
            document_id = item["document_id"]

            mode_a = rag.answer(
                question,
                top_k=top_k,
                document_id=document_id,
            )
            mode_b = verified.answer(
                question,
                top_k=top_k,
                document_id=document_id,
            )
            mode_c = agentic.answer(
                question,
                top_k=top_k,
                document_id=document_id,
            )

            metrics_a = evaluate_classical_answer(mode_a)
            metrics_b = evaluate_verified_answer(mode_b)
            metrics_c = evaluate_agentic_answer(mode_c)
            mode_a_metrics.append(metrics_a)
            mode_b_metrics.append(metrics_b)
            mode_c_metrics.append(metrics_c)

            record = {
                "question": question,
                "document_id": document_id,
                "mode_a": {
                    "answer": mode_a.model_dump(mode="json"),
                    "metrics": metrics_a,
                },
                "mode_b": {
                    "answer": mode_b.model_dump(mode="json"),
                    "metrics": metrics_b,
                },
                "mode_c": {
                    "answer": mode_c.model_dump(mode="json"),
                    "metrics": metrics_c,
                },
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "configuration": {
            "index_dir": str(index_dir),
            "questions_path": str(questions_path),
            "top_k": top_k,
            "max_rounds": max_rounds,
            "additional_top_k": additional_top_k,
            "generator": "ExtractiveGenerator",
        },
        "mode_a_classical": aggregate_mode_metrics(mode_a_metrics),
        "mode_b_verified": aggregate_mode_metrics(mode_b_metrics),
        "mode_c_agentic": aggregate_mode_metrics(mode_c_metrics),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/abc"),
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--additional-top-k", type=int, default=5)
    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k must be greater than zero")
    if args.max_rounds <= 0:
        parser.error("--max-rounds must be greater than zero")
    if args.additional_top_k <= 0:
        parser.error("--additional-top-k must be greater than zero")

    summary = evaluate(
        index_dir=args.index,
        questions_path=args.questions,
        output_dir=args.output,
        top_k=args.top_k,
        max_rounds=args.max_rounds,
        additional_top_k=args.additional_top_k,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
