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
    ocr_engine: str = "auto"  # auto | paddleocr | tesseract | easyocr | hybrid
    ocr_model_path: str = ""
    tesseract_path: str = ""
    ocr_confidence_threshold: int = 90

    # --- Translation ---
    translation_model: str = "facebook/nllb-200-distilled-600M"
    translation_model_path: str = ""

    # --- NER ---
    ner_model_path: str = ""
    spacy_model: str = "en_core_web_sm"

    # --- Sentiment ---
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual"
    classification_model_path: str = ""

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
    processing_workers: int = 2

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
