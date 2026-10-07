"""V2 semantic/NLI claim-grounding verifier."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.models import AnswerCitation, ClaimVerification, ExtractedClaim
from .verifier import CitationGroundingVerifier, lexical_support_score


class EntailmentScorer(Protocol):
    """Minimal semantic entailment scoring interface."""

    def score(self, premise: str, hypothesis: str) -> float:
        ...


class LocalNLIEntailmentScorer:
    """Lazy local NLI scorer backed by a Hugging Face sequence classifier."""

    def __init__(
        self,
        *,
        model_name: str = "cross-encoder/nli-MiniLM2-L6-H768",
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._entailment_index = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Semantic verification requires transformers/torch. "
                "Install requirements-retrieval.txt."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.eval()

        id2label = getattr(model.config, "id2label", {}) or {}
        entailment_index = None
        for index, label in id2label.items():
            if "entail" in str(label).lower():
                entailment_index = int(index)
                break

        if entailment_index is None:
            # The selected default model uses:
            # 0=contradiction, 1=entailment, 2=neutral.
            if getattr(model.config, "num_labels", 0) == 3:
                entailment_index = 1
            else:
                raise RuntimeError(
                    "Could not determine the entailment label for the NLI model."
                )

        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._entailment_index = entailment_index

    def score(self, premise: str, hypothesis: str) -> float:
        self._ensure_loaded()
        inputs = self._tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        )
        with self._torch.no_grad():
            logits = self._model(**inputs).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1)
        return float(probabilities[self._entailment_index].item())


class SemanticCitationGroundingVerifier:
    """Citation-aware semantic verifier with lexical fallback.

    Citation mapping remains mandatory. Once a claim cites valid retrieved
    evidence, a local NLI model estimates whether that evidence entails the
    claim. Lexical overlap is retained as a diagnostic, not as the primary
    decision signal.
    """

    def __init__(
        self,
        *,
        scorer: EntailmentScorer | None = None,
        supported_threshold: float = 0.70,
        review_threshold: float = 0.40,
        fallback_on_error: bool = True,
    ) -> None:
        if not 0.0 <= review_threshold <= supported_threshold <= 1.0:
            raise ValueError(
                "Require 0 <= review_threshold <= supported_threshold <= 1."
            )
        self.scorer = scorer or LocalNLIEntailmentScorer()
        self.supported_threshold = supported_threshold
        self.review_threshold = review_threshold
        self.fallback_on_error = fallback_on_error
        self.lexical_fallback = CitationGroundingVerifier()

    def _fallback(
        self,
        claim: ExtractedClaim,
        citations: Sequence[AnswerCitation],
        exc: Exception,
    ) -> ClaimVerification:
        result = self.lexical_fallback.verify([claim], citations)[0]
        return result.model_copy(
            update={
                "verifier_method": "lexical_fallback",
                "reason": (
                    f"Semantic verifier unavailable ({type(exc).__name__}); "
                    + result.reason
                ),
            }
        )

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
                        verifier_method="semantic_nli",
                        lexical_support_score=0.0,
                        semantic_entailment_score=0.0,
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
                        verifier_method="semantic_nli",
                        lexical_support_score=0.0,
                        semantic_entailment_score=0.0,
                    )
                )
                continue

            evidence_text = " ".join(citation.text for citation in matched)
            lexical_score = lexical_support_score(claim.text, evidence_text)

            try:
                semantic_score = self.scorer.score(evidence_text, claim.text)
            except Exception as exc:
                if not self.fallback_on_error:
                    raise
                results.append(self._fallback(claim, citations, exc))
                continue

            if semantic_score >= self.supported_threshold:
                status = "supported"
                reason = (
                    "The local NLI model finds the cited evidence semantically "
                    "entails the claim."
                )
            elif semantic_score >= self.review_threshold:
                status = "needs_review"
                reason = (
                    "The cited evidence is semantically related, but entailment "
                    "confidence is not strong enough for automatic support."
                )
            else:
                status = "unsupported"
                reason = (
                    "The local NLI model finds weak entailment between the cited "
                    "evidence and the claim."
                )

            results.append(
                ClaimVerification(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    citation_labels=claim.citation_labels,
                    evidence_labels=evidence_labels,
                    status=status,
                    support_score=semantic_score,
                    reason=reason,
                    verifier_method="semantic_nli",
                    lexical_support_score=lexical_score,
                    semantic_entailment_score=semantic_score,
                )
            )

        return results
