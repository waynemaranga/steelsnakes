"""
US Steel Sections Module.
"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.database import USSectionDatabase, get_US_database
from steelsnakes.US.factory import USSectionFactory, get_US_factory
from steelsnakes.US.checks import (
    ClassificationContext,
    Classification,
    ClassificationResult,
    CompressionCase,
    ElementClassification,
    ElementInput,
    FlexureCase,
    StressPattern,
    classify_compression,
    classify_element,
    classify_elements,
    classify_flexure,
    classify_section,
    classify_section_from_dict,
)
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
    "ElementInput",
    "ElementClassification",
    "ClassificationResult",
    "ClassificationContext",
    "StressPattern",
    "Classification",
    "CompressionCase",
    "FlexureCase",
    "classify_element",
    "classify_elements",
    "classify_section",
    "classify_section_from_dict",
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
