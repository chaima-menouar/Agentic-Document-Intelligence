"""Tests for the V2 semantic/NLI citation verifier."""

from app.models import AnswerCitation, ExtractedClaim
from app.verification import SemanticCitationGroundingVerifier


class FakeScorer:
    def __init__(self, score: float):
        self.value = score
        self.calls = []

    def score(self, premise: str, hypothesis: str) -> float:
        self.calls.append((premise, hypothesis))
        return self.value


class FailingScorer:
    def score(self, premise: str, hypothesis: str) -> float:
        raise RuntimeError("model unavailable")


def _citation(text: str, label: str = "S1") -> AnswerCitation:
    return AnswerCitation(
        label=label,
        dataset="uploaded_pdf",
        document_id="doc-1",
        chunk_id="chunk-1",
        source_id="source-1",
        score=0.91,
        page_number=1,
        section=None,
        text=text,
    )


def _claim(text: str, labels=None) -> ExtractedClaim:
    return ExtractedClaim(
        claim_id="claim_001",
        text=text,
        citation_labels=list(["S1"] if labels is None else labels),
    )


def test_semantic_verifier_supports_paraphrase_with_high_entailment() -> None:
    scorer = FakeScorer(0.91)
    verifier = SemanticCitationGroundingVerifier(scorer=scorer)

    result = verifier.verify(
        [_claim("The experiment reduced latency.")],
        [_citation("The experiment made responses substantially faster.")],
    )[0]

    assert result.status == "supported"
    assert result.verifier_method == "semantic_nli"
    assert result.semantic_entailment_score == 0.91
    assert result.support_score == 0.91
    assert len(scorer.calls) == 1


def test_semantic_verifier_marks_mid_confidence_for_review() -> None:
    verifier = SemanticCitationGroundingVerifier(scorer=FakeScorer(0.55))

    result = verifier.verify(
        [_claim("The method improves performance.")],
        [_citation("The method was evaluated on several tasks.")],
    )[0]

    assert result.status == "needs_review"
    assert result.semantic_entailment_score == 0.55


def test_semantic_verifier_rejects_low_entailment() -> None:
    verifier = SemanticCitationGroundingVerifier(scorer=FakeScorer(0.12))

    result = verifier.verify(
        [_claim("The model improved accuracy.")],
        [_citation("The model did not improve accuracy.")],
    )[0]

    assert result.status == "unsupported"
    assert result.semantic_entailment_score == 0.12


def test_semantic_verifier_requires_a_real_citation_before_scoring() -> None:
    scorer = FakeScorer(0.99)
    verifier = SemanticCitationGroundingVerifier(scorer=scorer)

    result = verifier.verify(
        [_claim("A claim without evidence.", labels=[])],
        [_citation("Some evidence.")],
    )[0]

    assert result.status == "unsupported"
    assert result.support_score == 0.0
    assert scorer.calls == []


def test_semantic_verifier_rejects_unknown_citation_label() -> None:
    scorer = FakeScorer(0.99)
    verifier = SemanticCitationGroundingVerifier(scorer=scorer)

    result = verifier.verify(
        [_claim("A claim.", labels=["S9"])],
        [_citation("Some evidence.", label="S1")],
    )[0]

    assert result.status == "unsupported"
    assert result.evidence_labels == []
    assert scorer.calls == []


def test_semantic_verifier_falls_back_to_lexical_on_model_error() -> None:
    verifier = SemanticCitationGroundingVerifier(
        scorer=FailingScorer(),
        fallback_on_error=True,
    )

    result = verifier.verify(
        [_claim("The system reduces latency significantly.")],
        [_citation("The system reduces latency significantly in the experiment.")],
    )[0]

    assert result.status == "supported"
    assert result.verifier_method == "lexical_fallback"
    assert result.lexical_support_score == 1.0
    assert "Semantic verifier unavailable" in result.reason
