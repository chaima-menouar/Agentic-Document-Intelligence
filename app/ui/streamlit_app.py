"""Streamlit UI for Agentic Document Intelligence."""

from __future__ import annotations

import base64
import json
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app.agent import AdaptiveAgenticVerifiedRAG, AgenticVerifiedRAG
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
    render_pipeline,
    status_pills,
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
    page_title="Agentic Document Intelligence V2",
    page_icon="📄",
    layout="wide",
)

apply_v2_theme()
render_hero()


def _ensure_state() -> None:
    defaults = {
        "workspace_dir": None,
        "workspace_result": None,
        "retriever": None,
        "hybrid_retriever": None,
        "reranked_retriever": None,
        "history": [],
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


def _get_verifier(mode: str):
    if mode == "V2 semantic NLI":
        return _cached_semantic_verifier()
    return CitationGroundingVerifier()


_ensure_state()

with st.sidebar:
    st.header("Configuration")
    st.info(
        "Recommended V2 demo: Agentic Verified RAG + dense BGE (validated default) "
        "+ V2 semantic NLI + V2 adaptive budgeted agent. Enable the grounded local "
        "LLM only when a local Ollama/LM Studio endpoint is running."
    )
    assistant_mode = st.selectbox(
        "Assistant mode",
        ["Classical RAG", "Verified RAG", "Verified + Corrected RAG", "Agentic Verified RAG"],
        help="Verified RAG adds claim-level evidence checks after generation.",
    )
    generator_mode = st.selectbox(
        "Generator",
        ["Offline extractive baseline", "V2 grounded local LLM"],
        help=(
            "The offline baseline is fully free. "
            "The V2 local LLM option adds citation validation, one repair "
            "attempt, and a safe extractive fallback. It works with Ollama, "
            "LM Studio, or another local OpenAI-compatible server."
        ),
    )
    local_model = ""
    local_base_url = ""
    if generator_mode == "V2 grounded local LLM":
        local_base_url = st.text_input(
            "Local endpoint",
            value="http://localhost:11434/v1",
        )
        local_model = st.text_input(
            "Model name",
            placeholder="e.g. qwen2.5:3b, llama3.2:3b, or your local model",
        )
        st.caption(
            "V2 guard: validate citations → repair once → extractive fallback."
        )

    top_k = st.slider("Top-K evidence", min_value=1, max_value=10, value=5)
    agent_policy_mode = st.selectbox(
        "Agent policy",
        ["V2 adaptive budgeted", "V1 fixed bounded"],
        index=0,
        help=(
            "V2 chooses retrieval actions from verification failure reasons, "
            "stops when no new evidence is found, and enforces a strict chunk budget."
        ),
    )
    agent_budget = st.slider(
        "Agent retrieval budget (chunks)",
        min_value=2,
        max_value=20,
        value=10,
        disabled=assistant_mode != "Agentic Verified RAG"
        or agent_policy_mode != "V2 adaptive budgeted",
    )
    retrieval_mode = st.selectbox(
        "Retrieval",
        ["V1 dense BGE + FAISS", "V2 hybrid RRF", "V2 hybrid + reranker"],
        index=0,
        help=(
            "Dense BGE remains the validated default. Hybrid retrieval combines "
            "dense semantic search with BM25 lexical search; the reranked mode adds "
            "a local cross-encoder over fused candidates."
        ),
    )
    if retrieval_mode == "V2 hybrid + reranker":
        st.caption("First reranked query may download/load the local cross-encoder.")
    verifier_mode = st.selectbox(
        "Verifier",
        ["V1 lexical", "V2 semantic NLI"],
        index=1,
        help=(
            "V2 uses a local NLI model to test semantic entailment. "
            "If the model cannot load, it automatically falls back to V1 lexical verification."
        ),
    )
    if verifier_mode == "V2 semantic NLI":
        st.caption("First use may download/load the local NLI model.")
    st.divider()
    st.subheader("V2 ingestion")
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


overview_tab, documents_tab, assistant_tab, evaluation_tab, comparison_tab, configuration_tab = st.tabs(
    ["Overview", "Documents", "Assistant", "Evaluation", "V1 vs V2", "Configuration"]
)

with overview_tab:
    render_pipeline()
    status_pills(
        [
            ("V2 release candidate", "info"),
            ("Local-first", ""),
            ("Evidence-grounded", ""),
            ("No paid API required", "gold"),
        ]
    )

    st.markdown('<div class="adi-section">Core capabilities</div>', unsafe_allow_html=True)
    cap1, cap2, cap3 = st.columns(3)
    with cap1:
        feature_card("OCR", "Document ingestion", "Text PDFs and scanned pages with local OCR, page provenance, and extraction-quality signals.")
    with cap2:
        feature_card("RAG", "Evidence retrieval", "Validated dense BGE + FAISS with optional BM25 fusion and local cross-encoder reranking.")
    with cap3:
        feature_card("NLI", "Claim verification", "Every answer can be decomposed into claims and checked against cited evidence with local semantic entailment.")

    cap4, cap5, cap6 = st.columns(3)
    with cap4:
        feature_card("AI", "Grounded generation", "Deterministic extractive baseline plus guarded local LLM generation with citation repair and safe fallback.")
    with cap5:
        feature_card("↻", "Adaptive recovery", "The agent identifies evidence failures, re-retrieves within a strict budget, and exposes its action trace.")
    with cap6:
        feature_card("A/B", "Evaluation workspace", "Inspect session behavior, benchmark V1 against V2, and compare safety, retrieval, and recovery metrics.")

    overview_result = st.session_state.get("workspace_result")
    st.markdown('<div class="adi-section">Workspace status</div>', unsafe_allow_html=True)
    if overview_result is None:
        st.info("No active corpus yet. Open Documents, upload one or more PDFs, then process the workspace.")
    else:
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Documents", len(overview_result.documents))
        o2.metric("Chunks", overview_result.total_chunks)
        o3.metric("Vectors", overview_result.index_manifest.get("vector_count", 0))
        o4.metric("OCR pages", sum(item.ocr_page_count for item in overview_result.documents))

with documents_tab:
    st.markdown('<div class="adi-section">Document workspace</div>', unsafe_allow_html=True)
    st.caption(
        "Build a provenance-preserving corpus from text PDFs or scanned pages. "
        "Every processed page stays traceable to the evidence shown later."
    )

    upload_col, ingest_col = st.columns([1.55, 1])
    with upload_col:
        uploaded_files = st.file_uploader(
            "PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload one or more English PDFs. OCR can recover scanned/text-poor pages.",
        )
    with ingest_col:
        zone_intro(
            "Ingestion pipeline",
            "Local PDF extraction → OCR fallback when needed → provenance-preserving chunks → BGE embeddings → FAISS index.",
        )
        status_pills(
            [
                ("Local OCR", "info"),
                ("Page provenance", ""),
                ("Multi-PDF", ""),
            ]
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

        st.markdown('<div class="adi-section">Inspect document & extracted evidence</div>', unsafe_allow_html=True)
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
                      style="border:1px solid rgba(98,230,255,.18);border-radius:16px;background:#0b1628;">
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
    st.subheader("Assistant")
    dense_retriever = st.session_state.get("retriever")
    if retrieval_mode == "V2 hybrid RRF":
        retriever = st.session_state.get("hybrid_retriever")
    elif retrieval_mode == "V2 hybrid + reranker":
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

        selected_document = st.selectbox(
            "Search scope",
            list(document_options.keys()),
        )
        question = st.text_area(
            "Question",
            placeholder="Ask a question about the uploaded documents...",
            height=100,
        )

        if st.button("Ask", type="primary", disabled=not question.strip()):
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
                            if agent_policy_mode == "V2 adaptive budgeted":
                                pipeline = AdaptiveAgenticVerifiedRAG(
                                    verified_rag=verified_pipeline,
                                    retriever=retriever,
                                    verifier=verifier,
                                    max_rounds=3,
                                    additional_top_k=top_k,
                                    max_total_additional_chunks=agent_budget,
                                )
                            else:
                                pipeline = AgenticVerifiedRAG(
                                    verified_rag=verified_pipeline,
                                    retriever=retriever,
                                    verifier=verifier,
                                    max_rounds=2,
                                    additional_top_k=top_k,
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



with comparison_tab:
    st.subheader("V1 vs V2 side-by-side")
    st.caption(
        "This demo uses the same offline extractive generator and the same dense "
        "BGE retriever on both sides, isolating the verification and agent-policy "
        "differences."
    )

    comparison_retriever = st.session_state.get("retriever")
    comparison_result = st.session_state.get("workspace_result")

    if comparison_retriever is None or comparison_result is None:
        st.info("Process at least one PDF in the Documents tab first.")
    else:
        comparison_documents = {"All documents": None}
        for item in comparison_result.documents:
            comparison_documents[item.filename] = item.document_id

        comparison_scope = st.selectbox(
            "Comparison search scope",
            list(comparison_documents.keys()),
            key="comparison_scope",
        )
        comparison_question = st.text_area(
            "Comparison question",
            placeholder="Ask one question to run through both V1 and V2...",
            height=100,
            key="comparison_question",
        )
        comparison_top_k = st.slider(
            "Comparison Top-K",
            min_value=1,
            max_value=10,
            value=5,
            key="comparison_top_k",
        )

        if st.button(
            "Compare V1 vs V2",
            type="primary",
            disabled=not comparison_question.strip(),
            key="compare_v1_v2_button",
        ):
            try:
                document_id = comparison_documents[comparison_scope]

                v1_generator = ExtractiveGenerator()
                v1_rag = ClassicalRAG(
                    retriever=comparison_retriever,
                    generator=v1_generator,
                )
                v1_verifier = CitationGroundingVerifier()
                v1_verified = VerifiedRAG(
                    rag=v1_rag,
                    verifier=v1_verifier,
                )
                v1_pipeline = AgenticVerifiedRAG(
                    verified_rag=v1_verified,
                    retriever=comparison_retriever,
                    verifier=v1_verifier,
                    max_rounds=2,
                    additional_top_k=comparison_top_k,
                )

                v2_generator = ExtractiveGenerator()
                v2_rag = ClassicalRAG(
                    retriever=comparison_retriever,
                    generator=v2_generator,
                )
                v2_verifier = _get_verifier("V2 semantic NLI")
                v2_verified = VerifiedRAG(
                    rag=v2_rag,
                    verifier=v2_verifier,
                )
                v2_pipeline = AdaptiveAgenticVerifiedRAG(
                    verified_rag=v2_verified,
                    retriever=comparison_retriever,
                    verifier=v2_verifier,
                    max_rounds=3,
                    additional_top_k=comparison_top_k,
                    max_total_additional_chunks=10,
                )

                with st.spinner("Running V1 and V2 on the same evidence..."):
                    v1_answer = v1_pipeline.answer(
                        comparison_question,
                        top_k=comparison_top_k,
                        document_id=document_id,
                    )
                    v2_answer = v2_pipeline.answer(
                        comparison_question,
                        top_k=comparison_top_k,
                        document_id=document_id,
                    )

                left, right = st.columns(2)

                with left:
                    st.markdown("### V1")
                    st.markdown(v1_answer.final_answer)
                    st.write(
                        "Verification:",
                        v1_answer.final_verification_status.replace("_", " ").title(),
                    )
                    st.write("Status:", v1_answer.status.replace("_", " ").title())
                    st.metric("Additional rounds", v1_answer.rounds_used)
                    st.metric(
                        "Additional chunks",
                        v1_answer.additional_chunks_considered,
                    )
                    st.caption("Verifier: lexical · Agent: fixed bounded")

                with right:
                    st.markdown("### V2")
                    st.markdown(v2_answer.final_answer)
                    st.write(
                        "Verification:",
                        v2_answer.final_verification_status.replace("_", " ").title(),
                    )
                    st.write("Status:", v2_answer.status.replace("_", " ").title())
                    st.metric("Additional rounds", v2_answer.rounds_used)
                    st.metric(
                        "Additional chunks",
                        v2_answer.additional_chunks_considered,
                    )
                    st.caption(
                        "Verifier: semantic NLI · Agent: adaptive budgeted"
                    )
                    if v2_answer.early_stop_reason:
                        st.caption(
                            "Early stop: "
                            + v2_answer.early_stop_reason.replace("_", " ")
                        )

                st.markdown("#### Comparison")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric(
                    "Round difference (V2 − V1)",
                    v2_answer.rounds_used - v1_answer.rounds_used,
                )
                col_b.metric(
                    "Chunk difference (V2 − V1)",
                    (
                        v2_answer.additional_chunks_considered
                        - v1_answer.additional_chunks_considered
                    ),
                )
                col_c.metric(
                    "V2 recovered claims",
                    len(v2_answer.recovered_claim_ids),
                )

                with st.expander("V2 adaptive trace"):
                    if not v2_answer.steps:
                        st.write("No additional retrieval was needed.")
                    for step in v2_answer.steps:
                        st.write(
                            f"Round {step.round_index} · {step.action} · "
                            f"resolved={step.resolved}"
                        )
                        st.caption(
                            f"reason={step.failure_reason or 'n/a'} · "
                            f"new_chunks={step.new_chunks} · "
                            f"support_delta={step.support_improvement:+.2f}"
                        )
                        st.caption(step.query)
            except Exception as exc:
                st.error(f"Could not run the V1/V2 comparison: {exc}")
