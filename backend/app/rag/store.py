"""Vector storage with graceful degradation.

Primary: ChromaDB (persistent, local) — the standard choice for a small RAG app.

Fallback: a dependency-free in-memory store using cosine similarity over
numpy vectors. Keeps the demo runnable without installing chromadb.

Each analysis request gets its own short-lived collection so concurrent
requests never see each other's documents.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

import numpy as np

log = logging.getLogger("rag-resume-coach")


class VectorStore(Protocol):
    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        ...

    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        """Return hits as {id, score, document, metadata}, best first."""
        ...

    def delete_collection(self) -> None:
        """Drop the underlying collection (cleanup after analysis)."""
        ...


class ChromaStore:
    def __init__(self, collection_name: str) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DIR", "./.chroma")
        )
        self._collection = self._client.get_or_create_collection(collection_name)

    def upsert(self, ids, vectors, documents, metadatas) -> None:
        self._collection.add(
            ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas
        )

    def query(self, vector, top_k):
        result = self._collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist, _id in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            result["ids"][0],
        ):
            # Chroma returns squared L2 distance; convert to a 0..1 similarity.
            hits.append(
                {
                    "id": _id,
                    "score": 1.0 / (1.0 + dist),
                    "document": doc,
                    "metadata": meta,
                }
            )
        return hits

    def delete_collection(self) -> None:
        self._client.delete_collection(self._collection.name)


class InMemoryStore:
    """Pure-python/numpy fallback: brute-force cosine similarity."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []

    def upsert(self, ids, vectors, documents, metadatas) -> None:
        matrix = np.asarray(vectors, dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._ids = ids
        self._matrix = matrix / norms
        self._documents = documents
        self._metadatas = metadatas

    def query(self, vector, top_k):
        assert self._matrix is not None, "query() called before upsert()"
        q = np.asarray(vector, dtype=np.float64)
        q = q / (np.linalg.norm(q) or 1.0)
        scores = self._matrix @ q
        order = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "id": self._ids[i],
                "score": float(scores[i]),
                "document": self._documents[i],
                "metadata": self._metadatas[i],
            }
            for i in order
        ]

    def delete_collection(self) -> None:
        self._ids, self._documents, self._metadatas = [], [], []
        self._matrix = None


def create_store(collection_name: str) -> VectorStore:
    """Prefer ChromaDB; fall back to in-memory when it isn't installed."""
    try:
        store: VectorStore = ChromaStore(collection_name)
        log.info("Using ChromaDB vector store.")
        return store
    except Exception as exc:  # ImportError or client init failure
        log.warning("ChromaDB unavailable (%s); using in-memory store.", exc)
        return InMemoryStore()


def store_name() -> str:
    try:
        import chromadb  # noqa: F401

        return "ChromaStore"
    except ImportError:
        return "InMemoryStore"
