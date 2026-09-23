"""
Translation Service.

Local neural machine translation using AI4Bharat IndicTrans2 (ai4bharat/indictrans2-indic-en-1B).
All inference runs locally with CUDA GPU acceleration.
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

import torch
from config import get_settings
from services.indic_processor import IndicProcessor

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "models" / "indictrans2"

# Supported language mapping from app codes to IndicTrans2 / FLORES-200 codes
INDICTRANS2_LANG_MAP = {
    "ta": "tam_Taml",
    "tam": "tam_Taml",
    "hi": "hin_Deva",
    "hin": "hin_Deva",
    "te": "tel_Telu",
    "tel": "tel_Telu",
    "kn": "kan_Knda",
    "kan": "kan_Knda",
    "ml": "mal_Mlym",
    "mal": "mal_Mlym",
    "gu": "guj_Gujr",
    "guj": "guj_Gujr",
    "bn": "ben_Beng",
    "ben": "ben_Beng",
    "mr": "mar_Deva",
    "mar": "mar_Deva",
    "pa": "pan_Guru",
    "pan": "pan_Guru",
    "or": "ory_Orya",
    "ory": "ory_Orya",
    "as": "asm_Beng",
    "asm": "asm_Beng",
    "ur": "urd_Arab",
    "urd": "urd_Arab",
    "en": "eng_Latn",
    "eng": "eng_Latn",
}


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
    Local translation service using actual AI4Bharat IndicTrans2.

    Features:
    - Genuine IndicTrans2 model inference (ai4bharat/indictrans2-indic-en-1B)
    - Full CUDA GPU acceleration (FP16)
    - Entity protection during translation
    - Standard interface compatibility
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._indic_processor = None
        self._loaded = False
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self):
        """Lazy-load the IndicTrans2 model onto GPU with FP16 precision."""
        if self._loaded:
            return

        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            from huggingface_hub import login

            settings = get_settings()
            hf_token = getattr(settings, "hf_token", None) or os.getenv("HF_TOKEN")
            is_offline = os.getenv("HF_HUB_OFFLINE") == "1" or os.getenv("TRANSFORMERS_OFFLINE") == "1"
            if hf_token and not is_offline:
                try:
                    login(token=hf_token)
                except Exception as e:
                    logger.warning(f"Hugging Face login note: {e}")

            model_name = getattr(settings, "translation_model", "ai4bharat/indictrans2-indic-en-1B")
            is_local = MODEL_DIR.exists() and (MODEL_DIR / "model.safetensors").exists()
            model_path = str(MODEL_DIR) if is_local else model_name

            logger.info(f"Loading IndicTrans2 model from: {model_path} onto {self._device} (local_files_only={is_local})")

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                local_files_only=is_local,
            )

            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            load_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": dtype,
                "local_files_only": is_local,
            }
            if self._device == "cuda":
                load_kwargs["device_map"] = {"": "cuda:0"}
            else:
                load_kwargs["low_cpu_mem_usage"] = True

            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model_path,
                **load_kwargs,
            )
            if self._device != "cuda":
                self._model = self._model.to(self._device)

            self._indic_processor = IndicProcessor(inference=True)
            self._loaded = True
            logger.info(f"IndicTrans2 model ({model_name}) successfully loaded on {self._device} (FP16={torch.cuda.is_available()})")
        except Exception as e:
            logger.error(f"Failed to load IndicTrans2 model: {e}")
            raise

    def translate_batch(
        self,
        texts: list,
        source_language: str,
        target_language: str = "en",
    ) -> list:
        """
        Translate a batch of texts from source to target language in one GPU inference pass.

        This is the GPU-optimised path: all texts are tokenised together and
        passed to model.generate() in a single call, maximising GPU utilisation.

        Args:
            texts: List of source texts to translate
            source_language: Source language ISO code (e.g. 'ta', 'hi')
            target_language: Target language ISO code (default 'en')

        Returns:
            List of TranslationServiceResult, one per input text.
            On partial failure the failing item returns its original text with status='error'.
        """
        if not texts:
            return []

        # Resolve language codes once
        src_code = INDICTRANS2_LANG_MAP.get(source_language.lower())
        if not src_code:
            from services.language_config import get_language_registry
            src_code = get_language_registry().get_nllb_code(source_language)

        tgt_code = INDICTRANS2_LANG_MAP.get(target_language.lower(), "eng_Latn")

        if not src_code:
            # Unsupported language — return passthrough results
            return [
                TranslationServiceResult(
                    source_text=t, translated_text=t,
                    source_language=source_language, target_language=target_language,
                    confidence=None, confidence_source="not_available",
                    status="unsupported",
                    error=f"Unsupported language: {source_language}",
                    processing_time=0.0,
                )
                for t in texts
            ]

        try:
            self._load_model()
        except Exception as e:
            return [
                TranslationServiceResult(
                    source_text=t, translated_text=t,
                    source_language=source_language, target_language=target_language,
                    confidence=0.0, confidence_source="not_available",
                    status="error", error=str(e), processing_time=0.0,
                )
                for t in texts
            ]

        from pipeline.nlp.translation.entity_protector import (
            protect_entities, restore_entities, extract_potential_entities,
        )

        start_time = time.time()
        protected_texts = []
        all_placeholders = []
        for text in texts:
            entities_to_protect = extract_potential_entities(text)
            protected_text, placeholders = protect_entities(text, entities_to_protect)
            protected_texts.append(protected_text)
            all_placeholders.append(placeholders)

        try:
            # 1. Preprocess entire batch
            preprocessed = self._indic_processor.preprocess_batch(
                protected_texts,
                src_lang=src_code,
                tgt_lang=tgt_code,
            )

            # 2. Tokenise batch
            inputs = self._tokenizer(
                preprocessed,
                padding="longest",
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self._device)

            # 3. Single model.generate() call for the whole batch
            settings = get_settings()
            num_beams = getattr(settings, "translation_num_beams", 1)
            with torch.no_grad():
                generated_tokens = self._model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=512,
                    num_beams=num_beams,
                    num_return_sequences=1,
                )

            # 4. Decode
            decoded = self._tokenizer.batch_decode(
                generated_tokens.detach().cpu().tolist(),
                skip_special_tokens=True,
            )

            # 5. Postprocess
            translated_batch = self._indic_processor.postprocess_batch(
                decoded,
                lang=tgt_code,
            )

            elapsed = round(time.time() - start_time, 2)
            results = []
            for i, (orig_text, translated, placeholders) in enumerate(
                zip(texts, translated_batch, all_placeholders)
            ):
                translated = restore_entities(translated, placeholders)
                results.append(TranslationServiceResult(
                    source_text=orig_text,
                    translated_text=translated,
                    source_language=source_language,
                    target_language=target_language,
                    confidence=None,
                    confidence_source="not_available",
                    entities_protected=list(placeholders.values()),
                    entity_mapping={v: k for k, v in placeholders.items()},
                    processing_time=round(elapsed / max(len(texts), 1), 3),
                    model_used="ai4bharat/indictrans2-indic-en-1B",
                    review_required=False,
                ))
            return results

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"IndicTrans2 batch translation failed: {e}")
            return [
                TranslationServiceResult(
                    source_text=t, translated_text=t,
                    source_language=source_language, target_language=target_language,
                    confidence=0.0, confidence_source="not_available",
                    status="error", error=str(e),
                    processing_time=round(elapsed / max(len(texts), 1), 3),
                )
                for t in texts
            ]

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en",
        protected_entities: Optional[List[str]] = None,
    ) -> TranslationServiceResult:
        """
        Translate text from regional source language to English using IndicTrans2.

        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'ta', 'hi', 'ml', 'kn', 'te', 'gu')
            target_language: Target language code (default: 'en')
            protected_entities: Entity strings to protect during translation

        Returns:
            TranslationServiceResult with translation and confidence
        """
        start_time = time.time()

        # Skip translation for same-language or English
        if source_language == target_language or source_language == "en":
            return TranslationServiceResult(
                source_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=100.0,
                confidence_source="identical",
                model_used="passthrough",
                processing_time=round(time.time() - start_time, 2),
            )

        if not text or len(text.strip()) < 2:
            return TranslationServiceResult(
                source_text=text,
                translated_text=text or "",
                source_language=source_language,
                target_language=target_language,
                confidence=None,
                confidence_source="not_available",
                model_used="none",
                processing_time=round(time.time() - start_time, 2),
            )

        # Resolve internal IndicTrans2 / FLORES-200 language codes
        src_code = INDICTRANS2_LANG_MAP.get(source_language.lower())
        if not src_code:
            from services.language_config import get_language_registry
            registry = get_language_registry()
            src_code = registry.get_nllb_code(source_language)

        tgt_code = INDICTRANS2_LANG_MAP.get(target_language.lower(), "eng_Latn")

        if not src_code:
            return TranslationServiceResult(
                source_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=None,
                confidence_source="not_available",
                status="unsupported",
                error=f"Translation not supported for language: {source_language}",
                processing_time=round(time.time() - start_time, 2),
            )

        try:
            self._load_model()
        except Exception as e:
            return TranslationServiceResult(
                source_text=text,
                translated_text=f"[Translation unavailable] {text}",
                source_language=source_language,
                target_language=target_language,
                confidence=0.0,
                confidence_source="not_available",
                status="error",
                error=str(e),
                processing_time=round(time.time() - start_time, 2),
            )

        # Protect entities
        from pipeline.nlp.translation.entity_protector import (
            protect_entities,
            restore_entities,
            extract_potential_entities,
        )

        entities_to_protect = list(protected_entities or [])
        auto_entities = extract_potential_entities(text)
        entities_to_protect.extend([e for e in auto_entities if e not in entities_to_protect])

        protected_text, placeholders = protect_entities(text, entities_to_protect)

        try:
            # 1. Preprocess with IndicProcessor
            preprocessed = self._indic_processor.preprocess_batch(
                [protected_text],
                src_lang=src_code,
                tgt_lang=tgt_code,
            )

            # 2. Tokenize and move to device
            inputs = self._tokenizer(
                preprocessed,
                padding="longest",
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self._device)

            # 3. Model generation on CUDA (num_beams from config)
            num_beams = getattr(settings, "translation_num_beams", 1)
            with torch.no_grad():
                generated_tokens = self._model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=512,
                    num_beams=num_beams,
                    num_return_sequences=1,
                )

            # 4. Decode tokens
            decoded = self._tokenizer.batch_decode(
                generated_tokens.detach().cpu().tolist(),
                skip_special_tokens=True,
            )

            # 5. Postprocess with IndicProcessor
            translated = self._indic_processor.postprocess_batch(
                decoded,
                lang=tgt_code,
            )[0]

            # 6. Restore protected entities
            translated = restore_entities(translated, placeholders)

            elapsed = round(time.time() - start_time, 2)

            confidence_val = None
            confidence_src = "not_available"
            if len(translated.strip()) < 2:
                confidence_val = 0.0
                confidence_src = "heuristic"

            from services.language_config import get_language_registry
            registry = get_language_registry()
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
                model_used="ai4bharat/indictrans2-indic-en-1B",
                review_required=review_required,
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"IndicTrans2 translation failed: {e}")
            return TranslationServiceResult(
                source_text=text,
                translated_text=f"[Translation error] {text}",
                source_language=source_language,
                target_language=target_language,
                confidence=0.0,
                confidence_source="not_available",
                status="error",
                error=str(e),
                processing_time=elapsed,
            )
