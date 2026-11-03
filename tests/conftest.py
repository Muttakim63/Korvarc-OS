"""Pytest fixtures with isolated SQLite database and mocked AI providers."""

from __future__ import annotations

import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from korvarc.database.connection import init_db
from korvarc.database.schema import Base
from korvarc.models.schemas import EmailGenerationResult


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Creates a fresh, isolated temporary SQLite database for every test."""
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_korvarc.db")
    monkeypatch.setenv("KORVARC_DB_PATH", temp_db_path)

    # Initialize tables and seed rules
    init_db(temp_db_path)

    yield temp_db_path

    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except Exception:
        pass


@pytest.fixture
def sample_generation_result():
    return EmailGenerationResult(
        subject_lines=[
            "Quick question on your PyTorch pipeline",
            "Sponsorship match for Codebasics audience",
            "Developer tools integration proposal",
        ],
        primary_draft=(
            "Saw your recent breakdown of end-to-end PyTorch model deployment. "
            "At Korvarc, we match technical creators with developer tool companies like Neon and Pinecone for non-exclusive integrations. "
            "Would you be open to exploring this for an upcoming video?"
        ),
        alternative_drafts=[
            "Enjoyed your clean explanation of data pipelines. Would you be interested in a sponsored developer segment?"
        ],
        personalization_explanation="Directly references the PyTorch model deployment tutorial without generic flattery.",
        offer_relevance="Matches a data science creator with database/infrastructure developer sponsors.",
        unsupported_claims_warnings=[],
        word_count=43,
        quality_score=0.98,
        quality_notes="Meets 50-word constraint and peer-to-peer tone.",
        research_grounding=["PyTorch model deployment topic"],
        applied_memory_rules=["Keep influencer emails around 50 words"],
    )

