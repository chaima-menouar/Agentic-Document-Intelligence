"""V2 adaptive agentic retrieval with failure-aware actions and a strict budget."""

from __future__ import annotations

from app.models import (
    AgenticRAGAnswer,
    AgenticRetrievalStep,
    AnswerCitation,
    VerifiedRAGAnswer,
)
from app.verification import correct_verified_answer

from .policy import AdaptiveRetrievalPolicy


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


class AdaptiveAgenticVerifiedRAG:
    """Failure-aware V2 agent with bounded retrieval and early stopping."""

    def __init__(
        self,
        *,
        verified_rag,
        retriever,
        verifier,
        policy: AdaptiveRetrievalPolicy | None = None,
        max_rounds: int = 3,
        additional_top_k: int = 5,
        max_total_additional_chunks: int = 12,
    ) -> None:
        if max_rounds <= 0:
            raise ValueError("max_rounds must be greater than zero.")
        if additional_top_k <= 0:
            raise ValueError("additional_top_k must be greater than zero.")
        if max_total_additional_chunks <= 0:
            raise ValueError(
                "max_total_additional_chunks must be greater than zero."
            )

        self.verified_rag = verified_rag
        self.retriever = retriever
        self.verifier = verifier
        self.policy = policy or AdaptiveRetrievalPolicy()
        self.max_rounds = max_rounds
        self.additional_top_k = additional_top_k
        self.max_total_additional_chunks = max_total_additional_chunks

    def _retrieve(
        self,
        query: str,
        *,
        document_id: str | None,
        top_k: int,
    ):
        if document_id:
            return self.retriever.search_many_scoped(
                [query],
                [document_id],
                top_k=top_k,
            )[0]
        return self.retriever.search(query, top_k=top_k)

    @staticmethod
    def _last_claim_step(steps, claim_id: str):
        for step in reversed(steps):
            if step.claim_id == claim_id:
                return step
        return None

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
        budget_exhausted = False
        early_stop_reason: str | None = None

        # If generation produced no claims, first broaden the original question.
        if not current.claims:
            for round_index in range(1, self.max_rounds + 1):
                remaining = (
                    self.max_total_additional_chunks
                    - additional_chunks_considered
                )
                if remaining <= 0:
                    budget_exhausted = True
                    early_stop_reason = "retrieval_budget_exhausted"
                    break

                rounds_used = round_index
                retry_top_k = min(
                    top_k + round_index * self.additional_top_k,
                    top_k + remaining,
                )
                retry = self.verified_rag.answer(
                    question,
                    top_k=retry_top_k,
                    document_id=document_id,
                )
                added = max(
                    0,
                    retry.retrieved_chunks - current.retrieved_chunks,
                )
                added = min(added, remaining)
                additional_chunks_considered += added

                score = max(
                    (item.support_score for item in retry.verifications),
                    default=0.0,
                )
                resolved = bool(retry.claims)
                no_new_evidence = added == 0 and not resolved
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
                        action="broaden_answer_evidence",
                        failure_reason="no_claims",
                        support_score_before=0.0,
                        support_improvement=score,
                        new_chunks=added,
                        stopped_early=no_new_evidence,
                    )
                )
                current = retry

                if resolved:
                    break
                if no_new_evidence:
                    early_stop_reason = "no_new_evidence"
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
                retrieval_budget=self.max_total_additional_chunks,
                budget_exhausted=budget_exhausted,
                early_stop_reason=early_stop_reason,
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
        stopped_claim_ids: set[str] = set()

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
                and claim_id not in stopped_claim_ids
            ]
            if not unresolved_claims:
                break

            rounds_used = round_index
            for claim_position, claim in enumerate(unresolved_claims, start=1):
                verification_before = verification_by_id[claim.claim_id]
                previous_step = self._last_claim_step(steps, claim.claim_id)
                decision = self.policy.decide(
                    question=question,
                    claim=claim,
                    verification=verification_before,
                    round_index=round_index,
                    previous_step=previous_step,
                )

                if decision.stop:
                    stopped_claim_ids.add(claim.claim_id)
                    early_stop_reason = decision.failure_reason
                    steps.append(
                        AgenticRetrievalStep(
                            round_index=round_index,
                            claim_id=claim.claim_id,
                            query=decision.query,
                            retrieved_labels=[],
                            support_score=verification_before.support_score,
                            resolved=False,
                            action=decision.action,
                            failure_reason=decision.failure_reason,
                            support_score_before=verification_before.support_score,
                            support_improvement=0.0,
                            new_chunks=0,
                            stopped_early=True,
                        )
                    )
                    continue

                remaining = (
                    self.max_total_additional_chunks
                    - additional_chunks_considered
                )
                if remaining <= 0:
                    budget_exhausted = True
                    early_stop_reason = "retrieval_budget_exhausted"
                    stopped_claim_ids.add(claim.claim_id)
                    steps.append(
                        AgenticRetrievalStep(
                            round_index=round_index,
                            claim_id=claim.claim_id,
                            query=decision.query,
                            retrieved_labels=[],
                            support_score=verification_before.support_score,
                            resolved=False,
                            action="stop_budget_exhausted",
                            failure_reason="retrieval_budget_exhausted",
                            support_score_before=verification_before.support_score,
                            support_improvement=0.0,
                            new_chunks=0,
                            stopped_early=True,
                        )
                    )
                    continue

                retrieve_k = min(self.additional_top_k, remaining)
                hits = self._retrieve(
                    decision.query,
                    document_id=document_id,
                    top_k=retrieve_k,
                )
                additional_chunks_considered += len(hits)

                new_labels: list[str] = []
                new_chunks = 0
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
                                metadata=dict(hit.metadata),
                            )
                        )
                        new_chunks += 1
                    new_labels.append(label)

                updated_claim = claim.model_copy(
                    update={
                        "citation_labels": _unique_labels(
                            claim.citation_labels + new_labels
                        )
                    }
                )
                claims_by_id[claim.claim_id] = updated_claim
                verification_after = self.verifier.verify(
                    [updated_claim],
                    citations,
                )[0]
                verification_by_id[claim.claim_id] = verification_after

                improvement = (
                    verification_after.support_score
                    - verification_before.support_score
                )
                resolved = verification_after.status == "supported"
                no_new_evidence = new_chunks == 0 and not resolved
                if no_new_evidence:
                    stopped_claim_ids.add(claim.claim_id)
                    early_stop_reason = "no_new_evidence"

                steps.append(
                    AgenticRetrievalStep(
                        round_index=round_index,
                        claim_id=claim.claim_id,
                        query=decision.query,
                        retrieved_labels=new_labels,
                        support_score=verification_after.support_score,
                        resolved=resolved,
                        action=decision.action,
                        failure_reason=decision.failure_reason,
                        support_score_before=verification_before.support_score,
                        support_improvement=improvement,
                        new_chunks=new_chunks,
                        stopped_early=no_new_evidence,
                    )
                )

                if (
                    additional_chunks_considered
                    >= self.max_total_additional_chunks
                ):
                    budget_exhausted = True

            if all(
                item.status == "supported"
                for item in verification_by_id.values()
            ):
                break
            if budget_exhausted:
                early_stop_reason = (
                    early_stop_reason or "retrieval_budget_exhausted"
                )
                break
            if all(
                claim_id in stopped_claim_ids
                or verification_by_id[claim_id].status == "supported"
                for claim_id in verification_by_id
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
                initial.retrieved_chunks + additional_chunks_considered
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
            retrieval_budget=self.max_total_additional_chunks,
            budget_exhausted=budget_exhausted,
            early_stop_reason=early_stop_reason,
            recovered_claim_ids=recovered,
            unresolved_claim_ids=unresolved,
            steps=steps,
            claims=final_claims,
            verifications=final_verifications,
            citations=correction.citations,
        )
