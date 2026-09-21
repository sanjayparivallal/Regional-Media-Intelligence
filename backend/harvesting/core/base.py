"""
Base harvester abstract class.

All harvester strategies inherit from BaseHarvester.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from harvesting.core.models import EditionConfig, NewspaperSource
from harvesting.core.downloader import PDFDownloader
from harvesting.core.validator import PDFValidator, ValidationStatus
from harvesting.utils import (
    calculate_sha256,
    get_ist_date,
    make_newspaper_storage_path,
    substitute_date_in_url,
)
from harvesting.exceptions import (
    Duplicate,
    DownloadFailed,
    EmptyFile,
    InvalidPDF,
    HarvestError,
)

logger = logging.getLogger(__name__)


class DiscoveredEdition:
    """A resolved edition: we know its PDF URL and edition metadata."""

    def __init__(
        self,
        edition: EditionConfig,
        pdf_url: str,
        target_date: date,
    ):
        self.edition = edition
        self.pdf_url = pdf_url
        self.target_date = target_date


class BaseHarvester(ABC):
    """
    Abstract base for all harvester strategies.

    Subclass contract:
        - discover_editions()   → list of editions to attempt
        - discover_pdf()        → resolve PDF URL for one edition
        - download_edition()    → full download + validate + dedup pipeline
    """

    def __init__(self, storage_root: Optional[Path] = None):
        from config import get_settings
        settings = get_settings()
        self._storage_root = storage_root or Path(settings.storage_path)
        self._downloader = PDFDownloader()
        self._validator = PDFValidator()

    @abstractmethod
    async def discover_editions(
        self,
        source: NewspaperSource,
        target_date: date,
    ) -> List[EditionConfig]:
        """Return list of editions to attempt for this source and date."""

    @abstractmethod
    async def discover_pdf(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        """Resolve and return the direct PDF download URL."""

    async def download_edition(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
        storage: "HarvestStorage",  # type: ignore
    ) -> Tuple[Path, str]:
        """
        Full pipeline for one edition:
            discover_pdf → download → validate → dedup → return (path, sha256)

        Raises harvesting exceptions on failure.
        """
        from harvesting.core.storage import HarvestStorage  # local import

        # 1. Resolve PDF URL
        pdf_url = await self.discover_pdf(source, edition, target_date)
        logger.info(
            f"source={source.id} edition={edition.edition_name} "
            f"url={pdf_url} status=DOWNLOAD_STARTED"
        )

        # 2. Build storage path
        dest_path = make_newspaper_storage_path(
            self._storage_root, source.id, target_date, edition.edition_name
        )

        # 3. Download
        await self._downloader.download(pdf_url, dest_path)

        # 4. Validate
        status = self._validator.validate(dest_path)
        if status == ValidationStatus.EMPTY_FILE:
            dest_path.unlink(missing_ok=True)
            raise EmptyFile(f"Empty file: {pdf_url}")
        if status == ValidationStatus.INVALID_PDF:
            dest_path.unlink(missing_ok=True)
            raise InvalidPDF(f"Invalid PDF: {pdf_url}")

        # 5. Deduplication by SHA-256
        sha256 = calculate_sha256(dest_path)
        if storage.sha256_exists(sha256):
            dest_path.unlink(missing_ok=True)
            raise Duplicate(
                f"PDF already downloaded (sha256={sha256}): {source.id}/{edition.edition_name}"
            )

        file_size = dest_path.stat().st_size
        logger.info(
            f"source={source.id} edition={edition.edition_name} "
            f"status=VALIDATED size={file_size:,} sha256={sha256}"
        )
        return dest_path, sha256
