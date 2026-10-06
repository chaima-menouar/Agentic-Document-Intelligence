"""Tests for Mode B Verified RAG."""

from app.models import AnswerCitation, RAGAnswer
from app.verification import CitationGroundingVerifier, VerifiedRAG


class FakeRAG:
    def __init__(self, answer: RAGAnswer) -> None:
        self.result = answer

    def answer(self, question: str, *, top_k: int = 5, document_id=None):
        return self.result


def _citation() -> AnswerCitation:
    return AnswerCitation(
        label="S1",
        dataset="qasper",
        document_id="doc-1",
        chunk_id="chunk-1",
        source_id="source-1",
        score=0.9,
        text="The proposed model improves retrieval accuracy on the benchmark.",
    )


def test_verified_rag_reports_verified_answer() -> None:
    base = RAGAnswer(
        question="What improved?",
        answer="The proposed model improves retrieval accuracy on the benchmark [S1].",
        status="answered",
        citations=[_citation()],
        retrieved_chunks=3,
        used_citation_labels=["S1"],
    )
    pipeline = VerifiedRAG(
        rag=FakeRAG(base),
        verifier=CitationGroundingVerifier(),
    )

    result = pipeline.answer("What improved?")

    assert result.verification_status == "verified"
    assert len(result.claims) == 1
    assert result.verifications[0].status == "supported"


def test_verified_rag_keeps_insufficient_evidence_status() -> None:
    base = RAGAnswer(
        question="Unknown?",
        answer="I do not have enough evidence.",
        status="insufficient_evidence",
        citations=[],
        retrieved_chunks=0,
        used_citation_labels=[],
    )
    pipeline = VerifiedRAG(
        rag=FakeRAG(base),
        verifier=CitationGroundingVerifier(),
    )

    result = pipeline.answer("Unknown?")

    assert result.verification_status == "insufficient_evidence"
    assert result.claims == []
    assert result.verifications == []
