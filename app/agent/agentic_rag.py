"""Mode C: bounded agentic re-retrieval for unresolved claims."""

from __future__ import annotations

from app.models import (
    AgenticRAGAnswer,
    AgenticRetrievalStep,
    AnswerCitation,
    VerifiedRAGAnswer,
)
from app.verification import correct_verified_answer


def _summarize_verification_status(verifications) -> str:
    statuses = [item.status for item in verifications]
    if not statuses:
        return "unsupported"
    if all(status == "supported" for status in statuses):
        return "verified"
    if any(status == "supported" for status in statuses):
        return "partially_supported"
    if any(status == "needs_review" for status in statuses):
        return "needs_review"
    return "unsupported"


def _unique_labels(labels: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            result.append(label)
    return result


class AgenticVerifiedRAG:
    """Mode C with a hard bound on additional retrieval rounds.

    The agent starts from Mode B. Claims that are not supported are used as
    targeted retrieval queries. Newly retrieved passages are attached as
    evidence and the claim verifier runs again. The loop stops as soon as all
    claims are supported or when max_rounds is reached.
    """

    def __init__(
        self,
        *,
        verified_rag,
        retriever,
        verifier,
        max_rounds: int = 2,
        additional_top_k: int = 5,
    ) -> None:
        if max_rounds <= 0:
            raise ValueError("max_rounds must be greater than zero.")
        if additional_top_k <= 0:
            raise ValueError("additional_top_k must be greater than zero.")
        self.verified_rag = verified_rag
        self.retriever = retriever
        self.verifier = verifier
        self.max_rounds = max_rounds
        self.additional_top_k = additional_top_k

    def _retrieve(
        self,
        query: str,
        *,
        document_id: str | None,
    ):
        if document_id:
            return self.retriever.search_many_scoped(
                [query],
                [document_id],
                top_k=self.additional_top_k,
            )[0]
        return self.retriever.search(
            query,
            top_k=self.additional_top_k,
        )

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> AgenticRAGAnswer:
        initial = self.verified_rag.answer(
            question,
            top_k=top_k,
            document_id=document_id,
        )
        current = initial
        steps: list[AgenticRetrievalStep] = []
        rounds_used = 0
        additional_chunks_considered = 0

        # If Mode B could not even produce claims, retry the whole question with
        # a wider evidence window before switching to claim-specific searches.
        if not current.claims:
            for round_index in range(1, self.max_rounds + 1):
                rounds_used = round_index
                retry_top_k = top_k + round_index * self.additional_top_k
                retry = self.verified_rag.answer(
                    question,
                    top_k=retry_top_k,
                    document_id=document_id,
                )
                additional_chunks_considered += max(
                    0,
                    retry.retrieved_chunks - current.retrieved_chunks,
                )
                score = max(
                    (item.support_score for item in retry.verifications),
                    default=0.0,
                )
                resolved = bool(retry.claims)
                steps.append(
                    AgenticRetrievalStep(
                        round_index=round_index,
                        claim_id="answer",
                        query=question,
                        retrieved_labels=[
                            citation.label for citation in retry.citations
                        ],
                        support_score=score,
                        resolved=resolved,
                    )
                )
                current = retry
                if resolved:
                    break

        if current.verification_status == "verified":
            correction = correct_verified_answer(current)
            return AgenticRAGAnswer(
                question=current.question,
                initial_answer=initial.answer,
                final_answer=correction.final_answer,
                status="complete",
                initial_verification_status=initial.verification_status,
                final_verification_status=current.verification_status,
                correction_status=correction.correction_status,
                rounds_used=rounds_used,
                additional_chunks_considered=additional_chunks_considered,
                recovered_claim_ids=[],
                unresolved_claim_ids=[],
                steps=steps,
                claims=current.claims,
                verifications=current.verifications,
                citations=correction.citations,
            )

        claims_by_id = {
            claim.claim_id: claim
            for claim in current.claims
        }
        verification_by_id = {
            item.claim_id: item
            for item in current.verifications
        }
        citations = list(current.citations)
        citation_label_by_chunk = {
            citation.chunk_id: citation.label
            for citation in citations
        }

        initially_unresolved = {
            claim_id
            for claim_id, verification in verification_by_id.items()
            if verification.status != "supported"
        }

        start_round = rounds_used + 1
        for round_index in range(start_round, self.max_rounds + 1):
            unresolved_claims = [
                claims_by_id[claim_id]
                for claim_id, verification in verification_by_id.items()
                if verification.status != "supported"
                and claim_id in claims_by_id
            ]
            if not unresolved_claims:
                break

            rounds_used = round_index
            for claim_position, claim in enumerate(unresolved_claims, start=1):
                query = (
                    claim.text
                    if round_index == 1
                    else f"{question} {claim.text}"
                )
                hits = self._retrieve(
                    query,
                    document_id=document_id,
                )
                additional_chunks_considered += len(hits)

                new_labels: list[str] = []
                for rank, hit in enumerate(hits, start=1):
                    label = citation_label_by_chunk.get(hit.chunk_id)
                    if label is None:
                        label = f"A{round_index}C{claim_position}S{rank}"
                        citation_label_by_chunk[hit.chunk_id] = label
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
                    new_labels.append(label)

                updated_claim = claim.model_copy(
                    update={
                        "citation_labels": _unique_labels(
                            claim.citation_labels + new_labels
                        )
                    }
                )
                claims_by_id[claim.claim_id] = updated_claim
                verification = self.verifier.verify(
                    [updated_claim],
                    citations,
                )[0]
                verification_by_id[claim.claim_id] = verification

                steps.append(
                    AgenticRetrievalStep(
                        round_index=round_index,
                        claim_id=claim.claim_id,
                        query=query,
                        retrieved_labels=new_labels,
                        support_score=verification.support_score,
                        resolved=verification.status == "supported",
                    )
                )

            if all(
                item.status == "supported"
                for item in verification_by_id.values()
            ):
                break

        final_claims = [
            claims_by_id[claim.claim_id]
            for claim in current.claims
            if claim.claim_id in claims_by_id
        ]
        final_verifications = [
            verification_by_id[claim.claim_id]
            for claim in final_claims
            if claim.claim_id in verification_by_id
        ]
        final_verification_status = _summarize_verification_status(
            final_verifications
        )

        final_verified = VerifiedRAGAnswer(
            question=current.question,
            answer=current.answer,
            base_status=current.base_status,
            verification_status=final_verification_status,
            claims=final_claims,
            verifications=final_verifications,
            citations=citations,
            retrieved_chunks=(
                current.retrieved_chunks + additional_chunks_considered
            ),
        )
        correction = correct_verified_answer(final_verified)

        final_supported = {
            item.claim_id
            for item in final_verifications
            if item.status == "supported"
        }
        recovered = sorted(initially_unresolved & final_supported)
        unresolved = sorted(
            item.claim_id
            for item in final_verifications
            if item.status != "supported"
        )

        if correction.correction_status == "full_answer":
            status = "complete"
        elif correction.correction_status == "partial_answer":
            status = "partial"
        else:
            status = "insufficient_evidence"

        return AgenticRAGAnswer(
            question=current.question,
            initial_answer=initial.answer,
            final_answer=correction.final_answer,
            status=status,
            initial_verification_status=initial.verification_status,
            final_verification_status=final_verification_status,
            correction_status=correction.correction_status,
            rounds_used=rounds_used,
            additional_chunks_considered=additional_chunks_considered,
            recovered_claim_ids=recovered,
            unresolved_claim_ids=unresolved,
            steps=steps,
            claims=final_claims,
            verifications=final_verifications,
            citations=correction.citations,
        )
