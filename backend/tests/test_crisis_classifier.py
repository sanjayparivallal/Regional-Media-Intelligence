"""Unit tests for the crisis/topic classifier."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.crisis.classifier import CrisisClassifier, CrisisResult


def test_crisis_classification_regulatory():
    """Verify regulatory action text is classified properly with entity signal."""
    classifier = CrisisClassifier()
    text = "The RBI issued a directive imposing a fine and regulatory ban on the company for compliance failure."
    res = classifier.classify(
        text=text,
        entities=["RBI", "regulator"],
        sentiment_label="negative",
        sentiment_confidence=90.0,
    )
    assert res is not None
    assert isinstance(res, CrisisResult)
    assert res.topic in ("regulatory_action", "government_action")
    assert res.severity >= 0.60
    assert any(kw in ["RBI", "regulatory", "ban", "fine", "compliance"] for kw in res.keywords_matched)


def test_crisis_classification_fraud():
    """Verify fraud keywords trigger fraud topic."""
    classifier = CrisisClassifier()
    text = "Police arrested three suspects for money laundering and fraud scam involving fake invoices."
    res = classifier.classify(
        text=text,
        sentiment_label="negative",
        sentiment_confidence=85.0,
    )
    assert res is not None
    assert res.topic == "fraud"
    assert res.severity == 0.95


def test_crisis_classification_benign():
    """Verify benign text without crisis indicators returns None."""
    classifier = CrisisClassifier()
    text = "The company reported a wonderful quarter with higher customer satisfaction and new features."
    res = classifier.classify(
        text=text,
        sentiment_label="positive",
        sentiment_confidence=90.0,
    )
    assert res is None
