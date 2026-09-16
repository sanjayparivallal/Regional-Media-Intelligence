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
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from sqlalchemy.orm import selectinload

from database import get_db
from config import get_settings
from models.document import Document, Page, Article, ProcessingJob, DocumentStatus
from models.intelligence import Alert, Mention, Translation, Entity
from models.review import Review, AuditLog
from schemas.document import DocumentResponse, DocumentDetail, PageSummary, ProcessingJobResponse

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
ALLOWED_MIME_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/tiff",
    "image/jpg",
}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    publication_id: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    source_region: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
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
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = Path(settings.upload_path) / safe_filename

    # Save file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse optional fields
    pub_id = uuid.UUID(publication_id) if publication_id else None
    pub_date = None
    if publication_date:
        try:
            pub_date = datetime.fromisoformat(publication_date)
        except ValueError:
            pass

    # Create document record
    doc = Document(
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.UPLOADED,
        publication_id=pub_id,
        publication_date=pub_date,
        edition=edition,
        source_region=source_region,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with optional status filter."""
    query = select(Document).order_by(desc(Document.created_at))
    if status:
        query = query.where(Document.status == status)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get document detail with pages."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.pages), selectinload(Document.publication))
        .where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    detail = DocumentDetail.model_validate(doc)
    if doc.publication:
        detail.publication_name = doc.publication.display_name or doc.publication.name
    # Add article counts to pages
    for page_schema in detail.pages:
        page_obj = next((p for p in doc.pages if p.id == page_schema.id), None)
        if page_obj:
            count_result = await db.execute(
                select(func.count()).select_from(
                    select(Page).where(Page.id == page_obj.id).subquery()
                )
            )
    return detail


@router.post("/{document_id}/process", response_model=ProcessingJobResponse)
async def start_processing(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Queue document for AI processing pipeline."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.status == DocumentStatus.PROCESSING:
        raise HTTPException(409, "Document is already being processed")

    # Create processing job
    job = ProcessingJob(
        document_id=document_id,
        status="queued",
        current_stage="queued",
    )
    doc.status = DocumentStatus.QUEUED
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Trigger background processing (non-blocking)
    from workers.processor import process_document_task
    import asyncio
    asyncio.create_task(process_document_task(str(document_id), str(job.id)))

    return job


@router.get("/{document_id}/pages", response_model=list[PageSummary])
async def get_document_pages(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get all pages for a document."""
    result = await db.execute(
        select(Page)
        .where(Page.document_id == document_id)
        .order_by(Page.page_number)
    )
    return result.scalars().all()


@router.get("/{document_id}/jobs", response_model=list[ProcessingJobResponse])
async def get_document_jobs(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get processing jobs for a document."""
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(desc(ProcessingJob.created_at))
    )
    return result.scalars().all()


@router.post("/{document_id}/cancel")
async def cancel_processing(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel an in-progress or queued processing job."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.status not in (DocumentStatus.QUEUED, DocumentStatus.PROCESSING):
        raise HTTPException(409, f"Cannot cancel document with status '{doc.status}'")

    # Mark document as failed/cancelled
    from models.document import DocumentStatus as DS
    doc.status = DS.FAILED
    doc.error_message = "Cancelled by user"

    # Mark latest running job as failed
    job_result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(desc(ProcessingJob.created_at))
    )
    job = job_result.scalar_one_or_none()
    if job and job.status in ("queued", "running"):
        job.status = "failed"
        job.error_message = "Cancelled by user"

    await db.commit()
    return {"status": "cancelled", "document_id": str(document_id)}


@router.delete("/{document_id}")
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its associated data."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Clean up page images and thumbnails from disk
    pages_result = await db.execute(select(Page).where(Page.document_id == document_id))
    pages = pages_result.scalars().all()
    for p in pages:
        for img_path in (p.image_path, p.thumbnail_path):
            if img_path:
                try:
                    Path(img_path).unlink(missing_ok=True)
                except Exception:
                    pass

    # Delete the physical document file if it exists
    try:
        file_path = Path(doc.file_path)
        file_path.unlink(missing_ok=True)
    except Exception:
        pass

    # Find all articles for this document to delete their dependents
    articles_result = await db.execute(select(Article.id).where(Article.document_id == document_id))
    article_ids = articles_result.scalars().all()

    # Delete audit logs for this document
    await db.execute(delete(AuditLog).where(AuditLog.document_id == document_id))

    if article_ids:
        # Alerts referencing these articles
        alerts_result = await db.execute(select(Alert.id).where(Alert.article_id.in_(article_ids)))
        alert_ids = alerts_result.scalars().all()

        if alert_ids:
            await db.execute(delete(AuditLog).where(AuditLog.alert_id.in_(alert_ids)))
            await db.execute(delete(Review).where(Review.alert_id.in_(alert_ids)))
            await db.execute(delete(Alert).where(Alert.id.in_(alert_ids)))

        await db.execute(delete(AuditLog).where(AuditLog.article_id.in_(article_ids)))
        await db.execute(delete(Review).where(Review.article_id.in_(article_ids)))
        await db.execute(delete(Mention).where(Mention.article_id.in_(article_ids)))
        await db.execute(delete(Entity).where(Entity.article_id.in_(article_ids)))
        await db.execute(delete(Translation).where(Translation.article_id.in_(article_ids)))
        await db.execute(delete(Article).where(Article.id.in_(article_ids)))

    # Delete processing jobs and pages
    await db.execute(delete(ProcessingJob).where(ProcessingJob.document_id == document_id))
    await db.execute(delete(Page).where(Page.document_id == document_id))

    # Delete the document record
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted", "document_id": str(document_id)}

