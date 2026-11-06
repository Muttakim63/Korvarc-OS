"""Reusable UI component renderers for KORVARC OS."""

from __future__ import annotations

import base64
import os
import streamlit as st


def get_logo_base64() -> str:
    """Returns the base64-encoded logo image for fast inline HTML rendering."""
    asset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "assets", "logo_small.png")
    norm_path = os.path.normpath(asset_path)
    if os.path.exists(norm_path):
        with open(norm_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def render_metric_card(label: str, value: str | int | float, subtext: str = ""):
    subtext_html = f'<div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;">{subtext}</div>' if subtext else ""
    html = f"""
    <div class="korvarc-metric-tile">
        <div class="korvarc-metric-value">{value}</div>
        <div class="korvarc-metric-label">{label}</div>
        {subtext_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_verification_badge(status: str) -> str:
    status_lower = status.lower()
    if status_lower == "verified":
        return '<span class="badge-verified">VERIFIED</span>'
    elif status_lower == "user_provided":
        return '<span class="badge-user">USER SUPPLIED</span>'
    elif status_lower == "ai_interpretation":
        return '<span class="badge-status">AI DERIVED</span>'
    else:
        return '<span class="badge-unknown">UNVERIFIED / UNKNOWN</span>'


def render_warning_banner(warnings: list[str]):
    if not warnings:
        return
    items = "".join(f"<li>{w}</li>" for w in warnings)
    html = f"""
    <div class="korvarc-warning">
        <div style="font-weight: 600; margin-bottom: 4px;">⚠️ Grounding & Compliance Notice:</div>
        <ul style="margin: 0; padding-left: 20px;">{items}</ul>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

