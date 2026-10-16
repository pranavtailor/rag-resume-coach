"""Pydantic request/response models for the RAG Résumé Coach API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str
    embedder: str
    vector_store: str


class ResumeUploadResponse(BaseModel):
    filename: str
    text: str
    char_count: int


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(min_length=50, max_length=100_000)
    job_text: str = Field(min_length=50, max_length=100_000)
    top_k: int = Field(default=5, ge=1, le=10)


class Gap(BaseModel):
    """One area where the résumé falls short of the job posting."""

    title: str
    detail: str


class BulletRewrite(BaseModel):
    """A before/after suggestion for a single résumé bullet."""

    original: str
    rewritten: str
    rationale: str


class AnalysisResponse(BaseModel):
    match_score: float = Field(ge=0, le=100)
    missing_keywords: list[str]
    gaps: list[Gap]
    bullet_rewrites: list[BulletRewrite]
    provider: str
    evidence_chunks: list[str] = Field(default_factory=list)
