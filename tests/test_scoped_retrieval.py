"""Tests for exact document-scoped semantic retrieval."""

from __future__ import annotations

import numpy as np

from app.retrieval.semantic import SemanticRetriever


class FakeIndex:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = np.asarray(vectors, dtype=np.float32)
        self.ntotal = len(vectors)
        self.d = self._vectors.shape[1]

    def reconstruct_n(self, start: int, count: int) -> np.ndarray:
        return self._vectors[start : start + count]


class FakeEmbedder:
    def encode(self, texts, *, batch_size=64, show_progress_bar=False):
        mapping = {
            "query-a": np.asarray([1.0, 0.0], dtype=np.float32),
            "query-b": np.asarray([0.0, 1.0], dtype=np.float32),
        }
        return np.stack([mapping[text] for text in texts])


def _chunk(document_id: str, chunk_id: str, source_id: str, text: str) -> dict:
    return {
        "dataset": "qasper",
        "document_id": document_id,
        "chunk_id": chunk_id,
        "source_id": source_id,
        "text": text,
        "page_number": None,
        "section": "Test",
        "metadata": {},
    }


def test_scoped_search_never_returns_other_document() -> None:
    retriever = SemanticRetriever(
        index=FakeIndex(
            [
                [0.90, 0.10],  # doc-a
                [0.70, 0.30],  # doc-a
                [1.00, 0.00],  # doc-b: globally best for query-a
                [0.00, 1.00],  # doc-b
            ]
        ),
        chunk_metadata=[
            _chunk("doc-a", "a1", "a:s1", "a one"),
            _chunk("doc-a", "a2", "a:s2", "a two"),
            _chunk("doc-b", "b1", "b:s1", "b one"),
            _chunk("doc-b", "b2", "b:s2", "b two"),
        ],
        embedder=FakeEmbedder(),
        manifest={},
    )

    hits = retriever.search_many_scoped(
        ["query-a", "query-b"],
        ["doc-a", "doc-b"],
        top_k=2,
    )

    assert [hit.document_id for hit in hits[0]] == ["doc-a", "doc-a"]
    assert [hit.chunk_id for hit in hits[0]] == ["a1", "a2"]
    assert [hit.document_id for hit in hits[1]] == ["doc-b", "doc-b"]
    assert hits[1][0].chunk_id == "b2"


def test_scoped_search_unknown_document_returns_empty() -> None:
    retriever = SemanticRetriever(
        index=FakeIndex([[1.0, 0.0]]),
        chunk_metadata=[_chunk("doc-a", "a1", "a:s1", "a one")],
        embedder=FakeEmbedder(),
        manifest={},
    )

    assert retriever.search_many_scoped(["query-a"], ["missing"], top_k=5) == []
