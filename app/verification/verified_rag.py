"""Mode B: Classical RAG followed by claim-level verification."""

from __future__ import annotations

from app.models import VerifiedRAGAnswer
from app.verification.claim_extractor import extract_claims


class VerifiedRAG:
    """Wrap Mode A with deterministic claim extraction and grounding checks."""

    def __init__(self, *, rag, verifier) -> None:
        self.rag = rag
        self.verifier = verifier

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> VerifiedRAGAnswer:
        base = self.rag.answer(
            question,
            top_k=top_k,
            document_id=document_id,
        )

        if base.status == "insufficient_evidence":
            return VerifiedRAGAnswer(
                question=base.question,
                answer=base.answer,
                base_status=base.status,
                verification_status="insufficient_evidence",
                claims=[],
                verifications=[],
                citations=base.citations,
                retrieved_chunks=base.retrieved_chunks,
            )

        claims = extract_claims(base.answer)
        verifications = self.verifier.verify(claims, base.citations)

        statuses = [item.status for item in verifications]
        if not verifications:
            verification_status = "unsupported"
        elif all(status == "supported" for status in statuses):
            verification_status = "verified"
        elif any(status == "supported" for status in statuses):
            verification_status = "partially_supported"
        elif any(status == "needs_review" for status in statuses):
            verification_status = "needs_review"
        else:
            verification_status = "unsupported"

        return VerifiedRAGAnswer(
            question=base.question,
            answer=base.answer,
            base_status=base.status,
            verification_status=verification_status,
            claims=claims,
            verifications=verifications,
            citations=base.citations,
            retrieved_chunks=base.retrieved_chunks,
        )
