"""
Image Preprocessing Module.

Multi-variant preprocessing for OCR quality improvement.
Generates multiple preprocessing candidates and evaluates them
to find the best result — trial-and-error engineering.
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingVariant:
    name: str
    description: str
    image: np.ndarray
    operations: List[str]


def generate_preprocessing_variants(image: np.ndarray) -> List[PreprocessingVariant]:
    """
    Generate multiple preprocessing variants for trial-and-error OCR.
    Returns variants that can be OCR'd and compared.
    """
    import cv2

    variants = []

    # Original
    variants.append(PreprocessingVariant(
        name="original",
        description="Original image without preprocessing",
        image=image.copy(),
        operations=[],
    ))

    # Variant A: Grayscale + contrast
    try:
        gray = _to_grayscale(image)
        enhanced = _enhance_contrast(gray)
        variants.append(PreprocessingVariant(
            name="grayscale_contrast",
            description="Grayscale with CLAHE contrast enhancement",
            image=enhanced,
            operations=["grayscale", "contrast_enhancement"],
        ))
    except Exception as e:
        logger.warning(f"Variant A failed: {e}")

    # Variant B: Adaptive threshold
    try:
        gray = _to_grayscale(image)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        variants.append(PreprocessingVariant(
            name="adaptive_threshold",
            description="Adaptive Gaussian thresholding",
            image=thresh,
            operations=["grayscale", "adaptive_threshold"],
        ))
    except Exception as e:
        logger.warning(f"Variant B failed: {e}")

    # Variant C: Denoise + sharpen
    try:
        gray = _to_grayscale(image)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        variants.append(PreprocessingVariant(
            name="denoise_sharpen",
            description="Non-local means denoising + sharpening",
            image=sharpened,
            operations=["grayscale", "denoise", "sharpen"],
        ))
    except Exception as e:
        logger.warning(f"Variant C failed: {e}")

    # Variant D: Deskew + threshold
    try:
        gray = _to_grayscale(image)
        deskewed = _deskew(gray)
        _, binary = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(PreprocessingVariant(
            name="deskew_otsu",
            description="Deskewing + Otsu binarization",
            image=binary,
            operations=["grayscale", "deskew", "otsu_threshold"],
        ))
    except Exception as e:
        logger.warning(f"Variant D failed: {e}")

    # Variant E: Full pipeline
    try:
        gray = _to_grayscale(image)
        enhanced = _enhance_contrast(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 8, 7, 21)
        deskewed = _deskew(denoised)
        variants.append(PreprocessingVariant(
            name="full_pipeline",
            description="Grayscale → contrast → denoise → deskew",
            image=deskewed,
            operations=["grayscale", "contrast", "denoise", "deskew"],
        ))
    except Exception as e:
        logger.warning(f"Variant E failed: {e}")

    logger.info(f"Generated {len(variants)} preprocessing variants")
    return variants


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale if needed."""
    import cv2
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE contrast enhancement."""
    import cv2
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _deskew(image: np.ndarray) -> np.ndarray:
    """Deskew image using Hough line detection."""
    import cv2

    # Detect edges
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

    if lines is None or len(lines) == 0:
        return image

    # Calculate average angle
    angles = []
    for line in lines:
        try:
            coords = line[0] if (hasattr(line, "__len__") and len(line) > 0 and hasattr(line[0], "__len__")) else line
            if len(coords) == 4:
                x1, y1, x2, y2 = coords
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 15:  # Only consider near-horizontal lines
                    angles.append(angle)
        except Exception:
            continue

    if not angles:
        return image

    median_angle = np.median(angles)

    if abs(median_angle) < 0.5:  # Skip if nearly straight
        return image

    # Rotate
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    logger.info(f"Deskewed by {median_angle:.2f}°")
    return rotated


def select_best_variant(
    variants: List[dict],
) -> dict:
    """
    Select the best preprocessing variant based on OCR results.
    Each variant dict should contain:
    - name: str
    - ocr_confidence: float
    - word_count: int
    - text: str
    """
    if not variants:
        return None

    scored = []
    for v in variants:
        score = 0.0
        # OCR confidence (most important)
        score += v.get("ocr_confidence", 0) * 0.4
        # Word count (more words = better extraction)
        word_count = v.get("word_count", 0)
        score += min(word_count / 100, 1.0) * 30  # Normalize: 100 words = max score
        # Text density
        text_len = len(v.get("text", ""))
        score += min(text_len / 500, 1.0) * 20
        # Penalize very low confidence
        if v.get("ocr_confidence", 0) < 50:
            score *= 0.5

        scored.append((score, v))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]

    logger.info(
        f"Best preprocessing variant: {best['name']} "
        f"(confidence: {best.get('ocr_confidence', 0):.1f}%)"
    )
    return best
