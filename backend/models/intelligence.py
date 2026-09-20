import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import enum

class Translation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    source_language: str
    source_text: str
    translated_text: str
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    entities_protected: bool = False
    needs_review: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    text: str
    type: str
    normalized_name: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    confidence: Optional[float] = None
    is_monitored_brand: bool = False
    verification_status: str = "unverified"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Mention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    brand_id: str
    brand_name: str
    matched_text: str
    match_type: str
    confidence: Optional[float] = None
    context_snippet: Optional[str] = None
    verified_by_lfm: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class AlertPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AIAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    brand_id: Optional[str] = None
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_confidence: Optional[float] = None
    sentiment_reasoning: Optional[str] = None
    crisis_detected: bool = False
    crisis_category: Optional[str] = None
    crisis_severity: Optional[float] = None
    crisis_reasoning: Optional[str] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None
    model_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    brand_id: Optional[str] = None
    document_id: str
    priority: AlertPriority
    crisis_score: float
    sentiment: SentimentLabel
    category: Optional[str] = None
    summary: str
    status: str = "new"
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
