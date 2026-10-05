"""Semantic embedding and retrieval utilities."""

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
    "DEFAULT_EMBEDDING_MODEL",
    "RetrievalHit",
    "SemanticRetriever",
    "SentenceTransformerEmbedder",
    "evidence_paragraphs",
    "iter_qasper_questions",
    "match_evidence_source_ids",
    "recall_at_k",
]
