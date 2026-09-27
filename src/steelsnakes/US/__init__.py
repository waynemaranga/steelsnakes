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
    TensionResult,
    CompressionResult,
    FlexureResult,
    ShearResult,
    TorsionResult,
    BendingAxis,
    tension_utilisation,
    compression_utilisation,
    flexure_utilisation,
    shear_utilisation,
    check_axial_flexure_interaction,
    check_hss_combined_torsion,
    hss_torsion,
    amplified_required_strengths,
    calculate_B1,
    calculate_B2,
    notional_load,
    notional_loads,
    stiffness_reduction_tau_b,
)
from steelsnakes.US.checks.tension import tension
from steelsnakes.US.checks.compression import compression
from steelsnakes.US.checks.flexure import flexure
from steelsnakes.US.checks.shear import shear
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
    # Checks; AISC 360-22 Chapters D to H
    "tension",
    "compression",
    "flexure",
    "shear",
    "hss_torsion",
    "TensionResult",
    "CompressionResult",
    "FlexureResult",
    "ShearResult",
    "TorsionResult",
    "BendingAxis",
    "tension_utilisation",
    "compression_utilisation",
    "flexure_utilisation",
    "shear_utilisation",
    "check_axial_flexure_interaction",
    "check_hss_combined_torsion",
    # Stability; AISC 360-22 Chapter C and Appendix 8
    "notional_load",
    "notional_loads",
    "stiffness_reduction_tau_b",
    "calculate_B1",
    "calculate_B2",
    "amplified_required_strengths",
    # Section types
    "angles",
    "beams",
    "channels",
    "hollow",       
    "piles",
    "pipes",
    "tees"
]
