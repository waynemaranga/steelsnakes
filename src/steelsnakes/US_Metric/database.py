"""US_Metric-specific database implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from steelsnakes.base.database import SectionDatabase


class USMetricSectionDatabase(SectionDatabase):
    """US Metric-specific steel section database.
    
    This is now a thin wrapper around the simplified SectionDatabase
    that provides US Metric-specific configuration and convenience methods.
    Handles US sections in metric units from AISC standards.
    """

    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False) -> None:
        """Initialize US Metric database with automatic region configuration."""
        super().__init__(data_directory=data_directory, region="US_METRIC", use_sqlite=use_sqlite)


# Convenience function to create US Metric database (replaces global singleton)
def get_US_Metric_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> USMetricSectionDatabase:
    """Create a US Metric database instance."""
    return USMetricSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)


if __name__ == "__main__":
    db = get_US_Metric_database()
    print([i.value for i in db.get_supported_types()])
    print(f"Available types: {[t.value for t in db.get_available_section_types()]}")