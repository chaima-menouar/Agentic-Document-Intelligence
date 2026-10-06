"""Controlled A/B/C evaluation on the real BGE + FAISS index.

This is a reproducible stress benchmark, not a claim of general model quality.
It measures how the three modes behave on grounded, recoverable-uncited, and
unsupported claims while using the same retrieval index and zero paid APIs.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.agent import AgenticVerifiedRAG
from app.rag import ClassicalRAG
from app.retrieval import SemanticRetriever
from app.verification import (
    CitationGroundingVerifier,
    VerifiedRAG,
    correct_verified_answer,
)


class ScriptedGenerator:
    """Deterministic answer generator for controlled comparison."""

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


def _rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 0.0


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _timed(callable_obj):
    started = time.perf_counter()
    result = callable_obj()
    return result, time.perf_counter() - started


def _pipelines(
    retriever: SemanticRetriever,
    response: str,
    *,
    max_rounds: int,
    additional_top_k: int,
):
    classical = ClassicalRAG(
        retriever=retriever,
        generator=ScriptedGenerator(response),
    )
    verifier = CitationGroundingVerifier()
    verified = VerifiedRAG(
        rag=classical,
        verifier=verifier,
    )
    agentic = AgenticVerifiedRAG(
        verified_rag=verified,
        retriever=retriever,
        verifier=verifier,
        max_rounds=max_rounds,
        additional_top_k=additional_top_k,
    )
    return classical, verified, agentic


def evaluate(
    index_dir: Path,
    output_path: Path,
    *,
    cases: int = 20,
    max_rounds: int = 2,
    additional_top_k: int = 3,
) -> dict:
    retriever = SemanticRetriever.load(index_dir)
    selected = _select_cases(retriever, cases)

    normal_records = []
    recoverable_records = []
    unsupported_records = []
    latency_a: list[float] = []
    latency_b: list[float] = []
    latency_c: list[float] = []

    unsupported_claim = (
        "The ZXQ917 banana-neutrino lattice achieved violet-pineapple "
        "coherence of 99 zeptounits."
    )

    for case_index, payload in enumerate(selected, start=1):
        document_id = payload["document_id"]
        claim = _target_claim(payload["text"])

        # Normal grounded case: first probe the real top-1 passage, then
        # generate a claim taken from that exact [S1] evidence. This isolates
        # verification behavior instead of accidentally testing retrieval miss.
        normal_question = claim
        probe_hits = retriever.search_many_scoped(
            [normal_question],
            [document_id],
            top_k=1,
        )[0]
        if not probe_hits:
            continue
        grounded_claim = _target_claim(probe_hits[0].text)
        classical, verified, agentic = _pipelines(
            retriever,
            f"{grounded_claim} [S1]",
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
        )
        a_result, a_time = _timed(
            lambda: classical.answer(
                normal_question,
                top_k=1,
                document_id=document_id,
            )
        )
        b_result, b_time = _timed(
            lambda: verified.answer(
                normal_question,
                top_k=1,
                document_id=document_id,
            )
        )
        c_result, c_time = _timed(
            lambda: agentic.answer(
                normal_question,
                top_k=1,
                document_id=document_id,
            )
        )
        latency_a.append(a_time)
        latency_b.append(b_time)
        latency_c.append(c_time)
        normal_records.append(
            {
                "case": case_index,
                "document_id": document_id,
                "mode_a_status": a_result.status,
                "mode_a_citations": len(a_result.citations),
                "mode_b_status": b_result.verification_status,
                "mode_c_status": c_result.status,
                "mode_c_rounds": c_result.rounds_used,
            }
        )

        # Recoverable stress: real corpus claim, deliberately emitted uncited.
        recoverable_question = "What evidence is stated in this document?"
        classical, verified, agentic = _pipelines(
            retriever,
            claim,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
        )
        a_result, a_time = _timed(
            lambda: classical.answer(
                recoverable_question,
                top_k=1,
                document_id=document_id,
            )
        )
        b_result, b_time = _timed(
            lambda: verified.answer(
                recoverable_question,
                top_k=1,
                document_id=document_id,
            )
        )
        b_corrected = correct_verified_answer(b_result)
        c_result, c_time = _timed(
            lambda: agentic.answer(
                recoverable_question,
                top_k=1,
                document_id=document_id,
            )
        )
        latency_a.append(a_time)
        latency_b.append(b_time)
        latency_c.append(c_time)
        recoverable_records.append(
            {
                "case": case_index,
                "document_id": document_id,
                "mode_a_status": a_result.status,
                "mode_b_status": b_result.verification_status,
                "mode_b_correction": b_corrected.correction_status,
                "mode_c_status": c_result.status,
                "mode_c_rounds": c_result.rounds_used,
                "mode_c_additional_chunks": c_result.additional_chunks_considered,
                "mode_c_recovered_claims": len(c_result.recovered_claim_ids),
            }
        )

        # Unsupported stress: deliberately nonsensical claim.
        classical, verified, agentic = _pipelines(
            retriever,
            unsupported_claim,
            max_rounds=max_rounds,
            additional_top_k=additional_top_k,
        )
        a_result, a_time = _timed(
            lambda: classical.answer(
                "What unusual result does this document report?",
                top_k=1,
                document_id=document_id,
            )
        )
        b_result, b_time = _timed(
            lambda: verified.answer(
                "What unusual result does this document report?",
                top_k=1,
                document_id=document_id,
            )
        )
        b_corrected = correct_verified_answer(b_result)
        c_result, c_time = _timed(
            lambda: agentic.answer(
                "What unusual result does this document report?",
                top_k=1,
                document_id=document_id,
            )
        )
        latency_a.append(a_time)
        latency_b.append(b_time)
        latency_c.append(c_time)
        unsupported_records.append(
            {
                "case": case_index,
                "document_id": document_id,
                "mode_a_status": a_result.status,
                "mode_b_status": b_result.verification_status,
                "mode_b_correction": b_corrected.correction_status,
                "mode_c_status": c_result.status,
                "mode_c_rounds": c_result.rounds_used,
                "mode_c_additional_chunks": c_result.additional_chunks_considered,
                "mode_c_unresolved_claims": len(c_result.unresolved_claim_ids),
            }
        )

    summary = {
        "benchmark": "controlled_real_index_abc_stress_evaluation",
        "note": (
            "Deterministic stress evaluation over real QASPER-indexed passages; "
            "not a general LLM quality benchmark."
        ),
        "cases_per_scenario": len(selected),
        "retriever_model": retriever.manifest["embedding_model"],
        "external_paid_api_cost": 0.0,
        "normal_grounded": {
            "mode_a_cited_answer_rate": _rate([
                row["mode_a_status"] == "answered"
                and row["mode_a_citations"] > 0
                for row in normal_records
            ]),
            "mode_b_verified_rate": _rate([
                row["mode_b_status"] == "verified"
                for row in normal_records
            ]),
            "mode_c_no_extra_round_rate": _rate([
                row["mode_c_status"] == "complete"
                and row["mode_c_rounds"] == 0
                for row in normal_records
            ]),
        },
        "recoverable_uncited": {
            "mode_a_uncited_output_rate": _rate([
                row["mode_a_status"] == "uncited_answer"
                for row in recoverable_records
            ]),
            "mode_b_detection_rate": _rate([
                row["mode_b_status"] != "verified"
                for row in recoverable_records
            ]),
            "mode_b_safe_abstention_rate": _rate([
                row["mode_b_correction"] == "insufficient_evidence"
                for row in recoverable_records
            ]),
            "mode_c_recovery_rate": _rate([
                row["mode_c_status"] == "complete"
                and row["mode_c_recovered_claims"] > 0
                for row in recoverable_records
            ]),
            "mode_c_average_rounds": _mean([
                row["mode_c_rounds"]
                for row in recoverable_records
            ]),
            "mode_c_average_additional_chunks": _mean([
                row["mode_c_additional_chunks"]
                for row in recoverable_records
            ]),
        },
        "unsupported_claim": {
            "mode_b_detection_rate": _rate([
                row["mode_b_status"] != "verified"
                for row in unsupported_records
            ]),
            "mode_b_safe_abstention_rate": _rate([
                row["mode_b_correction"] == "insufficient_evidence"
                for row in unsupported_records
            ]),
            "mode_c_safe_abstention_rate": _rate([
                row["mode_c_status"] == "insufficient_evidence"
                for row in unsupported_records
            ]),
            "mode_c_bound_respected_rate": _rate([
                row["mode_c_rounds"] <= max_rounds
                for row in unsupported_records
            ]),
            "mode_c_average_rounds": _mean([
                row["mode_c_rounds"]
                for row in unsupported_records
            ]),
        },
        "latency_seconds": {
            "mode_a_mean": _mean(latency_a),
            "mode_b_mean": _mean(latency_b),
            "mode_c_mean": _mean(latency_c),
        },
        "configuration": {
            "max_rounds": max_rounds,
            "additional_top_k": additional_top_k,
        },
        "records": {
            "normal_grounded": normal_records,
            "recoverable_uncited": recoverable_records,
            "unsupported_claim": unsupported_records,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Modes A/B/C.")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper-bge-small"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/abc_evaluation.json"),
    )
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--additional-top-k", type=int, default=3)
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
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
