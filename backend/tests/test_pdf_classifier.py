"""Unit tests for PDF and image classification."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingestion.pdf_classifier import classify_pdf, PDFClassification


def test_classify_image_file():
    """Verify that image file path is classified as image type."""
    res = classify_pdf("sample_newspaper_page.jpg")
    assert isinstance(res, PDFClassification)
    assert res.document_type == "image"
    assert res.page_count == 1
    assert res.has_text_layer is False


def test_classify_png_file():
    res = classify_pdf("scanned_article.png")
    assert res.document_type == "image"
    assert res.image_pages == 1
