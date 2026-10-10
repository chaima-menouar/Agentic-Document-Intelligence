"""Streamlit UI for Agentic Document Intelligence."""

from __future__ import annotations

import base64
import json
import shutil
import tempfile
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app.agent import AdaptiveAgenticVerifiedRAG
from app.rag import ClassicalRAG, ExtractiveGenerator, GroundedLocalGenerator
from app.retrieval import (
    HybridRetriever,
    LocalCrossEncoderReranker,
    SemanticRetriever,
)
from app.ui.theme import (
    apply_v2_theme,
    config_line,
    feature_card,
    render_hero,
    status_pills,
    verification_gauge,
    zone_intro,
)
from app.ui.workspace import build_local_workspace
from app.verification import (
    CitationGroundingVerifier,
    CorrectedVerifiedRAG,
    SemanticCitationGroundingVerifier,
    VerifiedRAG,
)


st.set_page_config(
    page_title="Agentic Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

active_theme = "Dark"
apply_v2_theme(active_theme)
render_hero(active_theme)


def _ensure_state() -> None:
    defaults = {
        "workspace_dir": None,
        "workspace_result": None,
        "retriever": None,
        "hybrid_retriever": None,
        "reranked_retriever": None,
        "history": [],
        "session_events": [],
        "feedback": {},
        "upload_payloads": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_workspace() -> None:
    workspace_dir = st.session_state.get("workspace_dir")
    if workspace_dir:
        shutil.rmtree(workspace_dir, ignore_errors=True)
    st.session_state.workspace_dir = None
    st.session_state.workspace_result = None
    st.session_state.retriever = None
    st.session_state.hybrid_retriever = None
    st.session_state.reranked_retriever = None
    st.session_state.history = []
    st.session_state.session_events = []
    st.session_state.feedback = {}
    st.session_state.upload_payloads = {}


def _get_generator(mode: str, model: str, base_url: str):
    if mode == "Offline extractive baseline":
        return ExtractiveGenerator()
    return GroundedLocalGenerator(
        model=model.strip() or None,
        base_url=base_url.strip() or None,
    )


@st.cache_resource(show_spinner="Loading local semantic verifier...")
def _cached_semantic_verifier():
    return SemanticCitationGroundingVerifier()


def _get_verifier(mode: str = "Semantic NLI"):
    if mode == "Lexical":
        return CitationGroundingVerifier()
    return _cached_semantic_verifier()


_ensure_state()

with st.sidebar:
    st.header("Configuration")
    st.caption("Tune answer generation, evidence retrieval, and PDF processing.")
    assistant_mode = st.selectbox(
        "Assistant mode",
        ["Agentic Verified RAG", "Verified + Corrected RAG", "Verified RAG", "Classical RAG"],
        help="Agentic Verified RAG is the recommended final mode.",
    )
    generator_mode = st.selectbox(
        "Generator",
        ["Offline extractive baseline", "Grounded local LLM"],
        help=(
            "The offline baseline is fully free. "
            "The grounded local LLM option adds citation validation, one repair "
            "attempt, and a safe extractive fallback. It works with Ollama, "
            "LM Studio, or another local OpenAI-compatible server."
        ),
    )
    local_model = ""
    local_base_url = ""
    if generator_mode == "Grounded local LLM":
        local_base_url = st.text_input(
            "Local endpoint",
            value="http://localhost:11434/v1",
        )
        local_model = st.text_input(
            "Model name",
            placeholder="e.g. qwen2.5:3b, llama3.2:3b, or your local model",
        )
        st.caption(
            "Guard: validate citations → repair once → extractive fallback."
        )

    top_k = st.slider("Top-K evidence", min_value=1, max_value=10, value=5)
    agent_policy_mode = "Adaptive budgeted"
    agent_budget = st.slider(
        "Agent retrieval budget (chunks)",
        min_value=2,
        max_value=20,
        value=10,
        disabled=assistant_mode != "Agentic Verified RAG"
        or agent_policy_mode != "Adaptive budgeted",
    )
    retrieval_mode = st.selectbox(
        "Retrieval",
        ["Dense BGE + FAISS", "Hybrid RRF", "Hybrid + reranker"],
        index=0,
        help=(
            "Dense BGE remains the validated default. Hybrid retrieval combines "
            "dense semantic search with BM25 lexical search; the reranked mode adds "
            "a local cross-encoder over fused candidates."
        ),
    )
    if retrieval_mode == "Hybrid + reranker":
        st.caption("First reranked query may download/load the local cross-encoder.")
    verifier_mode = "Semantic NLI"
    st.divider()
    st.subheader("Document ingestion")
    ocr_fallback = st.checkbox(
        "OCR scanned/text-poor pages",
        value=True,
        help="Uses local Tesseract OCR only when embedded PDF text is too sparse.",
    )
    min_text_chars = st.slider(
        "OCR trigger: minimum embedded-text characters",
        min_value=0,
        max_value=200,
        value=40,
        disabled=not ocr_fallback,
    )
    st.caption("OCR language: English (eng) · local/free")
    st.caption("Embedding model: BAAI/bge-small-en-v1.5")
    if st.button("Reset workspace", use_container_width=True):
        _reset_workspace()
        st.rerun()


documents_tab, assistant_tab, evaluation_tab, configuration_tab = st.tabs(
    ["Documents", "Assistant", "Evaluation", "Settings"]
)

with documents_tab:
    st.html('<div class="adi-section">Add your documents</div>')
    st.caption("Upload English PDFs to start. Text documents and scanned pages are supported.")
    uploaded_files = st.file_uploader(
        "PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Add one or more PDFs. Scanned pages are read with local OCR when enabled.",
        label_visibility="collapsed",
    )

    if st.button(
        "Process documents",
        type="primary",
        disabled=not uploaded_files,
    ):
        _reset_workspace()
        workspace_dir = Path(tempfile.mkdtemp(prefix="agentic-doc-intel-"))
        st.session_state.workspace_dir = str(workspace_dir)

        uploads = [(item.name, item.getvalue()) for item in uploaded_files]
        st.session_state.upload_payloads = {
            f"{index:03d}_{Path(name).name}": payload
            for index, (name, payload) in enumerate(uploads, start=1)
        }
        try:
            with st.status("Building local document workspace...", expanded=True) as status:
                st.write("Extracting text and preserving page provenance...")
                st.write("Chunking documents...")
                st.write("Building the local BGE + FAISS semantic index...")
                result = build_local_workspace(
                    uploads,
                    workspace_dir,
                    ocr_fallback=ocr_fallback,
                    min_text_chars=min_text_chars,
                    ocr_language="eng",
                )
                retriever = SemanticRetriever.load(result.index_dir)
                hybrid_retriever = HybridRetriever(retriever)
                reranked_retriever = HybridRetriever(
                    retriever,
                    reranker=LocalCrossEncoderReranker(),
                )
                st.session_state.workspace_result = result
                st.session_state.retriever = retriever
                st.session_state.hybrid_retriever = hybrid_retriever
                st.session_state.reranked_retriever = reranked_retriever
                status.update(label="Workspace ready", state="complete")
        except Exception as exc:
            _reset_workspace()
            st.error(f"Could not process the PDFs: {exc}")

    result = st.session_state.get("workspace_result")
    if result is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Documents", len(result.documents))
        col2.metric("Chunks", result.total_chunks)
        col3.metric("Vectors", result.index_manifest.get("vector_count", 0))
        col4.metric(
            "OCR pages",
            sum(item.ocr_page_count for item in result.documents),
        )

        for item in result.documents:
            with st.expander(item.filename):
                st.write("Document ID:")
                st.code(item.document_id)
                st.write(f"Pages: {item.page_count}")
                st.write(f"Chunks: {item.chunk_count}")
                st.write(f"OCR pages: {item.ocr_page_count}")
                if item.warnings:
                    for warning in item.warnings:
                        st.warning(warning)

        st.html('<div class="adi-section">Inspect document & extracted evidence</div>')
        inspection_items = {item.filename: item for item in result.documents}
        inspection_name = st.selectbox(
            "Document to inspect",
            list(inspection_items.keys()),
            key="document_inspector",
        )
        inspection_item = inspection_items[inspection_name]

        page_chunks: dict[int, list[str]] = {}
        try:
            for raw_line in result.chunks_path.read_text(encoding="utf-8").splitlines():
                payload = json.loads(raw_line)
                if payload.get("document_id") != inspection_item.document_id:
                    continue
                page_number = payload.get("page_number")
                if page_number is None:
                    continue
                page_chunks.setdefault(int(page_number), []).append(payload.get("text", ""))
        except (OSError, json.JSONDecodeError):
            page_chunks = {}

        available_pages = sorted(page_chunks) or list(range(1, inspection_item.page_count + 1))
        inspection_page = st.selectbox(
            "Page",
            available_pages,
            key="document_inspector_page",
        )

        preview_col, text_col = st.columns(2)
        with preview_col:
            zone_intro(
                "Original page",
                "Visual PDF preview for the selected page. Use it to compare the source with extracted/OCR text.",
            )
            original_payload = st.session_state.upload_payloads.get(inspection_name)
            if original_payload:
                encoded_pdf = base64.b64encode(original_payload).decode("ascii")
                components.html(
                    f"""
                    <iframe
                      src="data:application/pdf;base64,{encoded_pdf}#page={inspection_page}&toolbar=0"
                      width="100%"
                      height="520"
                      style="border:1px solid #373A40;border-radius:14px;background:#1A1B1E;">
                    </iframe>
                    """,
                    height=540,
                )
            else:
                st.info("Original PDF preview is available after processing files in this session.")

        with text_col:
            zone_intro(
                "Extracted evidence",
                "Normalized text used by retrieval. OCR-derived pages remain linked to the same page provenance.",
            )
            extracted_text = "\n\n".join(page_chunks.get(inspection_page, []))
            if extracted_text:
                st.text_area(
                    "Extracted / OCR text",
                    value=extracted_text,
                    height=480,
                    disabled=True,
                    key=f"extracted_page_{inspection_item.document_id}_{inspection_page}",
                )
            else:
                st.info("No retrieval chunk text was produced for this page.")

with assistant_tab:
    st.html('<div class="adi-section">Grounded assistant</div>')
    st.caption(
        "Ask about your documents, then inspect the cited passages and claim checks."
    )
    dense_retriever = st.session_state.get("retriever")
    if retrieval_mode == "Hybrid RRF":
        retriever = st.session_state.get("hybrid_retriever")
    elif retrieval_mode == "Hybrid + reranker":
        retriever = st.session_state.get("reranked_retriever")
    else:
        retriever = dense_retriever

    if retriever is None:
        st.info("Process at least one PDF in the Documents tab first.")
    else:
        document_options = {"All documents": None}
        result = st.session_state.workspace_result
        for item in result.documents:
            document_options[item.filename] = item.document_id

        source_zone, answer_zone, evidence_zone = st.columns([0.95, 1.7, 1.15])

        with source_zone:
            zone_intro(
                "Sources",
                "Choose the active corpus scope and keep document status visible before asking.",
            )
            selected_document = st.selectbox(
                "Search scope",
                list(document_options.keys()),
                key="assistant_search_scope",
            )
            selected_id = document_options[selected_document]
            active_docs = (
                len(result.documents)
                if selected_id is None
                else 1
            )
            st.metric("Active documents", active_docs)
            status_pills(
                [
                    (retrieval_mode, "info"),
                    ("Top-K " + str(top_k), ""),
                ]
            )
            with st.expander("Corpus documents"):
                for item in result.documents:
                    marker = "●" if selected_id in {None, item.document_id} else "○"
                    st.write(f"{marker} {item.filename}")
                    st.caption(
                        f"{item.page_count} pages · {item.chunk_count} chunks · "
                        f"{item.ocr_page_count} OCR pages"
                    )

        with answer_zone:
            zone_intro(
                "Question + answer",
                "Ask the corpus. The selected RAG mode generates only from retrieved evidence and can abstain when support is insufficient.",
            )
            question = st.text_area(
                "Question",
                placeholder="Ask a question about the uploaded documents...",
                height=132,
                key="assistant_question",
            )
            ask_requested = st.button(
                "Ask the evidence",
                type="primary",
                disabled=not question.strip(),
                use_container_width=True,
            )
            status_pills(
                [
                    (assistant_mode, "info"),
                    (verifier_mode, ""),
                    (agent_policy_mode, "gold"),
                ]
            )

        with evidence_zone:
            zone_intro(
                "Evidence",
                "Inspect the latest citations, support decisions, and verification method without leaving the assistant.",
            )
            latest_history = st.session_state.history[-1] if st.session_state.history else None
            if latest_history is None:
                st.info("Evidence will appear here after the first answer.")
            else:
                if isinstance(latest_history, tuple):
                    latest_mode, latest_answer = latest_history
                else:
                    latest_mode, latest_answer = "classical", latest_history
                latest_citations = getattr(latest_answer, "citations", [])
                latest_verifications = getattr(latest_answer, "verifications", [])
                st.metric("Citations", len(latest_citations))
                if latest_verifications:
                    supported = sum(
                        item.status == "supported"
                        for item in latest_verifications
                    )
                    verification_gauge(
                        supported / len(latest_verifications),
                        "Verified support",
                        f"{supported} of {len(latest_verifications)} claims are fully supported by cited evidence.",
                        accent="d" if supported == len(latest_verifications) else "e",
                    )
                    for verification in latest_verifications[:3]:
                        icon = {
                            "supported": "✅",
                            "needs_review": "⚠️",
                            "unsupported": "❌",
                        }.get(verification.status, "•")
                        st.caption(
                            f"{icon} {verification.claim_id} · "
                            f"{verification.verifier_method} · "
                            f"{verification.support_score:.2f}"
                        )
                elif latest_citations:
                    for citation in latest_citations[:3]:
                        page_text = (
                            f"page {citation.page_number}"
                            if citation.page_number is not None
                            else "source passage"
                        )
                        st.caption(
                            f"[{citation.label}] {page_text} · {citation.score:.3f}"
                        )

        if ask_requested:
            request_started = time.perf_counter()
            try:
                generator = _get_generator(
                    generator_mode,
                    local_model,
                    local_base_url,
                )
                rag = ClassicalRAG(
                    retriever=retriever,
                    generator=generator,
                )
                with st.spinner("Retrieving evidence and generating the answer..."):
                    if assistant_mode in {
                        "Verified RAG",
                        "Verified + Corrected RAG",
                        "Agentic Verified RAG",
                    }:
                        verifier = _get_verifier(verifier_mode)
                        verified_pipeline = VerifiedRAG(
                            rag=rag,
                            verifier=verifier,
                        )
                        if assistant_mode == "Verified + Corrected RAG":
                            pipeline = CorrectedVerifiedRAG(
                                verified_rag=verified_pipeline,
                            )
                            answer = pipeline.answer(
                                question,
                                top_k=top_k,
                                document_id=document_options[selected_document],
                            )
                            st.session_state.history.append(("corrected", answer))
                        elif assistant_mode == "Agentic Verified RAG":
                            pipeline = AdaptiveAgenticVerifiedRAG(
                                verified_rag=verified_pipeline,
                                retriever=retriever,
                                verifier=verifier,
                                max_rounds=3,
                                additional_top_k=top_k,
                                max_total_additional_chunks=agent_budget,
                            )
                            answer = pipeline.answer(
                                question,
                                top_k=top_k,
                                document_id=document_options[selected_document],
                            )
                            st.session_state.history.append(("agentic", answer))
                        else:
                            answer = verified_pipeline.answer(
                                question,
                                top_k=top_k,
                                document_id=document_options[selected_document],
                            )
                            st.session_state.history.append(("verified", answer))
                    else:
                        answer = rag.answer(
                            question,
                            top_k=top_k,
                            document_id=document_options[selected_document],
                        )
                        st.session_state.history.append(("classical", answer))

                elapsed_seconds = time.perf_counter() - request_started
                latest_mode, latest_answer = st.session_state.history[-1]
                latest_verifications = getattr(latest_answer, "verifications", [])
                st.session_state.session_events.append(
                    {
                        "mode": latest_mode,
                        "question": question,
                        "latency_seconds": elapsed_seconds,
                        "citation_count": len(getattr(latest_answer, "citations", [])),
                        "claim_count": len(latest_verifications),
                        "supported_claims": sum(
                            verification.status == "supported"
                            for verification in latest_verifications
                        ),
                        "llm_calls": getattr(generator, "last_llm_calls", 0),
                        "rounds": getattr(latest_answer, "rounds_used", 0),
                        "additional_chunks": getattr(
                            latest_answer,
                            "additional_chunks_considered",
                            0,
                        ),
                    }
                )
            except Exception as exc:
                st.error(f"Could not answer the question: {exc}")

        for history_item in reversed(st.session_state.history):
            if isinstance(history_item, tuple):
                result_mode, answer = history_item
            else:
                result_mode, answer = "classical", history_item

            with st.container(border=True):
                st.markdown(f"**Q:** {answer.question}")

                if result_mode == "agentic":
                    st.markdown(answer.final_answer)
                    st.markdown(
                        f"**Agentic result:** {answer.status.replace('_', ' ').title()}"
                    )
                    st.markdown(
                        "**Verification:** "
                        + answer.final_verification_status.replace("_", " ").title()
                    )
                    budget_text = (
                        f" · budget: {answer.retrieval_budget}"
                        if answer.retrieval_budget is not None
                        else ""
                    )
                    st.caption(
                        f"Additional retrieval rounds: {answer.rounds_used} · "
                        f"chunks considered: {answer.additional_chunks_considered}"
                        f"{budget_text}"
                    )
                    if answer.budget_exhausted:
                        st.warning("Adaptive retrieval budget exhausted.")
                    if answer.early_stop_reason:
                        st.caption(
                            "Early-stop reason: "
                            + answer.early_stop_reason.replace("_", " ")
                        )
                    if answer.recovered_claim_ids:
                        st.success(
                            "Recovered claims: "
                            + ", ".join(answer.recovered_claim_ids)
                        )
                    if answer.unresolved_claim_ids:
                        st.warning(
                            "Still unresolved: "
                            + ", ".join(answer.unresolved_claim_ids)
                        )
                    if answer.steps:
                        with st.expander("Agentic retrieval trace"):
                            for step in answer.steps:
                                st.write(
                                    f"Round {step.round_index} · {step.claim_id} · "
                                    f"score {step.support_score:.2f} · "
                                    f"resolved={step.resolved}"
                                )
                                st.caption(
                                    f"action={step.action} · "
                                    f"failure={step.failure_reason or 'n/a'} · "
                                    f"new_chunks={step.new_chunks} · "
                                    f"improvement={step.support_improvement:+.2f}"
                                )
                                st.caption(step.query)
                elif result_mode == "corrected":
                    st.markdown(answer.final_answer)
                    correction_label = answer.correction_status.replace("_", " ").title()
                    verification_label = answer.verification_status.replace("_", " ").title()
                    st.markdown(f"**Correction:** {correction_label}")
                    st.markdown(f"**Verification:** {verification_label}")
                    if answer.removed_claim_ids:
                        st.caption(
                            "Removed non-supported claims: "
                            + ", ".join(answer.removed_claim_ids)
                        )
                else:
                    base_status = (
                        answer.base_status
                        if result_mode == "verified"
                        else answer.status
                    )

                    if base_status == "insufficient_evidence":
                        st.warning(answer.answer)
                    elif base_status == "uncited_answer":
                        st.warning(answer.answer)
                        st.caption(
                            "The generator returned an answer without a valid citation."
                        )
                    else:
                        st.markdown(answer.answer)

                if result_mode in {"verified", "corrected", "agentic"}:
                    if result_mode == "verified":
                        status_label = (
                            answer.verification_status.replace("_", " ").title()
                        )
                        st.markdown(f"**Verification:** {status_label}")
                    for verification in answer.verifications:
                        icon = {
                            "supported": "✅",
                            "needs_review": "⚠️",
                            "unsupported": "❌",
                        }.get(verification.status, "•")
                        with st.expander(
                            f"{icon} {verification.claim_id} · "
                            f"{verification.status} · "
                            f"{verification.support_score:.2f}"
                        ):
                            st.write(verification.claim_text)
                            st.caption(verification.reason)
                            st.write(f"Verifier: {verification.verifier_method}")
                            if verification.lexical_support_score is not None:
                                st.write(
                                    "Lexical score: "
                                    f"{verification.lexical_support_score:.2f}"
                                )
                            if verification.semantic_entailment_score is not None:
                                st.write(
                                    "Semantic entailment: "
                                    f"{verification.semantic_entailment_score:.2f}"
                                )
                            if verification.evidence_labels:
                                st.write(
                                    "Evidence: "
                                    + ", ".join(
                                        f"[{label}]"
                                        for label in verification.evidence_labels
                                    )
                                )

                if answer.citations:
                    st.markdown("**Sources**")
                    for citation in answer.citations:
                        location = []
                        if citation.page_number is not None:
                            location.append(f"page {citation.page_number}")
                        if citation.section:
                            location.append(citation.section)
                        location_text = " · ".join(location) or "source passage"
                        with st.expander(
                            f"[{citation.label}] {location_text} · score {citation.score:.3f}"
                        ):
                            st.write(citation.text)
                            st.caption(
                                f"document={citation.document_id} | chunk={citation.chunk_id}"
                            )
                            retrieval_kind = citation.metadata.get("retrieval_mode")
                            if retrieval_kind:
                                st.write(f"Retrieval: {retrieval_kind}")
                                details = []
                                for key, label in (
                                    ("dense_score", "dense"),
                                    ("sparse_score", "sparse"),
                                    ("fusion_score", "fusion"),
                                    ("rerank_score", "rerank"),
                                ):
                                    value = citation.metadata.get(key)
                                    if value is not None:
                                        details.append(f"{label}={value:.3f}")
                                if details:
                                    st.caption(" · ".join(details))



with evaluation_tab:
    st.html('<div class="adi-section">Evaluation & action log</div>')
    st.caption(
        "Monitor the current session alongside the validated release benchmark and live assistant behavior."
    )

    session_history = st.session_state.history
    session_events = st.session_state.session_events
    session_queries = len(session_history)
    session_citations = 0
    session_claims = 0
    session_supported = 0
    session_rounds = 0
    session_extra_chunks = 0

    for history_item in session_history:
        if isinstance(history_item, tuple):
            item_mode, item_answer = history_item
        else:
            item_mode, item_answer = "classical", history_item
        session_citations += len(getattr(item_answer, "citations", []))
        verifications = getattr(item_answer, "verifications", [])
        session_claims += len(verifications)
        session_supported += sum(
            verification.status == "supported"
            for verification in verifications
        )
        if item_mode == "agentic":
            session_rounds += getattr(item_answer, "rounds_used", 0)
            session_extra_chunks += getattr(
                item_answer,
                "additional_chunks_considered",
                0,
            )

    st.html('<div class="adi-section">Live session</div>')
    live1, live2, live3, live4 = st.columns(4)
    live1.metric("Questions", session_queries)
    live2.metric("Citations", session_citations)
    live3.metric(
        "Supported claims",
        f"{session_supported}/{session_claims}" if session_claims else "—",
    )
    live4.metric("Agent extra chunks", session_extra_chunks)

    avg_latency = (
        sum(event["latency_seconds"] for event in session_events) / len(session_events)
        if session_events
        else 0.0
    )
    total_llm_calls = sum(event["llm_calls"] for event in session_events)
    perf1, perf2, perf3 = st.columns(3)
    perf1.metric(
        "Average response time",
        f"{avg_latency:.2f}s" if session_events else "—",
    )
    perf2.metric("Local LLM calls", total_llm_calls)
    perf3.metric("Human ratings", len(st.session_state.feedback))

    st.html('<div class="adi-section">Validated release benchmark</div>')
    bench1, bench2, bench3, bench4 = st.columns(4)
    bench1.metric("Citation precision", "100%", "high precision")
    bench2.metric("Verifier accuracy", "66.7%", "semantic check")
    bench3.metric("Safe abstention", "100%", "maintained")
    bench4.metric("Unsupported rounds", "2.0", "bounded")

    eval_left, eval_right = st.columns(2)
    with eval_left:
        st.html("""
            <div class="adi-benchmark">
              <strong style="color:#eaf7ff">Retrieval decision</strong><br>
              Full QASPER Recall@5 keeps dense BGE at <strong>66.10%</strong>,
              so dense retrieval remains the validated default for the release.
            </div>
            """)
        st.html("""
            <div class="adi-benchmark">
              <strong style="color:#eaf7ff">Reranker signal</strong><br>
              On the matched 50-question sample, dense Recall@5 was
              <strong>70%</strong> and hybrid + local reranker reached
              <strong>74%</strong>.
            </div>
            """)

    with eval_right:
        st.html("""
            <div class="adi-benchmark">
              <strong style="color:#eaf7ff">Adaptive agent</strong><br>
              Recoverable-claim recovery reaches <strong>90%</strong>, while
              unsupported cases stay bounded at about <strong>2 rounds / 6 chunks</strong>.
            </div>
            """)
        st.html("""
            <div class="adi-benchmark">
              <strong style="color:#eaf7ff">Release principle</strong><br>
              The final interface exposes the strongest validated configuration
              while keeping safe fallbacks inside the pipeline.
            </div>
            """)

    st.html('<div class="adi-section">Recent search / verification activity</div>')
    if not session_history:
        st.info("Run a question in Assistant to populate the action log.")
    else:
        for index, history_item in enumerate(reversed(session_history[-5:]), start=1):
            if isinstance(history_item, tuple):
                item_mode, item_answer = history_item
            else:
                item_mode, item_answer = "classical", history_item
            with st.expander(
                f"{index}. {item_mode.replace('_', ' ').title()} · {item_answer.question}"
            ):
                final_text = getattr(
                    item_answer,
                    "final_answer",
                    getattr(item_answer, "answer", ""),
                )
                st.write(final_text)
                event_position = len(session_history) - index
                event = (
                    session_events[event_position]
                    if 0 <= event_position < len(session_events)
                    else None
                )
                event_suffix = (
                    f" · latency={event['latency_seconds']:.2f}s · "
                    f"llm_calls={event['llm_calls']}"
                    if event is not None
                    else ""
                )
                st.caption(
                    f"citations={len(getattr(item_answer, 'citations', []))} · "
                    f"verification={getattr(item_answer, 'final_verification_status', getattr(item_answer, 'verification_status', 'n/a'))}"
                    + event_suffix
                )
                steps = getattr(item_answer, "steps", [])
                for step in steps:
                    st.write(
                        f"Round {step.round_index} · {step.action} · "
                        f"new chunks={step.new_chunks} · resolved={step.resolved}"
                    )
                    st.caption(step.query)

    st.html('<div class="adi-section">Human evaluation</div>')
    if not session_history:
        st.info("Ask at least one question before adding human feedback.")
    else:
        feedback_index = len(session_history) - 1
        feedback_entry = st.session_state.feedback.get(feedback_index, {})
        feedback_col, note_col = st.columns([1, 1.5])
        with feedback_col:
            rating_options = [
                "Not rated",
                "Supported & useful",
                "Needs review",
                "Incorrect",
            ]
            default_rating = feedback_entry.get("rating", "Not rated")
            feedback_rating = st.selectbox(
                "Latest-answer rating",
                rating_options,
                index=rating_options.index(default_rating),
                key=f"latest_human_rating_{feedback_index}",
            )
        with note_col:
            feedback_note = st.text_input(
                "Reviewer note",
                value=feedback_entry.get("note", ""),
                placeholder="Optional note about answer quality, citation quality, or missing evidence.",
                key=f"latest_human_note_{feedback_index}",
            )
        if st.button("Save human evaluation", key="save_human_evaluation"):
            st.session_state.feedback[feedback_index] = {
                "rating": feedback_rating,
                "note": feedback_note,
            }
            st.success("Human evaluation saved for the latest answer.")


with configuration_tab:
    st.html('<div class="adi-section">Configuration workspace</div>')
    st.caption(
        "Open the sidebar using the top-left arrow to change these settings."
    )

    cfg_left, cfg_right = st.columns(2)
    with cfg_left:
        st.markdown("### Active pipeline")
        config_html = "".join(
            [
                config_line("Visual theme", "Dark gold"),
                config_line("Assistant mode", assistant_mode),
                config_line("Generator", generator_mode),
                config_line("Retrieval", retrieval_mode),
                config_line("Verifier", verifier_mode),
                config_line("Top-K evidence", str(top_k)),
                config_line("Chunk size", "220 words"),
                config_line("Chunk overlap", "40 words"),
                config_line("Prompt contract", "evidence-only + citations"),
                config_line("Agent policy", agent_policy_mode),
                config_line(
                    "Max retrieval rounds",
                    "3 adaptive",
                ),
                config_line(
                    "Agent chunk budget",
                    str(agent_budget)
                    if assistant_mode == "Agentic Verified RAG"
                    else "not active",
                ),
            ]
        )
        st.html(f'<div class="adi-card">{config_html}</div>')

    with cfg_right:
        st.markdown("### Ingestion & models")
        ingestion_html = "".join(
            [
                config_line("OCR fallback", "enabled" if ocr_fallback else "disabled"),
                config_line("OCR language", "English · eng"),
                config_line(
                    "OCR trigger",
                    f"< {min_text_chars} embedded-text chars"
                    if ocr_fallback
                    else "not active",
                ),
                config_line("Embedding model", "BAAI/bge-small-en-v1.5"),
                config_line("Vector index", "FAISS"),
                config_line(
                    "Corpus state",
                    (
                        f"{len(st.session_state.workspace_result.documents)} active document(s)"
                        if st.session_state.get("workspace_result") is not None
                        else "no active corpus"
                    ),
                ),
                config_line("Paid external API", "not required"),
            ]
        )
        st.html(f'<div class="adi-card">{ingestion_html}</div>')

    st.html('<div class="adi-section">Mode guide</div>')
    guide1, guide2, guide3 = st.columns(3)
    with guide1:
        feature_card(
            "A",
            "Classical RAG",
            "Retrieve evidence, generate an answer, and expose citations. Best for the simplest baseline comparison.",
            accent="b",
        )
    with guide2:
        feature_card(
            "B",
            "Verified RAG",
            "Adds claim-level evidence checks and can remove unsupported claims in corrected mode.",
            accent="c",
        )
    with guide3:
        feature_card(
            "C",
            "Agentic Verified RAG",
            "Adds failure-aware bounded retrieval, recovery traces, early stopping, and a strict evidence budget.",
            accent="d",
        )

    st.html('<div class="adi-section">Recommended release-demo configuration</div>')
    status_pills(
        [
            ("Agentic Verified RAG", "info"),
            ("Dense BGE + FAISS", ""),
            ("Semantic NLI", ""),
            ("Adaptive budgeted", "gold"),
            ("OCR enabled", "info"),
        ]
    )
    st.caption(
        "The offline extractive generator is recommended for the single final release test so the result does not depend on a separately running local LLM server."
    )
