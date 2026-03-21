"""US-specific factory implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.US.database import USSectionDatabase

logger: logging.Logger = logging.getLogger(__name__)

class USSectionFactory(SectionFactory):
    """US-specific steel section factory.
    
    This is now a thin wrapper around the simplified SectionFactory
    that provides US-specific configuration.
    """

    def __init__(self, database: Optional[USSectionDatabase] = None) -> None:
        """Initialize US factory with US database."""
        if database is None:
            database = USSectionDatabase()
        super().__init__(database)


# Convenience function to create US factory (replaces global singleton)
def get_US_factory(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> USSectionFactory:
    """Create a US factory instance."""
    database = USSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)
    return USSectionFactory(database)


if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    from steelsnakes.base.sections import SectionType
    
    factory = get_US_factory()
    
    try:
        test = factory.create_section("W12X26", SectionType.W)
        print(test.get_properties())
    except SectionNotFoundError as e:
        logger.error(f"{e}")