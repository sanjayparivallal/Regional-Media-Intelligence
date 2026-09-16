"""
Model Downloader for Regional Media Intelligence Agent.

Downloads and caches all required open-source AI models locally:
1. spaCy: spacy/en_core_web_sm (~12MB)
2. Sentiment: cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual (~1.1GB)
3. Translation: facebook/nllb-200-distilled-600M (~1.2GB)
4. EasyOCR: Detection and recognition models for English and Hindi (~80MB)
"""

import os
import sys
import logging
from pathlib import Path
from huggingface_hub import snapshot_download
from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("model_downloader")

settings = get_settings()
BASE_DIR = Path(__file__).parent
MODELS_DIR = Path(settings.ner_model_path).parent if settings.ner_model_path else BASE_DIR / "model_assets"
MODELS_DIR.mkdir(exist_ok=True, parents=True)


def download_spacy_model():
    """Download spaCy English model from Hugging Face."""
    logger.info(f"=== [1/4] Downloading spaCy model ({settings.spacy_model}) ===")
    target_dir = Path(settings.ner_model_path) if settings.ner_model_path else MODELS_DIR / "spacy_en"
    repo_id = "spacy/en_core_web_sm" if settings.spacy_model == "en_core_web_sm" else settings.spacy_model
    try:
        path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            ignore_patterns=["*.whl"],
        )
        logger.info(f"✓ spaCy model downloaded to: {path}")
        
        # Verify it loads in spaCy
        import spacy
        nlp = spacy.load(str(target_dir))
        doc = nlp("Reserve Bank of India regulatory update.")
        logger.info(f"✓ spaCy verification successful: {len(doc.ents)} entities detected")
        return str(target_dir)
    except Exception as e:
        logger.error(f"Failed to download spaCy model: {e}")
        return None


def download_sentiment_model():
    """Download CardiffNLP XLM-RoBERTa multilingual sentiment model."""
    logger.info(f"=== [2/4] Downloading Sentiment Model ({settings.sentiment_model}) ===")
    target_dir = Path(settings.classification_model_path) if settings.classification_model_path else MODELS_DIR / "sentiment"
    try:
        path = snapshot_download(
            repo_id=settings.sentiment_model,
            local_dir=str(target_dir),
        )
        logger.info(f"✓ Sentiment model downloaded to: {path}")
        return str(target_dir)
    except Exception as e:
        logger.error(f"Failed to download sentiment model: {e}")
        return None


def download_translation_model():
    """Download translation model."""
    logger.info(f"=== [3/4] Downloading Translation Model ({settings.translation_model}) ===")
    target_dir = Path(settings.translation_model_path) if settings.translation_model_path else MODELS_DIR / "translation"
    try:
        path = snapshot_download(
            repo_id=settings.translation_model,
            local_dir=str(target_dir),
        )
        logger.info(f"✓ Translation model downloaded to: {path}")
        return str(target_dir)
    except Exception as e:
        logger.error(f"Failed to download translation model: {e}")
        return None


def download_easyocr_models():
    """Download EasyOCR models for English and Hindi."""
    logger.info("=== [4/4] Initializing EasyOCR models for English and Hindi ===")
    try:
        import easyocr
        # Initializing the Reader triggers download of craft detection model + recognition models
        reader = easyocr.Reader(['en', 'hi'], gpu=False, download_enabled=True)
        logger.info("✓ EasyOCR models downloaded and initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"EasyOCR initialization warning: {e}")
        return False


def main():
    logger.info("Starting AI models download...")
    
    # 1. spaCy
    spacy_path = download_spacy_model()
    
    # 2. EasyOCR
    easyocr_ok = download_easyocr_models()

    # 3. Multilingual Sentiment
    sentiment_path = download_sentiment_model()

    # 4. NLLB-200 Translation
    translation_path = download_translation_model()

    logger.info("\n==========================================")
    logger.info("           MODEL DOWNLOAD SUMMARY          ")
    logger.info("==========================================")
    logger.info(f"spaCy (en_core_web_sm): {'SUCCESS -> ' + str(spacy_path) if spacy_path else 'FAILED'}")
    logger.info(f"EasyOCR (en, hi):      {'SUCCESS' if easyocr_ok else 'FAILED'}")
    logger.info(f"Sentiment (XLM-R):     {'SUCCESS -> ' + str(sentiment_path) if sentiment_path else 'FAILED'}")
    logger.info(f"Translation (NLLB-200): {'SUCCESS -> ' + str(translation_path) if translation_path else 'FAILED'}")
    logger.info("==========================================")


if __name__ == "__main__":
    main()
