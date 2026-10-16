"""FastAPI entrypoint for the RAG Résumé Coach.

Endpoints:
    GET  /api/health   – liveness + which providers are active (no secrets)
    POST /api/resume   – upload a PDF/DOCX/TXT résumé, get back extracted text
    POST /api/analyze  – résumé text + job posting text -> structured analysis

Run locally:
    uvicorn app.main:app --reload --port 8000   # from backend/
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .llm.base import LLMError
from .llm.factory import active_provider_name
from .parsing import (
    MAX_UPLOAD_BYTES,
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text,
)
from .rag.embeddings import embedder_name
from .rag.pipeline import analyze_documents
from .rag.store import store_name
from .schemas import (
    AnalyzeRequest,
    AnalysisResponse,
    HealthResponse,
    ResumeUploadResponse,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rag-resume-coach")

app = FastAPI(
    title="RAG Résumé Coach",
    description="Upload a résumé + job posting, get a RAG-grounded gap analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "RAG Résumé Coach API — see /docs for the interactive API."}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        llm_provider=active_provider_name(),
        embedder=embedder_name(),
        vector_store=store_name(),
    )


@app.post("/api/resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    filename = file.filename or "upload"
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB).",
        )
    try:
        text = extract_text(filename, data)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log.info("Parsed résumé '%s' (%d chars).", filename, len(text))
    return ResumeUploadResponse(filename=filename, text=text, char_count=len(text))


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    try:
        return analyze_documents(
            resume_text=request.resume_text.strip(),
            job_text=request.job_text.strip(),
            top_k=request.top_k,
        )
    except LLMError as exc:
        log.exception("LLM provider failed.")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak tracebacks to the client
        log.exception("Analysis failed.")
        raise HTTPException(status_code=500, detail="Analysis failed.") from exc
