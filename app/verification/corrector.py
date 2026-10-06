"""Partial-answer correction for Verified RAG."""

from __future__ import annotations

from app.models import CorrectedRAGAnswer, VerifiedRAGAnswer


def _render_supported_claim(text: str, labels: list[str]) -> str:
    rendered = text.strip()
    if rendered and rendered[-1] not in ".!?":
        rendered += "."
    if labels:
        rendered += " " + "".join(f"[{label}]" for label in labels)
    return rendered


def correct_verified_answer(
    verified: VerifiedRAGAnswer,
) -> CorrectedRAGAnswer:
    """Keep only supported claims and return a safe final answer.

    Claims marked needs_review or unsupported are excluded from partial answers.
    This makes Mode B conservative by default and creates a clean hand-off to
    the later agentic re-retrieval stage.
    """
    if verified.verification_status == "insufficient_evidence":
        return CorrectedRAGAnswer(
            question=verified.question,
            original_answer=verified.answer,
            final_answer=verified.answer,
            correction_status="insufficient_evidence",
            verification_status=verified.verification_status,
            claims=verified.claims,
            verifications=verified.verifications,
            citations=verified.citations,
            kept_claim_ids=[],
            removed_claim_ids=[],
            retrieved_chunks=verified.retrieved_chunks,
        )

    by_claim_id = {
        item.claim_id: item
        for item in verified.verifications
    }

    kept_claims = []
    removed_claims = []
    for claim in verified.claims:
        verification = by_claim_id.get(claim.claim_id)
        if verification is not None and verification.status == "supported":
            kept_claims.append(claim)
        else:
            removed_claims.append(claim)

    if verified.claims and len(kept_claims) == len(verified.claims):
        required_labels = {
            label
            for claim in kept_claims
            for label in claim.citation_labels
        }
        original_has_all_labels = all(
            f"[{label}]" in verified.answer
            for label in required_labels
        )
        final_answer = (
            verified.answer
            if original_has_all_labels
            else " ".join(
                _render_supported_claim(claim.text, claim.citation_labels)
                for claim in kept_claims
            )
        )
        correction_status = "full_answer"
    elif kept_claims:
        final_answer = " ".join(
            _render_supported_claim(claim.text, claim.citation_labels)
            for claim in kept_claims
        )
        correction_status = "partial_answer"
    else:
        final_answer = "I do not have enough verified evidence to answer safely."
        correction_status = "insufficient_evidence"

    used_labels = {
        label
        for claim in kept_claims
        for label in claim.citation_labels
    }
    final_citations = [
        citation
        for citation in verified.citations
        if citation.label in used_labels
    ]

    return CorrectedRAGAnswer(
        question=verified.question,
        original_answer=verified.answer,
        final_answer=final_answer,
        correction_status=correction_status,
        verification_status=verified.verification_status,
        claims=verified.claims,
        verifications=verified.verifications,
        citations=final_citations,
        kept_claim_ids=[claim.claim_id for claim in kept_claims],
        removed_claim_ids=[claim.claim_id for claim in removed_claims],
        retrieved_chunks=verified.retrieved_chunks,
    )


class CorrectedVerifiedRAG:
    """Run Mode B verification and then remove non-supported claims."""

    def __init__(self, *, verified_rag) -> None:
        self.verified_rag = verified_rag

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> CorrectedRAGAnswer:
        verified = self.verified_rag.answer(
            question,
            top_k=top_k,
            document_id=document_id,
        )
        return correct_verified_answer(verified)
