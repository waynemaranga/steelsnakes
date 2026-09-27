"""Analysis engine for `steelsnakes`: for now, section analysis of the tabulated sections and of built-up sections.

Applying forces to sections (stress analysis) and analysing members (`steelsnakes.engine.analysis`) come later; with the
regional checks, they close the loop of actions against resistances.
"""

from steelsnakes.engine.units import LENGTH_UNITS, SECTION_TABLE_UNITS, UNITS, Unit, get_unit
from steelsnakes.engine.sections import SectionAnalysis, analyse_section, section_geometry

__all__: list[str] = [
    # Units
    "Unit",
    "UNITS",
    "LENGTH_UNITS",
    "SECTION_TABLE_UNITS",
    "get_unit",
    # Section analysis
    "SectionAnalysis",
    "analyse_section",
    "section_geometry",
]
