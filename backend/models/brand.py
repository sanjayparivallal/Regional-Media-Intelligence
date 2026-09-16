"""
Brand-related ORM models.

Configurable brand monitoring with aliases for matching.
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


class Brand(Base):
    """Monitored brand entity."""
    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False, unique=True)
    display_name = Column(String(300))
    industry = Column(String(200))
    description = Column(Text)
    active = Column(Boolean, default=True)

    # Matching configuration
    keywords = Column(JSON, default=list)  # Additional keywords for context matching
    fuzzy_threshold = Column(Float, default=0.85)  # Minimum fuzzy match score

    # Statistics (denormalized for dashboard performance)
    total_mentions = Column(Integer, default=0)
    critical_alerts = Column(Integer, default=0)
    last_mention_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    aliases = relationship("BrandAlias", back_populates="brand", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="brand")
    alerts = relationship("Alert", back_populates="brand")

    __table_args__ = (
        Index("idx_brands_name", "name"),
        Index("idx_brands_active", "active"),
    )


class BrandAlias(Base):
    """Alternative name/spelling for a brand."""
    __tablename__ = "brand_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    alias = Column(String(300), nullable=False)
    alias_type = Column(String(50), default="name")  # name, abbreviation, misspelling, regional

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="aliases")

    __table_args__ = (
        Index("idx_aliases_brand", "brand_id"),
        Index("idx_aliases_alias", "alias"),
    )
