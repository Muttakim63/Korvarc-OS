"""AI Email Studio for Influencer and Brand Sponsorship Outreach."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import streamlit as st

from korvarc.ai.manager import AIManager
from korvarc.config import (
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_OPENAI,
    AppConfig,
)
from korvarc.crm.brand_crm import BrandCRM
from korvarc.crm.influencer_crm import InfluencerCRM
from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft
from korvarc.feedback.memory import FEEDBACK_REASONS, MemoryEngine
from korvarc.library.email_library import EmailLibrary
from korvarc.models.schemas import GenerationRequest, ResearchResult
from korvarc.research.engine import ResearchEngine
from korvarc.ui.components import render_verification_badge, render_warning_banner


def render_studio():
    st.markdown('<div class="korvarc-title">AI EMAIL STUDIO // SPONSORSHIP OUTREACH</div>', unsafe_allow_html=True)

    # Top Bar: Provider Selector & Model Options
    col_prov1, col_prov2, col_model, col_sender = st.columns([1.2, 1.2, 2, 2])

    with col_prov1:
        st.markdown("**AI Provider:**")
        current_prov = st.session_state.get("selected_provider", AIManager.get_setting("default_ai_provider", AI_PROVIDER_OPENAI))
        p_choice = st.radio(
            "AI Provider",
            options=[AI_PROVIDER_OPENAI, AI_PROVIDER_CLAUDE],
            index=0 if current_prov == AI_PROVIDER_OPENAI else 1,
            format_func=lambda x: "🟢 OpenAI" if x == AI_PROVIDER_OPENAI else "🟣 Claude (Anthropic)",
            horizontal=True,
            label_visibility="collapsed",
            key="studio_provider_choice",
        )
        st.session_state["selected_provider"] = p_choice

    with col_prov2:
        prov_available = AIManager.is_provider_available(p_choice)
        if prov_available:
            st.markdown(f'<span class="badge-verified" style="margin-top: 10px;">KEY CONFIGURED</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge-unknown" style="margin-top: 10px;">KEY MISSING</span>', unsafe_allow_html=True)

    with col_model:
        models = AIManager.get_available_models(p_choice)
        default_idx = 0
        selected_model = st.selectbox(
            "Model Selection:",
            options=models,
            index=default_idx,
            key=f"studio_model_{p_choice}",
            help="Select the specific language model identifier.",
        )

    with col_sender:
        sender_first_name = AIManager.get_setting("sender_first_name", "")
        if sender_first_name:
            st.markdown(f"<div style='font-size: 0.8rem; color: #94A3B8; margin-top: 10px;'>Signing as: <strong>{sender_first_name}</strong></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size: 0.8rem; color: #F59E0B; margin-top: 10px;'>⚠️ Sender name unconfigured (Drafts will be unsigned)</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Tabs: Influencer vs Brand Outreach
    tab_inf, tab_brand = st.tabs(["🎯 TAB A: INFLUENCER OUTREACH", "🏢 TAB B: BRAND OUTREACH"])

    with tab_inf:
        _render_outreach_interface(
            outreach_type="influencer",
            provider=p_choice,
            model_name=selected_model,
            prov_available=prov_available,
            sender_name=sender_first_name,
        )

    with tab_brand:
        _render_outreach_interface(
            outreach_type="brand",
            provider=p_choice,
            model_name=selected_model,
            prov_available=prov_available,
            sender_name=sender_first_name,
        )


def _render_outreach_interface(
    outreach_type: str,
    provider: str,
    model_name: str,
    prov_available: bool,
    sender_name: Optional[str],
):
    prefix = f"{outreach_type}_"

    col_input, col_output = st.columns([1.1, 1.2])

    with col_input:
        st.markdown(f"#### 1. Target Dossier & Intake ({outreach_type.title()})")

        # Entity Name
        entity_label = "Creator / Channel Name *" if outreach_type == "influencer" else "Company / Brand Name *"
        entity_name = st.text_input(entity_label, key=f"{prefix}entity_name", placeholder="e.g. Codebasics or Cursor")

        # Contact Name & Email
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            contact_name = st.text_input("Contact Person (Optional)", key=f"{prefix}contact_name", placeholder="e.g. Dhaval Patel")
        with col_c2:
            recipient_email = st.text_input("Email (Optional)", key=f"{prefix}recipient_email", placeholder="contact@domain.com")

        # URL Input
        url_label = "YouTube Video, Channel, or Website URL" if outreach_type == "influencer" else "Company Website / Profile URL"
        input_url = st.text_input(url_label, key=f"{prefix}url", placeholder="https://...")

        # User Observation / Transcript Fallback
        user_notes = st.text_area(
            "User Observations or Video Transcript (Optional)",
            key=f"{prefix}user_notes",
            placeholder="Paste transcript snippet, technical moment, or specific product detail if public extraction is unavailable.",
            height=90,
        )

        # Campaign Objective & Word Count
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            default_obj = "Commercial sponsorship exploration" if outreach_type == "influencer" else "Pitch creator roster sponsorship"
            campaign_obj = st.text_input("Objective", value=default_obj, key=f"{prefix}obj")
        with col_o2:
            target_wc = st.number_input(
                "Target Word Count",
                min_value=30,
                max_value=150,
                value=50 if outreach_type == "influencer" else 75,
                step=5,
                key=f"{prefix}wc",
                help="Korvarc standards: ~50 words for influencers, 50-90 words for brands.",
            )

        # Tone Selection
        desired_tone = st.selectbox(
            "Tone",
            options=["Confident, peer-to-peer, concise", "Direct & commercial", "Technical & observational"],
            key=f"{prefix}tone",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Action Buttons: Research & Generate
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("🔍 RESEARCH", key=f"{prefix}btn_research", use_container_width=True):
                if not entity_name.strip() and not input_url.strip() and not user_notes.strip():
                    st.warning("Please provide at least a Target Name, URL, or plain-text description.")
                else:
                    with st.spinner("Conducting grounded public research..."):
                        research_res = ResearchEngine.research(
                            target_name=entity_name.strip() or "Target",
                            target_type=outreach_type,
                            url=input_url.strip() or None,
                            user_pasted_content=user_notes.strip() or None,
                            force_refresh=True,
                        )
                        st.session_state[f"{prefix}research_data"] = research_res
                        st.success("Research completed.")

        with btn_col2:
            can_generate = prov_available and (entity_name.strip() or input_url.strip())
            gen_label = "⚡ GENERATE EMAIL" if prov_available else "⚠️ API Key Required"
            if st.button(gen_label, key=f"{prefix}btn_generate", disabled=not can_generate, use_container_width=True, type="primary"):
                _trigger_generation(
                    outreach_type=outreach_type,
                    entity_name=entity_name,
                    contact_name=contact_name,
                    recipient_email=recipient_email,
                    input_url=input_url,
                    user_notes=user_notes,
                    campaign_obj=campaign_obj,
                    target_wc=target_wc,
                    desired_tone=desired_tone,
                    provider=provider,
                    model_name=model_name,
                    sender_name=sender_name,
                )

        # Compare Models Option (Strictly opt-in)
        has_both = AIManager.is_provider_available(AI_PROVIDER_OPENAI) and AIManager.is_provider_available(AI_PROVIDER_CLAUDE)
        if has_both:
            with st.expander("⚖️ Compare Models (OpenAI vs Claude Side-by-Side)"):
                st.caption("Explicitly requests generation from both providers to compare tone and brevity.")
                if st.button("Compare OpenAI vs Claude", key=f"{prefix}btn_compare"):
                    _trigger_comparison(
                        outreach_type=outreach_type,
                        entity_name=entity_name,
                        contact_name=contact_name,
                        recipient_email=recipient_email,
                        input_url=input_url,
                        user_notes=user_notes,
                        campaign_obj=campaign_obj,
                        target_wc=target_wc,
                        desired_tone=desired_tone,
                        sender_name=sender_name,
                    )

        # Offline / Missing Credentials Notice
        if not prov_available:
            st.info(
                f"**Offline Mode Active:** {provider.title()} API key is not configured. "
                "AI generation is unavailable to prevent simulated output. "
                "You can still research public data, manually compose or paste drafts, and manage CRM records."
            )

        # Research Dossier Display
        research_data: Optional[ResearchResult] = st.session_state.get(f"{prefix}research_data")
        if research_data:
            st.markdown("---")
            st.markdown("#### 🔬 Factual Research Findings")
            if research_data.limitation_notes:
                st.warning(f"**Research Notice:** {research_data.limitation_notes}")

            for obs in research_data.observations:
                badge_html = render_verification_badge(obs.verification_status)
                st.markdown(
                    f"""
                    <div style="background-color: #12151B; border: 1px solid #1F2633; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.8rem; color: #8E9BAE; font-weight: 600;">{obs.source}</span>
                            {badge_html}
                        </div>
                        <div style="font-size: 0.85rem; color: #E2E8F0; margin-top: 4px;">{obs.observation}</div>
                        <div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;"><em>Evidence:</em> {obs.evidence}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_output:
        st.markdown(f"#### 2. Generated Outreach & Review")
        active_draft = st.session_state.get(f"{prefix}active_draft")

        if active_draft:
            _render_draft_review(active_draft, prefix, outreach_type)
        else:
            # Manual / Offline Draft Entry Mode
            st.markdown(
                """
                <div style="background-color: #161920; border: 1px dashed #2E384D; border-radius: 8px; padding: 25px; text-align: center; color: #8E9BAE;">
                    <div style="font-size: 1.1rem; font-weight: 600; color: #CBD5E1; margin-bottom: 6px;">No Active Draft Loaded</div>
                    <div style="font-size: 0.85rem;">Click 'Generate Email' or create a manual draft below.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("✍️ Compose Manual Draft (Offline / External AI)"):
                m_sub = st.text_input("Subject Line", key=f"{prefix}manual_sub")
                m_body = st.text_area("Email Body", key=f"{prefix}manual_body", height=150)
                if st.button("Save Manual Draft", key=f"{prefix}save_manual"):
                    if m_sub and m_body:
                        draft_rec = EmailLibrary.save_generation_result(
                            outreach_type=outreach_type,
                            entity_name=entity_name or "Manual Prospect",
                            contact_name=contact_name,
                            recipient_email=recipient_email,
                            selected_subject=m_sub,
                            subject_options=[m_sub],
                            email_body=m_body,
                            alternative_drafts=[],
                            research_summary="Manually composed / externally sourced.",
                            personalization_reasoning="Manual operator composition.",
                            offer_reasoning="Direct sponsorship proposition.",
                            unsupported_claims_warnings=AppConfig.check_for_placeholder_warnings(m_body),
                            word_count=len(m_body.split()),
                            quality_score=1.0,
                            quality_notes="Manual draft entry",
                            ai_provider="manual",
                            ai_model="human",
                            applied_memory_rules=[],
                        )
                        st.session_state[f"{prefix}active_draft"] = draft_rec
                        st.success("Manual draft saved to Library.")
                        st.rerun()


def _trigger_generation(
    outreach_type: str,
    entity_name: str,
    contact_name: Optional[str],
    recipient_email: Optional[str],
    input_url: Optional[str],
    user_notes: Optional[str],
    campaign_obj: str,
    target_wc: int,
    desired_tone: str,
    provider: str,
    model_name: str,
    sender_name: Optional[str],
):
    prefix = f"{outreach_type}_"
    with st.spinner(f"Generating personalized outreach with {provider.title()}..."):
        # 1. Fetch or load research
        research_data = st.session_state.get(f"{prefix}research_data")
        if not research_data:
            research_data = ResearchEngine.research(
                target_name=entity_name.strip() or "Prospect",
                target_type=outreach_type,
                url=input_url.strip() if input_url else None,
                user_pasted_content=user_notes.strip() if user_notes else None,
            )
            st.session_state[f"{prefix}research_data"] = research_data

        # 2. Retrieve active memory rules and lessons
        active_rules = MemoryEngine.get_active_rules(outreach_type)
        approved_examples = MemoryEngine.get_approved_examples(outreach_type, limit=2)
        rejected_lessons = MemoryEngine.get_rejected_lessons(outreach_type, limit=3)

        req = GenerationRequest(
            outreach_type=outreach_type,
            contact_name=contact_name.strip() if contact_name else None,
            entity_name=entity_name.strip() or "Target Prospect",
            url=input_url.strip() if input_url else None,
            email=recipient_email.strip() if recipient_email else None,
            additional_context=None,
            user_pasted_content=user_notes.strip() if user_notes else None,
            campaign_objective=campaign_obj,
            desired_tone=desired_tone,
            target_word_count=target_wc,
            provider=provider,
            model_name=model_name,
            sender_first_name=sender_name,
        )

        try:
            result = AIManager.generate_email(
                request=req,
                research=research_data,
                active_rules=active_rules,
                approved_examples=approved_examples,
                rejected_lessons=rejected_lessons,
            )

            # Persist to EmailLibrary
            draft = EmailLibrary.save_generation_result(
                outreach_type=outreach_type,
                entity_name=req.entity_name,
                contact_name=req.contact_name,
                recipient_email=req.email,
                selected_subject=result.subject_lines[0],
                subject_options=result.subject_lines,
                email_body=result.primary_draft,
                alternative_drafts=result.alternative_drafts,
                research_summary=research_data.raw_summary,
                personalization_reasoning=result.personalization_explanation,
                offer_reasoning=result.offer_relevance,
                unsupported_claims_warnings=result.unsupported_claims_warnings,
                word_count=result.word_count,
                quality_score=result.quality_score,
                quality_notes=result.quality_notes,
                ai_provider=provider,
                ai_model=model_name,
                applied_memory_rules=result.applied_memory_rules,
            )
            st.session_state[f"{prefix}active_draft"] = draft
            st.success("Personalized outreach draft generated successfully.")
            st.rerun()

        except Exception as e:
            st.error(f"Generation error: {str(e)}")


def _trigger_comparison(
    outreach_type: str,
    entity_name: str,
    contact_name: Optional[str],
    recipient_email: Optional[str],
    input_url: Optional[str],
    user_notes: Optional[str],
    campaign_obj: str,
    target_wc: int,
    desired_tone: str,
    sender_name: Optional[str],
):
    with st.spinner("Generating drafts with both OpenAI and Claude..."):
        research_data = ResearchEngine.research(
            target_name=entity_name or "Prospect",
            target_type=outreach_type,
            url=input_url,
            user_pasted_content=user_notes,
        )
        active_rules = MemoryEngine.get_active_rules(outreach_type)
        approved_examples = MemoryEngine.get_approved_examples(outreach_type, limit=2)
        rejected_lessons = MemoryEngine.get_rejected_lessons(outreach_type, limit=3)

        req = GenerationRequest(
            outreach_type=outreach_type,
            contact_name=contact_name,
            entity_name=entity_name or "Target",
            url=input_url,
            email=recipient_email,
            campaign_objective=campaign_obj,
            desired_tone=desired_tone,
            target_word_count=target_wc,
            provider="openai",
            sender_first_name=sender_name,
        )

        comparison = AIManager.compare_models(
            request=req,
            research=research_data,
            active_rules=active_rules,
            approved_examples=approved_examples,
            rejected_lessons=rejected_lessons,
        )

        st.session_state["comparison_results"] = comparison
        st.success("Comparison completed! Inspect the results below.")


def _render_draft_review(draft: EmailDraft, prefix: str, outreach_type: str):
    # Subject Lines
    subject_options = []
    try:
        subject_options = json.loads(draft.subject_options or "[]")
    except Exception:
        subject_options = [draft.selected_subject]

    st.markdown("**Subject Line Options (Click to select):**")
    for idx, sub in enumerate(subject_options):
        is_selected = sub == draft.selected_subject
        btn_type = "primary" if is_selected else "secondary"
        if st.button(f"{'✓ ' if is_selected else ''}Option {idx+1}: {sub}", key=f"{prefix}sub_opt_{idx}", type=btn_type):
            draft.selected_subject = sub
            with get_db_session() as s:
                db_d = s.query(EmailDraft).filter_by(id=draft.id).first()
                if db_d:
                    db_d.selected_subject = sub
            st.rerun()

    # Editable Email Body
    st.markdown("**Email Draft (Directly Editable):**")
    edited_body = st.text_area(
        "Email Body",
        value=draft.email_body,
        height=180,
        key=f"{prefix}body_area",
        label_visibility="collapsed",
    )

    # Word Count & Metadata Badge
    words = len(edited_body.split())
    wc_color = "#4ADE80" if words <= 65 else "#F59E0B"
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #8E9BAE; margin-bottom: 10px;">
            <span>Word count: <strong style="color: {wc_color};">{words} words</strong> (Target: ~50w)</span>
            <span>Provider: <strong>{draft.ai_provider}</strong> ({draft.ai_model}) | Version: {draft.version}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Unsupported Claims & Grounding Warnings
    warnings = []
    try:
        warnings = json.loads(draft.unsupported_claims_warnings or "[]")
    except Exception:
        pass
    render_warning_banner(warnings)

    # Grounding & Explainability Accordion
    with st.expander("💡 Personalization & Commercial Rationale"):
        st.markdown(f"**Personalization Angle:** {draft.personalization_reasoning}")
        st.markdown(f"**Offer Matchmaking Relevance:** {draft.offer_reasoning}")
        if draft.quality_notes:
            st.markdown(f"**Quality Assessment:** {draft.quality_notes}")

    # Alternative Draft Angles
    alt_drafts = []
    try:
        alt_drafts = json.loads(draft.alternative_drafts or "[]")
    except Exception:
        pass
    if alt_drafts:
        with st.expander(f"🔀 Alternative Draft Variations ({len(alt_drafts)})"):
            for i, alt in enumerate(alt_drafts, 1):
                st.markdown(f"**Alternative {i}:**")
                st.code(alt, language="text")
                if st.button(f"Use Alternative {i}", key=f"{prefix}use_alt_{i}"):
                    draft.email_body = alt
                    with get_db_session() as s:
                        db_d = s.query(EmailDraft).filter_by(id=draft.id).first()
                        if db_d:
                            db_d.email_body = alt
                            db_d.word_count = len(alt.split())
                            db_d.version += 1
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Core Action Buttons
    c_save, c_app, c_rej, c_copy = st.columns(4)

    with c_save:
        if st.button("💾 Save Edits", key=f"{prefix}btn_save", use_container_width=True):
            MemoryEngine.record_feedback(
                draft_id=draft.id,
                action="save_edit",
                edited_body=edited_body,
                selected_subject=draft.selected_subject,
            )
            st.success("Draft saved.")
            st.rerun()

    with c_app:
        if st.button("✅ Approve", key=f"{prefix}btn_approve", use_container_width=True, type="primary"):
            MemoryEngine.record_feedback(
                draft_id=draft.id,
                action="approve",
                rating=5,
                edited_body=edited_body,
                selected_subject=draft.selected_subject,
            )
            st.success("Email approved! Saved to memory as an exemplar.")
            st.rerun()

    with c_rej:
        if st.button("❌ Reject / Feedback", key=f"{prefix}btn_reject", use_container_width=True):
            st.session_state[f"{prefix}show_feedback_drawer"] = not st.session_state.get(f"{prefix}show_feedback_drawer", False)

    with c_copy:
        # Streamlit copy helper
        st.code(f"Subject: {draft.selected_subject}\n\n{edited_body}", language="text")

    # Feedback & Rejection Drawer
    if st.session_state.get(f"{prefix}show_feedback_drawer", False):
        st.markdown("---")
        st.markdown("##### 📝 Submit Feedback & Train Memory")
        st.caption("Tell Korvarc OS why this draft was rejected so future generations adapt.")

        rating = st.slider("Quality Rating", min_value=1, max_value=5, value=2, key=f"{prefix}rating")
        selected_reasons = st.multiselect(
            "Structured Feedback Reasons:",
            options=FEEDBACK_REASONS,
            default=["Too long"] if words > 65 else ["Too generic"],
            key=f"{prefix}reasons",
        )
        feedback_text = st.text_input(
            "Operator Instruction / Rule Synthesis:",
            placeholder="e.g. 'Keep influencer emails around 50 words' or 'Stop opening with I came across your channel'",
            key=f"{prefix}fb_text",
        )

        if st.button("Submit Rejection & Save Memory Rule", key=f"{prefix}submit_fb", type="primary"):
            MemoryEngine.record_feedback(
                draft_id=draft.id,
                action="reject",
                rating=rating,
                feedback_reasons=selected_reasons,
                free_text=feedback_text,
                edited_body=edited_body,
                selected_subject=draft.selected_subject,
            )
            st.session_state[f"{prefix}show_feedback_drawer"] = False
            st.success("Feedback recorded and proposed memory rule generated.")
            st.rerun()

