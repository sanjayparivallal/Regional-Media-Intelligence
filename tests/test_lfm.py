import os
import sys
import time
import json
import urllib.request
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "LiquidAI/lfm2.5-2.6b:q4_k_m"

def test_lfm_reasoning():
    print("==================================================")
    print("Testing Local Reasoning Model via Ollama (Liquid LFM2.5-2.6B)")
    print("==================================================")
    
    prompt = (
        "You are an expert news intelligence analyst. Extract entities, brand sentiment, and crisis risk from article text. "
        "Respond ONLY with valid JSON.\n\n"
        "Article: Tata Motors failed to build EV battery plant in Tamil Nadu, creating 5,000 jobs.\n"
        "Extract structured JSON with keys: 'entities' (list of brands/orgs), 'sentiment' (Positive/Negative/Neutral), 'crisis_risk' (Low/Medium/High), 'summary'."
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    print(f"Sending request to local Ollama model: {MODEL_NAME}...")
    start_time = time.time()

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            response_text = res_json.get('response', '')
            
        infer_time = time.time() - start_time
        print(f"Inference Time: {infer_time:.2f}s")
        print(f"\nModel Output:\n{response_text}")

        output_dir = Path("d:/Vee_Project/tests/lfm_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "lfm_result.json", "w", encoding="utf-8") as f:
            f.write(response_text)

        print("\nSUCCESS: LFM reasoning test via Ollama completed.")
        return True

    except Exception as e:
        print(f"\nFAILURE: Error testing LFM model via Ollama: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_lfm_reasoning()
