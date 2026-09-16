"""Unit tests for the explainable risk score engine."""

import pytest
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.crisis.risk_scorer import calculate_risk_score, RiskBreakdown


def test_risk_score_calculation_critical():
    """Verify high severity inputs yield critical priority risk score."""
    breakdown = calculate_risk_score(
        sentiment_label="negative",
        sentiment_confidence=95.0,
        brand_match_confidence=0.98,
        crisis_severity=0.95,
        crisis_confidence=90.0,
        publication_reach=0.9,
        overall_ai_confidence=92.0,
    )
    assert isinstance(breakdown, RiskBreakdown)
    assert breakdown.total >= 80.0
    assert breakdown.priority in ("critical", "high")
    assert breakdown.sentiment_score > 20.0
    assert breakdown.brand_score > 20.0
    assert breakdown.topic_score > 15.0


def test_risk_score_calculation_low():
    """Verify positive / low risk inputs yield low priority risk score."""
    breakdown = calculate_risk_score(
        sentiment_label="positive",
        sentiment_confidence=90.0,
        brand_match_confidence=0.3,
        crisis_severity=0.1,
        crisis_confidence=20.0,
        publication_reach=0.2,
        overall_ai_confidence=60.0,
    )
    assert breakdown.total < 35.0
    assert breakdown.priority == "low"
    d = breakdown.to_dict()
    assert "sentiment" in d
    assert "brand" in d
    assert "topic" in d
    assert "reach" in d
    assert "confidence" in d


def test_risk_score_breakdown_dict_structure():
    """Verify dictionary representation has all components and weights."""
    breakdown = calculate_risk_score()
    d = breakdown.to_dict()
    assert d["sentiment"]["max"] == 30.0
    assert d["brand"]["max"] == 25.0
    assert d["topic"]["max"] == 20.0
    assert d["reach"]["max"] == 15.0
    assert d["confidence"]["max"] == 10.0
    assert 0 <= d["total"] <= 100
