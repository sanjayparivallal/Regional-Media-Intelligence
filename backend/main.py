"""
Regional Media Intelligence Agent — FastAPI Application

Main entry point. Mounts all API routes and serves static files.
"""

import os
import sys

# Suppress transformers/tqdm weight-loading progress bars globally
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import init_db, close_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    try:
        import torch
        torch.set_num_threads(2)
    except Exception:
        pass

    settings.ensure_directories()
    await init_db()

    # Clean up any orphaned running jobs from prior restarts
    try:
        from database import async_session
        from models.document import ProcessingJob, Document, DocumentStatus
        from sqlalchemy import update
        async with async_session() as db:
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.status == "running")
                .values(status="failed", error_message="Server restarted during processing. Ready to reprocess.")
            )
            await db.execute(
                update(Document)
                .where(Document.status == DocumentStatus.PROCESSING)
                .values(status=DocumentStatus.FAILED, error_message="Server restarted during processing. Ready to reprocess.")
            )
            await db.commit()
    except Exception:
        pass

    yield

    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="AI-powered regional media intelligence platform. Transforms newspaper scans into actionable intelligence using local open-source AI models.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
from api.documents import router as documents_router
from api.alerts import router as alerts_router
from api.routes import (
    articles_router, reviews_router, brands_router,
    analytics_router, audit_router, search_router,
    publications_router, incidents_router,
)

app.include_router(documents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(brands_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(publications_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")

# Serve storage files (page images, uploads)
storage_path = Path(settings.storage_path)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "demo_mode": settings.demo_mode,
        "version": "1.0.0",
    }


@app.get("/api/system/info")
async def system_info():
    """System information including hardware and model status."""
    from pipeline.hardware import detect_hardware
    hw = detect_hardware()
    return {
        "hardware": hw,
        "demo_mode": settings.demo_mode,
        "ocr_engine": settings.ocr_engine,
        "translation_model": settings.translation_model,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
