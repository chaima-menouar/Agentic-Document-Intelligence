"""Single-process API for private local/Codespaces use; no paid API required."""
from __future__ import annotations

import atexit
import json
import logging
import os
import secrets
import shutil
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent import AdaptiveAgenticVerifiedRAG
from app.rag import ClassicalRAG, ExtractiveGenerator, GroundedLocalGenerator
from app.retrieval import HybridRetriever, LocalCrossEncoderReranker, SemanticRetriever
from app.ui.workspace import build_local_workspace
from app.verification import CitationGroundingVerifier, SemanticCitationGroundingVerifier, VerifiedRAG

app = FastAPI(title="Agentic Document Intelligence", docs_url=None, redoc_url=None)
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
MAX_BYTES = 25 * 1024 * 1024


@dataclass
class Workspace:
    lock: threading.RLock = field(default_factory=threading.RLock)
    directory: Path | None = None
    result: object = None
    retriever: object = None
    history: list = field(default_factory=list)
    feedback: dict = field(default_factory=dict)
    touched: float = field(default_factory=time.monotonic)

    def clear(self):
        if self.directory:
            shutil.rmtree(self.directory, ignore_errors=True)
        self.directory = self.result = self.retriever = None
        self.history.clear()
        self.feedback.clear()


_sessions: dict[str, Workspace] = {}
_sessions_lock = threading.Lock()
_model_lock = threading.Lock()
_semantic_verifier = None


@atexit.register
def cleanup():
    for workspace in _sessions.values():
        workspace.clear()


@app.middleware("http")
async def same_origin(request: Request, call_next):
    # Browsers cannot mutate a private workspace through another website.
    if request.method in {"POST", "DELETE"} and request.url.path.startswith("/api/"):
        if request.headers.get("x-adi-request") != "1":
            return Response("Missing application request header", status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def session(request: Request, response: Response) -> Workspace:
    token = request.cookies.get("adi_session", "")
    with _sessions_lock:
        now = time.monotonic()
        # Retire idle sessions only when they have no in-flight operation.
        for key, item in list(_sessions.items()):
            if now - item.touched > 8 * 3600 and item.lock.acquire(blocking=False):
                try:
                    item.clear()
                    del _sessions[key]
                finally:
                    item.lock.release()
        if token not in _sessions:
            if len(_sessions) >= 32:
                raise HTTPException(503, "Too many active workspaces. Try again later.")
            token = secrets.token_urlsafe(32)
            _sessions[token] = Workspace()
            response.set_cookie("adi_session", token, httponly=True, samesite="strict", secure=request.url.scheme == "https")
        result = _sessions[token]
        result.touched = now
        return result


def summary(ws):
    return {
        "documents": [asdict(d) for d in ws.result.documents] if ws.result else [],
        "total_chunks": ws.result.total_chunks if ws.result else 0,
        "history": ws.history,
        "feedback": ws.feedback,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/workspace")
def workspace(ws: Workspace = Depends(session)):
    with ws.lock:
        return summary(ws)


@app.delete("/api/workspace")
def reset(ws: Workspace = Depends(session)):
    with ws.lock:
        ws.clear()
        return summary(ws)


@app.post("/api/documents")
def upload(files: list[UploadFile] = File(...), ocr: bool = Form(True), ws: Workspace = Depends(session)):
    if not 1 <= len(files) <= 10:
        raise HTTPException(400, "Choose between 1 and 10 PDFs.")
    payloads = []
    total = 0
    for item in files:
        data = item.file.read(MAX_BYTES + 1)
        total += len(data)
        if len(data) > MAX_BYTES or total > 100 * 1024 * 1024:
            raise HTTPException(413, "Maximum: 25 MB per PDF and 100 MB per upload.")
        if not (item.filename or "").lower().endswith(".pdf") or not data.startswith(b"%PDF-"):
            raise HTTPException(400, "Only valid PDF files are supported.")
        payloads.append((Path(item.filename).name, data))
    with ws.lock:
        directory = Path(tempfile.mkdtemp(prefix="adi-react-"))
        try:
            # Keep the old corpus if extraction or indexing fails.
            with _model_lock:
                result = build_local_workspace(payloads, directory, ocr_fallback=ocr)
                retriever = SemanticRetriever.load(result.index_dir)
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            logger.exception("PDF processing failed")
            raise HTTPException(422, "Could not process these PDFs. Check readable text, OCR installation, and model downloads in the terminal.")
        ws.clear()
        ws.directory, ws.result, ws.retriever = directory, result, retriever
        ws.touched = time.monotonic()
        return summary(ws)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    budget: int = Field(default=10, ge=2, le=20)
    retrieval: Literal["dense", "hybrid", "reranked"] = "dense"
    verifier: Literal["semantic", "lexical"] = "semantic"
    generator: Literal["offline", "local"] = "offline"
    model: str = Field(default="", max_length=150)


def answer_question(ws, query):
    global _semantic_verifier
    retriever = ws.retriever
    if query.retrieval != "dense":
        retriever = HybridRetriever(retriever, reranker=LocalCrossEncoderReranker() if query.retrieval == "reranked" else None)
    generator = ExtractiveGenerator() if query.generator == "offline" else GroundedLocalGenerator(
        model=query.model.strip() or None,
        base_url=os.environ.get("ADI_LOCAL_LLM_URL", "http://localhost:11434/v1"),
    )
    if query.verifier == "semantic":
        if _semantic_verifier is None:
            _semantic_verifier = SemanticCitationGroundingVerifier()
        verifier = _semantic_verifier
    else:
        verifier = CitationGroundingVerifier()
    rag = ClassicalRAG(retriever=retriever, generator=generator)
    pipeline = AdaptiveAgenticVerifiedRAG(
        verified_rag=VerifiedRAG(rag=rag, verifier=verifier), retriever=retriever,
        verifier=verifier, max_rounds=3, additional_top_k=query.top_k,
        max_total_additional_chunks=query.budget,
    )
    return pipeline.answer(query.question.strip(), top_k=query.top_k, document_id=query.document_id).model_dump(mode="json")


@app.post("/api/ask")
def ask(query: Question, ws: Workspace = Depends(session)):
    if not query.question.strip():
        raise HTTPException(400, "Enter a question.")
    with ws.lock:
        if ws.retriever is None:
            raise HTTPException(409, "Upload and process documents first.")
        ids = {d.document_id for d in ws.result.documents}
        if query.document_id is not None and query.document_id not in ids:
            raise HTTPException(404, "Document is not in this workspace.")
        started = time.perf_counter()
        try:
            with _model_lock:
                answer = answer_question(ws, query)
        except Exception:
            logger.exception("Answer generation failed")
            raise HTTPException(503, "Could not generate an answer. Check model availability and the server terminal, then retry.")
        answer["latency_seconds"] = round(time.perf_counter() - started, 2)
        answer["id"] = secrets.token_hex(8)
        answer["settings"] = query.model_dump(exclude={"question", "document_id"})
        ws.history.append(answer)
        ws.history = ws.history[-50:]
        ws.touched = time.monotonic()
        return answer


@app.get("/api/documents/{document_id}/source")
def source(document_id: str, ws: Workspace = Depends(session)):
    with ws.lock:
        doc = next((d for d in ws.result.documents if d.document_id == document_id), None) if ws.result else None
        if doc is None:
            raise HTTPException(404, "Document not found.")
        return FileResponse(ws.directory / "uploads" / doc.filename, media_type="application/pdf", filename=doc.filename, content_disposition_type="inline")


@app.get("/api/documents/{document_id}/chunks")
def chunks(document_id: str, ws: Workspace = Depends(session)):
    with ws.lock:
        if not ws.result or document_id not in {d.document_id for d in ws.result.documents}:
            raise HTTPException(404, "Document not found.")
        return [c for line in ws.result.chunks_path.read_text().splitlines() if (c := json.loads(line))["document_id"] == document_id]


class Feedback(BaseModel):
    rating: Literal["useful", "needs_review", "incorrect"]
    note: str = Field(default="", max_length=2000)


@app.post("/api/answers/{answer_id}/feedback")
def feedback(answer_id: str, data: Feedback, ws: Workspace = Depends(session)):
    with ws.lock:
        if answer_id not in {a["id"] for a in ws.history}:
            raise HTTPException(404, "Answer not found.")
        ws.feedback[answer_id] = data.model_dump()
        return {"saved": True}


# API routes take precedence; Vite assets are served on the same private port.
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="react")
else:
    @app.get("/")
    def missing_build():
        return Response("Build the React frontend first: cd frontend && npm ci && npm run build", status_code=503)
