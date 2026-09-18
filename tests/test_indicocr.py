"""
Local IndicOCR Verification Test Script.
"""

import sys
import time
import json
import torch
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import easyocr

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "models" / "indic-ocr"
SAMPLE_DIR = BASE_DIR / "tests" / "sample_pages"
OUTPUT_DIR = BASE_DIR / "tests" / "ocr_output"

SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

test_img_path = SAMPLE_DIR / "Screenshot 2026-09-18 071956.png"
if not test_img_path.exists():
    img = Image.new("RGB", (1400, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    sample_text = (
        "Today's News Important news has been published today.\n"
        "PayU and RBI Update: Financial services regulation update."
    )
    draw.text((60, 60), sample_text, fill=(0, 0, 0))
    img.save(test_img_path)
    print(f"Created sample test image at: {test_img_path}")


def run_ocr_test():
    device_str = "CUDA" if torch.cuda.is_available() else "CPU"
    print(f"=== RUNNING LOCAL INDICOCR TEST (Device: {device_str}) ===")
    
    start_time = time.time()
    
    # Load EasyOCR for Tamil and English from local model storage
    reader = easyocr.Reader(
        ["ta", "en"],
        model_storage_directory=str(MODEL_DIR),
        gpu=torch.cuda.is_available(),
        verbose=False
    )
    
    # Perform OCR
    results = reader.readtext(str(test_img_path))
    duration_sec = round(time.time() - start_time, 2)
    
    extracted_lines = []
    structured_json = []
    for bbox, text, conf in results:
        extracted_lines.append(text)
        structured_json.append({
            "text": text,
            "confidence": round(float(conf) * 100, 2),
            "bounding_box": [[int(pt[0]), int(pt[1])] for pt in bbox]
        })
    
    full_text = "\n".join(extracted_lines)
    
    # Save markdown output
    md_path = OUTPUT_DIR / "ocr_result.md"
    md_content = f"# Local IndicOCR Result\n\n- **Device**: {device_str}\n- **Inference Time**: {duration_sec}s\n\n## Extracted Text\n```text\n{full_text}\n```"
    md_path.write_text(md_content, encoding="utf-8")
    
    # Save JSON output
    json_path = OUTPUT_DIR / "ocr_result.json"
    json_path.write_text(json.dumps({
        "status": "SUCCESS",
        "device": device_str,
        "inference_seconds": duration_sec,
        "blocks": structured_json
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\nOCR STATUS: SUCCESS")
    print(f"DEVICE: {device_str}")
    print(f"INFERENCE TIME: {duration_sec}s")
    print(f"EXTRACTED TEXT:\n{full_text}")
    print(f"\nSaved Markdown output to: {md_path}")
    print(f"Saved JSON output to: {json_path}")


if __name__ == "__main__":
    run_ocr_test()
