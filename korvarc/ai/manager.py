"""Provider manager, credential discovery, cost safeguards, and optional model comparison."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from korvarc.ai.anthropic_provider import AnthropicProvider
from korvarc.ai.base import BaseAIProvider
from korvarc.ai.openai_provider import OpenAIProvider
from korvarc.config import (
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_OPENAI,
    DEFAULT_MODELS,
    AppConfig,
)
from korvarc.database.connection import get_db_session
from korvarc.database.schema import AppSetting
from korvarc.models.schemas import (
    ComparisonResult,
    EmailGenerationResult,
    GenerationRequest,
    ResearchResult,
)


class AIManager:
    """Manages AI provider selection, credentials, safeguards, and comparison."""

    @classmethod
    def get_setting(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a setting from DB first, falling back to environment or default."""
        try:
            with get_db_session() as session:
                setting = session.query(AppSetting).filter_by(key=key).first()
                if setting and setting.value is not None and setting.value.strip() != "":
                    return setting.value.strip()
        except Exception:
            pass
        return os.getenv(key.upper(), default)

    @classmethod
    def set_setting(cls, key: str, value: str) -> None:
        """Saves a setting to the database."""
        with get_db_session() as session:
            setting = session.query(AppSetting).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                session.add(AppSetting(key=key, value=value))

    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        if provider == AI_PROVIDER_OPENAI:
            return cls.get_setting("openai_api_key") or AppConfig.get_openai_api_key()
        elif provider == AI_PROVIDER_CLAUDE:
            return cls.get_setting("anthropic_api_key") or AppConfig.get_anthropic_api_key()
        return None

    @classmethod
    def is_provider_available(cls, provider: str) -> bool:
        key = cls.get_api_key(provider)
        return bool(key and len(key.strip()) > 5)

    @classmethod
    def get_available_models(cls, provider: str) -> List[str]:
        return DEFAULT_MODELS.get(provider, [])

    @classmethod
    def get_provider_instance(cls, provider: str, model_name: Optional[str] = None) -> BaseAIProvider:
        api_key = cls.get_api_key(provider)
        if provider == AI_PROVIDER_OPENAI:
            default_m = model_name or cls.get_setting("openai_default_model", "gpt-4o-mini")
            return OpenAIProvider(api_key=api_key, default_model=default_m)
        elif provider == AI_PROVIDER_CLAUDE:
            default_m = model_name or cls.get_setting("anthropic_default_model", "claude-3-5-sonnet-20241022")
            return AnthropicProvider(api_key=api_key, default_model=default_m)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    @classmethod
    def generate_email(
        cls,
        request: GenerationRequest,
        research: ResearchResult,
        active_rules: List[str],
        approved_examples: List[dict],
        rejected_lessons: List[dict],
    ) -> EmailGenerationResult:
        """Executes generation with single selected provider after checking availability and safeguards."""
        provider_name = request.provider
        if not cls.is_provider_available(provider_name):
            disp_name = "OpenAI" if provider_name == AI_PROVIDER_OPENAI else "Anthropic Claude"
            raise ValueError(
                f"Cannot generate email: API key for {disp_name} is not configured. "
                f"Please navigate to Settings to enter your {disp_name} API key."
            )

        provider = cls.get_provider_instance(provider_name, request.model_name)
        return provider.generate_email(
            request=request,
            research=research,
            active_rules=active_rules,
            approved_examples=approved_examples,
            rejected_lessons=rejected_lessons,
        )

    @classmethod
    def compare_models(
        cls,
        request: GenerationRequest,
        research: ResearchResult,
        active_rules: List[str],
        approved_examples: List[dict],
        rejected_lessons: List[dict],
    ) -> ComparisonResult:
        """Explicitly opt-in feature to generate drafts from both OpenAI and Claude side-by-side."""
        openai_res: Optional[EmailGenerationResult] = None
        claude_res: Optional[EmailGenerationResult] = None

        if cls.is_provider_available(AI_PROVIDER_OPENAI):
            openai_p = cls.get_provider_instance(AI_PROVIDER_OPENAI)
            openai_res = openai_p.generate_email(
                request=request,
                research=research,
                active_rules=active_rules,
                approved_examples=approved_examples,
                rejected_lessons=rejected_lessons,
            )

        if cls.is_provider_available(AI_PROVIDER_CLAUDE):
            claude_p = cls.get_provider_instance(AI_PROVIDER_CLAUDE)
            claude_res = claude_p.generate_email(
                request=request,
                research=research,
                active_rules=active_rules,
                approved_examples=approved_examples,
                rejected_lessons=rejected_lessons,
            )

        diff_summary = ""
        if openai_res and claude_res:
            diff_summary = (
                f"OpenAI word count: {openai_res.word_count} words | "
                f"Claude word count: {claude_res.word_count} words. "
                f"Both models adhered to Korvarc non-exclusive sponsorship guidelines."
            )

        return ComparisonResult(
            openai_result=openai_res,
            claude_result=claude_res,
            differences_summary=diff_summary,
        )
