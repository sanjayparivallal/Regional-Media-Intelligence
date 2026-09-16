"""
Hybrid Named Entity Extractor.

Combines spaCy NER + regex gazetteers + heuristic patterns
for robust entity extraction from both original and translated text.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DetectedEntity:
    text: str
    entity_type: str  # ORGANIZATION, PERSON, LOCATION, PRODUCT, REGULATOR, BRAND
    confidence: float
    start: int = 0
    end: int = 0
    source: str = "unknown"  # spacy, regex, gazetteer
    normalized: Optional[str] = None


# Gazetteers for Indian entities
REGULATORS = [
    "RBI", "Reserve Bank of India", "SEBI", "Securities and Exchange Board",
    "IRDAI", "Insurance Regulatory", "TRAI", "NPCI", "PFRDA",
    "Ministry of Finance", "Ministry of Commerce", "Finance Ministry",
    "Enforcement Directorate", "ED", "CBI", "Income Tax Department",
    "Competition Commission", "CCI", "NCLT", "Consumer Forum",
    "National Consumer Disputes", "NCDRC", "Supreme Court", "High Court",
]

ORGANIZATIONS = [
    "PayU", "Paytm", "PhonePe", "Google Pay", "Amazon Pay",
    "Razorpay", "CRED", "BharatPe", "MobiKwik", "FreeCharge",
    "HDFC Bank", "ICICI Bank", "State Bank", "SBI", "Axis Bank",
    "Kotak Mahindra", "Yes Bank", "PNB", "Bank of Baroda",
    "Reliance", "Tata", "Infosys", "TCS", "Wipro", "HCL",
    "Adani", "Byju's", "Ola", "Swiggy", "Zomato", "Flipkart",
    "Airtel", "Jio", "Vodafone Idea", "Vi",
]


class EntityExtractor:
    """Hybrid entity extraction using multiple methods."""

    def __init__(self):
        self._spacy_model = None
        self._spacy_loaded = False

    def _load_spacy(self):
        """Lazy-load spaCy model."""
        if self._spacy_loaded:
            return
        self._spacy_loaded = True
        try:
            import spacy
            from pathlib import Path
            from config import get_settings
            settings = get_settings()
            local_path = Path(settings.ner_model_path) if settings.ner_model_path else Path(__file__).resolve().parent.parent.parent.parent / "model_assets" / "spacy_en"
            if local_path.exists():
                self._spacy_model = spacy.load(str(local_path))
                logger.info(f"Loaded spaCy from local assets: {local_path}")
            else:
                self._spacy_model = spacy.load(settings.spacy_model)
                logger.info(f"Loaded spaCy {settings.spacy_model}")
        except Exception as e:
            logger.warning(f"spaCy not available: {e}")
            self._spacy_model = None

    def extract(self, text: str, language: str = "en") -> List[DetectedEntity]:
        """
        Extract entities using all available methods.
        Deduplicates and merges results.
        """
        if not text or len(text.strip()) < 3:
            return []

        start = time.time()
        entities = []

        # Method 1: spaCy NER (for English/translated text)
        spacy_entities = self._extract_spacy(text)
        entities.extend(spacy_entities)

        # Method 2: Regex gazetteers
        gazetteer_entities = self._extract_gazetteers(text)
        entities.extend(gazetteer_entities)

        # Method 3: Pattern-based extraction
        pattern_entities = self._extract_patterns(text)
        entities.extend(pattern_entities)

        # Deduplicate
        entities = self._deduplicate(entities)

        elapsed = int((time.time() - start) * 1000)
        logger.info(f"Extracted {len(entities)} entities in {elapsed}ms")

        return entities

    def _extract_spacy(self, text: str) -> List[DetectedEntity]:
        """Extract entities using spaCy."""
        self._load_spacy()
        if not self._spacy_model:
            return []

        try:
            doc = self._spacy_model(text[:10000])  # Limit text length
            entities = []

            type_map = {
                "ORG": "ORGANIZATION",
                "PERSON": "PERSON",
                "GPE": "LOCATION",
                "LOC": "LOCATION",
                "PRODUCT": "PRODUCT",
                "MONEY": "FINANCIAL",
                "DATE": "DATE",
            }

            for ent in doc.ents:
                mapped_type = type_map.get(ent.label_, ent.label_)
                entities.append(DetectedEntity(
                    text=ent.text,
                    entity_type=mapped_type,
                    confidence=0.8,
                    start=ent.start_char,
                    end=ent.end_char,
                    source="spacy",
                ))

            return entities
        except Exception as e:
            logger.warning(f"spaCy extraction failed: {e}")
            return []

    def _extract_gazetteers(self, text: str) -> List[DetectedEntity]:
        """Extract entities using predefined gazetteers."""
        entities = []
        text_lower = text.lower()

        # Check regulators
        for reg in REGULATORS:
            if reg.lower() in text_lower:
                idx = text_lower.find(reg.lower())
                entities.append(DetectedEntity(
                    text=reg,
                    entity_type="REGULATOR",
                    confidence=0.95,
                    start=idx,
                    end=idx + len(reg),
                    source="gazetteer",
                ))

        # Check organizations
        for org in ORGANIZATIONS:
            if org.lower() in text_lower:
                idx = text_lower.find(org.lower())
                # Get the actual case from the text
                actual = text[idx:idx + len(org)]
                entities.append(DetectedEntity(
                    text=actual,
                    entity_type="ORGANIZATION",
                    confidence=0.90,
                    start=idx,
                    end=idx + len(org),
                    source="gazetteer",
                    normalized=org,
                ))

        return entities

    def _extract_patterns(self, text: str) -> List[DetectedEntity]:
        """Extract entities using regex patterns."""
        entities = []

        # Capitalized multi-word names (potential organizations/people)
        cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
        for match in cap_pattern.finditer(text):
            name = match.group(1)
            if len(name) > 4 and name not in ("The New", "In The", "At The"):
                entities.append(DetectedEntity(
                    text=name,
                    entity_type="UNKNOWN",
                    confidence=0.5,
                    start=match.start(),
                    end=match.end(),
                    source="regex",
                ))

        # All-caps abbreviations (often organizations)
        abbrev_pattern = re.compile(r'\b([A-Z]{2,6})\b')
        for match in abbrev_pattern.finditer(text):
            abbrev = match.group(1)
            if abbrev not in ("THE", "AND", "FOR", "NOT", "BUT", "OCR", "PDF", "AI"):
                entities.append(DetectedEntity(
                    text=abbrev,
                    entity_type="ORGANIZATION",
                    confidence=0.4,
                    start=match.start(),
                    end=match.end(),
                    source="regex",
                ))

        return entities

    def _deduplicate(self, entities: List[DetectedEntity]) -> List[DetectedEntity]:
        """Remove duplicate entities, keeping highest confidence."""
        seen = {}
        for ent in entities:
            key = ent.text.lower()
            if key not in seen or ent.confidence > seen[key].confidence:
                seen[key] = ent
        return list(seen.values())
