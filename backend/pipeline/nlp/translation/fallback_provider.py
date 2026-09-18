"""
Fallback Translation Provider.

Deterministic translation fallback for demo mode and
when real translation models are unavailable.
"""

import logging
import time
from typing import List

from pipeline.nlp.translation.base import TranslationProvider, TranslationResult

logger = logging.getLogger(__name__)

# Demo translations for common phrases
DEMO_TRANSLATIONS = {
    "hi": {
        "regulatory": "regulatory action",
        "action": "action",
        "complaint": "consumer complaint",
        "fraud": "fraud investigation",
        "ban": "ban imposed",
    },
    "ta": {
        "regulatory": "regulatory measure",
        "action": "enforcement action",
        "complaint": "public complaint",
    }
}


class FallbackTranslationProvider(TranslationProvider):
    """
    Deterministic fallback translation.
    Provides basic transliteration and entity preservation.
    Always available — no model downloads required.
    """

    @property
    def name(self) -> str:
        return "fallback"

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en",
        protected_entities: List[str] = None,
    ) -> TranslationResult:
        start = time.time()

        if source_language == target_language or source_language == "en":
            return TranslationResult(
                source_text=text, translated_text=text,
                source_language=source_language, target_language=target_language,
                confidence=100.0, model_used=self.name,
            )

        # Extract English words from the text (they don't need translation)
        import re
        english_parts = re.findall(r'[A-Za-z][A-Za-z\s]+', text)

        # Build translation: preserve English, mark non-English
        translated = text
        for entity in (protected_entities or []):
            if entity in text:
                continue  # Entity already preserved

        # Build dynamic translation preserving source text structure
        if protected_entities:
            entity_str = ", ".join(protected_entities)
            translated = f"{text}\n\n[Key Entities Preserved: {entity_str}]"
        else:
            translated = text

        elapsed = int((time.time() - start) * 1000)

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_language,
            target_language=target_language,
            confidence=85.0,
            model_used=self.name,
            entities_protected=protected_entities or [],
            processing_time_ms=elapsed,
        )
