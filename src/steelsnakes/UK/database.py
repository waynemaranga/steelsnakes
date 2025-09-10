"""UK-specific database implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from steelsnakes.base.database import SectionDatabase

class UKSectionDatabase(SectionDatabase):
    """UK-specific steel section database.
    
    This is now a thin wrapper around the simplified SectionDatabase
    that provides UK-specific configuration and convenience methods.
    """

    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False) -> None:
        """Initialize UK database with automatic region configuration."""
        super().__init__(data_directory=data_directory, region="UK", use_sqlite=use_sqlite)


# Convenience function to create UK database (replaces global singleton)
def get_UK_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> UKSectionDatabase:
    """Create a UK database instance."""
    return UKSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)


if __name__ == "__main__":
    db = get_UK_database()
    print([i.value for i in db.get_supported_types()])
    print(f"Available types: {[t.value for t in db.get_available_section_types()]}")