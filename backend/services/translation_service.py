"""
Translation Service.

Local translation using NLLB-200-distilled-600M with entity protection.
All inference runs locally. No cloud APIs.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "backend" / "model_assets" / "translation"
if not MODEL_DIR.exists():
    MODEL_DIR = BASE_DIR / "models" / "indictrans2"


@dataclass
class TranslationServiceResult:
    """Translation result with confidence and entity tracking."""
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: Optional[float]
    confidence_source: str  # "model", "heuristic", "not_available"
    entities_protected: List[str] = field(default_factory=list)
    entity_mapping: Dict[str, str] = field(default_factory=dict)
    processing_time: float = 0.0
    model_used: str = ""
    review_required: bool = False
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "confidence": self.confidence,
            "confidence_source": self.confidence_source,
            "entities_protected": self.entities_protected,
            "entity_mapping": self.entity_mapping,
            "processing_time": self.processing_time,
            "model_used": self.model_used,
            "review_required": self.review_required,
            "status": self.status,
        }


class TranslationService:
    """
    Local translation service using NLLB-200-distilled-600M.

    Features:
    - Entity protection during translation
    - Language-routed source code selection
    - Explicit confidence reporting (null if unavailable)
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._loaded = False

    def _load_model(self):
        """Lazy-load the translation model."""
        if self._loaded:
            return

        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            import torch

            is_local = MODEL_DIR.exists()
            model_path = str(MODEL_DIR) if is_local else "facebook/nllb-200-distilled-600M"
            logger.info(f"Loading translation model from: {model_path} (offline/local_files_only={is_local})")

            self._tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=is_local)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=is_local)

            if torch.cuda.is_available():
                self._model = self._model.cuda()
                logger.info("Translation model loaded on GPU")
            else:
                logger.info("Translation model loaded on CPU")

            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load translation model: {e}")
            raise

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en",
        protected_entities: Optional[List[str]] = None,
    ) -> TranslationServiceResult:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'ta', 'hi')
            target_language: Target language code (default: 'en')
            protected_entities: Entity strings to protect during translation

        Returns:
            TranslationServiceResult with translation and confidence
        """
        start_time = time.time()

        # Skip translation for same-language or English
        if source_language == target_language or source_language == "en":
            return TranslationServiceResult(
                source_text=text, translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=100.0, confidence_source="identical",
                model_used="passthrough",
                processing_time=round(time.time() - start_time, 2),
            )

        if not text or len(text.strip()) < 2:
            return TranslationServiceResult(
                source_text=text, translated_text=text or "",
                source_language=source_language,
                target_language=target_language,
                confidence=None, confidence_source="not_available",
                model_used="none",
                processing_time=round(time.time() - start_time, 2),
            )

        # Get NLLB language codes
        from services.language_config import get_language_registry
        registry = get_language_registry()
        src_code = registry.get_nllb_code(source_language)
        tgt_code = registry.get_nllb_code(target_language) or "eng_Latn"

        if not src_code:
            return TranslationServiceResult(
                source_text=text, translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=None, confidence_source="not_available",
                status="unsupported",
                error=f"Translation not supported for language: {source_language}",
                processing_time=round(time.time() - start_time, 2),
            )

        try:
            self._load_model()
        except Exception as e:
            return TranslationServiceResult(
                source_text=text, translated_text=f"[Translation unavailable] {text}",
                source_language=source_language,
                target_language=target_language,
                confidence=0.0, confidence_source="not_available",
                status="error", error=str(e),
                processing_time=round(time.time() - start_time, 2),
            )

        # Protect entities
        from pipeline.nlp.translation.entity_protector import (
            protect_entities, restore_entities, extract_potential_entities,
        )

        entities_to_protect = list(protected_entities or [])
        # Also auto-detect potential entities
        auto_entities = extract_potential_entities(text)
        entities_to_protect.extend([e for e in auto_entities if e not in entities_to_protect])

        protected_text, placeholders = protect_entities(text, entities_to_protect)

        try:
            import torch

            self._tokenizer.src_lang = src_code
            inputs = self._tokenizer(
                protected_text, return_tensors="pt",
                max_length=512, truncation=True,
            )

            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            tgt_lang_id = self._tokenizer.convert_tokens_to_ids(tgt_code)

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    forced_bos_token_id=tgt_lang_id,
                    max_new_tokens=512,
                )

            translated = self._tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Restore protected entities
            translated = restore_entities(translated, placeholders)

            elapsed = round(time.time() - start_time, 2)

            # NLLB does not provide per-sequence confidence scores.
            # We set confidence to None and mark source honestly.
            confidence_val = None
            confidence_src = "not_available"

            # Heuristic: check if translation looks reasonable
            if len(translated.strip()) < 2:
                confidence_val = 0.0
                confidence_src = "heuristic"

            # Check review threshold
            review_threshold = registry.translation_review_threshold
            review_required = confidence_val is not None and confidence_val < review_threshold

            return TranslationServiceResult(
                source_text=text,
                translated_text=translated,
                source_language=source_language,
                target_language=target_language,
                confidence=confidence_val,
                confidence_source=confidence_src,
                entities_protected=list(placeholders.values()),
                entity_mapping={v: k for k, v in placeholders.items()},
                processing_time=elapsed,
                model_used="nllb-200-distilled-600M",
                review_required=review_required,
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"Translation failed: {e}")
            return TranslationServiceResult(
                source_text=text,
                translated_text=f"[Translation error] {text}",
                source_language=source_language,
                target_language=target_language,
                confidence=0.0,
                confidence_source="not_available",
                status="error", error=str(e),
                processing_time=elapsed,
            )
