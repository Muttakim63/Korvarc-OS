"""Campaign CRM view for commercial deals, deliverables, and revenue tracking."""

from __future__ import annotations

import streamlit as st
from korvarc.crm.brand_crm import BrandCRM
from korvarc.crm.campaign_crm import VALID_CAMPAIGN_STATUSES, CampaignCRM
from korvarc.crm.influencer_crm import InfluencerCRM
from korvarc.database.connection import get_db_session
from korvarc.database.schema import Brand, Campaign, Influencer


def render_campaigns():
    st.markdown('<div class="korvarc-title">CAMPAIGN CRM // COMMERCIAL SPONSORSHIPS</div>', unsafe_allow_html=True)

    tab_list, tab_create = st.tabs(["📊 Active Sponsorships", "➕ Create Campaign"])

    # TAB 1: List
    with tab_list:
        status_filter = st.selectbox("Status Filter:", options=["All"] + VALID_CAMPAIGN_STATUSES, key="camp_status_f")
        campaigns = CampaignCRM.list_campaigns(status=status_filter)

        if not campaigns:
            st.info("No commercial campaigns tracked yet. Create a campaign to track deliverables and commissions.")
        else:
            for c in campaigns:
                with st.expander(f"{c.campaign_name} — {c.status} ({c.currency} ${c.agreed_rate or c.proposed_rate or 0:,.2f})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Brand ID:** {c.brand_id or 'Unassigned'}")
                        st.markdown(f"**Creator ID:** {c.influencer_id or 'Unassigned'}")
                        st.markdown(f"**Deliverables:** {c.deliverables or 'TBD'}")
                    with col2:
                        st.markdown(f"**Proposed Rate:** {c.currency} ${c.proposed_rate or 0:,.2f}")
                        st.markdown(f"**Agreed Rate:** {c.currency} ${c.agreed_rate or 0:,.2f}")
                        st.markdown(f"**Agency Commission (20%):** {c.currency} ${c.commission_amount or 0:,.2f}")
                    with col3:
                        new_status = st.selectbox(
                            "Status:",
                            options=VALID_CAMPAIGN_STATUSES,
                            index=VALID_CAMPAIGN_STATUSES.index(c.status) if c.status in VALID_CAMPAIGN_STATUSES else 0,
                            key=f"camp_status_{c.id}",
                        )
                        if new_status != c.status:
                            CampaignCRM.update_campaign(c.id, status=new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()

    # TAB 2: Create Campaign
    with tab_create:
        st.markdown("#### Create Commercial Sponsorship Deal")
        brands = BrandCRM.list_brands()
        creators = InfluencerCRM.list_influencers()

        brand_options = {b.id: b.company_name for b in brands}
        creator_options = {inf.id: f"{inf.name} ({inf.channel_name or 'Channel'})" for inf in creators}

        with st.form("create_campaign_form"):
            c_name = st.text_input("Campaign Name *", placeholder="e.g. Cursor Q4 Dev Sponsorship")
            col1, col2 = st.columns(2)
            with col1:
                sel_brand = st.selectbox("Select Brand", options=[None] + list(brand_options.keys()), format_func=lambda x: brand_options.get(x, "Select brand..."))
                prop_rate = st.number_input("Proposed Rate ($)", min_value=0.0, step=250.0, value=2500.0)
                curr = st.selectbox("Currency", options=["CAD", "USD"], index=0)
            with col2:
                sel_creator = st.selectbox("Select Creator", options=[None] + list(creator_options.keys()), format_func=lambda x: creator_options.get(x, "Select creator..."))
                agreed_rate = st.number_input("Agreed Rate ($)", min_value=0.0, step=250.0, value=0.0)
                status = st.selectbox("Initial Status", options=VALID_CAMPAIGN_STATUSES, index=0)

            deliverables = st.text_area("Deliverables", placeholder="1x 60-second integrated mid-roll with custom CTA link.")

            if st.form_submit_button("Create Campaign Record", type="primary"):
                if not c_name.strip():
                    st.error("Campaign Name is required.")
                else:
                    CampaignCRM.create_campaign(
                        campaign_name=c_name.strip(),
                        brand_id=sel_brand,
                        influencer_id=sel_creator,
                        status=status,
                        deliverables=deliverables.strip() or None,
                        proposed_rate=prop_rate,
                        agreed_rate=agreed_rate if agreed_rate > 0 else None,
                        currency=curr,
                    )
                    st.success("Campaign recorded successfully.")
                    st.rerun()

