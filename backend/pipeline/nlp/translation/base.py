"""
Translation Provider Base Class.

Abstract interface for translation engines.
All providers must support entity-protected translation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    source_language: str
    target_language: str = "en"
    confidence: float = 0.0
    model_used: str = ""
    entities_protected: List[str] = field(default_factory=list)
    processing_time_ms: int = 0


class TranslationProvider(ABC):
    """Abstract base class for translation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en",
        protected_entities: List[str] = None,
    ) -> TranslationResult:
        pass

    def is_available(self) -> bool:
        return True
