"""
Brand Matching Module.

Configurable brand intelligence with exact, alias, fuzzy, and context matching.
Every match includes confidence to prevent false positives.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BrandMatch:
    brand_id: str
    brand_name: str
    matched_text: str
    match_type: str  # exact, alias, fuzzy, context
    confidence: float
    context_snippet: str = ""


class BrandMatcher:
    """
    Configurable brand matching with multiple strategies.
    Uses exact → alias → fuzzy → context matching pipeline.
    """

    def __init__(self):
        self._brands = []  # List of brand dicts

    def load_brands(self, brands: List[dict]):
        """Load brands with aliases and keywords."""
        self._brands = brands
        logger.info(f"Loaded {len(brands)} brands for matching")

    def match(self, text: str, entities: List[str] = None) -> List[BrandMatch]:
        """
        Find all brand matches in text.
        Returns matches with confidence scores.
        """
        if not text or not self._brands:
            return []

        matches = []
        text_lower = text.lower()

        for brand in self._brands:
            if not brand.get("active", True):
                continue

            brand_name = brand["name"]
            brand_id = str(brand.get("id", ""))
            aliases = brand.get("aliases", [])
            keywords = brand.get("keywords", [])
            fuzzy_threshold = brand.get("fuzzy_threshold", 0.85)

            # 1. Exact match
            if brand_name.lower() in text_lower:
                idx = text_lower.find(brand_name.lower())
                snippet = _get_context(text, idx, len(brand_name))
                matches.append(BrandMatch(
                    brand_id=brand_id, brand_name=brand_name,
                    matched_text=brand_name, match_type="exact",
                    confidence=0.98, context_snippet=snippet,
                ))
                continue

            # 2. Alias match
            alias_matched = False
            for alias_info in aliases:
                alias = alias_info if isinstance(alias_info, str) else alias_info.get("alias", "")
                if alias.lower() in text_lower:
                    idx = text_lower.find(alias.lower())
                    snippet = _get_context(text, idx, len(alias))
                    matches.append(BrandMatch(
                        brand_id=brand_id, brand_name=brand_name,
                        matched_text=alias, match_type="alias",
                        confidence=0.92, context_snippet=snippet,
                    ))
                    alias_matched = True
                    break

            if alias_matched:
                continue

            # 3. Fuzzy match
            fuzzy_match = _fuzzy_match(brand_name, text, fuzzy_threshold)
            if fuzzy_match:
                matched_text, score = fuzzy_match
                snippet = _get_context(text, text_lower.find(matched_text.lower()), len(matched_text))
                matches.append(BrandMatch(
                    brand_id=brand_id, brand_name=brand_name,
                    matched_text=matched_text, match_type="fuzzy",
                    confidence=score, context_snippet=snippet,
                ))
                continue

            # 4. Context/keyword match
            if keywords:
                keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
                if keyword_hits >= 2:
                    matches.append(BrandMatch(
                        brand_id=brand_id, brand_name=brand_name,
                        matched_text=", ".join(kw for kw in keywords if kw.lower() in text_lower),
                        match_type="context",
                        confidence=min(0.7, 0.3 + keyword_hits * 0.15),
                        context_snippet=text[:200],
                    ))

        return matches


def _fuzzy_match(
    brand_name: str, text: str, threshold: float = 0.85
) -> Optional[Tuple[str, float]]:
    """Fuzzy match a brand name against text using rapidfuzz."""
    try:
        from rapidfuzz import fuzz, process

        # Extract candidate words/phrases from text
        words = text.split()
        # Check single words and bigrams
        candidates = list(set(words))
        for i in range(len(words) - 1):
            candidates.append(f"{words[i]} {words[i + 1]}")

        result = process.extractOne(
            brand_name, candidates,
            scorer=fuzz.ratio,
            score_cutoff=threshold * 100,
        )

        if result:
            return result[0], result[1] / 100

    except ImportError:
        # rapidfuzz not available — skip fuzzy matching
        pass
    except Exception as e:
        logger.warning(f"Fuzzy match error: {e}")

    return None


def _get_context(text: str, pos: int, length: int, window: int = 80) -> str:
    """Extract context snippet around a match position."""
    if pos < 0:
        return text[:200]
    start = max(0, pos - window)
    end = min(len(text), pos + length + window)
    return text[start:end]
