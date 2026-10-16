"""OpenAI-compatible LLM provider.

Reads configuration from the environment:
    OPENAI_API_KEY   – required; without it the factory picks the stub provider
    OPENAI_MODEL     – defaults to gpt-4o-mini
    OPENAI_BASE_URL  – optional; point at any OpenAI-compatible endpoint
                       (e.g. a local Ollama or vLLM server)

No key is ever logged or returned to clients.
"""

from __future__ import annotations

import json
import logging
import os
import re

from ..schemas import AnalysisResponse, BulletRewrite, Gap
from .base import LLMError

log = logging.getLogger("rag-resume-coach")

SYSTEM_PROMPT = """\
You are an expert technical résumé coach. Given a candidate's résumé, a job
posting, and retrieved evidence (the résumé passages most relevant to the job),
produce a structured analysis as JSON with exactly these keys:

{
  "match_score": <0-100, overall fit of résumé to job>,
  "missing_keywords": ["<skills/terms in the job but absent from the résumé>"],
  "gaps": [{"title": "<short label>", "detail": "<1-2 sentence explanation>"}],
  "bullet_rewrites": [
    {"original": "<verbatim résumé bullet>",
     "rewritten": "<improved bullet weaving in a missing keyword or metric>",
     "rationale": "<why this rewrite helps for THIS job>"}
  ]
}

Rules:
- missing_keywords: at most 12, ordered by importance to the job.
- gaps: at most 5, each tied to a real requirement in the posting.
- bullet_rewrites: 2-4 rewrites, each grounded in the candidate's actual
  experience — never invent employers, metrics, or technologies.
- Respond with JSON only, no markdown fences.
"""


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set.")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # base_url=None -> official OpenAI; otherwise any compatible endpoint.
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def analyze(
        self, resume_text: str, job_text: str, evidence: list[str]
    ) -> AnalysisResponse:
        evidence_block = "\n\n".join(f"- {chunk}" for chunk in evidence) or "(none)"
        user_prompt = (
            f"## Résumé\n{resume_text}\n\n"
            f"## Job posting\n{job_text}\n\n"
            f"## Retrieved evidence (most relevant résumé passages)\n{evidence_block}"
        )
        try:
            kwargs: dict = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            }
            # response_format is OpenAI-specific; skip it for custom endpoints.
            if not self.base_url:
                kwargs["response_format"] = {"type": "json_object"}
            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return _parse_analysis(content)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc


def _parse_analysis(content: str) -> AnalysisResponse:
    """Parse the model's JSON, tolerating markdown fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Could not parse provider response as JSON: {exc}") from exc

    try:
        return AnalysisResponse(
            match_score=max(0.0, min(100.0, float(data.get("match_score", 0)))),
            missing_keywords=[str(k) for k in data.get("missing_keywords", [])][:12],
            gaps=[Gap(**g) for g in data.get("gaps", [])][:5],
            bullet_rewrites=[BulletRewrite(**b) for b in data.get("bullet_rewrites", [])][:4],
            provider="openai",
        )
    except Exception as exc:
        raise LLMError(f"Provider response failed schema validation: {exc}") from exc
