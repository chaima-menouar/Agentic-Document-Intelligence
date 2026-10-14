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


def test_dated_question_abstains_on_undated_research_text() -> None:
    prompt = _prompt(
        "What was this research project's annual revenue in 2025?",
        "[S1] page=1\nThe research project improved retrieval accuracy.",
    )
    assert ExtractiveGenerator().generate(prompt) == "INSUFFICIENT_EVIDENCE"


def test_dated_question_uses_matching_year() -> None:
    prompt = _prompt(
        "What was revenue in 2025?",
        "[S1] page=1\nRevenue in 2024 was 10 million. Revenue in 2025 was 12 million.",
    )
    answer = ExtractiveGenerator().generate(prompt)
    assert "2025 was 12 million" in answer
    assert "2024" not in answer


def test_translation_score_keeps_requested_direction() -> None:
    prompt = _prompt("What BLEU score is reported for English-to-French translation?",
        "[S1] page=1\nEnglish-to-German translation achieved a BLEU score of 28.4.\n\n[S2] page=1\nEnglish-to-French translation achieved a BLEU score of 41.8.")
    answer = ExtractiveGenerator().generate(prompt)
    assert "41.8" in answer and "28.4" not in answer


def test_numeric_answer_recognizes_spelled_out_counts() -> None:
    prompt = _prompt("How many tasks were evaluated?", "[S1] page=1\nThe model was evaluated on eleven tasks.")
    assert "eleven" in ExtractiveGenerator().generate(prompt)


def test_generator_does_not_cut_a_long_sentence_mid_claim() -> None:
    prompt = _prompt("What did the study find?", "[S1] page=1\nThe study found " + "many preliminary observations " * 30 + "but did not establish a result.")
    assert ExtractiveGenerator().generate(prompt) == "INSUFFICIENT_EVIDENCE"


def test_when_question_accepts_month_date_without_year():
    prompt = _prompt('When does the pilot launch?', '[S1] page=2\nThe pilot launches on 12 November.')
    assert ExtractiveGenerator().generate(prompt) == 'The pilot launches on 12 November. [S1]'


def test_explicit_year_question_still_requires_year():
    prompt = _prompt('What year does the pilot launch?', '[S1] page=2\nThe pilot launches on 12 November.')
    assert ExtractiveGenerator().generate(prompt) == 'INSUFFICIENT_EVIDENCE'


def test_when_question_abstains_without_time_evidence():
    prompt = _prompt('When does the pilot launch?', '[S1] page=2\nThe pilot launch involves three research teams.')
    assert ExtractiveGenerator().generate(prompt) == 'INSUFFICIENT_EVIDENCE'
