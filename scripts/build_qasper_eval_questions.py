"""Build a deterministic QASPER question set for A/B/C RAG evaluation."""

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
)


def build_questions(qasper_path: Path, output_path: Path, *, limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    dataset = Dataset.from_parquet(str(qasper_path))
    rows: list[dict[str, str]] = []

    for raw_row in dataset:
        row = dict(raw_row)
        document = qasper_row_to_document(row)
        for question_record in iter_qasper_questions(row):
            evidence = evidence_paragraphs(question_record.get("answers"))
            if not evidence:
                continue
            if not match_evidence_source_ids(document, evidence):
                continue

            rows.append(
                {
                    "question": str(question_record["question"]).strip(),
                    "document_id": document.document_id,
                    "question_id": str(question_record["question_id"]),
                }
            )
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break

    if not rows:
        raise RuntimeError("No evaluable QASPER questions were found.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    count = build_questions(args.qasper, args.output, limit=args.limit)
    print(f"Wrote {count} QASPER evaluation questions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
