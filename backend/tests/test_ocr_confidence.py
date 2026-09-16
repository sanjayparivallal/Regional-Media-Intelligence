"""Unit tests for OCR confidence scoring."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ocr.base import OCRResult, OCRBox
from pipeline.ocr.confidence import calculate_ocr_confidence


def test_calculate_ocr_confidence_good_quality():
    boxes = [
        OCRBox(text="Reserve Bank of India", confidence=95.0, x=10, y=10, width=200, height=30),
        OCRBox(text="issues new regulatory notification", confidence=90.0, x=10, y=50, width=300, height=25),
    ]
    ocr_res = OCRResult(
        boxes=boxes,
        text="Reserve Bank of India issues new regulatory notification",
        confidence=92.5,
        engine="test",
        language="en",
    )
    conf = calculate_ocr_confidence(ocr_res, expected_language="en")
    assert conf >= 75.0
    assert 0 <= conf <= 100


def test_calculate_ocr_confidence_gibberish():
    boxes = [
        OCRBox(text="!@ #$ %^ &*", confidence=20.0, x=0, y=0, width=50, height=10),
    ]
    ocr_res = OCRResult(
        boxes=boxes,
        text="!@ #$ %^ &*",
        confidence=20.0,
        engine="test",
        language="en",
    )
    conf = calculate_ocr_confidence(ocr_res, expected_language="en")
    assert conf < 50.0
