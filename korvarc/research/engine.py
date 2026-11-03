"""Unified Research Engine coordinating web, YouTube, and user-supplied factual observations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from korvarc.models.schemas import ResearchObservation, ResearchResult
from korvarc.research.web import research_website, sanitize_untrusted_text
from korvarc.research.youtube import is_youtube_url, research_youtube

# In-memory research cache to prevent redundant network requests
_RESEARCH_CACHE: dict[str, ResearchResult] = {}


class ResearchEngine:
    """Gathers available, legitimate public information and produces grounded observations."""

    @classmethod
    def research(
        cls,
        target_name: str,
        target_type: str = "influencer",
        url: Optional[str] = None,
        user_pasted_content: Optional[str] = None,
        force_refresh: bool = False,
    ) -> ResearchResult:
        cache_key = f"{target_type}:{target_name}:{url or ''}"
        if not force_refresh and cache_key in _RESEARCH_CACHE:
            return _RESEARCH_CACHE[cache_key]

        observations: list[ResearchObservation] = []
        now_str = datetime.now(timezone.utc).isoformat()
        clean_target = target_name.strip() or "Prospect"
        limitation_notes: list[str] = []

        # 1. Inspect URL if provided
        if url and url.strip():
            clean_url = url.strip()
            if is_youtube_url(clean_url):
                yt_obs = research_youtube(clean_url)
                observations.extend(yt_obs)
            else:
                web_obs = research_website(clean_url, clean_target)
                observations.extend(web_obs)
        else:
            limitation_notes.append("No public URL provided. Relying solely on user-supplied context.")

        # 2. Integrate user-pasted content / transcript
        if user_pasted_content and user_pasted_content.strip():
            clean_user_content = sanitize_untrusted_text(user_pasted_content.strip())
            snippet = clean_user_content[:400] + ("..." if len(clean_user_content) > 400 else "")
            observations.append(
                ResearchObservation(
                    source="User-Provided Notes / Transcript",
                    url=url,
                    observation="Specific content observation or transcript supplied directly by agency operator.",
                    evidence=snippet,
                    retrieved_at=now_str,
                    verification_status="user_provided",
                    confidence="high",
                )
            )

        # 3. Check for unknowns / limitations
        verified_count = sum(1 for o in observations if o.verification_status == "verified")
        user_count = sum(1 for o in observations if o.verification_status == "user_provided")

        if verified_count == 0 and user_count == 0:
            observations.append(
                ResearchObservation(
                    source="Research Limitation",
                    url=url,
                    observation="No verified public data or user observations available. Grounding is limited.",
                    evidence="Extraction unavailable; operator intervention required to supply video/website context.",
                    retrieved_at=now_str,
                    verification_status="unknown",
                    confidence="low",
                )
            )
            limitation_notes.append(
                "Automated research could not extract deep content details. Ground drafts in verified niche topics or paste video/page notes."
            )

        # 4. Extract topics and summary
        extracted_topics = cls._extract_topics(clean_target, observations)

        # Construct raw summary
        summary_lines = [f"Research dossier for {clean_target} ({target_type.title()}):"]
        for obs in observations:
            summary_lines.append(f"[{obs.verification_status.upper()}] ({obs.source}): {obs.observation}")

        result = ResearchResult(
            target_name=clean_target,
            target_type="influencer" if target_type == "influencer" else "brand",
            input_url=url,
            observations=observations,
            extracted_topics=extracted_topics,
            potential_matches=[],
            raw_summary="\n".join(summary_lines),
            limitation_notes="; ".join(limitation_notes) if limitation_notes else None,
        )

        _RESEARCH_CACHE[cache_key] = result
        return result

    @classmethod
    def _extract_topics(cls, name: str, observations: list[ResearchObservation]) -> list[str]:
        """Extracts key technical keywords from observations."""
        niche_keywords = [
            "ai", "llm", "machine learning", "deep learning", "python", "data science",
            "developer tools", "cloud", "saas", "api", "database", "devops",
            "kubernetes", "docker", "frontend", "backend", "open source", "rag",
            "vector database", "fine-tuning", "agents", "langchain", "pytorch"
        ]
        found = set()
        for obs in observations:
            combined = f"{obs.observation} {obs.evidence}".lower()
            for kw in niche_keywords:
                if kw in combined:
                    found.add(kw.title())
        if not found:
            found.add("Technical Software Engineering")
            found.add("Developer Tools")
        return sorted(list(found))

