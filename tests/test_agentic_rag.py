"""Tests for bounded Mode C agentic re-retrieval."""

from app.agent import AgenticVerifiedRAG
from app.models import (
    ClaimVerification,
    ExtractedClaim,
    VerifiedRAGAnswer,
)
from app.retrieval import RetrievalHit
from app.verification import CitationGroundingVerifier


class FakeVerifiedRAG:
    def __init__(self, result: VerifiedRAGAnswer) -> None:
        self.result = result
        self.calls = []

    def answer(self, question: str, *, top_k: int = 5, document_id=None):
        self.calls.append((question, top_k, document_id))
        return self.result


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.queries = []

    def search(self, query: str, *, top_k: int = 5):
        self.queries.append(("global", query, top_k))
        return self.hits[:top_k]

    def search_many_scoped(self, queries, document_ids, *, top_k: int = 5):
        self.queries.append(("scoped", queries[0], top_k))
        return [self.hits[:top_k]]


def _hit(text: str) -> RetrievalHit:
    return RetrievalHit(
        rank=1,
        score=0.95,
        dataset="qasper",
        document_id="doc-1",
        chunk_id="chunk-1",
        source_id="source-1",
        text=text,
        page_number=None,
        section="Results",
        metadata={},
    )


def _unsupported_answer() -> VerifiedRAGAnswer:
    return VerifiedRAGAnswer(
        question="What happened?",
        answer="The system reduces latency significantly.",
        base_status="uncited_answer",
        verification_status="unsupported",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="The system reduces latency significantly.",
                citation_labels=[],
            )
        ],
        verifications=[
            ClaimVerification(
                claim_id="claim_001",
                claim_text="The system reduces latency significantly.",
                citation_labels=[],
                evidence_labels=[],
                status="unsupported",
                support_score=0.0,
                reason="No citation.",
            )
        ],
        citations=[],
        retrieved_chunks=1,
    )


def test_agentic_retrieval_recovers_unsupported_claim() -> None:
    initial = _unsupported_answer()
    retriever = FakeRetriever([
        _hit("The system reduces latency significantly in the experiment.")
    ])
    agent = AgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(initial),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=2,
        additional_top_k=1,
    )

    result = agent.answer("What happened?", document_id="doc-1")

    assert result.status == "complete"
    assert result.final_verification_status == "verified"
    assert result.recovered_claim_ids == ["claim_001"]
    assert result.unresolved_claim_ids == []
    assert result.rounds_used == 1
    assert "[A1C1S1]" in result.final_answer
    assert result.steps[0].resolved is True


def test_agentic_retrieval_respects_round_bound() -> None:
    initial = _unsupported_answer()
    retriever = FakeRetriever([
        _hit("Completely unrelated evidence about another topic.")
    ])
    agent = AgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(initial),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=2,
        additional_top_k=1,
    )

    result = agent.answer("What happened?")

    assert result.rounds_used == 2
    assert result.status == "insufficient_evidence"
    assert result.unresolved_claim_ids == ["claim_001"]
    assert len(result.steps) == 2


def test_agentic_mode_skips_extra_retrieval_when_already_verified() -> None:
    verified = VerifiedRAGAnswer(
        question="Q?",
        answer="A supported claim [S1].",
        base_status="answered",
        verification_status="verified",
        claims=[
            ExtractedClaim(
                claim_id="claim_001",
                text="A supported claim.",
                citation_labels=["S1"],
            )
        ],
        verifications=[
            ClaimVerification(
                claim_id="claim_001",
                claim_text="A supported claim.",
                citation_labels=["S1"],
                evidence_labels=["S1"],
                status="supported",
                support_score=1.0,
                reason="supported",
            )
        ],
        citations=[],
        retrieved_chunks=1,
    )
    retriever = FakeRetriever([])
    agent = AgenticVerifiedRAG(
        verified_rag=FakeVerifiedRAG(verified),
        retriever=retriever,
        verifier=CitationGroundingVerifier(),
        max_rounds=2,
        additional_top_k=1,
    )

    result = agent.answer("Q?")

    assert result.status == "complete"
    assert result.rounds_used == 0
    assert result.steps == []
    assert retriever.queries == []
