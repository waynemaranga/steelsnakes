"""
Preloaded bolt specifications implementation.

This module implements Grade 8.8 and Grade 10.9 preloaded bolt specifications
using the generic base system. These provide design resistances for various
loading conditions and steel grades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class PreloadedBolt88(BaseSection):
    """
    Grade 8.8 Preloaded Bolt specification.
    
    High-strength friction grip bolt with Grade 8.8 material properties.
    Provides design resistances for various loading conditions.
    """
    
    # Basic properties
    d: float = 0.0  # Nominal bolt diameter (mm)
    A: float = 0.0  # Gross cross-sectional area (mm²)
    
    # Design resistances for different limit states
    SLS: Dict = field(default_factory=dict)  # SLS design resistances for different loading configurations
    
    # Ultimate limit state resistances
    ULS: Dict = field(default_factory=dict)  # ULS design resistances for different loading configurations
    
    # Tension resistances for different steel grades
    TENSION: Dict = field(default_factory=dict)  # Tension resistances for different steel grades
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.BOLT_PRE_88


@dataclass
class PreloadedBolt109(BaseSection):
    """
    Grade 10.9 Preloaded Bolt specification.
    
    High-strength friction grip bolt with Grade 10.9 material properties.
    Provides design resistances for various loading conditions.
    """
    
    # Basic properties
    d: float = 0.0  # Nominal bolt diameter (mm)
    A: float = 0.0  # Gross cross-sectional area (mm²)
    
    # Design resistances for different limit states
    SLS: Dict = field(default_factory=dict)  # SLS design resistances for different loading configurations
    
    # Ultimate limit state resistances
    ULS: Dict = field(default_factory=dict)  # ULS design resistances for different loading configurations
    
    # Tension resistances for different steel grades
    TENSION: Dict = field(default_factory=dict)  # Tension resistances for different steel grades
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.BOLT_PRE_109


# Convenience functions for direct instantiation
def BOLT_PRE_88(designation: str, data_directory: Optional[Path] = None) -> PreloadedBolt88:
    """Create a Grade 8.8 Preloaded Bolt specification by designation."""
    factory = get_factory(data_directory)
    if SectionType.BOLT_PRE_88 not in factory._section_classes:
        factory.register_section_class(PreloadedBolt88)
    return factory.create_section(designation, SectionType.BOLT_PRE_88)


def BOLT_PRE_109(designation: str, data_directory: Optional[Path] = None) -> PreloadedBolt109:
    """Create a Grade 10.9 Preloaded Bolt specification by designation."""
    factory = get_factory(data_directory)
    if SectionType.BOLT_PRE_109 not in factory._section_classes:
        factory.register_section_class(PreloadedBolt109)
    return factory.create_section(designation, SectionType.BOLT_PRE_109)


# Auto-register classes when module is imported
def _register_bolt_sections():
    """Register all bolt section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(PreloadedBolt88)
    factory.register_section_class(PreloadedBolt109)


# Auto-register when imported
_register_bolt_sections()