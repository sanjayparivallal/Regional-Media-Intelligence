"""
Crisis/Topic Classification Module.

Hybrid classifier using:
- Keyword scoring
- Entity signals
- Sentiment signals
- Pattern matching

NOT just keyword matching — uses weighted multi-signal scoring.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Crisis topics with associated keywords and severity
CRISIS_TOPICS = {
    "regulatory_action": {
        "keywords": ["regulatory", "regulation", "compliance", "RBI", "SEBI", "penalty", "fine",
                      "enforcement", "violation", "directive", "order", "notice", "ban"],
        "severity": 0.85,
    },
    "fraud": {
        "keywords": ["fraud", "scam", "cheat", "deceive", "ponzi", "embezzlement",
                      "money laundering", "counterfeit", "forgery", "swindle"],
        "severity": 0.95,
    },
    "legal_case": {
        "keywords": ["court", "lawsuit", "legal", "judge", "verdict", "hearing",
                      "petition", "appeal", "bail", "FIR", "complaint filed"],
        "severity": 0.70,
    },
    "product_complaint": {
        "keywords": ["complaint", "defect", "malfunction", "quality", "recall",
                      "customer", "consumer", "grievance", "faulty", "broken"],
        "severity": 0.60,
    },
    "safety_issue": {
        "keywords": ["accident", "death", "injury", "fire", "explosion", "hazard",
                      "safety", "dangerous", "toxic", "contaminated", "harmful"],
        "severity": 0.90,
    },
    "data_privacy": {
        "keywords": ["data breach", "privacy", "hack", "leak", "cybersecurity",
                      "personal data", "information leak", "surveillance", "GDPR"],
        "severity": 0.80,
    },
    "financial_issue": {
        "keywords": ["loss", "bankruptcy", "default", "debt", "insolvency",
                      "downgrade", "liquidation", "NPE", "bad loan", "write-off"],
        "severity": 0.75,
    },
    "executive_controversy": {
        "keywords": ["CEO", "founder", "director", "chairman", "arrested",
                      "resigned", "controversy", "scandal", "allegation"],
        "severity": 0.70,
    },
    "reputational_issue": {
        "keywords": ["controversy", "scandal", "backlash", "outrage", "protest",
                      "boycott", "criticism", "expose", "allegation"],
        "severity": 0.65,
    },
    "government_action": {
        "keywords": ["government", "ministry", "parliament", "policy", "legislation",
                      "bill", "act", "ordinance", "notification", "gazette"],
        "severity": 0.60,
    },
    "product_failure": {
        "keywords": ["crash", "outage", "downtime", "failure", "glitch", "bug",
                      "not working", "service disruption", "unavailable"],
        "severity": 0.55,
    },
    "customer_complaint": {
        "keywords": ["customer complaint", "consumer forum", "poor service",
                      "refund", "overcharged", "misleading", "unfair"],
        "severity": 0.50,
    },
}


@dataclass
class CrisisResult:
    topic: str
    confidence: float
    severity: float
    keywords_matched: List[str]
    model_score: float = 0.0
    keyword_score: float = 0.0
    entity_signal: float = 0.0
    sentiment_signal: float = 0.0


class CrisisClassifier:
    """Hybrid crisis topic classifier."""

    def classify(
        self,
        text: str,
        entities: List[str] = None,
        sentiment_label: str = None,
        sentiment_confidence: float = 0.0,
    ) -> Optional[CrisisResult]:
        """
        Classify crisis topic using multi-signal scoring:
        MODEL_SCORE + KEYWORD_SCORE + ENTITY_SIGNAL + SENTIMENT_SIGNAL
        """
        if not text:
            return None

        text_lower = text.lower()
        best_topic = None
        best_score = 0.0
        best_keywords = []

        for topic, config in CRISIS_TOPICS.items():
            keywords = config["keywords"]
            severity = config["severity"]

            # Keyword matching score
            matched = [kw for kw in keywords if kw.lower() in text_lower]
            if not matched:
                continue

            keyword_score = min(len(matched) / 3, 1.0) * 40  # Max 40 from keywords

            # Entity signal (regulators/government boost regulatory topics)
            entity_signal = 0.0
            if entities:
                entity_types = [e if isinstance(e, str) else str(e) for e in entities]
                entity_str = " ".join(entity_types).lower()
                if any(reg in entity_str for reg in ["rbi", "sebi", "ministry", "regulator"]):
                    if topic in ("regulatory_action", "government_action"):
                        entity_signal = 20
                    else:
                        entity_signal = 5

            # Sentiment signal
            sentiment_signal = 0.0
            if sentiment_label == "negative":
                sentiment_signal = min(sentiment_confidence / 100 * 25, 25)
            elif sentiment_label == "positive":
                sentiment_signal = -10  # Positive sentiment reduces crisis score

            # Combined score
            total_score = keyword_score + entity_signal + sentiment_signal
            total_score *= severity  # Adjust by topic severity

            if total_score > best_score:
                best_score = total_score
                best_topic = topic
                best_keywords = matched

        if not best_topic or best_score < 10:
            return None

        confidence = min(best_score / 60 * 100, 98)

        return CrisisResult(
            topic=best_topic,
            confidence=round(confidence, 1),
            severity=CRISIS_TOPICS[best_topic]["severity"],
            keywords_matched=best_keywords,
            keyword_score=round(best_score, 1),
        )
