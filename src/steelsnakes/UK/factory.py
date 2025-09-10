"""UK-specific factory implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.database import SectionDatabase
from steelsnakes.UK.database import UKSectionDatabase

logger: logging.Logger = logging.getLogger(__name__)


class UKSectionFactory(SectionFactory):
    """UK-specific steel section factory.
    
    This is now a thin wrapper around the simplified SectionFactory
    that provides UK-specific configuration.
    """

    def __init__(self, database: Optional[UKSectionDatabase] = None) -> None:
        """Initialize UK factory with UK database."""
        if database is None:
            database = UKSectionDatabase()
        super().__init__(database)


# Convenience function to create UK factory (replaces global singleton)
def get_UK_factory(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> UKSectionFactory:
    """Create a UK factory instance."""
    database = UKSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)
    return UKSectionFactory(database)


if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    from steelsnakes.base.sections import SectionType
    
    factory = get_UK_factory()
    
    # Test fuzzy matching with a close-but-incorrect designation
    try:
        test_1 = factory.create_section("30x30x3.0", SectionType.L_EQUAL)
        print(test_1.get_properties())
    except SectionNotFoundError as e:
        logger.error(f"{e}")
   
    print("---------------------------")

    try:
        test_2 = factory.create_section("254x146x30", SectionType.UB)
        print(test_2.get_properties())
    except SectionNotFoundError as e:
        logger.error(f"{e}")