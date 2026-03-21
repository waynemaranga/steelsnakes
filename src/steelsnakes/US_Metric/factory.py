"""US_Metric-specific factory implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.US_Metric.database import USMetricSectionDatabase

logger: logging.Logger = logging.getLogger(__name__)


class USMetricSectionFactory(SectionFactory):
    """US Metric-specific steel section factory.
    
    This is now a thin wrapper around the simplified SectionFactory
    that provides US Metric-specific configuration.
    """

    def __init__(self, database: Optional[USMetricSectionDatabase] = None) -> None:
        """Initialize US Metric factory with US Metric database."""
        if database is None:
            database = USMetricSectionDatabase()
        super().__init__(database)


# Convenience function to create US Metric factory (replaces global singleton)
def get_US_Metric_factory(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> USMetricSectionFactory:
    """Create a US Metric factory instance."""
    database = USMetricSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)
    return USMetricSectionFactory(database)


if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    from steelsnakes.base.sections import SectionType
    
    factory = get_US_Metric_factory()
    
    try:
        test = factory.create_section("W310X39", SectionType.W) # FIXME: implement US Metric sections
        print(test.get_properties())
    except SectionNotFoundError as e:
        logger.error(f"{e}")