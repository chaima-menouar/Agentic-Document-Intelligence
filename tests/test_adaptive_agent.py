"""Tests for the V2 adaptive agent policy and budgeted retrieval loop."""

from app.agent import AdaptiveAgenticVerifiedRAG, AdaptiveRetrievalPolicy
from app.models import (
    AnswerCitation,
    ClaimVerification,
    ExtractedClaim,
    VerifiedRAGAnswer,
)
from app.retrieval import RetrievalHit
from app.verification import CitationGroundingVerifier


def _claim(text="The system reduces latency significantly.", labels=None):
    return ExtractedClaim(
        claim_id="claim_001",
        text=text,
        citation_labels=[] if labels is None else list(labels),
    )


def _verification(
    *,
    status="unsupported",
    score=0.0,
    reason="The claim has no citation label.",
    labels=None,
):
    return ClaimVerification(
        claim_id="claim_001",
        claim_text="The system reduces latency significantly.",
        citation_labels=[] if labels is None else list(labels),
        evidence_labels=[] if labels is None else list(labels),
        status=status,
        support_score=score,
        reason=reason,
    )


def _hit(chunk_id, text, score=0.9):
    return RetrievalHit(
        rank=1,
        score=score,
        dataset="qasper",
        document_id="doc-1",
        chunk_id=chunk_id,
        source_id=f"src-{chunk_id}",
        text=text,
        page_number=1,
        section="Results",
        metadata={},
    )


def _citation(chunk_id, text):
    return AnswerCitation(
        label="S1",
        dataset="qasper",
        document_id="doc-1",
        chunk_id=chunk_id,
        source_id=f"src-{chunk_id}",
        score=0.9,
        page_number=1,
        section="Results",
        text=text,
    )


class FakeVerifiedRAG:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def answer(self, question, *, top_k=5, document_id=None):
        self.calls.append((question, top_k, document_id))
        return self.result


class FakeRetriever:
    def __init__(self, hits):
        self.hits = list(hits)
        self.calls = []

    def search(self, query, *, top_k=5):
        self.calls.append(("global", query, top_k))
        return self.hits[:top_k]

    def search_many_scoped(self, queries, document_ids, *, top_k=5):
        self.calls.append(("scoped", queries[0], top_k))
        return [self.hits[:top_k]]


def _unsupported_answer(*, citations=None, labels=None, reason=None):
    claim = _claim(labels=labels)
    verification = _verification(
        labels=labels,
        reason=reason or (
            "The claim has no citation label."
            if not labels
            else "The cited evidence has weak lexical grounding for this claim."
        ),
    )
    return VerifiedRAGAnswer(
        question="What happened?",
        answer="The system reduces latency significantly.",
        base_status="answered" if citations else "uncited_answer",
        verification_status="unsupported",
        claims=[claim],
        verifications=[verification],
        citations=list(citations or []),
        retrieved_chunks=len(citations or []) or 1,
    )


def test_policy_targets_missing_citation() -> None:
    policy = AdaptiveRetrievalPolicy()
    decision = policy.decide(
        question="What happened?",
        claim=_claim(),
        verification=_verification(),
        round_index=1,
    )

    assert decision.action == "recover_missing_citation"
    assert decision.failure_reason == "missing_citation"
    assert decision.query == "The system reduces latency significantly."
    assert decision.stop is False


def test_policy_detects_answer_type_mismatch() -> None:
    policy = AdaptiveRetrievalPolicy()
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="The program launched recently.",
        citation_labels=[],
    )
    verification = ClaimVerification(
        claim_id="claim_001",
        claim_text=claim.text,
        citation_labels=[],
        evidence_labels=[],
        status="unsupported",
        support_score=0.0,
        reason="No citation.",
    )

    decision = policy.decide(
        question="What year was the program launched?",
        claim=claim,
        verification=verification,
        round_index=1,
    )

    assert decision.action == "answer_type_search"
    assert decision.failure_reason == "answer_type_mismatch"
    assert "year" in decision.query.lower()


def test_policy_strengthens_needs_review_claim() -> None:
    policy = AdaptiveRetrievalPolicy()
    verification = _verification(
        status="needs_review",
        score=0.4,
        reason="The citation is valid, but grounding is partial.",
        labels=["S1"],
    )

    decision = policy.decide(
        question="What happened?",
        claim=_claim(labels=["S1"]),
        verification=verification,
        round_index=1,
    )

    assert decision.action == "strengthen_weak_evidence"
    assert decision.failure_reason == "weak_evidence"


def test_adaptive_agent_stops_when_retrieval_adds_no_new_chunk() -> None:
    existing_text = "Unrelated evidence about another topic."
    initial = _unsupported_answer(
        citations=[_citation("chunk-1", existing_text)],
        labels=["S1"],
    )
    retriever = FakeRetriever([_hit("chunk-1", existing_text)])
    agent = AdaptiveAgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(initial),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=3,
        additional_top_k=1,
        max_total_additional_chunks=5,
    )

    result = agent.answer("What happened?", document_id="doc-1")

    assert result.status == "insufficient_evidence"
    assert result.early_stop_reason == "no_new_evidence"
    assert len(retriever.calls) == 1
    assert result.steps[0].new_chunks == 0
    assert result.steps[0].stopped_early is True


def test_adaptive_agent_respects_strict_chunk_budget() -> None:
    initial = _unsupported_answer()
    retriever = FakeRetriever([
        _hit("c1", "Unrelated evidence one."),
        _hit("c2", "Unrelated evidence two."),
        _hit("c3", "Unrelated evidence three."),
        _hit("c4", "Unrelated evidence four."),
    ])
    agent = AdaptiveAgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(initial),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=3,
        additional_top_k=5,
        max_total_additional_chunks=2,
    )

    result = agent.answer("What happened?")

    assert result.additional_chunks_considered == 2
    assert result.retrieval_budget == 2
    assert result.budget_exhausted is True
    assert retriever.calls[0][2] == 2


def test_adaptive_agent_recovers_supported_claim() -> None:
    initial = _unsupported_answer()
    retriever = FakeRetriever([
        _hit(
            "support",
            "The system reduces latency significantly in the experiment.",
        )
    ])
    agent = AdaptiveAgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(initial),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=3,
        additional_top_k=1,
        max_total_additional_chunks=5,
    )

    result = agent.answer("What happened?", document_id="doc-1")

    assert result.status == "complete"
    assert result.final_verification_status == "verified"
    assert result.recovered_claim_ids == ["claim_001"]
    assert result.steps[0].action == "recover_missing_citation"
    assert result.steps[0].support_improvement > 0
    assert result.steps[0].new_chunks == 1
