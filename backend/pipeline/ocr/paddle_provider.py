"""
PaddleOCR Provider.

Primary OCR engine with excellent multilingual support.
Supports Hindi, Tamil, and other Indian languages.
"""

import logging
import time
from typing import List
import numpy as np

from pipeline.ocr.base import OCRProvider, OCRResult, OCRBox

logger = logging.getLogger(__name__)

LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "mr": "mr",
    "bn": "bn",
    "kn": "kn",
    "ml": "ml",
    "multi": "en",
}


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR provider — primary OCR engine."""

    def __init__(self):
        self._engines = {}

    @property
    def name(self) -> str:
        return "paddleocr"

    def is_available(self) -> bool:
        try:
            from paddleocr import PaddleOCR
            return True
        except ImportError:
            return False

    def _get_engine(self, language: str):
        """Get or create a PaddleOCR engine for the given language."""
        lang_code = LANG_MAP.get(language, "en")
        if lang_code not in self._engines:
            try:
                from paddleocr import PaddleOCR
                self._engines[lang_code] = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang_code,
                    show_log=False,
                    use_gpu=self._check_gpu(),
                )
                logger.info(f"Initialized PaddleOCR engine for language: {lang_code}")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR for {lang_code}: {e}")
                return None
        return self._engines[lang_code]

    def _check_gpu(self) -> bool:
        try:
            import paddle
            return paddle.device.is_compiled_with_cuda()
        except Exception:
            return False

    def ocr(self, image: np.ndarray, language: str = "en") -> OCRResult:
        start = time.time()

        engine = self._get_engine(language)
        if engine is None:
            return OCRResult(
                text="", confidence=0.0, engine=self.name,
                language=language,
                processing_time_ms=int((time.time() - start) * 1000),
            )

        try:
            results = engine.ocr(image, cls=True)

            boxes = []
            confidences = []
            texts = []

            if results and results[0]:
                for idx, line in enumerate(results[0]):
                    bbox_points = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text_info = line[1]     # (text, confidence)

                    text = text_info[0]
                    conf = text_info[1] * 100  # PaddleOCR returns 0-1

                    # Convert polygon to bounding rect
                    xs = [p[0] for p in bbox_points]
                    ys = [p[1] for p in bbox_points]
                    x = min(xs)
                    y = min(ys)
                    w = max(xs) - x
                    h = max(ys) - y

                    box = OCRBox(
                        x=x, y=y, width=w, height=h,
                        text=text, confidence=conf,
                        line_num=idx,
                        font_size_estimate=h,
                    )
                    boxes.append(box)
                    confidences.append(conf)
                    texts.append(text)

            full_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            elapsed = int((time.time() - start) * 1000)

            result = OCRResult(
                text=full_text,
                boxes=boxes,
                confidence=avg_confidence,
                word_count=len(texts),
                engine=self.name,
                language=language,
                processing_time_ms=elapsed,
            )

            logger.info(
                f"PaddleOCR ({language}): {len(texts)} blocks, "
                f"confidence {avg_confidence:.1f}%, {elapsed}ms"
            )
            return result

        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            return OCRResult(
                text="", confidence=0.0, engine=self.name,
                language=language,
                processing_time_ms=int((time.time() - start) * 1000),
            )
