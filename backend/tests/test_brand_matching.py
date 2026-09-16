"""Unit tests for brand matching engine."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.entity.brand_matcher import BrandMatcher, BrandMatch


def test_brand_matcher_exact_and_alias():
    matcher = BrandMatcher()
    sample_brands = [
        {
            "id": "b-1",
            "name": "PayU",
            "aliases": ["PayU Finance", "PayU India"],
            "keywords": ["payment gateway", "fintech"],
            "active": True,
        },
        {
            "id": "b-2",
            "name": "Paytm",
            "aliases": ["One97 Communications"],
            "keywords": ["wallet", "upi"],
            "active": True,
        }
    ]
    matcher.load_brands(sample_brands)

    # 1. Exact match
    matches = matcher.match("PayU announced a new partnership today.")
    assert len(matches) == 1
    assert matches[0].brand_name == "PayU"
    assert matches[0].match_type == "exact"
    assert matches[0].confidence >= 0.95

    # 2. Alias match
    matches_alias = matcher.match("One97 Communications issued a statement to the stock exchanges.")
    assert len(matches_alias) == 1
    assert matches_alias[0].brand_name == "Paytm"
    assert matches_alias[0].match_type == "alias"
    assert matches_alias[0].confidence >= 0.90


def test_brand_matcher_context_matching():
    matcher = BrandMatcher()
    sample_brands = [
        {
            "id": "b-1",
            "name": "PayU",
            "aliases": [],
            "keywords": ["payment gateway", "fintech", "digital transaction"],
            "active": True,
        }
    ]
    matcher.load_brands(sample_brands)

    # Text mentions keywords without brand name
    matches = matcher.match("The fintech sector is updating payment gateway protocols for security.")
    assert len(matches) == 1
    assert matches[0].brand_name == "PayU"
    assert matches[0].match_type == "context"
