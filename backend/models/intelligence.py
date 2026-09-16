"""
Intelligence-related ORM models.

Translation, Entity, Mention, Alert, Incident — the analysis outputs.
Every record maintains foreign keys back to the source article/page/document.
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


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AlertPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Translation(Base):
    """Translation of an article with confidence tracking."""
    __tablename__ = "translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)

    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), default="en")
    source_text = Column(Text)
    translated_text = Column(Text)
    confidence = Column(Float)

    # Model used
    model_used = Column(String(200))
    translation_time_ms = Column(Integer)

    # Entity preservation
    entities_protected = Column(JSON)  # Entities that were preserved during translation

    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    corrected_text = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="translations")

    __table_args__ = (
        Index("idx_translations_article", "article_id"),
    )


class Entity(Base):
    """Named entity extracted from an article."""
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)

    text = Column(String(500), nullable=False)
    entity_type = Column(String(100))  # ORGANIZATION, PERSON, LOCATION, PRODUCT, etc.
    confidence = Column(Float)

    # Position in text
    start_offset = Column(Integer)
    end_offset = Column(Integer)

    # Source
    detected_in = Column(String(50))  # original, translated
    model_used = Column(String(200))

    # Normalization
    normalized_text = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="entities")

    __table_args__ = (
        Index("idx_entities_article", "article_id"),
        Index("idx_entities_type", "entity_type"),
    )


class Mention(Base):
    """Brand mention detected in an article."""
    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)

    matched_text = Column(String(500))
    match_type = Column(String(50))  # exact, alias, fuzzy, context
    match_confidence = Column(Float)
    context_snippet = Column(Text)  # Surrounding text for evidence

    # Sentiment for this specific mention
    sentiment = Column(SAEnum(SentimentLabel))
    sentiment_confidence = Column(Float)
    sentiment_model_used = Column(String(200))

    # Crisis classification
    crisis_topic = Column(String(200))
    crisis_confidence = Column(Float)

    # Risk scoring
    risk_score = Column(Float)
    risk_breakdown = Column(JSON)  # {sentiment, brand, topic, reach, confidence}
    risk_priority = Column(SAEnum(AlertPriority))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="mentions")
    brand = relationship("Brand", back_populates="mentions")

    __table_args__ = (
        Index("idx_mentions_article", "article_id"),
        Index("idx_mentions_brand", "brand_id"),
        Index("idx_mentions_risk", "risk_score"),
    )


class Alert(Base):
    """Generated alert for a brand mention requiring attention."""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    mention_id = Column(UUID(as_uuid=True), ForeignKey("mentions.id", ondelete="CASCADE"), nullable=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True)

    # Alert details
    title = Column(String(500))
    summary = Column(Text)
    priority = Column(SAEnum(AlertPriority), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_breakdown = Column(JSON)

    # Context
    publication_name = Column(String(200))
    page_number = Column(Integer)
    language = Column(String(20))
    region = Column(String(200))

    # Sentiment
    sentiment = Column(SAEnum(SentimentLabel))
    sentiment_confidence = Column(Float)

    # Crisis
    crisis_topic = Column(String(200))
    crisis_keywords = Column(JSON)

    # Status
    status = Column(String(50), default="active")  # active, reviewed, dismissed, escalated
    reviewed_by = Column(String(200))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Deduplication
    fingerprint = Column(String(200))
    is_duplicate = Column(Boolean, default=False)

    # Demo
    is_demo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="alerts")
    brand = relationship("Brand", back_populates="alerts")
    incident = relationship("Incident", back_populates="alerts")

    __table_args__ = (
        Index("idx_alerts_brand", "brand_id"),
        Index("idx_alerts_priority", "priority"),
        Index("idx_alerts_risk", "risk_score"),
        Index("idx_alerts_created", "created_at"),
        Index("idx_alerts_status", "status"),
    )


class Incident(Base):
    """Grouped/deduplicated alerts representing a single story/event."""
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500))
    summary = Column(Text)
    priority = Column(SAEnum(AlertPriority))
    max_risk_score = Column(Float)

    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    alert_count = Column(Integer, default=1)

    status = Column(String(50), default="active")
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="incident")
    brand = relationship("Brand")

    __table_args__ = (
        Index("idx_incidents_priority", "priority"),
        Index("idx_incidents_brand", "brand_id"),
    )
