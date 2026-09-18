"""
Tesseract OCR Provider.

Fallback OCR engine using pytesseract.
Supports Hindi (Devanagari) and Tamil scripts.
"""

import logging
import time
from typing import List
import numpy as np

from pipeline.ocr.base import OCRProvider, OCRResult, OCRBox

logger = logging.getLogger(__name__)

# Tesseract language codes
LANG_MAP = {
    "en": "eng",
    "hi": "hin",
    "ta": "tam",
    "te": "tel",
    "mr": "mar",
    "bn": "ben",
    "kn": "kan",
    "ml": "mal",
    "multi": "eng+hin+tam",
}


class TesseractProvider(OCRProvider):
    """Tesseract OCR provider."""

    @property
    def name(self) -> str:
        return "tesseract"

    def is_available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def ocr(self, image: np.ndarray, language: str = "en") -> OCRResult:
        start = time.time()

        try:
            import pytesseract
            from PIL import Image

            # Convert numpy to PIL (OpenCV loads as BGR, PIL expects RGB)
            if len(image.shape) == 2:
                pil_image = Image.fromarray(image)
            else:
                import cv2
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            lang_code = LANG_MAP.get(language, "eng")

            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(
                pil_image,
                lang=lang_code,
                output_type=pytesseract.Output.DICT,
                config='--psm 3'  # Fully automatic page segmentation
            )

            boxes = []
            confidences = []
            texts = []

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])

                if text and conf > 0:
                    box = OCRBox(
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i],
                        text=text,
                        confidence=max(conf, 0),
                        line_num=data["line_num"][i],
                        block_num=data["block_num"][i],
                        font_size_estimate=data["height"][i],
                    )
                    boxes.append(box)
                    if conf > 0:
                        confidences.append(conf)
                    texts.append(text)

            full_text = " ".join(texts)
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
                f"Tesseract OCR ({lang_code}): {len(texts)} words, "
                f"confidence {avg_confidence:.1f}%, {elapsed}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                language=language,
                processing_time_ms=int((time.time() - start) * 1000),
            )
