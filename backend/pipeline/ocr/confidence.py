"""
OCR Confidence Calculator.

Calculates OCR quality from multiple measurable signals:
- Engine confidence
- Recognized character ratio
- Language probability
- Dictionary/lexicon match
- Text coherence
- Layout consistency
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Unicode ranges for script detection
SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),   # Hindi, Marathi, Sanskrit
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "bengali": (0x0980, 0x09FF),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
    "gujarati": (0x0A80, 0x0AFF),
    "latin": (0x0041, 0x007A),
}


def calculate_ocr_confidence(result, expected_language: str = None) -> float:
    """
    Calculate comprehensive OCR confidence from multiple signals.
    Returns normalized score 0-100.
    """
    from pipeline.ocr.base import OCRResult

    if not isinstance(result, OCRResult):
        return 0.0

    text = result.full_text
    if not text or len(text.strip()) < 5:
        return 0.0

    scores = {}

    # 1. Engine confidence (40% weight)
    engine_conf = result.confidence
    scores["engine_confidence"] = min(engine_conf, 100)

    # 2. Character validity (20% weight)
    char_score = _calculate_char_validity(text, expected_language)
    scores["char_validity"] = char_score

    # 3. Text coherence (15% weight)
    coherence = _calculate_coherence(text)
    scores["coherence"] = coherence

    # 4. Word density (15% weight)
    density = _calculate_word_density(text)
    scores["word_density"] = density

    # 5. Script consistency (10% weight)
    script_score = _calculate_script_consistency(text, expected_language)
    scores["script_consistency"] = script_score

    # Weighted combination
    final = (
        scores["engine_confidence"] * 0.40 +
        scores["char_validity"] * 0.20 +
        scores["coherence"] * 0.15 +
        scores["word_density"] * 0.15 +
        scores["script_consistency"] * 0.10
    )

    return round(min(max(final, 0), 100), 1)


def _calculate_char_validity(text: str, language: str = None) -> float:
    """Score based on ratio of valid characters."""
    if not text:
        return 0.0

    # If text has no alphabetic characters, it is noise/symbols
    if not any(c.isalpha() for c in text):
        return 10.0

    total = len(text)
    valid = 0

    for char in text:
        cp = ord(char)
        # Whitespace and punctuation are always valid
        if char.isspace() or char in '.,;:!?-()[]{}"\'/\\@#$%&*+=<>0123456789':
            valid += 1
        # Latin characters
        elif 0x0041 <= cp <= 0x007A or 0x00C0 <= cp <= 0x024F:
            valid += 1
        # Devanagari
        elif 0x0900 <= cp <= 0x097F:
            valid += 1
        # Tamil
        elif 0x0B80 <= cp <= 0x0BFF:
            valid += 1
        # Other Indian scripts
        elif 0x0980 <= cp <= 0x0CFF or 0x0D00 <= cp <= 0x0D7F:
            valid += 1
        # Common Unicode
        elif cp < 0xFFFD:
            valid += 0.5

    ratio = valid / max(total, 1)
    return ratio * 100


def _calculate_coherence(text: str) -> float:
    """Score text coherence based on word length and spacing patterns."""
    words = text.split()
    if len(words) < 3:
        return 30.0

    # Average word length (good OCR produces reasonable word lengths)
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 1.5 or avg_len > 20:
        length_score = 30
    elif 3 <= avg_len <= 10:
        length_score = 90
    else:
        length_score = 60

    # Ratio of "garbage" words (single chars, very long)
    garbage = sum(1 for w in words if len(w) == 1 and not w.isdigit()) + \
              sum(1 for w in words if len(w) > 25)
    garbage_ratio = garbage / len(words)
    garbage_score = max(0, 100 - garbage_ratio * 200)

    return (length_score * 0.5 + garbage_score * 0.5)


def _calculate_word_density(text: str) -> float:
    """Score based on word count and text length ratio."""
    words = text.split()
    if len(words) < 2:
        return 20.0

    # Good OCR produces reasonable density
    total_chars = len(text)
    chars_per_word = total_chars / max(len(words), 1)

    if 3 <= chars_per_word <= 12:
        return 90.0
    elif chars_per_word < 3:
        return 50.0
    else:
        return 40.0


def _calculate_script_consistency(text: str, expected_language: str = None) -> float:
    """Score based on how consistent the detected script is."""
    if not text or not expected_language:
        return 70.0  # Neutral if we don't know what to expect

    script_counts = {}
    total = 0

    for char in text:
        if char.isspace() or not char.isalpha():
            continue
        total += 1
        cp = ord(char)
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= cp <= end:
                script_counts[script] = script_counts.get(script, 0) + 1
                break

    if total == 0:
        return 50.0

    # Expected script mapping
    expected_script = {
        "hi": "devanagari",
        "ta": "tamil",
        "te": "telugu",
        "bn": "bengali",
        "kn": "kannada",
        "ml": "malayalam",
        "en": "latin",
        "mr": "devanagari",
    }.get(expected_language)

    if not expected_script:
        return 70.0

    # Consistency = ratio of expected script chars
    expected_count = script_counts.get(expected_script, 0)
    consistency = expected_count / max(total, 1)

    return consistency * 100
