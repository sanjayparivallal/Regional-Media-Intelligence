"""
EasyOCR Provider.

Alternative OCR engine with good multilingual support.
"""

import logging
import time
import numpy as np

from pipeline.ocr.base import OCRProvider, OCRResult, OCRBox

logger = logging.getLogger(__name__)

LANG_MAP = {
    "en": ["en"],
    "hi": ["hi", "en"],
    "ta": ["ta", "en"],
    "te": ["te", "en"],
    "mr": ["mr", "en"],
    "bn": ["bn", "en"],
    "kn": ["kn", "en"],
    "multi": ["en", "hi", "ta"],
}


class EasyOCRProvider(OCRProvider):
    """EasyOCR provider — alternative OCR engine."""

    def __init__(self):
        self._readers = {}

    @property
    def name(self) -> str:
        return "easyocr"

    def is_available(self) -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False

    def _get_reader(self, language: str):
        lang_codes = LANG_MAP.get(language, ["en"])
        key = tuple(lang_codes)
        if key not in self._readers:
            try:
                import easyocr
                gpu = False
                try:
                    import torch
                    gpu = torch.cuda.is_available()
                except ImportError:
                    pass
                self._readers[key] = easyocr.Reader(list(lang_codes), gpu=gpu)
                logger.info(f"Initialized EasyOCR reader for: {lang_codes}")
            except Exception as e:
                logger.error(f"Failed to init EasyOCR: {e}")
                return None
        return self._readers[key]

    def ocr(self, image: np.ndarray, language: str = "en") -> OCRResult:
        start = time.time()

        reader = self._get_reader(language)
        if reader is None:
            return OCRResult(text="", confidence=0.0, engine=self.name, language=language)

        try:
            import cv2
            h, w = image.shape[:2]
            max_dim = max(h, w)
            scale = 1.0
            if max_dim > 1600:
                scale = 1600.0 / max_dim
                new_w = int(w * scale)
                new_h = int(h * scale)
                proc_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                proc_image = image

            results = reader.readtext(proc_image)

            boxes = []
            confidences = []
            texts = []

            for idx, (bbox, text, conf) in enumerate(results):
                # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                xs = [p[0] / scale for p in bbox]
                ys = [p[1] / scale for p in bbox]
                x = min(xs)
                y = min(ys)
                w_box = max(xs) - x
                h_box = max(ys) - y

                box = OCRBox(
                    x=int(x), y=int(y), width=int(w_box), height=int(h_box),
                    text=text, confidence=conf * 100,
                    line_num=idx, font_size_estimate=int(h_box),
                )
                boxes.append(box)
                confidences.append(conf * 100)
                texts.append(text)

            full_text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            elapsed = int((time.time() - start) * 1000)

            return OCRResult(
                text=full_text, boxes=boxes, confidence=avg_conf,
                word_count=len(texts), engine=self.name,
                language=language, processing_time_ms=elapsed,
            )

        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return OCRResult(text="", confidence=0.0, engine=self.name, language=language)
