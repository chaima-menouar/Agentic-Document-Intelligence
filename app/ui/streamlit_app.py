"""Streamlit UI for Agentic Document Intelligence."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import streamlit as st

from app.agent import AgenticVerifiedRAG
from app.rag import ClassicalRAG, ExtractiveGenerator, OpenAICompatibleGenerator
from app.retrieval import SemanticRetriever
from app.ui.workspace import build_local_workspace
from app.verification import (
    CitationGroundingVerifier,
    CorrectedVerifiedRAG,
    VerifiedRAG,
)


st.set_page_config(
    page_title="Agentic Document Intelligence",
    page_icon="📄",
    layout="wide",
)

st.title("Agentic Document Intelligence")
st.caption("Local-first document QA with semantic retrieval and inspectable citations.")


def _ensure_state() -> None:
    defaults = {
        "workspace_dir": None,
        "workspace_result": None,
        "retriever": None,
        "history": [],
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
    st.session_state.history = []


def _get_generator(mode: str, model: str, base_url: str):
    if mode == "Offline extractive baseline":
        return ExtractiveGenerator()
    return OpenAICompatibleGenerator(
        model=model.strip() or None,
        base_url=base_url.strip() or None,
    )


_ensure_state()

with st.sidebar:
    st.header("Configuration")
    assistant_mode = st.selectbox(
        "Assistant mode",
        ["Classical RAG", "Verified RAG", "Verified + Corrected RAG", "Agentic Verified RAG"],
        help="Verified RAG adds claim-level evidence checks after generation.",
    )
    generator_mode = st.selectbox(
        "Generator",
        ["Offline extractive baseline", "Local OpenAI-compatible LLM"],
        help=(
            "The offline baseline is fully free. "
            "The local LLM option is intended for Ollama, LM Studio, "
            "or another local OpenAI-compatible server."
        ),
    )
    local_model = ""
    local_base_url = ""
    if generator_mode == "Local OpenAI-compatible LLM":
        local_base_url = st.text_input(
            "Local endpoint",
            value="http://localhost:11434/v1",
        )
        local_model = st.text_input(
            "Model name",
            placeholder="Your local model name",
        )

    top_k = st.slider("Top-K evidence", min_value=1, max_value=10, value=5)
    st.caption("Embedding model: BAAI/bge-small-en-v1.5")
    if st.button("Reset workspace", use_container_width=True):
        _reset_workspace()
        st.rerun()


documents_tab, assistant_tab = st.tabs(["Documents", "Assistant"])

with documents_tab:
    st.subheader("Documents")
    st.write(
        "Upload one or more English text-based PDFs. "
        "V1 does not support OCR for scanned PDFs."
    )

    uploaded_files = st.file_uploader(
        "PDF files",
        type=["pdf"],
        accept_multiple_files=True,
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
        try:
            with st.status("Building local document workspace...", expanded=True) as status:
                st.write("Extracting text and preserving page provenance...")
                st.write("Chunking documents...")
                st.write("Building the local BGE + FAISS semantic index...")
                result = build_local_workspace(uploads, workspace_dir)
                retriever = SemanticRetriever.load(result.index_dir)
                st.session_state.workspace_result = result
                st.session_state.retriever = retriever
                status.update(label="Workspace ready", state="complete")
        except Exception as exc:
            _reset_workspace()
            st.error(f"Could not process the PDFs: {exc}")

    result = st.session_state.get("workspace_result")
    if result is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Documents", len(result.documents))
        col2.metric("Chunks", result.total_chunks)
        col3.metric("Vectors", result.index_manifest.get("vector_count", 0))

        for item in result.documents:
            with st.expander(item.filename):
                st.write("Document ID:")
                st.code(item.document_id)
                st.write(f"Pages: {item.page_count}")
                st.write(f"Chunks: {item.chunk_count}")
                if item.warnings:
                    for warning in item.warnings:
                        st.warning(warning)

with assistant_tab:
    st.subheader("Assistant")
    retriever = st.session_state.get("retriever")

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
                        verifier = CitationGroundingVerifier()
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
                    st.caption(
                        f"Additional retrieval rounds: {answer.rounds_used} · "
                        f"chunks considered: {answer.additional_chunks_considered}"
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
