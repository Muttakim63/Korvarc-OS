"""Influencer CRM view and CSV/XLSX bulk import wizard."""

from __future__ import annotations

import streamlit as st
from korvarc.crm.influencer_crm import VALID_STATUSES, InfluencerCRM
from korvarc.database.connection import get_db_session
from korvarc.database.schema import Influencer


def render_influencers():
    st.markdown('<div class="korvarc-title">INFLUENCER CRM // TECHNICAL CREATORS</div>', unsafe_allow_html=True)

    tab_list, tab_import, tab_add = st.tabs(["👥 Creator Directory", "📥 CSV / XLSX Import Wizard", "➕ Add Creator"])

    # TAB 1: Creator Directory
    with tab_list:
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            search = st.text_input("🔍 Search creators by name, channel, niche, or email:", key="inf_search")
        with col_f2:
            status_filter = st.selectbox("Status Filter:", options=["All"] + VALID_STATUSES, key="inf_status_filter")
        with col_f3:
            total_count = InfluencerCRM.count_influencers(status_filter)
            st.metric("Total Records", total_count)

        creators = InfluencerCRM.list_influencers(status=status_filter, search_query=search, limit=50)

        if not creators:
            st.info("No influencer records match your query. Use the Import Wizard to load creator records.")
        else:
            for inf in creators:
                status_color = "#4ADE80" if "Onboarded" in inf.representation_status else ("#F87171" if inf.representation_status in ("Declined", "Do Not Contact") else "#60A5FA")
                with st.expander(f"{inf.name} ({inf.channel_name or 'Channel'}) — {inf.representation_status}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Platform:** {inf.platform}")
                        st.markdown(f"**Email:** {inf.business_email or 'None'}")
                        st.markdown(f"**URL:** {inf.profile_url or 'None'}")
                    with c2:
                        st.markdown(f"**Niche:** {inf.niche or 'Technical'}")
                        st.markdown(f"**Country:** {inf.country or 'Unknown'}")
                        st.markdown(f"**Historical Rate Ref:** ${inf.rate_reference:,.2f}" if inf.rate_reference else "**Rate Ref:** Unset")
                    with c3:
                        new_status = st.selectbox(
                            "Update Status:",
                            options=VALID_STATUSES,
                            index=VALID_STATUSES.index(inf.representation_status) if inf.representation_status in VALID_STATUSES else 0,
                            key=f"inf_status_{inf.id}",
                        )
                        if new_status != inf.representation_status:
                            InfluencerCRM.update_influencer(inf.id, representation_status=new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()

                    # Quick button to launch outreach
                    if st.button("✉️ Draft Outreach to this Creator", key=f"inf_outreach_{inf.id}"):
                        st.session_state["influencer_entity_name"] = inf.name
                        st.session_state["influencer_url"] = inf.profile_url or ""
                        st.session_state["influencer_recipient_email"] = inf.business_email or ""
                        st.session_state["nav_selection"] = "AI Email Studio"
                        st.rerun()

    # TAB 2: CSV / XLSX Import Wizard
    with tab_import:
        st.markdown("#### Bulk Creator Import (CSV / Excel)")
        st.caption("Upload your spreadsheet of creator records. Duplicate detection prevents redundant entries.")

        uploaded_file = st.file_uploader("Choose a CSV or XLSX file", type=["csv", "xlsx", "xls"], key="inf_file_upload")

        if uploaded_file:
            try:
                df = InfluencerCRM.parse_import_file(uploaded_file.getvalue(), uploaded_file.name)
                st.write(f"Detected **{len(df)} rows** and **{len(df.columns)} columns**.")

                st.markdown("##### 1. Column Mapping")
                st.caption("Map the columns in your spreadsheet to Korvarc CRM fields:")

                cols = ["(Skip)"] + list(df.columns)
                cm1, cm2, cm3 = st.columns(3)

                with cm1:
                    name_col = st.selectbox("Creator / Person Name *", options=cols, index=1 if len(cols) > 1 else 0)
                    channel_col = st.selectbox("Channel Name", options=cols, index=2 if len(cols) > 2 else 0)
                    email_col = st.selectbox("Business Email", options=cols, index=3 if len(cols) > 3 else 0)

                with cm2:
                    url_col = st.selectbox("Profile / Channel URL", options=cols, index=4 if len(cols) > 4 else 0)
                    niche_col = st.selectbox("Niche / Category", options=cols, index=5 if len(cols) > 5 else 0)
                    country_col = st.selectbox("Country", options=cols, index=0)

                with cm3:
                    rate_col = st.selectbox("Rate Reference", options=cols, index=0)
                    status_col = st.selectbox("Status", options=cols, index=0)
                    dup_strategy = st.selectbox("Duplicate Resolution:", options=["skip", "update", "keep_both"], format_func=lambda x: f"Skip duplicates ({x})" if x == "skip" else f"{x.title()}")

                mapping = {
                    "name": name_col if name_col != "(Skip)" else None,
                    "channel_name": channel_col if channel_col != "(Skip)" else None,
                    "business_email": email_col if email_col != "(Skip)" else None,
                    "profile_url": url_col if url_col != "(Skip)" else None,
                    "niche": niche_col if niche_col != "(Skip)" else None,
                    "country": country_col if country_col != "(Skip)" else None,
                    "rate_reference": rate_col if rate_col != "(Skip)" else None,
                    "representation_status": status_col if status_col != "(Skip)" else None,
                }

                if mapping["name"]:
                    # Preview analysis
                    analysis = InfluencerCRM.preview_import(df, mapping)
                    st.markdown("##### 2. Import Validation Preview")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    col_p1.metric("Total Rows in File", analysis["total_rows"])
                    col_p2.metric("New Records", analysis["valid_rows"])
                    col_p3.metric("Detected Duplicates", analysis["duplicate_rows"])

                    st.dataframe(analysis["preview_sample"], use_container_width=True)

                    if st.button("🚀 Execute Import", type="primary", key="btn_exec_import"):
                        with st.spinner("Importing records into Korvarc database..."):
                            res = InfluencerCRM.execute_import(df, mapping, duplicate_strategy=dup_strategy)
                            st.success(f"Import complete! Added: {res['imported']} | Updated: {res['updated']} | Skipped: {res['skipped']}")
                            st.rerun()
                else:
                    st.warning("Please map at least the 'Creator / Person Name' field to proceed.")

            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    # TAB 3: Add Creator Manually
    with tab_add:
        st.markdown("#### Add Single Creator Record")
        with st.form("add_creator_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Creator Name *", placeholder="e.g. Sentdex")
                new_channel = st.text_input("Channel Name", placeholder="e.g. Sentdex Python")
                new_email = st.text_input("Business Email", placeholder="creator@business.com")
                new_url = st.text_input("Channel / Profile URL", placeholder="https://youtube.com/@...")
            with c2:
                new_niche = st.text_input("Niche", value="Python & Artificial Intelligence")
                new_country = st.text_input("Country", placeholder="Canada, US, UK, etc.")
                new_rate = st.number_input("Rate Reference ($)", min_value=0.0, step=100.0, value=0.0)
                new_status = st.selectbox("Status", options=VALID_STATUSES, index=0)

            new_notes = st.text_area("General Notes / Observations")

            if st.form_submit_button("Save Creator to CRM", type="primary"):
                if not new_name.strip():
                    st.error("Creator Name is required.")
                else:
                    InfluencerCRM.create_influencer(
                        name=new_name.strip(),
                        channel_name=new_channel.strip() or new_name.strip(),
                        business_email=new_email.strip() or None,
                        profile_url=new_url.strip() or None,
                        niche=new_niche.strip(),
                        country=new_country.strip() or None,
                        rate_reference=new_rate if new_rate > 0 else None,
                        representation_status=new_status,
                        general_notes=new_notes.strip() or None,
                    )
                    st.success(f"Creator '{new_name}' added to CRM.")
                    st.rerun()

