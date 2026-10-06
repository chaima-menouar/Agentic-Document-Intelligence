"""Tests for conservative partial-answer correction."""

from app.models import (
    AnswerCitation,
    ClaimVerification,
    ExtractedClaim,
    VerifiedRAGAnswer,
)
from app.verification import CorrectedVerifiedRAG, correct_verified_answer


def _citation(label: str) -> AnswerCitation:
    return AnswerCitation(
        label=label,
        dataset="qasper",
        document_id="doc-1",
        chunk_id=f"chunk-{label}",
        source_id=f"source-{label}",
        score=0.9,
        text=f"Evidence for {label}.",
    )


def _verification(claim_id: str, status: str, score: float) -> ClaimVerification:
    return ClaimVerification(
        claim_id=claim_id,
        claim_text=f"Claim text for {claim_id}.",
        citation_labels=["S1"],
        evidence_labels=["S1"],
        status=status,
        support_score=score,
        reason="test",
    )


def test_corrector_returns_full_answer_when_all_claims_supported() -> None:
    verified = VerifiedRAGAnswer(
        question="Q?",
        answer="Supported statement [S1].",
        base_status="answered",
        verification_status="verified",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="Supported statement.",
                citation_labels=["S1"],
            )
        ],
        verifications=[_verification("claim_001", "supported", 1.0)],
        citations=[_citation("S1")],
        retrieved_chunks=3,
    )

    corrected = correct_verified_answer(verified)

    assert corrected.correction_status == "full_answer"
    assert corrected.final_answer == verified.answer
    assert corrected.removed_claim_ids == []


def test_corrector_returns_partial_answer_without_unsupported_claims() -> None:
    verified = VerifiedRAGAnswer(
        question="Q?",
        answer="Supported fact [S1]. Unsupported fact [S2].",
        base_status="answered",
        verification_status="partially_supported",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="Supported fact.",
                citation_labels=["S1"],
            ),
            ExtractedClaim(
                claim_id="claim_002",
                text="Unsupported fact.",
                citation_labels=["S2"],
            ),
        ],
        verifications=[
            _verification("claim_001", "supported", 1.0),
            ClaimVerification(
                claim_id="claim_002",
                claim_text="Unsupported fact.",
                citation_labels=["S2"],
                evidence_labels=["S2"],
                status="unsupported",
                support_score=0.1,
                reason="weak evidence",
            ),
        ],
        citations=[_citation("S1"), _citation("S2")],
        retrieved_chunks=5,
    )

    corrected = correct_verified_answer(verified)

    assert corrected.correction_status == "partial_answer"
    assert "Supported fact." in corrected.final_answer
    assert "Unsupported fact" not in corrected.final_answer
    assert corrected.kept_claim_ids == ["claim_001"]
    assert corrected.removed_claim_ids == ["claim_002"]
    assert [citation.label for citation in corrected.citations] == ["S1"]


def test_corrector_abstains_when_nothing_is_supported() -> None:
    verified = VerifiedRAGAnswer(
        question="Q?",
        answer="Weak statement [S1].",
        base_status="answered",
        verification_status="unsupported",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="Weak statement.",
                citation_labels=["S1"],
            )
        ],
        verifications=[_verification("claim_001", "unsupported", 0.0)],
        citations=[_citation("S1")],
        retrieved_chunks=2,
    )

    corrected = correct_verified_answer(verified)

    assert corrected.correction_status == "insufficient_evidence"
    assert corrected.citations == []
    assert corrected.removed_claim_ids == ["claim_001"]


class FakeVerifiedRAG:
    def __init__(self, result: VerifiedRAGAnswer) -> None:
        self.result = result

    def answer(self, question: str, *, top_k: int = 5, document_id=None):
        return self.result


def test_corrected_verified_rag_wraps_verified_pipeline() -> None:
    verified = VerifiedRAGAnswer(
        question="Q?",
        answer="Supported statement [S1].",
        base_status="answered",
        verification_status="verified",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="Supported statement.",
                citation_labels=["S1"],
            )
        ],
        verifications=[_verification("claim_001", "supported", 1.0)],
        citations=[_citation("S1")],
        retrieved_chunks=1,
    )

    pipeline = CorrectedVerifiedRAG(verified_rag=FakeVerifiedRAG(verified))
    result = pipeline.answer("Q?")

    assert result.correction_status == "full_answer"
