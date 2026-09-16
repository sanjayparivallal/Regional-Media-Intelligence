"""Unit tests for alert generation, fingerprinting, and deduplication."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.alerting.generator import generate_alert, check_duplicate, AlertData


def test_generate_alert_structure():
    risk_breakdown = {
        "sentiment": {"score": 28, "max": 30},
        "brand": {"score": 24, "max": 25},
        "topic": {"score": 18, "max": 20},
        "reach": {"score": 13, "max": 15},
        "confidence": {"score": 8, "max": 10},
        "total": 91,
        "priority": "critical",
    }
    alert = generate_alert(
        article_id="art-1",
        brand_id="brand-1",
        brand_name="PayU",
        headline="RBI issues directive on fintech compliance",
        crisis_topic="regulatory_action",
        risk_score=91.0,
        risk_breakdown=risk_breakdown,
        sentiment="negative",
        sentiment_confidence=92.0,
        publication_name="Dainik Jagran",
        page_number=1,
        language="hi",
        region="North India",
    )
    assert isinstance(alert, AlertData)
    assert alert.priority == "critical"
    assert alert.brand_id == "brand-1"
    assert "Regulatory Action" in alert.title
    assert alert.fingerprint != ""


def test_deduplication_exact_and_headline_similarity():
    fingerprint = "abcdef1234567890abcdef1234567890"
    existing_fps = [fingerprint]

    # Exact duplicate
    assert check_duplicate(new_fingerprint=fingerprint, existing_fingerprints=existing_fps) is True

    # Headline similarity duplicate
    is_dup = check_duplicate(
        new_fingerprint="newfingerprint999",
        existing_fingerprints=[],
        new_headline="RBI bans PayU from onboarding new merchants",
        existing_headlines=["RBI bans PayU from onboarding new merchants in latest order"],
    )
    assert is_dup is True
