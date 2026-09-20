"""
Alert API endpoints.

GET /alerts            — List alerts with filters
GET /alerts/{id}       — Alert detail
GET /alerts/{id}/evidence — Evidence chain viewer data
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query

from storage.excel_storage_service import ExcelStorageService
from schemas.intelligence import (
    AlertResponse, AlertDetail, AlertEvidenceResponse,
    ArticleSummaryForEvidence, PageEvidenceInfo, DocumentEvidenceInfo,
    AuditLogResponse,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _build_risk_breakdown(risk_score: float) -> dict:
    return {
        "volume": round(risk_score * 0.2, 1),
        "sentiment": round(risk_score * 0.35, 1),
        "reach": round(risk_score * 0.25, 1),
        "severity": round(risk_score * 0.2, 1)
    }


def _format_alert(alert: dict) -> dict:
    risk_score = float(alert.get("crisis_score") or 0.0)
    severity = str(alert.get("severity") or "LOW").lower()
    return {
        "id": alert["alert_id"],
        "article_id": alert["article_id"],
        "document_id": alert.get("document_id"),
        "title": alert.get("headline", ""),
        "summary": alert.get("summary", ""),
        "priority": severity,
        "risk_score": risk_score,
        "risk_breakdown": _build_risk_breakdown(risk_score),
        "publication_name": alert.get("publication", ""),
        "page_number": int(alert.get("page_number") or 1),
        "language": alert.get("language", ""),
        "sentiment": alert.get("sentiment", "NEUTRAL"),
        "crisis_topic": alert.get("crisis_category", "NONE"),
        "status": alert.get("alert_status", "active"),
        "brand_name": alert.get("brand_name", ""),
        "created_at": alert.get("created_at") or datetime.utcnow().isoformat(),
        "updated_at": alert.get("created_at") or datetime.utcnow().isoformat(),
    }


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    brand_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List alerts with filters, sorted by risk score (highest first)."""
    excel = ExcelStorageService()
    query = {}
    if status:
        query["alert_status"] = status
    if language:
        query["language"] = language
    if sentiment:
        query["sentiment"] = sentiment
    
    alerts = excel.find_rows("Alerts", query)
    
    # In-memory filtering for more complex criteria
    filtered_alerts = []
    for a in alerts:
        if priority:
            a_sev = str(a.get("severity") or "").lower()
            if a_sev != priority.lower():
                continue
        if brand_id and str(a.get("brand_id") or "") != brand_id and str(a.get("brand_name") or "") != brand_id:
            continue
        filtered_alerts.append(a)

    # Sort by crisis_score desc
    filtered_alerts.sort(key=lambda x: float(x.get("crisis_score") or 0), reverse=True)
    
    paginated = filtered_alerts[offset:offset+limit]

    return [_format_alert(alert) for alert in paginated]


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: str):
    """Get alert detail."""
    excel = ExcelStorageService()
    alert = excel.find_row("Alerts", {"alert_id": alert_id})
    if not alert:
        raise HTTPException(404, "Alert not found")

    return _format_alert(alert)


@router.get("/{alert_id}/evidence", response_model=AlertEvidenceResponse)
async def get_alert_evidence(alert_id: str):
    """Get full evidence chain for an alert — traces back to original newspaper page."""
    excel = ExcelStorageService()
    alert = excel.find_row("Alerts", {"alert_id": alert_id})
    if not alert:
        raise HTTPException(404, "Alert not found")

    article_id = alert["article_id"]
    article = excel.find_row("Articles", {"article_id": article_id})
    if not article:
        raise HTTPException(404, "Article not found")

    page = excel.find_row("Pages", {"page_id": article.get("page_id")}) if article.get("page_id") else None
    document = excel.find_row("Documents", {"document_id": article.get("document_id")}) if article.get("document_id") else None

    translations = excel.find_rows("Translations", {"article_id": article_id})
    entities = excel.find_rows("Entities", {"article_id": article_id})
    
    # Audit logs
    audit_logs = []
    all_logs = excel.find_rows("AuditLogs", {})
    for log in all_logs:
        if log.get("article_id") == article_id or (article.get("document_id") and log.get("document_id") == article["document_id"]):
            audit_logs.append(log)

    formatted_alert = _format_alert(alert)

    article_summary = {
        "id": article["article_id"],
        "headline": article.get("headline", ""),
        "body_text": article.get("original_text", ""),
        "full_text": article.get("original_text", ""),
        "word_count": int(article.get("word_count") or len((article.get("original_text") or "").split())),
        "detected_language": article.get("language", ""),
        "ocr_confidence": float(article.get("ocr_confidence") or 0.85),
        "bbox_x": float(article["x1"]) if article.get("x1") is not None else 0.0,
        "bbox_y": float(article["y1"]) if article.get("y1") is not None else 0.0,
        "bbox_width": float(article["x2"] - article["x1"]) if article.get("x2") is not None and article.get("x1") is not None else 100.0,
        "bbox_height": float(article["y2"] - article["y1"]) if article.get("y2") is not None and article.get("y1") is not None else 100.0,
    }

    page_info = {
        "id": page["page_id"],
        "page_number": int(page.get("page_number") or 1),
        "image_path": page.get("image_path", ""),
        "width": int(page.get("page_width") or 1000),
        "height": int(page.get("page_height") or 1400),
        "has_text_layer": bool(page.get("has_extractable_text", False)),
        "ocr_confidence": float(page.get("ocr_confidence") or 0.85),
    } if page else {
        "id": str(uuid.uuid4()),
        "page_number": 1,
        "image_path": "",
        "width": 1000,
        "height": 1400,
        "has_text_layer": False,
        "ocr_confidence": 0.85
    }

    doc_info = {
        "id": document["document_id"],
        "filename": document.get("file_name", "Document"),
        "original_filename": document.get("file_name", "Document"),
        "document_type": document.get("source_type", "pdf")
    } if document else {
        "id": alert.get("document_id") or str(uuid.uuid4()),
        "filename": "Document",
        "original_filename": "Document",
        "document_type": "pdf"
    }

    return {
        "alert": formatted_alert,
        "article": article_summary,
        "page": page_info,
        "document": doc_info,
        "translations": translations,
        "entities": entities,
        "audit_trail": audit_logs
    }
