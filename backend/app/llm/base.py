"""The provider interface every LLM implementation must satisfy.

Adding a new provider (Anthropic, Bedrock, a local Ollama server, ...) means
writing one small class that implements ``analyze`` and registering it in
``factory.py``. Nothing else in the app changes.
"""

from __future__ import annotations

from typing import Protocol

from ..schemas import AnalysisResponse


class LLMProvider(Protocol):
    name: str

    def analyze(
        self,
        resume_text: str,
        job_text: str,
        evidence: list[str],
    ) -> AnalysisResponse:
        """Produce a structured gap analysis for the résumé/job pair.

        *evidence* holds the résumé chunks the retriever found most relevant
        to the job posting — providers should ground their analysis in it.
        """
        ...


class LLMError(RuntimeError):
    """Raised when a provider fails to produce an analysis."""
