"""Helpers for QASPER evidence-retrieval evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.ingestion.dataset_normalizer import clean_text
from app.models import CorpusDocument


def iter_qasper_questions(row: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield question records from QASPER's column-oriented `qas` structure."""
    qas = row.get("qas") or {}

    if isinstance(qas, list):
        for item in qas:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(qas, dict):
        return

    questions = qas.get("question") or []
    question_ids = qas.get("question_id") or []
    answer_groups = qas.get("answers") or []

    if isinstance(questions, str):
        questions = [questions]
    if isinstance(question_ids, str):
        question_ids = [question_ids]
    if isinstance(answer_groups, dict):
        # Rare Arrow layouts can columnize nested structs. Reconstruct the
        # top-level group by indexing each list-valued field.
        size = len(questions)
        reconstructed = []
        for index in range(size):
            group = {}
            for key, value in answer_groups.items():
                if isinstance(value, list) and index < len(value):
                    group[key] = value[index]
                else:
                    group[key] = value
            reconstructed.append(group)
        answer_groups = reconstructed

    for index, question in enumerate(questions):
        yield {
            "question": clean_text(question),
            "question_id": (
                clean_text(question_ids[index])
                if index < len(question_ids)
                else f"question-{index}"
            ),
            "answers": (
                answer_groups[index]
                if isinstance(answer_groups, list) and index < len(answer_groups)
                else {}
            ),
        }


def evidence_paragraphs(answer_group: Any) -> set[str]:
    """Collect textual paragraph-level evidence from all answer annotations."""
    if not isinstance(answer_group, dict):
        return set()

    annotations = answer_group.get("answer") or []
    if isinstance(annotations, dict):
        # Columnized nested answer struct -> one dict per annotation.
        lengths = [
            len(value)
            for value in annotations.values()
            if isinstance(value, list)
        ]
        count = max(lengths, default=0)
        rows = []
        for index in range(count):
            row = {}
            for key, value in annotations.items():
                if isinstance(value, list) and index < len(value):
                    row[key] = value[index]
                else:
                    row[key] = value
            rows.append(row)
        annotations = rows

    if not isinstance(annotations, list):
        return set()

    evidence: set[str] = set()
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        values = annotation.get("evidence") or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            normalized = clean_text(value)
            if normalized and not normalized.startswith("FLOAT SELECTED"):
                evidence.add(normalized)
    return evidence


def match_evidence_source_ids(
    document: CorpusDocument,
    evidence: set[str],
) -> set[str]:
    """Map gold QASPER evidence paragraphs to canonical source segment IDs."""
    if not evidence:
        return set()

    normalized_segments = [
        (segment.segment_id, clean_text(segment.text))
        for segment in document.segments
        if clean_text(segment.text)
    ]

    matched: set[str] = set()
    for gold in evidence:
        # Evidence is documented by QASPER as paragraph-level text, so exact
        # normalized equality is the primary match.
        exact = {
            segment_id
            for segment_id, text in normalized_segments
            if text == gold
        }
        if exact:
            matched.update(exact)
            continue

        # Conservative fallback for small serialization/whitespace differences.
        for segment_id, text in normalized_segments:
            if len(gold) >= 40 and (gold in text or text in gold):
                matched.add(segment_id)

    return matched


def recall_at_k(
    ranked_source_ids: list[list[str]],
    gold_source_ids: list[set[str]],
    k: int,
) -> float:
    """Fraction of evaluable questions with at least one gold source in top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero.")
    if len(ranked_source_ids) != len(gold_source_ids):
        raise ValueError("Predictions and gold labels must have equal length.")
    if not gold_source_ids:
        return 0.0

    hits = 0
    for predicted, gold in zip(ranked_source_ids, gold_source_ids, strict=True):
        if gold.intersection(predicted[:k]):
            hits += 1
    return hits / len(gold_source_ids)
