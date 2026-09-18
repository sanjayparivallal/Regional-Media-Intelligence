"""
NLLB Translation Provider.

Uses Facebook's NLLB-200-distilled-600M for local translation.
Supports Hindi ↔ English, Tamil ↔ English, and 200+ languages.
"""

import logging
import time
from typing import List, Optional

from pipeline.nlp.translation.base import TranslationProvider, TranslationResult
from pipeline.nlp.translation.entity_protector import protect_entities, restore_entities

logger = logging.getLogger(__name__)

# NLLB language codes
NLLB_LANG_MAP = {
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "bn": "ben_Beng",
    "mr": "mar_Deva",
    "kn": "kan_Knda",
    "ml": "mal_Mlym",
    "gu": "guj_Gujr",
    "ur": "urd_Arab",
    "pa": "pan_Guru",
    "en": "eng_Latn",
}


class NLLBTranslationProvider(TranslationProvider):
    """NLLB-200 local translation provider."""

    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        self.model_name = model_name
        self._pipeline = None
        self._tokenizer = None
        self._model = None

    @property
    def name(self) -> str:
        return "nllb"

    def is_available(self) -> bool:
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            return True
        except ImportError:
            return False

    def _load_model(self):
        """Lazy-load the translation model."""
        if self._model is not None:
            return

        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            from pathlib import Path
            import torch

            from config import get_settings
            settings = get_settings()

            # Prefer local model directory
            from pathlib import Path
            local_model_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "models" / "indictrans2"
            local_path = Path(settings.translation_model_path) if settings.translation_model_path else local_model_dir
            load_source = str(local_path) if local_path.exists() else (settings.translation_model or self.model_name)

            logger.info(f"Loading NLLB model from: {load_source}")

            self._tokenizer = AutoTokenizer.from_pretrained(load_source)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(load_source)

            # Use GPU if available
            if torch.cuda.is_available():
                self._model = self._model.cuda()
                logger.info("NLLB model loaded on GPU")
            else:
                logger.info("NLLB model loaded on CPU")

        except Exception as e:
            logger.error(f"Failed to load NLLB model: {e}")
            raise

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en",
        protected_entities: List[str] = None,
    ) -> TranslationResult:
        start = time.time()

        if not text or len(text.strip()) < 2:
            return TranslationResult(
                source_text=text, translated_text=text,
                source_language=source_language, target_language=target_language,
                model_used=self.name, confidence=100.0,
            )

        try:
            self._load_model()
        except Exception:
            return TranslationResult(
                source_text=text, translated_text=f"[Translation unavailable] {text}",
                source_language=source_language, target_language=target_language,
                model_used=self.name, confidence=0.0,
            )

        # Protect named entities from translation
        protected_text, placeholders = protect_entities(text, protected_entities or [])

        src_code = NLLB_LANG_MAP.get(source_language, "eng_Latn")
        tgt_code = NLLB_LANG_MAP.get(target_language, "eng_Latn")

        try:
            import torch

            self._tokenizer.src_lang = src_code
            inputs = self._tokenizer(protected_text, return_tensors="pt", max_length=512, truncation=True)

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

            elapsed = int((time.time() - start) * 1000)

            return TranslationResult(
                source_text=text,
                translated_text=translated,
                source_language=source_language,
                target_language=target_language,
                confidence=85.0,  # NLLB generally good quality
                model_used=f"nllb-200-distilled-600M",
                entities_protected=list(placeholders.values()) if placeholders else [],
                processing_time_ms=elapsed,
            )

        except Exception as e:
            logger.error(f"NLLB translation failed: {e}")
            elapsed = int((time.time() - start) * 1000)
            return TranslationResult(
                source_text=text,
                translated_text=f"[Translation error] {text}",
                source_language=source_language,
                target_language=target_language,
                confidence=0.0,
                model_used=self.name,
                processing_time_ms=elapsed,
            )
