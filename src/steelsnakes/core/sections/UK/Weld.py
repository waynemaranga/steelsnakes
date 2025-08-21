"""
Weld specifications implementation.

This module implements weld specifications using the generic base system.
Provides weld properties and design resistances for different steel grades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class WeldSpecification(BaseSection):
    """
    Weld specification with design resistances.
    
    Provides weld throat thickness, area properties, and design resistances
    for different steel grades (S355, S420, S460).
    """
    
    # Basic weld properties
    s: float = 0.0  # Weld size - throat thickness (mm)
    a: float = 0.0  # Weld throat area per unit length (mm²/mm)
    
    # Design resistances for different steel grades
    S355: Optional[Dict[str, float]] = field(default_factory=dict)  # Resistances for S355 steel grade
    S420: Optional[Dict[str, float]] = field(default_factory=dict)  # Resistances for S420 steel grade
    S460: Optional[Dict[str, float]] = field(default_factory=dict)  # Resistances for S460 steel grade
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WELDS


# Convenience function for direct instantiation
def WELD(designation: str, data_directory: Optional[Path] = None) -> WeldSpecification:
    """Create a Weld specification by designation (weld size)."""
    factory = get_factory(data_directory)
    if SectionType.WELDS not in factory._section_classes:
        factory.register_section_class(WeldSpecification)
    return factory.create_section(designation, SectionType.WELDS)


# Auto-register class when module is imported
def _register_weld_sections():
    """Register weld section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(WeldSpecification)


# Auto-register when imported
_register_weld_sections()