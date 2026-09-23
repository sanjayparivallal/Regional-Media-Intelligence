"""
DB Storage Service for Regional Media Intelligence Agent.

Drop-in replacement for ExcelStorageService backed by PostgreSQL.

Public API is IDENTICAL to ExcelStorageService:
    append_row(sheet_name, row_dict)
    update_row(sheet_name, query, update_dict) -> bool
    find_rows(sheet_name, query) -> List[dict]
    find_row(sheet_name, query) -> Optional[dict]
    delete_rows(sheet_name, query, limit=None) -> int
    delete_row(sheet_name, query) -> bool
    seed_defaults_if_empty()

Design:
  - One PostgreSQL table per logical "sheet" (same names as DEFAULT_SHEETS)
  - All column values stored as TEXT (nullable) to match Excel's loose typing
  - Extra columns added at runtime via ALTER TABLE ... ADD COLUMN IF NOT EXISTS
  - Synchronous SQLAlchemy + psycopg2 so call-sites require zero changes
  - Thread safety via SQLAlchemy connection pool (NullPool for safety)
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, Text, inspect
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema definition — mirrors DEFAULT_SHEETS in excel_storage_service.py
# ---------------------------------------------------------------------------

DEFAULT_SHEETS: Dict[str, List[str]] = {
    "Documents": [
        "document_id", "original_filename", "storage_path", "file_hash", "file_size",
        "page_count", "mime_type", "language", "source_type", "processing_status",
        "processing_error", "current_stage", "progress_percent", "created_at",
        "updated_at", "processed_at",
        # Extra columns used by API/processor that were dynamically added to Excel
        "file_name", "publication", "edition", "publication_date",
        "total_pages", "overall_sentiment", "overall_risk_score",
        "processing_started_at", "processing_completed_at",
        "harvest_source_id", "harvest_source_name", "harvest_edition",
        "harvest_region", "harvest_date", "harvest_url",
    ],
    "Pages": [
        "page_id", "document_id", "page_number", "image_path", "width", "height",
        "dpi", "ocr_engine", "ocr_confidence", "ocr_text", "ocr_words_count",
        "created_at",
        # Extra columns used by the pipeline
        "page_width", "page_height", "has_extractable_text",
        "is_scanned", "ocr_status", "language",
    ],
    "Articles": [
        "article_id", "document_id", "page_id", "page_number", "headline",
        "raw_text", "language", "language_confidence", "category",
        "bounding_box", "created_at",
        # Extra columns used by pipeline / API
        "original_text", "word_count", "ocr_confidence",
        "x1", "y1", "x2", "y2",
        "article_type", "article_confidence",
    ],
    "Translations": [
        "translation_id", "article_id", "document_id", "source_text", "translated_text",
        "source_language", "target_language", "model_name", "created_at",
        # Extra columns used by pipeline
        "original_text", "translation_confidence", "entity_protected",
        "review_required", "translation_model",
    ],
    "Alerts": [
        "alert_id", "article_id", "document_id", "brand_name", "severity",
        "title", "summary", "risk_score", "sentiment_score", "created_at",
        # Extra columns used by API / pipeline
        "brand_id", "headline", "crisis_category", "crisis_score",
        "sentiment", "language", "page_number", "publication",
        "alert_status", "matched_text", "reason",
        "evidence_page_path", "evidence_article_coordinates",
    ],
    "AuditLogs": [
        "log_id", "document_id", "article_id", "stage", "status", "duration_ms",
        "metadata", "created_at",
        # Extra columns used by pipeline
        "action", "message", "model", "model_used",
        "started_at", "completed_at", "error", "actor",
        "processing_time_ms",
    ],
    "Reviews": [
        "review_id", "article_id", "document_id", "status", "reviewer_notes",
        "assigned_to", "created_at", "updated_at",
        # Extra columns
        "review_type", "reason", "review_comment", "reviewed_at",
        "original_value", "corrected_value", "reviewer",
    ],
    "MonitoredBrands": [
        "brand_id", "brand_name", "aliases", "industry", "keywords", "enabled",
        "created_at", "updated_at",
    ],
    "AIAnalysis": [
        "analysis_id", "article_id", "sentiment", "sentiment_score", "summary",
        "created_at",
        # Extra columns used by pipeline
        "brand_name", "sentiment_confidence", "crisis_category",
        "crisis_reason", "ai_confidence", "model_name",
    ],
    "Entities": [
        "entity_id", "article_id", "name", "type", "score", "created_at",
        # Extra columns used by pipeline
        "entity_text", "entity_type", "normalized_name",
        "start_position", "end_position", "confidence",
        "is_monitored_brand", "verification_status",
    ],
    "CrisisScores": [
        "score_id", "article_id", "crisis_type", "risk_score", "severity",
        "created_at",
        # Extra columns used by pipeline
        "brand_name", "sentiment_score", "brand_relevance_score",
        "crisis_severity_score", "publication_reach_score",
        "ai_confidence_score", "final_crisis_score",
    ],
    "BrandMentions": [
        "mention_id", "article_id", "document_id", "brand_id", "brand_name",
        "context", "sentiment", "risk_score", "created_at",
        # Extra columns used by API / pipeline
        "matched_text", "match_type", "match_confidence", "verified_by_lfm",
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

# Table name → lowercase for PostgreSQL (quoted in SQL to preserve case)
_TABLE_MAP = {sheet: sheet.lower() for sheet in DEFAULT_SHEETS}


# ---------------------------------------------------------------------------
# Value helpers (mirrors Excel helpers so filtering behaviour is identical)
# ---------------------------------------------------------------------------

def _matches_filter(row_val: Any, filter_val: Any) -> bool:
    """Compare a row value with a query filter value — same semantics as Excel service."""
    if filter_val is None:
        return row_val is None or row_val == ""

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

    if isinstance(filter_val, str):
        if row_val is None:
            return False
        return str(row_val).strip().lower() == filter_val.strip().lower()

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


def _serialize_val(val: Any) -> Optional[str]:
    """Convert Python value to a TEXT-compatible string (or None)."""
    if val is None:
        return None
    if hasattr(val, "value"):          # Enum
        return str(val.value)
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, bool):
        return str(val)
    return str(val)


def _deserialize_val(val: Optional[str]) -> Any:
    """Normalize TEXT values back to Python — same as Excel _deserialize_cell."""
    if val is None:
        return None
    if isinstance(val, str):
        if val.startswith("AttemptStatus."):
            return val.replace("AttemptStatus.", "")
        if val.startswith("HarvestStatus."):
            return val.replace("HarvestStatus.", "")
    return val


# ---------------------------------------------------------------------------
# Engine singleton
# ---------------------------------------------------------------------------

_engine: Optional[Engine] = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        raw_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://rmi_user:saNjay*34@localhost:5432/rmi_db"
        )
        # Convert async driver URL to sync psycopg2 URL
        sync_url = (
            raw_url
            .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("postgresql+aiopg://", "postgresql+psycopg2://")
        )
        if not sync_url.startswith("postgresql"):
            sync_url = "postgresql+psycopg2://rmi_user:saNjay*34@localhost:5432/rmi_db"

        _engine = create_engine(
            sync_url,
            poolclass=NullPool,    # No connection pool — safe for multi-worker/thread use
            echo=False,
            connect_args={"options": "-c client_encoding=UTF8"},
        )
        logger.info(f"[DBStorage] Engine created: {sync_url.split('@')[-1]}")
    return _engine


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------

def _table_name(sheet_name: str) -> str:
    """Return quoted PostgreSQL table name for a sheet."""
    return f'"{sheet_name.lower()}"'


def _ensure_tables(engine: Engine) -> None:
    """Create all tables and ensure all columns exist."""
    with engine.connect() as conn:
        for sheet_name, columns in DEFAULT_SHEETS.items():
            tbl = _table_name(sheet_name)
            # Build column list — all TEXT nullable
            col_defs = ",\n    ".join(f'"{col}" TEXT' for col in columns)
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    _pk SERIAL PRIMARY KEY,
                    {col_defs}
                )
            """))
            # Ensure all columns exist for tables created with an older schema
            for col in columns:
                conn.execute(text(
                    f'ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS "{col}" TEXT'
                ))
        conn.commit()
    logger.info("[DBStorage] All tables and columns ensured.")



def _ensure_columns(engine: Engine, sheet_name: str, columns: List[str]) -> None:
    """Add any columns that are missing from the table (ALTER TABLE ADD COLUMN IF NOT EXISTS)."""
    tbl = _table_name(sheet_name)
    with engine.connect() as conn:
        for col in columns:
            try:
                conn.execute(text(
                    f'ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS "{col}" TEXT'
                ))
            except Exception:
                pass  # Column already exists or other non-fatal error
        conn.commit()


# ---------------------------------------------------------------------------
# DBStorageService
# ---------------------------------------------------------------------------

class DBStorageService:
    """
    Thread-safe PostgreSQL persistence engine.

    Implements the same public API as ExcelStorageService:
        append_row, update_row, find_rows, find_row,
        delete_rows, delete_row, seed_defaults_if_empty
    """

    def __init__(self, excel_path: Optional[str] = None):
        # excel_path is accepted but ignored — kept for signature compatibility
        self._engine = _get_engine()
        self._col_cache: Dict[str, set] = {}
        self._tables_ensured = False
        self._ensure_all_tables()

    def _ensure_all_tables(self) -> None:
        if self._tables_ensured:
            return
        try:
            _ensure_tables(self._engine)
            self._tables_ensured = True
        except Exception as e:
            logger.error(f"[DBStorage] Failed to ensure tables: {e}")

    def _get_table_columns(self, conn, sheet_name: str) -> set:
        """Return the set of column names currently present in the table (cached)."""
        tname = sheet_name.lower()
        if tname not in self._col_cache:
            rs = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :tname
            """), {"tname": tname})
            self._col_cache[tname] = {r[0] for r in rs.fetchall()}
        return self._col_cache[tname]

    def _ensure_sheet_columns(self, sheet_name: str, extra_cols: List[str]) -> None:
        """Dynamically add any new columns the caller is trying to write."""
        tname = sheet_name.lower()
        known = self._col_cache.get(tname) or set(DEFAULT_SHEETS.get(sheet_name, []))
        new_cols = [c for c in extra_cols if c not in known and c != "_pk"]
        if new_cols:
            _ensure_columns(self._engine, sheet_name, new_cols)
            if tname in self._col_cache:
                self._col_cache[tname].update(new_cols)

    # ------------------------------------------------------------------
    # find_rows / find_row
    # ------------------------------------------------------------------

    def find_rows(
        self, sheet_name: str, query: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Return all rows in sheet matching the query dict."""
        query = query or {}
        tbl = _table_name(sheet_name)
        results: List[Dict[str, Any]] = []

        try:
            with self._engine.connect() as conn:
                # Check table exists
                rs = conn.execute(text(
                    "SELECT to_regclass(:tname)"
                ), {"tname": sheet_name.lower()})
                row = rs.fetchone()
                if not row or row[0] is None:
                    return results

                # Get existing columns to safely validate query fields
                valid_cols = self._get_table_columns(conn, sheet_name)
                sql_where, sql_params, py_filters, can_match = _build_where(query, valid_cols)
                if not can_match:
                    return results

                if sql_where:
                    full_sql = f"SELECT * FROM {tbl} WHERE {sql_where}"
                else:
                    full_sql = f"SELECT * FROM {tbl}"

                rs2 = conn.execute(text(full_sql), sql_params)
                cols = list(rs2.keys())

                for db_row in rs2.fetchall():
                    row_dict = {
                        col: _deserialize_val(db_row[i])
                        for i, col in enumerate(cols)
                        if col != "_pk"
                    }
                    # Apply any remaining Python-side filters (bool, numeric, complex)
                    if all(
                        _matches_filter(row_dict.get(k), v)
                        for k, v in py_filters.items()
                    ):
                        results.append(row_dict)

        except Exception as e:
            logger.error(f"[DBStorage] find_rows({sheet_name}) error: {e}")

        return results

    def find_row(
        self, sheet_name: str, query: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Return first row matching query, or None."""
        rows = self.find_rows(sheet_name, query)
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # append_row
    # ------------------------------------------------------------------

    def append_row(self, sheet_name: str, row_dict: Dict[str, Any]) -> None:
        """Insert a new row into the sheet."""
        if not row_dict:
            return

        tbl = _table_name(sheet_name)

        # Ensure any new columns exist
        self._ensure_sheet_columns(sheet_name, list(row_dict.keys()))

        col_names = [f'"{k}"' for k in row_dict.keys()]
        placeholders = [f":{k}" for k in row_dict.keys()]
        params = {k: _serialize_val(v) for k, v in row_dict.items()}

        sql = (
            f"INSERT INTO {tbl} ({', '.join(col_names)}) "
            f"VALUES ({', '.join(placeholders)})"
        )

        try:
            with self._engine.connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
        except Exception as e:
            logger.error(f"[DBStorage] append_row({sheet_name}) error: {e}")
            raise

    # ------------------------------------------------------------------
    # update_row
    # ------------------------------------------------------------------

    def update_row(
        self,
        sheet_name: str,
        query: Dict[str, Any],
        update_dict: Dict[str, Any],
    ) -> bool:
        """Update all rows matching query. Returns True if any row matched."""
        if not update_dict:
            return False

        tbl = _table_name(sheet_name)

        # Ensure any new columns exist
        self._ensure_sheet_columns(sheet_name, list(update_dict.keys()))

        # We do a SELECT first to identify matching _pk values (reuses Python filter logic)
        matched_pks = self._find_pks(sheet_name, query)
        if not matched_pks:
            return False

        set_clauses = ", ".join(f'"{k}" = :upd_{k}' for k in update_dict.keys())
        params = {f"upd_{k}": _serialize_val(v) for k, v in update_dict.items()}

        # Expand pk list inline to avoid psycopg2 array binding issues
        pk_placeholders = ", ".join(f":pk_{i}" for i in range(len(matched_pks)))
        for i, pk in enumerate(matched_pks):
            params[f"pk_{i}"] = pk

        sql = f"UPDATE {tbl} SET {set_clauses} WHERE _pk IN ({pk_placeholders})"

        try:
            with self._engine.connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"[DBStorage] update_row({sheet_name}) error: {e}")
            raise

    # ------------------------------------------------------------------
    # delete_rows / delete_row
    # ------------------------------------------------------------------

    def delete_row(self, sheet_name: str, query: Dict[str, Any]) -> bool:
        """Delete first matching row. Returns True if deleted."""
        return self.delete_rows(sheet_name, query, limit=1) > 0

    def delete_rows(
        self,
        sheet_name: str,
        query: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> int:
        """Delete all matching rows (or up to `limit`). Returns count deleted."""
        tbl = _table_name(sheet_name)
        matched_pks = self._find_pks(sheet_name, query)
        if not matched_pks:
            return 0

        if limit is not None:
            matched_pks = matched_pks[:limit]

        # Expand pk list inline to avoid psycopg2 array binding issues
        pk_placeholders = ", ".join(f":pk_{i}" for i in range(len(matched_pks)))
        params = {f"pk_{i}": pk for i, pk in enumerate(matched_pks)}
        sql = f"DELETE FROM {tbl} WHERE _pk IN ({pk_placeholders})"
        try:
            with self._engine.connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
            return len(matched_pks)
        except Exception as e:
            logger.error(f"[DBStorage] delete_rows({sheet_name}) error: {e}")
            raise

    # ------------------------------------------------------------------
    # seed_defaults_if_empty
    # ------------------------------------------------------------------

    def seed_defaults_if_empty(self) -> None:
        """Seed default monitored brands and sources if tables are empty."""
        # 1. Monitored Brands
        brands = self.find_rows("MonitoredBrands")
        if not brands:
            brands_config = (
                Path(__file__).resolve().parent.parent.parent
                / "config" / "brands.json"
            )
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
                            "enabled": "True",
                            "created_at": now_str,
                            "updated_at": now_str,
                        })
                    logger.info("[DBStorage] Seeded default MonitoredBrands")
                except Exception as e:
                    logger.warning(f"[DBStorage] Failed seeding MonitoredBrands: {e}")

        # 2. Harvest Sources
        sources = self.find_rows("HarvestSources")
        if not sources:
            newspapers_config = (
                Path(__file__).resolve().parent.parent
                / "harvesting" / "config" / "newspapers.json"
            )
            if newspapers_config.exists():
                try:
                    with open(newspapers_config, "r", encoding="utf-8") as f:
                        news_data = json.load(f)
                    sources_list = (
                        news_data.get("sources", [])
                        if isinstance(news_data, dict)
                        else (news_data if isinstance(news_data, list) else [])
                    )
                    for s in sources_list:
                        self.append_row("HarvestSources", {
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "publisher": s.get("publisher"),
                            "language": s.get("language"),
                            "language_code": s.get("language_code"),
                            "region": s.get("region"),
                            "source_type": s.get("source_type"),
                            "enabled": str(s.get("enabled", True)),
                            "requires_login": str(s.get("requires_login", False)),
                            "url_template": s.get("url_template", ""),
                            "last_harvest_status": None,
                            "last_harvest_at": None,
                            "last_document_id": None,
                        })
                    logger.info("[DBStorage] Seeded default HarvestSources")
                except Exception as e:
                    logger.warning(f"[DBStorage] Failed seeding HarvestSources: {e}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_pks(self, sheet_name: str, query: Dict[str, Any]) -> List[int]:
        """Return list of _pk values for rows matching query."""
        tbl = _table_name(sheet_name)
        pks: List[int] = []

        try:
            with self._engine.connect() as conn:
                rs = conn.execute(text(
                    "SELECT to_regclass(:tname)"
                ), {"tname": sheet_name.lower()})
                row = rs.fetchone()
                if not row or row[0] is None:
                    return pks

                valid_cols = self._get_table_columns(conn, sheet_name)
                sql_where, sql_params, py_filters, can_match = _build_where(query, valid_cols)
                if not can_match:
                    return pks

                if sql_where:
                    full_sql = f"SELECT * FROM {tbl} WHERE {sql_where}"
                else:
                    full_sql = f"SELECT * FROM {tbl}"

                rs2 = conn.execute(text(full_sql), sql_params)
                cols = list(rs2.keys())

                for db_row in rs2.fetchall():
                    row_dict = {col: db_row[i] for i, col in enumerate(cols)}
                    plain_dict = {
                        col: _deserialize_val(row_dict[col])
                        for col in cols
                        if col != "_pk"
                    }
                    if all(
                        _matches_filter(plain_dict.get(k), v)
                        for k, v in py_filters.items()
                    ):
                        pks.append(row_dict["_pk"])
        except Exception as e:
            logger.error(f"[DBStorage] _find_pks({sheet_name}) error: {e}")

        return pks


# ---------------------------------------------------------------------------
# Query builder helper
# ---------------------------------------------------------------------------

def _build_where(
    query: Dict[str, Any],
    valid_cols: set,
) -> tuple:
    """
    Build a SQL WHERE clause for simple string equality filters.

    Returns (where_clause_str, sql_params_dict, python_only_filters_dict, can_match).

    If any query filter refers to a column not in valid_cols:
      - If filter value is None or empty string, condition is trivially satisfied
        (treated as None/empty, matching Excel behavior).
      - If filter value is non-empty, NO row can match in this table -> can_match = False.
    """
    sql_parts: List[str] = []
    sql_params: Dict[str, Any] = {}
    py_filters: Dict[str, Any] = {}

    for i, (key, val) in enumerate(query.items()):
        param_name = f"qv_{i}"
        if key not in valid_cols:
            if val is None or val == "" or (isinstance(val, str) and val.strip() == ""):
                continue
            else:
                return "", {}, {}, False

        if val is None:
            # NULL or empty string
            sql_parts.append(f'("{key}" IS NULL OR "{key}" = \'\')')
        elif isinstance(val, str):
            # Case-insensitive push to SQL
            sql_parts.append(f'LOWER("{key}") = LOWER(:{param_name})')
            sql_params[param_name] = val
        else:
            # bool / numeric — defer to Python filter to avoid type coercion issues
            py_filters[key] = val

    where_clause = " AND ".join(sql_parts) if sql_parts else ""
    return where_clause, sql_params, py_filters, True
