"""
DirectPDFHarvester.

For sources where the PDF URL is known (possibly with date tokens).
No browser interaction needed — pure HTTP streaming.

Strategy:
    1. For each edition, resolve URL from url_template (date substitution)
    2. Download via PDFDownloader
    3. Validate
    4. Dedup by SHA-256
"""

import logging
from datetime import date
from pathlib import Path
from typing import List, Tuple

from harvesting.core.base import BaseHarvester
from harvesting.core.models import EditionConfig, NewspaperSource
from harvesting.exceptions import EditionNotFound
from harvesting.utils import substitute_date_in_url

logger = logging.getLogger(__name__)


class DirectPDFHarvester(BaseHarvester):
    """
    Downloads newspaper PDFs from direct, predictable URLs.

    Configuration requires either:
    - `url_template` on the source (used for all editions)
    - `url_template` on each edition (per-edition override)
    """

    async def discover_editions(
        self,
        source: NewspaperSource,
        target_date: date,
    ) -> List[EditionConfig]:
        """
        Return configured editions.

        If no editions are configured, synthesise a single "default" edition
        using the source-level url_template.
        """
        if source.editions:
            return source.editions

        if source.url_template:
            return [
                EditionConfig(
                    edition_name="default",
                    url_template=source.url_template,
                    region=source.region,
                )
            ]

        raise EditionNotFound(
            f"No editions and no url_template configured for source: {source.id}"
        )

    async def discover_pdf(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        """
        Resolve the PDF URL from the edition's (or source's) url_template.
        """
        template = edition.url_template or source.url_template
        if not template:
            raise EditionNotFound(
                f"No url_template for edition '{edition.edition_name}' "
                f"in source '{source.id}'"
            )
        url = substitute_date_in_url(template, target_date)
        logger.info(
            f"source={source.id} edition={edition.edition_name} "
            f"resolved_url={url}"
        )
        return url

    async def download_edition(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
        storage: "HarvestStorage",  # type: ignore
    ) -> Tuple[Path, str]:
        """
        Download direct PDF, falling back to Playwright web capture if unavailable.
        """
        try:
            return await super().download_edition(source, edition, target_date, storage)
        except Exception as e:
            fallback_url = source.website_url or (
                "https://pib.gov.in/AllPressRelease.aspx" if source.id == "pib_india" else None
            )
            if fallback_url:
                logger.info(
                    f"Direct download failed for {source.id}: {e}. "
                    f"Falling back to Playwright web capture of {fallback_url}"
                )
                from harvesting.harvesters.playwright import PlaywrightHarvester
                source_copy = source.model_copy()
                source_copy.website_url = fallback_url
                pw = PlaywrightHarvester(self._storage_root)
                return await pw.download_edition(source_copy, edition, target_date, storage)
            raise
