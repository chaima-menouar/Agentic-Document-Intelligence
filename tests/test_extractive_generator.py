"""Tests for the offline extractive generator."""

from app.rag import ExtractiveGenerator


def test_extractive_generator_returns_grounded_source() -> None:
    prompt = """Evidence:
[S1] section=Results
The experiment improved accuracy by five points.

[S2] section=Methods
The model used two layers.

Answer:
"""
    answer = ExtractiveGenerator().generate(prompt)
    assert answer.endswith("[S1]")
    assert "experiment improved accuracy" in answer


def test_extractive_generator_abstains_without_source() -> None:
    assert ExtractiveGenerator().generate("No evidence here") == "INSUFFICIENT_EVIDENCE"
