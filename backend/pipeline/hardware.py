"""
Hardware Detection Module.

Detects CPU, RAM, GPU, and VRAM to choose appropriate model sizes.
"""

import platform
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def detect_hardware() -> dict:
    """Detect available hardware for model selection."""
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1) if HAS_PSUTIL else 8.0
    ram_avail = round(psutil.virtual_memory().available / (1024 ** 3), 1) if HAS_PSUTIL else 4.0

    info = {
        "cpu": platform.processor() or platform.machine(),
        "cpu_cores": os.cpu_count() or 1,
        "ram_gb": ram_gb,
        "ram_available_gb": ram_avail,
        "os": platform.system(),
        "gpu_available": False,
        "gpu_name": None,
        "vram_gb": None,
        "cuda_available": False,
        "recommended_tier": "cpu_light",  # cpu_light, cpu_full, gpu_light, gpu_full
    }

    # Check for CUDA GPU
    try:
        import torch
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["gpu_available"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_mem / (1024 ** 3), 1)

            if info["vram_gb"] >= 8:
                info["recommended_tier"] = "gpu_full"
            else:
                info["recommended_tier"] = "gpu_light"
        else:
            if info["ram_gb"] >= 16:
                info["recommended_tier"] = "cpu_full"
            else:
                info["recommended_tier"] = "cpu_light"
    except ImportError:
        if info["ram_gb"] >= 16:
            info["recommended_tier"] = "cpu_full"
        else:
            info["recommended_tier"] = "cpu_light"

    return info


def get_model_recommendations(hw_info: dict = None) -> dict:
    """Get model size recommendations based on hardware."""
    if hw_info is None:
        hw_info = detect_hardware()

    tier = hw_info.get("recommended_tier", "cpu_light")

    recommendations = {
        "gpu_full": {
            "ocr": "paddleocr",
            "translation": "facebook/nllb-200-distilled-600M",
            "sentiment": "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual",
            "ner": "spacy_transformer",
            "use_gpu": True,
        },
        "gpu_light": {
            "ocr": "paddleocr",
            "translation": "facebook/nllb-200-distilled-600M",
            "sentiment": "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual",
            "ner": "spacy_sm",
            "use_gpu": True,
        },
        "cpu_full": {
            "ocr": "paddleocr",
            "translation": "facebook/nllb-200-distilled-600M",
            "sentiment": "lexicon",
            "ner": "spacy_sm",
            "use_gpu": False,
        },
        "cpu_light": {
            "ocr": "tesseract",
            "translation": "fallback",
            "sentiment": "lexicon",
            "ner": "regex",
            "use_gpu": False,
        },
    }

    return recommendations.get(tier, recommendations["cpu_light"])
