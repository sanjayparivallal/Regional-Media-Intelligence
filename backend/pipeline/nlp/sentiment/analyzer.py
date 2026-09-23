"""
Sentiment Analysis Module.

Multi-model sentiment analysis:
1. XLM-RoBERTa multilingual sentiment (primary)
2. Lexicon-based sentiment (fallback)

Compares results from original language and translated text.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton for the transformer pipeline.
# Loaded at most once per process — prevents repeated "Loading weights" spam
# when processing multiple documents in the same server session.
# ──────────────────────────────────────────────────────────────────────────────
_TRANSFORMER_PIPELINE = None
_TRANSFORMER_ATTEMPTED = False


def _get_transformer_pipeline():
    """Return the shared transformer pipeline, loading it on the first call."""
    global _TRANSFORMER_PIPELINE, _TRANSFORMER_ATTEMPTED
    if _TRANSFORMER_ATTEMPTED:
        return _TRANSFORMER_PIPELINE
    _TRANSFORMER_ATTEMPTED = True
    # Suppress tqdm/transformers loading progress bars
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    try:
        from transformers import pipeline, logging as hf_logging
        from transformers.utils.logging import disable_progress_bar
        from pathlib import Path
        from config import get_settings
        
        # Silence transformers library logger so weight-loading bars are hidden
        hf_logging.set_verbosity_error()
        disable_progress_bar()
        
        settings = get_settings()
        cls_path = getattr(settings, "classification_model_path", None)
        local_path = (
            Path(cls_path)
            if cls_path
            else Path(__file__).resolve().parent.parent.parent.parent
            / "model_assets" / "sentiment"
        )
        sentiment_model_name = getattr(settings, "sentiment_model", "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")
        model_target = (
            str(local_path)
            if (local_path.exists() and (local_path / "config.json").exists())
            else sentiment_model_name
        )
        
        import torch
        device_id = 0 if torch.cuda.is_available() else -1
        
        _TRANSFORMER_PIPELINE = pipeline(
            "sentiment-analysis",
            model=model_target,
            top_k=3,
            device=device_id,
        )
        logger.info(f"Loaded sentiment model from {model_target} (device={device_id})")
    except Exception as e:
        logger.warning(f"Sentiment transformer not available: {e}")
        _TRANSFORMER_PIPELINE = None
    return _TRANSFORMER_PIPELINE



@dataclass
class SentimentResult:
    label: str  # positive, neutral, negative
    confidence: float
    positive_score: float = 0.0
    neutral_score: float = 0.0
    negative_score: float = 0.0
    model_used: str = ""
    processing_time_ms: int = 0


class SentimentAnalyzer:
    """Multi-model sentiment analysis with disagreement detection."""

    def __init__(self):
        pass  # Transformer pipeline is a module-level singleton

    def analyze(
        self,
        text: str,
        translated_text: str = None,
        language: str = "en",
    ) -> SentimentResult:
        """
        Analyze sentiment using best available model.
        Uses both original and translated text when available.
        """
        if not text or len(text.strip()) < 5:
            return SentimentResult("neutral", 50.0, model_used="none")

        start = time.time()

        # Try transformer model first
        transformer_result = self._analyze_transformer(text)

        # If translated text available, analyze it too
        translation_result = None
        if translated_text and translated_text != text:
            translation_result = self._analyze_transformer(translated_text)

        # Fall back to lexicon if transformer unavailable
        if not transformer_result:
            transformer_result = self._analyze_lexicon(translated_text or text)

        # Compare and merge results
        if translation_result and transformer_result:
            result = self._merge_results(transformer_result, translation_result)
        else:
            result = transformer_result or SentimentResult("neutral", 50.0, model_used="none")

        result.processing_time_ms = int((time.time() - start) * 1000)
        return result

    def _analyze_transformer(self, text: str) -> Optional[SentimentResult]:
        """Analyze using XLM-RoBERTa (uses module-level singleton pipeline)."""
        pipe = _get_transformer_pipeline()
        if not pipe:
            return None

        try:
            results = pipe(text[:512])[0]  # Limit input length

            scores = {"positive": 0, "neutral": 0, "negative": 0}
            for r in results:
                label = r["label"].lower()
                if label in scores:
                    scores[label] = r["score"] * 100

            top_label = max(scores, key=scores.get)
            top_score = scores[top_label]

            return SentimentResult(
                label=top_label,
                confidence=top_score,
                positive_score=scores["positive"],
                neutral_score=scores["neutral"],
                negative_score=scores["negative"],
                model_used="xlm-roberta-sentiment",
            )
        except Exception as e:
            logger.warning(f"Transformer sentiment failed: {e}")
            return None

    def _analyze_lexicon(self, text: str) -> SentimentResult:
        """Rule-based sentiment analysis using keyword lexicons."""
        from pipeline.nlp.sentiment.lexicon import analyze_lexicon_sentiment
        return analyze_lexicon_sentiment(text)

    def _merge_results(
        self, primary: SentimentResult, secondary: SentimentResult
    ) -> SentimentResult:
        """Merge results from original and translated text analysis."""
        # If they agree, boost confidence
        if primary.label == secondary.label:
            merged_conf = min(100, (primary.confidence + secondary.confidence) / 2 + 5)
            return SentimentResult(
                label=primary.label,
                confidence=merged_conf,
                positive_score=(primary.positive_score + secondary.positive_score) / 2,
                neutral_score=(primary.neutral_score + secondary.neutral_score) / 2,
                negative_score=(primary.negative_score + secondary.negative_score) / 2,
                model_used=f"{primary.model_used}+{secondary.model_used}",
            )

        # Disagreement — use higher confidence, flag for review
        if primary.confidence >= secondary.confidence:
            result = primary
        else:
            result = secondary

        # Reduce confidence due to disagreement
        result.confidence = max(result.confidence - 15, 30)
        result.model_used += " [disagreement]"
        return result
