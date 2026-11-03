"""Brand CRM view with pipeline status and explainable creator matchmaking."""

from __future__ import annotations

import streamlit as st
from korvarc.crm.brand_crm import VALID_BRAND_STATUSES, BrandCRM
from korvarc.database.connection import get_db_session
from korvarc.database.schema import Brand


def render_brands():
    st.markdown('<div class="korvarc-title">BRAND CRM // SPONSORSHIP PIPELINE</div>', unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["🏢 Brand Directory & Matchmaker", "➕ Add Brand"])

    # TAB 1: Brand Directory & Matchmaker
    with tab_list:
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            search = st.text_input("🔍 Search brands by company, category, contact, or email:", key="brand_search")
        with col_f2:
            status_filter = st.selectbox("Pipeline Status:", options=["All"] + VALID_BRAND_STATUSES, key="brand_status_filter")
        with col_f3:
            total_count = BrandCRM.count_brands(status_filter)
            st.metric("Total Brands", total_count)

        brands = BrandCRM.list_brands(status=status_filter, search_query=search, limit=50)

        if not brands:
            st.info("No brand records found. Add prospective brands to pitch your technical creators.")
        else:
            for b in brands:
                with st.expander(f"{b.company_name} — {b.product_category or 'Tech'} ({b.pipeline_status})"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Website:** {b.website or 'None'}")
                        st.markdown(f"**Contact:** {b.contact_name or 'Unspecified'} ({b.contact_email or 'No email'})")
                        st.markdown(f"**Target Audience:** {b.target_audience or 'General Tech'}")
                    with c2:
                        st.markdown(f"**Verified Budget:** ${b.verified_budget:,.2f}" if b.verified_budget else "**Verified Budget:** Unverified")
                        st.markdown(f"**Next Action:** {b.next_action or 'Initial pitch'}")
                        st.markdown(f"**Compliance Status:** {b.compliance_status}")
                    with c3:
                        new_s = st.selectbox(
                            "Update Pipeline Status:",
                            options=VALID_BRAND_STATUSES,
                            index=VALID_BRAND_STATUSES.index(b.pipeline_status) if b.pipeline_status in VALID_BRAND_STATUSES else 0,
                            key=f"brand_status_{b.id}",
                        )
                        if new_s != b.pipeline_status:
                            BrandCRM.update_brand(b.id, pipeline_status=new_s)
                            st.success(f"Status updated to {new_s}")
                            st.rerun()

                    st.markdown("---")
                    st.markdown("##### 🤝 Creator Matchmaker (Explainable Fit)")
                    matches = BrandCRM.find_creator_matches(b.id, limit=3)
                    if matches:
                        for m in matches:
                            reasons_str = " • ".join(m["reasons"])
                            st.markdown(
                                f"""
                                <div style="background-color: #12151B; border: 1px solid #1F2633; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                                    <strong>{m['creator_name']}</strong> ({m['channel_name']}) — <span style="color: #60A5FA;">{m['niche']}</span>
                                    <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 3px;"><strong>Fit Rationale:</strong> {reasons_str}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("Add more technical creators to the CRM to see explainable matches.")

                    if st.button("✉️ Draft Brand Pitch in Studio", key=f"brand_pitch_{b.id}"):
                        st.session_state["brand_entity_name"] = b.company_name
                        st.session_state["brand_url"] = b.website or ""
                        st.session_state["brand_recipient_email"] = b.contact_email or ""
                        st.session_state["nav_selection"] = "AI Email Studio"
                        st.rerun()

    # TAB 2: Add Brand
    with tab_add:
        st.markdown("#### Add Brand to Pipeline")
        with st.form("add_brand_form"):
            b1, b2 = st.columns(2)
            with b1:
                comp_name = st.text_input("Company Name *", placeholder="e.g. Supabase, Docker, Pinecone")
                website = st.text_input("Website URL", placeholder="https://...")
                c_name = st.text_input("Contact Person", placeholder="e.g. Jane Smith, Head of DevRel")
                c_email = st.text_input("Contact Email", placeholder="partnerships@company.com")
            with b2:
                category = st.text_input("Product Category", placeholder="Developer Tools, Database, AI Infrastructure")
                target_aud = st.text_input("Target Audience", placeholder="Python engineers, Data Scientists, AI builders")
                v_budget = st.number_input("Verified Budget ($)", min_value=0.0, step=500.0, value=0.0)
                pipe_status = st.selectbox("Pipeline Status", options=VALID_BRAND_STATUSES, index=0)

            b_notes = st.text_area("Research / Sponsorship Notes")

            if st.form_submit_button("Save Brand", type="primary"):
                if not comp_name.strip():
                    st.error("Company Name is required.")
                else:
                    BrandCRM.create_brand(
                        company_name=comp_name.strip(),
                        website=website.strip() or None,
                        contact_name=c_name.strip() or None,
                        contact_email=c_email.strip() or None,
                        product_category=category.strip() or None,
                        target_audience=target_aud.strip() or None,
                        verified_budget=v_budget if v_budget > 0 else None,
                        pipeline_status=pipe_status,
                        notes=b_notes.strip() or None,
                    )
                    st.success(f"Brand '{comp_name}' saved to pipeline.")
                    st.rerun()

