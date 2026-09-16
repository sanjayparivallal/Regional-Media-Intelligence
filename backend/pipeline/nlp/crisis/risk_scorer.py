"""
Explainable Risk Score Engine.

Calculates crisis risk score with full breakdown:
- Sentiment severity   = 30%
- Brand relevance      = 25%
- Topic/crisis severity= 20%
- Publication reach    = 15%
- AI confidence        = 10%

Score ranges:
- 0-30:  LOW
- 31-60: MEDIUM
- 61-80: HIGH
- 81-100: CRITICAL
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskBreakdown:
    sentiment_score: float = 0.0
    sentiment_max: float = 30.0
    brand_score: float = 0.0
    brand_max: float = 25.0
    topic_score: float = 0.0
    topic_max: float = 20.0
    reach_score: float = 0.0
    reach_max: float = 15.0
    confidence_score: float = 0.0
    confidence_max: float = 10.0
    total: float = 0.0
    priority: str = "low"

    def to_dict(self) -> dict:
        return {
            "sentiment": {"score": self.sentiment_score, "max": self.sentiment_max},
            "brand": {"score": self.brand_score, "max": self.brand_max},
            "topic": {"score": self.topic_score, "max": self.topic_max},
            "reach": {"score": self.reach_score, "max": self.reach_max},
            "confidence": {"score": self.confidence_score, "max": self.confidence_max},
            "total": self.total,
            "priority": self.priority,
        }


def calculate_risk_score(
    sentiment_label: str = "neutral",
    sentiment_confidence: float = 50.0,
    brand_match_confidence: float = 0.0,
    crisis_severity: float = 0.0,
    crisis_confidence: float = 0.0,
    publication_reach: float = 0.5,
    overall_ai_confidence: float = 50.0,
) -> RiskBreakdown:
    """
    Calculate explainable risk score with full breakdown.
    Every component is individually interpretable.
    """

    # 1. Sentiment severity (30% weight)
    sentiment_map = {"negative": 1.0, "neutral": 0.3, "positive": 0.05}
    sentiment_factor = sentiment_map.get(sentiment_label, 0.3)
    sentiment_score = round(sentiment_factor * (sentiment_confidence / 100) * 30, 1)

    # 2. Brand relevance (25% weight)
    brand_score = round(brand_match_confidence * 25, 1)

    # 3. Topic/crisis severity (20% weight)
    topic_score = round(crisis_severity * (crisis_confidence / 100) * 20, 1)

    # 4. Publication reach (15% weight)
    reach_score = round(publication_reach * 15, 1)

    # 5. AI confidence (10% weight)
    confidence_score = round((overall_ai_confidence / 100) * 10, 1)

    # Total
    total = round(sentiment_score + brand_score + topic_score + reach_score + confidence_score, 1)
    total = min(100, max(0, total))

    # Priority
    if total >= 81:
        priority = "critical"
    elif total >= 61:
        priority = "high"
    elif total >= 31:
        priority = "medium"
    else:
        priority = "low"

    breakdown = RiskBreakdown(
        sentiment_score=sentiment_score,
        brand_score=brand_score,
        topic_score=topic_score,
        reach_score=reach_score,
        confidence_score=confidence_score,
        total=total,
        priority=priority,
    )

    logger.info(
        f"Risk score: {total} ({priority}) | "
        f"sentiment={sentiment_score}/30 brand={brand_score}/25 "
        f"topic={topic_score}/20 reach={reach_score}/15 conf={confidence_score}/10"
    )

    return breakdown
