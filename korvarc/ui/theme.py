"""Premium Dark Theme CSS and styling for KORVARC OS."""

from __future__ import annotations

import streamlit as st

PREMIUM_DARK_CSS = """
<style>
/* Main app backgrounds */
.stApp {
    background-color: #0D0F12;
    color: #ECEFF4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #12151B;
    border-right: 1px solid #202632;
}

/* Cards & containers */
.korvarc-card {
    background-color: #161920;
    border: 1px solid #232A38;
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.korvarc-card-header {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8E9BAE;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* Metric tiles */
.korvarc-metric-tile {
    background: linear-gradient(180deg, #181C24 0%, #13161C 100%);
    border: 1px solid #262E3D;
    border-radius: 8px;
    padding: 1rem;
    text-align: left;
}
.korvarc-metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.02em;
}
.korvarc-metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8E9BAE;
    margin-top: 0.25rem;
}

/* Pills & Badges */
.badge-verified {
    background-color: rgba(34, 197, 94, 0.15);
    color: #4ADE80;
    border: 1px solid rgba(34, 197, 94, 0.3);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    display: inline-block;
}
.badge-user {
    background-color: rgba(59, 130, 246, 0.15);
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.3);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    display: inline-block;
}
.badge-unknown {
    background-color: rgba(234, 179, 8, 0.15);
    color: #FACC15;
    border: 1px solid rgba(234, 179, 8, 0.3);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    display: inline-block;
}
.badge-status {
    background-color: rgba(148, 163, 184, 0.15);
    color: #E2E8F0;
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 500;
    display: inline-block;
}

/* Metallic Header Accent */
.korvarc-title {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #F8FAFC;
    border-bottom: 1px solid #202632;
    padding-bottom: 0.5rem;
    margin-bottom: 1.25rem;
}

/* Subject line selector buttons */
.subject-pill {
    background-color: #1A1F29;
    border: 1px solid #2C3545;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    margin-bottom: 0.5rem;
    font-size: 0.88rem;
    color: #E2E8F0;
}

/* Warnings banner */
.korvarc-warning {
    background-color: rgba(245, 158, 11, 0.1);
    border-left: 3px solid #F59E0B;
    padding: 0.75rem 1rem;
    border-radius: 4px;
    margin: 0.75rem 0;
    color: #FDE68A;
    font-size: 0.85rem;
}
</style>
"""


def apply_theme():
    """Injects custom dark theme styling into the Streamlit session."""
    st.markdown(PREMIUM_DARK_CSS, unsafe_allow_html=True)

