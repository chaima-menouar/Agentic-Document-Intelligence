"""Tests for retriever comparison logic."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_retrievers import compare_reports


def _write_report(path: Path, model: str, recall5: float, recall10: float) -> None:
    path.write_text(
        json.dumps(
            {
                "metrics": {
                    "recall@1": 0.1,
                    "recall@3": 0.2,
                    "recall@5": recall5,
                    "recall@10": recall10,
                    "recall@20": 0.9,
                    "mrr@20": 0.3,
                },
                "index_manifest": {
                    "embedding_model": model,
                    "query_prefix": "",
                },
            }
        ),
        encoding="utf-8",
    )


def test_candidate_wins_on_primary_metric(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    output = tmp_path / "comparison.json"
    _write_report(baseline, "mini", 0.50, 0.70)
    _write_report(candidate, "bge", 0.60, 0.72)

    report = compare_reports(baseline, candidate, output)

    assert report["winner"] == "candidate"
    assert report["candidate_minus_baseline"]["recall@5"] == 0.10
