# Regional Media Intelligence Agent (RMIA)

> **Transforming Regional Newspapers and e-Papers into Actionable, Traceable Media Intelligence.**

---

## 🌟 Core Product Principle

### **EVERY AI DECISION MUST BE TRACEABLE BACK TO THE ORIGINAL NEWSPAPER PAGE.**

This system is not a standard text-based CRUD application. It is a full-stack, enterprise document-intelligence platform designed specifically for regional Indian print media and e-Papers (Hindi, Tamil, Telugu, Bengali, Kannada, Malayalam, Marathi, English).

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
