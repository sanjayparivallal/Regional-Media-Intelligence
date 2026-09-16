"""
Lexicon-based Sentiment Analysis.

Rule-based fallback sentiment using keyword scoring.
"""

import logging

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "good", "great", "excellent", "positive", "growth", "profit", "success",
    "improvement", "award", "innovation", "launch", "expand", "partnership",
    "benefit", "achieve", "record", "milestone", "appreciation", "gain",
    "progress", "development", "strong", "best", "leading", "top",
}

NEGATIVE_WORDS = {
    "bad", "poor", "fraud", "scam", "complaint", "loss", "negative", "crisis",
    "ban", "penalty", "fine", "violation", "illegal", "arrest", "investigation",
    "lawsuit", "court", "dispute", "failure", "collapse", "warning", "risk",
    "accident", "death", "injury", "corruption", "default", "shutdown",
    "controversy", "scandal", "breach", "hack", "leak", "expose", "allege",
    "suspend", "revoke", "cancel", "reject", "decline", "drop", "crash",
    "regulatory", "enforcement", "action", "probe", "scrutiny", "concern",
}

INTENSIFIERS = {"very", "extremely", "highly", "seriously", "severely", "major"}
NEGATORS = {"not", "no", "never", "neither", "nor", "hardly", "barely"}


def analyze_lexicon_sentiment(text: str):
    """
    Analyze sentiment using keyword lexicon.
    Returns SentimentResult.
    """
    from pipeline.nlp.sentiment.analyzer import SentimentResult

    if not text:
        return SentimentResult("neutral", 50.0, model_used="lexicon")

    words = text.lower().split()
    pos_count = 0
    neg_count = 0
    total_words = len(words)

    for i, word in enumerate(words):
        # Check for negation
        negated = i > 0 and words[i - 1] in NEGATORS
        intensified = i > 0 and words[i - 1] in INTENSIFIERS

        weight = 1.5 if intensified else 1.0

        if word in POSITIVE_WORDS:
            if negated:
                neg_count += weight
            else:
                pos_count += weight
        elif word in NEGATIVE_WORDS:
            if negated:
                pos_count += weight
            else:
                neg_count += weight

    # Calculate scores
    total_sentiment = pos_count + neg_count
    if total_sentiment == 0:
        return SentimentResult(
            "neutral", 60.0,
            positive_score=33.0, neutral_score=34.0, negative_score=33.0,
            model_used="lexicon",
        )

    pos_ratio = pos_count / total_sentiment
    neg_ratio = neg_count / total_sentiment

    if neg_ratio > 0.6:
        label = "negative"
        confidence = min(95, 50 + neg_ratio * 45)
    elif pos_ratio > 0.6:
        label = "positive"
        confidence = min(95, 50 + pos_ratio * 45)
    else:
        label = "neutral"
        confidence = 55.0

    return SentimentResult(
        label=label,
        confidence=round(confidence, 1),
        positive_score=round(pos_ratio * 100, 1),
        neutral_score=round(max(0, 100 - pos_ratio * 100 - neg_ratio * 100), 1),
        negative_score=round(neg_ratio * 100, 1),
        model_used="lexicon",
    )
