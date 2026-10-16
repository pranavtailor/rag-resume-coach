"""Pick the LLM provider based on environment configuration.

Priority:
    1. OPENAI_API_KEY set  -> OpenAIProvider (any OpenAI-compatible endpoint)
    2. otherwise           -> StubProvider (heuristic, fully offline demo)
"""

from __future__ import annotations

import logging
import os

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .stub import StubProvider

log = logging.getLogger("rag-resume-coach")


def get_llm_provider() -> LLMProvider:
    if os.getenv("OPENAI_API_KEY"):
        log.info("OPENAI_API_KEY detected — using OpenAI-compatible provider.")
        return OpenAIProvider()
    log.warning("OPENAI_API_KEY not set — using heuristic stub provider (demo mode).")
    return StubProvider()


def active_provider_name() -> str:
    return "openai" if os.getenv("OPENAI_API_KEY") else StubProvider.name
