# Regional Media Intelligence Agent — Frontend Reference

> **Last Updated**: September 2026  
> Keep this file updated as the project evolves so future sessions don't need to re-audit the codebase.

---

## Project Overview

**Purpose**: AI-powered regional media intelligence platform that ingests Indian newspaper broadsheet PDFs, runs an OCR + NER + translation + sentiment pipeline, detects brand mentions, and surfaces actionable alerts.

**Stack**:
- **Frontend**: Next.js 14 (App Router, Client Components), Tailwind CSS with custom config
- **Backend**: Python FastAPI + SQLAlchemy (async) + PostgreSQL + pgvector
- **AI Pipeline**: PaddleOCR → Tesseract (fallback) → EasyOCR → NLLB-200 translation → spaCy NER + gazetteer → XLM-RoBERTa sentiment → XLM-RoBERTa crisis classification

---

## Directory Structure

```
d:\projects\vee\
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings via pydantic-settings
│   ├── database.py                # Async SQLAlchemy engine + get_db()
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── document.py            # Document, Page, Article
│   │   ├── intelligence.py        # Alert, Mention, Translation, Entity, Incident
│   │   ├── brand.py               # Brand, BrandAlias
│   │   ├── review.py              # Review, AuditLog
│   │   └── publication.py         # Publication
│   ├── schemas/                   # Pydantic response schemas
│   ├── api/
│   │   ├── routes.py              # articles, reviews, brands, analytics, audit, search, publications, incidents routers
│   │   ├── alerts.py              # alerts router (CRUD + evidence endpoint)
│   │   └── documents.py           # documents router (upload, process, cancel, delete, jobs)
│   ├── pipeline/
│   │   ├── orchestrator.py        # ModelOrchestrator — singleton, coordinates all AI models
│   │   ├── ocr/                   # OCR providers: paddle, tesseract, easyocr, hybrid
│   │   ├── nlp/
│   │   │   ├── entity/
│   │   │   │   ├── extractor.py   # EntityExtractor (uses module-level spaCy singleton)
│   │   │   │   └── brand_matcher.py
│   │   │   ├── sentiment/
│   │   │   │   ├── analyzer.py    # SentimentAnalyzer (module-level transformer singleton)
│   │   │   │   └── lexicon.py
│   │   │   ├── translation/       # NLLB provider + fallback
│   │   │   └── crisis/            # CrisisClassifier
│   │   ├── alerting/generator.py  # Alert generation + deduplication
│   │   └── ingestion/preprocessor.py
│   └── workers/processor.py       # Main async document processing worker
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js App Router pages
│   │   │   ├── page.tsx           # Dashboard overview
│   │   │   ├── alerts/page.tsx    # Alert management table
│   │   │   ├── brands/page.tsx    # Brand profile management (CRUD + delete + toggle)
│   │   │   ├── coverage/page.tsx  # Coverage analytics
│   │   │   ├── documents/page.tsx # Document archive
│   │   │   ├── evidence/page.tsx  # Evidence explorer (search)
│   │   │   ├── evidence/[id]/page.tsx  # Evidence dossier viewer
│   │   │   ├── incidents/page.tsx # Incident lifecycle
│   │   │   ├── ingestion/page.tsx # File upload (drag-drop)
│   │   │   ├── mentions/page.tsx  # Brand mention stream (live API)
│   │   │   ├── processing/page.tsx # Pipeline progress (polls every 8s)
│   │   │   ├── reviews/page.tsx   # Human-in-the-loop review queue
│   │   │   ├── publications/page.tsx # Publication registry
│   │   │   ├── audit/page.tsx     # AI decision audit trail (doc selector)
│   │   │   └── settings/page.tsx  # System configuration (static display)
│   │   ├── components/
│   │   │   ├── layout/Sidebar.tsx # Navigation sidebar
│   │   │   └── alerts/RiskScore.tsx
│   │   └── lib/
│   │       └── api.ts             # Centralized API client (all fetch calls go here)
│   ├── .env.local                 # NEXT_PUBLIC_API_URL=/api, NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
│   └── next.config.ts             # Rewrites /api/* → backend, /storage/* → backend
```

---

## API Client — `src/lib/api.ts`

All backend calls go through the `api` object. Base URL is `/api` (proxied to `http://127.0.0.1:8000/api` via `next.config.ts`).

| Method | Endpoint | Notes |
|--------|----------|-------|
| `api.getOverview()` | `GET /analytics/overview` | Dashboard KPI stats |
| `api.getCoverage()` | `GET /analytics/coverage` | Language + sentiment distribution |
| `api.getAlerts(params)` | `GET /alerts` | Optional `?priority=`, `?limit=` |
| `api.getAlert(id)` | `GET /alerts/:id` | |
| `api.getAlertEvidence(id)` | `GET /alerts/:id/evidence` | Returns `{alert, article, page, document, translations, entities, audit_trail}` |
| `api.getDocuments(status?)` | `GET /documents?status=` | Optional status filter |
| `api.uploadDocument(file, meta)` | `POST /documents/upload` | multipart/form-data |
| `api.processDocument(id)` | `POST /documents/:id/process` | |
| `api.cancelDocument(id)` | `POST /documents/:id/cancel` | |
| `api.deleteDocument(id)` | `DELETE /documents/:id` | |
| `api.getDocumentJobs(id)` | `GET /documents/:id/jobs` | Pipeline job progress |
| `api.getMentions(params)` | `GET /articles/mentions/all` | `{id, brand_name, headline, snippet, publication_name, language, sentiment, risk_score, date, page_number}` |
| `api.getBrands()` | `GET /brands` | |
| `api.createBrand(data)` | `POST /brands` | |
| `api.updateBrand(id, data)` | `PATCH /brands/:id` | Used for `active` toggle |
| `api.deleteBrand(id)` | `DELETE /brands/:id` | |
| `api.getReviews(params)` | `GET /reviews` | |
| `api.updateReview(id, data)` | `PATCH /reviews/:id` | `{status, reviewer, correction, review_notes}` |
| `api.getIncidents(params)` | `GET /incidents` | |
| `api.getArticles(params)` | `GET /articles` | |
| `api.getArticle(id)` | `GET /articles/:id` | |
| `api.search(query)` | `GET /search?q=` | Returns `{articles:[{id,headline,type}], alerts:[{id,title,type,priority}], brands:[{id,name,type}]}` |
| `api.getPublications()` | `GET /publications` | |
| `api.getAuditTrail(docId)` | `GET /audit/:document_id` | Array of `AuditLog` entries |
| `api.getSystemInfo()` | `GET /system/info` | Not yet implemented on backend |

> ⚠️ **Search returns shallow objects** — not full article details. `{id, headline, type}` only. Fetch `/articles/:id` for full details.

---

## Backend API Routers (registered in `main.py`)

| Router | Prefix | File |
|--------|--------|------|
| documents | `/api/documents` | `api/documents.py` |
| alerts | `/api/alerts` | `api/alerts.py` |
| articles | `/api/articles` | `api/routes.py` |
| reviews | `/api/reviews` | `api/routes.py` |
| brands | `/api/brands` | `api/routes.py` |
| analytics | `/api/analytics` | `api/routes.py` |
| audit | `/api/audit` | `api/routes.py` |
| search | `/api/search` | `api/routes.py` |
| publications | `/api/publications` | `api/routes.py` |
| incidents | `/api/incidents` | `api/routes.py` |

---

## Key Design Patterns

### State Management
Pages use `useEffect` + `useState` + async `load()` functions. Pattern:
```tsx
const [data, setData] = useState<T[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  async function load() {
    try {
      setData(await api.getSomething());
    } catch (e: any) {
      setError(e.message);
    } finally { setLoading(false); }
  }
  load();
}, []);
```

### CSS Classes (Tailwind Custom Utilities)
Defined in `globals.css`:
- `.glass-card` — white card with border + shadow
- `.kpi-card` — stat card with color variants: `primary`, `emerald`, `cyan`, `violet`, `coral`
- `.badge` — inline label with color variants: `badge-critical`, `badge-high`, `badge-medium`, `badge-low`, `badge-positive`, `badge-negative`, `badge-neutral`
- `.btn-primary` — primary action button
- `.btn-secondary` — secondary action button
- `.nav-item` — sidebar navigation link

---

## Backend AI Pipeline Notes

### spaCy — Windows DLL Issue
**Problem**: `DLL load failed while importing example: An Application Control policy has blocked this file`  
**Root cause**: Windows Defender Application Control blocks spaCy's native DLL.  
**Fix applied**: `extractor.py` uses a **module-level singleton** `_get_spacy_model()` — warning logged once, subsequent calls are silent. Entity extraction falls back to regex gazetteers (REGULATORS + ORGANIZATIONS lists) which work without spaCy.
*Note: Due to `uvicorn --reload` spinning up fresh worker processes, you may still see this warning once per server restart.*

### Transformer Models — "Loading weights" spam
**Problem**: `Loading weights: 100% | 201/201` printed 4x per processing run (one per document/page).  
**Fix applied**: `analyzer.py` uses a **module-level singleton** `_get_transformer_pipeline()`. Added environment variables `TOKENIZERS_PARALLELISM=false` and `TRANSFORMERS_VERBOSITY=error` in `main.py` at startup to completely silence the progress bars.

### Analytics & Coverage
**Problem**: Coverage analytics for Crisis Topics and Brand Mentions were empty.
**Fix applied**: Extended `GET /analytics/coverage` in `api/routes.py` to aggregate and return `crisis_topics` and `brand_mentions` statistics. Frontend updated to handle empty states.

### Search & Evidence
**Problem**: Search results for articles linked to broken evidence pages.
**Fix applied**: Differentiated between Alerts (which have evidence pages via `/alerts/:id/evidence`) and Articles in `evidence/page.tsx`.

### Pipeline Stages (in order)
1. `upload` → `pdf_classification` → `page_rendering` → `ocr` → `layout_analysis`
2. `article_extraction` → `language_detection` → `translation`
3. `entity_detection` → `sentiment_analysis` → `crisis_analysis`
4. `alert_generation` → `evidence_indexed`

### Processing Polling
`processing/page.tsx` polls every **8 seconds** when active documents exist (status = `processing` or `queued`).

---

## Known Limitations / TODOs

- `settings/page.tsx` — Displays static engine info. Backend `/system/info` endpoint not yet implemented. Future: load real model status.
- `audit/page.tsx` — Uses `/audit/:document_id` which returns `AuditLog` DB records. These are only created when pipeline stages call `db.add(AuditLog(...))` — not all stages may log yet.
- Evidence `[id]` page — The broadsheet view shows a simulated newspaper layout placeholder, not an actual page image. Future: fetch and display real page images from `/storage/`.
- `publications/page.tsx` — Shows empty state if no publications are seeded in DB. Seed via `POST /api/publications`.
- Coverage page analytics graph is not yet connected to a time-series endpoint.

---

## Dev Commands

```powershell
# Backend (from d:\projects\vee\backend)
uvicorn main:app --reload

# Frontend (from d:\projects\vee\frontend)
npm run dev
```

Frontend runs on `http://localhost:3000`. Backend on `http://127.0.0.1:8000`. All `/api/*` calls are proxied automatically via `next.config.ts`.
