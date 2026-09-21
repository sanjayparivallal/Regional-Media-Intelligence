# Production Project & Directory Structure Specification

> **Full-Stack AI/ML Intelligence Platform Architecture Standard**  
> *FastAPI Backend · Next.js 16 Frontend · Local AI/ML & OCR Pipelines · PostgreSQL / SQLite Storage*

---

## Table of Contents
1. [Architectural Overview](#1-architectural-overview)
2. [Complete Directory Structure Tree](#2-complete-directory-structure-tree)
3. [Deep-Dive Folder Governance & Breakdown](#3-deep-dive-folder-governance--breakdown)
   - [`models/` (AI/ML Models)](#models)
   - [`storage/uploads/` (User & Ingestion Uploads)](#storageuploads)
   - [`storage/pages/` & `storage/generated/` (Rendered Pages & Outputs)](#storagepages--storagegenerated)
   - [`data/seed/` & `data/spreadsheets/` (Seed Data, Excel & CSV)](#dataseed--dataspreadsheets)
   - [`database/` (Database, Migrations & SQLite)](#database)
   - [`config/` (Static Configuration)](#config)
   - [`environments/` & `.env` Files](#environments--env-files)
   - [`scripts/` (Utilities & Automation)](#scripts)
   - [`backend/` (FastAPI Application & Pipelines)](#backend)
   - [`frontend/` (Next.js 16 UI)](#frontend)
   - [`logs/` (Application & Pipeline Logs)](#logs)
   - [`tmp/` (Temporary & Cache Files)](#tmp)
   - [`tests/` (Automated Test Suites)](#tests)
   - [`docs/` (System Documentation)](#docs)
4. [Quick Reference Matrix](#4-quick-reference-matrix)
5. [Production `.gitignore` Blueprint](#5-production-gitignore-blueprint)

---

## 1. Architectural Overview

This specification establishes the production folder and file structure for a full-stack media intelligence and document-AI platform. It is engineered to satisfy the following principles:

- **Strict Data Governance**: Clear separation between persistent raw user inputs, ephemeral raster cache buffers, and immutable generated evidence assets.
- **Self-Contained Local AI/ML Execution**: Local weight registries for OCR, translation, sentiment, and layout models with zero runtime external cloud dependencies.
- **Modular Backend Architecture**: FastAPI layered pattern separating route controllers (`api/`), core framework abstractions (`core/`), SQLAlchemy models (`models/`), 12-stage ML processing pipelines (`pipeline/`), business logic (`services/`), and asynchronous task workers (`workers/`).
- **Interactive Modern Frontend**: Next.js 16 App Router architecture with custom canvas overlays for bounding-box evidence inspection, WebSocket streaming, and state management.

---

## 2. Complete Directory Structure Tree

```plaintext
regional-media-intelligence/
├── .env.example                          # Template for all required environment variables
├── .env.local                            # Local developer overrides (NEVER commit to VCS)
├── .gitignore                            # Root gitignore rules for Python, Node, data & models
├── docker-compose.yml                    # Multi-container orchestration (DB, Backend, Frontend, Worker)
├── Dockerfile.backend                    # Container definition for FastAPI backend & ML dependencies
├── Dockerfile.frontend                   # Container definition for Next.js frontend
├── Makefile                              # Quick automation shortcuts (setup, run, test, lint)
├── README.md                             # Project overview, quick start, and architectural guide
├── PROJECT_STRUCTURE.md                  # This file: definitive architecture and directory guide
│
├── config/                               # Central static business logic & domain configuration
│   ├── brands.json                       # Tracked entity dictionary, aliases, and keyword lexicons
│   ├── crisis_scoring.json               # Severity weight matrix and scoring formulas
│   ├── languages.json                    # Supported language codes, OCR engines, and script bounds
│   └── local_models.json                 # Model registry metadata, weights paths, and device targets
│
├── data/                                 # Data assets (seed data, spreadsheets, ground truths)
│   ├── raw/                              # Original, unmodified reference files
│   │   └── sample_newspapers_2026.zip    # Compressed raw historical ingest datasets
│   ├── seed/                             # Database initialization and mock data
│   │   ├── initial_users.json            # Default system roles, admin credentials, and ACLs
│   │   ├── initial_sources.json          # Publication registries, tiers, circulation numbers
│   │   └── mock_articles.json            # Deterministic articles for offline/demo mode
│   └── spreadsheets/                     # Tabular Excel and CSV lookup datasets
│       ├── regional_media_intelligence.xlsx # Master business dictionary and keyword weights
│       ├── brand_taxonomy.csv            # Hierarchical brand and competitor mappings
│       └── publication_tiers.csv         # District, state, and national circulation metrics
│
├── database/                             # Database schema, migration, and persistence files
│   ├── migrations/                       # Alembic database migration revisions
│   │   ├── env.py                        # Alembic async migration environment script
│   │   ├── script.py.mako                # Migration template file
│   │   └── versions/                     # Revision history
│   │       ├── 20260101_0001_init.py     # Initial tables (documents, articles, entities, alerts)
│   │       └── 20260215_0002_feedback.py # Human review and audit trail schemas
│   ├── schemas/                          # Raw SQL definitions / init scripts
│   │   └── 01_init_postgres.sql          # DB bootstrap script for container cold starts
│   └── sqlite/                           # Local development fallback storage
│       └── dev_rmia.db                   # Local SQLite database file (ignored in production)
│
├── docs/                                 # System architecture, developer guides, and API specs
│   ├── architecture/                     # Architecture Decision Records (ADRs) & pipeline diagrams
│   │   ├── pipeline_flow.png             # 12-stage processing architecture visual
│   │   └── risk_score_engine.md          # 5-factor weighted formula specification
│   ├── api/                              # OpenAPI specifications and integration guides
│   │   └── openapi.json                  # Exported OpenAPI schema
│   ├── deployment/                       # Deployment guides (Docker, Kubernetes, GPU nodes)
│   │   └── gpu_provisioning.md           # CUDA/cuDNN environment setup guide
│   └── user_guide/                       # End-user and reviewer documentation
│       └── evidence_viewer_guide.md      # Manual for bounding box reviewer dashboard
│
├── environments/                         # Environment-specific configuration files
│   ├── .env.development                  # Default configuration for local developer environments
│   ├── .env.staging                      # Staging cluster configuration
│   └── .env.production                   # Production template (secrets injected via vault/K8s)
│
├── logs/                                 # Runtime application, access, and pipeline log files
│   ├── .gitkeep                          # Preserves folder in git while logs are git-ignored
│   ├── app.log                           # General backend API application log
│   ├── pipeline.log                      # ML batch pipeline and OCR execution logs
│   ├── celery_worker.log                 # Background worker task lifecycle logs
│   └── model_benchmark.json              # Latency, memory, and throughput profiling records
│
├── models/                               # Local AI/ML weights, tokenizers, and model checkpoints
│   ├── .gitkeep
│   ├── indic_ocr/                        # OCR models (PaddleOCR / Tesseract models for Indic scripts)
│   │   ├── tamil_v4/
│   │   └── hindi_v4/
│   ├── indictrans2/                      # Translation weights and tokenizer vocabulary
│   │   ├── config.json
│   │   ├── tokenizer_config.json
│   │   └── model.safetensors             # FP16 / INT8 quantized translation model
│   ├── sentiment/                        # Multilingual sentiment analysis checkpoints
│   │   └── xlm_roberta_sentiment/
│   │       ├── config.json
│   │       └── pytorch_model.bin
│   └── spacy_en/                         # SpaCy English core NER pipelines
│       └── en_core_web_sm-3.7.1/
│
├── scripts/                              # Developer utilities, batch runners, and setup automation
│   ├── setup_environment.sh              # Shell script to install system dependencies (Tesseract, CUDA)
│   ├── download_models.py                # CLI script to download weights from HuggingFace/S3
│   ├── seed_database.py                  # Script to load `data/seed/` and `data/spreadsheets/` into DB
│   ├── benchmark_pipeline.py             # Performance testing harness for OCR and inference
│   └── export_training_data.py           # Exports human-reviewed corrections for fine-tuning
│
├── storage/                              # Primary runtime file repository for user & system files
│   ├── uploads/                          # Raw files uploaded by users or ingestion workers
│   │   ├── 2026-09-20/
│   │   │   └── doc_8f12a8bc_dinamalar.pdf
│   │   └── temp_chunks/                  # Multi-part chunked upload destination
│   ├── pages/                            # High-resolution rendered newspaper pages (PNG/JPEG)
│   │   └── doc_8f12a8bc/
│   │       ├── page_1.png
│   │       └── page_2.png
│   ├── generated/                        # System-generated outputs, reports, and crops
│   │   ├── crops/                        # Article-level image crops with bounding box coords
│   │   │   └── doc_8f12a8bc/
│   │   │       ├── art_c104_p1_crop.png
│   │   │       └── art_c105_p1_crop.png
│   │   └── reports/                      # Automated daily intelligence briefing exports
│   │       ├── daily_briefing_2026-09-20.pdf
│   │       └── crisis_summary_2026-09-20.xlsx
│   └── exports/                          # User-requested CSV/Excel/JSON data exports
│       └── export_alerts_tenant1_20260920.csv
│
├── tmp/                                  # Ephemeral cache, scratch buffers, and PID files
│   ├── .gitkeep
│   ├── ocr_cache/                        # Intermediate page thresholding and image deskew buffers
│   └── task_locks/                       # File-based worker locks
│
├── backend/                              # FastAPI Backend Application Root
│   ├── pyproject.toml                    # Poetry/Pip project definitions & lockfiles
│   ├── requirements.txt                  # Python dependencies
│   ├── main.py                           # Application bootstrap, CORS, and root lifespan handler
│   ├── api/                              # REST API Route controllers
│   │   ├── __init__.py
│   │   ├── deps.py                       # FastAPI dependency injection (DB sessions, auth user)
│   │   └── v1/                           # API Version 1 endpoints
│   │       ├── __init__.py
│   │       ├── router.py                 # Master v1 route aggregation
│   │       ├── auth.py                   # Authentication, API keys, JWT endpoints
│   │       ├── documents.py              # PDF upload, ingestion status, and page streaming
│   │       ├── articles.py               # Article intelligence, risk scores, entities
│   │       ├── alerts.py                 # Real-time crisis alerts and notification hooks
│   │       └── review.py                 # Human-in-the-loop review and audit approvals
│   ├── core/                             # Core framework abstractions
│   │   ├── __init__.py
│   │   ├── config.py                     # Pydantic Settings class (reads .env dynamically)
│   │   ├── database.py                   # Async SQLAlchemy session engine & base declarations
│   │   ├── security.py                   # Password hashing, JWT token creation/verification
│   │   └── logging.py                    # Structured JSON logging formatters and rotating handlers
│   ├── models/                           # SQLAlchemy ORM database models
│   │   ├── __init__.py
│   │   ├── document.py                   # Ingested PDF/e-Paper document records
│   │   ├── page.py                       # Page metadata, dimensions, image references
│   │   ├── article.py                    # Segmented article, bounding boxes, text content
│   │   ├── entity.py                     # Extracted entities (Org, Person, Brand, Location)
│   │   ├── alert.py                      # Generated crisis alerts and risk score audit logs
│   │   └── feedback.py                   # Reviewer approval, correction, and feedback records
│   ├── pipeline/                         # 12-Stage AI/ML Media Intelligence Pipeline
│   │   ├── __init__.py
│   │   ├── manager.py                    # Pipeline orchestrator and stage lifecycle manager
│   │   ├── ingestion/                    # Step 1: Preprocessing & Page Rendering
│   │   │   ├── pdf_processor.py          # PyMuPDF / pdf2image multi-threaded rasterizer
│   │   │   └── image_enhancer.py         # OpenCV adaptive thresholding & contrast booster
│   │   ├── ocr/                          # Step 2 & 4: Multilingual OCR & Script Detection
│   │   │   ├── ocr_engine.py             # PaddleOCR / Tesseract unified wrapper
│   │   │   └── script_detector.py        # Unicode range and script classifier
│   │   ├── layout/                       # Step 3: Layout Analysis & Article Segmentation
│   │   │   ├── column_detector.py        # Morphological column boundary finder
│   │   │   └── article_segmenter.py      # Headline & body clustering algorithms
│   │   ├── nlp/                          # Step 5-9: Translation, NER, Sentiment, Crisis
│   │   │   ├── translation/              # Local NLLB-200 / IndicTrans2 interface
│   │   │   │   └── translator.py
│   │   │   ├── entity/                   # Brand & Named Entity Recognition
│   │   │   │   ├── ner_extractor.py
│   │   │   │   └── brand_matcher.py      # Fuzzy & exact alias matching against config
│   │   │   ├── sentiment/                # Multilingual XLM-RoBERTa sentiment engine
│   │   │   │   └── sentiment_analyzer.py
│   │   │   └── crisis/                   # 12-Category topic and severity classifier
│   │   │       └── classifier.py
│   │   └── scoring/                      # Step 10-11: Risk Scoring & Deduplication
│   │       ├── risk_engine.py            # 5-factor weighted formula calculator
│   │       └── deduplicator.py           # Cryptographic fingerprinting & similarity check
│   ├── schemas/                          # Pydantic validation schemas (DTOs)
│   │   ├── __init__.py
│   │   ├── document.py                   # Ingestion request and response models
│   │   ├── article.py                    # Article payload with bounding box coordinates
│   │   ├── risk.py                       # Risk score factor breakdown models
│   │   └── alert.py                      # Alert notification schemas
│   ├── services/                         # Business logic services (bridge between API & DB)
│   │   ├── __init__.py
│   │   ├── document_service.py           # Ingestion lifecycle and storage synchronization
│   │   ├── article_service.py            # Querying, filtering, and aggregation logic
│   │   └── alert_service.py              # Webhook triggers, email dispatchers
│   └── workers/                          # Celery / Redis background workers
│       ├── __init__.py
│       ├── celery_app.py                 # Celery app configuration and task routing
│       └── tasks.py                      # Asynchronous document processing task definitions
│
├── frontend/                             # Next.js 16 (App Router) Frontend Application
│   ├── package.json                      # Node dependencies and build scripts
│   ├── tsconfig.json                     # TypeScript compiler configuration
│   ├── next.config.ts                    # Next.js runtime, image domains, and proxy configuration
│   ├── postcss.config.mjs                # PostCSS plugins
│   ├── public/                           # Static assets served at root `/`
│   │   ├── favicon.ico
│   │   ├── logos/                        # Application and tenant branding logos
│   │   │   └── logo.svg
│   │   └── sounds/                       # Notification alert chimes
│   │       └── crisis_alert.mp3
│   └── src/                              # Application source code
│       ├── app/                          # Next.js App Router routes & layouts
│       │   ├── layout.tsx                # Root HTML shell, providers, and global font loading
│       │   ├── page.tsx                  # Landing / Root redirect page
│       │   ├── (auth)/                   # Authentication route group
│       │   │   ├── login/page.tsx
│       │   │   └── register/page.tsx
│       │   ├── (dashboard)/              # Authenticated workspace route group
│       │   │   ├── layout.tsx            # Dashboard shell (Sidebar, TopNav, Notification Bar)
│       │   │   ├── dashboard/page.tsx    # KPI Summary, Risk Heatmaps, Volume charts
│       │   │   ├── upload/page.tsx       # Drag-and-drop PDF uploader & real-time queue
│       │   │   ├── alerts/page.tsx       # Live crisis feed and filterable alert table
│       │   │   ├── evidence/[id]/page.tsx# Interactive split-screen evidence viewer
│       │   │   └── review/page.tsx       # Human-in-the-loop review queue
│       │   └── api/                      # Next.js edge route handlers (BFF - Backend for Frontend)
│       │       └── proxy/[...path]/route.ts
│       ├── components/                   # Reusable React components
│       │   ├── ui/                       # Atomic UI primitives (Buttons, Modals, Badges, Cards)
│       │   │   ├── button.tsx
│       │   │   ├── modal.tsx
│       │   │   └── badge.tsx
│       │   ├── dashboard/                # Analytics widgets and chart components
│       │   │   ├── risk_gauge.tsx
│       │   │   └── volume_trend_chart.tsx
│       │   ├── evidence/                 # Evidence Viewer custom components
│       │   │   ├── newspaper_canvas.tsx  # Bounding box rendering overlay on high-res pages
│       │   │   ├── article_panel.tsx     # Extracted OCR, English translation & entities
│       │   │   └── audit_timeline.tsx    # 14-stage execution trace viewer
│       │   └── layout/                   # Structural navigation components
│       │       ├── sidebar.tsx
│       │       └── header.tsx
│       ├── hooks/                        # Custom React Hooks
│       │   ├── use_pipeline_socket.ts    # WebSocket hook for live ingestion progress
│       │   ├── use_evidence_canvas.ts    # Zoom, pan, and bounding box selection math
│       │   └── use_alerts.ts             # SWR/TanStack Query hook for alerts
│       ├── lib/                          # Utility functions and shared clients
│       │   ├── api_client.ts             # Axios / Fetch wrapper with automatic token refresh
│       │   ├── formatters.ts             # Date, number, currency, and risk score formatters
│       │   └── utils.ts                  # Tailwind `cn()` helper and DOM helpers
│       ├── stores/                       # State management (Zustand / Redux Toolkit)
│       │   ├── auth_store.ts             # User session and permissions state
│       │   └── viewer_store.ts           # Active document, selected article, zoom scale state
│       ├── styles/                       # Global CSS & Tailwind stylesheets
│       │   └── globals.css               # Design tokens, CSS variables, glassmorphism classes
│       └── types/                        # TypeScript type definitions & interfaces
│           ├── document.ts               # Document, Page, and Pipeline status types
│           ├── article.ts                # Article, BoundingBox, and Entity types
│           └── risk.ts                   # RiskScore breakdown and alert interfaces
│
└── tests/                                # Global integration and end-to-end test suites
    ├── backend/                          # Backend PyTest integration tests
    │   ├── conftest.py                   # PyTest fixtures (DB test session, mock files)
    │   ├── test_api_documents.py         # Document upload and streaming endpoint tests
    │   ├── test_pipeline_ocr.py          # OCR accuracy and script detection assertions
    │   ├── test_risk_formula.py          # Deterministic risk engine calculation tests
    │   └── test_translation.py           # Indic-to-English translation tests
    ├── frontend/                         # Frontend unit and component tests (Vitest / React Testing Lib)
    │   ├── setup.ts
    │   ├── components/
    │   │   └── newspaper_canvas.test.tsx # Bounding box click & coordinate transform tests
    │   └── hooks/
    │       └── use_evidence_canvas.test.ts
    └── sample_pages/                     # Static ground-truth sample files for automated tests
        ├── sample_tamil_newspaper.pdf    # Fixture for OCR & translation verification
        └── sample_hindi_newspaper.png    # Fixture for column layout detection
```

---

## 3. Deep-Dive Folder Governance & Breakdown

---

### `models/`
- **What it is used for:** Central storage for local machine learning model weights, checkpoints, quantized formats (GGUF, ONNX, SafeTensors), tokenizers, and vocabulary configs.
- **What files should be placed there:**
  - Model weights: `models/indictrans2/model.safetensors`, `models/sentiment/pytorch_model.bin`
  - Tokenizer configs: `tokenizer.json`, `vocab.txt`, `tokenizer_config.json`
  - Architecture configs: `config.json`, `generation_config.json`
- **What files should NOT be placed there:**
  - Training scripts or data preparation code (place in `scripts/`).
  - Python inference wrappers or pipeline stages (place in `backend/pipeline/`).
  - Training output evaluation logs or benchmarks.
- **Application Connectivity & Data Flow:**
  - On application startup, `backend/pipeline/manager.py` reads paths declared in `config/local_models.json`.
  - The weights are loaded directly into RAM/VRAM once and shared across worker tasks.

---

### `storage/uploads/`
- **What it is used for:** Persistent runtime storage for original, unmodified files uploaded by users or fetched from external e-Paper crawlers.
- **What files should be placed there:**
  - Raw newspaper PDF files (`.pdf`), high-resolution scanned page images (`.png`, `.jpg`, `.tiff`), and multi-part upload chunks (`.part`).
- **What files should NOT be placed there:**
  - Processed images, cropped bounding boxes, or thresholded pages.
  - Source code, database backups, or temporary log files.
- **Application Connectivity & Data Flow:**
  - `POST /api/v1/documents/upload` streams incoming files into `storage/uploads/YYYY-MM-DD/<uuid>.<ext>`.
  - The relative storage path is written to the `documents` table in PostgreSQL.
  - Background Celery workers receive the file path to execute the ingestion and OCR pipeline.

---

### `storage/pages/` & `storage/generated/`
- **What it is used for:** Storage for all assets created by the processing pipeline, including rendered pages, bounding-box article crops, and exported reports.
- **What files should be placed there:**
  - `storage/pages/<doc_id>/`: Full-page high-DPI rendered images (`page_1.png`, `page_2.png`).
  - `storage/generated/crops/<doc_id>/`: Extracted bounding-box crops for individual articles (`art_c104_p1_crop.png`).
  - `storage/generated/reports/`: Generated PDF executive briefings and Excel summaries.
  - `storage/exports/`: User-requested CSV or JSON export bundles.
- **What files should NOT be placed there:**
  - Raw original uploaded documents (belong in `storage/uploads/`).
  - Short-lived image transformation buffers (belong in `tmp/`).
- **Application Connectivity & Data Flow:**
  - The PDF processor renders pages to `storage/pages/<doc_id>/`.
  - The Next.js Evidence Viewer requests these page images via `GET /api/v1/documents/<doc_id>/pages/<page_num>/image` to display interactive bounding-box overlays.

---

### `data/seed/` & `data/spreadsheets/`
- **What it is used for:** Static reference datasets, initial database seeds, ground-truth taxonomy sheets, and domain Excel/CSV spreadsheets.
- **What files should be placed there:**
  - Excel master workbooks: `data/spreadsheets/regional_media_intelligence.xlsx`
  - CSV lookup tables: `brand_taxonomy.csv`, `publication_tiers.csv`
  - Seed fixtures: `initial_users.json`, `initial_sources.json`, `mock_articles.json`
- **What files should NOT be placed there:**
  - Dynamic user-uploaded files at runtime.
  - Ephemeral pipeline outputs or logs.
- **Application Connectivity & Data Flow:**
  - `scripts/seed_database.py` reads these files on deployment to bootstrap database tables.
  - The brand matcher (`backend/pipeline/nlp/entity/brand_matcher.py`) cross-references `brand_taxonomy.csv` for fuzzy alias matching.

---

### `database/`
- **What it is used for:** Database schema migrations, bootstrap SQL scripts, and local SQLite development database files.
- **What files should be placed there:**
  - Alembic migration scripts (`database/migrations/versions/*.py`) and configuration (`env.py`).
  - Database initialization SQL scripts (`database/schemas/01_init_postgres.sql`).
  - Local development SQLite database files (`database/sqlite/dev_rmia.db`).
- **What files should NOT be placed there:**
  - SQLAlchemy Python ORM classes (place in `backend/models/`).
  - Business queries or repository functions (place in `backend/services/`).
- **Application Connectivity & Data Flow:**
  - During container initialization, `alembic upgrade head` applies migration files to PostgreSQL.

---

### `config/`
- **What it is used for:** Static business logic, domain rules, model registries, and risk score weight matrices.
- **What files should be placed there:**
  - JSON/YAML config files:
    - `brands.json`: Tracked entities, competitor keywords, and aliases.
    - `crisis_scoring.json`: Weights for the 5-factor risk formula.
    - `languages.json`: Script-to-language mappings and OCR confidence thresholds.
    - `local_models.json`: Paths and device configuration for local model weights.
- **What files should NOT be placed there:**
  - Sensitive environment variables, API secrets, database passwords (must reside in `.env`).
- **Application Connectivity & Data Flow:**
  - Loaded once into memory on backend startup via `backend/core/config.py`.
  - The risk scoring engine (`backend/pipeline/scoring/risk_engine.py`) reads `crisis_scoring.json` to compute dynamic risk scores.

---

### `environments/` & `.env` Files
- **What it is used for:** Environment variables, secrets templates, and runtime parameters for different environments.
- **What files should be placed there:**
  - `.env.example`: Public template documenting all mandatory keys.
  - `environments/.env.development`: Local development settings (`DEBUG=True`).
  - `environments/.env.staging`: Staging cluster settings.
  - `environments/.env.production`: Production config templates.
- **What files should NOT be placed there:**
  - Live production passwords or private cryptographic keys committed into git.
- **Application Connectivity & Data Flow:**
  - Parsed by `backend/core/config.py` using `pydantic-settings` to inject typed configuration parameters across backend modules.

---

### `scripts/`
- **What it is used for:** Developer utilities, CLI runners, model downloaders, and environment initialization helpers.
- **What files should be placed there:**
  - `setup_environment.sh`: Installs system dependencies (CUDA, Tesseract, poppler).
  - `download_models.py`: Downloads pre-trained weights to `models/`.
  - `seed_database.py`: Populates DB from `data/seed/` and `data/spreadsheets/`.
  - `benchmark_pipeline.py`: Profiles OCR and NLP inference latency.
- **What files should NOT be placed there:**
  - REST API routes or core application business logic.
- **Application Connectivity & Data Flow:**
  - Executed via CLI by developers or CI/CD pipelines (e.g. `python scripts/download_models.py`).

---

### `backend/`
- **What it is used for:** The complete FastAPI backend application, REST API controllers, SQLAlchemy models, Pydantic schemas, 12-stage ML pipeline, and Celery workers.
- **What files should be placed there:**
  - `api/`: REST API endpoints (`documents.py`, `articles.py`, `alerts.py`).
  - `core/`: Config, DB engines, security, logging.
  - `models/`: SQLAlchemy ORM models (`document.py`, `article.py`, `alert.py`).
  - `pipeline/`: 12-stage document intelligence pipeline.
  - `schemas/`: Pydantic validation schemas (DTOs).
  - `services/`: Business services layer.
  - `workers/`: Background task processors (`tasks.py`).
- **What files should NOT be placed there:**
  - Large binary model weights (belong in `models/`).
  - User uploaded or rendered files (belong in `storage/`).
  - Frontend components or styles.
- **Application Connectivity & Data Flow:**
  - Listens on port `8000`. Serves REST/WebSocket endpoints to the Next.js frontend, manages async pipeline tasks, and reads/writes to PostgreSQL.

---

### `frontend/`
- **What it is used for:** Next.js 16 (App Router) user interface application.
- **What files should be placed there:**
  - `src/app/`: Page routes (`upload/page.tsx`, `evidence/[id]/page.tsx`, `alerts/page.tsx`).
  - `src/components/`: Reusable UI components (`newspaper_canvas.tsx`, `risk_gauge.tsx`).
  - `src/hooks/`: Custom React hooks (`use_pipeline_socket.ts`, `use_evidence_canvas.ts`).
  - `src/lib/`: API clients (`api_client.ts`), formatters, and utilities.
  - `src/stores/`: Zustand state management stores.
  - `src/types/`: TypeScript type interfaces.
- **What files should NOT be placed there:**
  - Python backend code, ML models, or SQLite database files.
- **Application Connectivity & Data Flow:**
  - Runs on port `3000`. Connects to FastAPI on port `8000` via HTTP REST and WebSockets.

---

### `logs/`
- **What it is used for:** Runtime logs, pipeline execution traces, worker logs, and model performance benchmarks.
- **What files should be placed there:**
  - `app.log`: General backend API server logs.
  - `pipeline.log`: OCR and ML pipeline execution logs.
  - `celery_worker.log`: Background task queue lifecycle logs.
  - `model_benchmark.json`: Latency and memory profiling outputs.
- **What files should NOT be placed there:**
  - Business records or unredacted user credentials.
- **Application Connectivity & Data Flow:**
  - `backend/core/logging.py` writes structured JSON logs with rotating 50MB file limits.

---

### `tmp/`
- **What it is used for:** Ephemeral scratch directory for intermediate processing, image deskew buffers, and task lock files.
- **What files should be placed there:**
  - Temporary deskew bitmaps, threshold buffers, and task lock files (`.lock`).
- **What files should NOT be placed there:**
  - Permanent user uploads or outputs requiring persistence.
- **Application Connectivity & Data Flow:**
  - Used by OpenCV and PDF rasterizers during heavy compute steps; purged automatically after job completion or via daily cleanup cron.

---

### `tests/`
- **What it is used for:** Automated integration test suites, unit tests, mock fixtures, and ground-truth sample documents.
- **What files should be placed there:**
  - PyTest modules (`test_api_documents.py`, `test_risk_formula.py`).
  - Vitest UI component tests (`newspaper_canvas.test.tsx`).
  - Sample test documents (`sample_pages/sample_tamil_newspaper.pdf`).
- **What files should NOT be placed there:**
  - Production client documents containing unredacted PII.
- **Application Connectivity & Data Flow:**
  - Executed via `pytest tests/` in CI/CD pipelines to validate pipeline accuracy and API contracts before deployment.

---

### `docs/`
- **What it is used for:** System architecture documentation, Architecture Decision Records (ADRs), user manuals, and API specifications.
- **What files should be placed there:**
  - Markdown documentation (`.md`), OpenAPI schemas (`openapi.json`), and architecture diagrams (`.png`, `.svg`, `.mermaid`).
- **What files should NOT be placed there:**
  - Executable source code or configuration secrets.
- **Application Connectivity & Data Flow:**
  - Central documentation hub for engineering, QA, and operations teams.

---

## 4. Quick Reference Matrix

| Requirement Category | Designated Directory | Example File Path |
|---|---|---|
| **AI/ML Model Files** | `models/<category>/` | `models/indictrans2/model.safetensors` |
| **Downloaded Files (Raw Ingestion)** | `storage/uploads/<date>/` | `storage/uploads/2026-09-20/doc_8f12a8bc.pdf` |
| **Seed Data** | `data/seed/` | `data/seed/initial_sources.json` |
| **Excel / CSV Files** | `data/spreadsheets/` | `data/spreadsheets/regional_media_intelligence.xlsx` |
| **Database & Migration Files** | `database/` | `database/migrations/versions/20260101_0001_init.py` |
| **Uploaded Files (User Uploads)** | `storage/uploads/` | `storage/uploads/temp_chunks/chunk_01.part` |
| **Generated / Output Files** | `storage/generated/` & `storage/pages/` | `storage/generated/crops/art_c104_p1_crop.png` |
| **Configuration Files** | `config/` | `config/crisis_scoring.json` |
| **Environment Variables & .env** | Project root & `environments/` | `.env.example`, `environments/.env.development` |
| **Scripts & Utilities** | `scripts/` | `scripts/download_models.py` |
| **API & Backend Code** | `backend/` | `backend/api/v1/articles.py` |
| **Frontend Code** | `frontend/src/` | `frontend/src/components/evidence/newspaper_canvas.tsx` |
| **Logs** | `logs/` | `logs/pipeline.log` |
| **Temporary & Cache Files** | `tmp/` | `tmp/ocr_cache/deskew_buffer_01.png` |
| **Tests** | `tests/` | `tests/backend/test_risk_formula.py` |
| **Documentation** | `docs/` | `docs/architecture/risk_score_engine.md` |

---

## 5. Production `.gitignore` Blueprint

```gitignore
# ==============================================================================
# Environment & Secrets (NEVER COMMIT)
# ==============================================================================
.env
.env.local
.env.*.local
*.pem
*.key
*.cert

# ==============================================================================
# Python & Caches
# ==============================================================================
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# ==============================================================================
# Node & Frontend
# ==============================================================================
node_modules/
.next/
out/
*.tsbuildinfo
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# ==============================================================================
# AI/ML Models & Large Binary Weights
# ==============================================================================
models/**/*.bin
models/**/*.safetensors
models/**/*.pt
models/**/*.onnx
models/**/*.gguf
models/**/*.tar.gz
!models/**/.gitkeep

# ==============================================================================
# Storage, Uploads & Generated Outputs
# ==============================================================================
storage/uploads/*
storage/pages/*
storage/generated/*
storage/exports/*
!storage/**/.gitkeep
!storage/uploads/.gitkeep
!storage/pages/.gitkeep
!storage/generated/.gitkeep

# ==============================================================================
# Logs & Ephemeral Temporary Buffers
# ==============================================================================
logs/*.log
logs/*.json
tmp/*
!tmp/.gitkeep
!logs/.gitkeep

# ==============================================================================
# Database Persistence Files
# ==============================================================================
database/sqlite/*.db
database/sqlite/*.sqlite3
```
