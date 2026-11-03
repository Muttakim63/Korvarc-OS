"""SQLAlchemy ORM models for KORVARC OS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Influencer(Base):
    __tablename__ = "influencers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    channel_name = Column(String(255), nullable=True)
    platform = Column(String(100), default="YouTube")
    profile_url = Column(String(1000), nullable=True, index=True)
    business_email = Column(String(255), nullable=True, index=True)
    niche = Column(String(255), default="AI & Software Engineering")
    country = Column(String(100), nullable=True)

    # Metrics and Context (stored as JSON string or text)
    audience_metrics = Column(Text, default="{}")  # e.g. {"subscribers": 150000, "avg_views": 25000}
    audience_notes = Column(Text, nullable=True)
    previous_collaborations = Column(Text, nullable=True)
    potential_sponsors = Column(Text, nullable=True)

    # Commercial References
    rate_reference = Column(Float, nullable=True)  # Historical unverified reference
    current_verified_rates = Column(Float, nullable=True)  # Formally verified current rate

    # Status: Prospect | Contacted | Interested | Negotiating | Onboarded Non-exclusive | Inactive | Declined | Do Not Contact
    representation_status = Column(String(100), default="Prospect", nullable=False)

    contact_history = Column(Text, nullable=True)
    consent_compliance_notes = Column(Text, nullable=True)  # Canadian CASL notes
    last_contacted = Column(DateTime, nullable=True)
    next_follow_up = Column(DateTime, nullable=True)
    general_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    campaigns = relationship("Campaign", back_populates="influencer")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False, index=True)
    website = Column(String(1000), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True, index=True)
    product_category = Column(String(255), nullable=True)  # Developer tools, SaaS, Cloud, etc.
    target_audience = Column(Text, nullable=True)
    previous_sponsorship_evidence = Column(Text, nullable=True)
    potential_creator_matches = Column(Text, nullable=True)
    verified_budget = Column(Float, nullable=True)

    # Status: Researching | Qualified | Contacted | Interested | Negotiating | Active Partner | Closed | Declined | Do Not Contact
    pipeline_status = Column(String(100), default="Researching", nullable=False)

    last_contacted = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    next_action = Column(String(255), nullable=True)
    compliance_status = Column(String(100), default="Pending Review")

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    campaigns = relationship("Campaign", back_populates="brand")


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, nullable=True)
    outreach_type = Column(String(50), nullable=False, default="influencer")  # influencer | brand
    recipient_name = Column(String(255), nullable=True)
    recipient_entity = Column(String(255), nullable=True)  # Channel or Company
    recipient_email = Column(String(255), nullable=True)

    # Subject options and selection
    subject_options = Column(Text, default="[]")  # JSON list of 3 strings
    selected_subject = Column(String(500), nullable=False)

    # Body and revisions
    email_body = Column(Text, nullable=False)
    alternative_drafts = Column(Text, default="[]")  # JSON list of alternative bodies

    # Grounding & Explainability
    research_summary = Column(Text, nullable=True)
    personalization_reasoning = Column(Text, nullable=True)
    offer_reasoning = Column(Text, nullable=True)
    unsupported_claims_warnings = Column(Text, default="[]")  # JSON list of warnings
    word_count = Column(Integer, default=0)
    quality_score = Column(Float, default=1.0)
    quality_notes = Column(Text, nullable=True)

    # AI Metadata
    ai_provider = Column(String(50), nullable=False)  # openai | claude | manual
    ai_model = Column(String(100), nullable=False)

    # Lifecycle & Feedback
    # Status: draft | approved | rejected | archived
    approval_status = Column(String(50), default="draft", nullable=False)
    user_rating = Column(Integer, nullable=True)  # 1 to 5
    feedback_reasons = Column(Text, default="[]")  # JSON list
    free_text_feedback = Column(Text, nullable=True)
    applied_memory_rules = Column(Text, default="[]")  # JSON list

    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("email_drafts.id"), nullable=True)

    # Anti-inflation guard: Drafts are never counted as sent without verified evidence
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class MemoryRule(Base):
    __tablename__ = "memory_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Level 1: Global | Level 2: Outreach Type (influencer/brand) | Level 3: Prospect/Niche specific
    level = Column(Integer, default=1, nullable=False)
    outreach_type = Column(String(50), default="all", nullable=False)  # all | influencer | brand
    rule_text = Column(Text, nullable=False)
    source_feedback = Column(Text, nullable=True)

    is_approved = Column(Boolean, default=True, nullable=False)  # confirmed by user
    is_active = Column(Boolean, default=True, nullable=False)

    version = Column(Integer, default=1)
    previous_versions = Column(Text, default="[]")  # JSON list of past rule_text strings

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=True)
    campaign_name = Column(String(255), nullable=False)

    # Status: Pitching | Negotiating | Contracted | In Production | Live | Completed | Cancelled
    status = Column(String(100), default="Pitching", nullable=False)
    deliverables = Column(Text, nullable=True)  # e.g. "1x 60-second dedicated integration"

    proposed_rate = Column(Float, nullable=True)
    agreed_rate = Column(Float, nullable=True)
    currency = Column(String(10), default="CAD")  # CAD or USD
    commission_rate = Column(Float, default=0.20)  # default agency 20%
    commission_amount = Column(Float, nullable=True)

    approval_status = Column(String(50), default="Draft")
    posting_schedule = Column(DateTime, nullable=True)
    invoice_status = Column(String(50), default="Unbilled")
    payment_status = Column(String(50), default="Pending")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="campaigns")
    influencer = relationship("Influencer", back_populates="campaigns")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class ApiCostLog(Base):
    __tablename__ = "api_cost_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    operation = Column(String(100), default="generate_email")
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

