"""V2 hybrid dense+sparse retrieval with optional local reranking."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol

from .semantic import RetrievalHit, SemanticRetriever


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


class PairReranker(Protocol):
    """Minimal reranker interface used by HybridRetriever."""

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        ...


class LocalCrossEncoderReranker:
    """Lazy local cross-encoder reranker.

    The default model is compact and optimized for passage ranking. Raw logits
    are converted with a sigmoid so returned scores are easy to inspect.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self.model_name = model_name
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "Reranking requires sentence-transformers. "
                "Install requirements-retrieval.txt."
            ) from exc
        self._model = CrossEncoder(self.model_name)

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        self._ensure_loaded()
        import numpy as np

        pairs = [(query, passage) for passage in passages]
        raw = self._model.predict(pairs)
        values = np.asarray(raw, dtype=float).reshape(-1)
        return [float(1.0 / (1.0 + math.exp(-value))) for value in values]


class BM25Index:
    """Small in-memory BM25 index over the already-loaded retrieval chunks."""

    def __init__(
        self,
        texts: Sequence[str],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be greater than zero.")
        if not 0.0 <= b <= 1.0:
            raise ValueError("b must be between zero and one.")

        self.k1 = k1
        self.b = b
        self.doc_tokens = [_tokens(text) for text in texts]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_length = (
            sum(self.doc_lengths) / len(self.doc_lengths)
            if self.doc_lengths
            else 0.0
        )
        self.term_frequencies = [Counter(tokens) for tokens in self.doc_tokens]

        document_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            document_frequency.update(set(tokens))

        n_docs = len(self.doc_tokens)
        self.idf = {
            term: math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def scores(
        self,
        query: str,
        *,
        candidate_indices: Sequence[int] | None = None,
    ) -> list[tuple[int, float]]:
        query_terms = _tokens(query)
        if not query_terms:
            return []

        if candidate_indices is None:
            indices = range(len(self.doc_tokens))
        else:
            indices = candidate_indices

        results: list[tuple[int, float]] = []
        avgdl = self.avg_doc_length or 1.0

        for index in indices:
            frequencies = self.term_frequencies[index]
            doc_len = self.doc_lengths[index]
            score = 0.0

            for term in query_terms:
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * doc_len / avgdl
                )
                score += idf * (tf * (self.k1 + 1.0)) / denominator

            if score > 0:
                results.append((int(index), float(score)))

        results.sort(key=lambda item: item[1], reverse=True)
        return results


class HybridRetriever:
    """Fuse dense semantic and sparse lexical retrieval, then optionally rerank."""

    def __init__(
        self,
        dense_retriever: SemanticRetriever,
        *,
        reranker: PairReranker | None = None,
        candidate_multiplier: int = 4,
        rrf_k: int = 60,
    ) -> None:
        if candidate_multiplier <= 0:
            raise ValueError("candidate_multiplier must be greater than zero.")
        if rrf_k <= 0:
            raise ValueError("rrf_k must be greater than zero.")

        self.dense = dense_retriever
        self.reranker = reranker
        self.candidate_multiplier = candidate_multiplier
        self.rrf_k = rrf_k
        self.manifest = {
            **dense_retriever.manifest,
            "retrieval_mode": (
                "hybrid_rrf_reranked" if reranker is not None else "hybrid_rrf"
            ),
        }
        self.chunk_metadata = dense_retriever.chunk_metadata
        self.sparse = BM25Index(
            [payload["text"] for payload in self.chunk_metadata]
        )
        self._document_to_indices: dict[str, list[int]] = {}
        self._chunk_to_index: dict[str, int] = {}

        for index, payload in enumerate(self.chunk_metadata):
            self._document_to_indices.setdefault(
                payload["document_id"], []
            ).append(index)
            self._chunk_to_index[payload["chunk_id"]] = index

    def _hit_from_metadata(
        self,
        index: int,
        *,
        rank: int,
        score: float,
        metadata_updates: dict,
    ) -> RetrievalHit:
        payload = self.chunk_metadata[index]
        metadata = dict(payload.get("metadata") or {})
        metadata.update(metadata_updates)
        return RetrievalHit(
            rank=rank,
            score=float(score),
            dataset=payload["dataset"],
            document_id=payload["document_id"],
            chunk_id=payload["chunk_id"],
            source_id=payload["source_id"],
            text=payload["text"],
            page_number=payload.get("page_number"),
            section=payload.get("section"),
            metadata=metadata,
        )

    def _fuse(
        self,
        query: str,
        dense_hits: Sequence[RetrievalHit],
        sparse_ranked: Sequence[tuple[int, float]],
        *,
        top_k: int,
    ) -> list[RetrievalHit]:
        dense_by_index: dict[int, tuple[int, float]] = {}
        for rank, hit in enumerate(dense_hits, start=1):
            index = self._chunk_to_index[hit.chunk_id]
            dense_by_index[index] = (rank, float(hit.score))

        sparse_by_index = {
            index: (rank, score)
            for rank, (index, score) in enumerate(sparse_ranked, start=1)
        }

        candidate_indices = set(dense_by_index) | set(sparse_by_index)
        fused: list[tuple[int, float]] = []
        for index in candidate_indices:
            score = 0.0
            if index in dense_by_index:
                score += 1.0 / (self.rrf_k + dense_by_index[index][0])
            if index in sparse_by_index:
                score += 1.0 / (self.rrf_k + sparse_by_index[index][0])
            fused.append((index, score))

        fused.sort(key=lambda item: item[1], reverse=True)
        candidate_limit = min(
            max(top_k, top_k * self.candidate_multiplier),
            len(fused),
        )
        fused = fused[:candidate_limit]

        if self.reranker is not None and fused:
            passages = [self.chunk_metadata[index]["text"] for index, _ in fused]
            rerank_scores = self.reranker.score(query, passages)
            if len(rerank_scores) != len(fused):
                raise RuntimeError(
                    "Reranker returned a different number of scores than passages."
                )
            reranked = [
                (index, float(score), float(rerank_score))
                for (index, score), rerank_score in zip(
                    fused, rerank_scores, strict=True
                )
            ]
            reranked.sort(key=lambda item: item[2], reverse=True)

            return [
                self._hit_from_metadata(
                    index,
                    rank=rank,
                    score=rerank_score,
                    metadata_updates={
                        "retrieval_mode": "hybrid_rrf_reranked",
                        "fusion_score": fusion_score,
                        "rerank_score": rerank_score,
                        "dense_score": (
                            dense_by_index[index][1]
                            if index in dense_by_index
                            else None
                        ),
                        "sparse_score": (
                            sparse_by_index[index][1]
                            if index in sparse_by_index
                            else None
                        ),
                    },
                )
                for rank, (index, fusion_score, rerank_score) in enumerate(
                    reranked[:top_k], start=1
                )
            ]

        return [
            self._hit_from_metadata(
                index,
                rank=rank,
                score=fusion_score,
                metadata_updates={
                    "retrieval_mode": "hybrid_rrf",
                    "fusion_score": fusion_score,
                    "dense_score": (
                        dense_by_index[index][1]
                        if index in dense_by_index
                        else None
                    ),
                    "sparse_score": (
                        sparse_by_index[index][1]
                        if index in sparse_by_index
                        else None
                    ),
                },
            )
            for rank, (index, fusion_score) in enumerate(fused[:top_k], start=1)
        ]

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        candidate_k = max(top_k, top_k * self.candidate_multiplier)
        dense_hits = self.dense.search(query, top_k=candidate_k)
        sparse_hits = self.sparse.scores(query)[:candidate_k]
        return self._fuse(
            query,
            dense_hits,
            sparse_hits,
            top_k=top_k,
        )

    def search_many(
        self,
        queries: Sequence[str],
        *,
        top_k: int = 5,
        batch_size: int = 64,
    ) -> list[list[RetrievalHit]]:
        del batch_size
        return [self.search(query, top_k=top_k) for query in queries]

    def search_many_scoped(
        self,
        queries: Sequence[str],
        document_ids: Sequence[str],
        *,
        top_k: int = 5,
        batch_size: int = 64,
    ) -> list[list[RetrievalHit]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if len(queries) != len(document_ids):
            raise ValueError("queries and document_ids must have equal length.")
        if not queries:
            return []

        candidate_k = max(top_k, top_k * self.candidate_multiplier)
        dense_results = self.dense.search_many_scoped(
            queries,
            document_ids,
            top_k=candidate_k,
            batch_size=batch_size,
        )

        all_hits: list[list[RetrievalHit]] = []
        for query, document_id, dense_hits in zip(
            queries, document_ids, dense_results, strict=True
        ):
            candidate_indices = self._document_to_indices.get(document_id, [])
            sparse_hits = self.sparse.scores(
                query,
                candidate_indices=candidate_indices,
            )[:candidate_k]
            all_hits.append(
                self._fuse(
                    query,
                    dense_hits,
                    sparse_hits,
                    top_k=top_k,
                )
            )
        return all_hits
