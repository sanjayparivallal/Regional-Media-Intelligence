"""
Document API endpoints.

POST /documents/upload — Upload PDF/image
GET  /documents        — List documents
GET  /documents/{id}   — Document detail with pages
POST /documents/{id}/process — Start processing pipeline
"""

import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from config import get_settings
from storage.excel_storage_service import ExcelStorageService
from schemas.document import DocumentResponse, DocumentDetail, PageSummary, ProcessingJobResponse
from models.document import DocumentStatus

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
ALLOWED_MIME_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/tiff",
    "image/jpg",
}


def _format_doc_response(d: dict) -> dict:
    """Helper to convert a storage document dictionary to DocumentResponse dictionary."""
    return {
        "id": d["document_id"],
        "filename": d.get("file_name", "unnamed"),
        "original_filename": d.get("file_name", "unnamed"),
        "status": d.get("processing_status", "UPLOADED"),
        "error_message": d.get("processing_error"),
        "current_stage": d.get("current_stage"),
        "progress_percent": float(d.get("progress_percent") or 0.0),
        "overall_sentiment": d.get("overall_sentiment"),
        "overall_risk_score": float(d["overall_risk_score"]) if d.get("overall_risk_score") is not None else None,
        "created_at": d.get("created_at") or datetime.utcnow().isoformat(),
        "updated_at": d.get("processing_completed_at") or d.get("created_at") or datetime.utcnow().isoformat(),
        "page_count": int(d.get("total_pages") or 0),
        "document_type": d.get("source_type") or "unknown",
    }


def infer_document_language(filename: str = "", publication: str = "") -> Optional[str]:
    """Infer document language from filename or publication title."""
    combined = f"{filename} {publication}".lower()
    mapping = {
        "kannada": "kn", "prabha": "kn", "prajavani": "kn", "vijayavani": "kn",
        "eenadu": "te", "sakshi": "te", "andhra": "te", "telugu": "te",
        "thanthi": "ta", "dinamani": "ta", "dinamalar": "ta", "tamil": "ta",
        "jagran": "hi", "jansatta": "hi", "bhaskar": "hi", "amar_ujala": "hi", "navbharat": "hi", "hindi": "hi",
        "manorama": "ml", "madhyamam": "ml", "mathrubhumi": "ml", "malayalam": "ml",
        "anandabazar": "bn", "bengali": "bn", "bartaman": "bn",
        "loksatta": "mr", "marathi": "mr", "sakala": "mr",
        "sandesh": "gu", "gujarat": "gu",
        "telegraph": "en", "times_of_india": "en", "the_hindu": "en", "hindu": "en", "deccan": "en", "express": "en"
    }
    for key, lang in mapping.items():
        if key in combined:
            return lang
    return None


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    publication_id: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    source_region: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
):
    """Upload a newspaper PDF or image for processing."""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    # Validate file size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(400, f"File too large. Maximum: {settings.max_upload_size_mb}MB")

    # Generate safe filename
    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}{ext}"
    file_path = Path(settings.upload_path) / safe_filename

    # Save file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse optional fields
    pub_date = None
    if publication_date:
        try:
            pub_date = datetime.fromisoformat(publication_date)
        except ValueError:
            pass

    # Hash file for deduplication
    import hashlib
    file_hash = hashlib.sha256(content).hexdigest()

    excel = ExcelStorageService()
    existing_doc = excel.find_row("Documents", {"file_hash": file_hash})
    if existing_doc:
        if existing_doc.get("processing_status") in ("CANCELLED", "FAILED"):
            excel.update_row("Documents", {"document_id": existing_doc["document_id"]}, {
                "processing_status": "UPLOADED",
                "current_stage": "queued",
                "progress_percent": 0.0,
                "processing_error": None,
            })
            existing_doc["processing_status"] = "UPLOADED"
            existing_doc["current_stage"] = "queued"
            existing_doc["progress_percent"] = 0.0
            existing_doc["processing_error"] = None
        return _format_doc_response(existing_doc)

    resolved_lang = language or infer_document_language(file.filename or "", publication_id or "")

    # Create document record
    doc_dict = {
        "document_id": document_id,
        "file_name": file.filename,
        "file_hash": file_hash,
        "source_type": ext,
        "publication": publication_id,
        "edition": edition,
        "publication_date": pub_date.isoformat() if pub_date else None,
        "language": resolved_lang,
        "total_pages": 0,
        "processing_status": "UPLOADED",
        "current_stage": "queued",
        "progress_percent": 0.0,
        "overall_sentiment": None,
        "overall_risk_score": None,
        "processing_started_at": None,
        "processing_completed_at": None,
        "processing_error": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    excel.append_row("Documents", doc_dict)
    return _format_doc_response(doc_dict)


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List all documents with optional status filter."""
    excel = ExcelStorageService()
    docs = excel.find_rows("Documents", {})
    
    if status:
        stat_lower = status.lower()
        docs = [d for d in docs if (d.get("processing_status") or "").lower() == stat_lower]
        
    # Sort descending by created_at manually
    docs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    # Paginate
    paginated = docs[offset:offset+limit]
    
    return [_format_doc_response(d) for d in paginated]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str):
    """Get document detail with pages."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    pages = excel.find_rows("Pages", {"document_id": document_id})
    page_summaries = []
    for p in pages:
        articles = excel.find_rows("Articles", {"page_id": p["page_id"]})
        page_summaries.append({
            "id": p["page_id"],
            "page_number": p["page_number"],
            "image_path": p["image_path"],
            "has_text_layer": p.get("has_extractable_text", False),
            "article_count": len(articles)
        })

    resp = _format_doc_response(doc)
    resp["pages"] = page_summaries
    resp["publication_name"] = doc.get("publication")
    return resp


@router.post("/{document_id}/process", response_model=ProcessingJobResponse)
async def start_processing(document_id: str):
    """Queue document for AI processing pipeline."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.get("processing_status") == "PROCESSING":
        from workers.processor import _active_tasks
        active = _active_tasks.get(document_id)
        if active and not active.done():
            raise HTTPException(409, "Document is already being processed")

    excel.update_row("Documents", {"document_id": document_id}, {"processing_status": "QUEUED", "current_stage": "queued", "progress_percent": 0.0})

    # Trigger background processing (non-blocking)
    from workers.processor import process_document_task, register_task
    import asyncio
    job_id = str(uuid.uuid4())
    task = asyncio.create_task(process_document_task(document_id, job_id))
    register_task(document_id, task)

    return {
        "id": job_id,
        "document_id": document_id,
        "status": "queued",
        "current_stage": "queued",
        "progress_percent": 0.0,
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/{document_id}/jobs")
async def get_document_jobs(document_id: str):
    """Get processing jobs/progress for a document."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    status = (doc.get("processing_status") or "UPLOADED").lower()
    current_stage = (doc.get("current_stage") or "queued").lower()
    progress = float(doc.get("progress_percent") or 0.0)
    is_done = status == "completed"
    is_failed = status == "failed"

    def _stage(completed_above: float, running_keyword: str) -> str:
        """Return stage status string based on progress band and stage keyword."""
        if is_done:
            return "completed"
        if is_failed:
            return "failed"
        if progress >= completed_above:
            return "completed"
        if running_keyword and running_keyword in current_stage:
            return "running"
        return "pending"

    # Map the 3-phase progress bands to the 13 frontend stage keys.
    # Phase 1 OCR:        0%  → 30%
    # Phase 2 Translate:  30% → 65%
    # Phase 3 Sentiment:  65% → 95%
    # Finalise:           95% → 100%
    stages = {
        "upload":             "completed" if progress > 0 or is_done else "pending",
        "pdf_classification": "completed" if progress >= 2 or is_done else (
                              "running"   if "pdf_class" in current_stage or "classif" in current_stage else "pending"),
        "page_rendering":     "completed" if progress >= 2 or is_done else (
                              "running"   if "render" in current_stage or "phase 1" in current_stage else "pending"),
        "ocr":                _stage(30,  "ocr"),
        "layout_analysis":    _stage(35,  "layout"),
        "article_extraction": _stage(40,  "article"),
        "language_detection": _stage(45,  "language"),
        "translation":        _stage(65,  "translat"),
        "entity_detection":   _stage(72,  "entity"),
        "sentiment_analysis": _stage(82,  "sentiment"),
        "crisis_analysis":    _stage(88,  "crisis"),
        "alert_generation":   _stage(92,  "alert"),
        "evidence_indexed":   "completed" if is_done else (
                              "running"   if progress >= 95 else "pending"),
    }

    return [{
        "id": f"job-{document_id[:8]}",
        "document_id": document_id,
        "status": status,
        "current_stage": doc.get("current_stage") or "queued",
        "progress_percent": progress,
        "created_at": doc.get("created_at") or datetime.utcnow().isoformat(),
        "stages": stages,
    }]


@router.post("/{document_id}/cancel")
async def cancel_document(document_id: str):
    """Cancel processing for a document."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    
    from workers.processor import cancel_task
    cancel_task(document_id)

    excel.update_row("Documents", {"document_id": document_id}, {
        "processing_status": "CANCELLED",
        "current_stage": "cancelled"
    })
    return {"status": "cancelled", "document_id": document_id}


@router.get("/{document_id}/pages", response_model=List[PageSummary])
async def get_document_pages(document_id: str):
    """Get all pages for a document."""
    excel = ExcelStorageService()
    pages = excel.find_rows("Pages", {"document_id": document_id})
    pages.sort(key=lambda x: x.get("page_number", 0))
    
    result = []
    for p in pages:
        articles = excel.find_rows("Articles", {"page_id": p["page_id"]})
        result.append({
            "id": p["page_id"],
            "page_number": p["page_number"],
            "image_path": p["image_path"],
            "has_text_layer": p.get("has_extractable_text", False),
            "article_count": len(articles)
        })
    return result


@router.get("/{document_id}/pages/{page_number}/image")
async def get_page_image(document_id: str, page_number: int):
    """Get the image file for a specific page."""
    from fastapi.responses import FileResponse
    excel = ExcelStorageService()
    pages = excel.find_rows("Pages", {"document_id": document_id, "page_number": page_number})
    if not pages:
        raise HTTPException(404, "Page not found")
    page = pages[0]
    
    if not page.get("image_path") or not Path(page["image_path"]).exists():
        raise HTTPException(404, "Page image not found")
    return FileResponse(page["image_path"])


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete document and related data from storage."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    
    excel.delete_rows("Documents", {"document_id": document_id})
    excel.delete_rows("Pages", {"document_id": document_id})
    excel.delete_rows("Articles", {"document_id": document_id})
    excel.delete_rows("Alerts", {"document_id": document_id})
    excel.delete_rows("AuditLogs", {"document_id": document_id})
    return {"status": "deleted", "document_id": document_id}
