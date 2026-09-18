"""
OCR Service.

Unified OCR interface with language-routed provider selection.
Uses EasyOCR for supported languages and PaddleOCR as fallback
for Gujarati and Malayalam.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "models" / "indic-ocr"


@dataclass
class OCRBlock:
    """Single OCR text detection with bounding box."""
    text: str
    confidence: float
    bounding_box: List[List[int]]
    line_num: int = 0


@dataclass
class OCRServiceResult:
    """Structured OCR result matching the specified output format."""
    text: str
    language_hint: Optional[str]
    confidence: Optional[float]
    blocks: List[OCRBlock] = field(default_factory=list)
    bounding_boxes: List[Dict] = field(default_factory=list)
    processing_time: float = 0.0
    engine: str = ""
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "language_hint": self.language_hint,
            "confidence": self.confidence,
            "blocks": [
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "bounding_box": b.bounding_box,
                    "line_num": b.line_num,
                }
                for b in self.blocks
            ],
            "bounding_boxes": self.bounding_boxes,
            "processing_time": self.processing_time,
            "engine": self.engine,
            "status": self.status,
            "error": self.error,
        }


class OCRService:
    """
    Unified OCR service with language-routed provider selection.

    Uses EasyOCR for: en, hi, bn, mr, te, ta, ur, kn
    Uses PaddleOCR for: gu, ml (EasyOCR unsupported)
    """

    def __init__(self):
        self._easyocr_readers: Dict[str, Any] = {}
        self._paddle_reader = None
        self._gpu_available = False

        try:
            import torch
            self._gpu_available = torch.cuda.is_available()
        except ImportError:
            pass

    def _get_easyocr_reader(self, language: str):
        """Get or create an EasyOCR reader for a specific language."""
        # EasyOCR groups languages by script for its recognition model.
        # For Devanagari (hi, mr), they share the same recognition model.
        # Each reader is keyed by its language list.
        from services.language_config import get_language_registry
        registry = get_language_registry()

        lang_cfg = registry.get(language)
        if not lang_cfg or not lang_cfg.easyocr_code:
            return None

        # Build the language list for EasyOCR
        # Use single-language reader to avoid character set conflicts
        lang_list = [lang_cfg.easyocr_code]
        key = tuple(lang_list)

        if key not in self._easyocr_readers:
            try:
                import easyocr
                reader = easyocr.Reader(
                    lang_list,
                    gpu=self._gpu_available,
                    model_storage_directory=str(MODEL_DIR),
                    download_enabled=True,
                    verbose=False,
                )
                self._easyocr_readers[key] = reader
                logger.info(f"Initialized EasyOCR reader for: {lang_list}")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR for {lang_list}: {e}")
                return None

        return self._easyocr_readers[key]

    def _get_paddle_reader(self, language: str):
        """Get PaddleOCR reader for fallback languages (Gujarati, Malayalam)."""
        if self._paddle_reader is not None:
            return self._paddle_reader

        try:
            from paddleocr import PaddleOCR

            # PaddleOCR language mapping
            paddle_lang_map = {
                "gu": "devanagari",
                "ml": "devanagari",
            }

            paddle_lang = paddle_lang_map.get(language, "en")
            self._paddle_reader = PaddleOCR(
                use_angle_cls=True,
                lang=paddle_lang,
                use_gpu=self._gpu_available,
                show_log=False,
            )
            logger.info(f"Initialized PaddleOCR reader for: {language}")
            return self._paddle_reader
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            return None

    def process_page(
        self,
        image_path: str,
        language: str | None = None,
    ) -> OCRServiceResult:
        """
        Process a page image through OCR.

        Args:
            image_path: Path to the image file
            language: ISO 639-1 language code (e.g., 'ta', 'hi').
                      If None, attempts auto-detection.

        Returns:
            OCRServiceResult with text, confidence, blocks, bounding_boxes
        """
        start_time = time.time()

        # Validate image exists
        img_path = Path(image_path)
        if not img_path.exists():
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"Image not found: {image_path}",
            )

        # Determine OCR provider based on language
        from services.language_config import get_language_registry
        registry = get_language_registry()

        if language and not registry.is_supported(language):
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="unsupported",
                error=f"OCR model does not support this language: {language}",
            )

        # Select provider
        provider = registry.get_ocr_provider(language) if language else "easyocr"
        effective_language = language or "en"

        try:
            if provider == "paddleocr":
                return self._ocr_paddle(image_path, effective_language, start_time)
            else:
                return self._ocr_easyocr(image_path, effective_language, start_time)
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"OCR failed for {image_path}: {e}")
            return OCRServiceResult(
                text="", language_hint=effective_language, confidence=None,
                processing_time=elapsed, engine=provider,
                status="error", error=str(e),
            )

    def _ocr_easyocr(self, image_path: str, language: str, start_time: float) -> OCRServiceResult:
        """Perform OCR using EasyOCR."""
        reader = self._get_easyocr_reader(language)
        if reader is None:
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"EasyOCR reader not available for: {language}",
            )

        results = reader.readtext(image_path)
        elapsed = round(time.time() - start_time, 2)

        blocks = []
        bounding_boxes = []
        texts = []
        confidences = []

        for idx, (bbox, text, conf) in enumerate(results):
            texts.append(text)
            confidences.append(conf)

            # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            bb = [[int(pt[0]), int(pt[1])] for pt in bbox]
            blocks.append(OCRBlock(
                text=text,
                confidence=round(float(conf) * 100, 2),
                bounding_box=bb,
                line_num=idx,
            ))
            bounding_boxes.append({
                "points": bb,
                "text": text,
                "confidence": round(float(conf) * 100, 2),
            })

        full_text = "\n".join(texts)
        avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else None

        return OCRServiceResult(
            text=full_text,
            language_hint=language,
            confidence=avg_conf,
            blocks=blocks,
            bounding_boxes=bounding_boxes,
            processing_time=elapsed,
            engine="easyocr",
        )

    def _ocr_paddle(self, image_path: str, language: str, start_time: float) -> OCRServiceResult:
        """Perform OCR using PaddleOCR (fallback for Gujarati, Malayalam)."""
        reader = self._get_paddle_reader(language)
        if reader is None:
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"PaddleOCR reader not available for: {language}",
            )

        result = reader.ocr(image_path, cls=True)
        elapsed = round(time.time() - start_time, 2)

        blocks = []
        bounding_boxes = []
        texts = []
        confidences = []

        if result and result[0]:
            for idx, line in enumerate(result[0]):
                bbox_pts, (text, conf) = line
                texts.append(text)
                confidences.append(conf)

                bb = [[int(p[0]), int(p[1])] for p in bbox_pts]
                blocks.append(OCRBlock(
                    text=text,
                    confidence=round(float(conf) * 100, 2),
                    bounding_box=bb,
                    line_num=idx,
                ))
                bounding_boxes.append({
                    "points": bb,
                    "text": text,
                    "confidence": round(float(conf) * 100, 2),
                })

        full_text = "\n".join(texts)
        avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else None

        return OCRServiceResult(
            text=full_text,
            language_hint=language,
            confidence=avg_conf,
            blocks=blocks,
            bounding_boxes=bounding_boxes,
            processing_time=elapsed,
            engine="paddleocr",
        )

    def get_supported_languages(self) -> Dict[str, dict]:
        """Return which languages are supported and by which engine."""
        from services.language_config import get_language_registry
        registry = get_language_registry()

        result = {}
        for lang in registry.get_enabled():
            result[lang.code] = {
                "name": lang.name,
                "script": lang.script,
                "ocr_provider": lang.ocr_provider,
                "easyocr_supported": lang.easyocr_code is not None,
                "note": lang.ocr_note,
            }
        return result
