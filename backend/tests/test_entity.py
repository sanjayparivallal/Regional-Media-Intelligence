"""Unit tests for entity extraction."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.entity.extractor import EntityExtractor, DetectedEntity


def test_entity_extraction_gazetteers():
    extractor = EntityExtractor()
    text = "The RBI issued new directives regarding PayU and Paytm operations."
    entities = extractor.extract(text, language="en")
    assert len(entities) >= 2
    entity_texts = [e.text for e in entities]
    assert any("RBI" in t for t in entity_texts)
    assert any("PayU" in t or "Paytm" in t for t in entity_texts)

    rbi_entity = next(e for e in entities if "RBI" in e.text)
    assert rbi_entity.entity_type == "REGULATOR"
    assert rbi_entity.confidence >= 0.90


def test_entity_extraction_patterns():
    extractor = EntityExtractor()
    text = "State Bank has revised transaction security policies."
    entities = extractor.extract(text, language="en")
    assert any("State Bank" in e.text for e in entities)
