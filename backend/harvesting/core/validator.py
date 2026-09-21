"""
PDF Validator.

Validates a downloaded file is a genuine, openable PDF.

Checks:
    1. File exists
    2. File size > minimum
    3. Starts with %PDF signature
    4. PyMuPDF can open it
    5. At least one page exists
"""

import enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_PDF_BYTES = 1_024  # 1 KB
PDF_HEADER = b"%PDF"


class ValidationStatus(str, enum.Enum):
    VALID       = "VALID"
    EMPTY_FILE  = "EMPTY_FILE"
    INVALID_PDF = "INVALID_PDF"
    NOT_FOUND   = "NOT_FOUND"


class PDFValidator:
    """Validates a PDF file after download."""

    def validate(self, file_path: Path) -> ValidationStatus:
        """
        Validate a PDF file.

        Returns:
            ValidationStatus enum value.
        """
        if not file_path.exists():
            logger.warning(f"Validation: file not found: {file_path}")
            return ValidationStatus.NOT_FOUND

        size = file_path.stat().st_size
        if size < MIN_PDF_BYTES:
            logger.warning(f"Validation: file too small ({size} bytes): {file_path}")
            return ValidationStatus.EMPTY_FILE

        # Check magic bytes
        with open(file_path, "rb") as f:
            header = f.read(4)
        if header != PDF_HEADER:
            logger.warning(f"Validation: not a PDF (header={header!r}): {file_path}")
            return ValidationStatus.INVALID_PDF

        # Try opening with PyMuPDF
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            page_count = len(doc)
            doc.close()
            if page_count < 1:
                logger.warning(f"Validation: PDF has no pages: {file_path}")
                return ValidationStatus.INVALID_PDF
        except Exception as e:
            logger.warning(f"Validation: PyMuPDF could not open PDF: {e}: {file_path}")
            return ValidationStatus.INVALID_PDF

        logger.info(f"Validation: OK ({size:,} bytes, {page_count} pages): {file_path}")
        return ValidationStatus.VALID
