"""Base classes and utilities for `steelsnakes`"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.connectors import BaseConnector, ConnectorType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.exceptions import SectionFactoryError, SectionNotFoundError, SectionTypeNotRegisteredError
from steelsnakes.base.sqlite3db import SQLiteJSONInterface, build_regional_sqlite_db

__all__: list[str] = [
    "BaseSection",
    "SectionType",
    "BaseConnector",
    "ConnectorType",
    "SectionDatabase",
    "SQLiteJSONInterface",
    "build_regional_sqlite_db",
    "SectionFactory",
    "SectionFactoryError",
    "SectionNotFoundError",
    "SectionTypeNotRegisteredError",
]