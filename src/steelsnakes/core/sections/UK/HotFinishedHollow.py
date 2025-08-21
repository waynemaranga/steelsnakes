"""
Hot Finished Hollow Section steel sections implementation.

This module implements Circular, Square, Rectangular, and Elliptical Hot Finished Hollow Sections
using the generic base system. These are hollow sections formed by hot working,
commonly used for structural applications requiring higher strength and precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class HotFinishedCircularHollowSection(BaseSection):
    """
    Hot Finished Circular Hollow Section (HFCHS).
    
    Circular hollow section formed by hot working, providing superior
    mechanical properties and dimensional accuracy.
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
    
    # Second moments of area and section properties
    I: float = 0.0  # Second moment of area (cm⁴)
    i: float = 0.0  # Radius of gyration (cm)
    W_el: float = 0.0  # Elastic section modulus (cm³)
    W_pl: float = 0.0  # Plastic section modulus (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    W_t: float = 0.0  # Torsional section modulus (cm³)
    
    # Surface areas for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HFCHS


@dataclass
class HotFinishedSquareHollowSection(BaseSection):
    """
    Hot Finished Square Hollow Section (HFSHS).
    
    Square hollow section formed by hot working, providing superior
    mechanical properties and dimensional accuracy.
    """
    
    # Identification
    hxh: str  # Side dimensions (e.g., '100x100')
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Geometric ratios
    c_t: float = 0.0  # Side to thickness ratio
    
    # Second moments of area and section properties
    I: float = 0.0  # Second moment of area (cm⁴)
    i: float = 0.0  # Radius of gyration (cm)
    W_el: float = 0.0  # Elastic section modulus (cm³)
    W_pl: float = 0.0  # Plastic section modulus (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    W_t: float = 0.0  # Torsional section modulus (cm³)
    
    # Surface areas for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HFSHS


@dataclass
class HotFinishedRectangularHollowSection(BaseSection):
    """
    Hot Finished Rectangular Hollow Section (HFRHS).
    
    Rectangular hollow section formed by hot working, providing superior
    mechanical properties and dimensional accuracy.
    """
    
    # Identification
    hxb: str  # Side dimensions (e.g., '150x100')
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Geometric ratios
    cw_t: float = 0.0  # Web slenderness ratio
    cf_t: float = 0.0  # Flange slenderness ratio
    
    # Second moments of area - biaxial
    I_yy: float = 0.0  # Second moment of area, major axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, minor axis (cm⁴)
    i_yy: float = 0.0  # Radius of gyration, major axis (cm)
    i_zz: float = 0.0  # Radius of gyration, minor axis (cm)
    
    # Section moduli - biaxial
    W_el_yy: float = 0.0  # Elastic section modulus, major axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, minor axis (cm³)
    W_pl_yy: float = 0.0  # Plastic section modulus, major axis (cm³)
    W_pl_zz: float = 0.0  # Plastic section modulus, minor axis (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    W_t: float = 0.0  # Torsional section modulus (cm³)
    
    # Surface areas for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HFRHS


@dataclass
class HotFinishedEllipticalHollowSection(BaseSection):
    """
    Hot Finished Elliptical Hollow Section (HFEHS).
    
    Elliptical hollow section formed by hot working, providing unique
    aesthetic and structural properties for specialized applications.
    """
    
    # Identification
    hxb: str  # Major x minor axis dimensions (e.g., '300x150')
    t: float = 0.0  # Wall thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Second moments of area - biaxial
    I_yy: float = 0.0  # Second moment of area, major axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, minor axis (cm⁴)
    i_yy: float = 0.0  # Radius of gyration, major axis (cm)
    i_zz: float = 0.0  # Radius of gyration, minor axis (cm)
    
    # Section moduli - biaxial
    W_el_yy: float = 0.0  # Elastic section modulus, major axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, minor axis (cm³)
    W_pl_yy: float = 0.0  # Plastic section modulus, major axis (cm³)
    W_pl_zz: float = 0.0  # Plastic section modulus, minor axis (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    W_t: float = 0.0  # Torsional section modulus (cm³)
    
    # Surface areas for coating/painting
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HFEHS


# Convenience functions for direct instantiation
def HFCHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedCircularHollowSection:
    """Create a Hot Finished Circular Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.HFCHS not in factory._section_classes:
        factory.register_section_class(HotFinishedCircularHollowSection)
    return factory.create_section(designation, SectionType.HFCHS)


def HFSHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedSquareHollowSection:
    """Create a Hot Finished Square Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.HFSHS not in factory._section_classes:
        factory.register_section_class(HotFinishedSquareHollowSection)
    return factory.create_section(designation, SectionType.HFSHS)


def HFRHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedRectangularHollowSection:
    """Create a Hot Finished Rectangular Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.HFRHS not in factory._section_classes:
        factory.register_section_class(HotFinishedRectangularHollowSection)
    return factory.create_section(designation, SectionType.HFRHS)


def HFEHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedEllipticalHollowSection:
    """Create a Hot Finished Elliptical Hollow Section by designation."""
    factory = get_factory(data_directory)
    if SectionType.HFEHS not in factory._section_classes:
        factory.register_section_class(HotFinishedEllipticalHollowSection)
    return factory.create_section(designation, SectionType.HFEHS)


# Auto-register classes when module is imported
def _register_hot_finished_sections():
    """Register all hot finished section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(HotFinishedCircularHollowSection)
    factory.register_section_class(HotFinishedSquareHollowSection)
    factory.register_section_class(HotFinishedRectangularHollowSection)
    factory.register_section_class(HotFinishedEllipticalHollowSection)


# Auto-register when imported
_register_hot_finished_sections()