"""
Page Renderer Module.

Renders PDF pages as high-resolution images for OCR processing.
Handles both PDF and direct image files.
"""

import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RenderedPage:
    page_number: int
    image_path: str
    thumbnail_path: str
    width: int
    height: int
    dpi: int


def render_pdf_pages(
    file_path: str,
    output_dir: str,
    dpi: int = 180,
    thumbnail_size: int = 400,
    generate_thumbnails: bool = True,
) -> List[RenderedPage]:
    """
    Render PDF pages as PNG images at specified DPI.
    Also generates thumbnails for the UI (skipped when generate_thumbnails=False).
    """
    path = Path(file_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rendered = []

    # Handle direct image files
    if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tiff', '.tif'):
        return _handle_image_file(path, out, thumbnail_size)

    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open(file_path)

        for i, page in enumerate(doc):
            page_num = i + 1

            # Render at high DPI
            zoom = dpi / 72  # 72 is the default PDF DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save full-resolution image
            image_filename = f"page_{page_num:03d}.png"
            image_path = out / image_filename
            pix.save(str(image_path))

            # Generate thumbnail only when requested (skip during pipeline OCR runs)
            thumb_filename = f"page_{page_num:03d}_thumb.png"
            thumb_path = out / thumb_filename
            if generate_thumbnails:
                _create_thumbnail(str(image_path), str(thumb_path), thumbnail_size)

            rendered.append(RenderedPage(
                page_number=page_num,
                image_path=str(image_path),
                thumbnail_path=str(thumb_path),
                width=pix.width,
                height=pix.height,
                dpi=dpi,
            ))

            logger.info(f"Rendered page {page_num}: {pix.width}x{pix.height} @ {dpi}dpi")

        doc.close()

    except Exception as e:
        logger.error(f"Page rendering failed: {e}")
        raise

    return rendered


def _handle_image_file(
    path: Path, output_dir: Path, thumbnail_size: int
) -> List[RenderedPage]:
    """Handle direct image file uploads."""
    from PIL import Image
    import shutil

    image_path = output_dir / f"page_001{path.suffix}"
    shutil.copy2(str(path), str(image_path))

    # Get dimensions
    with Image.open(str(image_path)) as img:
        width, height = img.size

    # Create thumbnail
    thumb_path = output_dir / "page_001_thumb.png"
    _create_thumbnail(str(image_path), str(thumb_path), thumbnail_size)

    return [RenderedPage(
        page_number=1,
        image_path=str(image_path),
        thumbnail_path=str(thumb_path),
        width=width,
        height=height,
        dpi=300,
    )]


def _create_thumbnail(image_path: str, thumb_path: str, max_size: int = 400):
    """Create a thumbnail of the given image."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.thumbnail((max_size, max_size))
            img.save(thumb_path, "PNG")
    except Exception as e:
        logger.warning(f"Thumbnail creation failed: {e}")
