"""Tests for deterministic claim extraction."""

from app.verification import extract_claims


def test_extract_claims_preserves_citation_labels() -> None:
    claims = extract_claims(
        "The model improves retrieval [S1]. "
        "It also reduces latency [S2][S3]."
    )

    assert len(claims) == 2
    assert claims[0].text == "The model improves retrieval."
    assert claims[0].citation_labels == ["S1"]
    assert claims[1].citation_labels == ["S2", "S3"]


def test_extract_claims_attaches_trailing_citation_fragment() -> None:
    claims = extract_claims("The result improved significantly. [S1]")

    assert len(claims) == 1
    assert claims[0].citation_labels == ["S1"]
    assert claims[0].text == "The result improved significantly."


def test_extract_claims_empty_answer() -> None:
    assert extract_claims("   ") == []
