"""
Verification script for all downloaded AI models.
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("model_verifier")

BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "model_assets"

def test_spacy():
    logger.info("Testing spaCy model...")
    import spacy
    spacy_path = MODELS_DIR / "spacy_en"
    nlp = spacy.load(str(spacy_path))
    doc = nlp("Reserve Bank of India regulatory order for PayU.")
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    logger.info(f"spaCy loaded successfully! Detected entities: {entities}")
    return True

def test_sentiment():
    logger.info("Testing XLM-RoBERTa Sentiment model...")
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    sentiment_path = MODELS_DIR / "sentiment"
    tokenizer = AutoTokenizer.from_pretrained(str(sentiment_path))
    model = AutoModelForSequenceClassification.from_pretrained(str(sentiment_path))
    logger.info(f"Sentiment model loaded successfully! Model type: {type(model).__name__}")
    return True

def test_translation():
    logger.info("Testing NLLB-200 Translation model...")
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    trans_path = MODELS_DIR / "translation"
    tokenizer = AutoTokenizer.from_pretrained(str(trans_path))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(trans_path))
    logger.info(f"NLLB-200 model loaded successfully! Model type: {type(model).__name__}")
    return True

def test_easyocr():
    logger.info("Testing EasyOCR model...")
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False, download_enabled=False)
    logger.info("EasyOCR loaded successfully with pre-downloaded CRAFT model!")
    return True

if __name__ == "__main__":
    logger.info("=== RUNNING LOCAL MODEL VERIFICATION ===")
    results = {}
    try:
        results["spaCy"] = test_spacy()
    except Exception as e:
        results["spaCy"] = f"ERROR: {e}"

    try:
        results["EasyOCR"] = test_easyocr()
    except Exception as e:
        results["EasyOCR"] = f"ERROR: {e}"

    try:
        results["Sentiment"] = test_sentiment()
    except Exception as e:
        results["Sentiment"] = f"ERROR: {e}"

    try:
        results["Translation"] = test_translation()
    except Exception as e:
        results["Translation"] = f"ERROR: {e}"

    logger.info("\n=== VERIFICATION SUMMARY ===")
    for k, v in results.items():
        status = "PASSED" if v is True else f"FAILED ({v})"
        logger.info(f"  {k:15}: {status}")
