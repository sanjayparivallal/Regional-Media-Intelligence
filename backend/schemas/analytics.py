"""
Analytics Pydantic schemas for dashboard data.
"""

from datetime import datetime
from typing import Optional, List, Union
from uuid import UUID
from pydantic import BaseModel


class OverviewStats(BaseModel):
    documents_processed: int = 0
    pages_processed: int = 0
    articles_detected: int = 0
    brand_mentions: int = 0
    critical_alerts: int = 0
    high_alerts: int = 0
    pending_reviews: int = 0
    active_brands: int = 0


class LanguageCoverage(BaseModel):
    language: str
    count: int
    percentage: float


class PublicationCoverage(BaseModel):
    publication: str
    count: int
    region: Optional[str] = None


class SentimentDistribution(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class CrisisTopicDistribution(BaseModel):
    topic: str
    count: int
    avg_risk_score: float


class BrandMentionSummary(BaseModel):
    brand_name: str
    total_mentions: int
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    critical_alerts: int = 0
    avg_risk_score: float = 0.0


class TrendPoint(BaseModel):
    date: str
    value: float
    label: Optional[str] = None


class CoverageAnalytics(BaseModel):
    language_coverage: List[LanguageCoverage] = []
    publication_coverage: List[PublicationCoverage] = []
    sentiment_distribution: SentimentDistribution = SentimentDistribution()
    crisis_topics: List[CrisisTopicDistribution] = []
    brand_mentions: List[BrandMentionSummary] = []
    sentiment_trend: List[TrendPoint] = []
    crisis_trend: List[TrendPoint] = []


class PublicationCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    language: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    reach_tier: int = 2
    estimated_circulation: Optional[int] = None
    default_ocr_language: Optional[str] = None


class PublicationResponse(BaseModel):
    id: Union[UUID, str]
    name: str
    display_name: Optional[str] = None
    language: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    reach_tier: int = 2
    estimated_circulation: Optional[int] = None
    reach_score: float = 0.5
    default_ocr_language: Optional[str] = None
    active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True
