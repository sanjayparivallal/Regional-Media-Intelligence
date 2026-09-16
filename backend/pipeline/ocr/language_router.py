"""
OCR Language Router.

Detects script from image or partial OCR to select the correct OCR language model.
Implements multi-language fallback when script detection is uncertain.
"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Unicode script ranges for routing
SCRIPT_DETECTORS = {
    "devanagari": {"range": (0x0900, 0x097F), "languages": ["hi", "mr"]},
    "tamil": {"range": (0x0B80, 0x0BFF), "languages": ["ta"]},
    "telugu": {"range": (0x0C00, 0x0C7F), "languages": ["te"]},
    "bengali": {"range": (0x0980, 0x09FF), "languages": ["bn"]},
    "kannada": {"range": (0x0C80, 0x0CFF), "languages": ["kn"]},
    "malayalam": {"range": (0x0D00, 0x0D7F), "languages": ["ml"]},
    "latin": {"range": (0x0041, 0x007A), "languages": ["en"]},
}


def detect_script_from_text(text: str) -> List[Tuple[str, float]]:
    """
    Detect scripts present in text using Unicode ranges.
    Returns sorted list of (script, confidence) tuples.
    """
    if not text or len(text.strip()) < 5:
        return [("unknown", 0.0)]

    script_counts = {}
    total_alpha = 0

    for char in text:
        if not char.isalpha() and not char.isdigit():
            continue
        total_alpha += 1
        cp = ord(char)

        for script_name, info in SCRIPT_DETECTORS.items():
            start, end = info["range"]
            if start <= cp <= end:
                script_counts[script_name] = script_counts.get(script_name, 0) + 1
                break

    if total_alpha == 0:
        return [("unknown", 0.0)]

    # Calculate proportions
    results = []
    for script, count in script_counts.items():
        confidence = count / total_alpha
        results.append((script, round(confidence * 100, 1)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results if results else [("unknown", 0.0)]


def route_ocr_language(
    text: str = None,
    default_language: str = None,
) -> List[str]:
    """
    Determine which OCR language(s) to use.

    Returns ordered list of language codes to try.
    If uncertain, returns multiple languages for trial-and-error.
    """
    if default_language:
        return [default_language]

    if not text:
        # No text to analyze — try common languages
        return ["hi", "ta", "en"]

    scripts = detect_script_from_text(text)

    if not scripts or scripts[0][0] == "unknown":
        return ["hi", "ta", "en"]

    top_script, top_conf = scripts[0]

    # High confidence → single language
    if top_conf > 70:
        langs = SCRIPT_DETECTORS.get(top_script, {}).get("languages", ["en"])
        return langs

    # Medium confidence → try top and fallbacks
    languages = []
    for script, conf in scripts[:3]:
        for lang in SCRIPT_DETECTORS.get(script, {}).get("languages", []):
            if lang not in languages:
                languages.append(lang)

    if not languages:
        languages = ["hi", "ta", "en"]

    return languages


def get_language_for_script(script: str) -> str:
    """Get primary language code for a detected script."""
    mapping = {
        "devanagari": "hi",
        "tamil": "ta",
        "telugu": "te",
        "bengali": "bn",
        "kannada": "kn",
        "malayalam": "ml",
        "latin": "en",
    }
    return mapping.get(script, "en")
