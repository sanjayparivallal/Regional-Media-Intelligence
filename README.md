# Regional Media Intelligence Agent (RMIA)

> **Transforming Regional Newspapers and e-Papers into Actionable, Traceable Media Intelligence.**

---

## 🌟 Core Product Principle

### **EVERY AI DECISION MUST BE TRACEABLE BACK TO THE ORIGINAL NEWSPAPER PAGE.**

RMIA is a full-stack, enterprise document-intelligence platform designed specifically for regional Indian print media and e-Papers. It automatically **harvests, processes, translates, and analyses** newspapers in Hindi, Tamil, Telugu, Bengali, Kannada, Malayalam, Marathi, Gujarati, Punjabi, Odia, Assamese, and English.

---

## 🤖 AI Model Stack (DO NOT REPLACE)

| Model | Role | Integration |
|---|---|---|
| **IndicOCR** | Regional-script OCR | `services/ocr_service.py` |
| **IndicTrans2** (`ai4bharat/indictrans2-indic-en-1B`) | Indic → English translation | `services/translation_service.py` |
| **LFM 2.5** (`LiquidAI/lfm2.5-2.6b:q4_k_m`) | Sentiment, crisis, entity analysis | `services/lfm_service.py` via Ollama |

> **Critical for agents:** Do NOT replace these models. Do NOT use spaCy NER or NLLB-200 as the primary pipeline.

---

## 🏛️ Complete Processing Pipeline

```
Automated Harvest OR Manual Upload
         │
         ▼
1.  ePaper Harvesting      (harvesting/ — auto-downloads 50+ newspaper sources)
2.  PDF Ingestion          (PyMuPDF + OpenCV preprocessing)
3.  Multilingual OCR       (IndicOCR — supports 12+ Indic scripts)
4.  Layout Analysis        (column detection, article segmentation)
5.  Language Detection     (Unicode range analysis + langdetect)
6.  Entity-Safe Translation (IndicTrans2 — Indic → English)
7.  Named Entity Recognition
8.  Brand Matching         (exact, alias, fuzzy, context)
9.  Sentiment Analysis     (LFM 2.5 via Ollama)
10. Crisis Classification  (12 categories: Regulatory, Fraud, Lawsuit…)
11. Explainable Risk Score (5-factor weighted formula)
12. Alert Generation       (deduplication, evidence linking)
13. Evidence Viewer        (bounding box overlay + audit trail)
14. Human Review           (approve/reject/edit AI decisions)
```

---

## 📰 Harvesting System

RMIA includes a fully automated ePaper harvesting module (`backend/harvesting/`) that discovers and downloads Indian newspapers daily using a **configuration-driven, strategy-based** architecture.

### Architecture

```
backend/harvesting/
  ├── config/newspapers.json   ← ALL source configs here (no hardcoded if/else)
  ├── core/
  │   ├── base.py              ← BaseHarvester abstract class
  │   ├── registry.py          ← source_type → harvester strategy selector
  │   ├── models.py            ← Pydantic models: Source, HarvestJob, Attempt
  │   ├── downloader.py        ← Streaming PDF downloader (retry, backoff, atomic)
  │   ├── validator.py         ← PDF validator (header + PyMuPDF + page count)
  │   └── storage.py           ← ExcelStorageService adapter for harvest sheets
  ├── harvesters/
  │   ├── direct_pdf.py        ← URL-template sources (date substitution)
  │   ├── playwright.py        ← JS-rendered sites (DOM PDF discovery)
  │   ├── authenticated.py     ← Session-persistent auth sites
  │   └── aggregator.py        ← Aggregator sites
  ├── scheduler.py             ← APScheduler daily cron (configurable IST time)
  ├── service.py               ← HarvestingService: parallel workers, error isolation
  ├── utils.py                 ← IST dates, SHA-256, path generation, URL templates
  └── exceptions.py            ← HarvestError, AuthRequired, CaptchaRequired, etc.
```

### Harvesting API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/harvesting/sources` | List all newspaper sources with last harvest state |
| `PATCH` | `/api/harvesting/sources/{id}` | Enable/disable a source |
| `POST` | `/api/harvesting/run` | **Trigger harvest NOW** (manual, with date picker) |
| `POST` | `/api/harvesting/run/scheduled` | Run the scheduled harvest immediately |
| `GET` | `/api/harvesting/jobs` | List recent harvest jobs |
| `GET` | `/api/harvesting/jobs/{job_id}` | Job detail with per-source attempt breakdown |
| `GET` | `/api/harvesting/documents` | Documents downloaded by harvesting (filtered) |
| `POST` | `/api/harvesting/sources/{id}/reauthenticate` | Get reauthentication instructions |

### Manual Trigger (Key Feature)

The `POST /api/harvesting/run` endpoint triggers a harvest immediately without waiting for the scheduler. The frontend has a **"Run Harvest Now"** button and a **"Run Scheduled"** button.

- Returns immediately with `{ job_id, status: "RUNNING", poll_url }`
- Poll `GET /api/harvesting/jobs/{job_id}` for progress updates
- Frontend auto-polls every 4 seconds while a harvest is running

### Adding a New Newspaper Source

Edit `backend/harvesting/config/newspapers.json` — no code changes needed:

```json
{
  "id": "my_paper",
  "name": "My Newspaper",
  "publisher": "Publisher Name",
  "language": "Tamil",
  "language_code": "ta",
  "region": "Tamil Nadu",
  "source_type": "direct_pdf",
  "enabled": true,
  "url_template": "https://example.com/epaper/{yyyy}/{mm}/{dd}/edition.pdf"
}
```

**`source_type` options:**
- `direct_pdf` — Known URL with `{yyyy}`, `{mm}`, `{dd}` tokens
- `playwright` — JS-rendered page (DOM PDF link discovery)
- `authenticated` — Login-required sites (session persistence)
- `aggregator` — Aggregator websites

### Scheduling

Daily harvest runs automatically at the time configured in `.env`:

```
HARVEST_SCHEDULE=06:30        # HH:MM in HARVEST_TIMEZONE
HARVEST_TIMEZONE=Asia/Kolkata
HARVEST_MAX_CONCURRENCY=5     # Parallel downloads
```

The scheduler starts automatically when the FastAPI backend starts.

### Authentication (Subscription Sources)

For sources requiring login, set env vars and enable in `newspapers.json`:

```env
THE_HINDU_USERNAME=your@email.com
THE_HINDU_PASSWORD=yourpassword
```

Then enable the source:
```json
{ "id": "the_hindu", "enabled": true, ... }
```

CAPTCHA/MFA: If detected, the source is marked `CAPTCHA_REQUIRED` and skipped — **never bypassed**.

---

## 💾 Storage Architecture

> **Agent note:** There is NO SQLAlchemy ORM in the active code. `database.py` was removed. All data persists via `ExcelStorageService` (openpyxl-backed Excel workbook at `backend/rmi_db.xlsx`).

| Sheet | Contents |
|---|---|
| `Documents` | All uploaded/harvested PDFs |
| `Pages` | Rendered page images + OCR results |
| `Articles` | Segmented articles |
| `Translations` | IndicTrans2 outputs |
| `Alerts` | Generated intelligence alerts |
| `AuditLogs` | 14-stage processing trace |
| `HarvestJobs` | Harvest run summaries |
| `HarvestAttempts` | Per-source download attempt records |

**Rules for agents:**
- Import via `from storage.excel_storage_service import ExcelStorageService`
- Use `excel.append_row(sheet, dict)`, `excel.find_row(sheet, filter_dict)`, `excel.update_row(...)`, `excel.find_rows(...)`
- Never use SQLAlchemy session or `database.py`

---

## 📊 Risk Score Engine

$$\text{Risk Score} = \text{Sentiment}(30\%) + \text{Brand}(25\%) + \text{Topic}(20\%) + \text{Reach}(15\%) + \text{Confidence}(10\%)$$

---

## 🛠️ Technology Stack

- **Frontend**: Next.js (App Router), TypeScript, Vanilla CSS + CSS modules, Lucide Icons, Recharts
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, openpyxl (ExcelStorageService)
- **Document Processing**: PyMuPDF, OpenCV, Pillow
- **OCR**: IndicOCR (primary), EasyOCR + PaddleOCR (fallback)
- **Translation**: IndicTrans2 (`ai4bharat/indictrans2-indic-en-1B`)
- **Analysis**: LFM 2.5 via Ollama (`LiquidAI/lfm2.5-2.6b:q4_k_m`)
- **Harvesting**: Playwright (async), APScheduler, httpx (streaming downloader)
- **Testing**: PyTest, PyTest-Asyncio

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama running with `LiquidAI/lfm2.5-2.6b:q4_k_m` loaded

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JS-rendered newspaper sites)
playwright install chromium

# Copy environment file
cp ../.env.example ../.env
# Edit .env as needed

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### API Documentation

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Testing

```bash
cd backend
.\venv\Scripts\python.exe -m pytest tests/ -v
```

Tests cover: PDF classification, OCR confidence, layout analysis, language detection, translation, brand matching, sentiment, crisis classification, risk scoring, alert deduplication, and pipeline integration.

---

## 📂 Project Structure

```
.
├── backend/
│   ├── api/                 # REST API routers
│   │   ├── documents.py     # Upload, process, status
│   │   ├── alerts.py        # Intelligence alerts
│   │   ├── routes.py        # Articles, brands, analytics, audit…
│   │   └── harvesting.py    # ePaper harvesting endpoints
│   ├── harvesting/          # Automated harvesting system
│   │   ├── config/
│   │   │   └── newspapers.json  ← ADD NEW SOURCES HERE
│   │   ├── core/            # Base, registry, downloader, validator, storage
│   │   ├── harvesters/      # direct_pdf, playwright, authenticated, aggregator
│   │   ├── service.py       # Orchestrator (parallel workers, error isolation)
│   │   └── scheduler.py     # APScheduler daily cron
│   ├── models/              # Pydantic models (Document, Page, Article…)
│   ├── schemas/             # API request/response schemas
│   ├── pipeline/            # AI Intelligence Pipeline
│   │   ├── ingestion/       # PDF classifier, page renderer, preprocessor
│   │   ├── ocr/             # IndicOCR, EasyOCR, PaddleOCR providers
│   │   ├── layout/          # Column detection, article segmentation
│   │   ├── nlp/             # Language detection, IndicTrans2, NER, sentiment, crisis
│   │   └── alerting/        # Alert generation, deduplication, risk scoring
│   ├── services/            # IndicOCR, IndicTrans2, LFM service wrappers
│   ├── workers/
│   │   └── processor.py     # 3-phase background pipeline: OCR → Translate → Analyse
│   ├── tests/               # Pytest suite
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (pydantic-settings, reads .env)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   │   ├── ingestion/   # Manual PDF upload + pipeline progress
│   │   │   ├── harvesting/  # ePaper harvesting dashboard
│   │   │   ├── alerts/      # Intelligence alerts
│   │   │   ├── evidence/    # Bounding box evidence viewer
│   │   │   └── …
│   │   └── lib/
│   │       └── api.ts       # Centralized API client (all fetch calls)
│   └── next.config.ts       # Proxies /api/* → backend
├── .env                     # Environment variables (never commit secrets)
├── .env.example             # Template for new developers
└── README.md
```

---

## 🔑 Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `OCR_ENGINE` | `indic-ocr` | OCR engine selection |
| `TRANSLATION_MODEL` | `ai4bharat/indictrans2-indic-en-1B` | IndicTrans2 model |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama endpoint |
| `LFM_MODEL_NAME` | `LiquidAI/lfm2.5-2.6b:q4_k_m` | LFM 2.5 model |
| `HARVEST_SCHEDULE` | `06:30` | Daily harvest time (HH:MM IST) |
| `HARVEST_TIMEZONE` | `Asia/Kolkata` | Harvest timezone |
| `HARVEST_MAX_CONCURRENCY` | `5` | Parallel source downloads |
| `HARVEST_NEWSPAPERS_CONFIG` | `./harvesting/config/newspapers.json` | Source config path |
| `{PREFIX}_USERNAME` | — | Source login username |
| `{PREFIX}_PASSWORD` | — | Source login password |

---

## 🛡️ Design Rules (For Agents)

1. **Never hardcode newspaper names** — use `newspapers.json` config
2. **Never bypass CAPTCHA or MFA** — mark `CAPTCHA_REQUIRED` and continue
3. **Never log credentials** — read from env vars only, never log values
4. **Always use ExcelStorageService** — not SQLAlchemy, not sqlite3 directly
5. **Never replace IndicOCR, IndicTrans2, or LFM 2.5** — these are the required stack
6. **Preserve traceability** — every alert must link back to PDF page via `document_id → page_id → bounding_box`
7. **Error isolation** — one source/page failure must never stop the overall job


---

## 🏛️ End-to-End Pipeline Architecture

```
Regional Newspaper PDF / Image
  │
  ├── 1. Ingestion & Preprocessing (PyMuPDF, OpenCV contrast/adaptive thresholding)
  ├── 2. Multilingual OCR Pipeline (PaddleOCR, Tesseract, confidence scoring)
  ├── 3. Layout Analysis & Article Segmentation (Column detection, headline/body grouping)
  ├── 4. Script & Language Detection (Unicode range analysis, langdetect)
  ├── 5. Entity-Preserving Translation (NLLB-200 local model, fallback transliteration)
  ├── 6. Named Entity Recognition (Regulator, Organization, Location, Person)
  ├── 7. Brand Matching (Exact, alias, fuzzy, and context matching)
  ├── 8. Multilingual Sentiment Analysis (XLM-RoBERTa + lexicon scoring)
  ├── 9. Crisis & Topic Classification (12 categories: Regulatory, Fraud, Lawsuit, etc.)
  ├── 10. Explainable Risk Score (5-factor weighted formula)
  ├── 11. Alert Generation & Deduplication (Cryptographic fingerprinting)
  └── 12. Traceable Evidence Viewer & Human Review (Bounding box overlay & audit trail)
```

---

## 📊 Explainable Risk Score Engine

Risk scores are 100% explainable, computed using a 5-factor weighted model:

$$\text{Risk Score} = \text{Sentiment}(30\%) + \text{Brand}(25\%) + \text{Topic}(20\%) + \text{Reach}(15\%) + \text{Confidence}(10\%)$$

| Factor | Weight | Description |
|---|---|---|
| **Sentiment Severity** | **30%** | Negative sentiment severity scaled by model confidence |
| **Brand Relevance** | **25%** | Direct mention vs alias vs keyword match confidence |
| **Topic Severity** | **20%** | Crisis category weight (Fraud: 0.95, Regulatory: 0.85, Safety: 0.90) |
| **Publication Reach** | **15%** | Tier 1 (national) vs Tier 2 (state) vs Tier 3 (district) circulation |
| **AI Confidence** | **10%** | Composite OCR, language, and model certainty score |

---

## 🚀 Key Features

- **Multi-Panel Evidence Viewer**: View original scanned newspaper pages with interactive bounding boxes highlighting the exact location of the article, side-by-side with OCR text, translated English text, extracted entities, and risk breakdown.
- **Human Review & Feedback Loop**: Human reviewers can approve, edit, or reject AI detections, continuously training and tuning confidence thresholds.
- **Full Audit Trail**: Immutable 14-stage processing log capturing timestamps, models utilized, and execution durations for every document.
- **No External API Keys Required**: Built completely on open-source, local models (PaddleOCR, Tesseract, NLLB-200, XLM-RoBERTa, spaCy) with zero external cloud dependencies and full offline demo mode.
- **Modern Next.js 16 Interface**: Premium Vibrant Light Intelligence UI with glassmorphism, KPI cards, real-time pipeline visualizers, and interactive Recharts dashboards.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4, Lucide Icons, Recharts
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL / SQLite, Pydantic v2
- **Document Processing**: PyMuPDF, OpenCV, Pillow, pdf2image
- **OCR & NLP**: PaddleOCR, Tesseract, spaCy, NLLB-200, XLM-RoBERTa
- **Testing**: PyTest, PyTest-Asyncio

---

## ⚡ Quick Start

### 1. Using Docker Compose (Recommended)

Run the entire platform (PostgreSQL database, FastAPI backend, and Next.js frontend) with a single command:

```bash
docker-compose up --build
```

- **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database**: PostgreSQL on `localhost:5432`

---

### 2. Manual Local Development

#### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn main:app --reload --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install packages
npm install

# Start Next.js development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to access the dashboard.

---

## 🧪 Testing

Run the automated backend test suite:

```bash
cd backend
python -m pytest tests/ -v
```

All 28 tests cover:
- PDF classification
- Multi-signal OCR confidence calculations
- Layout analysis and column-first segmentation
- Script and language detection
- Translation with entity protection
- Brand and alias fuzzy matching
- Sentiment analysis & lexicon fallback
- Crisis topic classification
- 5-factor explainable risk scoring
- Alert deduplication and fingerprinting
- End-to-end media intelligence pipeline flow

---

## 📂 Project Structure

```
.
├── backend/
│   ├── api/                 # REST API endpoints (documents, alerts, brands, analytics, etc.)
│   ├── models/              # SQLAlchemy ORM models (Document, Page, Article, Alert, etc.)
│   ├── schemas/             # Pydantic validation schemas
│   ├── pipeline/            # AI Intelligence Pipeline
│   │   ├── ingestion/       # PDF classifier, page renderer, OpenCV preprocessor
│   │   ├── ocr/             # PaddleOCR, Tesseract, OCR confidence calculator
│   │   ├── layout/          # Column detection, block classifier, article segmentation
│   │   ├── nlp/             # Language detection, NLLB translation, NER, sentiment, crisis
│   │   └── alerting/        # Alert generation, deduplication, risk scoring
│   ├── workers/             # Background document processing worker
│   ├── seed/                # Demo data seeder (brands.json, publications.json)
│   ├── tests/               # Pytest suite
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and settings
│   ├── database.py          # Async database setup
│   └── Dockerfile           # Backend container definition
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router pages (Overview, Alerts, Evidence, Ingestion...)
│   │   ├── components/      # Reusable UI components (RiskScore, Sidebar, KPICard...)
│   │   └── lib/             # API client & types
│   ├── tailwind.config.ts   # Design tokens & color palette
│   └── Dockerfile           # Frontend container definition
├── docker-compose.yml       # Production stack orchestration
└── README.md                # Documentation
```

---

## 🛡️ License

Built for Regional Media Intelligence hackathons and enterprise media monitoring operations.
