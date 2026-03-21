"""European Beam sections"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, cast
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.factory import get_EU_factory

@dataclass
class BearingPile(BaseSection):
    """Base class for all European steel BearingPile sections."""
    
    # Identification  
    serial_size: str = ""
    histar_fy: bool = False # yield strength calculated from histar
    
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
        from dataclasses import asdict
        return asdict(self)


@dataclass
class WideFlangeBearingPile(BearingPile):
    """Wide Flange BearingPile section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HP

@dataclass
class UniversalBearingPile(BearingPile):
    """Universal BearingPile section."""

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UBP

# ------------------------------------------------------------


def HP(designation: str) -> WideFlangeBearingPile:
    return cast(WideFlangeBearingPile, get_EU_factory().create_section(designation))
 

def UBP(designation: str) -> UniversalBearingPile:
    return cast(UniversalBearingPile, get_EU_factory().create_section(designation))


if __name__ == "__main__":
    # print(UBP("356x406x1299").get_properties(), "\n") # FIXME: Unexpected behaviour: created UBP using UC designation; probably due to mathching properties
    # print(HP("HD-400x421").get_properties()) # FIXME: Unexpected behaviour: created HP using HD designation; probably due to mathching properties
    
    print(UBP("356x368x109").get_properties(), "\n") 
    print(HP("HP-400x231").get_properties()) 
    print("🐬")