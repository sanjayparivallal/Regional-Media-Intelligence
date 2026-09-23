"""
Image Preprocessing Service.

Fast adaptive preprocessing pipeline for OCR.

Key design principles:
- All quality assessment runs on a DOWNSCALED thumbnail (max 800 px),
  so Laplacian / HoughLinesP operate on ~0.1 MP instead of 8+ MP.
- Denoising is intentionally skipped — cv2.fastNlMeansDenoising is
  extremely slow on large images (90-180 s) and provides negligible
  benefit for newspaper OCR.
- Deskew angle is detected on the thumbnail; rotation is then applied
  to the full-resolution image (fast affine warp).
- If no preprocessing is needed the original path is returned immediately
  without any disk I/O.
- Original image is NEVER modified — a _processed copy is saved.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Maximum dimension used for all quality assessment calculations.
# Keeps HoughLinesP / Laplacian fast regardless of source image size.
_ASSESS_MAX_DIM = 800


@dataclass
class ImageQualityReport:
    """Quality assessment of an image."""
    brightness: float       # 0-255
    contrast: float         # 0-100
    sharpness: float        # 0-100
    noise_level: float      # 0-100
    is_skewed: bool
    skew_angle: float
    needs_preprocessing: bool
    recommended_operations: list

    def to_dict(self) -> dict:
        return {
            "brightness": round(self.brightness, 1),
            "contrast": round(self.contrast, 1),
            "sharpness": round(self.sharpness, 1),
            "noise_level": round(self.noise_level, 1),
            "is_skewed": self.is_skewed,
            "skew_angle": round(self.skew_angle, 2),
            "needs_preprocessing": self.needs_preprocessing,
            "recommended_operations": self.recommended_operations,
        }


class ImagePreprocessingService:
    """
    Fast adaptive image preprocessing for OCR.

    All quality checks run on a tiny thumbnail so large newspaper
    scans are assessed in < 0.5 s instead of 60-180 s.
    Only contrast enhancement and deskew are applied; denoising is
    intentionally omitted (too slow, negligible OCR benefit on newsprint).
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_thumbnail(gray: np.ndarray, max_dim: int = _ASSESS_MAX_DIM) -> np.ndarray:
        """Return a downscaled grayscale copy for fast analysis."""
        import cv2
        h, w = gray.shape[:2]
        biggest = max(h, w)
        if biggest <= max_dim:
            return gray
        scale = max_dim / biggest
        return cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))),
                          interpolation=cv2.INTER_AREA)

    def _detect_skew(self, gray_thumb: np.ndarray) -> float:
        """Detect skew angle using HoughLinesP on a THUMBNAIL (fast)."""
        import cv2
        edges = cv2.Canny(gray_thumb, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80,
                                minLineLength=50, maxLineGap=10)
        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            try:
                coords = line[0] if hasattr(line, "__len__") and len(line) > 0 else line
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                    if abs(angle) < 15:
                        angles.append(angle)
            except Exception:
                continue

        return float(np.median(angles)) if angles else 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess_quality(self, image_path: str) -> ImageQualityReport:
        """
        Assess image quality to determine what preprocessing is needed.

        All heavy operations run on a small thumbnail so this returns in
        well under 1 second even for large full-page newspaper scans.

        Args:
            image_path: Path to the image file

        Returns:
            ImageQualityReport with quality metrics and recommendations.
            Note: 'denoising' is NEVER recommended — it is too slow and
            offers negligible benefit for newspaper OCR.
        """
        import cv2

        image = cv2.imread(image_path)
        if image is None:
            return ImageQualityReport(
                brightness=0, contrast=0, sharpness=0, noise_level=0,
                is_skewed=False, skew_angle=0,
                needs_preprocessing=False,
                recommended_operations=[],
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # All metric computation on thumbnail — fast regardless of source size
        thumb = self._make_thumbnail(gray)

        brightness = float(np.mean(thumb))
        contrast = float(np.std(thumb))

        # Sharpness via Laplacian variance (thumbnail)
        laplacian = cv2.Laplacian(thumb, cv2.CV_64F)
        sharpness_normalized = min(float(laplacian.var()) / 100, 100)

        # Noise estimate via median absolute deviation (thumbnail)
        median_val = np.median(thumb)
        mad = np.median(np.abs(thumb.astype(float) - median_val))
        noise_level = float(mad)

        # Skew — HoughLinesP on thumbnail
        skew_angle = self._detect_skew(thumb)
        is_skewed = abs(skew_angle) > 1.0

        operations = []
        needs = False

        if brightness < 80 or brightness > 210 or contrast < 40:
            operations.append("contrast_enhancement")
            needs = True

        if is_skewed:
            operations.append("deskew")
            needs = True

        # NOTE: "denoising" intentionally excluded — cv2.fastNlMeansDenoising
        # is O(n²) on large images and takes 60-180 s on full newspaper pages.
        # Sharpening is also skipped as it rarely helps EasyOCR on newsprint.

        return ImageQualityReport(
            brightness=brightness,
            contrast=contrast,
            sharpness=sharpness_normalized,
            noise_level=noise_level,
            is_skewed=is_skewed,
            skew_angle=skew_angle,
            needs_preprocessing=needs,
            recommended_operations=list(dict.fromkeys(operations)),  # dedupe, preserve order
        )

    def preprocess(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        operations: Optional[list] = None,
    ) -> str:
        """
        Apply adaptive preprocessing to an image.

        Only contrast enhancement and deskew are applied.
        All operations work on a grayscale version of the image for speed.
        The original file is NEVER modified.

        Args:
            image_path: Path to the original image
            output_path: Destination for processed image (auto-generated if None)
            operations: Specific operations list; None = auto-detect from quality report

        Returns:
            Path to processed image, or original path if no processing needed.
        """
        import cv2

        if operations is None:
            quality = self.assess_quality(image_path)
            operations = quality.recommended_operations

        if not operations:
            # Nothing to do — return original immediately (no disk I/O)
            return image_path

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

        # Detect skew angle from thumbnail (if deskew will be applied)
        skew_angle = 0.0
        if "deskew" in operations:
            thumb = self._make_thumbnail(gray)
            skew_angle = self._detect_skew(thumb)

        # Apply operations in order
        for op in operations:
            if op == "contrast_enhancement":
                # CLAHE on full-resolution grayscale — fast (single pass)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray = clahe.apply(gray)

            elif op == "deskew":
                if abs(skew_angle) > 0.5:
                    h, w = gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                    gray = cv2.warpAffine(
                        gray, M, (w, h),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE,
                    )

            # "denoising", "sharpening", "threshold", "grayscale" — intentionally skipped
            # for performance reasons. Add back only if accuracy benchmarks justify it.

        if output_path is None:
            p = Path(image_path)
            output_path = str(p.parent / f"{p.stem}_processed{p.suffix}")

        cv2.imwrite(output_path, gray)
        logger.debug(f"Preprocessed image saved: {output_path} (ops: {operations})")
        return output_path
