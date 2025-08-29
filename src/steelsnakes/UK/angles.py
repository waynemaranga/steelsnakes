"""
Angle steel sections for UK module.
This module implements Equal Angles, Unequal Angles, and their Back-to-Back variants.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


@dataclass
class EqualAngle(BaseSection):
    """
    Equal Angle (L_EQUAL) section.
    
    L-shaped section with equal leg lengths, commonly used for 
    bracing, connections, and structural framing applications.
    """
    
    # Identification
    hxh: str = ""
    t: float = 0.0  # Thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry - radii
    r_1: float = 0.0  # Root radius (mm)
    r_2: float = 0.0  # Toe radius (mm)
    
    # Centroidal distances
    c: float = 0.0  # Distance from back of angle to centroidal axis (mm)
    
    # Second moments of area - principal and geometric axes
    I_yy: float = 0.0  # Second moment of area, y-axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm⁴)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm⁴)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm³)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm⁴)
    phi_a: float = 0.0  # Torsional parameter
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return {
            'designation': self.designation,
            'hxh': self.hxh,
            't': self.t,
            'mass_per_metre': self.mass_per_metre,
            'A': self.A,
            'I_yy': self.I_yy,
            'I_zz': self.I_zz,
            'I_uu': self.I_uu,
            'I_vv': self.I_vv,
        }


@dataclass
class UnequalAngle(BaseSection):
    """
    Unequal Angle (L_UNEQUAL) section.
    
    L-shaped section with different leg lengths, commonly used for 
    specialized structural applications where asymmetry is beneficial.
    """
    
    # Identification
    hxb: str = ""  # Leg dimensions (e.g., '200x100')
    t: float = 0.0  # Thickness (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry - radii
    r_1: float = 0.0  # Root radius (mm)
    r_2: float = 0.0  # Toe radius (mm)
    
    # Centroidal distances
    c_y: float = 0.0  # Distance from back of longer leg to y-axis (mm)
    c_z: float = 0.0  # Distance from back of shorter leg to z-axis (mm)
    
    # Second moments of area - principal and geometric axes
    I_yy: float = 0.0  # Second moment of area, y-axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm⁴)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm⁴)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm³)
    W_el_uu: float = 0.0  # Elastic section modulus, major principal axis (cm³)
    W_el_vv: float = 0.0  # Elastic section modulus, minor principal axis (cm³)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Principal axis properties
    tan_alpha: float = 0.0  # Tangent of principal axis angle
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return {
            'designation': self.designation,
            'hxb': self.hxb,
            't': self.t,
            'mass_per_metre': self.mass_per_metre,
            'A': self.A,
            'I_yy': self.I_yy,
            'I_zz': self.I_zz,
            'I_uu': self.I_uu,
            'I_vv': self.I_vv,
        }


@dataclass
class EqualAngleBackToBack(BaseSection):
    """
    Back-to-Back Equal Angles (L_EQUAL_B2B) section.
    
    Two equal angles arranged back-to-back, commonly used for 
    compression members and built-up sections.
    """
    
    # Identification
    hxh: str = ""  # Leg dimensions (e.g., '200x200')
    t: float = 0.0  # Thickness (mm)
    s: float = 0.0  # Spacing between backs (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry - radii (per angle)
    r_1: float = 0.0  # Root radius (mm)
    r_2: float = 0.0  # Toe radius (mm)
    
    # Second moments of area
    I_yy: float = 0.0  # Second moment of area, y-axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm⁴)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm⁴)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm³)
    W_el_uu: float = 0.0  # Elastic section modulus, major principal axis (cm³)
    W_el_vv: float = 0.0  # Elastic section modulus, minor principal axis (cm³)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL_B2B
    
    def get_properties(self) -> dict[str,Any]:
        """Return all section properties as a dictionary."""
        return {
            'designation': self.designation,
            'hxh': self.hxh,
            't': self.t,
            's': self.s,
            'mass_per_metre': self.mass_per_metre,
            'A': self.A,
            'I_yy': self.I_yy,
            'I_zz': self.I_zz,
        }


@dataclass
class UnequalAngleBackToBack(BaseSection):
    """
    Back-to-Back Unequal Angles (L_UNEQUAL_B2B) section.
    
    Two unequal angles arranged back-to-back, commonly used for 
    specialized structural applications requiring built-up sections.
    """
    
    # Identification
    hxb: str = ""  # Leg dimensions (e.g., '200x100')
    t: float = 0.0  # Thickness (mm)
    s: float = 0.0  # Spacing between backs (mm)
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    
    # Geometry - radii (per angle)
    r_1: float = 0.0  # Root radius (mm)
    r_2: float = 0.0  # Toe radius (mm)
    
    # Second moments of area
    I_yy: float = 0.0  # Second moment of area, y-axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm⁴)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm⁴)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm³)
    W_el_uu: float = 0.0  # Elastic section modulus, major principal axis (cm³)
    W_el_vv: float = 0.0  # Elastic section modulus, minor principal axis (cm³)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Principal axis properties
    tan_alpha: float = 0.0  # Tangent of principal axis angle
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL_B2B
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return {
            'designation': self.designation,
            'hxb': self.hxb,
            't': self.t,
            's': self.s,
            'mass_per_metre': self.mass_per_metre,
            'A': self.A,
            'I_yy': self.I_yy,
            'I_zz': self.I_zz,
        }


# Convenience functions for direct instantiation
def L_EQUAL(designation: str, data_directory: Optional[Path] = None) -> EqualAngle:
    """Create an Equal Angle section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.L_EQUAL)
    return cast(EqualAngle, factory.create_section(designation, SectionType.L_EQUAL))


def L_UNEQUAL(designation: str, data_directory: Optional[Path] = None) -> UnequalAngle:
    """Create an Unequal Angle section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.L_UNEQUAL)
    return cast(UnequalAngle, factory.create_section(designation, SectionType.L_UNEQUAL))


def L_EQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> EqualAngleBackToBack:
    """Create a Back-to-Back Equal Angles section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.L_EQUAL_B2B)
    return cast(EqualAngleBackToBack, factory.create_section(designation, SectionType.L_EQUAL_B2B))


def L_UNEQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> UnequalAngleBackToBack:
    """Create a Back-to-Back Unequal Angles section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.L_UNEQUAL_B2B)
    return cast(UnequalAngleBackToBack, factory.create_section(designation, SectionType.L_UNEQUAL_B2B))
