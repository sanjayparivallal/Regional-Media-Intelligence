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


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    publication_id: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    source_region: Optional[str] = Form(None),
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
        return _format_doc_response(existing_doc)

    # Create document record
    doc_dict = {
        "document_id": document_id,
        "file_name": file.filename,
        "file_hash": file_hash,
        "source_type": ext,
        "publication": publication_id,
        "edition": edition,
        "publication_date": pub_date.isoformat() if pub_date else None,
        "language": None,
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
        raise HTTPException(409, "Document is already being processed")

    excel.update_row("Documents", {"document_id": document_id}, {"processing_status": "QUEUED", "current_stage": "queued", "progress_percent": 0.0})

    # Trigger background processing (non-blocking)
    from workers.processor import process_document_task
    import asyncio
    job_id = str(uuid.uuid4())
    asyncio.create_task(process_document_task(document_id, job_id))

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
    current_stage = doc.get("current_stage") or "queued"
    progress = float(doc.get("progress_percent") or 0.0)
    
    return [{
        "id": f"job-{document_id[:8]}",
        "document_id": document_id,
        "status": status,
        "current_stage": current_stage,
        "progress_percent": progress,
        "created_at": doc.get("created_at") or datetime.utcnow().isoformat(),
        "stages": {
            "extracting_text": {"status": "completed" if progress >= 30 else ("running" if "extracting" in current_stage or "ocr" in current_stage.lower() else "pending")},
            "segmenting": {"status": "completed" if progress >= 50 else ("running" if "segmenting" in current_stage else "pending")},
            "translating": {"status": "completed" if progress >= 70 else ("running" if "translating" in current_stage or "translation" in current_stage.lower() else "pending")},
            "analyzing": {"status": "completed" if progress >= 90 else ("running" if "analyzing" in current_stage or "sentiment" in current_stage.lower() else "pending")}
        }
    }]


@router.post("/{document_id}/cancel")
async def cancel_document(document_id: str):
    """Cancel processing for a document."""
    excel = ExcelStorageService()
    doc = excel.find_row("Documents", {"document_id": document_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    
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
