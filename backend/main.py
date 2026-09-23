"""
Regional Media Intelligence Agent — FastAPI Application

Main entry point. Mounts all API routes and serves static files.
"""

import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Suppress transformers/tqdm weight-loading progress bars globally and enforce 100% offline air-gapped mode
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    import logging
    logger_main = logging.getLogger(__name__)

    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
            logger_main.info(f"GPU detected: {gpu_name} ({vram_gb} GB VRAM) — running in GPU mode")
            # On GPU: let torch use all CPU cores for data pre/post-processing
            import os
            torch.set_num_threads(os.cpu_count() or 4)
        else:
            logger_main.warning("No CUDA GPU detected — running in CPU mode")
            torch.set_num_threads(2)
    except Exception:
        pass

    settings.ensure_directories()
    
    # Initialize Excel Storage
    from storage.excel_storage_service import ExcelStorageService
    excel = ExcelStorageService()
    excel.seed_defaults_if_empty()

    # Clean up any orphaned running jobs from prior restarts
    try:
        excel.update_row("Documents", {"processing_status": "PROCESSING"}, {"processing_status": "FAILED", "processing_error": "Server restarted during processing. Ready to reprocess."})
    except Exception as e:
        logger_main.warning(f"Failed to reset orphaned jobs: {e}")

    # Start harvest scheduler
    from harvesting.scheduler import start_scheduler, stop_scheduler
    _scheduler = None
    try:
        _scheduler = start_scheduler()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Harvest scheduler failed to start: {e}")

    # Pre-warm OCR + translation models onto GPU in a background thread
    # so the first uploaded paper doesn't pay the cold-start penalty
    if getattr(settings, "warmup_models", True):
        try:
            import asyncio
            from workers.processor import warmup_models
            asyncio.get_event_loop().run_in_executor(None, warmup_models)
            logger_main.info("[Startup] Model warmup dispatched to background thread")
        except Exception as e:
            logger_main.warning(f"[Startup] Model warmup dispatch failed: {e}")

    yield

    # Shutdown
    if _scheduler:
        try:
            stop_scheduler()
        except Exception:
            pass


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
from api.harvesting import router as harvesting_router
from api.routes import (
    articles_router, reviews_router, brands_router,
    analytics_router, search_router, incidents_router,
    publications_router, audit_router
)

app.include_router(documents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(harvesting_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(brands_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(publications_router, prefix="/api")
app.include_router(audit_router, prefix="/api")

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

    gpu_info = {"available": False, "name": None, "vram_gb": None, "cuda": False}
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1),
                "cuda": True,
                "cuda_version": torch.version.cuda,
            }
    except Exception:
        pass

    return {
        "hardware": hw,
        "gpu": gpu_info,
        "demo_mode": settings.demo_mode,
        "ocr_engine": settings.ocr_engine,
        "translation_model": settings.translation_model,
        "processing_workers": settings.processing_workers,
        "ocr_page_concurrency": getattr(settings, "ocr_page_concurrency", 4),
        "ocr_batch_size_gpu": getattr(settings, "ocr_batch_size_gpu", 64),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        reload_excludes=["storage/*", "*.xlsx", "*.log", "*.html", "tests/*", "scratch/*"],
    )
