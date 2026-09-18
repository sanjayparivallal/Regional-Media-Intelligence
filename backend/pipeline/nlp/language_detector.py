"""
Language Detection Module.

Combines Unicode script detection + character distribution + langdetect library
for robust language identification of Indian languages.
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Unicode block ranges for Indian scripts
SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "bengali": (0x0980, 0x09FF),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
    "gujarati": (0x0A80, 0x0AFF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "arabic": (0x0600, 0x06FF),
    "latin": (0x0041, 0x007A),
}

SCRIPT_TO_LANG = {
    "devanagari": "hi",
    "tamil": "ta",
    "telugu": "te",
    "bengali": "bn",
    "kannada": "kn",
    "malayalam": "ml",
    "gujarati": "gu",
    "gurmukhi": "pa",
    "arabic": "ur",
    "latin": "en",
}


@dataclass
class LanguageResult:
    language: str
    confidence: float
    script: str
    method: str  # unicode, langdetect, combined


def detect_language(text: str) -> LanguageResult:
    """
    Detect language using multiple methods and combine results.
    Priority: Unicode script detection → langdetect library → combined.
    """
    if not text or len(text.strip()) < 3:
        return LanguageResult("unknown", 0.0, "unknown", "none")

    # Method 1: Unicode script detection
    script_result = _detect_by_unicode(text)

    # Method 2: langdetect library
    lib_result = _detect_by_library(text)

    # Combine results
    if script_result.confidence > 80:
        # Strong script signal — trust it
        return script_result
    elif lib_result.confidence > 70 and script_result.language == "en":
        # Library has good confidence and script is Latin
        return lib_result
    elif script_result.confidence > 50:
        # Medium script signal — prefer script detection for Indian languages
        return script_result
    elif lib_result.confidence > 50:
        return lib_result
    else:
        # Low confidence on both — return best guess
        if script_result.confidence >= lib_result.confidence:
            return script_result
        return lib_result


def detect_language_multi(text: str) -> List[LanguageResult]:
    """Detect all languages present in text (for multilingual content)."""
    results = []

    # Script analysis
    script_counts = _count_scripts(text)
    total = sum(script_counts.values())

    for script, count in sorted(script_counts.items(), key=lambda x: x[1], reverse=True):
        if count > 0 and total > 0:
            conf = (count / total) * 100
            lang = SCRIPT_TO_LANG.get(script, "unknown")
            results.append(LanguageResult(lang, conf, script, "unicode"))

    if not results:
        results.append(detect_language(text))

    return results


def _detect_by_unicode(text: str) -> LanguageResult:
    """Detect language by analyzing Unicode character distribution."""
    script_counts = _count_scripts(text)
    total = sum(script_counts.values())

    if total == 0:
        return LanguageResult("unknown", 0.0, "unknown", "unicode")

    # Find dominant script
    top_script = max(script_counts, key=script_counts.get)
    top_count = script_counts[top_script]
    confidence = (top_count / total) * 100

    language = SCRIPT_TO_LANG.get(top_script, "unknown")

    return LanguageResult(language, round(confidence, 1), top_script, "unicode")


def _detect_by_library(text: str) -> LanguageResult:
    """Detect language using the langdetect library."""
    try:
        from langdetect import detect_langs
        results = detect_langs(text)

        if results:
            top = results[0]
            # Map langdetect codes to our codes
            lang_map = {"hi": "hi", "ta": "ta", "te": "te", "bn": "bn",
                        "en": "en", "mr": "mr", "kn": "kn", "ml": "ml"}
            lang = lang_map.get(top.lang, top.lang)
            conf = top.prob * 100

            return LanguageResult(lang, round(conf, 1), "detected", "langdetect")
    except Exception as e:
        logger.warning(f"langdetect failed: {e}")

    return LanguageResult("unknown", 0.0, "unknown", "langdetect")


def _count_scripts(text: str) -> dict:
    """Count characters belonging to each Unicode script."""
    counts = {script: 0 for script in SCRIPT_RANGES}

    for char in text:
        if not char.isalpha():
            continue
        cp = ord(char)
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= cp <= end:
                counts[script] += 1
                break

    return {k: v for k, v in counts.items() if v > 0}
