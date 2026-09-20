"""
Document-related Pydantic schemas for API request/response.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class PageSummary(BaseModel):
    id: UUID
    page_number: int
    width: Optional[int] = None
    height: Optional[int] = None
    ocr_confidence: float = 0.0
    ocr_word_count: int = 0
    ocr_engine_used: Optional[str] = None
    detected_columns: Optional[int] = None
    image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    has_text_layer: bool = False
    article_count: int = 0

    class Config:
        from_attributes = True


class ArticleSummary(BaseModel):
    id: UUID
    page_id: UUID
    document_id: UUID
    headline: Optional[str] = None
    body_text: Optional[str] = None
    word_count: int = 0
    detected_language: Optional[str] = None
    language_confidence: Optional[float] = None
    ocr_confidence: Optional[float] = None
    article_type: Optional[str] = None
    is_advertisement: bool = False
    needs_review: bool = False
    review_reason: Optional[str] = None

    # Bounding box
    bbox_x: Optional[float] = None
    bbox_y: Optional[float] = None
    bbox_width: Optional[float] = None
    bbox_height: Optional[float] = None

    # Page info
    page_number: int = 0

    class Config:
        from_attributes = True


class ArticleDetail(ArticleSummary):
    full_text: Optional[str] = None
    bounding_boxes: Optional[list] = None
    segmentation_confidence: Optional[float] = None
    segmentation_strategy: Optional[str] = None
    detected_script: Optional[str] = None
    created_at: datetime

    # Nested
    translations: List["TranslationResponse"] = []
    entities: List["EntityResponse"] = []
    mentions: List["MentionResponse"] = []

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    publication_id: Optional[UUID] = None
    publication_date: Optional[datetime] = None
    edition: Optional[str] = None
    source_region: Optional[str] = None


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    document_type: Optional[str] = None
    page_count: int = 0
    status: str
    error_message: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percent: float = 0.0
    overall_sentiment: Optional[str] = None
    overall_risk_score: Optional[float] = None

    publication_id: Optional[UUID] = None
    publication_date: Optional[datetime] = None
    source_region: Optional[str] = None

    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None

    is_demo: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetail(DocumentResponse):
    pages: List[PageSummary] = []
    publication_name: Optional[str] = None


class ProcessingJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    current_stage: Optional[str] = None
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    stages: dict = {}
    model_selections: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Forward refs for ArticleDetail
class TranslationResponse(BaseModel):
    id: UUID
    source_language: str
    target_language: str = "en"
    source_text: Optional[str] = None
    translated_text: Optional[str] = None
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    needs_review: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class EntityResponse(BaseModel):
    id: UUID
    text: str
    entity_type: Optional[str] = None
    confidence: Optional[float] = None
    detected_in: Optional[str] = None
    normalized_text: Optional[str] = None

    class Config:
        from_attributes = True


class MentionResponse(BaseModel):
    id: UUID
    brand_id: UUID
    brand_name: Optional[str] = None
    matched_text: Optional[str] = None
    match_type: Optional[str] = None
    match_confidence: Optional[float] = None
    context_snippet: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    crisis_topic: Optional[str] = None
    risk_score: Optional[float] = None
    risk_breakdown: Optional[dict] = None
    risk_priority: Optional[str] = None

    class Config:
        from_attributes = True


# Resolve forward references
ArticleDetail.model_rebuild()
