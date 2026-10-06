"""Tests for A/B/C evaluation metrics."""

from app.evaluation import (
    aggregate_mode_metrics,
    evaluate_agentic_answer,
    evaluate_classical_answer,
    evaluate_verified_answer,
)
from app.models import (
    AgenticRAGAnswer,
    AnswerCitation,
    ClaimVerification,
    ExtractedClaim,
    RAGAnswer,
    VerifiedRAGAnswer,
)


def _citation(label: str = "S1") -> AnswerCitation:
    return AnswerCitation(
        label=label,
        dataset="test",
        document_id="doc-1",
        chunk_id=f"chunk-{label}",
        source_id=f"source-{label}",
        score=0.9,
        text="Grounded evidence.",
    )


def _claim() -> ExtractedClaim:
    return ExtractedClaim(
        claim_id="claim_001",
        text="Grounded claim.",
        citation_labels=["S1"],
    )


def _verification(status: str, score: float) -> ClaimVerification:
    return ClaimVerification(
        claim_id="claim_001",
        claim_text="Grounded claim.",
        citation_labels=["S1"],
        evidence_labels=["S1"],
        status=status,
        support_score=score,
        reason="test",
    )


def test_classical_metrics_track_citations() -> None:
    answer = RAGAnswer(
        question="Q?",
        answer="A [S1].",
        status="answered",
        citations=[_citation()],
        retrieved_chunks=5,
        used_citation_labels=["S1"],
    )
    metrics = evaluate_classical_answer(answer)
    assert metrics["answered"] == 1.0
    assert metrics["has_citation"] == 1.0
    assert metrics["citation_count"] == 1.0


def test_verified_metrics_track_supported_claim_rate() -> None:
    answer = VerifiedRAGAnswer(
        question="Q?",
        answer="A [S1].",
        base_status="answered",
        verification_status="verified",
        claims=[_claim()],
        verifications=[_verification("supported", 0.8)],
        citations=[_citation()],
        retrieved_chunks=5,
    )
    metrics = evaluate_verified_answer(answer)
    assert metrics["verified_answer"] == 1.0
    assert metrics["supported_claim_rate"] == 1.0
    assert metrics["mean_support_score"] == 0.8


def test_agentic_metrics_track_recovery() -> None:
    answer = AgenticRAGAnswer(
        question="Q?",
        initial_answer="A.",
        final_answer="A [A1C1S1].",
        status="complete",
        initial_verification_status="unsupported",
        final_verification_status="verified",
        correction_status="full_answer",
        rounds_used=1,
        additional_chunks_considered=2,
        recovered_claim_ids=["claim_001"],
        unresolved_claim_ids=[],
        steps=[],
        claims=[_claim()],
        verifications=[_verification("supported", 0.9)],
        citations=[_citation("A1C1S1")],
    )
    metrics = evaluate_agentic_answer(answer)
    assert metrics["complete_answer"] == 1.0
    assert metrics["recovery_rate"] == 1.0
    assert metrics["rounds_used"] == 1.0


def test_aggregate_mode_metrics_averages_values() -> None:
    summary = aggregate_mode_metrics(
        [
            {"answered": 1.0, "citation_count": 2.0},
            {"answered": 0.0, "citation_count": 0.0},
        ]
    )
    assert summary["examples"] == 2.0
    assert summary["answered"] == 0.5
    assert summary["citation_count"] == 1.0
