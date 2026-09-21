"""
Pydantic models for the harvesting subsystem.

These are storage-layer / API-layer models.
They are persisted through ExcelStorageService (not SQLAlchemy).
"""

import enum
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------

class HarvestStatus(str, enum.Enum):
    PENDING       = "PENDING"
    RUNNING       = "RUNNING"
    COMPLETED     = "COMPLETED"
    PARTIAL       = "PARTIAL"
    FAILED        = "FAILED"


class AttemptStatus(str, enum.Enum):
    PENDING            = "PENDING"
    DOWNLOAD_STARTED   = "DOWNLOAD_STARTED"
    DOWNLOADED         = "DOWNLOADED"
    VALIDATED          = "VALIDATED"
    DUPLICATE          = "DUPLICATE"
    PIPELINE_SUBMITTED = "PIPELINE_SUBMITTED"
    DOWNLOAD_FAILED    = "DOWNLOAD_FAILED"
    INVALID_PDF        = "INVALID_PDF"
    EMPTY_FILE         = "EMPTY_FILE"
    AUTH_REQUIRED      = "AUTH_REQUIRED"
    CAPTCHA_REQUIRED   = "CAPTCHA_REQUIRED"
    TIMEOUT            = "TIMEOUT"
    EDITION_NOT_FOUND  = "EDITION_NOT_FOUND"
    DISABLED           = "DISABLED"
    FAILED             = "FAILED"


class SourceType(str, enum.Enum):
    DIRECT_PDF    = "direct_pdf"
    PLAYWRIGHT    = "playwright"
    AUTHENTICATED = "authenticated"
    AGGREGATOR    = "aggregator"


# ---------------------------------------------------------------------------
# Configuration models (from newspapers.json)
# ---------------------------------------------------------------------------

class EditionConfig(BaseModel):
    """One edition of a newspaper (e.g. Chennai, Delhi, National)."""
    edition_name: str
    url_template: Optional[str] = None      # Supports {yyyy}, {mm}, {dd} tokens
    region: Optional[str] = None
    language_override: Optional[str] = None  # If this edition has a different language


class NewspaperSource(BaseModel):
    """A single newspaper source configuration entry."""
    id: str
    name: str
    publisher: str
    language: str
    language_code: str
    region: str
    website_url: Optional[str] = None
    source_type: SourceType = SourceType.DIRECT_PDF
    requires_login: bool = False
    enabled: bool = True
    editions: List[EditionConfig] = Field(default_factory=list)

    # For direct PDF sources — global URL template (overridden per edition)
    url_template: Optional[str] = None

    # Credentials env var prefix, e.g. "THE_HINDU" → THE_HINDU_USERNAME / THE_HINDU_PASSWORD
    credentials_env_prefix: Optional[str] = None

    # Auth state file path (relative to storage/auth/)
    auth_state_file: Optional[str] = None

    # Selectors for Playwright-based sources (optional overrides)
    selectors: Dict[str, Any] = Field(default_factory=dict)

    # Extra metadata preserved in traceability chain
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Runtime / storage models
# ---------------------------------------------------------------------------

class HarvestJob(BaseModel):
    """A complete harvest run for a given date."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_date: str                            # ISO date string YYYY-MM-DD
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: HarvestStatus = HarvestStatus.PENDING
    total_sources: int = 0
    successful_sources: int = 0
    failed_sources: int = 0
    auth_required: int = 0
    manual_action_required: int = 0
    documents_downloaded: int = 0
    duration_seconds: Optional[float] = None
    triggered_by: str = "scheduler"            # "scheduler" | "api" | "manual"


class HarvestAttempt(BaseModel):
    """One attempt to harvest a single edition from a single source."""
    attempt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    source_id: str
    source_name: str
    edition_name: str
    language: str
    language_code: str
    target_date: str
    status: AttemptStatus = AttemptStatus.PENDING
    discovered_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    sha256: Optional[str] = None
    document_id: Optional[str] = None          # RMIA document_id after submission
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class HarvestResult(BaseModel):
    """Structured summary returned from a completed harvest job."""
    job_id: str
    target_date: str
    total_sources: int
    successful: int
    failed: int
    auth_required: int
    manual_action_required: int
    documents_downloaded: int
    duration_seconds: float
    attempts: List[Dict[str, Any]] = Field(default_factory=list)
