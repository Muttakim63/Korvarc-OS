"""Web page research extractor with prompt-injection defense and untrusted content sanitization."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from korvarc.models.schemas import ResearchObservation
from korvarc.research.fetcher import safe_fetch


def sanitize_untrusted_text(text: str) -> str:
    """Sanitizes untrusted scraped content against prompt injection attempts."""
    if not text:
        return ""
    # Strip dangerous directives that attempt to hijack LLM behavior
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"(?i)system\s*:\s*",
        r"(?i)you\s+are\s+now\s+(a\s+)?",
        r"(?i)disregard\s+(the\s+)?system\s+prompt",
        r"(?i)<\|im_start\|>",
        r"(?i)<\|im_end\|>",
        r"(?i)\[INST\]",
        r"(?i)\[/INST\]",
    ]
    sanitized = text
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[BLOCKED_DIRECTIVE]", sanitized)
    return sanitized.strip()


def research_website(url: str, target_name: str = "") -> list[ResearchObservation]:
    """Extracts factual observations from a public brand or creator website."""
    observations: list[ResearchObservation] = []
    now_str = datetime.now(timezone.utc).isoformat()

    try:
        html_content = safe_fetch(url, timeout_seconds=8.0)
    except Exception as e:
        observations.append(
            ResearchObservation(
                source="Website Scraper Limitation",
                url=url,
                observation=f"Unable to fetch public website data: {str(e)}",
                evidence="HTTP fetch error / access restriction",
                retrieved_at=now_str,
                verification_status="unknown",
                confidence="low",
            )
        )
        return observations

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, and navigation tags
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()

    # Title
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if title:
        clean_title = sanitize_untrusted_text(title)
        observations.append(
            ResearchObservation(
                source="Website Title",
                url=url,
                observation=f"Page title: '{clean_title}'",
                evidence=f"<title>{clean_title}</title>",
                retrieved_at=now_str,
                verification_status="verified",
                confidence="high",
            )
        )

    # Meta description
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = sanitize_untrusted_text(desc_tag["content"].strip())
        if meta_desc:
            observations.append(
                ResearchObservation(
                    source="Meta Description",
                    url=url,
                    observation=f"Public value proposition / description: '{meta_desc}'",
                    evidence=f'meta description: "{meta_desc}"',
                    retrieved_at=now_str,
                    verification_status="verified",
                    confidence="high",
                )
            )

    # Key Headings (H1, H2)
    headings = []
    for h in soup.find_all(["h1", "h2"])[:4]:
        text = sanitize_untrusted_text(h.get_text())
        if text and len(text) > 4 and text not in headings:
            headings.append(text)

    if headings:
        heading_summary = "; ".join(headings)
        observations.append(
            ResearchObservation(
                source="Page Headings",
                url=url,
                observation=f"Core messaging and product features: {heading_summary}",
                evidence=f"H1/H2 tags: {heading_summary[:300]}",
                retrieved_at=now_str,
                verification_status="verified",
                confidence="high",
            )
        )

    # Body snippet
    body_text = soup.get_text(separator=" ", strip=True)
    body_text = " ".join(body_text.split())
    clean_body = sanitize_untrusted_text(body_text[:1200])
    if clean_body and len(clean_body) > 60:
        observations.append(
            ResearchObservation(
                source="Website Content Extraction",
                url=url,
                observation="Public web copy describing tools, platform, or developer workflows.",
                evidence=clean_body[:400] + ("..." if len(clean_body) > 400 else ""),
                retrieved_at=now_str,
                verification_status="verified",
                confidence="medium",
            )
        )

    return observations

