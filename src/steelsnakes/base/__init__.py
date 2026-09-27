"""Base classes and utilities for `steelsnakes`"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.connectors import BaseConnector, ConnectorType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.exceptions import SectionFactoryError, SectionNotFoundError, SectionTypeNotRegisteredError
from steelsnakes.base.sqlite3db import SQLiteJSONInterface, build_regional_sqlite_db
# from steelsnakes.base.stress import (
#     StressLoadCase,
#     StressPlotConfig,
#     compute_stress_grid,
#     plot_stress_dashboard_2d_plotly,
#     plot_stress_2d_matplotlib,
#     plot_stress_2d_plotly,
# )

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
    # "StressLoadCase",
    # "StressPlotConfig",
    # "compute_stress_grid",
    # "plot_stress_dashboard_2d_plotly",
    # "plot_stress_2d_matplotlib",
    # "plot_stress_2d_plotly",
]