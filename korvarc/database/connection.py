"""Database connection and initialization for KORVARC OS."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from korvarc.database.schema import AppSetting, Base, MemoryRule

_engines: dict[str, Any] = {}
_sessionmakers: dict[str, sessionmaker] = {}


def get_current_db_path(db_path: Optional[str] = None) -> str:
    from korvarc.config import BASE_DIR
    return db_path or os.getenv("KORVARC_DB_PATH") or str(BASE_DIR / "korvarc.db")


def get_engine(db_path: Optional[str] = None):
    path = get_current_db_path(db_path)
    if path not in _engines:
        engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        Base.metadata.create_all(bind=engine)
        _engines[path] = engine
        _sessionmakers[path] = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
        )
    return _engines[path]


def get_sessionmaker(db_path: Optional[str] = None) -> sessionmaker:
    path = get_current_db_path(db_path)
    get_engine(path)
    return _sessionmakers[path]


@contextmanager
def get_db_session(db_path: Optional[str] = None) -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    sm = get_sessionmaker(db_path)
    session = sm()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Create all tables and seed default confirmed agency memory rules."""
    path = get_current_db_path(db_path)
    engine = get_engine(path)
    Base.metadata.create_all(bind=engine)

    # Seed baseline agency memory rules
    with get_db_session(path) as session:
        existing_rules = session.query(MemoryRule).count()
        if existing_rules == 0:
            baseline_rules = [
                MemoryRule(
                    level=1,
                    outreach_type="all",
                    rule_text="Never sound needy, overly enthusiastic, flattering, or robotic. Avoid 'I love your content', 'I stumbled across your channel', or 'Your engagement is incredible'.",
                    source_feedback="Agency Core Standard: Professional commercial peer-to-peer tone.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
                MemoryRule(
                    level=1,
                    outreach_type="all",
                    rule_text="Korvarc operates strictly under a NON-EXCLUSIVE, per-campaign representation model. Never imply exclusive representation or portray prospects as onboarded clients.",
                    source_feedback="Agency Core Standard: Non-exclusive commercial matchmaking integrity.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
                MemoryRule(
                    level=1,
                    outreach_type="all",
                    rule_text="Potential brand matches are commercial matchmaking suggestions, not confirmed partners or secured budgets.",
                    source_feedback="Agency Core Standard: Truthful commercial positioning.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
                MemoryRule(
                    level=2,
                    outreach_type="influencer",
                    rule_text="Influencer emails must target approximately 50 words with concise paragraphs. CTA must be a single short, reply-oriented question like 'Would you be interested?' or 'Open to exploring this?'.",
                    source_feedback="Agency Core Standard: High-response short creator outreach.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
                MemoryRule(
                    level=2,
                    outreach_type="influencer",
                    rule_text="Personalization must cite a concrete technical topic, specific explanation, or verified audience problem from actual content. If unverified, state the audience angle honestly without inventing moments.",
                    source_feedback="Agency Core Standard: Factual grounding requirement.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
                MemoryRule(
                    level=2,
                    outreach_type="brand",
                    rule_text="Brand emails must target 50 to 90 words. Highlight brand product, relevant technical creator audience fit, and a clear commercial sponsorship opportunity with a direct CTA.",
                    source_feedback="Agency Core Standard: High-conversion brand pitch format.",
                    is_approved=True,
                    is_active=True,
                    version=1,
                    previous_versions=json.dumps([]),
                ),
            ]
            session.add_all(baseline_rules)

        default_settings = {
            "default_ai_provider": "openai",
            "openai_default_model": "gpt-4o-mini",
            "anthropic_default_model": "claude-3-5-sonnet-20241022",
            "max_cost_per_request": "0.15",
            "sender_first_name": "",
            "agency_location": "Ontario, Canada",
        }
        for k, v in default_settings.items():
            if not session.query(AppSetting).filter_by(key=k).first():
                session.add(AppSetting(key=k, value=v))
