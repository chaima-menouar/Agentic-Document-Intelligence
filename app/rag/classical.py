"""Mode A: classical retrieval-augmented generation with citations."""

from __future__ import annotations

import re
from typing import Sequence

from app.models import AnswerCitation, RAGAnswer
from app.retrieval import RetrievalHit

_CITATION_RE = re.compile(r"\[S(\d+)\]")
_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


def build_rag_prompt(question: str, hits: Sequence[RetrievalHit]) -> str:
    """Create a grounded prompt with stable source labels."""
    evidence_blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        location_parts = []
        if hit.section:
            location_parts.append(f"section={hit.section}")
        if hit.page_number is not None:
            location_parts.append(f"page={hit.page_number}")
        location = ", ".join(location_parts) if location_parts else "location=unknown"
        evidence_blocks.append(
            f"[S{index}] {location}\n{hit.text.strip()}"
        )

    evidence = "\n\n".join(evidence_blocks) if evidence_blocks else "(no evidence)"
    return f"""Answer the question using ONLY the evidence below.

Rules:
1. Do not use outside knowledge.
2. End every factual sentence with one or more source labels such as [S1].
3. Only cite labels that appear in the evidence; never invent a label.
4. If the evidence is not sufficient to answer, output exactly:
   { _INSUFFICIENT }
5. Keep the answer concise and directly responsive.
6. Do not add a bibliography or a separate sources section.

Question:
{question}

Evidence:
{evidence}

Answer:
"""


def _citation_numbers(answer: str, max_label: int) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    for raw in _CITATION_RE.findall(answer):
        number = int(raw)
        if 1 <= number <= max_label and number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers


class ClassicalRAG:
    """Retrieve evidence, generate a grounded answer, and map citations."""

    def __init__(self, *, retriever, generator) -> None:
        self.retriever = retriever
        self.generator = generator

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> RAGAnswer:
        question = question.strip()
        if not question:
            raise ValueError("question cannot be empty.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if document_id:
            hits = self.retriever.search_many_scoped(
                [question],
                [document_id],
                top_k=top_k,
            )[0]
        else:
            hits = self.retriever.search(question, top_k=top_k)

        if not hits:
            return RAGAnswer(
                question=question,
                answer="I do not have enough evidence in the indexed documents.",
                status="insufficient_evidence",
                citations=[],
                retrieved_chunks=0,
                used_citation_labels=[],
            )

        prompt = build_rag_prompt(question, hits)
        generated = self.generator.generate(prompt).strip()

        if not generated or generated == _INSUFFICIENT:
            return RAGAnswer(
                question=question,
                answer="I do not have enough evidence in the retrieved passages.",
                status="insufficient_evidence",
                citations=[],
                retrieved_chunks=len(hits),
                used_citation_labels=[],
            )

        citation_numbers = _citation_numbers(generated, len(hits))
        citations = []
        labels = []
        for number in citation_numbers:
            hit = hits[number - 1]
            label = f"S{number}"
            labels.append(label)
            citations.append(
                AnswerCitation(
                    label=label,
                    dataset=hit.dataset,
                    document_id=hit.document_id,
                    chunk_id=hit.chunk_id,
                    source_id=hit.source_id,
                    score=hit.score,
                    page_number=hit.page_number,
                    section=hit.section,
                    text=hit.text,
                )
            )

        status = "answered" if citations else "uncited_answer"
        return RAGAnswer(
            question=question,
            answer=generated,
            status=status,
            citations=citations,
            retrieved_chunks=len(hits),
            used_citation_labels=labels,
        )
