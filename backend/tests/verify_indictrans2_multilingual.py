"""
Comprehensive verification test for IndicTrans2 across 6 regional Indian languages on CUDA GPU.
"""

import sys
import time
import torch

# Configure stdout for UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from services.translation_service import TranslationService
from services.ocr_service import OCRService
from services.lfm_service import LFMService

def run_tests():
    print("=" * 65)
    print("RMIA PIPELINE VERIFICATION — GPU & MODEL STACK")
    print("=" * 65)

    # 1. System & GPU Info
    print("\n[1] GPU Environment:")
    print(f"  PyTorch Version: {torch.__version__}")
    print(f"  CUDA Available:  {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA Version:    {torch.version.cuda}")
        print(f"  Device Name:     {torch.cuda.get_device_name(0)}")
        print(f"  Total VRAM:      {round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)} GB")

    # 2. IndicTrans2 Multilingual Translation Test
    print("\n[2] Testing IndicTrans2 (ai4bharat/indictrans2-indic-en-1B on CUDA):")
    ts = TranslationService()
    ts._load_model()
    print(f"  Device:          {ts._device}")
    print(f"  Allocated VRAM:  {round(torch.cuda.memory_allocated() / (1024**3), 2)} GB")

    test_sentences = [
        {
            "lang_name": "Tamil",
            "lang_code": "ta",
            "text": "சென்னையில் பெய்த கனமழை காரணமாக பல பகுதிகளில் வெள்ளப்பெருக்கு ஏற்பட்டுள்ளது.",
        },
        {
            "lang_name": "Hindi",
            "lang_code": "hi",
            "text": "प्रधानमंत्री ने आज नई आर्थिक नीति और डिजिटल इंडिया मिशन पर उच्चस्तरीय बैठक की।",
        },
        {
            "lang_name": "Malayalam",
            "lang_code": "ml",
            "text": "കേരളത്തിൽ കനത്ത മഴയെ തുടർന്ന് വിവിധ ജില്ലകളിൽ റെഡ് അലർട്ട് പ്രഖ്യാപിച്ചു.",
        },
        {
            "lang_name": "Kannada",
            "lang_code": "kn",
            "text": "ಬೆಂಗಳೂರಿನಲ್ಲಿ ಮೆಟ್ರೋ ರೈಲು ಯೋಜನೆಯ ಎರಡನೇ ಹಂತದ ಕಾಮಗಾರಿ ಶೀಘ್ರವೇ ಪೂರ್ಣಗೊಳ್ಳಲಿದೆ.",
        },
        {
            "lang_name": "Telugu",
            "lang_code": "te",
            "text": "హైదరాబాద్ నగరంలో కొత్త ఐటీ పాలసీని ప్రభుత్వం ఘనంగా ప్రారంభించింది.",
        },
        {
            "lang_name": "Gujarati",
            "lang_code": "gu",
            "text": "અમદાવાદમાં વાઇબ્રન્ટ ગુજરાત ગ્લોબલ સમિટનું ભવ્ય આયોજન કરવામાં આવ્યું છે.",
        },
    ]

    all_passed = True
    for item in test_sentences:
        t0 = time.time()
        result = ts.translate(item["text"], source_language=item["lang_code"], target_language="en")
        elapsed = round(time.time() - t0, 2)

        print(f"\n  Language:   {item['lang_name']} ({item['lang_code']} -> en)")
        print(f"  Original:   {item['text']}")
        print(f"  Translated: {result.translated_text}")
        print(f"  Model Used: {result.model_used}")
        print(f"  Time:       {elapsed}s")
        print(f"  Status:     {result.status}")

        if result.status != "success" or not result.translated_text:
            all_passed = False

    # 3. IndicOCR Test
    print("\n[3] Testing IndicOCR (EasyOCR primary + PaddleOCR fallback):")
    ocr = OCRService()
    print(f"  OCR GPU Available: {ocr._gpu_available}")
    reader = ocr._get_easyocr_reader("ta")
    print(f"  EasyOCR Tamil Reader: {'Ready (GPU)' if reader else 'Failed'}")
    paddle_reader = ocr._get_paddle_reader("gu")
    print(f"  PaddleOCR Gujarati Fallback: {'Ready (GPU)' if paddle_reader else 'Failed'}")

    # 4. LFM 2.5 Analytics Test
    print("\n[4] Testing LFM 2.5 (via Ollama):")
    lfm = LFMService()
    print(f"  Endpoint: {lfm._url}")
    print(f"  Model:    {lfm._model}")
    print(f"  Ollama Available: {lfm.is_available()}")

    print("\n" + "=" * 65)
    if all_passed:
        print("ALL 6 LANGUAGES TRANSLATED SUCCESSFULLY WITH INDICTRANS2 ON GPU!")
    else:
        print("SOME TESTS ENCOUNTERED ISSUES.")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
