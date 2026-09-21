"""
Verification script for specified AI pipeline models:
1. IndicOCR
2. IndicTrans2
3. Liquid AI LFM 2.5
"""

import sys
import logging
from pathlib import Path
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("model_verifier")

BASE_DIR = Path(__file__).parent


def test_indic_ocr():
    logger.info("Testing IndicOCR model pipeline...")
    from services.ocr_service import OCRService
    ocr = OCRService()
    logger.info("IndicOCR service initialized successfully.")
    return True


def test_indictrans2():
    logger.info("Testing IndicTrans2 model pipeline...")
    from services.translation_service import TranslationService
    ts = TranslationService()
    logger.info("IndicTrans2 service initialized successfully.")
    return True


def test_lfm2_5():
    logger.info("Testing Liquid AI LFM 2.5 (Ollama endpoint)...")
    from services.lfm_service import LFMService
    lfm = LFMService()
    logger.info(f"LFM 2.5 service initialized with model: {lfm._model} at endpoint: {lfm._url}")
    return True


if __name__ == "__main__":
    logger.info("=== RUNNING LOCAL MODEL VERIFICATION (IndicOCR, IndicTrans2, LFM 2.5) ===")
    results = {}

    try:
        results["IndicOCR"] = test_indic_ocr()
    except Exception as e:
        results["IndicOCR"] = f"ERROR: {e}"

    try:
        results["IndicTrans2"] = test_indictrans2()
    except Exception as e:
        results["IndicTrans2"] = f"ERROR: {e}"

    try:
        results["LFM 2.5"] = test_lfm2_5()
    except Exception as e:
        results["LFM 2.5"] = f"ERROR: {e}"

    logger.info("\n=== VERIFICATION SUMMARY ===")
    for k, v in results.items():
        status = "PASSED" if v is True else f"FAILED ({v})"
        logger.info(f"  {k:15}: {status}")
