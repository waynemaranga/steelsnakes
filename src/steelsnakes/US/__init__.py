"""
US Steel Sections Module.
"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.database import USSectionDatabase, get_US_database
from steelsnakes.US.factory import USSectionFactory, get_US_factory
from steelsnakes.US.checks import Classification, classify_compression, classify_flexure
from steelsnakes.US.sections import (
    angles,
    beams,
    channels,
    hollow,       
    piles,
    pipes,
    tees,
)

__all__: list[str] = [
    "BaseSection",
    "SectionType",
    "USSectionDatabase",
    "get_US_database",
    "USSectionFactory",
    "get_US_factory",
    "Classification",
    "classify_compression",
    "classify_flexure",
    # Section types
    "angles",
    "beams",
    "channels",
    "hollow",       
    "piles",
    "pipes",
    "tees"
]