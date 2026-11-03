"""OpenAI provider adapter with structured output, cost tracking, and error handling."""

from __future__ import annotations

import json
from typing import List, Optional, Tuple
import openai

from korvarc.ai.base import BaseAIProvider
from korvarc.ai.prompts import (
    BRAND_SYSTEM_PROMPT,
    INFLUENCER_SYSTEM_PROMPT,
    build_generation_prompt,
)
from korvarc.models.schemas import EmailGenerationResult, GenerationRequest, ResearchResult

# Approximate pricing per 1M tokens (USD)
OPENAI_RATES = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 2.50, "out": 10.00},
    "gpt-4-turbo": {"in": 10.00, "out": 30.00},
    "o1-mini": {"in": 3.00, "out": 12.00},
}


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gpt-4o-mini"):
        super().__init__(api_key=api_key, default_model=default_model)

    def estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        rates = OPENAI_RATES.get(model, {"in": 0.50, "out": 1.50})
        cost = (tokens_in / 1_000_000 * rates["in"]) + (tokens_out / 1_000_000 * rates["out"])
        return round(cost, 6)

    def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "OpenAI API key is missing. Please configure it in Settings."
        try:
            client = openai.OpenAI(api_key=self.api_key, timeout=10.0)
            # Lightweight verification: list models
            client.models.list()
            return True, "OpenAI API connection verified successfully."
        except Exception as e:
            return False, f"OpenAI connection error: {str(e)}"

    def generate_email(
        self,
        request: GenerationRequest,
        research: ResearchResult,
        active_rules: List[str],
        approved_examples: List[dict],
        rejected_lessons: List[dict],
    ) -> EmailGenerationResult:
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is not configured. Please add your key in Settings or set OPENAI_API_KEY."
            )

        model = request.model_name or self.default_model or "gpt-4o-mini"
        system_prompt = (
            INFLUENCER_SYSTEM_PROMPT if request.outreach_type == "influencer" else BRAND_SYSTEM_PROMPT
        )
        user_prompt = build_generation_prompt(
            request, research, active_rules, approved_examples, rejected_lessons
        )

        client = openai.OpenAI(api_key=self.api_key, timeout=30.0)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            content = response.choices[0].message.content or "{}"
            raw_data = self.clean_json_response(content)

            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0
            cost = self.estimate_cost(model, tokens_in, tokens_out)

            self.record_cost(
                provider="openai",
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                success=True,
            )

            result = self.validate_and_postprocess(raw_data, request)
            return result

        except Exception as e:
            self.record_cost(
                provider="openai",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                success=False,
                error=str(e),
            )
            raise e

