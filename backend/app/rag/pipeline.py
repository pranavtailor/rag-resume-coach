"""Orchestrate the RAG analysis for one résumé + job posting pair.

Flow:
    1. Chunk both documents (labelled by source).
    2. Embed every chunk with the local embedding model.
    3. Index chunks in a short-lived vector collection.
    4. For each job chunk, retrieve the most similar *résumé* chunks —
       these become the "evidence" grounding the analysis.
    5. Hand the full texts plus evidence to the LLM provider, which returns
       the structured analysis (score, keywords, gaps, bullet rewrites).
    6. Tear down the collection so requests stay isolated.
"""

from __future__ import annotations

import logging
import uuid

from ..llm.factory import get_llm_provider
from ..schemas import AnalysisResponse
from .chunking import chunk_text
from .embeddings import get_embedder
from .store import create_store

log = logging.getLogger("rag-resume-coach")

# Bound the number of retrieval queries so huge job postings stay fast.
MAX_EVIDENCE_QUERIES = 10


def analyze_documents(
    resume_text: str, job_text: str, top_k: int = 5
) -> AnalysisResponse:
    embedder = get_embedder()
    provider = get_llm_provider()
    collection_name = f"analysis-{uuid.uuid4().hex[:12]}"
    store = create_store(collection_name)

    try:
        resume_chunks = chunk_text(resume_text, source="resume")
        job_chunks = chunk_text(job_text, source="job")
        all_chunks = resume_chunks + job_chunks

        vectors = embedder.embed([c.text for c in all_chunks])
        store.upsert(
            ids=[f"{c.source}-{c.index}" for c in all_chunks],
            vectors=vectors,
            documents=[c.text for c in all_chunks],
            metadatas=[{"source": c.source, "index": c.index} for c in all_chunks],
        )

        evidence = _retrieve_evidence(store, embedder, job_chunks, top_k)
        analysis = provider.analyze(resume_text, job_text, evidence)
        analysis.provider = provider.name
        analysis.evidence_chunks = evidence[:top_k]
        return analysis
    finally:
        store.delete_collection()


def _retrieve_evidence(store, embedder, job_chunks, top_k: int) -> list[str]:
    """Find résumé chunks most similar to each job chunk (deduped, ordered)."""
    seen: set[str] = set()
    evidence: list[str] = []
    for job_chunk in job_chunks[:MAX_EVIDENCE_QUERIES]:
        (query_vector,) = embedder.embed([job_chunk.text])
        for hit in store.query(query_vector, top_k=top_k):
            if hit["metadata"].get("source") != "resume":
                continue
            doc = hit["document"]
            if doc not in seen:
                seen.add(doc)
                evidence.append(doc)
    log.info("Retrieved %d evidence chunks.", len(evidence))
    return evidence
