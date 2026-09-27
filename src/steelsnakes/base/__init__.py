"""Base classes and utilities for `steelsnakes`"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.connectors import BaseConnector, ConnectorType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.exceptions import SectionClass4Error, SectionDatabaseError, SectionFactoryError, SectionNotFoundError, SectionTypeNotRegisteredError
from steelsnakes.base.sqlite3db import SQLiteJSONInterface, build_regional_sqlite_db
from steelsnakes.base.checks import Classification, DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
# NOTE: stress analysis (the old steelsnakes.base.stress, now in tests/dump) belongs in steelsnakes.engine

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
    "SectionDatabaseError",
    "SectionClass4Error",
    # Checks, shared by every design code
    "DesignCode",
    "LimitState",
    "SectionClass",
    "Classification",
    "Reference",
    "UtilisationCheck",
    "compute_utilisation",
]
