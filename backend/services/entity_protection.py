"""
Entity Protection Service.

Protects named entities during translation using deterministic
placeholder replacement. Integrates with brand dictionary.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProtectedEntity:
    """An entity that was protected during translation."""
    original_text: str
    placeholder: str
    entity_type: str  # BRAND, PERSON, ORGANIZATION, LOCATION, etc.
    source: str  # brand_dict, regex, ner


@dataclass
class EntityProtectionResult:
    """Result of entity protection."""
    protected_text: str
    entities: List[ProtectedEntity] = field(default_factory=list)
    placeholder_mapping: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "protected_text": self.protected_text,
            "entities": [
                {
                    "original_text": e.original_text,
                    "placeholder": e.placeholder,
                    "entity_type": e.entity_type,
                    "source": e.source,
                }
                for e in self.entities
            ],
            "placeholder_mapping": self.placeholder_mapping,
        }


class EntityProtectionService:
    """
    Deterministic entity protection for translation pipeline.

    Priority order:
    1. Monitored brand dictionary (from config/brands.json)
    2. Regex-detected entities (capitalized words, abbreviations)
    3. NER-detected entities (if available)

    Placeholder format: <ENTITY_001>, <ENTITY_002>, ...
    """

    def __init__(self):
        self._brands: List[str] = []
        self._brand_aliases: Dict[str, str] = {}
        self._loaded = False

    def _load_brands(self):
        """Load monitored brands from config/brands.json."""
        if self._loaded:
            return

        import json
        from pathlib import Path
        
        # 1. Try ExcelStorageService
        try:
            from storage.excel_storage_service import ExcelStorageService
            excel = ExcelStorageService()
            db_brands = excel.find_rows("MonitoredBrands", {"enabled": True})
            for b in db_brands:
                name = b["brand_name"]
                if name not in self._brands:
                    self._brands.append(name)
                for alias in (b.get("aliases") or "").split(","):
                    if alias.strip():
                        self._brand_aliases[alias.strip().lower()] = name
        except Exception:
            pass

        # 2. Try seed/brands.json
        seed_path = Path(__file__).resolve().parent.parent / "seed" / "brands.json"
        if seed_path.exists():
            try:
                data = json.loads(seed_path.read_text(encoding="utf-8"))
                for brand in data:
                    name = brand["name"]
                    if name not in self._brands:
                        self._brands.append(name)
                    for alias in brand.get("aliases", []):
                        self._brand_aliases[alias.lower()] = name
            except Exception as e:
                logger.warning(f"Could not load seed brands config: {e}")

        logger.info(f"Loaded {len(self._brands)} monitored brands into EntityProtectionService")
        self._loaded = True

    def protect(
        self,
        text: str,
        additional_entities: Optional[List[str]] = None,
    ) -> EntityProtectionResult:
        """
        Detect and replace entities with deterministic placeholders.

        Args:
            text: Original text (may be in any language)
            additional_entities: Extra entity strings to protect

        Returns:
            EntityProtectionResult with protected text and mapping
        """
        self._load_brands()

        entities_found: List[ProtectedEntity] = []
        entity_texts: List[str] = []

        # 1. Brand dictionary matching
        text_lower = text.lower()
        for brand in self._brands:
            if brand.lower() in text_lower:
                entity_texts.append(brand)
                entities_found.append(ProtectedEntity(
                    original_text=brand,
                    placeholder="",  # assigned below
                    entity_type="BRAND",
                    source="brand_dict",
                ))

        # Also check aliases
        for alias_lower, brand_name in self._brand_aliases.items():
            if alias_lower in text_lower and brand_name not in entity_texts:
                # Find the actual text (preserve case)
                idx = text_lower.find(alias_lower)
                actual = text[idx:idx + len(alias_lower)]
                entity_texts.append(actual)
                entities_found.append(ProtectedEntity(
                    original_text=actual,
                    placeholder="",
                    entity_type="BRAND",
                    source="brand_dict",
                ))

        # 2. Regex-based detection: capitalized words in non-Latin text
        caps_pattern = re.compile(r'\b[A-Z][a-zA-Z]{2,}\b')
        for match in caps_pattern.finditer(text):
            word = match.group()
            if word not in entity_texts and word not in ("The", "And", "For", "Not", "But", "This", "That", "With"):
                entity_texts.append(word)
                entities_found.append(ProtectedEntity(
                    original_text=word,
                    placeholder="",
                    entity_type="UNKNOWN",
                    source="regex",
                ))

        # 3. All-caps abbreviations
        abbrev_pattern = re.compile(r'\b[A-Z]{2,6}\b')
        for match in abbrev_pattern.finditer(text):
            abbrev = match.group()
            if abbrev not in entity_texts and abbrev not in ("THE", "AND", "FOR", "NOT", "BUT", "OCR", "PDF", "AI"):
                entity_texts.append(abbrev)
                entities_found.append(ProtectedEntity(
                    original_text=abbrev,
                    placeholder="",
                    entity_type="ORGANIZATION",
                    source="regex",
                ))

        # 4. Additional entities from caller
        if additional_entities:
            for ent in additional_entities:
                if ent not in entity_texts and ent in text:
                    entity_texts.append(ent)
                    entities_found.append(ProtectedEntity(
                        original_text=ent,
                        placeholder="",
                        entity_type="UNKNOWN",
                        source="external",
                    ))

        # Sort by length (longer first) to avoid partial replacements
        sorted_entities = sorted(
            zip(entity_texts, entities_found),
            key=lambda x: len(x[0]),
            reverse=True,
        )

        # Replace with deterministic placeholders
        protected_text = text
        placeholder_mapping: Dict[str, str] = {}
        counter = 1

        for entity_text, entity_obj in sorted_entities:
            placeholder = f"<ENTITY_{counter:03d}>"
            entity_obj.placeholder = placeholder

            if entity_text in protected_text:
                protected_text = protected_text.replace(entity_text, placeholder)
                placeholder_mapping[placeholder] = entity_text
                counter += 1

        return EntityProtectionResult(
            protected_text=protected_text,
            entities=[e for e in [eo for _, eo in sorted_entities] if e.placeholder],
            placeholder_mapping=placeholder_mapping,
        )

    def restore(
        self,
        translated_text: str,
        placeholder_mapping: Dict[str, str],
    ) -> str:
        """
        Restore original entities in translated text.

        Handles cases where the translation model may have modified
        or split placeholder tokens.
        """
        if not placeholder_mapping:
            return translated_text

        result = translated_text

        for placeholder, entity in placeholder_mapping.items():
            # Exact replacement
            result = result.replace(placeholder, entity)

            # Handle common model modifications
            # Models sometimes add spaces around angle brackets
            variations = [
                placeholder.replace("<", "< ").replace(">", " >"),
                placeholder.replace("_", " "),
                placeholder.lower(),
                placeholder.replace("<", "").replace(">", ""),
            ]
            for var in variations:
                result = result.replace(var, entity)

        return result
