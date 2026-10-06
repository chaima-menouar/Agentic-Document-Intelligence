"""Reusable FAISS index construction for canonical text chunks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .semantic import DEFAULT_EMBEDDING_MODEL, SentenceTransformerEmbedder, _require_faiss


def _iter_chunks(path: Path, dataset_filter: str | None):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            if dataset_filter and chunk.get("dataset") != dataset_filter:
                continue
            yield chunk


def build_index(
    chunks_path: Path,
    output_dir: Path,
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    dataset_filter: str | None = None,
    batch_size: int = 128,
    limit: int | None = None,
    query_prefix: str = "",
) -> dict:
    """Embed canonical chunks and persist a cosine-ready FAISS index."""
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero when provided.")

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "chunks.jsonl"
    index_path = output_dir / "index.faiss"

    embedder = SentenceTransformerEmbedder(
        embedding_model,
        query_prefix=query_prefix,
    )
    faiss = _require_faiss()

    index = None
    vector_count = 0
    pending: list[dict] = []

    def flush(metadata_file) -> None:
        nonlocal index, vector_count, pending
        if not pending:
            return

        texts = [item["text"] for item in pending]
        vectors = embedder.encode_passages(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
        )
        vectors = np.asarray(vectors, dtype=np.float32)

        if index is None:
            if vectors.ndim != 2 or vectors.shape[1] <= 0:
                raise RuntimeError("Embedding model returned invalid vector shape.")
            index = faiss.IndexFlatIP(int(vectors.shape[1]))

        index.add(vectors)
        for item in pending:
            metadata_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        vector_count += len(pending)
        pending = []

    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        for chunk in _iter_chunks(chunks_path, dataset_filter):
            pending.append(chunk)
            if len(pending) >= batch_size:
                flush(metadata_file)
            if limit is not None and vector_count + len(pending) >= limit:
                pending = pending[: max(0, limit - vector_count)]
                flush(metadata_file)
                break

        flush(metadata_file)

    if index is None or vector_count == 0:
        raise RuntimeError("No chunks matched the requested index configuration.")

    faiss.write_index(index, str(index_path))

    manifest = {
        "format_version": 1,
        "embedding_model": embedding_model,
        "metric": "cosine_similarity_via_normalized_inner_product",
        "query_prefix": query_prefix,
        "dataset_filter": dataset_filter,
        "vector_count": vector_count,
        "dimension": int(index.d),
        "batch_size": batch_size,
        "source_chunks": str(chunks_path),
        "files": {
            "index": index_path.name,
            "chunks": metadata_path.name,
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest
