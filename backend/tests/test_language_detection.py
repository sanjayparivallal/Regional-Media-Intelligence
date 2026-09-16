"""Unit tests for language and script detection."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp.language_detector import detect_language, detect_language_multi, LanguageResult


def test_detect_language_hindi():
    hindi_text = "भारतीय रिजर्व बैंक ने नए नियमों की घोषणा की है।"
    res = detect_language(hindi_text)
    assert isinstance(res, LanguageResult)
    assert res.language == "hi"
    assert res.script == "devanagari"
    assert res.confidence > 70.0


def test_detect_language_tamil():
    tamil_text = "ரிசர்வ் வங்கி புதிய விதிமுறைகளை அறிவித்துள்ளது."
    res = detect_language(tamil_text)
    assert res.language == "ta"
    assert res.script == "tamil"
    assert res.confidence > 70.0


def test_detect_language_english():
    english_text = "Reserve Bank of India has announced new guidelines for digital payments."
    res = detect_language(english_text)
    assert res.language in ("en", "latin")
    assert res.confidence > 50.0


def test_detect_language_empty():
    res = detect_language("")
    assert res.language == "unknown"
    assert res.confidence == 0.0
