"""
Language Configuration Loader.

Loads language settings from config/languages.json and provides
a centralized registry for all language-related lookups.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "languages.json"


@dataclass
class LanguageConfig:
    """Configuration for a single language."""
    code: str
    name: str
    script: str
    enabled: bool
    easyocr_code: Optional[str]
    nllb_code: str
    ocr_provider: str
    is_target_language: bool
    priority: int
    ocr_note: Optional[str] = None


class LanguageRegistry:
    """Centralized language registry loaded from config/languages.json."""

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = Path(config_path) if config_path else CONFIG_PATH
        self._languages: Dict[str, LanguageConfig] = {}
        self._raw_config: dict = {}
        self._load()

    def _load(self):
        """Load language configuration from JSON file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._raw_config = json.load(f)

            for code, data in self._raw_config.get("languages", {}).items():
                self._languages[code] = LanguageConfig(
                    code=code,
                    name=data["name"],
                    script=data["script"],
                    enabled=data.get("enabled", True),
                    easyocr_code=data.get("easyocr_code"),
                    nllb_code=data.get("nllb_code", ""),
                    ocr_provider=data.get("ocr_provider", "easyocr"),
                    is_target_language=data.get("is_target_language", False),
                    priority=data.get("priority", 99),
                    ocr_note=data.get("ocr_note"),
                )
            logger.info(f"Loaded {len(self._languages)} languages from {self._config_path}")
        except Exception as e:
            logger.error(f"Failed to load language config: {e}")

    def get(self, code: str) -> Optional[LanguageConfig]:
        """Get language config by code."""
        return self._languages.get(code)

    def get_enabled(self) -> List[LanguageConfig]:
        """Get all enabled languages."""
        return [l for l in self._languages.values() if l.enabled]

    def get_easyocr_languages(self) -> List[str]:
        """Get language codes supported by EasyOCR."""
        return [l.easyocr_code for l in self._languages.values()
                if l.enabled and l.easyocr_code and l.ocr_provider == "easyocr"]

    def get_paddleocr_languages(self) -> List[str]:
        """Get language codes that need PaddleOCR fallback."""
        return [l.code for l in self._languages.values()
                if l.enabled and l.ocr_provider == "paddleocr"]

    def get_nllb_code(self, lang_code: str) -> Optional[str]:
        """Get NLLB model code for a language."""
        lang = self._languages.get(lang_code)
        return lang.nllb_code if lang else None

    def get_ocr_provider(self, lang_code: str) -> str:
        """Get the OCR provider name for a language."""
        lang = self._languages.get(lang_code)
        return lang.ocr_provider if lang else "easyocr"

    def get_primary_languages(self) -> List[str]:
        """Get the primary focus languages."""
        return self._raw_config.get("primary_languages", [])

    @property
    def default_target(self) -> str:
        return self._raw_config.get("default_target_language", "en")

    @property
    def ocr_confidence_threshold(self) -> int:
        return self._raw_config.get("ocr_settings", {}).get("confidence_threshold", 90)

    @property
    def translation_review_threshold(self) -> int:
        return self._raw_config.get("translation_settings", {}).get("review_threshold", 90)

    def is_supported(self, code: str) -> bool:
        """Check if a language code is supported and enabled."""
        lang = self._languages.get(code)
        return lang is not None and lang.enabled

    def all_codes(self) -> List[str]:
        """Get all enabled language codes."""
        return [l.code for l in self._languages.values() if l.enabled]


# Singleton instance
_registry: Optional[LanguageRegistry] = None


def get_language_registry() -> LanguageRegistry:
    """Get the global language registry singleton."""
    global _registry
    if _registry is None:
        _registry = LanguageRegistry()
    return _registry
