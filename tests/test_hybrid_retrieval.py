"""Tests for V2 hybrid dense+sparse retrieval and reranking."""

from app.retrieval import BM25Index, HybridRetriever, RetrievalHit


def _hit(rank, score, chunk_id, text, document_id="doc-1"):
    return RetrievalHit(
        rank=rank,
        score=score,
        dataset="uploaded_pdf",
        document_id=document_id,
        chunk_id=chunk_id,
        source_id=f"src-{chunk_id}",
        text=text,
        page_number=rank,
        section=None,
        metadata={},
    )


CHUNKS = [
    {
        "dataset": "uploaded_pdf",
        "document_id": "doc-1",
        "chunk_id": "c1",
        "source_id": "src-c1",
        "text": "Neural semantic retrieval uses dense vector embeddings.",
        "page_number": 1,
        "section": None,
        "metadata": {},
    },
    {
        "dataset": "uploaded_pdf",
        "document_id": "doc-1",
        "chunk_id": "c2",
        "source_id": "src-c2",
        "text": "The exact project codename is ORION-7429 and appears in the appendix.",
        "page_number": 2,
        "section": None,
        "metadata": {},
    },
    {
        "dataset": "uploaded_pdf",
        "document_id": "doc-2",
        "chunk_id": "c3",
        "source_id": "src-c3",
        "text": "ORION-7429 is also mentioned in an unrelated external document.",
        "page_number": 1,
        "section": None,
        "metadata": {},
    },
]


class FakeDenseRetriever:
    def __init__(self):
        self.chunk_metadata = CHUNKS
        self.manifest = {"embedding_model": "fake-dense"}

    def search(self, query, *, top_k=5):
        hits = [
            _hit(1, 0.95, "c1", CHUNKS[0]["text"]),
            _hit(2, 0.40, "c2", CHUNKS[1]["text"]),
            _hit(3, 0.30, "c3", CHUNKS[2]["text"], document_id="doc-2"),
        ]
        return hits[:top_k]

    def search_many_scoped(self, queries, document_ids, *, top_k=5, batch_size=64):
        results = []
        for document_id in document_ids:
            if document_id == "doc-1":
                results.append([
                    _hit(1, 0.95, "c1", CHUNKS[0]["text"]),
                    _hit(2, 0.40, "c2", CHUNKS[1]["text"]),
                ][:top_k])
            elif document_id == "doc-2":
                results.append([
                    _hit(
                        1,
                        0.90,
                        "c3",
                        CHUNKS[2]["text"],
                        document_id="doc-2",
                    )
                ][:top_k])
            else:
                results.append([])
        return results


class FakeReranker:
    def __init__(self, preferred_phrase):
        self.preferred_phrase = preferred_phrase
        self.calls = []

    def score(self, query, passages):
        self.calls.append((query, list(passages)))
        return [
            0.95 if self.preferred_phrase in passage else 0.10
            for passage in passages
        ]


def test_bm25_prefers_exact_identifier_match() -> None:
    index = BM25Index([item["text"] for item in CHUNKS])

    ranked = index.scores("ORION-7429")

    assert ranked
    assert ranked[0][0] in {1, 2}
    assert ranked[0][1] > 0


def test_hybrid_fusion_can_promote_sparse_exact_match() -> None:
    retriever = HybridRetriever(
        FakeDenseRetriever(),
        candidate_multiplier=3,
    )

    hits = retriever.search("ORION-7429", top_k=2)

    assert {hit.chunk_id for hit in hits} == {"c1", "c2"} or {
        hit.chunk_id for hit in hits
    } == {"c2", "c3"}
    assert any(hit.chunk_id == "c2" for hit in hits)
    c2 = next(hit for hit in hits if hit.chunk_id == "c2")
    assert c2.metadata["sparse_score"] is not None
    assert c2.metadata["fusion_score"] > 0
    assert c2.metadata["retrieval_mode"] == "hybrid_rrf"


def test_hybrid_reranker_controls_final_order() -> None:
    reranker = FakeReranker("exact project codename")
    retriever = HybridRetriever(
        FakeDenseRetriever(),
        reranker=reranker,
        candidate_multiplier=3,
    )

    hits = retriever.search("What is the project codename?", top_k=2)

    assert hits[0].chunk_id == "c2"
    assert hits[0].metadata["retrieval_mode"] == "hybrid_rrf_reranked"
    assert hits[0].metadata["rerank_score"] == 0.95
    assert reranker.calls


def test_hybrid_scoped_search_never_leaks_other_document() -> None:
    retriever = HybridRetriever(
        FakeDenseRetriever(),
        candidate_multiplier=3,
    )

    results = retriever.search_many_scoped(
        ["ORION-7429"],
        ["doc-1"],
        top_k=3,
    )

    assert results
    assert all(hit.document_id == "doc-1" for hit in results[0])
    assert all(hit.chunk_id != "c3" for hit in results[0])


def test_hybrid_manifest_records_retrieval_mode() -> None:
    plain = HybridRetriever(FakeDenseRetriever())
    reranked = HybridRetriever(
        FakeDenseRetriever(),
        reranker=FakeReranker("codename"),
    )

    assert plain.manifest["retrieval_mode"] == "hybrid_rrf"
    assert reranked.manifest["retrieval_mode"] == "hybrid_rrf_reranked"
