"""US-specific database implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from steelsnakes.base.database import SectionDatabase


class USSectionDatabase(SectionDatabase):
    """US-specific steel section database.
    
    Thin wrapper around the simplified SectionDatabase
    that provides US-specific configuration and convenience methods.
    Handles US sections from AISC standards.
    """

    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False) -> None:
        """Initialize US database with automatic region configuration."""
        super().__init__(data_directory=data_directory, region="US", use_sqlite=use_sqlite)


# Convenience function to create US database (replaces global singleton)
def get_US_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> USSectionDatabase:
    """Create a US database instance."""
    return USSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)


if __name__ == "__main__":
    db = get_US_database()
    print([i.value for i in db.get_supported_types()])
    print(f"Available types: {[t.value for t in db.get_available_section_types()]}")