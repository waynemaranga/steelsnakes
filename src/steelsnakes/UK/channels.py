"""
Channel steel sections for UK module.
This module implements Parallel Flange Channels (PFC).
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import get_uk_factory


@dataclass
class ParallelFlangeChannel(BaseSection):
    """
    Parallel Flange Channel (PFC) section.
    
    C-shaped section with parallel flanges, commonly used for 
    secondary beams, purlins, and cladding rails.
    """
    
    # Identification
    serial_size: str = ""
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0  # Mass per metre (kg/m)
    h: float = 0.0  # Overall depth (mm)
    b: float = 0.0  # Overall width (mm)
    tw: float = 0.0  # Web thickness (mm)
    tf: float = 0.0  # Flange thickness (mm)
    r: float = 0.0  # Root radius (mm)
    d: float = 0.0  # Depth between fillets (mm)
    
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
    
    # Cross-sectional area
    A: float = 0.0  # Cross-sectional area (cm²)
    
    # Channel-specific properties
    c_y: float = 0.0  # Distance from web to shear center (mm)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PFC
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return {
            'designation': self.designation,
            'serial_size': self.serial_size,
            'mass_per_metre': self.mass_per_metre,
            'h': self.h,
            'b': self.b,
            'tw': self.tw,
            'tf': self.tf,
            'A': self.A,
            'I_yy': self.I_yy,
            'I_zz': self.I_zz,
        }


# Convenience function for direct instantiation
def PFC(designation: str, data_directory: Optional[Path] = None) -> ParallelFlangeChannel:
    """Create a Parallel Flange Channel section by designation."""
    factory = get_uk_factory(data_directory)
    return factory.create_section(designation, SectionType.PFC)
