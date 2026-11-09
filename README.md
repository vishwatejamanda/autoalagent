# AI Job Search & Auto-Apply Agent (LinkedIn + Naukri + Workday)

Production-grade personal AI agent running locally on your machine (No Docker needed). Discovers jobs across LinkedIn, Naukri, and Workday, ranks them using a two-stage evaluation engine, tailors resumes with an anti-fabrication fact-checking pass, and automates applications.

---

## Complete Feature Matrix

| Feature | Description | Status |
|---|---|---|
| **Multi-Provider LLM Layer** | Mistral AI + NVIDIA NIM (Nemotron) with automatic fallback and JSON schema validation | ✅ Built |
| **Master Profile (Single Source of Truth)** | PDF/DOCX parser, structured JSON editor; prevents candidate profile hallucinations | ✅ Built |
| **Job Search Personas** | Configurable profiles (e.g. "Software Engineer", "AI Engineer") with caps, keywords, and notice periods | ✅ Built |
| **ATS-Safe Resume Tailoring** | Dynamic keyword mirroring, custom summary, cover letter, and ATS keyword scoring | ✅ Built |
| **Strict Anti-Fabrication Fact-Check** | 2nd LLM pass diffing generated resume against Master Profile; rejects unverified skills | ✅ Built |
| **DOCX & PDF Builders** | Single-column, selectable text, standard ATS typography using python-docx & ReportLab | ✅ Built |
| **Job Discovery Adapters** | Workday (REST CXS + Playwright), LinkedIn (Easy Apply), and Naukri | ✅ Built |
| **Cross-Portal Deduplication** | RapidFuzz token set ratio matching on title + company + location & SHA-256 description hashes | ✅ Built |
| **Two-Stage Matcher** | Stage 1 (Fast rule & seniority filter) + Stage 2 (LLM fit evaluation & red flag detection) | ✅ Built |
| **Application Engine** | Headed Playwright automation with human delays, CAPTCHA detection, and screenshot logging | ✅ Built |
| **Answer Bank & Safety Guards** | Fuzzy question matching; strict requirement for manual approval on legal, salary & visa questions | ✅ Built |
| **Kanban Tracker & Manual Queue** | Visual funnel tracking (Found &rarr; Matched &rarr; Applied &rarr; Interview &rarr; Offer) + Manual Queue | ✅ Built |
| **Scheduler & Notifications** | APScheduler background worker + Telegram alerts for matches and CAPTCHAs | ✅ Built |
| **Security & Auditing** | Fernet encryption for portal credentials, global emergency kill switch, and full audit logs | ✅ Built |

---

## Quickstart (2 Commands)

### 1. Terminal 1 — Backend (FastAPI)

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

uvicorn app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

### 2. Terminal 2 — Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```
- Access Dashboard at `http://localhost:3000`

---

## Configuration (`.env`)

```env
# LLM Providers
MISTRAL_API_KEY=your-mistral-api-key
NVIDIA_API_KEY=your-nvidia-api-key
DEFAULT_PROVIDER=mistral

# Models
MISTRAL_STRONG_MODEL=mistral-large-latest
MISTRAL_CHEAP_MODEL=mistral-small-latest
NVIDIA_STRONG_MODEL=nvidia/llama-3.1-nemotron-70b-instruct
NVIDIA_CHEAP_MODEL=nvidia/llama-3.1-nemotron-51b-instruct

# Security (Fernet Key)
FERNET_KEY=w0YUrZmrMw5i340_cuLFNEA7BdmzzuFknn7IQVy_y6o=

# Telegram Alerts (Optional)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# App Settings
DATABASE_URL=sqlite:///./data/job_agent.db
BROWSER_PROFILE_DIR=./data/browser_profile
```

---

## Running the Automated Test Suite

Run the full pytest suite (17 tests covering deduplication, scoring rules, answer bank matching, fact-checking, and document generation):

```bash
cd backend
pytest -v
```

---

## Directory Structure

```
autoapply/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & lifespan
│   │   ├── config.py          # Pydantic BaseSettings & Fernet encryption
│   │   └── database.py        # SQLite WAL connection & session factory
│   ├── api/
│   │   ├── health.py          # System health check
│   │   ├── settings_api.py    # LLM configuration & connectivity tests
│   │   ├── profiles.py        # Master profile & persona CRUD
│   │   ├── resumes.py         # Tailoring, diff, DOCX/PDF download
│   │   ├── jobs.py            # Job search, scan trigger, Workday companies
│   │   ├── matching.py        # Review queue & batch scoring
│   │   ├── applications.py    # Application engine, tracker & kill switch
│   │   ├── answer_bank.py     # Question answer bank management
│   │   └── analytics.py       # Funnel stats, CSV export & DB backup
│   ├── llm/
│   │   ├── provider.py        # Abstract LLM provider interface
│   │   ├── mistral.py         # Mistral AI adapter
│   │   ├── nvidia.py          # NVIDIA NIM (Nemotron) adapter
│   │   └── router.py          # Multi-provider fallback & JSON repair
│   ├── sources/
│   │   ├── base.py            # Abstract job source adapter
│   │   ├── workday.py         # Workday CXS REST & Playwright adapter
│   │   ├── linkedin.py        # LinkedIn search & detail parser
│   │   ├── naukri.py          # Naukri search & detail parser
│   │   ├── selectors.json     # Externalized portal CSS selectors
│   │   └── workday_companies.yaml
│   ├── appliers/
│   │   ├── base.py            # Base applier with CAPTCHA detection
│   │   ├── workday.py         # Workday form filler (data-automation-id)
│   │   ├── linkedin.py        # LinkedIn Easy Apply dialog handler
│   │   └── naukri.py          # Naukri 1-click apply handler
│   ├── services/
│   │   ├── resume_parser.py   # PDF/DOCX resume text extraction & parsing
│   │   ├── resume_tailor.py   # Resume tailoring & caching engine
│   │   ├── fact_check.py      # Strict anti-fabrication 2nd LLM pass
│   │   ├── matcher.py         # Stage 1 (heuristic) & Stage 2 (LLM) matcher
│   │   ├── dedupe.py          # RapidFuzz cross-portal deduplication
│   │   ├── answer_bank.py     # Answer bank lookup & sensitive guard
│   │   ├── notifier.py        # Telegram bot alerts
│   │   └── scheduler.py       # APScheduler background tasks
│   ├── docs/
│   │   ├── builder_docx.py    # ATS-safe DOCX resume builder
│   │   └── builder_pdf.py     # ATS-safe ReportLab PDF resume builder
│   ├── models/                # SQLModel database tables
│   ├── schemas/               # Pydantic schemas
│   └── tests/                 # Full automated test suite
├── frontend/                  # Next.js (App Router) + Tailwind CSS + Lucide UI
├── data/                      # SQLite DB, generated resumes & screenshots
├── .env                       # Environment variables
└── README.md
```
