"""
Image Preprocessing Service.

Adaptive preprocessing pipeline that checks image quality first
and only applies necessary operations.
Preserves the original image — never overwrites evidence.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ImageQualityReport:
    """Quality assessment of an image."""
    brightness: float  # 0-255
    contrast: float  # 0-100
    sharpness: float  # 0-100
    noise_level: float  # 0-100
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
    Adaptive image preprocessing for OCR.

    Only applies necessary preprocessing based on quality assessment.
    Preserves original images — processes a copy.
    """

    def assess_quality(self, image_path: str) -> ImageQualityReport:
        """
        Assess image quality to determine what preprocessing is needed.

        Args:
            image_path: Path to the image file

        Returns:
            ImageQualityReport with quality metrics and recommendations
        """
        import cv2

        image = cv2.imread(image_path)
        if image is None:
            return ImageQualityReport(
                brightness=0, contrast=0, sharpness=0, noise_level=0,
                is_skewed=False, skew_angle=0,
                needs_preprocessing=True,
                recommended_operations=["image_load_failed"],
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Brightness
        brightness = float(np.mean(gray))

        # Contrast (standard deviation of pixel values)
        contrast = float(np.std(gray))

        # Sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())
        sharpness_normalized = min(sharpness / 100, 100)

        # Noise estimate (using median absolute deviation)
        median = np.median(gray)
        mad = np.median(np.abs(gray.astype(float) - median))
        noise_level = float(mad)

        # Skew detection
        skew_angle = self._detect_skew(gray)
        is_skewed = abs(skew_angle) > 1.0

        # Determine recommendations
        operations = []
        needs = False

        if brightness < 80 or brightness > 200:
            operations.append("contrast_enhancement")
            needs = True

        if contrast < 40:
            operations.append("contrast_enhancement")
            needs = True

        if sharpness_normalized < 10:
            operations.append("sharpening")
            needs = True

        if noise_level > 30:
            operations.append("denoising")
            needs = True

        if is_skewed:
            operations.append("deskew")
            needs = True

        return ImageQualityReport(
            brightness=brightness,
            contrast=contrast,
            sharpness=sharpness_normalized,
            noise_level=noise_level,
            is_skewed=is_skewed,
            skew_angle=skew_angle,
            needs_preprocessing=needs,
            recommended_operations=list(set(operations)),
        )

    def preprocess(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        operations: Optional[list] = None,
    ) -> str:
        """
        Apply adaptive preprocessing to an image.

        Args:
            image_path: Path to the original image
            output_path: Where to save the processed image (original is never modified)
            operations: Specific operations to apply. If None, auto-determines from quality assessment.

        Returns:
            Path to the processed image
        """
        import cv2

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        # Auto-assess if no operations specified
        if operations is None:
            quality = self.assess_quality(image_path)
            operations = quality.recommended_operations

        if not operations:
            # No preprocessing needed — return original
            return image_path

        # Work on a copy
        processed = image.copy()

        for op in operations:
            if op == "grayscale":
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

            elif op == "contrast_enhancement":
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                processed = clahe.apply(processed)

            elif op == "denoising":
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                processed = cv2.fastNlMeansDenoising(processed, None, 10, 7, 21)

            elif op == "sharpening":
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
                processed = cv2.filter2D(processed, -1, kernel)

            elif op == "deskew":
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                angle = self._detect_skew(processed)
                if abs(angle) > 0.5:
                    h, w = processed.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    processed = cv2.warpAffine(
                        processed, M, (w, h),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE,
                    )

            elif op == "threshold":
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                processed = cv2.adaptiveThreshold(
                    processed, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2,
                )

        # Save processed image
        if output_path is None:
            p = Path(image_path)
            output_path = str(p.parent / f"{p.stem}_processed{p.suffix}")

        cv2.imwrite(output_path, processed)
        logger.info(f"Preprocessed image saved: {output_path} (operations: {operations})")

        return output_path

    def _detect_skew(self, gray: np.ndarray) -> float:
        """Detect skew angle using Hough transform."""
        import cv2

        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

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

        if not angles:
            return 0.0

        return float(np.median(angles))
