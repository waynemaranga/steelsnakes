"""
Cold Formed Hollow Section steel sections implementation.

This module implements Circular, Square, and Rectangular Cold Formed Hollow Sections
using the generic base system. These are hollow sections formed by cold working,
commonly used for structural and architectural applications.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class ColdFormedCircularHollowSection(BaseSection):
    """
    Cold Formed Circular Hollow Section (CFCHS).
    
    Circular hollow section formed by cold working, commonly used for
    compression members, tension members, and architectural applications.
    """
    
    # Identification
    d: float = 0.0  # Outside diameter (mm)
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Geometric ratios
    d_t: float = 0.0  # Diameter to thickness ratio
    
    # Second moments of area
    I: float = 0.0  # Second moment of area (cm⁴)
    
    # Radii of gyration
    i: float = 0.0  # Radius of gyration (cm)
    
    # Section moduli
    W_el: float = 0.0  # Elastic section modulus (cm³)
    W_pl: float = 0.0  # Plastic section modulus (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    W_t: float = 0.0  # Torsional section modulus (cm³)
    
    # Surface area per metre for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFCHS


@dataclass
class ColdFormedSquareHollowSection(BaseSection):
    """
    Cold Formed Square Hollow Section (CFSHS).
    
    Square hollow section formed by cold working, commonly used for
    structural framing and architectural applications.
    """
    
    # Identification
    H: float = 0.0  # Outside dimension (mm)
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry
    r_ext: float = 0.0  # External corner radius (mm)
    r_int: float = 0.0  # Internal corner radius (mm)
    
    # Second moments of area
    I: float = 0.0  # Second moment of area (cm⁴)
    
    # Radii of gyration
    i: float = 0.0  # Radius of gyration (cm)
    
    # Section moduli
    W_el: float = 0.0  # Elastic section modulus (cm³)
    W_pl: float = 0.0  # Plastic section modulus (cm³)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Surface area per metre for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    # Geometric properties
    C: float = 0.0  # Torsional constant factor
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFSHS


@dataclass
class ColdFormedRectangularHollowSection(BaseSection):
    """
    Cold Formed Rectangular Hollow Section (CFRHS).
    
    Rectangular hollow section formed by cold working, commonly used for
    structural framing and architectural applications.
    """
    
    # Identification
    H: float = 0.0  # Height (mm)
    B: float = 0.0  # Width (mm)
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry
    r_ext: float = 0.0  # External corner radius (mm)
    r_int: float = 0.0  # Internal corner radius (mm)
    
    # Second moments of area
    I_yy: float = 0.0  # Second moment of area, major axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, minor axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, major axis (cm)
    i_zz: float = 0.0  # Radius of gyration, minor axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, major axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, minor axis (cm³)
    W_pl_yy: float = 0.0  # Plastic section modulus, major axis (cm³)
    W_pl_zz: float = 0.0  # Plastic section modulus, minor axis (cm³)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Surface area per metre for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    # Geometric properties
    C: float = 0.0  # Torsional constant factor
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFRHS


# Convenience functions for direct instantiation
def CFCHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedCircularHollowSection:
    """Create a Cold Formed Circular Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.CFCHS not in factory._section_classes:
        factory.register_section_class(ColdFormedCircularHollowSection)
    return factory.create_section(designation, SectionType.CFCHS)


def CFSHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedSquareHollowSection:
    """Create a Cold Formed Square Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.CFSHS not in factory._section_classes:
        factory.register_section_class(ColdFormedSquareHollowSection)
    return factory.create_section(designation, SectionType.CFSHS)


def CFRHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedRectangularHollowSection:
    """Create a Cold Formed Rectangular Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.CFRHS not in factory._section_classes:
        factory.register_section_class(ColdFormedRectangularHollowSection)
    return factory.create_section(designation, SectionType.CFRHS)


# Auto-register classes when module is imported
def _register_cold_formed_sections():
    """Register all cold formed section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(ColdFormedCircularHollowSection)
    factory.register_section_class(ColdFormedSquareHollowSection)
    factory.register_section_class(ColdFormedRectangularHollowSection)


# Auto-register when imported
_register_cold_formed_sections()