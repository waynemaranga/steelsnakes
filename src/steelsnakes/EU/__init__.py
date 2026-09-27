from steelsnakes.EU.factory import EUSectionFactory, get_EU_factory
from steelsnakes.EU.database import get_EU_database, EUSectionDatabase
from steelsnakes.EU.checks import (
    ClassificationResult,
    ElementClassification,
    ElementInput,
    ElementStressDistribution,
    StressPattern,
    outstand_buckling_factor,
    classify_circular_hollow,
    classify_element,
    classify_elements,
    classify_internal_part,
    classify_outstand_flange,
    classify_section,
    classify_section_from_dict,
    MomentDiagram,
    steel_material,
    check_tension,
    check_compression,
    check_bending,
    check_shear,
    check_cross_section,
    check_buckling_resistance,
    check_lateral_torsional_buckling,
    check_restrained_beam,
    check_bending_and_axial_compression,
    check_general_method,
    sls_combination,
    check_serviceability_stresses,
    check_vertical_deflection,
    check_beam_deflection,
    check_horizontal_deflection,
    check_vibration,
)
from steelsnakes.EU.sections import angles, beams, columns, piles, channels, flats
from steelsnakes.EU.sections.angles import L_EQUAL, L_EQUAL_B2B, L_UNEQUAL, L_UNEQUAL_B2B
from steelsnakes.EU.sections.beams import HE, HL, HLZ, IPE, UB
from steelsnakes.EU.sections.channels import PFC, UPE, UPN
from steelsnakes.EU.sections.columns import HD, UC
from steelsnakes.EU.sections.flats import S_section, Z_section
from steelsnakes.EU.sections.piles import HP, UBP

__all__: list[str] = [
    # Factories
    "EUSectionFactory",
    "get_EU_factory",   
    # Database
    "EUSectionDatabase",
    "get_EU_database",
    # Checks
    "ElementInput",
    "ElementStressDistribution",
    "StressPattern",
    "outstand_buckling_factor",
    "ElementClassification",
    "ClassificationResult",
    "classify_element",
    "classify_circular_hollow",
    "classify_internal_part",
    "classify_outstand_flange",
    "classify_elements",
    "classify_section",
    "classify_section_from_dict",
    # ULS checks (EN 1993-1-1 Section 6)
    "MomentDiagram",
    "steel_material",
    "check_tension",
    "check_compression",
    "check_bending",
    "check_shear",
    "check_cross_section",
    "check_buckling_resistance",
    "check_lateral_torsional_buckling",
    "check_restrained_beam",
    "check_bending_and_axial_compression",
    "check_general_method",
    # SLS checks (EN 1993-1-1 Section 7)
    "sls_combination",
    "check_serviceability_stresses",
    "check_vertical_deflection",
    "check_beam_deflection",
    "check_horizontal_deflection",
    "check_vibration",
    # Convenience constructors
    "IPE",
    "HE",
    "HL",
    "HLZ",
    "UB",
    "HD",
    "UC",
    "HP",
    "UBP",
    "PFC",
    "UPE",
    "UPN",
    "L_EQUAL",
    "L_UNEQUAL",
    "L_EQUAL_B2B",
    "L_UNEQUAL_B2B",
    "S_section",
    "Z_section",
    # Section types
    "angles",
    "beams",
    "columns",
    "piles",
    "channels",
    "flats",
 
]
# HD, HE, HL-HLZ, HP, IPE, L_EQUAL, L_UNEQUAL, L_EQUAL_B2B, L_UNEQUAL_B2B, PFC, S, UB, UBP, UC, UPE, UPN, Z
# Thanks to Arcelor Mittal: https://orangebook.arcelormittal.com/taxonomy/term/1

# --- Beams ---
# IPE - Parallel Flange I-sections
# HE - Wide Flange Beams
# HL, HLZ - Extra Wide Flange Beams
# UB - Universal Beams

# --- Columns ---
# HD - Wide Flange Columns
# UB - Universal Columns

# --- Bearing Piles ---
# HP - Wide Flange Bearing Piles
# UBP - Universal Bearing Piles

# --- Channels ---
# UPE - Parallel Flange Channels (EU)
# UPN - Tapered Flange Channels
# PFC - Parallel Flange Channels (UK)

# --- Angles ---
# L_EQUAL - Equal Angles
# L_UNEQUAL - Unequal Angles
# L_EQUAL_B2B - Back to Back Equal Angles
# L_UNEQUAL_B2B - Back to Back Unequal Angles

# --- Flats ---
# S - SIGMA
# Z - Zed-butted Sections
