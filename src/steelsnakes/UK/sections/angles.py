"""
Angle steel sections for UK module.

This module implements Equal Angles, Unequal Angles, and their Back-to-Back variants.
TODO: Fix UK/EU angle classes and properties; do dataprep again for UK sections on angles
to clean up properties OR remarshall json for fixing
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


def _parse_leg_pair(*candidates: str) -> tuple[float, float] | None:
    """Extract the first two leg dimensions from property hints or designation text."""
    for value in candidates:
        if not value:
            continue
        numbers = re.findall(r"\d+(?:\.\d+)?", value)
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
    return None


def _angle_elements(leg_hint: str, designation: str, t: float) -> list[Any]:
    """Build EC3 classification elements from UK angle naming conventions."""
    from steelsnakes.EU.checks.classification import angle_section_elements

    if t <= 0.0:
        return []

    pair = _parse_leg_pair(leg_hint, designation)
    if pair is None:
        return []

    leg_1, leg_2 = pair
    return angle_section_elements(leg_1_mm=leg_1, leg_2_mm=leg_2, t_mm=t)


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
    I_yy: float = 0.0  # Second moment of area, y-axis (cm^4)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm^4)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm^4)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm^4)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm^3)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm^3)
    
    # Torsional properties
    I_t: float = 0.0  # Torsional constant (cm^4)
    phi_a: float = 0.0  # Torsional parameter
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm^2)

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxh, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return vars(self).copy()


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
    I_yy: float = 0.0  # Second moment of area, y-axis (cm^4)
    I_zz: float = 0.0  # Second moment of area, z-axis (cm^4)
    I_uu: float = 0.0  # Second moment of area, major principal axis (cm^4)
    I_vv: float = 0.0  # Second moment of area, minor principal axis (cm^4)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, y-axis (cm)
    i_zz: float = 0.0  # Radius of gyration, z-axis (cm)
    i_uu: float = 0.0  # Radius of gyration, major principal axis (cm)
    i_vv: float = 0.0  # Radius of gyration, minor principal axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, y-axis (cm^3)
    W_el_zz: float = 0.0  # Elastic section modulus, z-axis (cm^3)
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm^2)
    
    # Principal axis properties
    tan_alpha: float = 0.0  # Tangent of principal axis angle
    I_t: float = 0.0
    phi_a_min: float = 0.0
    phi_a_max: float = 0.0
    psi_a: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxb, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return vars(self).copy()


@dataclass
class EqualAngleBackToBack(BaseSection):
    """
    Back-to-Back Equal Angles (L_EQUAL_B2B) section.
    
    Two equal angles arranged back-to-back, commonly used for
    compression members and built-up sections.
    """

    # Identification
    hxh: str = ""  # TODO: resolve dataprep for h value and t value (or) employ in calc engine
    is_additional: bool = False
    t: float = 0.0
    total_mass_per_metre: float = 0.0
    n_y: float = 0.0
    total_area: float = 0.0
    I_yy: float = 0.0
    i_yy: float = 0.0
    W_el_yy: float = 0.0
    i_zz: Any = ()  # FIXME: dict/list/set/OrderedDict mutable defaults not allowed

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL_B2B

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxh, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return vars(self).copy()


@dataclass
class UnequalAngleBackToBack(BaseSection):
    """
    Back-to-Back Unequal Angles (L_UNEQUAL_B2B) section.
    
    Two unequal angles arranged back-to-back, commonly used for
    specialized structural applications requiring built-up sections.
    """

    # Identification
    hxb: str = ""
    is_additional: bool = False
    t: float = 0.0
    total_mass_per_metre: float = 0.0
    n_y: float = 0.0
    total_area: float = 0.0
    I_yy: float = 0.0
    i_yy: float = 0.0
    W_el_yy: float = 0.0
    i_zz: Any = ()  # FIXME: dict/list/set/OrderedDict mutable defaults not allowed

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL_B2B

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxb, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return vars(self).copy()


def L_EQUAL(designation: str, data_directory: Optional[Path] = None) -> EqualAngle:
    """Create an Equal Angle section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    return cast(EqualAngle, factory.create_section(designation, SectionType.L_EQUAL))


def L_UNEQUAL(designation: str, data_directory: Optional[Path] = None) -> UnequalAngle:
    """Create an Unequal Angle section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    return cast(UnequalAngle, factory.create_section(designation, SectionType.L_UNEQUAL))


def L_EQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> EqualAngleBackToBack:
    """Create a Back-to-Back Equal Angles section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    return cast(EqualAngleBackToBack, factory.create_section(designation, SectionType.L_EQUAL_B2B))


def L_UNEQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> UnequalAngleBackToBack:
    """Create a Back-to-Back Unequal Angles section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    return cast(UnequalAngleBackToBack, factory.create_section(designation, SectionType.L_UNEQUAL_B2B))
