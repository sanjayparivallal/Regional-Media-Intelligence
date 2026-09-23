"""
OCR Service.

Unified OCR interface with language-routed provider selection.
Respects ocr_engine from configuration (defaulting to 'indic-ocr' via EasyOCR architecture
with Indic-OCR models), and supports PaddleOCR fallback for languages like Gujarati and Malayalam.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from config import get_settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class OCRBlock:
    """Single OCR text detection with bounding box."""
    text: str
    confidence: float
    bounding_box: List[List[int]]
    line_num: int = 0


@dataclass
class OCRServiceResult:
    """Structured OCR result matching the specified output format."""
    text: str
    language_hint: Optional[str]
    confidence: Optional[float]
    blocks: List[OCRBlock] = field(default_factory=list)
    bounding_boxes: List[Dict] = field(default_factory=list)
    processing_time: float = 0.0
    engine: str = ""
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "language_hint": self.language_hint,
            "confidence": self.confidence,
            "blocks": [
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "bounding_box": b.bounding_box,
                    "line_num": b.line_num,
                }
                for b in self.blocks
            ],
            "bounding_boxes": self.bounding_boxes,
            "processing_time": self.processing_time,
            "engine": self.engine,
            "status": self.status,
            "error": self.error,
        }


class OCRService:
    """
    Unified OCR service with language-routed provider selection.

    Uses Indic-OCR (via EasyOCR engine & models) for: en, hi, bn, mr, te, ta, ur, kn
    Uses PaddleOCR for: gu, ml (where Indic-OCR fallback is needed)
    """

    def __init__(self):
        self._indicocr_readers: Dict[str, Any] = {}
        self._easyocr_readers = self._indicocr_readers
        self._paddle_reader = None
        self._gpu_available = False
        self._settings = get_settings()

        # Resolve configured OCR model path for Indic-OCR
        model_cfg_path = Path(self._settings.ocr_model_path)
        if not model_cfg_path.is_absolute():
            self._model_dir = (BASE_DIR / model_cfg_path).resolve()
        else:
            self._model_dir = model_cfg_path.resolve()
        self._model_dir.mkdir(parents=True, exist_ok=True)

        self._configured_engine = (self._settings.ocr_engine or "indic-ocr").strip().lower()
        logger.info(f"OCRService: Configured OCR engine is '{self._configured_engine}' (model_dir={self._model_dir})")

        try:
            import torch
            self._gpu_available = torch.cuda.is_available()
            if self._gpu_available:
                logger.info(f"OCRService: GPU detected — {torch.cuda.get_device_name(0)}")
            else:
                logger.info("OCRService: No GPU detected, running on CPU")
        except ImportError:
            pass

        # Choose batch size and image dim limit based on GPU availability
        self._batch_size = (
            self._settings.ocr_batch_size_gpu if self._gpu_available
            else self._settings.ocr_batch_size_cpu
        )
        self._max_image_dim = (
            self._settings.ocr_max_image_dim if self._gpu_available
            else 1600
        )

    def _get_indicocr_reader(self, language: str):
        """Get or create an Indic-OCR reader for a specific language."""
        from services.language_config import get_language_registry
        registry = get_language_registry()

        lang_cfg = registry.get(language) if language else None
        easyocr_code = lang_cfg.easyocr_code if lang_cfg else (language or "ta")

        if not easyocr_code:
            easyocr_code = "ta"

        # Build the language list for Indic-OCR (bilingual regional + English)
        lang_list = [easyocr_code]
        if "en" not in lang_list and easyocr_code != "en":
            lang_list.append("en")
        key = (tuple(sorted(lang_list)), bool(self._gpu_available))

        if key not in self._indicocr_readers:
            reader = self._init_indicocr_reader(list(key[0]), use_gpu=self._gpu_available)
            if reader is not None:
                self._indicocr_readers[key] = reader
            elif key[0] != ("en",):
                return self._get_indicocr_reader("en")
            else:
                return None

        return self._indicocr_readers.get(key)

    # Alias for backward compatibility
    _get_easyocr_reader = _get_indicocr_reader

    def _init_indicocr_reader(self, lang_list: list, use_gpu: bool):
        """
        Initialize an Indic-OCR reader with GPU, falling back to CPU on failure.

        EasyOCR 1.7.x with PyTorch 2.x / cuDNN 9 can fail with
        cudaErrorSharedObjectInitFailed when DataParallel wraps the LSTM
        recognizer. Disabling cudnn.benchmark prevents this. If GPU init
        still fails (e.g. another process holds the CUDA context), we retry
        on CPU so OCR always proceeds.
        """
        import easyocr

        # Patch EasyOCR 1.7.2 Tamil character definition if missing Tamil numerals/symbols
        if "ta" in lang_list:
            import easyocr.config as cfg
            tamil_cfg = cfg.recognition_models.get("gen1", {}).get("tamil_g1", {})
            if "characters" in tamil_cfg and len(tamil_cfg["characters"]) == 126:
                extra_chars = "".join(chr(c) for c in range(0x0BE6, 0x0BF6))
                tamil_cfg["characters"] += extra_chars

        # Disable cudnn benchmark mode — prevents cudaErrorSharedObjectInitFailed
        # in LSTM flatten_parameters() with PyTorch 2.x + cuDNN 9.
        try:
            import torch
            torch.backends.cudnn.benchmark = False
        except Exception:
            pass

        if use_gpu:
            try:
                reader = easyocr.Reader(
                    lang_list,
                    gpu=True,
                    model_storage_directory=str(self._model_dir),
                    download_enabled=True,
                    verbose=False,
                )
                logger.info(f"Initialized Indic-OCR reader: {lang_list} on GPU (model_dir={self._model_dir})")
                return reader
            except Exception as e:
                logger.warning(
                    f"Indic-OCR GPU init failed ({e}), retrying on CPU. "
                    f"This is a known EasyOCR 1.7.x/PyTorch 2.x cuDNN issue."
                )
                self._gpu_available = False  # Mark GPU as unavailable for subsequent pages

        # CPU fallback (or initial CPU path)
        try:
            reader = easyocr.Reader(
                lang_list,
                gpu=False,
                model_storage_directory=str(self._model_dir),
                download_enabled=True,
                verbose=False,
            )
            logger.info(f"Initialized Indic-OCR reader: {lang_list} on CPU (model_dir={self._model_dir})")
            return reader
        except Exception as e:
            logger.error(f"Indic-OCR CPU init also failed for {lang_list}: {e}")
            return None

    # Alias for backward compatibility
    _init_easyocr_reader = _init_indicocr_reader

    def _get_paddle_reader(self, language: str):
        """Get PaddleOCR reader for fallback languages (Gujarati, Malayalam)."""
        if self._paddle_reader is not None:
            return self._paddle_reader

        try:
            from paddleocr import PaddleOCR

            # PaddleOCR language mapping
            paddle_lang_map = {
                "gu": "devanagari",
                "ml": "devanagari",
            }

            paddle_lang = paddle_lang_map.get(language, "en")
            self._paddle_reader = PaddleOCR(
                use_angle_cls=True,
                lang=paddle_lang,
                use_gpu=self._gpu_available,
                show_log=False,
            )
            logger.info(f"Initialized PaddleOCR reader for: {language}")
            return self._paddle_reader
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            return None

    def process_page(
        self,
        image_path: str,
        language: str | None = None,
    ) -> OCRServiceResult:
        """
        Process a page image through OCR.

        Args:
            image_path: Path to the image file
            language: ISO 639-1 language code (e.g., 'ta', 'hi').
                      If None, attempts auto-detection.

        Returns:
            OCRServiceResult with text, confidence, blocks, bounding_boxes
        """
        start_time = time.time()

        # Validate image exists
        img_path = Path(image_path)
        if not img_path.exists():
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"Image not found: {image_path}",
            )

        # Determine OCR provider based on language and configured ocr_engine
        from services.language_config import get_language_registry
        registry = get_language_registry()

        if language and not registry.is_supported(language):
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="unsupported",
                error=f"OCR model does not support this language: {language}",
            )

        effective_language = language or "ta"
        registry_provider = registry.get_ocr_provider(language) if language else "easyocr"
        configured_engine = self._configured_engine

        # Select provider based on configuration and language requirements
        if configured_engine == "paddleocr":
            selected_provider = "paddleocr"
        elif configured_engine in ("indic-ocr", "easyocr"):
            # Check if language requires paddleocr fallback (e.g. Gujarati, Malayalam)
            if registry_provider == "paddleocr":
                selected_provider = "paddleocr"
            else:
                selected_provider = "indic-ocr" if configured_engine == "indic-ocr" else "easyocr"
        else:
            # "auto" or unrecognized: fallback to language registry
            selected_provider = "indic-ocr" if registry_provider == "easyocr" else registry_provider

        try:
            if selected_provider == "paddleocr":
                return self._ocr_paddle(image_path, effective_language, start_time, engine_name="paddleocr")
            else:
                return self._ocr_indicocr(image_path, effective_language, start_time, engine_name="indic-ocr")
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"OCR failed for {image_path}: {e}")
            return OCRServiceResult(
                text="", language_hint=effective_language, confidence=None,
                processing_time=elapsed, engine=selected_provider,
                status="error", error=str(e),
            )

    def _ocr_indicocr(
        self,
        image_path: str,
        language: str,
        start_time: float,
        engine_name: str = "indic-ocr",
    ) -> OCRServiceResult:
        """Perform OCR directly using Indic-OCR with adaptive scaling and batched inference."""
        reader = self._get_indicocr_reader(language)
        if reader is None:
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"Indic-OCR reader not available for: {language}",
            )

        try:
            import torch
            if not self._gpu_available and torch.get_num_threads() < 4:
                torch.set_num_threads(min(4, os.cpu_count() or 4))
        except Exception:
            pass

        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"Failed to read image at: {image_path}",
            )

        orig_h, orig_w = img.shape[:2]
        max_dim = max(orig_h, orig_w)
        scale = 1.0

        # Scale down images exceeding max_dim; GPU uses 2000px, CPU uses 1600px
        if max_dim > self._max_image_dim:
            scale = self._max_image_dim / max_dim
            proc_w = max(1, int(orig_w * scale))
            proc_h = max(1, int(orig_h * scale))
            proc_img = cv2.resize(img, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
        else:
            proc_img = img

        # Use configured batch_size — 64 on GPU, 32 on CPU
        results = reader.readtext(proc_img, batch_size=self._batch_size)
        elapsed = round(time.time() - start_time, 2)

        blocks = []
        bounding_boxes = []
        texts = []
        confidences = []

        inv_scale = 1.0 / scale

        for idx, (bbox, text, conf) in enumerate(results):
            texts.append(text)
            confidences.append(conf)

            # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            # Rescale points back to original image coordinates
            bb = [[int(pt[0] * inv_scale), int(pt[1] * inv_scale)] for pt in bbox]
            blocks.append(OCRBlock(
                text=text,
                confidence=round(float(conf) * 100, 2),
                bounding_box=bb,
                line_num=idx,
            ))
            bounding_boxes.append({
                "points": bb,
                "text": text,
                "confidence": round(float(conf) * 100, 2),
            })

        full_text = "\n".join(texts)
        avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else None

        return OCRServiceResult(
            text=full_text,
            language_hint=language,
            confidence=avg_conf,
            blocks=blocks,
            bounding_boxes=bounding_boxes,
            processing_time=elapsed,
            engine=engine_name,
        )

    # Alias for backward compatibility
    _ocr_easyocr = _ocr_indicocr

    def _ocr_paddle(
        self,
        image_path: str,
        language: str,
        start_time: float,
        engine_name: str = "paddleocr",
    ) -> OCRServiceResult:
        """Perform OCR using PaddleOCR (fallback for Gujarati, Malayalam)."""
        reader = self._get_paddle_reader(language)
        if reader is None:
            return OCRServiceResult(
                text="", language_hint=language, confidence=None,
                status="error", error=f"PaddleOCR reader not available for: {language}",
            )

        result = reader.ocr(image_path, cls=True)
        elapsed = round(time.time() - start_time, 2)

        blocks = []
        bounding_boxes = []
        texts = []
        confidences = []

        if result and result[0]:
            for idx, line in enumerate(result[0]):
                bbox_pts, (text, conf) = line
                texts.append(text)
                confidences.append(conf)

                bb = [[int(p[0]), int(p[1])] for p in bbox_pts]
                blocks.append(OCRBlock(
                    text=text,
                    confidence=round(float(conf) * 100, 2),
                    bounding_box=bb,
                    line_num=idx,
                ))
                bounding_boxes.append({
                    "points": bb,
                    "text": text,
                    "confidence": round(float(conf) * 100, 2),
                })

        full_text = "\n".join(texts)
        avg_conf = round(sum(confidences) / len(confidences) * 100, 2) if confidences else None

        return OCRServiceResult(
            text=full_text,
            language_hint=language,
            confidence=avg_conf,
            blocks=blocks,
            bounding_boxes=bounding_boxes,
            processing_time=elapsed,
            engine=engine_name,
        )

    def get_supported_languages(self) -> Dict[str, dict]:
        """Return which languages are supported and by which engine."""
        from services.language_config import get_language_registry
        registry = get_language_registry()

        result = {}
        for lang in registry.get_enabled():
            provider = lang.ocr_provider
            if provider == "easyocr" and self._configured_engine == "indic-ocr":
                provider = "indic-ocr"
            result[lang.code] = {
                "name": lang.name,
                "script": lang.script,
                "ocr_provider": provider,
                "easyocr_supported": lang.easyocr_code is not None,
                "note": lang.ocr_note,
            }
        return result
