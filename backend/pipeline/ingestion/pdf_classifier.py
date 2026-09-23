"""
PDF Classification Module.

Determines:
- PDF page count
- Page dimensions
- Whether text layer exists
- Image resolution
- Whether it's image-only vs text-based
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    page_number: int
    width: float
    height: float
    has_text: bool
    text_char_count: int
    has_images: bool
    image_count: int


@dataclass
class PDFClassification:
    page_count: int
    document_type: str  # pdf_scanned, pdf_text, pdf_mixed, image
    has_text_layer: bool
    pages: List[PageInfo] = field(default_factory=list)
    text_pages: int = 0
    image_pages: int = 0
    avg_text_density: float = 0.0


def classify_pdf(file_path: str) -> PDFClassification:
    """
    Inspect a PDF to determine its type and characteristics.
    Uses PyMuPDF for fast PDF inspection.
    """
    path = Path(file_path)

    # Handle image files directly
    if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tiff', '.tif'):
        return PDFClassification(
            page_count=1,
            document_type="image",
            has_text_layer=False,
            pages=[PageInfo(
                page_number=1, width=0, height=0,
                has_text=False, text_char_count=0,
                has_images=True, image_count=1,
            )],
            image_pages=1,
        )

    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open(file_path)
        pages = []
        text_pages = 0
        image_pages = 0
        total_chars = 0

        for i, page in enumerate(doc):
            text = page.get_text()
            char_count = len(text.strip())
            images = page.get_images()

            has_text = char_count > 200  # >200 chars = genuine text layer; watermarks/metadata are typically <60 chars
            has_images = len(images) > 0

            pages.append(PageInfo(
                page_number=i + 1,
                width=page.rect.width,
                height=page.rect.height,
                has_text=has_text,
                text_char_count=char_count,
                has_images=has_images,
                image_count=len(images),
            ))

            if has_text:
                text_pages += 1
            else:
                image_pages += 1
            total_chars += char_count

        doc.close()

        # Classify
        page_count = len(pages)
        avg_density = total_chars / max(page_count, 1)

        if text_pages == 0:
            doc_type = "pdf_scanned"
            has_text_layer = False
        elif image_pages == 0:
            doc_type = "pdf_text"
            has_text_layer = True
        else:
            doc_type = "pdf_mixed"
            has_text_layer = True

        result = PDFClassification(
            page_count=page_count,
            document_type=doc_type,
            has_text_layer=has_text_layer,
            pages=pages,
            text_pages=text_pages,
            image_pages=image_pages,
            avg_text_density=avg_density,
        )

        logger.info(
            f"PDF classified: {doc_type}, {page_count} pages, "
            f"{text_pages} text / {image_pages} image"
        )
        return result

    except Exception as e:
        logger.error(f"PDF classification failed: {e}")
        return PDFClassification(
            page_count=0,
            document_type="unknown",
            has_text_layer=False,
        )
