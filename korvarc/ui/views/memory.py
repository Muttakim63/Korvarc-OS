"""AI Memory and Feedback Management view with confirmation workflow and version reversion."""

from __future__ import annotations

import json
import streamlit as st
from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft, MemoryRule
from korvarc.feedback.memory import MemoryEngine


def render_memory():
    st.markdown('<div class="korvarc-title">AI MEMORY & FEEDBACK // RETRIEVAL-BASED LEARNING</div>', unsafe_allow_html=True)

    st.caption(
        "Korvarc OS uses persistent local retrieval memory. Confirmed preferences and approved examples are dynamically "
        "injected into generation prompts. (Note: Feedback steers contextual prompts and does not retrain underlying model weights)."
    )

    tab_rules, tab_pending, tab_exemplars, tab_add = st.tabs([
        "🧠 Active Confirmed Rules",
        "⏳ Proposed Rules (Pending Confirmation)",
        "🌟 Approved Email Exemplars",
        "➕ Add Memory Rule",
    ])

    # TAB 1: Active Confirmed Rules
    with tab_rules:
        all_rules = MemoryEngine.get_all_rules()
        active_confirmed = [r for r in all_rules if r.is_approved]

        if not active_confirmed:
            st.info("No confirmed rules yet.")
        else:
            for r in active_confirmed:
                status_badge = "🟢 ACTIVE" if r.is_active else "⚪ DISABLED"
                level_str = "Level 1: Global" if r.level == 1 else f"Level 2: {r.outreach_type.title()} Outreach"

                with st.expander(f"Rule #{r.id} ({level_str}) — {status_badge} — v{r.version}"):
                    st.markdown(f"**Origin / Source:** {r.source_feedback or 'System Baseline'}")
                    edit_text = st.text_area("Rule Instruction", value=r.rule_text, key=f"rule_text_{r.id}", height=80)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button("💾 Update Rule", key=f"rule_upd_{r.id}", use_container_width=True):
                            MemoryEngine.update_rule_text(r.id, edit_text)
                            st.success("Rule updated and version archived.")
                            st.rerun()

                    with col2:
                        toggle_lbl = "Disable Rule" if r.is_active else "Enable Rule"
                        if st.button(toggle_lbl, key=f"rule_tog_{r.id}", use_container_width=True):
                            MemoryEngine.toggle_rule_active(r.id, not r.is_active)
                            st.rerun()

                    with col3:
                        if st.button("🗑️ Delete", key=f"rule_del_{r.id}", use_container_width=True):
                            MemoryEngine.delete_rule(r.id)
                            st.success("Rule deleted.")
                            st.rerun()

                    with col4:
                        # Version history & Reversion
                        prev_vers = []
                        try:
                            prev_vers = json.loads(r.previous_versions or "[]")
                        except Exception:
                            pass
                        if prev_vers:
                            target_v = st.selectbox(
                                "Restore Past Version:",
                                options=[v["version"] for v in prev_vers],
                                format_func=lambda v: f"v{v}",
                                key=f"restore_v_{r.id}",
                            )
                            if st.button("⏪ Restore", key=f"btn_restore_{r.id}"):
                                MemoryEngine.restore_previous_version(r.id, target_v)
                                st.success(f"Restored version {target_v}")
                                st.rerun()

    # TAB 2: Proposed Rules (Pending Confirmation)
    with tab_pending:
        all_rules = MemoryEngine.get_all_rules()
        pending = [r for r in all_rules if not r.is_approved]

        if not pending:
            st.info("No pending proposals. Rejections with feedback will appear here for operator confirmation.")
        else:
            st.caption("Review proposed memory rules derived from user rejection feedback before confirming them:")
            for p in pending:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="korvarc-card">
                            <div class="korvarc-card-header">Proposed from Rejection // {p.outreach_type.title()} Outreach</div>
                            <div style="font-size: 0.95rem; color: #F1F5F9; font-weight: 500; margin-bottom: 8px;">"{p.rule_text}"</div>
                            <div style="font-size: 0.78rem; color: #8E9BAE;">{p.source_feedback}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    c_app, c_del = st.columns([1, 1])
                    with c_app:
                        if st.button(f"✅ Approve & Enforce Rule #{p.id}", key=f"app_pend_{p.id}", type="primary"):
                            MemoryEngine.approve_rule(p.id)
                            st.success("Rule approved and enforced for future generation.")
                            st.rerun()
                    with c_del:
                        if st.button(f"❌ Dismiss Rule #{p.id}", key=f"del_pend_{p.id}"):
                            MemoryEngine.delete_rule(p.id)
                            st.rerun()

    # TAB 3: Approved Email Exemplars
    with tab_exemplars:
        st.caption("Approved emails are retrieved as few-shot demonstrations for future generations.")
        with get_db_session() as s:
            approved = s.query(EmailDraft).filter_by(approval_status="approved").order_by(EmailDraft.updated_at.desc()).limit(10).all()
            if not approved:
                st.info("No approved emails yet. Approve high-quality generations in the AI Email Studio.")
            else:
                for a in approved:
                    with st.expander(f"[{a.outreach_type.upper()}] {a.recipient_entity or 'Target'} — \"{a.selected_subject}\""):
                        st.markdown(f"**Word Count:** {a.word_count} words | **Model:** {a.ai_provider} ({a.ai_model})")
                        st.code(a.email_body, language="text")

    # TAB 4: Add Rule Manually
    with tab_add:
        st.markdown("#### Create Explicit Agency Memory Rule")
        with st.form("add_manual_rule_form"):
            r_text = st.text_input("Rule Instruction *", placeholder="e.g. 'Keep influencer emails around 50 words'")
            col1, col2 = st.columns(2)
            with col1:
                r_type = st.selectbox("Outreach Applicability", options=["all", "influencer", "brand"], format_func=lambda x: x.title())
            with col2:
                r_level = st.selectbox("Rule Level", options=[1, 2], format_func=lambda x: "Level 1: Global" if x == 1 else "Level 2: Outreach-Specific")

            if st.form_submit_button("Save & Confirm Memory Rule", type="primary"):
                if not r_text.strip():
                    st.error("Rule text cannot be empty.")
                else:
                    with get_db_session() as session:
                        rule = MemoryRule(
                            level=r_level,
                            outreach_type=r_type,
                            rule_text=r_text.strip(),
                            source_feedback="Manually configured agency standard",
                            is_approved=True,
                            is_active=True,
                            version=1,
                            previous_versions=json.dumps([]),
                        )
                        session.add(rule)
                    st.success("Memory rule created and activated.")
                    st.rerun()

