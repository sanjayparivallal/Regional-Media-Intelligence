"""
Alert Generation and Deduplication Module.

Generates alerts from brand mentions with risk scores.
Deduplicates using fingerprinting and similarity detection.
Groups related alerts into incidents.
"""

import logging
import hashlib
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AlertData:
    """Alert data for database insertion."""
    article_id: str
    brand_id: str
    title: str
    summary: str
    priority: str
    risk_score: float
    risk_breakdown: dict
    publication_name: str = ""
    page_number: int = 0
    language: str = ""
    region: str = ""
    sentiment: str = "neutral"
    sentiment_confidence: float = 0.0
    crisis_topic: str = ""
    crisis_keywords: list = None
    fingerprint: str = ""
    is_duplicate: bool = False


def generate_alert(
    article_id: str,
    brand_id: str,
    brand_name: str,
    headline: str,
    crisis_topic: str,
    risk_score: float,
    risk_breakdown: dict,
    sentiment: str,
    sentiment_confidence: float,
    publication_name: str = "",
    page_number: int = 0,
    language: str = "",
    region: str = "",
    crisis_keywords: list = None,
) -> AlertData:
    """Generate an alert from analysis results."""

    # Create descriptive title
    topic_display = crisis_topic.replace("_", " ").title()
    title = f"{topic_display} — {brand_name}"
    if headline:
        title = f"{topic_display}: {headline[:100]}"

    # Create summary
    summary = (
        f"{topic_display} detected involving {brand_name}. "
        f"Sentiment: {sentiment} ({sentiment_confidence:.0f}% confidence). "
        f"Source: {publication_name}, page {page_number}."
    )

    # Generate fingerprint for deduplication
    fingerprint = _generate_fingerprint(brand_name, headline, crisis_topic, publication_name)

    priority = risk_breakdown.get("priority", "low")

    return AlertData(
        article_id=article_id,
        brand_id=brand_id,
        title=title,
        summary=summary,
        priority=priority,
        risk_score=risk_score,
        risk_breakdown=risk_breakdown,
        publication_name=publication_name,
        page_number=page_number,
        language=language,
        region=region,
        sentiment=sentiment,
        sentiment_confidence=sentiment_confidence,
        crisis_topic=crisis_topic,
        crisis_keywords=crisis_keywords or [],
        fingerprint=fingerprint,
    )


def _generate_fingerprint(
    brand: str, headline: str, topic: str, publication: str
) -> str:
    """Generate a fingerprint for deduplication."""
    # Normalize
    parts = [
        brand.lower().strip(),
        _normalize_headline(headline),
        topic.lower().strip(),
        datetime.utcnow().strftime("%Y-%m-%d"),
    ]
    content = "|".join(parts)
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _normalize_headline(headline: str) -> str:
    """Normalize headline for comparison."""
    if not headline:
        return ""
    import re
    # Remove punctuation, lowercase, collapse whitespace
    normalized = re.sub(r'[^\w\s]', '', headline.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def check_duplicate(
    new_fingerprint: str,
    existing_fingerprints: List[str],
    new_headline: str = "",
    existing_headlines: List[str] = None,
) -> bool:
    """
    Check if an alert is a duplicate.
    Uses fingerprint matching and headline similarity.
    """
    # Exact fingerprint match
    if new_fingerprint in existing_fingerprints:
        return True

    # Headline similarity check
    if new_headline and existing_headlines:
        normalized_new = _normalize_headline(new_headline)
        for existing in existing_headlines:
            normalized_existing = _normalize_headline(existing)
            if _similarity(normalized_new, normalized_existing) >= 0.65:
                return True

    return False


def _similarity(a: str, b: str) -> float:
    """Simple word overlap similarity."""
    if not a or not b:
        return 0.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
