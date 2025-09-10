"""EU-specific database implementation using simplified architecture."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from steelsnakes.base.database import SectionDatabase


class EUSectionDatabase(SectionDatabase):
    """EU-specific steel section database.
    
    Thin wrapper around the simplified SectionDatabase
    that provides EU-specific configuration and convenience methods.
    Handles EU sections from EN 10365:2017 standard.
    """

    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False) -> None:
        """Initialize EU database with automatic region configuration."""
        super().__init__(data_directory=data_directory, region="EU", use_sqlite=use_sqlite)


# Convenience function to create EU database (replaces global singleton)
def get_EU_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> EUSectionDatabase:
    """Create an EU database instance."""
    return EUSectionDatabase(data_directory=data_directory, use_sqlite=use_sqlite)


if __name__ == "__main__":
    db = get_EU_database()
    print([i.value for i in db.get_supported_types()])
    print(f"Available types: {[t.value for t in db.get_available_section_types()]}")