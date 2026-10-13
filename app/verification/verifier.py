"""Free local claim-grounding verifier for Mode B."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.models import AnswerCitation, ClaimVerification, ExtractedClaim

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "their", "this", "to", "was", "were", "which", "with",
}


def _content_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS and len(token) > 1
    }


def lexical_support_score(claim: str, evidence: str) -> float:
    """Return the fraction of claim content tokens present in evidence."""
    claim_tokens = _content_tokens(claim)
    if not claim_tokens:
        return 0.0
    evidence_tokens = _content_tokens(evidence)
    return len(claim_tokens & evidence_tokens) / len(claim_tokens)


class CitationGroundingVerifier:
    """Transparent offline claim verifier.

    This baseline does not pretend to solve natural-language entailment. It
    verifies that claims cite real retrieved evidence and measures lexical
    grounding against those cited passages. Low-overlap cited claims are marked
    for review rather than being presented as verified facts.
    """

    def __init__(
        self,
        *,
        supported_threshold: float = 0.55,
        review_threshold: float = 0.25,
    ) -> None:
        if not 0.0 <= review_threshold <= supported_threshold <= 1.0:
            raise ValueError(
                "Require 0 <= review_threshold <= supported_threshold <= 1."
            )
        self.supported_threshold = supported_threshold
        self.review_threshold = review_threshold

    def verify(
        self,
        claims: Sequence[ExtractedClaim],
        citations: Sequence[AnswerCitation],
    ) -> list[ClaimVerification]:
        citation_map = {citation.label: citation for citation in citations}
        results: list[ClaimVerification] = []

        for claim in claims:
            matched = [
                citation_map[label]
                for label in claim.citation_labels
                if label in citation_map
            ]
            evidence_labels = [citation.label for citation in matched]

            if not claim.citation_labels:
                results.append(
                    ClaimVerification(
                        claim_id=claim.claim_id,
                        claim_text=claim.text,
                        citation_labels=[],
                        evidence_labels=[],
                        status="unsupported",
                        support_score=0.0,
                        reason="The claim has no citation label.",
                        verifier_method="lexical",
                        lexical_support_score=0.0,
                    )
                )
                continue

            if not matched:
                results.append(
                    ClaimVerification(
                        claim_id=claim.claim_id,
                        claim_text=claim.text,
                        citation_labels=claim.citation_labels,
                        evidence_labels=[],
                        status="unsupported",
                        support_score=0.0,
                        reason="The cited labels do not map to retrieved evidence.",
                        verifier_method="lexical",
                        lexical_support_score=0.0,
                    )
                )
                continue

            evidence_text = " ".join(citation.text for citation in matched)
            score = lexical_support_score(claim.text, evidence_text)

            if score >= self.supported_threshold:
                status = "supported"
                reason = "The claim is strongly grounded in its cited evidence."
            elif score >= self.review_threshold:
                status = "needs_review"
                reason = (
                    "The citation is valid, but lexical grounding is only partial."
                )
            else:
                status = "unsupported"
                reason = (
                    "The cited evidence has weak lexical grounding for this claim."
                )

            results.append(
                ClaimVerification(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    citation_labels=claim.citation_labels,
                    evidence_labels=evidence_labels,
                    status=status,
                    support_score=score,
                    reason=reason,
                    verifier_method="lexical",
                    lexical_support_score=score,
                )
            )

        return results
