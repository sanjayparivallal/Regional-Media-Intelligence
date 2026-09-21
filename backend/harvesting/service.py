"""
HarvestingService — main orchestrator.

Responsibilities:
    - Load source configuration from newspapers.json
    - For each enabled source: select harvester → download → validate → submit
    - Parallelise up to HARVEST_MAX_CONCURRENCY concurrent downloads
    - Persist job/attempt records via HarvestStorage
    - Submit downloaded PDFs to the existing RMIA pipeline
      (IndicOCR → IndicTrans2 → LFM 2.5) via process_document_task()
    - Error isolation: one source failure NEVER stops the overall job
"""

import asyncio
import json
import logging
import sys
import time
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Union

from harvesting.core.models import (
    AttemptStatus,
    EditionConfig,
    HarvestAttempt,
    HarvestJob,
    HarvestResult,
    HarvestStatus,
    NewspaperSource,
)
from harvesting.core.registry import HarvesterRegistry
from harvesting.core.storage import HarvestStorage
from harvesting.exceptions import (
    AuthRequired,
    CaptchaRequired,
    Duplicate,
    HarvestError,
    SourceDisabled,
)
from harvesting.utils import get_ist_now

logger = logging.getLogger(__name__)


class HarvestingService:
    """
    Coordinates newspaper harvesting across all configured sources.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        storage_root: Optional[Path] = None,
    ):
        from config import get_settings
        self._settings = get_settings()
        self._config_path = config_path or (
            Path(__file__).parent / "config" / "newspapers.json"
        )
        self._storage = HarvestStorage()
        self._sources: List[NewspaperSource] = []
        self._loaded = False

    # ------------------------------------------------------------------ load

    def load_sources(self) -> List[NewspaperSource]:
        """Load sources from newspapers.json into memory."""
        if not self._config_path.exists():
            logger.warning(f"Newspaper config not found: {self._config_path}")
            return []

        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self._sources = [NewspaperSource(**item) for item in raw]
        self._loaded = True
        logger.info(f"Loaded {len(self._sources)} sources from {self._config_path}")
        return self._sources

    def get_sources(self) -> List[NewspaperSource]:
        if not self._loaded:
            self.load_sources()
        return self._sources

    def get_source(self, source_id: str) -> Optional[NewspaperSource]:
        for s in self.get_sources():
            if s.id == source_id:
                return s
        return None

    # ------------------------------------------------------------------ harvest

    async def run_harvest(
        self,
        target_date: Optional[Union[date, str]] = None,
        source_ids: Optional[List[str]] = None,
        triggered_by: str = "api",
        job_id: Optional[str] = None,
    ) -> HarvestResult:
        """
        Run a complete harvest for target_date.

        Args:
            target_date: Date to harvest (defaults to today in IST)
            source_ids: If provided, only harvest these sources
            triggered_by: "scheduler" | "api" | "manual"
            job_id: Optional existing job ID to update rather than creating new

        Returns:
            HarvestResult summary.
        """
        if not self._loaded:
            self.load_sources()

        if target_date is None:
            from harvesting.utils import get_ist_date
            target_date = get_ist_date()
        elif isinstance(target_date, str):
            try:
                target_date = date.fromisoformat(target_date)
            except ValueError:
                from harvesting.utils import get_ist_date
                target_date = get_ist_date()

        # Filter sources
        sources = [s for s in self._sources if s.enabled]
        if source_ids:
            sources = [s for s in sources if s.id in source_ids]

        effective_job_id = job_id or str(uuid.uuid4())
        job = HarvestJob(
            job_id=effective_job_id,
            target_date=target_date.isoformat(),
            status=HarvestStatus.RUNNING,
            total_sources=len(sources),
            started_at=get_ist_now().isoformat(),
            triggered_by=triggered_by,
        )
        self._storage.save_job(job.model_dump())
        logger.info(
            f"Harvest job={job.job_id} started date={target_date} "
            f"sources={len(sources)} triggered_by={triggered_by}"
        )

        # Run with concurrency limit
        max_concurrency = getattr(self._settings, "harvest_max_concurrency", 5)
        semaphore = asyncio.Semaphore(max_concurrency)
        start_time = time.monotonic()

        tasks = [
            self._harvest_source(source, target_date, job.job_id, semaphore)
            for source in sources
        ]
        # return_exceptions=True: one source failure never aborts other sources
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successful HarvestAttempt results from unexpected exceptions
        attempts = []
        for idx, res in enumerate(raw_results):
            if isinstance(res, Exception):
                # A source raised an uncaught exception — log it, synthesize a FAILED attempt
                src = sources[idx]
                logger.error(
                    f"source={src.id} unhandled exception escaped _harvest_source: {res}",
                    exc_info=res,
                )
                failed_attempt = HarvestAttempt(
                    job_id=job.job_id,
                    source_id=src.id,
                    source_name=src.name,
                    edition_name="unknown",
                    language=src.language,
                    language_code=src.language_code,
                    target_date=target_date.isoformat(),
                    status=AttemptStatus.FAILED,
                    error_type=type(res).__name__,
                    error_message=str(res) or type(res).__name__,
                    started_at=get_ist_now().isoformat(),
                    completed_at=get_ist_now().isoformat(),
                )
                attempts.append(failed_attempt)
            else:
                attempts.append(res)

        # Compute totals
        elapsed = time.monotonic() - start_time
        successful = sum(
            1 for a in attempts
            if a.status == AttemptStatus.PIPELINE_SUBMITTED
        )
        failed = sum(
            1 for a in attempts
            if a.status in (
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.INVALID_PDF,
                AttemptStatus.EMPTY_FILE,
                AttemptStatus.FAILED,
                AttemptStatus.TIMEOUT,
                AttemptStatus.EDITION_NOT_FOUND,
            )
        )
        auth_required = sum(
            1 for a in attempts if a.status == AttemptStatus.AUTH_REQUIRED
        )
        manual = sum(
            1 for a in attempts if a.status == AttemptStatus.CAPTCHA_REQUIRED
        )
        docs_downloaded = sum(
            1 for a in attempts
            if a.status in (
                AttemptStatus.PIPELINE_SUBMITTED,
                AttemptStatus.DUPLICATE,
            )
        )

        overall_status = (
            HarvestStatus.COMPLETED if failed == 0
            else HarvestStatus.PARTIAL if successful > 0
            else HarvestStatus.FAILED
        )

        # Update job record
        job_update = {
            **job.model_dump(),
            "status": overall_status,
            "completed_at": get_ist_now().isoformat(),
            "successful_sources": successful,
            "failed_sources": failed,
            "auth_required": auth_required,
            "manual_action_required": manual,
            "documents_downloaded": docs_downloaded,
            "duration_seconds": round(elapsed, 2),
        }
        self._storage.save_job(job_update)

        result = HarvestResult(
            job_id=job.job_id,
            target_date=target_date.isoformat(),
            total_sources=len(sources),
            successful=successful,
            failed=failed,
            auth_required=auth_required,
            manual_action_required=manual,
            documents_downloaded=docs_downloaded,
            duration_seconds=round(elapsed, 2),
            attempts=[a.model_dump() for a in attempts],
        )
        logger.info(
            f"Harvest job={job.job_id} DONE "
            f"successful={successful} failed={failed} "
            f"duration={elapsed:.1f}s"
        )
        return result

    async def _harvest_source(
        self,
        source: NewspaperSource,
        target_date: date,
        job_id: str,
        semaphore: asyncio.Semaphore,
    ) -> HarvestAttempt:
        """
        Harvest all editions for a single source, error-isolated.

        Returns the attempt record (may carry an error status).
        """
        async with semaphore:
            target_date_str = target_date.isoformat() if hasattr(target_date, "isoformat") else str(target_date)
            attempt = HarvestAttempt(
                job_id=job_id,
                source_id=source.id,
                source_name=source.name,
                edition_name="",
                language=source.language,
                language_code=source.language_code,
                target_date=target_date_str,
                status=AttemptStatus.DOWNLOAD_STARTED,
                started_at=get_ist_now().isoformat(),
            )
            try:
                self._storage.save_attempt(attempt.model_dump())
            except Exception as _save_err:
                logger.warning(f"source={source.id} non-fatal storage error (initial save): {_save_err}")

            try:
                harvester = HarvesterRegistry.get(source)
                editions = await harvester.discover_editions(source, target_date)

                for edition in editions:
                    attempt.edition_name = edition.edition_name
                    attempt.status = AttemptStatus.DOWNLOAD_STARTED
                    try:
                        self._storage.save_attempt(attempt.model_dump())
                    except Exception as _save_err:
                        logger.warning(f"source={source.id} non-fatal storage error (edition start): {_save_err}")

                    try:
                        file_path, sha256 = await harvester.download_edition(
                            source, edition, target_date, self._storage
                        )
                        attempt.file_path = str(file_path)
                        attempt.sha256 = sha256
                        attempt.file_size = file_path.stat().st_size
                        attempt.status = AttemptStatus.VALIDATED

                        # Submit to RMIA pipeline
                        doc_id = await self._submit_to_pipeline(
                            file_path, source, edition, target_date
                        )
                        attempt.document_id = doc_id
                        attempt.status = AttemptStatus.PIPELINE_SUBMITTED

                    except Duplicate as e:
                        logger.info(f"source={source.id} edition={edition.edition_name} DUPLICATE")
                        attempt.status = AttemptStatus.DUPLICATE
                        attempt.error_message = str(e)
                    except AuthRequired as e:
                        logger.warning(f"source={source.id} AUTH_REQUIRED: {e}")
                        attempt.status = AttemptStatus.AUTH_REQUIRED
                        attempt.error_message = str(e)
                        break
                    except CaptchaRequired as e:
                        logger.warning(f"source={source.id} CAPTCHA_REQUIRED: {e}")
                        attempt.status = AttemptStatus.CAPTCHA_REQUIRED
                        attempt.error_message = str(e)
                        break
                    except HarvestError as e:
                        status_name = getattr(e, "status", "FAILED")
                        logger.error(f"source={source.id} edition={edition.edition_name} {status_name}: {e}")
                        attempt.status = AttemptStatus(status_name)
                        attempt.error_type = type(e).__name__
                        attempt.error_message = str(e)
                    except Exception as e:
                        logger.exception(f"source={source.id} unexpected error: {e}")
                        attempt.status = AttemptStatus.FAILED
                        attempt.error_type = type(e).__name__
                        attempt.error_message = str(e) or type(e).__name__

                    # Persist final attempt status for each edition
                    attempt.completed_at = get_ist_now().isoformat()
                    try:
                        self._storage.save_attempt(attempt.model_dump())
                    except Exception as _save_err:
                        logger.warning(f"source={source.id} non-fatal storage error (edition end): {_save_err}")

                    # If fatal error, stop trying further editions for this source
                    if attempt.status in (
                        AttemptStatus.AUTH_REQUIRED,
                        AttemptStatus.CAPTCHA_REQUIRED,
                    ):
                        break

            except Exception as e:
                logger.exception(f"source={source.id} fatal error in harvest: {e}")
                attempt.status = AttemptStatus.FAILED
                attempt.error_type = type(e).__name__
                attempt.error_message = str(e) or type(e).__name__

            attempt.completed_at = get_ist_now().isoformat()
            try:
                self._storage.save_attempt(attempt.model_dump())
            except Exception as _save_err:
                logger.warning(f"source={source.id} non-fatal storage error (final save): {_save_err}")
            return attempt

    async def _submit_to_pipeline(
        self,
        file_path: Path,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        """
        Register the downloaded PDF as a document and start the RMIA pipeline.

        Reuses the EXISTING ExcelStorageService document creation logic
        and triggers process_document_task(document_id, job_id).

        Returns the document_id.
        """
        import hashlib
        import shutil
        import uuid as _uuid
        from datetime import datetime

        from config import get_settings
        settings = get_settings()
        from storage.excel_storage_service import ExcelStorageService
        excel = ExcelStorageService()

        # Copy file into uploads directory
        document_id = str(_uuid.uuid4())
        upload_dest = Path(settings.upload_path) / f"{document_id}.pdf"
        upload_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, upload_dest)

        # Calculate hash for dedup
        with open(upload_dest, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Check if this exact file was already submitted as a document
        existing = excel.find_row("Documents", {"file_hash": file_hash})
        if existing:
            logger.info(
                f"Document already submitted: {existing['document_id']} "
                f"source={source.id}"
            )
            return existing["document_id"]

        # Create document record (same schema as api/documents.py)
        filename = f"{source.id}_{edition.edition_name}_{target_date.isoformat()}.pdf"
        doc_dict = {
            "document_id": document_id,
            "file_name": filename,
            "file_hash": file_hash,
            "source_type": ".pdf",
            "publication": source.name,
            "edition": edition.edition_name,
            "publication_date": target_date.isoformat(),
            "language": source.language_code,
            "total_pages": 0,
            "processing_status": "QUEUED",
            "current_stage": "queued",
            "progress_percent": 0.0,
            "overall_sentiment": None,
            "overall_risk_score": None,
            "processing_started_at": None,
            "processing_completed_at": None,
            "processing_error": None,
            "created_at": datetime.utcnow().isoformat(),
            # Traceability: full chain back to source
            "harvest_source_id": source.id,
            "harvest_source_name": source.name,
            "harvest_edition": edition.edition_name,
            "harvest_region": edition.region or source.region,
            "harvest_language_code": source.language_code,
        }
        excel.append_row("Documents", doc_dict)

        # Trigger RMIA pipeline (IndicOCR → IndicTrans2 → LFM 2.5)
        from workers.processor import process_document_task
        pipeline_job_id = str(_uuid.uuid4())
        asyncio.create_task(process_document_task(document_id, pipeline_job_id))

        logger.info(
            f"Submitted to pipeline: document_id={document_id} "
            f"source={source.id} edition={edition.edition_name}"
        )
        return document_id
