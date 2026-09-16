"""
Review and Audit ORM models.

Human review queue and complete audit trail for every AI decision.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime,
    ForeignKey, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Review(Base):
    """Human review queue item. Created when AI confidence is low."""
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
 
    review_type = Column(String(100))  # ocr, translation, segmentation, sentiment, entity, crisis
    reason = Column(Text)
    priority = Column(String(50), default="normal")  # low, normal, high, urgent

    # Current AI output for review
    ai_output = Column(JSON)
    confidence = Column(Float)

    # Review result
    status = Column(String(50), default="pending")  # pending, approved, corrected, rejected
    reviewer = Column(String(200))
    correction = Column(JSON)
    review_notes = Column(Text)
    reviewed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    article = relationship("Article")
    alert = relationship("Alert")

    __table_args__ = (
        Index("idx_reviews_status", "status"),
        Index("idx_reviews_type", "review_type"),
        Index("idx_reviews_priority", "priority"),
    )


class AuditLog(Base):
    """Complete audit trail for every AI decision and human action."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)

    # Action
    action = Column(String(200), nullable=False)
    stage = Column(String(100))  # Pipeline stage
    actor = Column(String(200), default="system")  # system, model_name, reviewer_name

    # Details
    details = Column(JSON)
    input_data = Column(JSON)
    output_data = Column(JSON)
    confidence = Column(Float)
    model_used = Column(String(200))

    # Timing
    processing_time_ms = Column(Integer)

    # Outcome
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_document", "document_id"),
        Index("idx_audit_article", "article_id"),
        Index("idx_audit_stage", "stage"),
        Index("idx_audit_created", "created_at"),
    )
