"""Apply Task 7 correction to a real Mode B smoke report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.models import VerifiedRAGAnswer
from app.verification import correct_verified_answer


def correct_report(input_path: Path, output_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    verified = VerifiedRAGAnswer.model_validate(payload["result"])
    corrected = correct_verified_answer(verified)

    if corrected.correction_status not in {
        "full_answer",
        "partial_answer",
        "insufficient_evidence",
    }:
        raise RuntimeError("Unexpected correction status.")

    report = {
        "mode": "verified_rag_with_correction",
        "source_mode_b_report": input_path.name,
        "result": corrected.model_dump(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Correct a Mode B smoke report.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = correct_report(args.input, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
