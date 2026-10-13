"""Tests for Mode A classical RAG."""

from __future__ import annotations

from app.rag import ClassicalRAG, build_rag_prompt
from app.retrieval import RetrievalHit


def _hit(rank: int, chunk_id: str, text: str) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        score=0.9 - rank * 0.01,
        dataset="qasper",
        document_id="doc-1",
        chunk_id=chunk_id,
        source_id=f"src-{rank}",
        text=text,
        page_number=None,
        section="Results",
        metadata={},
    )


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.scoped_calls = []

    def search(self, query: str, *, top_k: int = 5):
        return self.hits[:top_k]

    def search_many_scoped(self, queries, document_ids, *, top_k: int = 5):
        self.scoped_calls.append((queries, document_ids, top_k))
        return [self.hits[:top_k]]


class FakeGenerator:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def test_prompt_contains_numbered_evidence() -> None:
    prompt = build_rag_prompt(
        "What happened?",
        [_hit(1, "c1", "First evidence."), _hit(2, "c2", "Second evidence.")],
    )
    assert "[S1]" in prompt
    assert "[S2]" in prompt
    assert "ONLY the evidence" in prompt


def test_classical_rag_maps_valid_citations() -> None:
    retriever = FakeRetriever([
        _hit(1, "c1", "Evidence one."),
        _hit(2, "c2", "Evidence two."),
    ])
    generator = FakeGenerator("The finding is supported by the study [S2].")
    rag = ClassicalRAG(retriever=retriever, generator=generator)

    result = rag.answer("What is the finding?", top_k=2)

    assert result.status == "answered"
    assert result.used_citation_labels == ["S2"]
    assert result.citations[0].chunk_id == "c2"
    assert result.retrieved_chunks == 2


def test_classical_rag_document_scope() -> None:
    retriever = FakeRetriever([_hit(1, "c1", "Scoped evidence.")])
    generator = FakeGenerator("Scoped answer [S1].")
    rag = ClassicalRAG(retriever=retriever, generator=generator)

    result = rag.answer("Question?", document_id="doc-1")

    assert result.status == "answered"
    assert retriever.scoped_calls == [(["Question?"], ["doc-1"], 5)]


def test_classical_rag_abstains_on_generator_signal() -> None:
    rag = ClassicalRAG(
        retriever=FakeRetriever([_hit(1, "c1", "Weak evidence.")]),
        generator=FakeGenerator("INSUFFICIENT_EVIDENCE"),
    )

    result = rag.answer("Unanswerable?")

    assert result.status == "insufficient_evidence"
    assert result.citations == []


def test_classical_rag_marks_uncited_answer() -> None:
    rag = ClassicalRAG(
        retriever=FakeRetriever([_hit(1, "c1", "Evidence.")]),
        generator=FakeGenerator("An answer without a source label."),
    )

    result = rag.answer("Question?")

    assert result.status == "uncited_answer"
    assert result.citations == []



def test_classical_rag_preserves_retrieval_metadata_in_citation() -> None:
    hit = _hit(1, "c1", "Hybrid evidence.")
    hit = RetrievalHit(
        rank=hit.rank,
        score=hit.score,
        dataset=hit.dataset,
        document_id=hit.document_id,
        chunk_id=hit.chunk_id,
        source_id=hit.source_id,
        text=hit.text,
        page_number=hit.page_number,
        section=hit.section,
        metadata={
            "retrieval_mode": "hybrid_rrf",
            "dense_score": 0.8,
            "sparse_score": 2.1,
            "fusion_score": 0.03,
        },
    )
    rag = ClassicalRAG(
        retriever=FakeRetriever([hit]),
        generator=FakeGenerator("Hybrid answer [S1]."),
    )

    result = rag.answer("Question?")

    assert result.citations[0].metadata["retrieval_mode"] == "hybrid_rrf"
    assert result.citations[0].metadata["fusion_score"] == 0.03
