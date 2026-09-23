"""
Excel Storage Service for Regional Media Intelligence Agent.

Provides thread-safe spreadsheet-backed persistence for all entities:
- Documents, Pages, Articles, Translations, Alerts, AuditLogs, Reviews
- MonitoredBrands, AIAnalysis, Entities, CrisisScores, BrandMentions
- HarvestSources, HarvestJobs, HarvestAttempts
"""

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.workbook import Workbook

logger = logging.getLogger(__name__)

_GLOBAL_LOCK = threading.RLock()

DEFAULT_SHEETS: Dict[str, List[str]] = {
    "Documents": [
        "document_id", "original_filename", "storage_path", "file_hash", "file_size",
        "page_count", "mime_type", "language", "source_type", "processing_status",
        "processing_error", "current_stage", "progress_percent", "created_at",
        "updated_at", "processed_at",
    ],
    "Pages": [
        "page_id", "document_id", "page_number", "image_path", "width", "height",
        "dpi", "ocr_engine", "ocr_confidence", "ocr_text", "ocr_words_count",
        "created_at",
    ],
    "Articles": [
        "article_id", "document_id", "page_id", "page_number", "headline",
        "raw_text", "language", "language_confidence", "category",
        "bounding_box", "created_at",
    ],
    "Translations": [
        "translation_id", "article_id", "source_text", "translated_text",
        "source_language", "target_language", "model_name", "created_at",
    ],
    "Alerts": [
        "alert_id", "article_id", "document_id", "brand_name", "severity",
        "title", "summary", "risk_score", "sentiment_score", "created_at",
    ],
    "AuditLogs": [
        "log_id", "document_id", "article_id", "stage", "status", "duration_ms",
        "metadata", "created_at",
    ],
    "Reviews": [
        "review_id", "article_id", "document_id", "status", "reviewer_notes",
        "assigned_to", "created_at", "updated_at",
    ],
    "MonitoredBrands": [
        "brand_id", "brand_name", "aliases", "industry", "keywords", "enabled",
        "created_at", "updated_at",
    ],
    "AIAnalysis": [
        "analysis_id", "article_id", "sentiment", "sentiment_score", "summary",
        "created_at",
    ],
    "Entities": [
        "entity_id", "article_id", "name", "type", "score", "created_at",
    ],
    "CrisisScores": [
        "score_id", "article_id", "crisis_type", "risk_score", "severity",
        "created_at",
    ],
    "BrandMentions": [
        "mention_id", "article_id", "document_id", "brand_id", "brand_name",
        "context", "sentiment", "risk_score", "created_at",
    ],
    "HarvestSources": [
        "id", "name", "publisher", "language", "language_code", "region",
        "source_type", "enabled", "requires_login", "url_template",
        "last_harvest_status", "last_harvest_at", "last_document_id",
    ],
    "HarvestJobs": [
        "job_id", "target_date", "started_at", "completed_at", "status",
        "total_sources", "successful_sources", "failed_sources",
        "auth_required", "manual_action_required", "documents_downloaded",
        "duration_seconds", "triggered_by",
    ],
    "HarvestAttempts": [
        "attempt_id", "job_id", "source_id", "source_name", "edition_name",
        "language", "language_code", "target_date", "status",
        "discovered_url", "file_path", "file_size", "sha256",
        "document_id", "error_type", "error_message", "retry_count",
        "started_at", "completed_at", "duration_seconds",
    ],
}


def _matches_filter(row_val: Any, filter_val: Any) -> bool:
    """Compare a row value with a query filter value flexibly."""
    if filter_val is None:
        return row_val is None or row_val == ""

    # Boolean comparison
    if isinstance(filter_val, bool):
        if isinstance(row_val, bool):
            return row_val == filter_val
        if isinstance(row_val, (int, float)):
            return bool(row_val) == filter_val
        if isinstance(row_val, str):
            lower = row_val.strip().lower()
            if lower in ("true", "1", "yes"):
                return filter_val is True
            if lower in ("false", "0", "no", ""):
                return filter_val is False
        return False

    # String comparison
    if isinstance(filter_val, str):
        if row_val is None:
            return False
        return str(row_val).strip().lower() == filter_val.strip().lower()

    # Numeric comparison
    if isinstance(filter_val, (int, float)):
        if isinstance(row_val, (int, float)):
            return row_val == filter_val
        if isinstance(row_val, str):
            try:
                return float(row_val) == float(filter_val)
            except ValueError:
                return False
        return False

    return row_val == filter_val


def _serialize_val(val: Any) -> Any:
    """Serialize values safely into an Excel cell."""
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value)
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, (datetime,)):
        return val.isoformat()
    return val


def _deserialize_cell(val: Any) -> Any:
    """Normalize Excel cell values."""
    if val is None:
        return None
    if isinstance(val, str):
        if val.startswith("AttemptStatus."):
            return val.replace("AttemptStatus.", "")
        if val.startswith("HarvestStatus."):
            return val.replace("HarvestStatus.", "")
    return val


##############################################################################
# MIGRATION NOTE
# ExcelStorageService is now a transparent alias for DBStorageService.
# All call-sites (api/, workers/, harvesting/) continue to work unchanged.
# The class definition below is kept only as a fallback if the DB import fails.
##############################################################################

try:
    from storage.db_storage_service import DBStorageService as ExcelStorageService  # noqa: F401
    import logging as _logging
    _logging.getLogger(__name__).info("[Storage] Using DBStorageService (PostgreSQL)")
except Exception as _db_import_err:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        f"[Storage] DBStorageService unavailable ({_db_import_err}), falling back to Excel"
    )

    class ExcelStorageService:
        """Thread-safe Excel persistence engine (fallback)."""

    def __init__(self, excel_path: Optional[str] = None):
        if excel_path:
            self.file_path = Path(excel_path).resolve()
        else:
            # Default to backend/rmi_db.xlsx
            env_path = os.environ.get("RMI_EXCEL_PATH")
            if env_path:
                self.file_path = Path(env_path).resolve()
            else:
                backend_dir = Path(__file__).resolve().parent.parent
                self.file_path = backend_dir / "rmi_db.xlsx"

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_workbook()

    def _ensure_workbook(self) -> None:
        """Create workbook and sheets if file doesn't exist or is corrupt."""
        with _GLOBAL_LOCK:
            if not self.file_path.exists():
                wb = Workbook()
                default_sheet = wb.active
                is_first = True

                for sheet_name, cols in DEFAULT_SHEETS.items():
                    if is_first and default_sheet is not None:
                        ws = default_sheet
                        ws.title = sheet_name
                        is_first = False
                    else:
                        ws = wb.create_sheet(title=sheet_name)
                    ws.append(cols)

                self._save_workbook(wb)
                wb.close()
                logger.info(f"Initialized new Excel storage at {self.file_path}")
            else:
                # Ensure all required sheets exist; recover from corruption
                try:
                    wb = openpyxl.load_workbook(self.file_path)
                    modified = False
                    for sheet_name, cols in DEFAULT_SHEETS.items():
                        if sheet_name not in wb.sheetnames:
                            ws = wb.create_sheet(title=sheet_name)
                            ws.append(cols)
                            modified = True
                    if modified:
                        self._save_workbook(wb)
                    wb.close()
                except Exception as e:
                    logger.warning(f"Error checking workbook sheets: {e}")
                    self._recover_corrupt_workbook(reason=str(e))

    def _recover_corrupt_workbook(self, reason: str = "") -> None:
        """
        Back up the corrupt workbook and create a fresh one.

        Called when openpyxl raises BadZipFile or any load error.
        The backup is kept so data is not silently discarded.
        """
        import shutil
        from datetime import datetime as _dt
        backup_path = self.file_path.with_suffix(
            f".corrupt_backup_{_dt.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        try:
            if self.file_path.exists():
                shutil.move(str(self.file_path), str(backup_path))
                logger.error(
                    f"rmi_db.xlsx was corrupt ({reason}). "
                    f"Backed up to {backup_path.name} and recreating a fresh workbook."
                )
        except Exception as mv_err:
            logger.error(f"Could not back up corrupt workbook: {mv_err}")

        # Create a fresh workbook
        wb = Workbook()
        default_sheet = wb.active
        is_first = True
        for sheet_name, cols in DEFAULT_SHEETS.items():
            if is_first and default_sheet is not None:
                ws = default_sheet
                ws.title = sheet_name
                is_first = False
            else:
                ws = wb.create_sheet(title=sheet_name)
            ws.append(cols)
        self._save_workbook(wb)
        wb.close()
        logger.info("Fresh Excel workbook created after corruption recovery.")

    def _load_workbook_safe(self, read_only: bool = False) -> openpyxl.Workbook:
        """
        Load workbook, recovering from corruption automatically.
        Retries transient read collisions before declaring corruption.
        """
        for attempt in range(1, 16):
            try:
                return openpyxl.load_workbook(self.file_path, data_only=read_only)
            except Exception as e:
                if attempt < 15:
                    time.sleep(0.2)
                else:
                    logger.error(f"Workbook load failed ({e}) after 15 attempts, recovering...")
                    self._recover_corrupt_workbook(reason=str(e))
                    return openpyxl.load_workbook(self.file_path, data_only=read_only)

    def _save_workbook(self, wb: openpyxl.Workbook, max_retries: int = 15, retry_delay: float = 0.2) -> None:
        """Save workbook atomically with retries to handle transient file locks."""
        import uuid
        tmp_path = self.file_path.with_suffix(f".tmp_{uuid.uuid4().hex[:8]}.xlsx")
        try:
            wb.save(tmp_path)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            raise

        for attempt in range(1, max_retries + 1):
            try:
                os.replace(str(tmp_path), str(self.file_path))
                return
            except (PermissionError, OSError) as pe:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass
                    logger.error(f"Failed to replace '{self.file_path}' after {max_retries} attempts: {pe}")
                    raise

    def _get_or_create_sheet(self, wb: openpyxl.Workbook, sheet_name: str) -> openpyxl.worksheet.worksheet.Worksheet:
        """Get worksheet or create if not present."""
        if sheet_name in wb.sheetnames:
            return wb[sheet_name]
        ws = wb.create_sheet(title=sheet_name)
        cols = DEFAULT_SHEETS.get(sheet_name, [])
        if cols:
            ws.append(cols)
        return ws

    def _get_headers(self, ws: openpyxl.worksheet.worksheet.Worksheet) -> List[str]:
        """Return list of column headers from row 1."""
        headers = []
        for cell in ws[1]:
            val = cell.value
            headers.append(str(val) if val is not None else "")
        return headers

    def find_rows(self, sheet_name: str, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find all rows matching query in the specified sheet."""
        query = query or {}
        results: List[Dict[str, Any]] = []

        with _GLOBAL_LOCK:
            if not self.file_path.exists():
                return results

            wb = None
            try:
                wb = self._load_workbook_safe(read_only=True)
                if sheet_name not in wb.sheetnames:
                    return results

                ws = wb[sheet_name]
                headers = self._get_headers(ws)
                if not headers:
                    return results

                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not any(row):
                        continue
                    row_dict: Dict[str, Any] = {}
                    for col_idx, col_name in enumerate(headers):
                        if not col_name:
                            continue
                        val = row[col_idx] if col_idx < len(row) else None
                        row_dict[col_name] = _deserialize_cell(val)

                    # Filter match check
                    match = True
                    for q_key, q_val in query.items():
                        if not _matches_filter(row_dict.get(q_key), q_val):
                            match = False
                            break

                    if match:
                        results.append(row_dict)
            except Exception as e:
                logger.error(f"Error reading {sheet_name}: {e}")
            finally:
                if wb is not None:
                    try:
                        wb.close()
                    except Exception:
                        pass

        return results

    def find_row(self, sheet_name: str, query: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Find the first row matching query in the specified sheet."""
        rows = self.find_rows(sheet_name, query)
        return rows[0] if rows else None

    def append_row(self, sheet_name: str, row_dict: Dict[str, Any]) -> None:
        """Append a new row to sheet, automatically expanding columns if needed."""
        with _GLOBAL_LOCK:
            wb = None
            try:
                wb = self._load_workbook_safe()
                ws = self._get_or_create_sheet(wb, sheet_name)
                headers = self._get_headers(ws)

                # Check if any keys in row_dict are missing from headers
                new_cols = [k for k in row_dict.keys() if k not in headers]
                if new_cols:
                    for col in new_cols:
                        headers.append(col)
                        ws.cell(row=1, column=len(headers), value=col)

                # Build row values matching header positions
                row_vals = [_serialize_val(row_dict.get(h)) for h in headers]
                ws.append(row_vals)

                self._save_workbook(wb)
            finally:
                if wb is not None:
                    try:
                        wb.close()
                    except Exception:
                        pass

    def update_row(self, sheet_name: str, query: Dict[str, Any], update_dict: Dict[str, Any]) -> bool:
        """Update matching rows in sheet. Adds new columns if needed. Returns True if any matched."""
        with _GLOBAL_LOCK:
            wb = None
            try:
                wb = self._load_workbook_safe()
                if sheet_name not in wb.sheetnames:
                    return False

                ws = wb[sheet_name]
                headers = self._get_headers(ws)

                # Add any new columns to headers
                new_cols = [k for k in update_dict.keys() if k not in headers]
                if new_cols:
                    for col in new_cols:
                        headers.append(col)
                        ws.cell(row=1, column=len(headers), value=col)

                matched = False
                for row_idx in range(2, ws.max_row + 1):
                    row_dict: Dict[str, Any] = {}
                    for col_idx, col_name in enumerate(headers):
                        if not col_name:
                            continue
                        val = ws.cell(row=row_idx, column=col_idx + 1).value
                        row_dict[col_name] = _deserialize_cell(val)

                    # Check query match
                    match = True
                    for q_key, q_val in query.items():
                        if not _matches_filter(row_dict.get(q_key), q_val):
                            match = False
                            break

                    if match:
                        matched = True
                        for u_key, u_val in update_dict.items():
                            c_idx = headers.index(u_key) + 1
                            ws.cell(row=row_idx, column=c_idx, value=_serialize_val(u_val))

                if matched:
                    self._save_workbook(wb)
                return matched
            finally:
                if wb is not None:
                    try:
                        wb.close()
                    except Exception:
                        pass

    def delete_row(self, sheet_name: str, query: Dict[str, Any]) -> bool:
        """Delete first matching row."""
        return self.delete_rows(sheet_name, query, limit=1) > 0

    def delete_rows(self, sheet_name: str, query: Dict[str, Any], limit: Optional[int] = None) -> int:
        """Delete matching rows in sheet. Returns count of deleted rows."""
        with _GLOBAL_LOCK:
            wb = None
            try:
                wb = self._load_workbook_safe()
                if sheet_name not in wb.sheetnames:
                    return 0

                ws = wb[sheet_name]
                headers = self._get_headers(ws)
                deleted_count = 0

                # Iterate backwards to safely delete rows by index
                for row_idx in range(ws.max_row, 1, -1):
                    row_dict: Dict[str, Any] = {}
                    for col_idx, col_name in enumerate(headers):
                        if not col_name:
                            continue
                        val = ws.cell(row=row_idx, column=col_idx + 1).value
                        row_dict[col_name] = _deserialize_cell(val)

                    match = True
                    for q_key, q_val in query.items():
                        if not _matches_filter(row_dict.get(q_key), q_val):
                            match = False
                            break

                    if match:
                        ws.delete_rows(row_idx)
                        deleted_count += 1
                        if limit and deleted_count >= limit:
                            break

                if deleted_count > 0:
                    self._save_workbook(wb)
                return deleted_count
            finally:
                if wb is not None:
                    try:
                        wb.close()
                    except Exception:
                        pass

    def seed_defaults_if_empty(self) -> None:
        """Seed default monitored brands and sources if sheets are empty."""
        # 1. Monitored Brands
        brands = self.find_rows("MonitoredBrands")
        if not brands:
            brands_config = Path(__file__).resolve().parent.parent.parent / "config" / "brands.json"
            if brands_config.exists():
                try:
                    with open(brands_config, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    now_str = datetime.utcnow().isoformat()
                    for b in data.get("brands", []):
                        self.append_row("MonitoredBrands", {
                            "brand_id": str(uuid.uuid4()),
                            "brand_name": b.get("name"),
                            "aliases": ",".join(b.get("aliases", [])),
                            "industry": b.get("industry", "General"),
                            "keywords": ",".join(b.get("keywords", [])),
                            "enabled": True,
                            "created_at": now_str,
                            "updated_at": now_str,
                        })
                    logger.info("Successfully seeded default MonitoredBrands")
                except Exception as e:
                    logger.warning(f"Failed seeding MonitoredBrands: {e}")

        # 2. Harvest Sources
        sources = self.find_rows("HarvestSources")
        if not sources:
            newspapers_config = Path(__file__).resolve().parent.parent / "harvesting" / "config" / "newspapers.json"
            if newspapers_config.exists():
                try:
                    with open(newspapers_config, "r", encoding="utf-8") as f:
                        news_data = json.load(f)
                    sources_list = news_data.get("sources", []) if isinstance(news_data, dict) else (news_data if isinstance(news_data, list) else [])
                    for s in sources_list:
                        self.append_row("HarvestSources", {
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "publisher": s.get("publisher"),
                            "language": s.get("language"),
                            "language_code": s.get("language_code"),
                            "region": s.get("region"),
                            "source_type": s.get("source_type"),
                            "enabled": s.get("enabled", True),
                            "requires_login": s.get("requires_login", False),
                            "url_template": s.get("url_template", ""),
                            "last_harvest_status": None,
                            "last_harvest_at": None,
                            "last_document_id": None,
                        })
                    logger.info("Successfully seeded default HarvestSources")
                except Exception as e:
                    logger.warning(f"Failed seeding HarvestSources: {e}")
