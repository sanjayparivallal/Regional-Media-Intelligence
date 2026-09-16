"""
Publication ORM model.

Newspaper/publication configuration with region, language, and reach tier.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Publication(Base):
    """Newspaper/publication configuration."""
    __tablename__ = "publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False, unique=True)
    display_name = Column(String(300))
    language = Column(String(50))
    region = Column(String(200))
    state = Column(String(200))
    country = Column(String(100), default="India")

    # Reach
    reach_tier = Column(Integer, default=2)  # 1=national/high, 2=regional/high, 3=regional/local
    estimated_circulation = Column(Integer)
    reach_score = Column(Float, default=0.5)  # 0-1 normalized reach

    # Configuration
    default_ocr_language = Column(String(20))
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="publication")

    __table_args__ = (
        Index("idx_publications_name", "name"),
        Index("idx_publications_language", "language"),
        Index("idx_publications_region", "region"),
    )
