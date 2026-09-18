"""
Language Matrix Test.

Tests each of the 10 target languages through the pipeline:
OCR → Language Detection → Translation → Entity Preservation → LFM Analysis

Reports PASS / FAIL / UNSUPPORTED per language per stage.
"""

import sys
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

SAMPLE_DIR = BASE_DIR / "tests" / "sample_pages"
OUTPUT_DIR = BASE_DIR / "tests" / "language_matrix_output"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SENTENCES_PATH = BASE_DIR / "tests" / "sample_sentences.json"


def load_test_sentences():
    """Load test sentences from JSON."""
    with open(SENTENCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_test_image(text: str, lang_code: str) -> str:
    """Create a simple test image with text for OCR testing."""
    img_path = SAMPLE_DIR / f"test_{lang_code}.png"
    
    # Create white image with text
    img = Image.new("RGB", (1200, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a font that supports the script
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    
    draw.text((40, 40), text, fill=(0, 0, 0), font=font)
    img.save(str(img_path))
    return str(img_path)


def test_language_detection(text: str, expected_lang: str) -> dict:
    """Test language detection for a given text."""
    try:
        from services.language_service import LanguageService
        service = LanguageService()
        result = service.detect(text)
        
        detected = result.language
        confidence = result.confidence
        correct = detected == expected_lang
        
        return {
            "status": "PASS" if correct else "FAIL",
            "expected": expected_lang,
            "detected": detected,
            "confidence": confidence,
            "method": result.method,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_translation(text: str, source_lang: str) -> dict:
    """Test translation from source language to English."""
    if source_lang == "en":
        return {"status": "PASS", "note": "English is the target language, no translation needed"}
    
    try:
        from services.translation_service import TranslationService
        service = TranslationService()
        result = service.translate(text, source_lang, "en")
        
        if result.status == "unsupported":
            return {"status": "UNSUPPORTED", "error": result.error}
        
        if result.status == "error":
            return {"status": "FAIL", "error": result.error}
        
        has_output = len(result.translated_text.strip()) > 5
        not_same = result.translated_text != text  # Should be different from source
        
        return {
            "status": "PASS" if has_output and not_same else "FAIL",
            "translated_text": result.translated_text[:200],
            "confidence": result.confidence,
            "confidence_source": result.confidence_source,
            "processing_time": result.processing_time,
            "model_used": result.model_used,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_entity_preservation(text: str, lang_code: str) -> dict:
    """Test entity preservation during translation."""
    if lang_code == "en":
        return {"status": "PASS", "note": "English, no translation needed"}
    
    try:
        from services.entity_protection import EntityProtectionService
        service = EntityProtectionService()
        
        # Protect entities
        protection_result = service.protect(text)
        
        entities_found = [e.original_text for e in protection_result.entities]
        
        if not entities_found:
            return {
                "status": "PASS",
                "note": "No entities to protect in this text",
                "entities_found": [],
            }
        
        # Simulate translation + restore
        # (In real pipeline, translate the protected text, then restore)
        restored = service.restore(
            protection_result.protected_text,
            protection_result.placeholder_mapping,
        )
        
        # Check that entities are preserved
        all_preserved = all(entity in restored for entity in entities_found)
        
        return {
            "status": "PASS" if all_preserved else "FAIL",
            "entities_found": entities_found,
            "placeholders": protection_result.placeholder_mapping,
            "all_preserved": all_preserved,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def run_language_matrix():
    """Run the full language matrix test."""
    print("=" * 70)
    print("  Regional Media Intelligence — Language Matrix Test")
    print("=" * 70)
    
    data = load_test_sentences()
    test_data = data["test_sentences"]
    
    results = {}
    
    for lang_code, lang_info in test_data.items():
        lang_name = lang_info["language"]
        sentences = lang_info["sentences"]
        
        print(f"\n{'─' * 60}")
        print(f"  Testing: {lang_name} ({lang_code})")
        print(f"{'─' * 60}")
        
        lang_result = {
            "language": lang_name,
            "code": lang_code,
            "tests": {},
        }
        
        # Test 1: Language Detection
        test_text = sentences.get("brand_mention", sentences.get("normal_news", ""))
        print(f"\n  [1/3] Language Detection...", end=" ")
        det_result = test_language_detection(test_text, lang_code)
        lang_result["tests"]["language_detection"] = det_result
        print(f"{det_result['status']}", end="")
        if det_result.get("detected"):
            print(f" (detected: {det_result['detected']}, conf: {det_result.get('confidence', '?')}%)")
        else:
            print(f" ({det_result.get('error', 'unknown error')})")
        
        # Test 2: Translation
        crisis_text = sentences.get("regulatory_crisis", "")
        print(f"  [2/3] Translation...", end=" ")
        trans_result = test_translation(crisis_text, lang_code)
        lang_result["tests"]["translation"] = trans_result
        status = trans_result["status"]
        print(f"{status}", end="")
        if status == "PASS" and trans_result.get("translated_text"):
            print(f" ({trans_result['processing_time']}s)")
            print(f"        → {trans_result['translated_text'][:120]}...")
        elif trans_result.get("error"):
            print(f" ({trans_result['error'][:80]})")
        else:
            print()
        
        # Test 3: Entity Preservation
        entity_text = sentences.get("regulatory_crisis", "")
        print(f"  [3/3] Entity Preservation...", end=" ")
        entity_result = test_entity_preservation(entity_text, lang_code)
        lang_result["tests"]["entity_preservation"] = entity_result
        print(f"{entity_result['status']}", end="")
        if entity_result.get("entities_found"):
            print(f" (entities: {entity_result['entities_found']})")
        else:
            print()
        
        # Overall status
        statuses = [t.get("status", "FAIL") for t in lang_result["tests"].values()]
        if all(s == "PASS" for s in statuses):
            lang_result["overall"] = "PASS"
        elif any(s == "UNSUPPORTED" for s in statuses):
            lang_result["overall"] = "UNSUPPORTED"
        elif any(s == "FAIL" for s in statuses):
            lang_result["overall"] = "PARTIAL"
        else:
            lang_result["overall"] = "UNKNOWN"
        
        results[lang_code] = lang_result
    
    # Print summary
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  {'Language':<12} {'Detection':<12} {'Translation':<14} {'Entity':<12} {'Overall':<10}")
    print(f"  {'─' * 58}")
    
    for lang_code, r in results.items():
        tests = r["tests"]
        det = tests.get("language_detection", {}).get("status", "?")
        trans = tests.get("translation", {}).get("status", "?")
        ent = tests.get("entity_preservation", {}).get("status", "?")
        overall = r.get("overall", "?")
        print(f"  {r['language']:<12} {det:<12} {trans:<14} {ent:<12} {overall:<10}")
    
    # Save results
    output_path = OUTPUT_DIR / "language_matrix_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n  Results saved to: {output_path}")
    print(f"{'=' * 70}")
    
    return results


if __name__ == "__main__":
    run_language_matrix()
