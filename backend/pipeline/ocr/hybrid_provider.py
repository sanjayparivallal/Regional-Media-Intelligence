"""
Hybrid OCR Provider.

Runs multiple OCR engines and selects the best result.
Core implementation of the trial-and-error OCR philosophy.
"""

import logging
import time
from typing import List, Optional
import numpy as np

from pipeline.ocr.base import OCRProvider, OCRResult, OCRBox
from pipeline.ocr.confidence import calculate_ocr_confidence

logger = logging.getLogger(__name__)


class HybridOCRProvider(OCRProvider):
    """
    Hybrid OCR provider that runs multiple engines and picks the best.
    Implements automated trial-and-error for maximum accuracy.
    """

    def __init__(self, providers: List[OCRProvider] = None):
        self._providers = providers or []

    @property
    def name(self) -> str:
        return "hybrid"

    def add_provider(self, provider: OCRProvider):
        if provider.is_available():
            self._providers.append(provider)
            logger.info(f"Added OCR provider: {provider.name}")

    def ocr(self, image: np.ndarray, language: str = "en") -> OCRResult:
        """Run all available providers and return the best result."""
        start = time.time()

        if not self._providers:
            logger.error("No OCR providers available")
            return OCRResult(text="", confidence=0.0, engine="hybrid_none")

        results = []
        for provider in self._providers:
            try:
                result = provider.ocr(image, language)
                # Calculate comprehensive confidence
                enhanced_conf = calculate_ocr_confidence(result, language)
                result.confidence = enhanced_conf
                results.append(result)
                logger.info(
                    f"  {provider.name}: conf={enhanced_conf:.1f}%, "
                    f"words={result.word_count}"
                )
                # Early exit if provider achieved good confidence and words to avoid running redundant slow engines
                if enhanced_conf >= 70.0 and result.word_count >= 10:
                    logger.info(f"Early exit: {provider.name} satisfied confidence threshold ({enhanced_conf:.1f}%)")
                    break
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")

        if not results:
            return OCRResult(text="", confidence=0.0, engine="hybrid_failed")

        # Select the best result with non-empty text
        valid_results = [r for r in results if r.text and r.text.strip()]
        best = max(valid_results, key=lambda r: (r.confidence, r.word_count)) if valid_results else results[0]
        best.engine = f"hybrid({best.engine})"

        elapsed = int((time.time() - start) * 1000)
        best.processing_time_ms = elapsed

        logger.info(
            f"Hybrid OCR selected: {best.engine} "
            f"(confidence {best.confidence:.1f}%)"
        )
        return best
