"""
PDF Service.

Handles PDF classification, page rendering, and text extraction.
Implements text-PDF-first extraction to skip OCR when possible.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PageRenderResult:
    """Result of rendering a single PDF page."""
    page_number: int
    image_path: str
    has_text_layer: bool
    extracted_text: Optional[str] = None
    text_char_count: int = 0
    width: int = 0
    height: int = 0


@dataclass
class PDFProcessingResult:
    """Result of processing an entire PDF."""
    filename: str
    page_count: int
    document_type: str  # pdf_scanned, pdf_text, pdf_mixed, image
    pages: List[PageRenderResult] = field(default_factory=list)
    processing_time: float = 0.0
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "page_count": self.page_count,
            "document_type": self.document_type,
            "pages": [
                {
                    "page_number": p.page_number,
                    "image_path": p.image_path,
                    "has_text_layer": p.has_text_layer,
                    "extracted_text_length": p.text_char_count,
                    "width": p.width,
                    "height": p.height,
                }
                for p in self.pages
            ],
            "processing_time": self.processing_time,
            "status": self.status,
        }


class PDFService:
    """
    PDF processing service.

    Pipeline:
    1. Classify PDF (scanned vs text vs mixed)
    2. For text pages: extract text directly
    3. For scanned pages: render to image for OCR
    """

    def process_pdf(
        self,
        file_path: str,
        output_dir: str,
        dpi: int = 300,
    ) -> PDFProcessingResult:
        """
        Process a PDF file: classify, render pages, extract text layers.

        Args:
            file_path: Path to the PDF file
            output_dir: Directory to save rendered page images
            dpi: Resolution for page rendering

        Returns:
            PDFProcessingResult with page images and text layers
        """
        start_time = time.time()
        path = Path(file_path)

        if not path.exists():
            return PDFProcessingResult(
                filename=path.name, page_count=0, document_type="unknown",
                status="error", error=f"File not found: {file_path}",
            )

        # Handle image files directly
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tiff', '.tif'):
            elapsed = round(time.time() - start_time, 2)
            return PDFProcessingResult(
                filename=path.name, page_count=1, document_type="image",
                pages=[PageRenderResult(
                    page_number=1, image_path=str(path),
                    has_text_layer=False,
                )],
                processing_time=elapsed,
            )

        try:
            # Step 1: Classify PDF
            from pipeline.ingestion.pdf_classifier import classify_pdf
            classification = classify_pdf(file_path)

            # Step 2: Render pages
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            from pipeline.ingestion.page_renderer import render_pdf_pages
            rendered_pages = render_pdf_pages(file_path, str(out_dir))

            # Step 3: Extract text from text-layer pages
            pages = []
            for rp in rendered_pages:
                page_info = classification.pages[rp.page_number - 1] if rp.page_number <= len(classification.pages) else None
                has_text = page_info.has_text if page_info else False
                extracted_text = None
                text_chars = 0

                if has_text:
                    # Extract text directly from PDF (skip OCR for this page)
                    extracted_text = self._extract_text_layer(file_path, rp.page_number)
                    text_chars = len(extracted_text) if extracted_text else 0

                pages.append(PageRenderResult(
                    page_number=rp.page_number,
                    image_path=rp.image_path,
                    has_text_layer=has_text,
                    extracted_text=extracted_text,
                    text_char_count=text_chars,
                    width=rp.width,
                    height=rp.height,
                ))

            elapsed = round(time.time() - start_time, 2)

            return PDFProcessingResult(
                filename=path.name,
                page_count=classification.page_count,
                document_type=classification.document_type,
                pages=pages,
                processing_time=elapsed,
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"PDF processing failed: {e}")
            return PDFProcessingResult(
                filename=path.name, page_count=0, document_type="unknown",
                processing_time=elapsed, status="error", error=str(e),
            )

    def _extract_text_layer(self, pdf_path: str, page_number: int) -> Optional[str]:
        """Extract embedded text from a PDF page using PyMuPDF."""
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz

            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]
            text = page.get_text().strip()
            doc.close()
            return text if text else None
        except Exception as e:
            logger.warning(f"Text extraction failed for page {page_number}: {e}")
            return None
