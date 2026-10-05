"""Sentence-embedding + FAISS semantic retrieval.

Heavy retrieval dependencies are imported lazily so the lightweight project
test suite can still run without downloading ML models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _require_faiss():
    try:
        import faiss  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in integration CI
        raise RuntimeError(
            "FAISS is not installed. Run: pip install -r requirements-retrieval.txt"
        ) from exc
    return faiss


class SentenceTransformerEmbedder:
    """Thin wrapper around SentenceTransformers with cosine-ready embeddings."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - integration dependency
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install -r requirements-retrieval.txt"
            ) from exc

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 64,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        embeddings = self._model.encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress_bar,
        )
        return np.asarray(embeddings, dtype=np.float32)


@dataclass(frozen=True)
class RetrievalHit:
    """One ranked retrieval result."""

    rank: int
    score: float
    dataset: str
    document_id: str
    chunk_id: str
    source_id: str
    text: str
    page_number: int | None
    section: str | None
    metadata: dict[str, Any]


class SemanticRetriever:
    """Load a saved FAISS index and perform cosine-similarity search."""

    def __init__(
        self,
        *,
        index: Any,
        chunk_metadata: list[dict[str, Any]],
        embedder: Any,
        manifest: dict[str, Any],
    ) -> None:
        if int(index.ntotal) != len(chunk_metadata):
            raise ValueError(
                "FAISS vector count does not match retrieval metadata count."
            )
        self.index = index
        self.chunk_metadata = chunk_metadata
        self.embedder = embedder
        self.manifest = manifest

    @classmethod
    def load(
        cls,
        index_dir: str | Path,
        *,
        embedder: Any | None = None,
    ) -> "SemanticRetriever":
        path = Path(index_dir)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        faiss = _require_faiss()
        index = faiss.read_index(str(path / "index.faiss"))

        chunk_metadata: list[dict[str, Any]] = []
        with (path / "chunks.jsonl").open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    chunk_metadata.append(json.loads(line))

        if embedder is None:
            embedder = SentenceTransformerEmbedder(manifest["embedding_model"])

        return cls(
            index=index,
            chunk_metadata=chunk_metadata,
            embedder=embedder,
            manifest=manifest,
        )

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        return self.search_many([query], top_k=top_k)[0]

    def search_many(
        self,
        queries: Sequence[str],
        *,
        top_k: int = 5,
        batch_size: int = 64,
    ) -> list[list[RetrievalHit]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if not queries:
            return []

        query_vectors = self.embedder.encode(
            list(queries),
            batch_size=batch_size,
            show_progress_bar=False,
        )
        scores, indices = self.index.search(
            np.asarray(query_vectors, dtype=np.float32),
            min(top_k, len(self.chunk_metadata)),
        )

        all_hits: list[list[RetrievalHit]] = []
        for row_scores, row_indices in zip(scores, indices, strict=True):
            hits: list[RetrievalHit] = []
            for rank, (score, vector_index) in enumerate(
                zip(row_scores, row_indices, strict=True),
                start=1,
            ):
                if vector_index < 0:
                    continue
                payload = self.chunk_metadata[int(vector_index)]
                hits.append(
                    RetrievalHit(
                        rank=rank,
                        score=float(score),
                        dataset=payload["dataset"],
                        document_id=payload["document_id"],
                        chunk_id=payload["chunk_id"],
                        source_id=payload["source_id"],
                        text=payload["text"],
                        page_number=payload.get("page_number"),
                        section=payload.get("section"),
                        metadata=payload.get("metadata") or {},
                    )
                )
            all_hits.append(hits)

        return all_hits
