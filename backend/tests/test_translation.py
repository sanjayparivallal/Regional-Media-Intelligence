"""Unit tests for fallback translation provider and entity preservation."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.translation.fallback_provider import FallbackTranslationProvider
from pipeline.nlp.translation.base import TranslationResult


def test_fallback_translation_english_pass_through():
    provider = FallbackTranslationProvider()
    res = provider.translate(
        text="Digital payments grow rapidly in rural markets.",
        source_language="en",
        target_language="en",
    )
    assert isinstance(res, TranslationResult)
    assert res.translated_text == "Digital payments grow rapidly in rural markets."
    assert res.confidence == 100.0


def test_fallback_translation_with_protected_entities():
    provider = FallbackTranslationProvider()
    res = provider.translate(
        text="कंपनी ने PayU और RBI के दिशा निर्देशों का पालन किया।",
        source_language="hi",
        target_language="en",
        protected_entities=["PayU", "RBI"],
    )
    assert "PayU" in res.translated_text
    assert "RBI" in res.translated_text
    assert res.source_language == "hi"
    assert res.target_language == "en"
