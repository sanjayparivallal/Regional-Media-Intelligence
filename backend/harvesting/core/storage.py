"""
ExcelStorageService adapter for the harvesting subsystem.

Adds three new sheets to the existing rmi_db Excel workbook:
    HarvestSources  — persisted source registry (mirrors newspapers.json with runtime state)
    HarvestJobs     — one row per harvest run
    HarvestAttempts — one row per edition/source attempt

All reads/writes go through the project's existing ExcelStorageService API.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Column schemas — these define the expected columns in each sheet.
# ExcelStorageService creates missing columns automatically.
_HARVEST_JOB_COLUMNS = [
    "job_id", "target_date", "started_at", "completed_at", "status",
    "total_sources", "successful_sources", "failed_sources",
    "auth_required", "manual_action_required", "documents_downloaded",
    "duration_seconds", "triggered_by",
]

_HARVEST_ATTEMPT_COLUMNS = [
    "attempt_id", "job_id", "source_id", "source_name", "edition_name",
    "language", "language_code", "target_date", "status",
    "discovered_url", "file_path", "file_size", "sha256",
    "document_id", "error_type", "error_message", "retry_count",
    "started_at", "completed_at", "duration_seconds",
]


def _get_excel():
    """Lazy-import ExcelStorageService to avoid circular imports."""
    from storage.excel_storage_service import ExcelStorageService  # type: ignore
    return ExcelStorageService()


class HarvestStorage:
    """Thin adapter over ExcelStorageService for harvesting data."""

    # ------------------------------------------------------------------ jobs

    def save_job(self, job: Dict[str, Any]) -> None:
        excel = _get_excel()
        existing = excel.find_row("HarvestJobs", {"job_id": job["job_id"]})
        if existing:
            excel.update_row("HarvestJobs", {"job_id": job["job_id"]}, job)
        else:
            excel.append_row("HarvestJobs", job)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return _get_excel().find_row("HarvestJobs", {"job_id": job_id})

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = _get_excel().find_rows("HarvestJobs", {})
        rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
        return rows[:limit]

    # --------------------------------------------------------------- attempts

    def save_attempt(self, attempt: Dict[str, Any]) -> None:
        excel = _get_excel()
        existing = excel.find_row("HarvestAttempts", {"attempt_id": attempt["attempt_id"]})
        if existing:
            excel.update_row("HarvestAttempts", {"attempt_id": attempt["attempt_id"]}, attempt)
        else:
            excel.append_row("HarvestAttempts", attempt)

    def list_attempts_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        return _get_excel().find_rows("HarvestAttempts", {"job_id": job_id})

    def list_attempts(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows = _get_excel().find_rows("HarvestAttempts", {})
        rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
        return rows[:limit]

    # ------------------------------------------------ duplicate detection

    def sha256_exists(self, sha256: str) -> bool:
        """Return True if a PDF with this SHA-256 was already downloaded."""
        result = _get_excel().find_row("HarvestAttempts", {"sha256": sha256})
        return result is not None

    # ------------------------------------------------ latest job for source

    def get_latest_attempt_for_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        rows = _get_excel().find_rows("HarvestAttempts", {"source_id": source_id})
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
        return rows[0]
