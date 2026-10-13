"""Evaluation helpers for comparing RAG modes A/B/C."""

from .v2_metrics import (
    abstention_correct,
    answer_relevance_proxy,
    citation_precision,
    content_tokens,
)
from .metrics import (
    aggregate_mode_metrics,
    evaluate_agentic_answer,
    evaluate_classical_answer,
    evaluate_verified_answer,
)

__all__ = [
    "abstention_correct",
    "answer_relevance_proxy",
    "citation_precision",
    "content_tokens",
    "aggregate_mode_metrics",
    "evaluate_agentic_answer",
    "evaluate_classical_answer",
    "evaluate_verified_answer",
]
