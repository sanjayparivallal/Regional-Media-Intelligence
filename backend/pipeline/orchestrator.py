"""
Model Orchestrator.

Master controller that manages the complete AI processing pipeline.
Configuration-driven model selection with automatic fallback.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from config import get_settings
from pipeline.hardware import detect_hardware, get_model_recommendations

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PipelineResult:
    """Complete result of processing a document page."""
    page_number: int
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    ocr_engine: str = ""
    ocr_boxes: list = field(default_factory=list)
    preprocessing: str = ""
    articles: list = field(default_factory=list)
    language: str = ""
    language_confidence: float = 0.0
    processing_time_ms: int = 0
    model_selections: dict = field(default_factory=dict)


class ModelOrchestrator:
    """
    Orchestrates the complete AI pipeline.
    Decides which models to use based on hardware and document characteristics.
    """

    def __init__(self):
        self._hw_info = detect_hardware()
        self._recommendations = get_model_recommendations(self._hw_info)
        self._ocr_providers = {}
        self._initialized = False

        logger.info(f"Hardware tier: {self._hw_info.get('recommended_tier')}")
        logger.info(f"Model recommendations: {self._recommendations}")

    def initialize(self):
        """Initialize all required models."""
        if self._initialized:
            return

        self._init_ocr()
        self._initialized = True
        logger.info("Model orchestrator initialized")

    def _init_ocr(self):
        """Initialize OCR providers based on availability."""
        from pipeline.ocr.hybrid_provider import HybridOCRProvider

        hybrid = HybridOCRProvider()

        # Try PaddleOCR
        try:
            from pipeline.ocr.paddle_provider import PaddleOCRProvider
            paddle = PaddleOCRProvider()
            if paddle.is_available():
                hybrid.add_provider(paddle)
        except Exception as e:
            logger.warning(f"PaddleOCR not available: {e}")

        # Try Tesseract
        try:
            from pipeline.ocr.tesseract_provider import TesseractProvider
            tess = TesseractProvider()
            if tess.is_available():
                hybrid.add_provider(tess)
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")

        # Try EasyOCR
        try:
            from pipeline.ocr.easyocr_provider import EasyOCRProvider
            easy = EasyOCRProvider()
            if easy.is_available():
                hybrid.add_provider(easy)
        except Exception as e:
            logger.warning(f"EasyOCR not available: {e}")

        self._ocr_providers["hybrid"] = hybrid

    def get_ocr_provider(self):
        """Get the best available OCR provider."""
        self.initialize()
        return self._ocr_providers.get("hybrid")

    def get_translation_provider(self):
        """Get the best available translation provider."""
        try:
            from pipeline.nlp.translation.nllb_provider import NLLBTranslationProvider
            provider = NLLBTranslationProvider(settings.translation_model)
            if provider.is_available():
                return provider
        except Exception as e:
            logger.warning(f"NLLB not available: {e}")

        from pipeline.nlp.translation.fallback_provider import FallbackTranslationProvider
        return FallbackTranslationProvider()

    def get_entity_extractor(self):
        """Get entity extractor."""
        from pipeline.nlp.entity.extractor import EntityExtractor
        return EntityExtractor()

    def get_brand_matcher(self):
        """Get brand matcher."""
        from pipeline.nlp.entity.brand_matcher import BrandMatcher
        return BrandMatcher()

    def get_sentiment_analyzer(self):
        """Get sentiment analyzer."""
        from pipeline.nlp.sentiment.analyzer import SentimentAnalyzer
        return SentimentAnalyzer()

    def get_crisis_classifier(self):
        """Get crisis classifier."""
        from pipeline.nlp.crisis.classifier import CrisisClassifier
        return CrisisClassifier()

    @property
    def hardware_info(self) -> dict:
        return self._hw_info

    @property
    def model_recommendations(self) -> dict:
        return self._recommendations
