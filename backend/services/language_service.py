"""
Language Detection Service.

Article-level language detection with code-switching support.
Uses Unicode script detection + langdetect library.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionResult:
    """Single language detection result."""
    language: str
    language_name: str
    confidence: float
    script: str = ""
    method: str = ""

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "language_name": self.language_name,
            "confidence": self.confidence,
            "script": self.script,
            "method": self.method,
        }


@dataclass
class MultiLanguageResult:
    """Multi-language detection result for mixed-language content."""
    primary: LanguageDetectionResult
    languages: List[LanguageDetectionResult]
    is_multilingual: bool = False

    def to_dict(self) -> dict:
        return {
            "language": self.primary.language,
            "language_name": self.primary.language_name,
            "confidence": self.primary.confidence,
            "is_multilingual": self.is_multilingual,
            "languages": [l.to_dict() for l in self.languages],
        }


# Language name lookup
LANG_NAMES = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "ur": "Urdu",
    "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi", "unknown": "Unknown",
}


class LanguageService:
    """
    Article-level language detection with code-switching awareness.

    Does NOT classify English company names as a separate article language.
    Uses a lightweight local approach (no LLM).
    """

    def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detect the primary language of text.

        Returns language code, name, confidence, and detection method.
        """
        if not text or len(text.strip()) < 3:
            return LanguageDetectionResult(
                language="unknown", language_name="Unknown",
                confidence=0.0, method="none",
            )

        from pipeline.nlp.language_detector import detect_language
        result = detect_language(text)

        return LanguageDetectionResult(
            language=result.language,
            language_name=LANG_NAMES.get(result.language, result.language),
            confidence=result.confidence,
            script=result.script,
            method=result.method,
        )

    def detect_multi(self, text: str) -> MultiLanguageResult:
        """
        Detect all languages present in text.

        Handles code-switching (e.g., Tamil sentence + English company name).
        Does NOT classify English brand names in regional text as a separate
        article language.
        """
        if not text or len(text.strip()) < 3:
            empty = LanguageDetectionResult(
                language="unknown", language_name="Unknown",
                confidence=0.0, method="none",
            )
            return MultiLanguageResult(primary=empty, languages=[empty])

        from pipeline.nlp.language_detector import detect_language_multi

        results = detect_language_multi(text)

        lang_results = []
        for r in results:
            lang_results.append(LanguageDetectionResult(
                language=r.language,
                language_name=LANG_NAMES.get(r.language, r.language),
                confidence=r.confidence,
                script=r.script,
                method=r.method,
            ))

        # Filter out English if it's a minor component (< 20%)
        # This handles code-switching: English brand names in regional text
        regional_langs = [l for l in lang_results if l.language != "en"]
        english_langs = [l for l in lang_results if l.language == "en"]

        if regional_langs and english_langs:
            english_conf = english_langs[0].confidence
            regional_conf = regional_langs[0].confidence

            # If English is minor (< 20% of text), it's code-switching
            if english_conf < 20 and regional_conf > 50:
                primary = regional_langs[0]
                is_multilingual = True
            else:
                primary = lang_results[0]
                is_multilingual = len(lang_results) > 1
        else:
            primary = lang_results[0] if lang_results else LanguageDetectionResult(
                language="unknown", language_name="Unknown",
                confidence=0.0, method="none",
            )
            is_multilingual = len(lang_results) > 1

        return MultiLanguageResult(
            primary=primary,
            languages=lang_results,
            is_multilingual=is_multilingual,
        )
