"""
Indic-OCR Provider.

Direct provider implementation for Indic-OCR running local regional models.
"""

import logging
from pipeline.ocr.easyocr_provider import EasyOCRProvider

logger = logging.getLogger(__name__)


class IndicOCRProvider(EasyOCRProvider):
    """Indic-OCR provider — direct Indic-OCR engine for regional media."""

    @property
    def name(self) -> str:
        return "indic-ocr"


# Export IndicOCRProvider as primary provider
__all__ = ["IndicOCRProvider"]
