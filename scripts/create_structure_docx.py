import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def build_docx(filename="Project_Folder_Structure_Specification.docx"):
    doc = docx.Document()
    
    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
    
    # Color Palette
    PRIMARY = RGBColor(30, 58, 138)      # Deep Blue
    SECONDARY = RGBColor(15, 118, 110)   # Teal
    DARK_TEXT = RGBColor(30, 41, 59)     # Slate 800
    MUTED_TEXT = RGBColor(100, 116, 139) # Slate 500
    CODE_BG = "F1F5F9"                  # Slate 100
    HEADER_BG = "1E3A8A"                # Primary Navy
    ROW_ALT_BG = "F8FAFC"               # Slate 50
    
    # Base Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = DARK_TEXT
    
    # Document Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("Enterprise Project & Folder Structure Specification")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = PRIMARY
    
    # Subtitle
    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(16)
    run_sub = sub_p.add_run("Production Architecture Standard for Full-Stack AI/ML Intelligence Platforms")
    run_sub.font.size = Pt(12)
    run_sub.font.italic = True
    run_sub.font.color.rgb = SECONDARY
    
    # Horizontal separator
    p_sep = doc.add_paragraph()
    p_sep.paragraph_format.space_after = Pt(14)
    p_sep_run = p_sep.add_run("_________________________________________________________________________________")
    p_sep_run.font.color.rgb = RGBColor(203, 213, 225)
    
    # Section 1: Executive Overview
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    r = h1.add_run("1. Architectural Overview")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = PRIMARY
    
    p = doc.add_paragraph("This specification defines the complete, production-grade folder and file layout designed for scalable AI/ML platforms (FastAPI backend, Next.js frontend, PyTorch/OCR multi-stage pipelines, and PostgreSQL/Alembic storage). It establishes strict data governance, clean separation of concerns, and robust security practices for enterprise environments.")
    p.paragraph_format.space_after = Pt(12)
    
    # Section 2: Complete Folder Structure Tree
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(16)
    h2.paragraph_format.space_after = Pt(6)
    r = h2.add_run("2. Complete Directory Structure Tree")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = PRIMARY
    
    tree_text = """regional-media-intelligence/
├── .env.example                          # Template for all required environment variables
├── .env.local                            # Local developer overrides (NEVER commit to VCS)
├── .gitignore                            # Root gitignore rules for Python, Node, data & models
├── docker-compose.yml                    # Multi-container orchestration (DB, Backend, Frontend, Worker)
├── Dockerfile.backend                    # Container definition for FastAPI backend & ML dependencies
├── Dockerfile.frontend                   # Container definition for Next.js frontend
├── Makefile                              # Quick automation shortcuts (setup, run, test, lint)
├── README.md                             # Project overview, quick start, and architectural guide
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
        └── sample_hindi_newspaper.png    # Fixture for column layout detection"""

    # Monospace block in a styled single-cell table
    tree_table = doc.add_table(rows=1, cols=1)
    tree_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tree_cell = tree_table.cell(0, 0)
    set_cell_background(tree_cell, CODE_BG)
    set_cell_margins(tree_cell, top=140, bottom=140, left=180, right=180)
    
    p_code = tree_cell.paragraphs[0]
    p_code.paragraph_format.space_before = Pt(0)
    p_code.paragraph_format.space_after = Pt(0)
    r_code = p_code.add_run(tree_text)
    r_code.font.name = 'Consolas'
    r_code.font.size = Pt(8.5)
    r_code.font.color.rgb = DARK_TEXT
    
    doc.add_paragraph().paragraph_format.space_after = Pt(14)
    
    # Section 3: Detailed Folder Governance & Breakdown
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(18)
    h3.paragraph_format.space_after = Pt(8)
    r = h3.add_run("3. Detailed Folder Breakdown & Governance")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = PRIMARY
    
    folders_data = [
        {
            "name": "models/",
            "purpose": "Dedicated directory for local AI/ML model weights, checkpoints, quantized formats (GGUF, ONNX, SafeTensors), tokenizers, and vocabulary configs.",
            "allowed": "Model weight binaries (.safetensors, .bin, .onnx, .pt, .gguf), tokenizers (tokenizer.json, vocab.txt), architecture metadata (config.json, generation_config.json).",
            "forbidden": "Training code, evaluation scripts (use scripts/), inference wrappers (use backend/pipeline/), training run logs.",
            "flow": "During server startup, backend/pipeline/manager.py reads paths defined in config/local_models.json and loads checkpoints into GPU/CPU RAM. No external APIs or downloads are required at runtime."
        },
        {
            "name": "storage/uploads/",
            "purpose": "Persistent runtime landing area for raw, unedited documents uploaded by users or fetched by crawler jobs.",
            "allowed": "Raw PDF files (.pdf), scanned newspaper images (.png, .jpg, .tiff), chunked upload parts (.part), and ZIP archives (.zip).",
            "forbidden": "Extracted images, cropped articles, thresholded bitmaps, database files, source code.",
            "flow": "POST /api/v1/documents/upload streams the binary file into storage/uploads/YYYY-MM-DD/<uuid>.pdf. The path is saved in the database documents table. Celery background workers read this file for ingestion."
        },
        {
            "name": "storage/pages/ & storage/generated/",
            "purpose": "Permanent destination for system-derived assets, page rasterizations, article crops, and exported reports.",
            "allowed": "Rendered full-page images (page_1.png), bounding-box cropped article images (art_c104_p1_crop.png), generated intelligence briefings (.pdf, .xlsx), export CSVs.",
            "forbidden": "Raw user uploads (use storage/uploads/), temporary intermediate threshold caches (use tmp/).",
            "flow": "The ingestion processor renders PDF pages into storage/pages/<doc_id>/. The Next.js Evidence Viewer streams these high-DPI images via GET /api/v1/documents/<doc_id>/pages/<page_num>/image to render interactive bounding box overlays."
        },
        {
            "name": "data/seed/ & data/spreadsheets/",
            "purpose": "Source of truth for initial database bootstrap records, taxonomies, lookup tables, and domain Excel files.",
            "allowed": "Excel workbooks (.xlsx, .xls), CSV lookup tables (.csv), JSON seed fixtures (initial_users.json, publication_tiers.csv, regional_media_intelligence.xlsx).",
            "forbidden": "Dynamic runtime user uploads, server log outputs, model weights.",
            "flow": "scripts/seed_database.py parses these files on cold start to populate database tables (publications, circulation tiers, brand taxonomies). The brand matcher references these dictionaries during entity extraction."
        },
        {
            "name": "database/",
            "purpose": "Database persistence schemas, SQL initialization scripts, Alembic version migrations, and local development SQLite database files.",
            "allowed": "Alembic migration scripts (migrations/versions/*.py), SQL bootstrap scripts (01_init_postgres.sql), local SQLite database files (dev_rmia.db).",
            "forbidden": "SQLAlchemy ORM Python classes (use backend/models/), business queries (use backend/services/).",
            "flow": "During deployment, alembic upgrade head executes all revision files inside database/migrations/versions/ against PostgreSQL, ensuring database tables exactly match backend/models/ definitions."
        },
        {
            "name": "config/",
            "purpose": "Central static business rules, dynamic parameter scoring tables, risk weight matrices, and model registries.",
            "allowed": "JSON / YAML / TOML rule files (brands.json, crisis_scoring.json, languages.json, local_models.json).",
            "forbidden": "Hardcoded secret keys, database credentials, passwords (must strictly be placed in .env).",
            "flow": "Parsed on startup into typed Pydantic models by backend/core/config.py. The risk engine uses crisis_scoring.json to compute the 5-factor explainable risk formula dynamically without code modifications."
        },
        {
            "name": "environments/ & .env Files",
            "purpose": "Environment-specific runtime variables, secrets templates, and infrastructure parameters.",
            "allowed": ".env.example (public template), environments/.env.development, environments/.env.staging, environments/.env.production.",
            "forbidden": "Live production secrets or private cryptographic keys committed into git repositories.",
            "flow": "backend/core/config.py loads environment variables into memory at runtime to bind database connections, JWT secrets, worker queues, and storage directory paths."
        },
        {
            "name": "scripts/",
            "purpose": "Operational CLI tools, batch runners, model downloaders, and environment initialization helpers.",
            "allowed": "Python and Bash executable scripts (setup_environment.sh, download_models.py, seed_database.py, benchmark_pipeline.py).",
            "forbidden": "REST API route handlers, React frontend components, permanent runtime data.",
            "flow": "Executed directly via terminal or CI/CD pipelines (e.g., make seed runs python scripts/seed_database.py to prepare test environments)."
        },
        {
            "name": "backend/",
            "purpose": "FastAPI core backend application, including API endpoints, services, ORM models, 12-stage ML pipeline, and async Celery workers.",
            "allowed": "Python source code organized into api/, core/, models/, pipeline/, schemas/, services/, and workers/.",
            "forbidden": "Frontend UI code, binary model weights (use models/), uploaded files (use storage/).",
            "flow": "Runs as the central REST/WebSocket server on port 8000. Coordinates file processing through the 12-stage pipeline, logs execution traces, and responds to frontend requests."
        },
        {
            "name": "frontend/",
            "purpose": "Next.js 16 (App Router) user interface application with real-time dashboards and interactive evidence viewer.",
            "allowed": "React components, Next.js route handlers, TypeScript interfaces, Tailwind styles, custom hooks, and state stores.",
            "forbidden": "Python backend modules, heavy ML models, raw SQLite/Postgres database files.",
            "flow": "Runs on port 3000. Renders the interactive bounding box canvas, connects to backend WebSocket for live pipeline status, and presents real-time crisis alerts."
        },
        {
            "name": "logs/",
            "purpose": "Central repository for application execution logs, error traces, Celery task logs, and benchmark profiling metrics.",
            "allowed": "Structured log files (.log), rotating logs, model benchmark profiles (model_benchmark.json).",
            "forbidden": "Core business transaction data, user passwords, unmasked personal data.",
            "flow": "backend/core/logging.py emits JSON-structured logs to logs/app.log and logs/pipeline.log with automatic 50MB log rotation and 14-day retention."
        },
        {
            "name": "tmp/",
            "purpose": "Ephemeral scratch directory for intermediate processing, image deskew buffers, and task lock files.",
            "allowed": "Temporary threshold bitmaps, OpenCV scratch arrays, lock files (.lock), partial file downloads.",
            "forbidden": "Long-term data or user uploads that need persistence.",
            "flow": "Used by OpenCV and PDF rasterizers during heavy compute steps. Cleaned up automatically upon pipeline stage completion or via scheduled 24-hour cleanup cron."
        },
        {
            "name": "tests/",
            "purpose": "Automated test suites (PyTest, Vitest), mock fixtures, and ground-truth sample documents.",
            "allowed": "Test scripts (test_*.py, *.test.tsx), PyTest fixtures (conftest.py), and sample ground-truth newspaper pages (sample_pages/).",
            "forbidden": "Production client documents containing real un-redacted PII.",
            "flow": "Executed in CI/CD pipelines (pytest tests/ and npm test) to guarantee 100% deterministic risk score calculations, OCR precision, and API uptime."
        },
        {
            "name": "docs/",
            "purpose": "System architectural documentation, Architecture Decision Records (ADRs), user manuals, and API specifications.",
            "allowed": "Markdown files (.md), OpenAPI schemas (openapi.json), architecture diagrams (.png, .svg, .mermaid).",
            "forbidden": "Executable application code, raw model checkpoints.",
            "flow": "Referenced by engineering, QA, and operations teams for onboarding, auditing, and maintenance."
        }
    ]
    
    for folder in folders_data:
        # Folder title
        p_fhead = doc.add_paragraph()
        p_fhead.paragraph_format.space_before = Pt(12)
        p_fhead.paragraph_format.space_after = Pt(4)
        r_fhead = p_fhead.add_run(f"📁  {folder['name']}")
        r_fhead.font.size = Pt(13)
        r_fhead.font.bold = True
        r_fhead.font.color.rgb = SECONDARY
        
        # Governance Table for this folder
        ftable = doc.add_table(rows=4, cols=2)
        ftable.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(ftable, color="CBD5E1", sz="4", val="single")
        
        col_widths = [Inches(1.8), Inches(4.9)]
        row_headers = [
            ("Purpose & Usage", folder["purpose"]),
            ("Allowed Files", folder["allowed"]),
            ("Forbidden Files", folder["forbidden"]),
            ("Application Data Flow", folder["flow"])
        ]
        
        for i, (hdr, val) in enumerate(row_headers):
            row = ftable.rows[i]
            
            # Left Header Cell
            cell_hdr = row.cells[0]
            cell_hdr.width = col_widths[0]
            set_cell_background(cell_hdr, "F1F5F9")
            set_cell_margins(cell_hdr, top=70, bottom=70, left=100, right=100)
            p_h = cell_hdr.paragraphs[0]
            p_h.paragraph_format.space_before = Pt(0)
            p_h.paragraph_format.space_after = Pt(0)
            r_h = p_h.add_run(hdr)
            r_h.font.bold = True
            r_h.font.size = Pt(9.5)
            r_h.font.color.rgb = DARK_TEXT
            
            # Right Content Cell
            cell_val = row.cells[1]
            cell_val.width = col_widths[1]
            if i % 2 == 1:
                set_cell_background(cell_val, ROW_ALT_BG)
            set_cell_margins(cell_val, top=70, bottom=70, left=100, right=100)
            p_v = cell_val.paragraphs[0]
            p_v.paragraph_format.space_before = Pt(0)
            p_v.paragraph_format.space_after = Pt(0)
            r_v = p_v.add_run(val)
            r_v.font.size = Pt(9.5)
            r_v.font.color.rgb = DARK_TEXT
            
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Section 4: Quick Reference Matrix
    h4 = doc.add_paragraph()
    h4.paragraph_format.space_before = Pt(18)
    h4.paragraph_format.space_after = Pt(8)
    r = h4.add_run("4. Quick Reference Matrix")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = PRIMARY
    
    matrix_data = [
        ("Requirement Category", "Designated Directory", "Example File Path"),
        ("AI/ML Model Files", "models/<category>/", "models/indictrans2/model.safetensors"),
        ("Downloaded Files (Ingestion)", "storage/uploads/<date>/", "storage/uploads/2026-09-20/doc_8f12a8bc.pdf"),
        ("Seed Data", "data/seed/", "data/seed/initial_sources.json"),
        ("Excel / CSV Files", "data/spreadsheets/", "data/spreadsheets/regional_media_intelligence.xlsx"),
        ("Database & Migration Files", "database/", "database/migrations/versions/20260101_0001_init.py"),
        ("Uploaded Files (User Uploads)", "storage/uploads/", "storage/uploads/temp_chunks/chunk_01.part"),
        ("Generated / Output Files", "storage/generated/ & storage/pages/", "storage/generated/crops/art_c104_p1_crop.png"),
        ("Configuration Files", "config/", "config/crisis_scoring.json"),
        ("Environment Variables & .env", "Project root & environments/", ".env.example, environments/.env.development"),
        ("Scripts & Utilities", "scripts/", "scripts/download_models.py"),
        ("API & Backend Code", "backend/", "backend/api/v1/articles.py"),
        ("Frontend Code", "frontend/src/", "frontend/src/components/evidence/newspaper_canvas.tsx"),
        ("Logs", "logs/", "logs/pipeline.log"),
        ("Temporary & Cache Files", "tmp/", "tmp/ocr_cache/deskew_buffer_01.png"),
        ("Tests", "tests/", "tests/backend/test_risk_formula.py"),
        ("Documentation", "docs/", "docs/architecture/risk_score_engine.md")
    ]
    
    mtbl = doc.add_table(rows=len(matrix_data), cols=3)
    mtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(mtbl, color="CBD5E1", sz="4", val="single")
    
    m_widths = [Inches(2.0), Inches(2.3), Inches(2.4)]
    
    for row_idx, row_vals in enumerate(matrix_data):
        row = mtbl.rows[row_idx]
        is_header = (row_idx == 0)
        
        for col_idx, text in enumerate(row_vals):
            cell = row.cells[col_idx]
            cell.width = m_widths[col_idx]
            
            if is_header:
                set_cell_background(cell, HEADER_BG)
            elif row_idx % 2 == 1:
                set_cell_background(cell, ROW_ALT_BG)
                
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.size = Pt(9)
            if is_header:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if col_idx == 0:
                    r.font.bold = True
                r.font.color.rgb = DARK_TEXT

    doc.add_paragraph().paragraph_format.space_after = Pt(14)
    
    # Section 5: Production .gitignore Blueprint
    h5 = doc.add_paragraph()
    h5.paragraph_format.space_before = Pt(18)
    h5.paragraph_format.space_after = Pt(8)
    r = h5.add_run("5. Production .gitignore Configuration")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = PRIMARY
    
    p_git = doc.add_paragraph("To protect sensitive environment credentials and prevent multi-gigabyte ML weights from polluting version control, ensure the following `.gitignore` rules are active:")
    p_git.paragraph_format.space_after = Pt(8)
    
    gitignore_text = """# Environment & Secrets
.env
.env.local
.env.*.local
*.pem
*.key

# Python & Caches
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Node & Frontend
node_modules/
.next/
out/
build/
dist/
*.tsbuildinfo

# AI/ML Models & Large Binaries
models/**/*.bin
models/**/*.safetensors
models/**/*.pt
models/**/*.onnx
models/**/*.gguf
!models/**/.gitkeep

# Storage, Uploads & Generated Outputs
storage/uploads/*
storage/pages/*
storage/generated/*
storage/exports/*
!storage/**/.gitkeep

# Logs & Temporary Buffers
logs/*.log
logs/*.json
tmp/*
!tmp/.gitkeep
!logs/.gitkeep

# Database Files
database/sqlite/*.db
database/sqlite/*.sqlite3"""

    git_table = doc.add_table(rows=1, cols=1)
    git_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    git_cell = git_table.cell(0, 0)
    set_cell_background(git_cell, CODE_BG)
    set_cell_margins(git_cell, top=120, bottom=120, left=150, right=150)
    
    p_gcode = git_cell.paragraphs[0]
    p_gcode.paragraph_format.space_before = Pt(0)
    p_gcode.paragraph_format.space_after = Pt(0)
    r_gcode = p_gcode.add_run(gitignore_text)
    r_gcode.font.name = 'Consolas'
    r_gcode.font.size = Pt(8.5)
    r_gcode.font.color.rgb = DARK_TEXT

    doc.save(filename)
    print(f"Successfully generated Word document: {filename}")

if __name__ == "__main__":
    build_docx("d:/Vee_Project/Project_Folder_Structure_Specification.docx")
