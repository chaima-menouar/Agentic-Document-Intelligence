"""Tests for the offline claim-grounding verifier."""

from app.models import AnswerCitation, ExtractedClaim
from app.verification import CitationGroundingVerifier, lexical_support_score


def _citation(label: str, text: str) -> AnswerCitation:
    return AnswerCitation(
        label=label,
        dataset="qasper",
        document_id="doc-1",
        chunk_id=f"chunk-{label}",
        source_id=f"source-{label}",
        score=0.9,
        text=text,
    )


def test_lexical_support_score_is_high_for_extractively_grounded_claim() -> None:
    score = lexical_support_score(
        "The model improves retrieval accuracy.",
        "The proposed model improves retrieval accuracy on the benchmark.",
    )
    assert score >= 0.75


def test_verifier_marks_supported_claim() -> None:
    verifier = CitationGroundingVerifier()
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="The model improves retrieval accuracy.",
        citation_labels=["S1"],
    )

    result = verifier.verify(
        [claim],
        [_citation("S1", "The model improves retrieval accuracy on the benchmark.")],
    )[0]

    assert result.status == "supported"
    assert result.evidence_labels == ["S1"]
    assert result.support_score >= 0.55


def test_verifier_marks_uncited_claim_unsupported() -> None:
    verifier = CitationGroundingVerifier()
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="The model improves retrieval accuracy.",
        citation_labels=[],
    )

    result = verifier.verify([claim], [])[0]

    assert result.status == "unsupported"
    assert result.support_score == 0.0


def test_verifier_marks_partial_overlap_for_review() -> None:
    verifier = CitationGroundingVerifier(
        supported_threshold=0.8,
        review_threshold=0.2,
    )
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="The system reduces energy and improves latency substantially.",
        citation_labels=["S1"],
    )

    result = verifier.verify(
        [claim],
        [_citation("S1", "The system improves latency in the experiment.")],
    )[0]

    assert result.status == "needs_review"
