"""
Entity Protector for Translation.

Protects named entities (brand names, people, locations, etc.)
from being modified during translation.
"""

import re
import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)


def protect_entities(
    text: str,
    entities: List[str],
) -> Tuple[str, Dict[str, str]]:
    """
    Replace named entities with placeholders before translation.
    Returns modified text and placeholder mapping.

    Example:
        Input:  "PayU மீது RBI நடவடிக்கை"
        Output: ("__ENT_0__ மீது __ENT_1__ நடவடிக்கை", {"__ENT_0__": "PayU", "__ENT_1__": "RBI"})
    """
    if not entities:
        return text, {}

    placeholders = {}
    protected_text = text

    # Sort by length (longer first) to avoid partial replacements
    sorted_entities = sorted(set(entities), key=len, reverse=True)

    for i, entity in enumerate(sorted_entities):
        placeholder = f"__ENT_{i}__"
        if entity in protected_text:
            protected_text = protected_text.replace(entity, placeholder)
            placeholders[placeholder] = entity

    return protected_text, placeholders


def restore_entities(
    translated_text: str,
    placeholders: Dict[str, str],
) -> str:
    """
    Restore original entities in translated text.
    Handles cases where the model may have slightly modified placeholders.
    """
    if not placeholders:
        return translated_text

    result = translated_text

    for placeholder, entity in placeholders.items():
        # Exact replacement
        result = result.replace(placeholder, entity)

        # Handle common model modifications to placeholders
        # Models sometimes add spaces or change underscores
        variations = [
            placeholder.replace("__", " __ "),
            placeholder.replace("__", " _ _ "),
            placeholder.replace("_", " "),
            placeholder.lower(),
        ]
        for var in variations:
            result = result.replace(var, entity)

    return result


def extract_potential_entities(text: str) -> List[str]:
    """
    Extract potential entities from text using heuristics.
    Useful when NER hasn't run yet (pre-translation).
    """
    entities = []

    # Capitalized words (English entities in non-English text)
    caps_pattern = re.compile(r'\b[A-Z][a-zA-Z]{2,}\b')
    entities.extend(caps_pattern.findall(text))

    # All-caps abbreviations
    abbrev_pattern = re.compile(r'\b[A-Z]{2,6}\b')
    entities.extend(abbrev_pattern.findall(text))

    # Numbers with context (dates, amounts)
    number_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
    entities.extend(number_pattern.findall(text))

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            unique.append(e)

    return unique
