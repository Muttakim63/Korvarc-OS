"""Settings view for AI credentials, cost safeguards, model selection, sender identity, and mobile security."""

from __future__ import annotations

import os
import streamlit as st
from korvarc.ai.anthropic_provider import AnthropicProvider
from korvarc.ai.manager import AIManager
from korvarc.ai.openai_provider import OpenAIProvider
from korvarc.config import (
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_OPENAI,
    DEFAULT_MODELS,
    AppConfig,
)
from korvarc.database.connection import get_db_session
from korvarc.database.schema import ApiCostLog, AppSetting


def render_settings():
    st.markdown('<div class="korvarc-title">AGENCY SETTINGS // AI CONFIGURATION & CONTROLS</div>', unsafe_allow_html=True)

    tab_ai, tab_sender, tab_costs, tab_security, tab_compliance = st.tabs([
        "🤖 AI Providers & Keys",
        "✍️ Sender Identity & Signature",
        "💰 Cost Safeguards & API Logs",
        "🔒 Access PIN & Mobile Access",
        "🇨🇦 Compliance & Anti-Spam (CASL)",
    ])

    # TAB 1: AI Providers & Keys
    with tab_ai:
        st.markdown("#### Dual AI Provider Configuration")
        st.caption("Korvarc OS supports both OpenAI and Anthropic Claude as selectable generation engines.")

        col1, col2 = st.columns(2)

        # OPENAI CONFIG
        with col1:
            st.markdown("##### 🟢 OpenAI Configuration")
            existing_openai_key = AIManager.get_api_key(AI_PROVIDER_OPENAI) or ""
            masked_openai = f"...{existing_openai_key[-4:]}" if len(existing_openai_key) > 6 else ""

            openai_input = st.text_input(
                f"OpenAI API Key {f'({masked_openai} configured)' if masked_openai else '(Not set)'}",
                type="password",
                placeholder="sk-...",
                key="cfg_openai_key",
            )
            openai_model = st.text_input(
                "OpenAI Model Identifier",
                value=AIManager.get_setting("openai_default_model", "gpt-4o-mini"),
                key="cfg_openai_model",
            )

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Save OpenAI Key", key="save_openai"):
                    if openai_input.strip():
                        AIManager.set_setting("openai_api_key", openai_input.strip())
                    AIManager.set_setting("openai_default_model", openai_model.strip())
                    st.success("OpenAI settings saved.")
                    st.rerun()

            with c_btn2:
                if st.button("🧪 Test OpenAI", key="test_openai"):
                    provider = OpenAIProvider(api_key=AIManager.get_api_key(AI_PROVIDER_OPENAI), default_model=openai_model)
                    success, msg = provider.test_connection()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        # ANTHROPIC CONFIG
        with col2:
            st.markdown("##### 🟣 Anthropic Claude Configuration")
            existing_claude_key = AIManager.get_api_key(AI_PROVIDER_CLAUDE) or ""
            masked_claude = f"...{existing_claude_key[-4:]}" if len(existing_claude_key) > 6 else ""

            claude_input = st.text_input(
                f"Anthropic API Key {f'({masked_claude} configured)' if masked_claude else '(Not set)'}",
                type="password",
                placeholder="sk-ant-...",
                key="cfg_claude_key",
            )
            claude_model = st.text_input(
                "Anthropic Model Identifier",
                value=AIManager.get_setting("anthropic_default_model", "claude-3-5-sonnet-20241022"),
                key="cfg_claude_model",
            )

            c_c1, c_c2 = st.columns(2)
            with c_c1:
                if st.button("Save Claude Key", key="save_claude"):
                    if claude_input.strip():
                        AIManager.set_setting("anthropic_api_key", claude_input.strip())
                    AIManager.set_setting("anthropic_default_model", claude_model.strip())
                    st.success("Anthropic settings saved.")
                    st.rerun()

            with c_c2:
                if st.button("🧪 Test Claude", key="test_claude"):
                    provider = AnthropicProvider(api_key=AIManager.get_api_key(AI_PROVIDER_CLAUDE), default_model=claude_model)
                    success, msg = provider.test_connection()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        st.markdown("---")
        st.markdown("##### Default Active Provider")
        curr_def = AIManager.get_setting("default_ai_provider", AI_PROVIDER_OPENAI)
        def_choice = st.radio(
            "Default Provider:",
            options=[AI_PROVIDER_OPENAI, AI_PROVIDER_CLAUDE],
            index=0 if curr_def == AI_PROVIDER_OPENAI else 1,
            format_func=lambda x: "OpenAI" if x == AI_PROVIDER_OPENAI else "Anthropic Claude",
            horizontal=True,
            key="cfg_def_prov",
        )
        if st.button("Set as Default Provider"):
            AIManager.set_setting("default_ai_provider", def_choice)
            st.success(f"Default provider set to {def_choice.title()}.")
            st.rerun()

    # TAB 2: Sender Identity & Signature
    with tab_sender:
        st.markdown("#### Sender Identity Configuration")
        st.caption("Agency outreach must reflect a genuine human representative.")

        current_sender = AIManager.get_setting("sender_first_name", "")
        sender_input = st.text_input("Sender First Name", value=current_sender, placeholder="e.g. Alex", key="cfg_sender_name")

        st.markdown(
            """
            <div class="korvarc-card">
                <div class="korvarc-card-header">Signature Rule Preview</div>
                <div style="font-size: 0.88rem; color: #ECEFF4;">
            """,
            unsafe_allow_html=True,
        )
        if sender_input.strip():
            st.code(f"Best regards,\n{sender_input.strip()}", language="text")
        else:
            st.markdown("*(Sender first name is not set. Generated copy will remain unsigned without fake `[Your Name]` placeholders).*")
        st.markdown("</div></div>", unsafe_allow_html=True)

        if st.button("Save Sender Identity", type="primary"):
            AIManager.set_setting("sender_first_name", sender_input.strip())
            st.success("Sender name saved.")
            st.rerun()

    # TAB 3: Cost Safeguards & API Logs
    with tab_costs:
        st.markdown("#### Spending Safeguards & Cost Tracking")
        curr_max_cost = float(AIManager.get_setting("max_cost_per_request", "0.20"))
        new_max_cost = st.number_input("Max Cost per Single Generation (USD)", min_value=0.01, max_value=2.00, value=curr_max_cost, step=0.01)

        if st.button("Update Cost Safeguard"):
            AIManager.set_setting("max_cost_per_request", str(new_max_cost))
            st.success(f"Cost threshold updated to ${new_max_cost:.2f} USD")

        st.markdown("---")
        st.markdown("##### 📜 Recent API Generation Cost Logs")
        with get_db_session() as s:
            logs = s.query(ApiCostLog).order_by(ApiCostLog.timestamp.desc()).limit(15).all()
            if not logs:
                st.info("No API calls logged yet. Automated test calls remain free of paid APIs.")
            else:
                table_rows = []
                for l in logs:
                    table_rows.append({
                        "Time": l.timestamp.strftime("%m-%d %H:%M") if l.timestamp else "N/A",
                        "Provider": l.provider,
                        "Model": l.model,
                        "In Tokens": l.tokens_in,
                        "Out Tokens": l.tokens_out,
                        "Cost (USD)": f"${l.estimated_cost_usd:.5f}",
                        "Status": "Success" if l.success else f"Error: {l.error_message[:30]}",
                    })
                st.dataframe(table_rows, use_container_width=True)

    # TAB 4: Access PIN & Mobile Security
    with tab_security:
        st.markdown("#### Operator Access PIN & iPhone Connectivity")
        st.caption("Protect Korvarc OS so that only you can access it, whether on your Mac or your iPhone.")

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("##### 📱 Accessing from Your iPhone")
            st.markdown(
                """
                <div class="korvarc-card">
                    <div class="korvarc-card-header">Local Wi-Fi Connection</div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.6;">
                        1. Connect your iPhone to the <strong>same Wi-Fi network</strong> as this Mac.<br>
                        2. Open Safari on your iPhone and go to:<br>
                        <div style="background-color: #0D0F12; padding: 8px 12px; border-radius: 6px; font-family: monospace; color: #60A5FA; margin: 8px 0; font-size: 0.95rem;">
                            http://10.0.0.66:8501
                        </div>
                        3. (Optional) In Safari, tap <strong>Share</strong> &gt; <strong>Add to Home Screen</strong> to use Korvarc OS like a native app icon!
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s2:
            st.markdown("##### 🔒 Private Access PIN")
            curr_pin = AIManager.get_setting("access_pin", os.getenv("KORVARC_ACCESS_PIN", ""))
            status_text = "🔒 PIN Protection is ACTIVE" if curr_pin else "⚪ No PIN Set (Open on local network)"
            st.markdown(f"**Current Status:** {status_text}")

            pin_input = st.text_input(
                "Set New Operator PIN (Leave blank to disable)",
                value=curr_pin,
                type="password",
                placeholder="e.g. 8492 or mySecretPin",
                key="cfg_pin_input",
                help="When set, any browser or iPhone must enter this PIN once to access Korvarc OS.",
            )

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                if st.button("Save PIN", type="primary"):
                    AIManager.set_setting("access_pin", pin_input.strip())
                    st.session_state["is_authenticated"] = True
                    st.success("Access PIN saved.")
                    st.rerun()

            with c_p2:
                if curr_pin and st.button("Remove PIN"):
                    AIManager.set_setting("access_pin", "")
                    st.success("PIN protection disabled.")
                    st.rerun()

    # TAB 5: CASL & Anti-Spam
    with tab_compliance:
        st.markdown("#### Canadian Commercial Outreach & CASL Compliance")
        st.markdown(
            """
            <div class="korvarc-card">
                <div class="korvarc-card-header">Canada's Anti-Spam Legislation (CASL) Overview</div>
                <div style="font-size: 0.85rem; color: #94A3B8; line-height: 1.5;">
                    <p>Korvarc operates from <strong>Ontario, Canada</strong>. Under Canadian law and commercial standards:</p>
                    <ul>
                        <li><strong>No Assumption of Consent:</strong> A publicly listed business email address on YouTube does not automatically constitute express commercial marketing consent.</li>
                        <li><strong>Sender Identification:</strong> Commercial messages must clearly identify Korvarc and provide valid physical and electronic contact coordinates.</li>
                        <li><strong>Clear Opt-Out:</strong> Any creator or brand requesting to be removed must be marked as <code>Do Not Contact</code> in the CRM immediately.</li>
                        <li><strong>Draft-Only MVP:</strong> Korvarc OS Version 1 strictly produces local drafts. It does not contain automated warm-up networks, mass-sending bots, or unsolicited delivery sequences.</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
