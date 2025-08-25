"""Base classes and utilities for `steelsnakes`"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase, SQLiteJSONInterface, build_regional_sqlite_db
from steelsnakes.base.factory import SectionFactory

__all__: list[str] = [
    "BaseSection",
    "SectionType",
    "SectionDatabase",
    "SQLiteJSONInterface",
    "build_regional_sqlite_db",
    "SectionFactory",
]