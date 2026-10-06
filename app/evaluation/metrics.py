"""Dependency-free metrics for Mode A/B/C comparison."""

from __future__ import annotations

from collections.abc import Iterable
from statistics import mean

from app.models import AgenticRAGAnswer, RAGAnswer, VerifiedRAGAnswer


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_classical_answer(answer: RAGAnswer) -> dict[str, float]:
    """Summarize one Mode A answer."""
    answered = answer.status == "answered"
    return {
        "answered": float(answered),
        "abstained": float(answer.status == "insufficient_evidence"),
        "uncited_answer": float(answer.status == "uncited_answer"),
        "citation_count": float(len(answer.citations)),
        "has_citation": float(bool(answer.citations)),
        "retrieved_chunks": float(answer.retrieved_chunks),
    }


def evaluate_verified_answer(answer: VerifiedRAGAnswer) -> dict[str, float]:
    """Summarize one Mode B answer at claim level."""
    statuses = [item.status for item in answer.verifications]
    scores = [item.support_score for item in answer.verifications]
    total = len(statuses)
    supported = statuses.count("supported")
    review = statuses.count("needs_review")
    unsupported = statuses.count("unsupported")

    return {
        "answered": float(answer.base_status in {"answered", "uncited_answer"}),
        "abstained": float(answer.base_status == "insufficient_evidence"),
        "verified_answer": float(answer.verification_status == "verified"),
        "claim_count": float(total),
        "supported_claim_rate": _ratio(supported, total),
        "needs_review_claim_rate": _ratio(review, total),
        "unsupported_claim_rate": _ratio(unsupported, total),
        "mean_support_score": mean(scores) if scores else 0.0,
        "citation_count": float(len(answer.citations)),
        "has_citation": float(bool(answer.citations)),
        "retrieved_chunks": float(answer.retrieved_chunks),
    }


def evaluate_agentic_answer(answer: AgenticRAGAnswer) -> dict[str, float]:
    """Summarize one Mode C answer including bounded recovery behavior."""
    statuses = [item.status for item in answer.verifications]
    scores = [item.support_score for item in answer.verifications]
    total = len(statuses)
    supported = statuses.count("supported")
    unresolved = len(answer.unresolved_claim_ids)
    initial_unresolved = unresolved + len(answer.recovered_claim_ids)

    return {
        "complete_answer": float(answer.status == "complete"),
        "partial_answer": float(answer.status == "partial"),
        "abstained": float(answer.status == "insufficient_evidence"),
        "verified_answer": float(answer.final_verification_status == "verified"),
        "claim_count": float(total),
        "supported_claim_rate": _ratio(supported, total),
        "mean_support_score": mean(scores) if scores else 0.0,
        "recovery_rate": _ratio(len(answer.recovered_claim_ids), initial_unresolved),
        "rounds_used": float(answer.rounds_used),
        "additional_chunks_considered": float(answer.additional_chunks_considered),
        "citation_count": float(len(answer.citations)),
        "has_citation": float(bool(answer.citations)),
    }


def aggregate_mode_metrics(
    records: Iterable[dict[str, float]],
) -> dict[str, float]:
    """Average numeric metrics across evaluation examples."""
    rows = list(records)
    if not rows:
        return {"examples": 0.0}

    keys = sorted({key for row in rows for key in row})
    summary: dict[str, float] = {"examples": float(len(rows))}
    for key in keys:
        values = [float(row[key]) for row in rows if key in row]
        if values:
            summary[key] = mean(values)
    return summary
