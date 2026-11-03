"""Dashboard view for agency KPIs, pipeline metrics, and quick actions."""

from __future__ import annotations

import streamlit as st
from korvarc.crm.analytics import AgencyAnalytics
from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft
from korvarc.ui.components import render_metric_card


def render_dashboard():
    st.markdown('<div class="korvarc-title">AGENCY OVERVIEW // DASHBOARD</div>', unsafe_allow_html=True)

    metrics = AgencyAnalytics.get_summary_metrics()

    # Primary KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Creators in CRM",
            metrics["total_influencers"],
            f"{metrics['onboarded_influencers']} Onboarded (Non-exclusive)",
        )
    with col2:
        render_metric_card(
            "Brands in Pipeline",
            metrics["total_brands"],
            f"{metrics['active_brand_partners']} Active Partners",
        )
    with col3:
        render_metric_card(
            "Email Drafts",
            metrics["total_drafts"],
            f"{metrics['approved_drafts']} Approved | {metrics['rejected_drafts']} Rejected",
        )
    with col4:
        rev_cad = metrics["confirmed_revenue_cad"]
        render_metric_card(
            "Confirmed Revenue",
            f"CAD ${rev_cad:,.2f}",
            f"Goal: CAD $5k–$10k/mo",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Operational Status & Quick Actions
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📋 Recent Email Activity")
        with get_db_session() as session:
            recent_drafts = (
                session.query(EmailDraft).order_by(EmailDraft.updated_at.desc()).limit(5).all()
            )
            if recent_drafts:
                for d in recent_drafts:
                    status_color = "#4ADE80" if d.approval_status == "approved" else ("#F87171" if d.approval_status == "rejected" else "#FBBF24")
                    st.markdown(
                        f"""
                        <div style="background-color: #161920; border: 1px solid #232A38; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong style="color: #F1F5F9;">{d.recipient_entity or d.recipient_name or 'Outreach Target'}</strong>
                                <span style="font-size: 0.75rem; color: {status_color}; font-weight: 600; text-transform: uppercase;">● {d.approval_status}</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">{d.selected_subject}</div>
                            <div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">
                                Type: {d.outreach_type.title()} | Model: {d.ai_provider} ({d.ai_model}) | Words: {d.word_count}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No email activity yet. Open the AI Email Studio to research and generate outreach drafts.")

    with col_right:
        st.markdown("### ⚡ Agency Rules & Quick Launch")
        st.markdown(
            """
            <div class="korvarc-card">
                <div class="korvarc-card-header">Core Standards</div>
                <ul style="font-size: 0.82rem; color: #94A3B8; padding-left: 18px; margin: 0;">
                    <li><strong>Non-Exclusive:</strong> Per campaign matching only.</li>
                    <li><strong>Mindset:</strong> Commercial peer, never a fanboy.</li>
                    <li><strong>Length:</strong> ~50 words for creators, 50–90 for brands.</li>
                    <li><strong>CTA:</strong> Short reply-oriented question.</li>
                    <li><strong>Sending:</strong> Drafts only; no automated sends in v1.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚀 Open AI Email Studio", use_container_width=True, type="primary"):
            st.session_state["nav_selection"] = "AI Email Studio"
            st.rerun()

