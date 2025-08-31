"""
Universal steel sections (UB, UC, UBP) for UK module.

This module implements Universal Beams, Universal Columns, and Universal Bearing Piles
using the new base system architecture.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory

@dataclass
class UniversalSection(BaseSection):
    """Base class for all universal steel sections (UB, UC, UBP)."""
    
    # Identification  
    serial_size: str = ""
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0
    h: float = 0.0  # Overall depth (mm)
    b: float = 0.0  # Overall width (mm)
    tw: float = 0.0  # Web thickness (mm) 
    tf: float = 0.0  # Flange thickness (mm)
    r: float = 0.0  # Root radius (mm)
    d: float = 0.0  # Depth between fillets (mm)
    
    # Ratios
    cw_tw: float = 0.0  # Web slenderness ratio
    cf_tf: float = 0.0  # Flange slenderness ratio
    
    # Clearances
    C: float = 0.0  # End clearance (mm)
    N: float = 0.0  # Notch clearance (mm)
    n: float = 0.0  # Alternative notch clearance (mm)
    
    # Surface areas
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
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
    
    # Buckling and torsion properties
    U: float = 0.0  # Buckling parameter
    X: float = 0.0  # Torsional index
    I_w: float = 0.0  # Warping constant (cm⁶)
    I_t: float = 0.0  # Torsional constant (cm⁴)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""

        # return self.__dict__ # DANGEROUS: live reference; caller can modify internal state
        # return vars(self).copy() # SAFE: returns a shallow copy, doesn't expose live references to the instance
        from dataclasses import asdict
        return asdict(self) # SAFE: applies recursively to field values that are dataclass instances.

        

@dataclass
class UniversalBeam(UniversalSection):
    """Universal Beam (UB) section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UB


@dataclass  
class UniversalColumn(UniversalSection):
    """Universal Column (UC) section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UC


@dataclass
class UniversalBearingPile(UniversalSection):
    """Universal Bearing Pile (UBP) section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UBP


# Convenience functions for direct instantiation
def UB(designation: str, data_directory: Optional[Path] = None) -> UniversalBeam:
    """
    Create a Universal Beam section by designation.
    
    Args:
        designation: Section designation (e.g., "457x191x67")
        data_directory: Optional path to data directory
    Returns:
        UniversalBeam instance with actual values from database
    """
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.UB)
    return cast(UniversalBeam, factory.create_section(designation, SectionType.UB))


def UC(designation: str, data_directory: Optional[Path] = None) -> UniversalColumn:
    """
    Create a Universal Column section by designation.
    
    Args:
        designation: Section designation (e.g., "305x305x137")
        data_directory: Optional path to data directory
    Returns:
        UniversalColumn instance with actual values from database
    """
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.UC)
    return cast(UniversalColumn, factory.create_section(designation, SectionType.UC))


def UBP(designation: str, data_directory: Optional[Path] = None) -> UniversalBearingPile:
    """
    Create a Universal Bearing Pile section by designation.
    
    Args:
        designation: Section designation (e.g., "203x203x45")
        data_directory: Optional path to data directory
    Returns:
        UniversalBearingPile instance with actual values from database
    """
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.UBP)
    return cast(UniversalBearingPile, factory.create_section(designation, SectionType.UBP))

if __name__ == "__main__":
    # print(UB("457x191x67"))
    # print(UC("305x305x137"))
    print(UBP("203x203x45").get_properties())