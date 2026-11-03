"""Analytics view showing factual performance metrics from stored database records."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from korvarc.crm.analytics import AgencyAnalytics
from korvarc.ui.components import render_metric_card


def render_analytics():
    st.markdown('<div class="korvarc-title">AGENCY ANALYTICS // REAL STORED PERFORMANCE</div>', unsafe_allow_html=True)
    st.caption("All metrics are computed exclusively from database records. No fabricated reply rates or open rates.")

    metrics = AgencyAnalytics.get_summary_metrics()

    # Top KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Total Creators", metrics["total_influencers"], f"{metrics['onboarded_influencers']} Onboarded")
    with col2:
        render_metric_card("Total Brands", metrics["total_brands"], f"{metrics['active_brand_partners']} Active Partners")
    with col3:
        render_metric_card("Drafts Approved", f"{metrics['approved_drafts']} / {metrics['total_drafts']}", f"{metrics['rejected_drafts']} Rejected")
    with col4:
        render_metric_card("Confirmed Agency Rev", f"CAD ${metrics['confirmed_revenue_cad']:,.2f}", f"USD ${metrics['confirmed_revenue_usd']:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Secondary KPI Row
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    with col_a1:
        render_metric_card("Avg Draft Word Count", f"{metrics['avg_word_count']} words", "Target: ~50w for creators")
    with col_a2:
        render_metric_card("Avg Quality Rating", f"{metrics['avg_rating']} / 5.0" if metrics['avg_rating'] else "N/A", "From user feedback")
    with col_a3:
        render_metric_card("Active Campaigns", metrics["active_campaigns"], "Deals in negotiation/pipeline")
    with col_a4:
        render_metric_card("Pending Drafts", metrics["pending_drafts"], "Drafts awaiting approval")

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("##### 🤖 Provider Usage Breakdown")
        dist = metrics["providers_distribution"]
        df_prov = pd.DataFrame(list(dist.items()), columns=["Provider", "Generations"])
        if df_prov["Generations"].sum() > 0:
            st.bar_chart(df_prov.set_index("Provider"), color="#60A5FA")
        else:
            st.info("No generations recorded yet.")

    with col_chart2:
        st.markdown("##### 📉 Feedback & Rejection Reasons")
        reasons_dist = metrics["feedback_reasons_distribution"]
        if reasons_dist:
            df_reasons = pd.DataFrame(list(reasons_dist.items()), columns=["Reason", "Count"])
            st.bar_chart(df_reasons.set_index("Reason"), color="#F87171")
        else:
            st.info("No structured rejection feedback recorded yet.")

