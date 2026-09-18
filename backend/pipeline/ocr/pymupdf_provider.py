"""
PyMuPDF Direct Text & Bounding Box Extractor.

Extracts text layer, words, and exact pixel bounding boxes directly
from PDF pages with high precision and zero rendering overhead.
"""

import logging
import time
from typing import List, Optional
import pymupdf as fitz

from pipeline.ocr.base import OCRProvider, OCRResult, OCRBox

logger = logging.getLogger(__name__)


class PyMuPDFProvider(OCRProvider):
    """PyMuPDF direct text and bounding box extractor."""

    @property
    def name(self) -> str:
        return "pymupdf_native"

    def is_available(self) -> bool:
        return True

    def extract_pdf_page(
        self,
        pdf_path: str,
        page_number: int,
        target_width: float,
        target_height: float,
    ) -> OCRResult:
        """Extract words and bounding boxes scaled to target image width & height."""
        start = time.time()
        try:
            doc = fitz.open(pdf_path)
            if page_number < 1 or page_number > len(doc):
                doc.close()
                return OCRResult(text="", confidence=0.0, engine=self.name)

            page = doc[page_number - 1]
            rect = page.rect
            pdf_w = rect.width or 1.0
            pdf_h = rect.height or 1.0

            scale_x = target_width / pdf_w if target_width > 0 else 1.0
            scale_y = target_height / pdf_h if target_height > 0 else 1.0

            # Extract word bounding boxes: (x0, y0, x1, y1, word, block_no, line_no, word_no)
            words = page.get_text("words")
            doc.close()

            if not words:
                return OCRResult(text="", confidence=0.0, engine=self.name)

            boxes: List[OCRBox] = []
            word_texts = []

            for w in words:
                x0, y0, x1, y1, text, block_no, line_no, _ = w
                clean_text = text.strip()
                if not clean_text:
                    continue

                bx = x0 * scale_x
                by = y0 * scale_y
                bw = (x1 - x0) * scale_x
                bh = (y1 - y0) * scale_y

                boxes.append(OCRBox(
                    x=bx,
                    y=by,
                    width=bw,
                    height=bh,
                    text=clean_text,
                    confidence=98.0,
                    line_num=line_no,
                    block_num=block_no,
                    font_size_estimate=bh,
                ))
                word_texts.append(clean_text)

            full_text = " ".join(word_texts)
            elapsed = int((time.time() - start) * 1000)

            return OCRResult(
                text=full_text,
                boxes=boxes,
                confidence=98.0,
                word_count=len(word_texts),
                engine=self.name,
                language="auto",
                processing_time_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"PyMuPDF native extraction failed: {e}")
            return OCRResult(text="", confidence=0.0, engine=self.name)

    def ocr(self, image, language: str = "en") -> OCRResult:
        return OCRResult(text="", confidence=0.0, engine=self.name)
