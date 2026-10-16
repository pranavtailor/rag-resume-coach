"""Heuristic stub provider — full demo with zero API keys.

When no ``OPENAI_API_KEY`` is set, the factory falls back to this provider so
the app (and its RAG pipeline) runs end-to-end offline. The analysis is
keyword/statistics-based rather than LLM-generated, and the frontend labels
it as demo mode so nobody mistakes it for model output.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from ..schemas import AnalysisResponse, BulletRewrite, Gap

log = logging.getLogger("rag-resume-coach")

# A small curated lexicon so the stub speaks "skills" instead of raw tokens.
SKILL_LEXICON: dict[str, list[str]] = {
    "Languages": [
        "python", "java", "javascript", "typescript", "go", "rust", "c#", "c++",
        "sql", "kotlin", "scala",
    ],
    "Cloud & Infrastructure": [
        "aws", "azure", "gcp", "terraform", "kubernetes", "docker",
        "cloudformation", "lambda", "ec2", "s3",
    ],
    "AI & Data": [
        "llm", "genai", "rag", "machine learning", "nlp", "pytorch",
        "tensorflow", "langchain", "embeddings", "vector db", "prompt engineering",
    ],
    "Web & APIs": [
        "react", "fastapi", "node.js", "rest", "graphql", "next.js", "flask",
        "django",
    ],
    "DevOps & Delivery": [
        "ci/cd", "github actions", "jenkins", "monitoring", "observability",
        "splunk", "datadog",
    ],
}

STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "has", "this", "that", "from", "they", "their", "about", "into", "per",
    "who", "what", "when", "where", "which", "been", "were", "was", "with",
    "work", "team", "teams", "role", "job", "including", "across", "using",
    "use", "used", "new", "all", "can", "its", "such", "more", "than", "other",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


def _skill_hits(text: str) -> set[str]:
    """Find lexicon skills present in *text* (phrase-aware, case-insensitive).

    Uses custom word boundaries so skills still match when followed by
    periods, parentheses, slashes, etc. ("AWS.", "(RAG)", "ci/cd-pipelines"),
    and so short tokens like "go" don't match inside "ongoing".
    """
    lowered = text.lower()
    hits = set()
    for skills in SKILL_LEXICON.values():
        for skill in skills:
            pattern = rf"(?<![\w#+-]){re.escape(skill)}(?![\w#+-])"
            if re.search(pattern, lowered):
                hits.add(skill)
    return hits


def _top_terms(text: str, limit: int = 30) -> list[str]:
    """Most frequent meaningful tokens — a cheap stand-in for keywords."""
    tokens = _WORD_RE.findall(text.lower())
    counts = Counter(t for t in tokens if len(t) >= 4 and t not in STOPWORDS)
    return [term for term, _ in counts.most_common(limit)]


def _extract_bullets(resume_text: str, limit: int = 4) -> list[str]:
    bullets = []
    for line in resume_text.splitlines():
        stripped = line.strip().lstrip("•-*").strip()
        if len(stripped) > 40:  # skip headers / one-liners
            bullets.append(stripped)
        if len(bullets) >= limit:
            break
    return bullets


class StubProvider:
    """Deterministic heuristic analysis. Clearly labelled as demo output."""

    name = "stub (heuristic demo)"

    def analyze(
        self, resume_text: str, job_text: str, evidence: list[str]
    ) -> AnalysisResponse:
        resume_skills = _skill_hits(resume_text)
        job_skills = _skill_hits(job_text)
        resume_terms = set(_top_terms(resume_text))
        job_terms = _top_terms(job_text)

        missing_skills = sorted(job_skills - resume_skills)
        # De-duplicate: skip terms already named as skills.
        seen = set(missing_skills)
        missing_terms = []
        for t in job_terms:
            if t not in resume_terms and t not in seen:
                seen.add(t)
                missing_terms.append(t)
        missing_terms = missing_terms[:12]
        # Skills first (they matter more), then raw terms.
        missing_keywords = (missing_skills + missing_terms)[:12]

        overlap = (job_skills & resume_skills) | (set(job_terms) & resume_terms)
        denom = max(len(job_skills | set(job_terms)), 1)
        match_score = round(100 * len(overlap) / denom, 1)

        gaps = self._build_gaps(missing_skills)
        rewrites = self._build_rewrites(resume_text, missing_keywords)

        log.info(
            "Stub analysis: score=%.1f, %d missing keywords, %d gaps, %d rewrites.",
            match_score, len(missing_keywords), len(gaps), len(rewrites),
        )
        return AnalysisResponse(
            match_score=match_score,
            missing_keywords=missing_keywords,
            gaps=gaps,
            bullet_rewrites=rewrites,
            provider=self.name,
        )

    def _build_gaps(self, missing_skills: list[str]) -> list[Gap]:
        gaps: list[Gap] = []
        for category, skills in SKILL_LEXICON.items():
            missing = [s for s in missing_skills if s in skills]
            if missing:
                gaps.append(
                    Gap(
                        title=f"Skill gap: {category}",
                        detail=(
                            f"The posting calls for {', '.join(missing)}, which "
                            "don't appear in the résumé. Add a bullet proving "
                            "hands-on experience, or a project that covers it."
                        ),
                    )
                )
            if len(gaps) >= 5:
                break
        return gaps

    def _build_rewrites(
        self, resume_text: str, missing_keywords: list[str]
    ) -> list[BulletRewrite]:
        rewrites: list[BulletRewrite] = []
        bullets = _extract_bullets(resume_text)
        keyword = missing_keywords[0] if missing_keywords else "a key job requirement"
        for bullet in bullets[:3]:
            rewritten = (
                f"{bullet} "
                f"[Suggested angle: explicitly name '{keyword}' and quantify the "
                "outcome — e.g. users served, latency cut, or cost saved.]"
            )
            rewrites.append(
                BulletRewrite(
                    original=bullet,
                    rewritten=rewritten,
                    rationale=(
                        f"The job emphasizes '{keyword}'. Naming it directly helps "
                        "both recruiters and ATS keyword scans; a metric makes the "
                        "impact concrete."
                    ),
                )
            )
        return rewrites
