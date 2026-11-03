"""Configuration and constants for KORVARC OS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Agency Identity Constants
AGENCY_NAME = "Korvarc"
AGENCY_LOCATION = os.getenv("KORVARC_AGENCY_LOCATION", "Ontario, Canada")
REPRESENTATION_MODEL = "NON-EXCLUSIVE, per campaign"
AGENCY_NICHES = [
    "Artificial intelligence",
    "Machine learning",
    "Data science",
    "Programming",
    "Software engineering",
    "Developer tools",
    "SaaS and technical education",
]

# Historical Unverified Rate References (Reference only; not validated commitments)
HISTORICAL_RATE_REFERENCES = {
    "Codebasics": 3000,
    "Aman": 2000,
    "AI Planet": 1500,
    "Sam Witteveen": 5000,
}

# Supported AI Providers
AI_PROVIDER_OPENAI = "openai"
AI_PROVIDER_CLAUDE = "claude"
SUPPORTED_PROVIDERS = [AI_PROVIDER_OPENAI, AI_PROVIDER_CLAUDE]

# Default Model Identifiers (editable in settings)
DEFAULT_MODELS = {
    AI_PROVIDER_OPENAI: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o1-mini"],
    AI_PROVIDER_CLAUDE: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
}

# Default Cost Safeguards (USD per single generation)
DEFAULT_MAX_COST_PER_REQUEST = float(os.getenv("MAX_COST_PER_REQUEST_USD", "0.20"))

# Database path
DEFAULT_DB_PATH = os.getenv("KORVARC_DB_PATH", str(BASE_DIR / "korvarc.db"))


class AppConfig:
    """Dynamic application configuration and settings store."""

    @classmethod
    def get_openai_api_key(cls) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY", "").strip() or None

    @classmethod
    def get_anthropic_api_key(cls) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY", "").strip() or None

    @classmethod
    def get_default_provider(cls) -> str:
        provider = os.getenv("DEFAULT_AI_PROVIDER", AI_PROVIDER_OPENAI).lower()
        return provider if provider in SUPPORTED_PROVIDERS else AI_PROVIDER_OPENAI

    @classmethod
    def get_sender_first_name(cls) -> Optional[str]:
        name = os.getenv("KORVARC_SENDER_FIRST_NAME", "").strip()
        return name if name else None

    @classmethod
    def get_signature(cls, sender_first_name: Optional[str] = None) -> str:
        """Returns the signature if sender first name is configured, else blank (unsigned)."""
        name = sender_first_name or cls.get_sender_first_name()
        if not name:
            return ""
        return f"Best regards,\n{name}"

    @classmethod
    def check_for_placeholder_warnings(cls, text: str) -> list[str]:
        """Detects unintended placeholder strings such as [Your Name] or [Insert Brand]."""
        warnings = []
        lowered = text.lower()
        placeholders = [
            "[your name]",
            "[name]",
            "[insert",
            "{your name}",
            "<your name>",
            "[sender]",
            "[brand]",
            "[creator]",
        ]
        for p in placeholders:
            if p in lowered:
                warnings.append(f"Unfilled placeholder detected: '{p}'. Please review the draft before approving.")
        return warnings

