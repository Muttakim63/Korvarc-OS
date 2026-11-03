"""YouTube video and channel research with legitimate public endpoints and transparent limitations."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlparse

from korvarc.models.schemas import ResearchObservation
from korvarc.research.fetcher import safe_fetch


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return "youtube.com" in lowered or "youtu.be" in lowered


def extract_youtube_video_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")
    if "youtube.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        match = re.search(r"/(?:embed|v|shorts)/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)
    return None


def research_youtube(url: str) -> list[ResearchObservation]:
    """Retrieves verified public metadata from YouTube using public oEmbed.
    
    Adheres strictly to the rule: Never fabricate video moments, timestamps, quotes, or product claims.
    """
    observations: list[ResearchObservation] = []
    now_str = datetime.now(timezone.utc).isoformat()

    # Step 1: Use YouTube official public oEmbed
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        raw_json = safe_fetch(oembed_url, timeout_seconds=6.0)
        data = json.loads(raw_json)

        title = data.get("title", "").strip()
        author_name = data.get("author_name", "").strip()
        author_url = data.get("author_url", "").strip()

        if title:
            observations.append(
                ResearchObservation(
                    source="YouTube Official oEmbed",
                    url=url,
                    observation=f"Published video title: '{title}' by creator '{author_name}'.",
                    evidence=f"oEmbed Title: {title} | Author: {author_name}",
                    retrieved_at=now_str,
                    verification_status="verified",
                    confidence="high",
                )
            )

        if author_url:
            observations.append(
                ResearchObservation(
                    source="YouTube Channel Link",
                    url=author_url,
                    observation=f"Creator verified channel: {author_name} ({author_url}).",
                    evidence=f"Channel URL: {author_url}",
                    retrieved_at=now_str,
                    verification_status="verified",
                    confidence="high",
                )
            )

    except Exception as e:
        observations.append(
            ResearchObservation(
                source="YouTube Research Limitation",
                url=url,
                observation="Could not verify YouTube metadata via public oEmbed endpoint.",
                evidence=str(e),
                retrieved_at=now_str,
                verification_status="unknown",
                confidence="low",
            )
        )

    # Step 2: Note transcript limitations honestly
    observations.append(
        ResearchObservation(
            source="YouTube Transcript Protocol",
            url=url,
            observation="Full video transcript requires creator permission, user input, or YouTube Data API credentials.",
            evidence="Per Korvarc OS rules: No automated fabrication of timestamps, video moments, or quotes.",
            retrieved_at=now_str,
            verification_status="unknown",
            confidence="high",
        )
    )

    return observations

