"""Tests for transparent V2 comparison metrics."""

from app.evaluation import (
    abstention_correct,
    answer_relevance_proxy,
    citation_precision,
)
from app.models import AnswerCitation


def _citation(label="S1"):
    return AnswerCitation(
        label=label,
        dataset="test",
        document_id="doc-1",
        chunk_id="chunk-1",
        source_id="source-1",
        score=0.9,
        text="Evidence.",
    )


def test_answer_relevance_proxy_tracks_question_content_coverage() -> None:
    score = answer_relevance_proxy(
        "What technology is used for semantic retrieval?",
        "Semantic retrieval uses BGE technology [S1].",
    )
    assert score == 1.0


def test_citation_precision_rejects_unknown_labels() -> None:
    score = citation_precision(
        "Supported [S1]. Invented [S9].",
        [_citation("S1")],
    )
    assert score == 0.5


def test_citation_precision_is_zero_without_citations() -> None:
    assert citation_precision("No source label.", [_citation()]) == 0.0


def test_abstention_correct_matches_expected_behavior() -> None:
    assert abstention_correct(abstained=True, should_abstain=True) == 1.0
    assert abstention_correct(abstained=False, should_abstain=True) == 0.0
