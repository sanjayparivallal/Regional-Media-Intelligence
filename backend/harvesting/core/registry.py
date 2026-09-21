"""
Harvester registry.

Maps source_type → harvester class.
Call HarvesterRegistry.get(source) to get the right strategy.
"""

import logging
from typing import TYPE_CHECKING

from harvesting.core.models import NewspaperSource, SourceType

if TYPE_CHECKING:
    from harvesting.core.base import BaseHarvester

logger = logging.getLogger(__name__)


class HarvesterRegistry:
    """Selects the correct harvester strategy based on source configuration."""

    @staticmethod
    def get(source: NewspaperSource) -> "BaseHarvester":
        """
        Return an initialised harvester for the given source.

        Strategy selection:
            direct_pdf    → DirectPDFHarvester
            playwright    → PlaywrightHarvester
            authenticated → AuthenticatedPlaywrightHarvester
            aggregator    → AggregatorHarvester
        """
        source_type = source.source_type

        if source_type == SourceType.DIRECT_PDF:
            from harvesting.harvesters.direct_pdf import DirectPDFHarvester
            return DirectPDFHarvester()

        if source_type == SourceType.PLAYWRIGHT:
            from harvesting.harvesters.playwright import PlaywrightHarvester
            return PlaywrightHarvester()

        if source_type == SourceType.AUTHENTICATED:
            from harvesting.harvesters.authenticated import AuthenticatedPlaywrightHarvester
            return AuthenticatedPlaywrightHarvester()

        if source_type == SourceType.AGGREGATOR:
            from harvesting.harvesters.aggregator import AggregatorHarvester
            return AggregatorHarvester()

        raise ValueError(f"Unknown source_type: {source_type}")
