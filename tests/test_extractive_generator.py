"""Tests for the deterministic offline extractive generator."""

from app.rag import ExtractiveGenerator


def _prompt(question: str, evidence: str) -> str:
    return f"""Answer the question using ONLY the evidence below.

Question:
{question}

Evidence:
{evidence}

Answer:
"""


def test_extractive_generator_returns_grounded_source() -> None:
    prompt = _prompt(
        "What improved in the experiment?",
        """[S1] section=Results
The experiment improved accuracy by five points.

[S2] section=Methods
The model used two layers.""",
    )
    answer = ExtractiveGenerator().generate(prompt)
    assert answer.endswith("[S1]")
    assert "experiment improved accuracy" in answer


def test_extractive_generator_abstains_without_source() -> None:
    assert ExtractiveGenerator().generate("No evidence here") == "INSUFFICIENT_EVIDENCE"


def test_extractive_generator_ignores_rule_example_label() -> None:
    prompt = """Rules:
2. Cite factual statements with one or more source labels such as [S1].
3. Only cite labels that appear in the evidence.

Question:
What should be returned?

Evidence:
[S1] section=Results
The retrieved evidence is the sentence that should be returned.

Answer:
"""
    answer = ExtractiveGenerator().generate(prompt)
    assert answer.startswith("The retrieved evidence")
    assert answer.endswith("[S1]")


def test_extractive_generator_selects_relevant_main_idea_sentence() -> None:
    prompt = _prompt(
        "What is the main idea of the text?",
        """[S1] page=1
important. Their purpose is changing, but the central idea is still the same: giving people access to knowledge and opportunities. In the future, successful libraries may combine traditional services with new ones.""",
    )

    answer = ExtractiveGenerator().generate(prompt)

    assert answer.startswith(
        "Their purpose is changing, but the central idea is still the same:"
    )
    assert answer.endswith("[S1]")
    assert answer != "important. [S1]"


def test_extractive_generator_can_choose_a_better_later_source() -> None:
    prompt = _prompt(
        "What technology is used for semantic search?",
        """[S1] page=1
The project contains a web interface for document upload.

[S2] page=2
Semantic search uses BGE embeddings with a FAISS vector index.""",
    )

    answer = ExtractiveGenerator().generate(prompt)

    assert "BGE embeddings" in answer
    assert answer.endswith("[S2]")


def test_extractive_generator_abstains_when_year_is_not_in_evidence() -> None:
    prompt = _prompt(
        "According to this document, what year was the first public library founded?",
        """[S1] page=1
Public libraries continue to provide access to knowledge and opportunities.

[S2] page=2
Modern libraries also provide digital services and practical workshops.""",
    )

    assert ExtractiveGenerator().generate(prompt) == "INSUFFICIENT_EVIDENCE"


def test_extractive_generator_returns_year_when_supported() -> None:
    prompt = _prompt(
        "What year was the program launched?",
        """[S1] page=1
The program was launched in 2021 and expanded the following year.""",
    )

    answer = ExtractiveGenerator().generate(prompt)

    assert "2021" in answer
    assert answer.endswith("[S1]")
