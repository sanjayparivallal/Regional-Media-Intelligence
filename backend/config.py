"""
Regional Media Intelligence Agent — Application Configuration

Loads environment variables with sensible defaults.
The application works in DEMO_MODE without any model downloads.
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    app_name: str = "Regional Media Intelligence Agent"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-a-real-secret"
    demo_mode: bool = False

    # --- Database ---
    database_url: str = "postgresql+asyncpg://rmi_user:saNjay*34@localhost:5432/rmi_db"

    # --- Storage ---
    storage_path: str = "./storage"
    upload_path: str = "./storage/uploads"
    page_image_path: str = "./storage/pages"

    # --- OCR ---
    ocr_engine: str = "indic-ocr"  # indic-ocr | auto | easyocr | paddleocr
    ocr_model_path: str = "./models/indic-ocr"
    tesseract_path: str = ""
    ocr_confidence_threshold: int = 90

    # --- Translation ---
    translation_model: str = "ai4bharat/indictrans2-indic-en-1B"
    translation_model_path: str = "./models/indictrans2"
    hf_token: str = ""

    # --- LFM 2.5 (Ollama) ---
    ollama_url: str = "http://localhost:11434/api/generate"
    lfm_model_name: str = "LiquidAI/lfm2.5-2.6b:q4_k_m"

    # --- Server ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://127.0.0.1:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins

    # --- Processing ---
    max_upload_size_mb: int = 100
    processing_workers: int = 1         # Parallel document slots (1 = safest for single GPU)
    ocr_page_concurrency: int = 1       # Pages OCR'd in parallel per document (1 = sequential, safe for GPU)
    ocr_batch_size_gpu: int = 16        # EasyOCR batch size on GPU — 16 is safe for RTX 2050 (4 GB VRAM)
    ocr_batch_size_cpu: int = 16        # EasyOCR batch size on CPU
    ocr_max_image_dim: int = 1800       # Max image dimension before downscale (at 150 DPI broadsheet pages are ~1000px wide, well within limit)
    warmup_models: bool = True          # Pre-warm OCR + translation on startup
    translation_num_beams: int = 1      # Beam search width (1=greedy, fastest; 4=best quality)

    # --- Harvesting ---
    harvest_schedule: str = "06:30"           # HH:MM in harvest_timezone
    harvest_timezone: str = "Asia/Kolkata"
    harvest_max_concurrency: int = 5          # Parallel source downloads
    harvest_newspapers_config: str = "./harvesting/config/newspapers.json"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self):
        """Create storage directories if they don't exist."""
        for path_str in [self.storage_path, self.upload_path, self.page_image_path]:
            Path(path_str).mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = [
            str(Path(__file__).parent.parent / ".env"),
            str(Path(__file__).parent / ".env"),
            ".env",
        ]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
