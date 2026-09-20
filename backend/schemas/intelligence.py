"""
Intelligence-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: UUID
    article_id: UUID
    brand_id: Optional[UUID] = None
    incident_id: Optional[UUID] = None

    title: Optional[str] = None
    summary: Optional[str] = None
    priority: str = "LOW"
    risk_score: float = 0.0
    risk_breakdown: Optional[dict] = None

    publication_name: Optional[str] = None
    page_number: Optional[int] = None
    language: Optional[str] = None
    region: Optional[str] = None

    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    crisis_topic: Optional[str] = None

    status: str = "active"
    is_duplicate: bool = False
    is_demo: bool = False

    # Joined data
    brand_name: Optional[str] = None
    document_id: Optional[UUID] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertDetail(AlertResponse):
    crisis_keywords: Optional[list] = None
    fingerprint: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    mention_id: Optional[UUID] = None


class AlertEvidenceResponse(BaseModel):
    """Evidence chain for an alert — links back to original newspaper page."""
    alert: AlertResponse
    article: "ArticleSummaryForEvidence"
    page: "PageEvidenceInfo"
    document: "DocumentEvidenceInfo"
    translations: list = []
    entities: list = []
    audit_trail: list = []


class ArticleSummaryForEvidence(BaseModel):
    id: UUID
    headline: Optional[str] = None
    body_text: Optional[str] = None
    full_text: Optional[str] = None
    word_count: Optional[int] = 0
    detected_language: Optional[str] = None
    ocr_confidence: Optional[float] = None
    bbox_x: Optional[float] = None
    bbox_y: Optional[float] = None
    bbox_width: Optional[float] = None
    bbox_height: Optional[float] = None
    bounding_boxes: Optional[list] = None

    class Config:
        from_attributes = True


class PageEvidenceInfo(BaseModel):
    id: UUID
    page_number: int = 1
    image_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    ocr_confidence: Optional[float] = 0.0
    ocr_engine_used: Optional[str] = None
    has_text_layer: Optional[bool] = False

    class Config:
        from_attributes = True


class DocumentEvidenceInfo(BaseModel):
    id: UUID
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    document_type: Optional[str] = None
    publication_id: Optional[UUID] = None
    publication_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    summary: Optional[str] = None
    priority: Optional[str] = None
    max_risk_score: Optional[float] = None
    brand_id: Optional[UUID] = None
    alert_count: int = 1
    status: str = "active"
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: UUID
    article_id: Optional[UUID] = None
    alert_id: Optional[UUID] = None
    review_type: Optional[str] = None
    reason: Optional[str] = None
    priority: str = "normal"
    ai_output: Optional[dict] = None
    confidence: Optional[float] = None
    status: str = "pending"
    reviewer: Optional[str] = None
    correction: Optional[dict] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewUpdate(BaseModel):
    status: str  # approved, corrected, rejected
    reviewer: Optional[str] = "analyst"
    correction: Optional[dict] = None
    review_notes: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: UUID
    document_id: Optional[UUID] = None
    article_id: Optional[UUID] = None
    alert_id: Optional[UUID] = None
    action: str
    stage: Optional[str] = None
    actor: str = "system"
    details: Optional[dict] = None
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
