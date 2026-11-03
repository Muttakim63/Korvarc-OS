"""Anthropic Claude provider adapter with structured JSON extraction, cost tracking, and safeguards."""

from __future__ import annotations

import json
from typing import List, Optional, Tuple
import anthropic

from korvarc.ai.base import BaseAIProvider
from korvarc.ai.prompts import (
    BRAND_SYSTEM_PROMPT,
    INFLUENCER_SYSTEM_PROMPT,
    build_generation_prompt,
)
from korvarc.models.schemas import EmailGenerationResult, GenerationRequest, ResearchResult

ANTHROPIC_RATES = {
    "claude-3-5-sonnet-20241022": {"in": 3.00, "out": 15.00},
    "claude-3-5-haiku-20241022": {"in": 0.80, "out": 4.00},
    "claude-3-opus-20240229": {"in": 15.00, "out": 75.00},
}


class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key=api_key, default_model=default_model)

    def estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        rates = ANTHROPIC_RATES.get(model, {"in": 3.00, "out": 15.00})
        cost = (tokens_in / 1_000_000 * rates["in"]) + (tokens_out / 1_000_000 * rates["out"])
        return round(cost, 6)

    def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Anthropic API key is missing. Please configure it in Settings."
        try:
            client = anthropic.Anthropic(api_key=self.api_key, timeout=10.0)
            # Lightweight test message
            res = client.messages.create(
                model=self.default_model or "claude-3-5-haiku-20241022",
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True, "Anthropic Claude API connection verified successfully."
        except Exception as e:
            return False, f"Anthropic connection error: {str(e)}"

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
                "Anthropic API key is not configured. Please add your key in Settings or set ANTHROPIC_API_KEY."
            )

        model = request.model_name or self.default_model or "claude-3-5-sonnet-20241022"
        system_prompt = (
            INFLUENCER_SYSTEM_PROMPT if request.outreach_type == "influencer" else BRAND_SYSTEM_PROMPT
        )
        # Claude responds best when explicitly instructed to output raw JSON with no conversational prefix
        system_prompt += "\nIMPORTANT: You must respond ONLY with the valid JSON object. Do not include any greeting or explanation before or after the JSON."

        user_prompt = build_generation_prompt(
            request, research, active_rules, approved_examples, rejected_lessons
        )

        client = anthropic.Anthropic(api_key=self.api_key, timeout=35.0)

        try:
            response = client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=1500,
                temperature=0.7,
            )

            content = response.content[0].text if response.content else "{}"
            raw_data = self.clean_json_response(content)

            tokens_in = response.usage.input_tokens if response.usage else 0
            tokens_out = response.usage.output_tokens if response.usage else 0
            cost = self.estimate_cost(model, tokens_in, tokens_out)

            self.record_cost(
                provider="claude",
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
                provider="claude",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                success=False,
                error=str(e),
            )
            raise e

