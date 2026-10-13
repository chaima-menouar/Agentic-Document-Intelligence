"""Compare V1 fixed and V2 adaptive agent policies on controlled real-index cases."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.agent import AdaptiveAgenticVerifiedRAG, AgenticVerifiedRAG
from app.rag import ClassicalRAG
from app.retrieval import SemanticRetriever
from app.verification import CitationGroundingVerifier, VerifiedRAG


class ScriptedGenerator:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def _target_claim(text: str) -> str:
    normalized = " ".join(text.split())
    first = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0].strip()
    if len(first.split()) < 8:
        first = " ".join(normalized.split()[:30]).rstrip(".!?") + "."
    return first


def _select_cases(retriever: SemanticRetriever, count: int) -> list[dict]:
    selected: list[dict] = []
    seen_documents: set[str] = set()
    for payload in retriever.chunk_metadata:
        document_id = payload["document_id"]
        if document_id in seen_documents:
            continue
        text = payload.get("text", "")
        if len(text.split()) < 12:
            continue
        seen_documents.add(document_id)
        selected.append(payload)
        if len(selected) >= count:
            break
    if not selected:
        raise RuntimeError("No suitable evaluation chunks were found.")
    return selected


def _pipeline(retriever, response: str):
    classical = ClassicalRAG(
        retriever=retriever,
        generator=ScriptedGenerator(response),
    )
    verifier = CitationGroundingVerifier()
    verified = VerifiedRAG(rag=classical, verifier=verifier)
    return verified, verifier


def _mean(values):
    return statistics.fmean(values) if values else 0.0


def _rate(values):
    return sum(values) / len(values) if values else 0.0


def evaluate(
    index_dir: Path,
    output_path: Path,
    *,
    cases: int = 20,
    max_rounds: int = 3,
    additional_top_k: int = 3,
    adaptive_budget: int = 6,
) -> dict:
    retriever = SemanticRetriever.load(index_dir)
    selected = _select_cases(retriever, cases)

    recoverable_records = []
    unsupported_records = []

    unsupported_claim = (
        "The ZXQ917 banana-neutrino lattice achieved violet-pineapple "
        "coherence of 99 zeptounits."
    )

    for case_index, payload in enumerate(selected, start=1):
        document_id = payload["document_id"]
        claim = _target_claim(payload["text"])

        # Recoverable uncited claim from the real indexed document.
        verified, verifier = _pipeline(retriever, claim)
        fixed = AgenticVerifiedRAG(
            verified_rag=verified,
            retriever=retriever,
            verifier=verifier,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
        )
        adaptive = AdaptiveAgenticVerifiedRAG(
            verified_rag=verified,
            retriever=retriever,
            verifier=verifier,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
            max_total_additional_chunks=adaptive_budget,
        )
        question = "What evidence is stated in this document?"
        fixed_result = fixed.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
        adaptive_result = adaptive.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
        recoverable_records.append(
            {
                "case": case_index,
                "document_id": document_id,
                "fixed_status": fixed_result.status,
                "fixed_rounds": fixed_result.rounds_used,
                "fixed_chunks": fixed_result.additional_chunks_considered,
                "fixed_recovered": bool(fixed_result.recovered_claim_ids),
                "adaptive_status": adaptive_result.status,
                "adaptive_rounds": adaptive_result.rounds_used,
                "adaptive_chunks": adaptive_result.additional_chunks_considered,
                "adaptive_recovered": bool(adaptive_result.recovered_claim_ids),
                "adaptive_budget_exhausted": adaptive_result.budget_exhausted,
                "adaptive_early_stop": adaptive_result.early_stop_reason,
            }
        )

        # Truly unsupported synthetic claim.
        verified, verifier = _pipeline(retriever, unsupported_claim)
        fixed = AgenticVerifiedRAG(
            verified_rag=verified,
            retriever=retriever,
            verifier=verifier,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
        )
        adaptive = AdaptiveAgenticVerifiedRAG(
            verified_rag=verified,
            retriever=retriever,
            verifier=verifier,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
            max_total_additional_chunks=adaptive_budget,
        )
        question = "What unusual result does this document report?"
        fixed_result = fixed.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
        adaptive_result = adaptive.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
        unsupported_records.append(
            {
                "case": case_index,
                "document_id": document_id,
                "fixed_status": fixed_result.status,
                "fixed_rounds": fixed_result.rounds_used,
                "fixed_chunks": fixed_result.additional_chunks_considered,
                "adaptive_status": adaptive_result.status,
                "adaptive_rounds": adaptive_result.rounds_used,
                "adaptive_chunks": adaptive_result.additional_chunks_considered,
                "adaptive_budget_exhausted": adaptive_result.budget_exhausted,
                "adaptive_early_stop": adaptive_result.early_stop_reason,
                "adaptive_budget_respected": (
                    adaptive_result.additional_chunks_considered
                    <= adaptive_budget
                ),
            }
        )

    report = {
        "benchmark": "v1_fixed_vs_v2_adaptive_agent_policy",
        "note": (
            "Controlled deterministic stress evaluation over real BGE+FAISS "
            "QASPER passages; not a general LLM quality benchmark."
        ),
        "cases_per_scenario": len(selected),
        "configuration": {
            "max_rounds": max_rounds,
            "additional_top_k": additional_top_k,
            "adaptive_budget": adaptive_budget,
        },
        "recoverable_uncited": {
            "fixed_recovery_rate": _rate([
                row["fixed_status"] == "complete" and row["fixed_recovered"]
                for row in recoverable_records
            ]),
            "adaptive_recovery_rate": _rate([
                row["adaptive_status"] == "complete"
                and row["adaptive_recovered"]
                for row in recoverable_records
            ]),
            "fixed_average_rounds": _mean([
                row["fixed_rounds"] for row in recoverable_records
            ]),
            "adaptive_average_rounds": _mean([
                row["adaptive_rounds"] for row in recoverable_records
            ]),
            "fixed_average_chunks": _mean([
                row["fixed_chunks"] for row in recoverable_records
            ]),
            "adaptive_average_chunks": _mean([
                row["adaptive_chunks"] for row in recoverable_records
            ]),
        },
        "unsupported_claim": {
            "fixed_safe_abstention_rate": _rate([
                row["fixed_status"] == "insufficient_evidence"
                for row in unsupported_records
            ]),
            "adaptive_safe_abstention_rate": _rate([
                row["adaptive_status"] == "insufficient_evidence"
                for row in unsupported_records
            ]),
            "fixed_average_rounds": _mean([
                row["fixed_rounds"] for row in unsupported_records
            ]),
            "adaptive_average_rounds": _mean([
                row["adaptive_rounds"] for row in unsupported_records
            ]),
            "fixed_average_chunks": _mean([
                row["fixed_chunks"] for row in unsupported_records
            ]),
            "adaptive_average_chunks": _mean([
                row["adaptive_chunks"] for row in unsupported_records
            ]),
            "adaptive_budget_respected_rate": _rate([
                row["adaptive_budget_respected"]
                for row in unsupported_records
            ]),
            "adaptive_early_stop_rate": _rate([
                bool(row["adaptive_early_stop"])
                for row in unsupported_records
            ]),
        },
        "records": {
            "recoverable_uncited": recoverable_records,
            "unsupported_claim": unsupported_records,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare fixed vs adaptive agent policies."
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper-bge-small"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/v2_agent_policy.json"),
    )
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--additional-top-k", type=int, default=3)
    parser.add_argument("--adaptive-budget", type=int, default=6)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cases <= 0:
        raise SystemExit("--cases must be greater than zero.")
    report = evaluate(
        args.index,
        args.output,
        cases=args.cases,
        max_rounds=args.max_rounds,
        additional_top_k=args.additional_top_k,
        adaptive_budget=args.adaptive_budget,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
