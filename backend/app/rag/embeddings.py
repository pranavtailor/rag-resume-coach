"""Text embeddings with graceful degradation.

Primary: a local sentence-transformers model (all-MiniLM-L6-v2) — no API key,
no data leaves the machine.

Fallback: a deterministic, dependency-free hashing embedder (hashed token
n-grams, L2-normalized). Retrieval quality is lower, but the app and its demo
run anywhere, even without torch installed.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Protocol

log = logging.getLogger("rag-resume-coach")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; returns one vector per input text."""
        ...


class SentenceTransformerEmbedder:
    """Local embeddings via sentence-transformers. Loaded lazily."""

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or os.getenv(
            "RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        log.info("Loading embedding model '%s' ...", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]


class HashingEmbedder:
    """Dependency-free fallback: hashed character/token n-gram vectors."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        tokens = _TOKEN_RE.findall(text.lower())
        # Unigrams + bigrams capture both keywords and short phrases.
        return tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for feature in self._features(text):
                idx = int(hashlib.sha256(feature.encode()).hexdigest(), 16) % self.dim
                vec[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Return a cached embedder, preferring sentence-transformers."""
    global _embedder
    if _embedder is None:
        try:
            _embedder = SentenceTransformerEmbedder()
            log.info("Using sentence-transformers embeddings.")
        except Exception as exc:  # ImportError, missing torch, no model cache, ...
            log.warning("sentence-transformers unavailable (%s); using hashing fallback.", exc)
            _embedder = HashingEmbedder()
    return _embedder


def embedder_name() -> str:
    embedder = get_embedder()
    return type(embedder).__name__
