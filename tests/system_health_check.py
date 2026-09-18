import sys
import os
import asyncio
from pathlib import Path
import cv2
import numpy as np

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

def create_dummy_image():
    """Create a blank white image for testing OCR initialization."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    path = "dummy_test_img.png"
    cv2.imwrite(path, img)
    return path

async def run_health_checks():
    print("=" * 60)
    print("AI MODEL HEALTH CHECK")
    print("Verifying all models can load and run on your hardware")
    print("=" * 60)
    
    img_path = create_dummy_image()
    
    # 1. Test IndicOCR (EasyOCR) - Hindi
    print("\n[1/4] Testing IndicOCR (EasyOCR) initialization...")
    try:
        from services.ocr_service import OCRService
        ocr = OCRService()
        # Hindi uses EasyOCR
        res = ocr.process_page(img_path, language="hi")
        print("✅ IndicOCR loaded successfully (Engine:", res.engine, ")")
    except Exception as e:
        print("❌ IndicOCR failed to load:", str(e))

    # 2. Test PaddleOCR - Gujarati
    print("\n[2/4] Testing PaddleOCR (Fallback) initialization...")
    try:
        from services.ocr_service import OCRService
        ocr = OCRService()
        # Gujarati uses PaddleOCR fallback
        res = ocr.process_page(img_path, language="gu")
        print("✅ PaddleOCR loaded successfully (Engine:", res.engine, ")")
    except Exception as e:
        print("❌ PaddleOCR failed to load:", str(e))

    # 3. Test Translation (NLLB-200 600M)
    print("\n[3/4] Testing IndicTrans2 (NLLB) initialization...")
    try:
        from services.translation_service import TranslationService
        translator = TranslationService()
        res = translator.translate("नमस्ते", "hi", "en", [])
        print("✅ Translation model loaded successfully.")
        print("   Test Output:", res.translated_text)
    except Exception as e:
        print("❌ Translation model failed to load:", str(e))

    # 4. Test LFM (Ollama)
    print("\n[4/4] Testing LFM2.5-2.6B (Ollama) connection...")
    try:
        from services.lfm_service import LFMService
        lfm = LFMService()
        if lfm.is_available():
            print("✅ LFM connected successfully.")
            res = lfm.analyze("The RBI has fined PayU.", ["RBI", "PayU"], "PayU")
            print("   Test Output Status:", res.status)
        else:
            print("❌ LFM via Ollama is unavailable. Is Ollama running?")
    except Exception as e:
        print("❌ LFM test failed:", str(e))
        
    # Cleanup
    try:
        os.remove(img_path)
    except:
        pass
        
    print("\n=" * 60)
    print("HEALTH CHECK COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_health_checks())
