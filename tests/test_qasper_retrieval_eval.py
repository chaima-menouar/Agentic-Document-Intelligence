"""Unit tests for QASPER evidence mapping and Recall@k."""

from __future__ import annotations

from app.ingestion.dataset_normalizer import qasper_row_to_document
from app.retrieval.qasper_eval import (
    evidence_paragraphs,
    iter_qasper_questions,
    match_evidence_source_ids,
    recall_at_k,
)


def _row() -> dict:
    return {
        "id": "paper-1",
        "title": "Example",
        "abstract": "An abstract.",
        "full_text": {
            "section_name": ["Intro"],
            "paragraphs": [["The relevant evidence paragraph.", "Another paragraph."]],
        },
        "qas": {
            "question": ["What is relevant?"],
            "question_id": ["q1"],
            "answers": [
                {
                    "answer": [
                        {
                            "evidence": ["The relevant evidence paragraph."],
                            "unanswerable": False,
                        }
                    ]
                }
            ],
        },
    }


def test_qasper_question_and_evidence_mapping() -> None:
    row = _row()
    question = list(iter_qasper_questions(row))[0]
    evidence = evidence_paragraphs(question["answers"])
    document = qasper_row_to_document(row)
    source_ids = match_evidence_source_ids(document, evidence)

    assert question["question_id"] == "q1"
    assert evidence == {"The relevant evidence paragraph."}
    assert source_ids == {"qasper:paper-1:s000:p0000"}


def test_float_evidence_is_not_treated_as_text() -> None:
    answers = {
        "answer": [
            {"evidence": ["FLOAT SELECTED: Figure 1"]},
        ]
    }
    assert evidence_paragraphs(answers) == set()


def test_recall_at_k() -> None:
    predictions = [["a", "b", "c"], ["x", "y", "z"]]
    gold = [{"b"}, {"missing"}]

    assert recall_at_k(predictions, gold, 1) == 0.0
    assert recall_at_k(predictions, gold, 2) == 0.5
