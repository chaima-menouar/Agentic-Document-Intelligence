"""Consolidated V1 vs V2 evaluation for Agentic Document Intelligence.

The benchmark mixes real-index controlled cases with explicit regression cases.
It is designed to measure grounding/safety behavior and engineering trade-offs,
not to claim general open-ended LLM quality.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.evaluation import (
    answer_relevance_proxy,
    citation_precision,
)
from app.models import AnswerCitation, ExtractedClaim
from app.rag import ClassicalRAG, ExtractiveGenerator, GroundedLocalGenerator
from app.retrieval import SemanticRetriever
from app.verification import (
    CitationGroundingVerifier,
    SemanticCitationGroundingVerifier,
)
from scripts.evaluate_agent_policies import evaluate as evaluate_agent_policies


class ScriptedGenerator:
    """Return one deterministic response exactly as supplied."""

    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


class SequenceClient:
    """Tiny local-generator test client with deterministic sequential outputs."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("No scripted local-generator response remains.")
        return self.responses.pop(0)


def _first_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    first = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0].strip()
    if len(first.split()) < 8:
        first = " ".join(normalized.split()[:30]).rstrip(".!?") + "."
    return first


def _select_real_case(retriever: SemanticRetriever) -> tuple[str, str]:
    """Return a document id and a sufficiently informative indexed claim."""
    for payload in retriever.chunk_metadata:
        text = payload.get("text", "")
        if len(text.split()) >= 20:
            return payload["document_id"], _first_sentence(text)
    raise RuntimeError("No suitable real-index evaluation passage found.")


def _timed(fn):
    started = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - started


def _citation(text: str, label: str = "S1") -> AnswerCitation:
    return AnswerCitation(
        label=label,
        dataset="controlled",
        document_id="controlled-doc",
        chunk_id=f"controlled-{label}",
        source_id=f"controlled-{label}",
        score=1.0,
        page_number=1,
        section="Controlled evaluation",
        text=text,
    )


def _verification_cases() -> list[dict]:
    return [
        {
            "name": "direct_entailment",
            "evidence": "The program was launched in 2021.",
            "claim": "The program was launched in 2021.",
            "expected": "supported",
        },
        {
            "name": "semantic_paraphrase",
            "evidence": "The experiment made responses substantially faster.",
            "claim": "The experiment reduced latency.",
            "expected": "supported",
        },
        {
            "name": "explicit_contradiction",
            "evidence": "The experiment did not improve accuracy.",
            "claim": "The experiment improved accuracy.",
            "expected": "unsupported",
        },
    ]


def _evaluate_verifiers() -> dict:
    lexical = CitationGroundingVerifier()
    semantic = SemanticCitationGroundingVerifier()

    records: list[dict] = []
    lexical_times: list[float] = []
    semantic_times: list[float] = []

    for index, case in enumerate(_verification_cases(), start=1):
        label = f"S{index}"
        claim = ExtractedClaim(
            claim_id=f"claim_{index:03d}",
            text=case["claim"],
            citation_labels=[label],
        )
        citation = _citation(case["evidence"], label=label)

        lexical_result, lexical_time = _timed(
            lambda: lexical.verify([claim], [citation])[0]
        )
        semantic_result, semantic_time = _timed(
            lambda: semantic.verify([claim], [citation])[0]
        )
        lexical_times.append(lexical_time)
        semantic_times.append(semantic_time)

        records.append(
            {
                **case,
                "v1": {
                    "status": lexical_result.status,
                    "support_score": lexical_result.support_score,
                    "correct": lexical_result.status == case["expected"],
                },
                "v2": {
                    "status": semantic_result.status,
                    "support_score": semantic_result.support_score,
                    "lexical_diagnostic": semantic_result.lexical_support_score,
                    "semantic_entailment": semantic_result.semantic_entailment_score,
                    "verifier_method": semantic_result.verifier_method,
                    "correct": semantic_result.status == case["expected"],
                },
            }
        )

    return {
        "cases": records,
        "v1_classification_accuracy": (
            sum(row["v1"]["correct"] for row in records) / len(records)
        ),
        "v2_classification_accuracy": (
            sum(row["v2"]["correct"] for row in records) / len(records)
        ),
        "v1_mean_latency_seconds": statistics.fmean(lexical_times),
        "v2_mean_latency_seconds": statistics.fmean(semantic_times),
    }


def _evaluate_generation_guard(retriever: SemanticRetriever) -> dict:
    document_id, seed_claim = _select_real_case(retriever)
    hits = retriever.search_many_scoped(
        [seed_claim],
        [document_id],
        top_k=1,
    )[0]
    if not hits:
        raise RuntimeError("Could not retrieve the controlled real-index passage.")

    grounded_claim = _first_sentence(hits[0].text)
    question = grounded_claim

    # V1 local-generation contract: an uncited model output passes through the
    # generator layer and ClassicalRAG marks it as an uncited answer.
    v1_rag = ClassicalRAG(
        retriever=retriever,
        generator=ScriptedGenerator(grounded_claim),
    )
    v1_answer, v1_latency = _timed(
        lambda: v1_rag.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
    )

    # V2 guard sees the same uncited first output, performs one repair, and
    # accepts the repaired evidence label.
    client = SequenceClient(
        [
            grounded_claim,
            f"{grounded_claim} [S1]",
        ]
    )
    v2_rag = ClassicalRAG(
        retriever=retriever,
        generator=GroundedLocalGenerator(
            client=client,
            max_repair_attempts=1,
        ),
    )
    v2_answer, v2_latency = _timed(
        lambda: v2_rag.answer(
            question,
            top_k=1,
            document_id=document_id,
        )
    )

    return {
        "question": question,
        "v1": {
            "status": v1_answer.status,
            "citation_precision": citation_precision(
                v1_answer.answer,
                v1_answer.citations,
            ),
            "answer_relevance_proxy": answer_relevance_proxy(
                question,
                v1_answer.answer,
            ),
            "latency_seconds": v1_latency,
        },
        "v2": {
            "status": v2_answer.status,
            "citation_precision": citation_precision(
                v2_answer.answer,
                v2_answer.citations,
            ),
            "answer_relevance_proxy": answer_relevance_proxy(
                question,
                v2_answer.answer,
            ),
            "repair_calls": client.calls,
            "latency_seconds": v2_latency,
        },
    }


def _evaluate_regressions() -> dict:
    generator = ExtractiveGenerator()

    main_idea_prompt = """Answer the question using ONLY the evidence below.

Question:
What is the main idea of the text?

Evidence:
[S1] page=1
important. Their purpose is changing, but the central idea is still the same: giving people access to knowledge and opportunities. In the future, successful libraries may combine traditional services with new ones.

Answer:
"""
    main_idea_answer = generator.generate(main_idea_prompt)

    unsupported_year_prompt = """Answer the question using ONLY the evidence below.

Question:
According to this document, what year was the first public library founded?

Evidence:
[S1] page=1
Public libraries continue to provide access to knowledge and opportunities.

[S2] page=2
Modern libraries also provide digital services and practical workshops.

Answer:
"""
    year_answer = generator.generate(unsupported_year_prompt)

    return {
        "main_idea_demo_regression": {
            "passed": (
                "central idea" in main_idea_answer.lower()
                and main_idea_answer != "important. [S1]"
            ),
            "answer": main_idea_answer,
        },
        "unsupported_year_demo_regression": {
            "passed": year_answer == "INSUFFICIENT_EVIDENCE",
            "answer": year_answer,
        },
    }


def evaluate(
    index_dir: Path,
    output_path: Path,
    *,
    agent_cases: int = 20,
) -> dict:
    retriever = SemanticRetriever.load(index_dir)

    generation_guard = _evaluate_generation_guard(retriever)
    verification = _evaluate_verifiers()

    agent_output = output_path.parent / "_v2_agent_policy_component.json"
    agent_policy = evaluate_agent_policies(
        index_dir,
        agent_output,
        cases=agent_cases,
        max_rounds=3,
        additional_top_k=3,
        adaptive_budget=6,
    )
    try:
        agent_output.unlink(missing_ok=True)
    except OSError:
        pass

    regressions = _evaluate_regressions()

    recoverable = agent_policy["recoverable_uncited"]
    unsupported = agent_policy["unsupported_claim"]

    scorecard = {
        "generation_citation_precision": {
            "v1": generation_guard["v1"]["citation_precision"],
            "v2": generation_guard["v2"]["citation_precision"],
        },
        "generation_answer_relevance_proxy": {
            "v1": generation_guard["v1"]["answer_relevance_proxy"],
            "v2": generation_guard["v2"]["answer_relevance_proxy"],
        },
        "verification_classification_accuracy": {
            "v1": verification["v1_classification_accuracy"],
            "v2": verification["v2_classification_accuracy"],
        },
        "recoverable_claim_recovery_rate": {
            "v1": recoverable["fixed_recovery_rate"],
            "v2": recoverable["adaptive_recovery_rate"],
        },
        "unsupported_safe_abstention_rate": {
            "v1": unsupported["fixed_safe_abstention_rate"],
            "v2": unsupported["adaptive_safe_abstention_rate"],
        },
        "unsupported_average_agent_rounds": {
            "v1": unsupported["fixed_average_rounds"],
            "v2": unsupported["adaptive_average_rounds"],
        },
        "unsupported_average_additional_chunks": {
            "v1": unsupported["fixed_average_chunks"],
            "v2": unsupported["adaptive_average_chunks"],
        },
        "paid_external_api_cost": {
            "v1": 0.0,
            "v2": 0.0,
        },
    }

    report = {
        "benchmark": "agentic_document_intelligence_v1_vs_v2",
        "note": (
            "Controlled grounding/safety and regression benchmark. "
            "Answer relevance is a transparent lexical proxy, not an LLM judge."
        ),
        "scorecard": scorecard,
        "generation_guard": generation_guard,
        "semantic_verification": verification,
        "agent_policy": agent_policy,
        "regressions": regressions,
        "capabilities": {
            "v1": {
                "scanned_pdf_ocr": False,
                "local_llm_citation_repair": False,
                "semantic_nli_verification": False,
                "adaptive_agent_budget": False,
            },
            "v2": {
                "scanned_pdf_ocr": True,
                "local_llm_citation_repair": True,
                "semantic_nli_verification": True,
                "adaptive_agent_budget": True,
            },
        },
        "configuration": {
            "retriever": retriever.manifest.get("embedding_model"),
            "agent_cases": agent_cases,
            "external_paid_api_cost": 0.0,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the consolidated V1 vs V2 evaluation."
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper-bge-small"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/v1_vs_v2.json"),
    )
    parser.add_argument("--agent-cases", type=int, default=20)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.agent_cases <= 0:
        raise SystemExit("--agent-cases must be greater than zero.")
    report = evaluate(
        args.index,
        args.output,
        agent_cases=args.agent_cases,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
