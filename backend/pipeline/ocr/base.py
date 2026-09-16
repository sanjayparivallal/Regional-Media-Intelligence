"""
OCR Provider Base Class.

Abstract interface for all OCR engines.
Every provider returns standardized OCR results with bounding boxes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any

try:
    import numpy as np
except Exception:
    np = None



@dataclass
class OCRBox:
    """Single OCR text detection with bounding box."""
    x: float
    y: float
    width: float
    height: float
    text: str
    confidence: float
    line_num: int = 0
    block_num: int = 0
    font_size_estimate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "x": self.x, "y": self.y,
            "width": self.width, "height": self.height,
            "text": self.text, "confidence": self.confidence,
            "line_num": self.line_num, "block_num": self.block_num,
            "font_size_estimate": self.font_size_estimate,
        }


@dataclass
class OCRResult:
    """Complete OCR result for a page."""
    text: str
    boxes: List[OCRBox] = field(default_factory=list)
    confidence: float = 0.0
    word_count: int = 0
    engine: str = ""
    language: str = ""
    processing_time_ms: int = 0
    preprocessing: str = ""

    @property
    def full_text(self) -> str:
        if self.text:
            return self.text
        return " ".join(box.text for box in self.boxes if box.text)


class OCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    def supported_languages(self) -> List[str]:
        """Languages this provider supports."""
        return ["en", "hi", "ta"]

    @abstractmethod
    def ocr(
        self,
        image: Any,
        language: str = "en",
    ) -> OCRResult:
        """
        Perform OCR on an image.

        Args:
            image: Input image as numpy array
            language: Language code (en, hi, ta, etc.)

        Returns:
            OCRResult with text, bounding boxes, and confidence
        """
        pass

    def is_available(self) -> bool:
        """Check if this OCR provider is available."""
        return True
