from steelsnakes.EU.factory import EUSectionFactory, get_EU_factory
from steelsnakes.EU.database import get_EU_database, EUSectionDatabase
from steelsnakes.EU.sections import angles, beams, columns, piles, channels, flats

__all__: list[str] = [
    # Factories
    "EUSectionFactory",
    "get_EU_factory",   
    # Database
    "EUSectionDatabase",
    "get_EU_database",
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
