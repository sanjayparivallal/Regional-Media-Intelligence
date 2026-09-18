import os
import sys
import time
import json
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

MODEL_DIR = Path("d:/Vee_Project/models/indictrans2")

def test_translation():
    print("==================================================")
    print("Testing Local Translation (NLLB-200 Distilled 600M)")
    print("==================================================")
    
    if not MODEL_DIR.exists() or not (MODEL_DIR / "pytorch_model.bin").exists():
        print(f"ERROR: Model weights not found in {MODEL_DIR}")
        return False

    print(f"Loading local model from: {MODEL_DIR}...")
    start_time = time.time()
    
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

        tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(str(MODEL_DIR), local_files_only=True)
        
        load_time = time.time() - start_time
        print(f"Model loaded successfully in {load_time:.2f}s")
        
        test_cases = [
            {
                "lang": "Tamil",
                "src_code": "tam_Tam",
                "tgt_code": "eng_Latn",
                "text": "வணக்கம்! சென்னை மற்றும் தமிழக செய்திகளை உடனுக்குடன் தெரிந்து கொள்ளுங்கள்."
            },
            {
                "lang": "Hindi",
                "src_code": "hin_Deva",
                "tgt_code": "eng_Latn",
                "text": "नमस्कार! आज की मुख्य समाचार और विश्लेषण पढ़ें।"
            }
        ]
        
        results = []
        for case in test_cases:
            t0 = time.time()
            translator = pipeline(
                'translation',
                model=model,
                tokenizer=tokenizer,
                src_lang=case["src_code"],
                tgt_lang=case["tgt_code"],
                max_length=400
            )
            out = translator(case["text"])
            infer_time = time.time() - t0
            
            translated_text = out[0]['translation_text'] if out else ""
            print(f"\n--- [{case['lang']}] Translation Test ---")
            print(f"Source Text:     {case['text']}")
            print(f"Translated Text: {translated_text}")
            print(f"Inference Time:  {infer_time:.2f}s")
            
            results.append({
                "language": case["lang"],
                "source": case["text"],
                "translation": translated_text,
                "latency_sec": round(infer_time, 2)
            })
            
        output_dir = Path("d:/Vee_Project/tests/translation_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "translation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print("\nSUCCESS: Translation test completed. Results saved to tests/translation_output/translation_results.json")
        return True
    except Exception as e:
        print(f"\nFAILURE: Error testing translation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_translation()
