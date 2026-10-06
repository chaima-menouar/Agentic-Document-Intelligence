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



def test_extractive_generator_ignores_rule_example_label() -> None:
    prompt = """Rules:
2. Cite factual statements with one or more source labels such as [S1].
3. Only cite labels that appear in the evidence.

Evidence:
[S1] section=Results
The retrieved evidence is the sentence that should be returned.

Answer:
"""
    answer = ExtractiveGenerator().generate(prompt)
    assert answer.startswith("The retrieved evidence")
    assert answer.endswith("[S1]")
