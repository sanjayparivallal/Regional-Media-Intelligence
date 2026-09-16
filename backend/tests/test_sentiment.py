"""Unit tests for sentiment analyzer and lexicon fallback."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.sentiment.analyzer import SentimentAnalyzer, SentimentResult
from pipeline.nlp.sentiment.lexicon import analyze_lexicon_sentiment


def test_lexicon_sentiment_negative():
    text = "The company faces severe penalty, fine, and regulatory ban after fraud scandal."
    res = analyze_lexicon_sentiment(text)
    assert isinstance(res, SentimentResult)
    assert res.label == "negative"
    assert res.confidence > 60.0
    assert res.negative_score > res.positive_score


def test_lexicon_sentiment_positive():
    text = "Company achieved record growth and won premier innovation award for partnership success."
    res = analyze_lexicon_sentiment(text)
    assert res.label == "positive"
    assert res.confidence > 60.0
    assert res.positive_score > res.negative_score


def test_sentiment_analyzer_fallback():
    analyzer = SentimentAnalyzer()
    res = analyzer.analyze(
        text="The regulatory committee announced a strict investigation into compliance violations.",
    )
    assert res.label in ("negative", "neutral")
    assert res.confidence > 0
