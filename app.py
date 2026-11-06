"""KORVARC OS - Local AI Agency Platform for Creator & Brand Sponsorships.

Preferred launch command:
    streamlit run app.py
"""

from __future__ import annotations

import base64
import os
import streamlit as st

def _get_logo_base64() -> str:
    asset_path = os.path.join(os.path.dirname(__file__), "assets", "logo_small.png")
    if os.path.exists(asset_path):
        with open(asset_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

# Find favicon path
_FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png")
_PAGE_ICON = _FAVICON_PATH if os.path.exists(_FAVICON_PATH) else "⚡"

# Streamlit Page Setup must be the first command
st.set_page_config(
    page_title="KORVARC OS",
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

from korvarc.ai.manager import AIManager
from korvarc.database.connection import init_db
from korvarc.ui.theme import apply_theme
from korvarc.ui.views.analytics import render_analytics
from korvarc.ui.views.brands import render_brands
from korvarc.ui.views.campaigns import render_campaigns
from korvarc.ui.views.dashboard import render_dashboard
from korvarc.ui.views.influencers import render_influencers
from korvarc.ui.views.library import render_library
from korvarc.ui.views.memory import render_memory
from korvarc.ui.views.settings import render_settings
from korvarc.ui.views.studio import render_studio

# Initialize Database Schema & Baseline Rules
init_db()

# Apply Premium Dark CSS
apply_theme()

# Base64 logo for clean branding
_LOGO_B64 = _get_logo_base64()
_LOGO_SIDEBAR_IMG = (
    f'<img src="data:image/png;base64,{_LOGO_B64}" style="width: 38px; height: 38px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.4);" />'
    if _LOGO_B64
    else '<span style="font-size: 1.5rem;">⚡</span>'
)

# Optional Operator Access PIN Gate (Protects local network and mobile access)
configured_pin = AIManager.get_setting("access_pin", os.getenv("KORVARC_ACCESS_PIN", ""))
if configured_pin:
    if not st.session_state.get("is_authenticated", False):
        _gate_logo_html = (
            f'<img src="data:image/png;base64,{_LOGO_B64}" style="width: 72px; height: 72px; border-radius: 14px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.6);" />'
            if _LOGO_B64
            else ""
        )
        st.markdown(
            f"""
            <div style="max-width: 440px; margin: 80px auto 20px auto; background-color: #161920; border: 1px solid #232A38; border-radius: 12px; padding: 2.2rem; box-shadow: 0 8px 24px rgba(0,0,0,0.5); text-align: center;">
                {_gate_logo_html}
                <div style="font-size: 1.5rem; font-weight: 800; color: #F8FAFC; letter-spacing: 0.05em; margin-bottom: 4px;">KORVARC OS</div>
                <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: #8E9BAE; margin-bottom: 24px;">Restricted Operator Access</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_pad1, col_center, col_pad2 = st.columns([1, 1.2, 1])
        with col_center:
            entered_pin = st.text_input("Enter Access PIN", type="password", key="auth_pin_input")
            if st.button("Unlock Dashboard", type="primary", use_container_width=True):
                if entered_pin.strip() == configured_pin.strip():
                    st.session_state["is_authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Access denied.")
        st.stop()

# Navigation definition
NAV_ITEMS = [
    "Dashboard",
    "AI Email Studio",
    "Influencers",
    "Brands",
    "Email Library",
    "Campaigns",
    "AI Memory",
    "Analytics",
    "Settings",
]

# Sidebar
with st.sidebar:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 12px; padding: 10px 0 18px 0; border-bottom: 1px solid #202632; margin-bottom: 15px;">
            {_LOGO_SIDEBAR_IMG}
            <div>
                <div style="font-size: 1.15rem; font-weight: 800; letter-spacing: 0.08em; color: #F8FAFC; line-height: 1.2;">
                    KORVARC OS
                </div>
                <div style="font-size: 0.68rem; color: #8E9BAE; letter-spacing: 0.05em; text-transform: uppercase; margin-top: 2px;">
                    AI Sponsorship Agency
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sync navigation state
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = "Dashboard"

    current_idx = NAV_ITEMS.index(st.session_state["nav_selection"]) if st.session_state["nav_selection"] in NAV_ITEMS else 0
    selected_page = st.radio(
        "Navigation",
        options=NAV_ITEMS,
        index=current_idx,
        label_visibility="collapsed",
        key="sidebar_nav",
    )
    st.session_state["nav_selection"] = selected_page

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size: 0.72rem; color: #64748B; border-top: 1px solid #1A202C; padding-top: 10px;">
            <div><strong>Location:</strong> Ontario, Canada</div>
            <div><strong>Model:</strong> Non-Exclusive, per campaign</div>
            <div><strong>Mode:</strong> Local Drafts Only (v1.0)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Router
if selected_page == "Dashboard":
    render_dashboard()
elif selected_page == "AI Email Studio":
    render_studio()
elif selected_page == "Influencers":
    render_influencers()
elif selected_page == "Brands":
    render_brands()
elif selected_page == "Email Library":
    render_library()
elif selected_page == "Campaigns":
    render_campaigns()
elif selected_page == "AI Memory":
    render_memory()
elif selected_page == "Analytics":
    render_analytics()
elif selected_page == "Settings":
    render_settings()
