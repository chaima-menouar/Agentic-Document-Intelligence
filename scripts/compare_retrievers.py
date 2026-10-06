"""Compare two retrieval evaluation reports and select the stronger baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare_reports(
    baseline_path: Path,
    candidate_path: Path,
    output_path: Path,
    *,
    primary_metric: str = "recall@5",
) -> dict:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]

    if primary_metric not in baseline_metrics or primary_metric not in candidate_metrics:
        raise ValueError(f"Primary metric {primary_metric!r} is missing from a report.")

    ordered_metrics = ["recall@1", "recall@3", "recall@5", "recall@10", "recall@20", "mrr@20"]
    deltas = {
        metric: candidate_metrics[metric] - baseline_metrics[metric]
        for metric in ordered_metrics
        if metric in baseline_metrics and metric in candidate_metrics
    }

    if candidate_metrics[primary_metric] > baseline_metrics[primary_metric]:
        winner = "candidate"
    elif candidate_metrics[primary_metric] < baseline_metrics[primary_metric]:
        winner = "baseline"
    else:
        # Stable tie-breaker: Recall@10, then MRR@20.
        tie_breakers = ["recall@10", "mrr@20"]
        winner = "tie"
        for metric in tie_breakers:
            if metric not in baseline_metrics or metric not in candidate_metrics:
                continue
            if candidate_metrics[metric] > baseline_metrics[metric]:
                winner = "candidate"
                break
            if candidate_metrics[metric] < baseline_metrics[metric]:
                winner = "baseline"
                break

    report = {
        "primary_metric": primary_metric,
        "winner": winner,
        "baseline": {
            "model": baseline["index_manifest"]["embedding_model"],
            "query_prefix": baseline["index_manifest"].get("query_prefix", ""),
            "metrics": baseline_metrics,
        },
        "candidate": {
            "model": candidate["index_manifest"]["embedding_model"],
            "query_prefix": candidate["index_manifest"].get("query_prefix", ""),
            "metrics": candidate_metrics,
        },
        "candidate_minus_baseline": deltas,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare retrieval evaluation reports.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--primary-metric", default="recall@5")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = compare_reports(
        args.baseline,
        args.candidate,
        args.output,
        primary_metric=args.primary_metric,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
