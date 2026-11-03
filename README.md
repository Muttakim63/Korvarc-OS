# KORVARC OS

> **Local AI Agency Platform for Technical Creator & Brand Sponsorship Matchmaking**  
> Agency: **Korvarc** | Representation Model: **Strictly Non-Exclusive, per campaign** | Location: **Ontario, Canada**

---

## ⚡ Overview

**KORVARC OS** is a premium, locally hosted full-stack application designed specifically for running a high-signal tech influencer marketing and commercial sponsorship agency.

Built for male technical content creators and developer-focused SaaS companies across **AI, Machine Learning, Data Science, Python, Software Engineering, Developer Tools, and Cloud Infrastructure**, Korvarc OS empowers agency operators to:
1. Conduct grounded, factual research on creators and brands without fabricating claims.
2. Generate concise, commercial peer-to-peer outreach emails (~50 words for creators, 50–90 words for brands) with 3 curiosity-driven subject lines.
3. Switch effortlessly between **OpenAI** and **Anthropic Claude**, or run an opt-in side-by-side comparison.
4. Adapt to operator writing preferences via a **3-tier persistent memory engine** with explicit human confirmation.
5. Manage an Influencer CRM (with CSV/XLSX import and duplicate detection) and Brand CRM (with explainable creator-brand matching).
6. Track campaigns, deliverables, and confirmed agency commissions with uninflated analytics.

**Important Note on v1.0:** The initial release is **strictly draft-only**. It does NOT contain automated sending sequences, artificial warm-up networks, or spam bots. All drafts are stored locally for operator review and export.

---

## 🏛️ Architecture & Project Structure

```
korvarc-os/
├── app.py                     # Main Streamlit application entrypoint & router
├── run.sh                     # One-click launch script
├── requirements.txt           # Python dependency requirements
├── pyproject.toml / pytest.ini# Test and build configuration
├── .env.example               # Environment variables template
├── .gitignore                 # Secrets, SQLite DBs, and venv exclusion
├── korvarc/
│   ├── config.py              # Agency constants, defaults, and placeholder checks
│   ├── database/
│   │   ├── connection.py      # SQLite connection manager & baseline rule seeding
│   │   └── schema.py          # SQLAlchemy models (Influencer, Brand, Draft, Rule, Campaign, CostLog)
│   ├── models/
│   │   └── schemas.py         # Pydantic schemas (Research, Generation, Feedback, Comparison)
│   ├── ai/
│   │   ├── base.py            # Base provider interface, cost tracker & validation
│   │   ├── prompts.py         # System prompts enforcing Korvarc commercial peer standards
│   │   ├── openai_provider.py # OpenAI adapter with JSON schema validation & token costing
│   │   ├── anthropic_provider.py # Anthropic Claude adapter with structured JSON extraction
│   │   └── manager.py         # Provider selector, credential discovery, safeguards, side-by-side
│   ├── research/
│   │   ├── fetcher.py         # SSRF-protected HTTP client (blocks private/loopback IPs & redirects)
│   │   ├── youtube.py         # Legitimate YouTube metadata extraction (oEmbed) & transparent fallbacks
│   │   ├── web.py             # Public web scraping with anti-prompt-injection sanitization
│   │   └── engine.py          # Grounded dossier builder (verified vs user-supplied vs unknowns)
│   ├── feedback/
│   │   └── memory.py          # 3-tier memory engine (Global, Outreach-type, Prospect/niche)
│   ├── crm/
│   │   ├── influencer_crm.py  # Creator CRUD, status management, CSV import & duplicate detection
│   │   ├── brand_crm.py       # Brand CRUD & explainable creator matchmaking
│   │   ├── campaign_crm.py    # Commercial deals, deliverables & 20% commission tracking
│   │   └── analytics.py       # Real database analytics (no fake reply or open rates)
│   ├── library/
│   │   └── email_library.py   # Searchable drafts archive, revision history, and CSV export
│   └── ui/
│       ├── theme.py           # Premium Dark theme CSS (charcoal #0D0F12, metallic accents)
│       ├── components.py      # Metric tiles, verification badges, warning banners
│       └── views/             # 9 specialized application screens
├── data/
│   └── sample_influencers.csv # Realistic sample import dataset with historical rate references
└── tests/
    ├── conftest.py            # Isolated SQLite test fixtures & mocked provider responses
    └── test_scenarios.py      # Automated test suite covering Scenarios A through L
```

---

## 🚀 Mac Installation & Launch

### Prerequisites
- macOS (Apple Silicon or Intel)
- Python 3.11+ (Python 3.14 supported)

### Step 1: Clone or Navigate to the Project
```bash
cd /Users/shuprov630/.gemini/antigravity/scratch/korvarc-os
```

### Step 2: Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run the Application
You can use the convenient launch script:
```bash
./run.sh
```
Or run Streamlit directly:
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🔑 AI Provider Configuration (OpenAI & Claude)

Korvarc OS supports **both OpenAI and Anthropic Claude**. Subscriptions to ChatGPT Plus or Claude Pro do not provide API access; standard API keys from platform consoles are required.

### Setting Keys via the UI (Recommended)
1. In the sidebar, navigate to **Settings** (`⚙️ Settings`).
2. Enter your **OpenAI API Key** (`sk-...`) and/or **Anthropic API Key** (`sk-ant-...`).
3. Click **🧪 Test OpenAI** or **🧪 Test Claude** to verify live connectivity.
4. Choose your preferred **Default Provider**.

### Setting Keys via `.env`
Alternatively, copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and fill in your keys:
```ini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_AI_PROVIDER=openai
OPENAI_DEFAULT_MODEL=gpt-4o-mini
ANTHROPIC_DEFAULT_MODEL=claude-3-5-sonnet-20241022
MAX_COST_PER_REQUEST_USD=0.20
KORVARC_SENDER_FIRST_NAME=
```

### Offline / Missing Keys Behavior
If API credentials are not provided:
- AI generation is safely disabled with an honest notice.
- No fake or simulated AI outputs are presented as real generations.
- You can manually compose, edit, and store drafts in the Email Library.
- Grounded web and YouTube research, CRM, CSV imports, and Analytics remain 100% operational.

---

## ✍️ Agency Writing Standards & Grounding

Korvarc OS enforces strict sponsorship agency writing rules:
- **Commercial Peer Mindset:** You bring real commercial value. Never sound needy, robotic, or flattering.
- **Forbidden Fanboy Phrases:** `I love your content`, `I'm a huge fan`, `I stumbled across your channel`, `Your engagement is incredible`.
- **Target Word Count:** Approximately 50 words for creators (2-3 concise paragraphs); 50–90 words for brands.
- **CTA:** Exactly one low-friction, reply-oriented question (`Would you be interested?` or `Open to exploring this?`). No meeting booking links.
- **Signature & Placeholders:** Unsigned if sender first name is not set in Settings. The system warns if a draft contains placeholders such as `[Your Name]`.
- **Factual Grounding:** Potential brand matches are identified as matchmaking suggestions, never claimed as confirmed partners or secured budgets.

---

## 🧠 3-Tier AI Feedback Memory Engine

Korvarc OS uses **retrieval-based learning**:
- **Level 1 (Global):** Core agency rules (non-exclusive representation, commercial peer tone).
- **Level 2 (Outreach-Type):** Influencer-specific (~50w, curiosity subjects) vs. Brand-specific (50-90w, product fit).
- **Level 3 (Contextual):** Niche or campaign-specific examples and rejection lessons.

### Human Confirmation Process
When you reject a draft and supply feedback (e.g. *"Keep influencer emails around 50 words"* or *"Stop opening with 'I came across your channel'"*), the system proposes a rule in the **AI Memory** tab (`⏳ Proposed Rules`). Once you review and approve it, the rule is automatically injected into future prompt contexts. Feedback steers generation prompts—it does not claim to retrain proprietary foundation model weights.

---

## 🧪 Automated Test Suite (Scenarios A through L)

Automated tests cover all required acceptance scenarios:
- **TEST A:** Grounded research, SSRF defense (blocking `127.0.0.1`, `localhost`, `192.168.1.1`), and transparent user fallback when scraping is limited.
- **TEST B:** Generation of 3 curiosity subject lines and 1 recommended draft within ~50 words.
- **TEST C:** Seamless switching between OpenAI and Claude without changing workflow.
- **TEST D:** Draft persistence across database sessions.
- **TEST E:** Rejection feedback creating proposed memory rules and successful retrieval into future generation prompts upon approval.
- **TEST F:** Editing, approving, and retrieving versioned drafts.
- **TEST G:** Ensuring creator prospects are never described as confirmed clients or exclusive talent.
- **TEST H:** Detection of ungrounded brand partnership claims and `[Your Name]` placeholders.
- **TEST I:** CSV bulk import and deduplication by email and profile URL.
- **TEST J:** Honest offline behavior when API credentials are absent.
- **TEST K:** Verification that Version 1 is strictly draft-only with no automatic sending capability.
- **TEST L:** Verification that analytics compute strictly from stored database records.

### Running the Tests
```bash
source .venv/bin/activate
pytest -v
```
All 12 test scenarios pass with zero failures.

---

## 🇨🇦 Legal, Compliance & Privacy

- **Canadian Anti-Spam Legislation (CASL):** Publicly available business emails on YouTube do not constitute express commercial marketing consent. Korvarc OS encourages verified sender identification, opt-out honorings (`Do Not Contact` CRM status), and draft-only approvals.
- **SSRF Defense:** Initial URLs and all HTTP redirect targets are resolved and validated against private IPv4/IPv6 address blocks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, loopbacks).
- **Untrusted Content:** Scraped websites and user transcripts are treated as untrusted text and sanitized against prompt injection patterns (`ignore previous instructions`, `system:`, etc.).
- **Data Privacy:** All data is stored locally in your SQLite database (`korvarc.db`). No telemetry containing creator or brand prospect data is transmitted externally.

---

## 📋 Recommended Workspace Notice
To keep this project easily accessible inside your Google Antigravity environment, recommend setting `/Users/shuprov630/.gemini/antigravity/scratch/korvarc-os` as your active workspace in Antigravity IDE.

