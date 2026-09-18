"""
Confidence Service.

Aggregates OCR, language detection, and translation confidence.
Separates real model confidence from heuristic estimates.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AggregatedConfidence:
    """Aggregated confidence scores from all pipeline stages."""
    ocr_confidence: Optional[float]
    language_confidence: Optional[float]
    translation_confidence: Optional[float]

    ocr_source: str = "not_available"
    language_source: str = "not_available"
    translation_source: str = "not_available"

    review_required: bool = False
    review_reasons: list = None

    def __post_init__(self):
        if self.review_reasons is None:
            self.review_reasons = []

    def to_dict(self) -> dict:
        return {
            "ocr_confidence": self.ocr_confidence,
            "language_confidence": self.language_confidence,
            "translation_confidence": self.translation_confidence,
            "ocr_source": self.ocr_source,
            "language_source": self.language_source,
            "translation_source": self.translation_source,
            "review_required": self.review_required,
            "review_reasons": self.review_reasons,
        }


class ConfidenceService:
    """
    Aggregates confidence scores from pipeline stages.

    Rules:
    - Real model confidence values are passed through as-is
    - If a model does not provide confidence, mark as null with source="not_available"
    - Heuristic scores are clearly labeled with source="heuristic"
    - Never present a heuristic as model confidence
    """

    def __init__(
        self,
        ocr_threshold: float = 90.0,
        translation_threshold: float = 90.0,
    ):
        self.ocr_threshold = ocr_threshold
        self.translation_threshold = translation_threshold

    def aggregate(
        self,
        ocr_confidence: Optional[float] = None,
        ocr_source: str = "not_available",
        language_confidence: Optional[float] = None,
        language_source: str = "not_available",
        translation_confidence: Optional[float] = None,
        translation_source: str = "not_available",
    ) -> AggregatedConfidence:
        """
        Aggregate confidence values and determine if review is needed.

        Args:
            ocr_confidence: OCR confidence (0-100, or None if unavailable)
            ocr_source: Source of OCR confidence ("model", "heuristic", "not_available")
            language_confidence: Language detection confidence (0-100)
            language_source: Source of language confidence
            translation_confidence: Translation confidence (0-100, or None)
            translation_source: Source of translation confidence

        Returns:
            AggregatedConfidence with review determination
        """
        review_required = False
        review_reasons = []

        # Check OCR confidence
        if ocr_confidence is not None and ocr_confidence < self.ocr_threshold:
            review_required = True
            review_reasons.append(f"OCR confidence {ocr_confidence:.0f}% below threshold {self.ocr_threshold:.0f}%")

        # Check translation confidence (only if actually provided)
        if translation_confidence is not None and translation_confidence < self.translation_threshold:
            review_required = True
            review_reasons.append(
                f"Translation confidence {translation_confidence:.0f}% below threshold {self.translation_threshold:.0f}%"
            )

        # If translation confidence is not available, flag for review
        # only if there was a translation attempt
        if translation_confidence is None and translation_source == "not_available":
            review_reasons.append("Translation confidence not available from model")
            # Don't auto-require review just because confidence is unavailable;
            # only flag if other signals are also weak

        return AggregatedConfidence(
            ocr_confidence=ocr_confidence,
            language_confidence=language_confidence,
            translation_confidence=translation_confidence,
            ocr_source=ocr_source,
            language_source=language_source,
            translation_source=translation_source,
            review_required=review_required,
            review_reasons=review_reasons,
        )
