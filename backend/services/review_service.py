"""
Review Service.

Human review queue with configurable thresholds.
Implements APPROVE / EDIT / REJECT workflow.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """A single review queue item."""
    review_type: str  # ocr, translation, segmentation, sentiment, entity, crisis
    reason: str
    priority: str  # low, normal, high, urgent
    ai_output: Dict[str, Any]
    confidence: Optional[float]
    article_id: Optional[str] = None
    alert_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "review_type": self.review_type,
            "reason": self.reason,
            "priority": self.priority,
            "ai_output": self.ai_output,
            "confidence": self.confidence,
            "article_id": self.article_id,
            "alert_id": self.alert_id,
        }


@dataclass
class ReviewAction:
    """Result of a human review action."""
    action: str  # APPROVE, EDIT, REJECT
    reviewer: str
    timestamp: str
    original_text: Optional[str] = None
    ai_translation: Optional[str] = None
    corrected_translation: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "original_text": self.original_text,
            "ai_translation": self.ai_translation,
            "corrected_translation": self.corrected_translation,
            "reason": self.reason,
        }


class ReviewService:
    """
    Human review queue service.

    Configurable thresholds:
    - ocr_review_threshold = 90
    - translation_review_threshold = 90

    Review actions: APPROVE, EDIT, REJECT
    Stores: reviewer, timestamp, original, AI output, correction, reason
    """

    def __init__(
        self,
        ocr_threshold: float = 90.0,
        translation_threshold: float = 90.0,
    ):
        self.ocr_threshold = ocr_threshold
        self.translation_threshold = translation_threshold

    def should_review(
        self,
        ocr_confidence: Optional[float] = None,
        translation_confidence: Optional[float] = None,
        segmentation_confidence: Optional[float] = None,
        lfm_status: Optional[str] = None,
    ) -> Optional[ReviewItem]:
        """
        Determine if an article needs human review.

        Returns a ReviewItem if review is needed, None otherwise.
        """
        reasons = []
        priority = "normal"

        # OCR confidence check
        if ocr_confidence is not None and ocr_confidence < self.ocr_threshold:
            reasons.append(f"OCR confidence {ocr_confidence:.0f}% below {self.ocr_threshold:.0f}%")
            if ocr_confidence < 60:
                priority = "high"

        # Translation confidence check
        if translation_confidence is not None and translation_confidence < self.translation_threshold:
            reasons.append(f"Translation confidence {translation_confidence:.0f}% below {self.translation_threshold:.0f}%")

        # Segmentation confidence check
        if segmentation_confidence is not None and segmentation_confidence < 50:
            reasons.append(f"Segmentation confidence {segmentation_confidence:.0f}% below 50%")

        # LFM failure
        if lfm_status == "failed_needs_review":
            reasons.append("LFM analysis failed after retry")
            priority = "high"

        if not reasons:
            return None

        return ReviewItem(
            review_type="quality",
            reason="; ".join(reasons),
            priority=priority,
            ai_output={
                "ocr_confidence": ocr_confidence,
                "translation_confidence": translation_confidence,
                "segmentation_confidence": segmentation_confidence,
                "lfm_status": lfm_status,
            },
            confidence=ocr_confidence,
        )

    def create_review_action(
        self,
        action: str,
        reviewer: str,
        original_text: Optional[str] = None,
        ai_translation: Optional[str] = None,
        corrected_translation: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> ReviewAction:
        """
        Create a review action record.

        Args:
            action: APPROVE, EDIT, or REJECT
            reviewer: Name/ID of the reviewer
            original_text: Original OCR text
            ai_translation: AI-generated translation
            corrected_translation: Human-corrected translation (for EDIT)
            reason: Reason for the action

        Returns:
            ReviewAction record
        """
        if action not in ("APPROVE", "EDIT", "REJECT"):
            raise ValueError(f"Invalid review action: {action}. Must be APPROVE, EDIT, or REJECT.")

        return ReviewAction(
            action=action,
            reviewer=reviewer,
            timestamp=datetime.utcnow().isoformat(),
            original_text=original_text,
            ai_translation=ai_translation,
            corrected_translation=corrected_translation,
            reason=reason,
        )
