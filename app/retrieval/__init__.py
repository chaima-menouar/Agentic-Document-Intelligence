"""Semantic embedding and retrieval utilities."""

from .hybrid import BM25Index, HybridRetriever, LocalCrossEncoderReranker
from .index_builder import build_index
from .qasper_eval import (
    evidence_paragraphs,
    iter_qasper_questions,
    match_evidence_source_ids,
    recall_at_k,
)
from .semantic import (
    DEFAULT_EMBEDDING_MODEL,
    RetrievalHit,
    SemanticRetriever,
    SentenceTransformerEmbedder,
)

__all__ = [
    "BM25Index",
    "HybridRetriever",
    "LocalCrossEncoderReranker",
    "DEFAULT_EMBEDDING_MODEL",
    "build_index",
    "RetrievalHit",
    "SemanticRetriever",
    "SentenceTransformerEmbedder",
    "evidence_paragraphs",
    "iter_qasper_questions",
    "match_evidence_source_ids",
    "recall_at_k",
]
