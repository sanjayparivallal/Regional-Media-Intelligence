"""
Alert API endpoints.

GET /alerts            — List alerts with filters
GET /alerts/{id}       — Alert detail
GET /alerts/{id}/evidence — Evidence chain viewer data
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from database import get_db
from models.intelligence import Alert, Mention, Translation, Entity, Incident
from models.document import Article, Page, Document
from models.brand import Brand
from models.review import AuditLog
from schemas.intelligence import (
    AlertResponse, AlertDetail, AlertEvidenceResponse,
    ArticleSummaryForEvidence, PageEvidenceInfo, DocumentEvidenceInfo,
    IncidentResponse, AuditLogResponse,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    brand_id: Optional[uuid.UUID] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with filters, sorted by risk score (highest first)."""
    query = (
        select(Alert)
        .options(selectinload(Alert.brand), selectinload(Alert.article))
        .order_by(desc(Alert.risk_score))
    )

    if brand_id:
        query = query.where(Alert.brand_id == brand_id)
    if priority:
        query = query.where(Alert.priority == priority)
    if status:
        query = query.where(Alert.status == status)
    if language:
        query = query.where(Alert.language == language)
    if sentiment:
        query = query.where(Alert.sentiment == sentiment)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    alerts = result.scalars().all()

    responses = []
    for alert in alerts:
        resp = AlertResponse.model_validate(alert)
        if alert.brand:
            resp.brand_name = alert.brand.display_name or alert.brand.name
        if alert.article:
            resp.document_id = alert.article.document_id
        responses.append(resp)

    return responses


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get alert detail."""
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.brand))
        .where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")

    resp = AlertDetail.model_validate(alert)
    if alert.brand:
        resp.brand_name = alert.brand.display_name or alert.brand.name
    return resp


@router.get("/{alert_id}/evidence", response_model=AlertEvidenceResponse)
async def get_alert_evidence(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get full evidence chain for an alert — traces back to original newspaper page."""
    # Fetch alert
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.brand))
        .where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")

    # Fetch article
    result = await db.execute(
        select(Article)
        .options(
            selectinload(Article.translations),
            selectinload(Article.entities),
        )
        .where(Article.id == alert.article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    # Fetch page
    result = await db.execute(select(Page).where(Page.id == article.page_id))
    page = result.scalar_one_or_none()

    # Fetch document
    result = await db.execute(select(Document).where(Document.id == article.document_id))
    document = result.scalar_one_or_none()

    # Fetch audit trail
    result = await db.execute(
        select(AuditLog)
        .where(
            (AuditLog.article_id == article.id) |
            (AuditLog.alert_id == alert_id) |
            (AuditLog.document_id == article.document_id)
        )
        .order_by(AuditLog.created_at)
    )
    audit_logs = result.scalars().all()

    return AlertEvidenceResponse(
        alert=AlertResponse.model_validate(alert),
        article=ArticleSummaryForEvidence.model_validate(article),
        page=PageEvidenceInfo.model_validate(page) if page else None,
        document=DocumentEvidenceInfo.model_validate(document) if document else None,
        translations=[
            {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            for t in (article.translations or [])
        ],
        entities=[
            {k: v for k, v in e.__dict__.items() if not k.startswith("_")}
            for e in (article.entities or [])
        ],
        audit_trail=[AuditLogResponse.model_validate(log) for log in audit_logs],
    )
