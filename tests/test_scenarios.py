"""Automated test suite verifying Scenarios A through L for KORVARC OS."""

from __future__ import annotations

import json
import pytest

from korvarc.ai.anthropic_provider import AnthropicProvider
from korvarc.ai.base import BaseAIProvider
from korvarc.ai.manager import AIManager
from korvarc.ai.openai_provider import OpenAIProvider
from korvarc.crm.analytics import AgencyAnalytics
from korvarc.crm.brand_crm import BrandCRM
from korvarc.crm.campaign_crm import CampaignCRM
from korvarc.crm.influencer_crm import InfluencerCRM
from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft, Influencer, MemoryRule
from korvarc.feedback.memory import MemoryEngine
from korvarc.library.email_library import EmailLibrary
from korvarc.models.schemas import (
    EmailGenerationResult,
    GenerationRequest,
    ResearchResult,
)
from korvarc.research.engine import ResearchEngine
from korvarc.research.fetcher import SSRFValidationError, validate_url_safe


# =====================================================================
# TEST A: Grounded Research & User-Supplied Fallback (with SSRF Defense)
# =====================================================================
def test_scenario_a_grounded_research_and_fallback():
    """Verify research produces grounded results, rejects SSRF attacks, and requests user input when unavailable."""
    # 1. SSRF attack rejection
    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://127.0.0.1:8080/internal")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://localhost/admin")

    with pytest.raises(SSRFValidationError):
        validate_url_safe("http://192.168.1.1/router")

    # 2. Research with user-supplied content fallback when public extraction is limited
    res = ResearchEngine.research(
        target_name="Codebasics",
        target_type="influencer",
        url="https://youtube.com/watch?v=mock_video_id",
        user_pasted_content="Covered how to fine-tune Llama 3 using LoRA and unsloth.",
        force_refresh=True,
    )

    assert res.target_name == "Codebasics"
    assert len(res.observations) >= 1
    # Check user-provided observation is strictly categorized as 'user_provided'
    user_obs = [o for o in res.observations if o.verification_status == "user_provided"]
    assert len(user_obs) == 1
    assert "fine-tune Llama 3" in user_obs[0].evidence

    # 3. Completely empty input requests user content honestly without inventing facts
    empty_res = ResearchEngine.research(
        target_name="Unknown Creator",
        target_type="influencer",
        url=None,
        user_pasted_content=None,
        force_refresh=True,
    )
    unknown_obs = [o for o in empty_res.observations if o.verification_status == "unknown"]
    assert len(unknown_obs) >= 1
    assert "No public URL provided" in empty_res.limitation_notes


# =====================================================================
# TEST B: Generate Three Subject Lines & One Grounded Email
# =====================================================================
def test_scenario_b_generate_three_subjects_and_email(sample_generation_result, monkeypatch):
    """Verify generation schema produces exactly three subject lines and recommended draft."""
    monkeypatch.setattr(OpenAIProvider, "generate_email", lambda *args, **kwargs: sample_generation_result)
    monkeypatch.setattr(AIManager, "is_provider_available", lambda p: True)

    req = GenerationRequest(
        outreach_type="influencer",
        entity_name="Codebasics",
        provider="openai",
        model_name="gpt-4o-mini",
        sender_first_name="Alex",
    )
    research = ResearchEngine.research("Codebasics", "influencer")

    result = AIManager.generate_email(req, research, [], [], [])

    assert len(result.subject_lines) == 3
    assert result.primary_draft
    assert result.word_count > 0
    assert result.word_count <= 65  # strictly adheres to ~50 words constraint
    assert "Would you be open to exploring this" in result.primary_draft


# =====================================================================
# TEST C: Switch Between OpenAI and Claude Seamlessly
# =====================================================================
def test_scenario_c_switch_providers_seamlessly(sample_generation_result, monkeypatch):
    """Verify switching between OpenAI and Claude adheres to the identical workflow and schema."""
    monkeypatch.setattr(OpenAIProvider, "generate_email", lambda *args, **kwargs: sample_generation_result)
    monkeypatch.setattr(AnthropicProvider, "generate_email", lambda *args, **kwargs: sample_generation_result)
    monkeypatch.setattr(AIManager, "is_provider_available", lambda p: True)

    research = ResearchEngine.research("Aman", "influencer")

    # Call with OpenAI
    req_openai = GenerationRequest(outreach_type="influencer", entity_name="Aman", provider="openai")
    res_openai = AIManager.generate_email(req_openai, research, [], [], [])
    assert len(res_openai.subject_lines) == 3

    # Switch to Claude
    req_claude = GenerationRequest(outreach_type="influencer", entity_name="Aman", provider="claude")
    res_claude = AIManager.generate_email(req_claude, research, [], [], [])
    assert len(res_claude.subject_lines) == 3
    assert res_claude.primary_draft == res_openai.primary_draft


# =====================================================================
# TEST D: Save, Close, and Reopen an Email (Persistence)
# =====================================================================
def test_scenario_d_save_and_reopen_persistence(sample_generation_result):
    """Verify draft persistence across sessions."""
    saved_draft = EmailLibrary.save_generation_result(
        outreach_type="influencer",
        entity_name="Sentdex",
        contact_name="Harrison",
        recipient_email="business@sentdex.com",
        selected_subject=sample_generation_result.subject_lines[0],
        subject_options=sample_generation_result.subject_lines,
        email_body=sample_generation_result.primary_draft,
        alternative_drafts=sample_generation_result.alternative_drafts,
        research_summary="Python Deep Learning",
        personalization_reasoning=sample_generation_result.personalization_explanation,
        offer_reasoning=sample_generation_result.offer_relevance,
        unsupported_claims_warnings=[],
        word_count=sample_generation_result.word_count,
        quality_score=0.95,
        quality_notes="Good",
        ai_provider="openai",
        ai_model="gpt-4o-mini",
        applied_memory_rules=[],
    )

    # Reopen from fresh session
    reopened = EmailLibrary.get_draft(saved_draft.id)
    assert reopened is not None
    assert reopened.recipient_entity == "Sentdex"
    assert reopened.selected_subject == sample_generation_result.subject_lines[0]
    assert reopened.word_count == sample_generation_result.word_count
    assert reopened.approval_status == "draft"


# =====================================================================
# TEST E: Reject Email, Save Feedback, Verify Memory Rule Workflow
# =====================================================================
def test_scenario_e_reject_feedback_and_memory_retrieval(sample_generation_result):
    """Verify rejecting an email generates a proposed rule, which once confirmed is retrieved in future generations."""
    draft = EmailLibrary.save_generation_result(
        outreach_type="influencer",
        entity_name="AI Planet",
        contact_name=None,
        recipient_email="partnerships@aiplanet.com",
        selected_subject="Initial subject",
        subject_options=["Initial subject"],
        email_body="This is an email that is far too long and verbose...",
        alternative_drafts=[],
        research_summary="",
        personalization_reasoning="",
        offer_reasoning="",
        unsupported_claims_warnings=[],
        word_count=85,
        quality_score=0.6,
        quality_notes="",
        ai_provider="openai",
        ai_model="gpt-4o-mini",
        applied_memory_rules=[],
    )

    # Reject with specific feedback
    MemoryEngine.record_feedback(
        draft_id=draft.id,
        action="reject",
        rating=1,
        feedback_reasons=["Too long"],
        free_text="Keep influencer emails around 50 words.",
    )

    # Verify proposed memory rule exists
    all_rules = MemoryEngine.get_all_rules()
    proposed = [r for r in all_rules if not r.is_approved and "Keep influencer emails around 50 words" in r.rule_text]
    assert len(proposed) == 1

    # Operator confirms / approves the rule
    MemoryEngine.approve_rule(proposed[0].id)

    # Confirm rule is now retrieved in active rules for subsequent influencer generation
    active_rules = MemoryEngine.get_active_rules("influencer")
    assert any("Keep influencer emails around 50 words" in r for r in active_rules)


# =====================================================================
# TEST F: Edit and Approve an Email, Retrieve Final Version
# =====================================================================
def test_scenario_f_edit_approve_and_retrieve():
    """Verify editing a draft creates a revised version and approving preserves the approved state."""
    draft = EmailLibrary.save_generation_result(
        outreach_type="influencer",
        entity_name="ArjanCodes",
        contact_name="Arjan",
        recipient_email="info@arjancodes.com",
        selected_subject="Subject v1",
        subject_options=["Subject v1"],
        email_body="Initial body text.",
        alternative_drafts=[],
        research_summary="",
        personalization_reasoning="",
        offer_reasoning="",
        unsupported_claims_warnings=[],
        word_count=3,
        quality_score=0.9,
        quality_notes="",
        ai_provider="manual",
        ai_model="human",
        applied_memory_rules=[],
    )

    # Operator edits body and approves
    edited_text = "Noticed your clean architecture video on dependency injection. We represent dev tool sponsors. Interested in exploring an integration?"
    MemoryEngine.record_feedback(
        draft_id=draft.id,
        action="approve",
        rating=5,
        edited_body=edited_text,
        selected_subject="Refined subject",
    )

    # Retrieve final
    retrieved = EmailLibrary.get_draft(draft.id)
    assert retrieved.approval_status == "approved"
    assert retrieved.email_body == edited_text
    assert retrieved.selected_subject == "Refined subject"
    assert retrieved.version == 2


# =====================================================================
# TEST G: Creator Prospects Are Not Described as Confirmed Represented
# =====================================================================
def test_scenario_g_prospect_integrity():
    """Verify creator prospects are never automatically marked as onboarded clients without verification."""
    creator = InfluencerCRM.create_influencer(
        name="Sam Witteveen",
        channel_name="Sam Witteveen",
        representation_status="Prospect",
    )
    assert creator.representation_status == "Prospect"
    assert creator.representation_status != "Onboarded Non-exclusive"

    # Ensure baseline memory rules explicitly forbid false representation claims
    active_rules = MemoryEngine.get_active_rules("all")
    assert any("NON-EXCLUSIVE" in r for r in active_rules)


# =====================================================================
# TEST H: No Fake Sponsorships & Detection of Unsupported Placeholders
# =====================================================================
def test_scenario_h_no_fake_sponsorships_or_placeholders():
    """Verify placeholder warnings trigger on [Your Name] and claims like 'secured budget' are flagged."""
    test_draft = (
        "Hi Alex, I love your content. We have a secured budget from Google for your channel. "
        "Best regards,\n[Your Name]"
    )

    provider = OpenAIProvider()
    res = provider.validate_and_postprocess(
        {
            "subject_lines": ["Sub 1", "Sub 2", "Sub 3"],
            "primary_draft": test_draft,
        },
        request=GenerationRequest(outreach_type="influencer", entity_name="Alex"),
    )

    # Check that warnings flag the placeholder [Your Name] and secured budget claim
    warnings_text = " ".join(res.unsupported_claims_warnings)
    assert "[your name]" in warnings_text.lower()
    assert "secured budget" in warnings_text.lower() or "compliance" in warnings_text.lower()


# =====================================================================
# TEST I: Import CSV and Detect Duplicates
# =====================================================================
def test_scenario_i_csv_import_and_duplicate_detection():
    """Verify CSV import parses, detects duplicates by email/URL, and skips or updates cleanly."""
    csv_bytes = (
        b"Creator Name,Channel Name,Profile URL,Business Email,Rate Reference,Status\n"
        b"Creator One,Channel 1,https://youtube.com/@creator1,c1@test.com,1000,Prospect\n"
        b"Creator Two,Channel 2,https://youtube.com/@creator2,c2@test.com,2000,Prospect\n"
        b"Creator Duplicate,Channel 1,https://youtube.com/@creator1,c1@test.com,1500,Prospect\n"
    )

    df = InfluencerCRM.parse_import_file(csv_bytes, "creators.csv")
    mapping = {
        "name": "Creator Name",
        "channel_name": "Channel Name",
        "profile_url": "Profile URL",
        "business_email": "Business Email",
        "rate_reference": "Rate Reference",
        "representation_status": "Status",
    }

    # Execute import with skip duplicates
    res = InfluencerCRM.execute_import(df, mapping, duplicate_strategy="skip")
    assert res["imported"] == 2
    assert res["skipped"] == 1

    # Verify duplicate is not in CRM twice
    with get_db_session() as session:
        records = session.query(Influencer).filter_by(business_email="c1@test.com").all()
        assert len(records) == 1


# =====================================================================
# TEST J: Offline Mode Without API Keys (Honest Unavailable State)
# =====================================================================
def test_scenario_j_offline_mode_without_api_keys(monkeypatch):
    """Verify honest error when API key is missing and verify manual drafting works offline."""
    monkeypatch.setattr(AIManager, "get_api_key", lambda p: None)

    assert not AIManager.is_provider_available("openai")
    assert not AIManager.is_provider_available("claude")

    req = GenerationRequest(outreach_type="influencer", entity_name="Test Prospect", provider="openai")
    research = ResearchEngine.research("Test Prospect", "influencer")

    with pytest.raises(ValueError) as excinfo:
        AIManager.generate_email(req, research, [], [], [])
    assert "API key for OpenAI is not configured" in str(excinfo.value)

    # Verify manual offline saving still functions perfectly
    offline_draft = EmailLibrary.save_generation_result(
        outreach_type="influencer",
        entity_name="Offline Prospect",
        contact_name="Lead",
        recipient_email="lead@test.com",
        selected_subject="Offline Subject",
        subject_options=["Offline Subject"],
        email_body="Manual draft composed offline without paid APIs.",
        alternative_drafts=[],
        research_summary="Manual",
        personalization_reasoning="Manual",
        offer_reasoning="Manual",
        unsupported_claims_warnings=[],
        word_count=8,
        quality_score=1.0,
        quality_notes="Offline",
        ai_provider="manual",
        ai_model="human",
        applied_memory_rules=[],
    )
    assert offline_draft.id is not None
    assert offline_draft.ai_provider == "manual"


# =====================================================================
# TEST K: Security & Draft-Only v1 (No Automated Sending)
# =====================================================================
def test_scenario_k_draft_only_no_automated_sending():
    """Verify that in version 1, all generated emails are strictly draft-only and cannot auto-send."""
    with get_db_session() as session:
        draft = EmailDraft(
            outreach_type="influencer",
            selected_subject="Draft Only",
            email_body="Body",
            ai_provider="manual",
            ai_model="human",
        )
        session.add(draft)
        session.flush()
        # Ensure is_sent is strictly False
        assert draft.is_sent is False
        assert draft.sent_at is None

    # Verify no send method or smtp exists in EmailLibrary
    assert not hasattr(EmailLibrary, "send_email")
    assert not hasattr(EmailLibrary, "auto_send")


# =====================================================================
# TEST L: Analytics Reflect Real Stored Records
# =====================================================================
def test_scenario_l_analytics_reflect_real_records():
    """Verify analytics compute strictly from database records without fabrication."""
    # Seed known records
    InfluencerCRM.create_influencer(name="Creator A", representation_status="Onboarded Non-exclusive")
    InfluencerCRM.create_influencer(name="Creator B", representation_status="Prospect")
    BrandCRM.create_brand(company_name="Brand A", pipeline_status="Active Partner")

    # Seed contracted campaign with commission
    CampaignCRM.create_campaign(
        campaign_name="Test Campaign",
        status="Contracted",
        agreed_rate=5000.0,
        currency="CAD",
        commission_rate=0.20,
    )

    metrics = AgencyAnalytics.get_summary_metrics()
    assert metrics["total_influencers"] == 2
    assert metrics["onboarded_influencers"] == 1
    assert metrics["total_brands"] == 1
    assert metrics["active_brand_partners"] == 1
    assert metrics["confirmed_revenue_cad"] == 1000.0  # 20% of 5,000 CAD

