"""
Document-related ORM models.

Maintains the chain: Document → Page → Article
Every article retains bounding box coordinates for evidence tracing.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DocumentType(str, enum.Enum):
    PDF_SCANNED = "pdf_scanned"
    PDF_TEXT = "pdf_text"
    PDF_MIXED = "pdf_mixed"
    IMAGE = "image"


class Document(Base):
    """Uploaded newspaper document (PDF or image)."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    document_type = Column(SAEnum(DocumentType))
    page_count = Column(Integer, default=0)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.UPLOADED)
    error_message = Column(Text)

    # Metadata
    publication_id = Column(UUID(as_uuid=True), ForeignKey("publications.id"), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    edition = Column(String(200))
    source_region = Column(String(200))

    # Processing
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    processing_duration_ms = Column(Integer)

    # Demo flag
    is_demo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    publication = relationship("Publication", back_populates="documents")
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_created", "created_at"),
        Index("idx_documents_publication", "publication_id"),
    )


class Page(Base):
    """Single page of a document. Stores rendered image and OCR results."""
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)

    # Image
    image_path = Column(String(1000))
    thumbnail_path = Column(String(1000))
    width = Column(Integer)
    height = Column(Integer)
    dpi = Column(Integer, default=300)

    # OCR
    has_text_layer = Column(Boolean, default=False)
    ocr_engine_used = Column(String(100))
    ocr_language = Column(String(50))
    ocr_raw_text = Column(Text)
    ocr_confidence = Column(Float, default=0.0)
    ocr_word_count = Column(Integer, default=0)
    ocr_bounding_boxes = Column(JSON)  # List of {x, y, w, h, text, confidence}
    preprocessing_applied = Column(String(200))

    # Layout
    detected_columns = Column(Integer)
    layout_regions = Column(JSON)  # List of detected regions with types

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="pages")
    articles = relationship("Article", back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_pages_document", "document_id"),
    )


class Article(Base):
    """Extracted article with bounding box for evidence viewer highlighting."""
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Content
    headline = Column(Text)
    body_text = Column(Text)
    full_text = Column(Text)  # headline + body combined
    word_count = Column(Integer, default=0)

    # Bounding box on the original page (for evidence highlighting)
    bbox_x = Column(Float)
    bbox_y = Column(Float)
    bbox_width = Column(Float)
    bbox_height = Column(Float)
    bounding_boxes = Column(JSON)  # All constituent OCR boxes

    # Classification
    article_type = Column(String(50))  # news, advertisement, editorial, etc.
    is_advertisement = Column(Boolean, default=False)

    # Language
    detected_language = Column(String(20))
    language_confidence = Column(Float)
    detected_script = Column(String(50))

    # Quality
    ocr_confidence = Column(Float)
    segmentation_confidence = Column(Float)
    segmentation_strategy = Column(String(100))

    # Processing
    needs_review = Column(Boolean, default=False)
    review_reason = Column(String(200))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    page = relationship("Page", back_populates="articles")
    translations = relationship("Translation", back_populates="article", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="article", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="article", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_articles_page", "page_id"),
        Index("idx_articles_document", "document_id"),
        Index("idx_articles_language", "detected_language"),
    )


class ProcessingJob(Base):
    """Tracks background processing pipeline state for a document."""
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    status = Column(String(50), default="queued")  # queued, running, completed, failed
    current_stage = Column(String(100))
    progress_percent = Column(Float, default=0.0)
    error_message = Column(Text)

    # Per-stage status tracking
    stages = Column(JSON, default=lambda: {
        "upload": "pending",
        "pdf_classification": "pending",
        "page_rendering": "pending",
        "ocr": "pending",
        "layout_analysis": "pending",
        "article_extraction": "pending",
        "language_detection": "pending",
        "translation": "pending",
        "entity_detection": "pending",
        "sentiment_analysis": "pending",
        "crisis_analysis": "pending",
        "alert_generation": "pending",
        "evidence_indexed": "pending",
    })

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Model choices (audit trail for which models were used)
    model_selections = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="processing_jobs")

    __table_args__ = (
        Index("idx_jobs_document", "document_id"),
        Index("idx_jobs_status", "status"),
    )
