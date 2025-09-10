"""EU-specific factory implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.EU.database import EUSectionDatabase

logger: logging.Logger = logging.getLogger(__name__)


class EUSectionFactory(SectionFactory):
    """EU-specific steel section factory.
    
    This is now a thin wrapper around the simplified SectionFactory
    that provides EU-specific configuration.
    """

    def __init__(self, database: Optional[EUSectionDatabase] = None) -> None:
        """Initialize EU factory with EU database."""
        if database is None:
            database = EUSectionDatabase()
        super().__init__(database)


# Convenience function to create EU factory (replaces global singleton)
def get_EU_factory(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> EUSectionFactory:
    """Create an EU factory instance."""
    database = EUSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)
    return EUSectionFactory(database)


if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    from steelsnakes.base.sections import SectionType
    
    factory = get_EU_factory()
    
    try:
        test_4 = factory.create_section("200x100x10", SectionType.L_UNEQUAL)
        print(test_4.get_properties())
    except SectionNotFoundError as e:
        logger.error(f"{e}")