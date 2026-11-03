"""Abstract base class and validation utilities for AI providers."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from korvarc.config import AppConfig
from korvarc.database.connection import get_db_session
from korvarc.database.schema import ApiCostLog
from korvarc.models.schemas import EmailGenerationResult, GenerationRequest, ResearchResult


class BaseAIProvider(ABC):
    """Abstract interface implemented by OpenAI and Anthropic adapters."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key
        self.default_model = default_model

    @abstractmethod
    def generate_email(
        self,
        request: GenerationRequest,
        research: ResearchResult,
        active_rules: List[str],
        approved_examples: List[dict],
        rejected_lessons: List[dict],
    ) -> EmailGenerationResult:
        """Generates email options and grounding analysis using the configured LLM."""
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Tests whether the API key is active and authorized."""
        pass

    @abstractmethod
    def estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Estimates cost in USD for a given model and token count."""
        pass

    def record_cost(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Persists API usage metrics to the database."""
        try:
            with get_db_session() as session:
                log = ApiCostLog(
                    provider=provider,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    estimated_cost_usd=cost_usd,
                    success=success,
                    error_message=error,
                )
                session.add(log)
        except Exception:
            pass  # Ensure logging failure doesn't crash user workflow

    def clean_json_response(self, text: str) -> dict:
        """Extracts JSON from response, stripping markdown code blocks if present."""
        clean = text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
            clean = clean.strip()
        return json.loads(clean)

    def validate_and_postprocess(
        self, raw_dict: dict, request: GenerationRequest
    ) -> EmailGenerationResult:
        """Ensures generated result strictly matches schema and checks placeholder warnings."""
        # Ensure subject lines has at least 3 elements
        subjects = raw_dict.get("subject_lines", [])
        if not isinstance(subjects, list) or len(subjects) < 3:
            default_sub = f"Commercial sponsorship opportunity for {request.entity_name}"
            subjects = [
                subjects[0] if len(subjects) > 0 else default_sub,
                subjects[1] if len(subjects) > 1 else f"Quick question regarding {request.entity_name}",
                subjects[2] if len(subjects) > 2 else f"Potential sponsor matches for your audience",
            ][:3]
        raw_dict["subject_lines"] = subjects[:3]

        primary_draft = raw_dict.get("primary_draft", "").strip()

        # Word count calculation
        words = [w for w in primary_draft.split() if w.strip()]
        actual_wc = len(words)
        raw_dict["word_count"] = actual_wc

        # Check for placeholder warnings
        warnings = raw_dict.get("unsupported_claims_warnings", [])
        if not isinstance(warnings, list):
            warnings = []

        placeholder_issues = AppConfig.check_for_placeholder_warnings(primary_draft)
        for issue in placeholder_issues:
            if issue not in warnings:
                warnings.append(issue)

        # Grounding check for brand sponsorships
        lower_body = primary_draft.lower()
        if "secured budget" in lower_body or "confirmed partner" in lower_body:
            warnings.append(
                "Agency Compliance Warning: Claiming secured budgets or confirmed partners without formal contracts violates Korvarc standards."
            )

        raw_dict["unsupported_claims_warnings"] = warnings

        # Fallback fields if missing
        raw_dict.setdefault("personalization_explanation", "Focuses on technical domain alignment.")
        raw_dict.setdefault("offer_relevance", "Positions developer tools sponsors for technical audience.")
        raw_dict.setdefault("alternative_drafts", [])
        raw_dict.setdefault("quality_score", 0.95 if actual_wc <= 65 else 0.85)
        raw_dict.setdefault("quality_notes", f"Word count: {actual_wc} words. Review draft before sending.")
        raw_dict.setdefault("research_grounding", [])
        raw_dict.setdefault("applied_memory_rules", [])

        return EmailGenerationResult(**raw_dict)

