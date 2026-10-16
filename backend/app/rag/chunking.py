"""Split documents into overlapping word-based chunks for embedding.

Word windows (rather than characters) keep chunks semantically coherent, and
the overlap preserves context that would otherwise be cut at a boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Source = Literal["resume", "job"]


@dataclass
class Chunk:
    text: str
    source: Source
    index: int


def chunk_text(
    text: str,
    source: Source,
    chunk_size: int = 120,
    overlap: int = 24,
) -> list[Chunk]:
    """Split *text* into overlapping chunks of ~*chunk_size* words."""
    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    step = max(chunk_size - overlap, 1)
    index = 0
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        chunks.append(Chunk(text=" ".join(window), source=source, index=index))
        index += 1
        if start + chunk_size >= len(words):
            break
    return chunks
