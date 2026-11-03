"""Email Library view for managing, editing, filtering, and exporting email drafts."""

from __future__ import annotations

import json
import streamlit as st
from korvarc.database.connection import get_db_session
from korvarc.database.schema import EmailDraft
from korvarc.feedback.memory import MemoryEngine
from korvarc.library.email_library import EmailLibrary


def render_library():
    st.markdown('<div class="korvarc-title">EMAIL LIBRARY // DRAFTS & REVISIONS</div>', unsafe_allow_html=True)

    # Filter Bar
    col_f1, col_f2, col_f3, col_exp = st.columns([2, 1, 1, 1.2])

    with col_f1:
        search = st.text_input("🔍 Search drafts by entity, subject, or copy:", key="lib_search")
    with col_f2:
        outreach_f = st.selectbox("Outreach Type:", options=["All", "Influencer", "Brand"], key="lib_outreach_f")
    with col_f3:
        status_f = st.selectbox("Status:", options=["All", "Draft", "Approved", "Rejected"], key="lib_status_f")

    drafts = EmailLibrary.list_drafts(
        outreach_type=outreach_f,
        approval_status=status_f,
        search_query=search,
        limit=50,
    )

    with col_exp:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if drafts:
            csv_data = EmailLibrary.export_drafts_csv(drafts)
            st.download_button(
                "📥 Export CSV",
                data=csv_data,
                file_name="korvarc_email_drafts.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown("---")

    if not drafts:
        st.info("No email drafts found. Generate drafts in the AI Email Studio.")
        return

    st.caption(f"Displaying {len(drafts)} drafts (anti-inflation rule: drafts are never counted as sent without verified proof):")

    for d in drafts:
        status_color = "#4ADE80" if d.approval_status == "approved" else ("#F87171" if d.approval_status == "rejected" else "#FBBF24")
        with st.expander(f"[{d.outreach_type.upper()}] {d.recipient_entity or 'Target'} — \"{d.selected_subject}\" (v{d.version})"):
            c_meta1, c_meta2, c_meta3 = st.columns(3)
            with c_meta1:
                st.markdown(f"**Status:** <span style='color: {status_color}; font-weight: 600;'>{d.approval_status.upper()}</span>", unsafe_allow_html=True)
                st.markdown(f"**Word Count:** {d.word_count} words")
            with c_meta2:
                st.markdown(f"**AI Model:** {d.ai_provider} ({d.ai_model})")
                st.markdown(f"**Created:** {d.created_at.strftime('%Y-%m-%d %H:%M') if d.created_at else 'N/A'}")
            with c_meta3:
                st.markdown(f"**Rating:** {'⭐' * d.user_rating if d.user_rating else 'Unrated'}")
                if d.free_text_feedback:
                    st.caption(f"Feedback: {d.free_text_feedback}")

            # Editable subject & body
            new_sub = st.text_input("Subject", value=d.selected_subject, key=f"lib_sub_{d.id}")
            new_body = st.text_area("Body", value=d.email_body, height=130, key=f"lib_body_{d.id}")

            # Buttons
            b1, b2, b3, b4, b5 = st.columns(5)
            with b1:
                if st.button("💾 Save Changes", key=f"lib_save_{d.id}", use_container_width=True):
                    MemoryEngine.record_feedback(
                        draft_id=d.id,
                        action="save_edit",
                        edited_body=new_body,
                        selected_subject=new_sub,
                    )
                    st.success("Draft updated.")
                    st.rerun()

            with b2:
                if st.button("✅ Approve", key=f"lib_app_{d.id}", use_container_width=True, type="primary"):
                    MemoryEngine.record_feedback(
                        draft_id=d.id,
                        action="approve",
                        rating=5,
                        edited_body=new_body,
                        selected_subject=new_sub,
                    )
                    st.success("Draft approved.")
                    st.rerun()

            with b3:
                if st.button("❌ Reject", key=f"lib_rej_{d.id}", use_container_width=True):
                    MemoryEngine.record_feedback(
                        draft_id=d.id,
                        action="reject",
                        rating=1,
                        edited_body=new_body,
                        selected_subject=new_sub,
                    )
                    st.success("Draft marked rejected.")
                    st.rerun()

            with b4:
                if st.button("📋 Duplicate", key=f"lib_dup_{d.id}", use_container_width=True):
                    EmailLibrary.duplicate_draft(d.id)
                    st.success("Draft cloned.")
                    st.rerun()

            with b5:
                if st.button("🗑️ Delete", key=f"lib_del_{d.id}", use_container_width=True):
                    EmailLibrary.delete_draft(d.id)
                    st.success("Draft deleted.")
                    st.rerun()

