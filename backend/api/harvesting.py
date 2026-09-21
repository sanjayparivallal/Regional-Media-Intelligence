"""
Harvesting API router.

Endpoints:
    GET  /harvesting/sources               — list configured sources
    PATCH /harvesting/sources/{id}         — enable / disable a source
    GET  /harvesting/jobs                  — list past harvest jobs
    GET  /harvesting/jobs/{job_id}         — job detail + attempts
    POST /harvesting/run                   — trigger harvest NOW (manual)
    POST /harvesting/run/scheduled         — trigger scheduler-equivalent run
    GET  /harvesting/documents             — harvested documents (with traceability)
    POST /harvesting/sources/{id}/reauthenticate — prompt reauthentication

All triggered harvests run as background asyncio tasks — they return immediately
with a job_id and status=RUNNING so the UI can poll.
"""

import asyncio
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/harvesting", tags=["Harvesting"])


# ------------------------------------------------------------------ request schemas

class RunHarvestRequest(BaseModel):
    target_date: Optional[str] = None          # ISO date YYYY-MM-DD; defaults to IST today
    source_ids: Optional[List[str]] = None     # Filter to specific sources
    triggered_by: str = "api"


class PatchSourceRequest(BaseModel):
    enabled: Optional[bool] = None


# ------------------------------------------------------------------ helper

def _get_service():
    from harvesting.service import HarvestingService
    svc = HarvestingService()
    svc.load_sources()
    return svc


def _get_storage():
    from harvesting.core.storage import HarvestStorage
    return HarvestStorage()


# ------------------------------------------------------------------ sources

@router.get("/sources")
async def list_sources():
    """
    List all configured newspaper sources.
    Returns both enabled and disabled sources, with runtime state.
    """
    svc = _get_service()
    sources = svc.get_sources()
    storage = _get_storage()

    result = []
    for src in sources:
        latest = storage.get_latest_attempt_for_source(src.id)
        result.append({
            **src.model_dump(),
            "last_harvest_status": latest.get("status") if latest else None,
            "last_harvest_at": latest.get("completed_at") if latest else None,
            "last_document_id": latest.get("document_id") if latest else None,
        })
    return result


@router.patch("/sources/{source_id}")
async def update_source(source_id: str, body: PatchSourceRequest):
    """
    Enable or disable a newspaper source at runtime.

    Note: Changes are applied in memory only for the current session.
    To persist, edit harvesting/config/newspapers.json.
    """
    svc = _get_service()
    source = svc.get_source(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")

    if body.enabled is not None:
        source.enabled = body.enabled

    return {
        "source_id": source_id,
        "enabled": source.enabled,
        "message": f"Source {'enabled' if source.enabled else 'disabled'} for this session. Edit newspapers.json to persist."
    }


# ------------------------------------------------------------------ manual run

@router.post("/run")
async def run_harvest_now(body: RunHarvestRequest, background_tasks: BackgroundTasks):
    """
    **Trigger a harvest immediately.**

    - Returns instantly with job_id and status=RUNNING
    - Harvest runs in the background
    - Poll GET /harvesting/jobs/{job_id} to track progress

    Request body:
        target_date   — ISO date (default: today IST)
        source_ids    — list of source IDs to harvest (default: all enabled)
        triggered_by  — label for audit trail (default: "api")
    """
    # Parse target date
    target_date: Optional[date] = None
    if body.target_date:
        try:
            target_date = date.fromisoformat(body.target_date)
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {body.target_date}. Use YYYY-MM-DD.")

    from harvesting.service import HarvestingService
    from harvesting.utils import get_ist_date

    svc = HarvestingService()
    svc.load_sources()

    if target_date is None:
        target_date = get_ist_date()

    # Create a placeholder job record to return immediately
    from harvesting.core.models import HarvestJob, HarvestStatus
    from harvesting.utils import get_ist_now
    from harvesting.core.storage import HarvestStorage

    storage = HarvestStorage()
    job = HarvestJob(
        target_date=target_date.isoformat(),
        status=HarvestStatus.RUNNING,
        triggered_by=body.triggered_by or "api",
        started_at=get_ist_now().isoformat(),
    )
    storage.save_job(job.model_dump())

    # Run in background
    async def _bg():
        try:
            result = await svc.run_harvest(
                target_date=target_date,
                source_ids=body.source_ids,
                triggered_by=body.triggered_by or "api",
                job_id=job.job_id,
            )
            logger.info(f"Background harvest {job.job_id} complete: {result.successful} ok, {result.failed} failed")
        except Exception:
            logger.exception(f"Background harvest {job.job_id} failed with exception")

    background_tasks.add_task(_bg)

    return {
        "job_id": job.job_id,
        "status": "RUNNING",
        "target_date": target_date.isoformat(),
        "triggered_by": body.triggered_by or "api",
        "message": "Harvest started. Poll GET /api/harvesting/jobs for progress.",
        "poll_url": f"/api/harvesting/jobs/{job.job_id}",
    }


@router.post("/run/scheduled")
async def run_scheduled_now(background_tasks: BackgroundTasks):
    """
    **Trigger the scheduled harvest job immediately** — same as the cron would run.

    Useful for:
    - Testing the scheduler without waiting for 06:30
    - Recovering missed harvests after a server restart
    - Manual operator intervention
    """
    from harvesting.utils import get_ist_date
    target_date = get_ist_date()

    return await run_harvest_now(
        RunHarvestRequest(target_date=target_date.isoformat(), triggered_by="scheduled_manual"),
        background_tasks,
    )


# ------------------------------------------------------------------ jobs

@router.get("/jobs")
async def list_jobs(limit: int = Query(50, le=200)):
    """List recent harvest jobs, newest first."""
    storage = _get_storage()
    jobs = storage.list_jobs(limit=limit)
    return jobs


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get harvest job detail including per-source attempts."""
    storage = _get_storage()
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")

    attempts = storage.list_attempts_for_job(job_id)
    return {**job, "attempts": attempts}


# ------------------------------------------------------------------ documents

@router.get("/documents")
async def list_harvested_documents(
    limit: int = Query(50, le=200),
    source_id: Optional[str] = None,
):
    """
    List documents that were downloaded by the harvesting system.

    These documents are also visible in /api/documents (same store).
    This endpoint adds harvesting-specific filters (by source_id).
    """
    from storage.excel_storage_service import ExcelStorageService
    excel = ExcelStorageService()
    docs = excel.find_rows("Documents", {})

    # Filter to harvested documents only (they have harvest_source_id)
    harvested = [d for d in docs if d.get("harvest_source_id")]

    if source_id:
        harvested = [d for d in harvested if d.get("harvest_source_id") == source_id]

    harvested.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    return harvested[:limit]


# ------------------------------------------------------------------ auth

@router.post("/sources/{source_id}/reauthenticate")
async def request_reauthenticate(source_id: str):
    """
    Mark a source as requiring reauthentication.

    Operator must run the manual auth helper script to save a new session:
        cd backend
        ./venv/Scripts/python.exe harvesting/tools/manual_auth.py {source_id}

    This endpoint returns instructions — it does NOT perform login.
    """
    svc = _get_service()
    source = svc.get_source(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")

    if not source.requires_login:
        raise HTTPException(400, f"Source '{source_id}' does not require authentication")

    from config import get_settings
    from pathlib import Path
    settings = get_settings()
    auth_path = Path(settings.storage_path) / "auth" / f"{source_id}.json"

    return {
        "source_id": source_id,
        "source_name": source.name,
        "requires_login": source.requires_login,
        "auth_state_file": str(auth_path),
        "instructions": (
            "To reauthenticate, run the manual auth helper:\n"
            f"  cd backend\n"
            f"  .\\venv\\Scripts\\python.exe harvesting\\tools\\manual_auth.py {source_id}\n\n"
            "The helper will open a visible browser window for you to log in. "
            "Once logged in, the session will be saved automatically."
        ),
    }
