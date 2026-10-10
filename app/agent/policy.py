"""Adaptive V2 retrieval policy for unresolved RAG claims."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import ClaimVerification, ExtractedClaim

_YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


@dataclass(frozen=True)
class RetrievalDecision:
    """One policy decision before an additional retrieval action."""

    action: str
    query: str
    failure_reason: str
    stop: bool = False


class AdaptiveRetrievalPolicy:
    """Choose a targeted next retrieval action from verification failure signals."""

    def __init__(self, *, min_support_improvement: float = 0.02) -> None:
        if min_support_improvement < 0:
            raise ValueError("min_support_improvement must be non-negative.")
        self.min_support_improvement = min_support_improvement

    @staticmethod
    def _answer_type_mismatch(question: str, claim_text: str) -> str | None:
        lowered = question.lower()
        if (
            "what year" in lowered
            or "which year" in lowered
            or lowered.startswith("when ")
        ) and not _YEAR_RE.search(claim_text):
            return "year"
        if (
            "how many" in lowered
            or "how much" in lowered
            or "number of" in lowered
        ) and not _NUMBER_RE.search(claim_text):
            return "number"
        return None

    def decide(
        self,
        *,
        question: str,
        claim: ExtractedClaim,
        verification: ClaimVerification,
        round_index: int,
        previous_step=None,
    ) -> RetrievalDecision:
        """Return a targeted query/action or an early-stop decision."""
        if previous_step is not None:
            new_chunks = getattr(previous_step, "new_chunks", 0)
            improvement = getattr(previous_step, "support_improvement", 0.0)
            if new_chunks == 0:
                return RetrievalDecision(
                    action="stop_no_new_evidence",
                    query=claim.text,
                    failure_reason="no_new_evidence",
                    stop=True,
                )
            # After a broadened/alternative search, another round with almost no
            # support gain is unlikely to justify more retrieval.
            if (
                round_index > 2
                and improvement < self.min_support_improvement
            ):
                return RetrievalDecision(
                    action="stop_stagnant_support",
                    query=claim.text,
                    failure_reason="stagnant_support",
                    stop=True,
                )

        mismatch = self._answer_type_mismatch(question, claim.text)
        if mismatch is not None:
            return RetrievalDecision(
                action="answer_type_search",
                query=f"{question} {mismatch} {claim.text}",
                failure_reason="answer_type_mismatch",
            )

        reason = verification.reason.lower()
        if not verification.citation_labels or "no citation" in reason:
            return RetrievalDecision(
                action="recover_missing_citation",
                query=claim.text,
                failure_reason="missing_citation",
            )

        if "do not map" in reason or "does not map" in reason:
            return RetrievalDecision(
                action="repair_citation_mapping",
                query=f"{question} {claim.text}",
                failure_reason="citation_mismatch",
            )

        if verification.status == "needs_review":
            return RetrievalDecision(
                action="strengthen_weak_evidence",
                query=f"{claim.text} {question}",
                failure_reason="weak_evidence",
            )

        if verification.status == "unsupported":
            return RetrievalDecision(
                action="search_alternative_evidence",
                query=(
                    claim.text
                    if round_index == 1
                    else f"{question} {claim.text}"
                ),
                failure_reason="unsupported_claim",
            )

        return RetrievalDecision(
            action="stop_already_supported",
            query=claim.text,
            failure_reason="already_supported",
            stop=True,
        )
