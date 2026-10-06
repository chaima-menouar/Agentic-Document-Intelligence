"""Real-index smoke test for Mode C agentic claim recovery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.agent import AgenticVerifiedRAG
from app.rag import ClassicalRAG
from app.retrieval import SemanticRetriever
from app.verification import CitationGroundingVerifier, VerifiedRAG


class ScriptedUncitedGenerator:
    """Return a known corpus claim without a citation to force Mode C recovery."""

    def __init__(self, claim: str) -> None:
        self.claim = claim

    def generate(self, prompt: str) -> str:
        return self.claim


def _target_claim(text: str) -> str:
    normalized = " ".join(text.split())
    sentence = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0].strip()
    if len(sentence.split()) < 8:
        words = normalized.split()[:30]
        sentence = " ".join(words).rstrip(".!?") + "."
    return sentence


def run_smoke(index_dir: Path, output_path: Path) -> dict:
    retriever = SemanticRetriever.load(index_dir)

    target_payload = next(
        item
        for item in retriever.chunk_metadata
        if len(item.get("text", "").split()) >= 12
    )
    claim = _target_claim(target_payload["text"])
    document_id = target_payload["document_id"]

    classical = ClassicalRAG(
        retriever=retriever,
        generator=ScriptedUncitedGenerator(claim),
    )
    verifier = CitationGroundingVerifier()
    verified = VerifiedRAG(
        rag=classical,
        verifier=verifier,
    )
    agent = AgenticVerifiedRAG(
        verified_rag=verified,
        retriever=retriever,
        verifier=verifier,
        max_rounds=2,
        additional_top_k=3,
    )

    result = agent.answer(
        "What evidence is stated in this document?",
        top_k=1,
        document_id=document_id,
    )

    if result.status != "complete":
        raise RuntimeError(f"Agentic recovery did not complete: {result.status}")
    if not result.recovered_claim_ids:
        raise RuntimeError("Agentic recovery did not recover an unsupported claim.")
    if not result.citations:
        raise RuntimeError("Recovered Mode C answer has no final citations.")

    report = {
        "mode": "agentic_verified_rag",
        "retriever_model": retriever.manifest["embedding_model"],
        "document_id": document_id,
        "forced_uncited_claim": claim,
        "result": result.model_dump(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test Mode C agentic recovery.")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/indexes/qasper-bge-small"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/agentic_rag_smoke.json"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_smoke(args.index, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
