"""Unit tests for layout analysis and article segmentation."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.layout.analyzer import analyze_layout, ExtractedArticle


def test_analyze_layout_clustering():
    boxes = [
        {"text": "Headline: Digital Economy Booms", "x": 50, "y": 100, "width": 400, "height": 40},
        {"text": "The digital payment sector witnessed massive growth.", "x": 50, "y": 150, "width": 400, "height": 20},
        {"text": "Multiple startups joined the ecosystem this month.", "x": 50, "y": 180, "width": 400, "height": 20},
        # Separate article far below
        {"text": "Headline: Weather Alert in Northern States", "x": 50, "y": 600, "width": 400, "height": 40},
        {"text": "Heavy rainfall predicted across Himalayan regions.", "x": 50, "y": 650, "width": 400, "height": 20},
    ]

    articles = analyze_layout(ocr_boxes=boxes, page_width=1000, page_height=1400)
    assert len(articles) >= 1
    assert all(isinstance(a, ExtractedArticle) for a in articles)
    assert any("Digital Economy" in a.full_text for a in articles)


def test_analyze_layout_empty():
    articles = analyze_layout(ocr_boxes=[], page_width=1000, page_height=1400)
    assert articles == []
