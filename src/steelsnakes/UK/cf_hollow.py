"""
Cold Formed Hollow sections for UK module.
This module implements Cold Formed Circular, Square, and Rectangular Hollow Sections.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


@dataclass
class ColdFormedCircularHollowSection(BaseSection):
    """Cold Formed Circular Hollow Section (CFCHS)."""
    
    mass_per_metre: float = 0.0
    d: float = 0.0
    t: float = 0.0
    is_additional: float = 0.0
    mass_per_metre: float = 0.0
    A: float = 0.0
    d_t: float = 0.0
    I: float = 0.0
    i: float = 0.0
    W_el: float = 0.0
    W_pl: float = 0.0
    I_t: float = 0.0
    W_t: float = 0.0
    surface_area_per_metre: float = 0.0
    surface_area_per_tonne: float = 0.0
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFCHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class ColdFormedSquareHollowSection(BaseSection):
    """Cold Formed Square Hollow Section (CFSHS)."""
    
    mass_per_metre: float = 0.0
    hxh: float = 0.0 
    t: float = 0.0 
    is_additional: float = 0.0 
    mass_per_metre: float = 0.0 
    A: float = 0.0 
    c_t: float = 0.0
    I: float = 0.0
    i: float = 0.0
    W_el: float = 0.0
    W_pl: float = 0.0
    I_t: float = 0.0
    W_t: float = 0.0
    surface_area_per_metre: float = 0.0
    surface_area_per_tonne: float = 0.0
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFSHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class ColdFormedRectangularHollowSection(BaseSection):
    """Cold Formed Rectangular Hollow Section (CFRHS)."""
    
    mass_per_metre: float = 0.0
    hxb: float = 0.0 
    t: float = 0.0 
    is_additional: float = 0.0 
    mass_per_metre: float = 0.0 
    A: float = 0.0 
    cw_t: float = 0.0 
    cf_t: float = 0.0 
    I_yy: float = 0.0 
    I_zz: float = 0.0 
    i_yy: float = 0.0 
    i_zz: float = 0.0 
    W_el_yy: float = 0.0 
    W_el_zz: float = 0.0 
    W_pl_yy: float = 0.0 
    W_pl_zz: float = 0.0 
    I_t: float = 0.0 
    W_t: float = 0.0 
    surface_area_per_metre: float = 0.0 
    surface_area_per_tonne: float = 0.0 
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFRHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)

# Convenience functions
def CFCHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedCircularHollowSection:
    """Create a Cold Formed Circular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFCHS)
    return cast(ColdFormedCircularHollowSection, factory.create_section(designation, SectionType.CFCHS))


def CFSHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedSquareHollowSection:
    """Create a Cold Formed Square Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFSHS)
    return cast(ColdFormedSquareHollowSection, factory.create_section(designation, SectionType.CFSHS))


def CFRHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedRectangularHollowSection:
    """Create a Cold Formed Rectangular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFRHS)
    return cast(ColdFormedRectangularHollowSection, factory.create_section(designation, SectionType.CFRHS))


if __name__ == "__main__":
    print(CFCHS("33.7x3.0").get_properties())
    print(CFRHS("50x25x2.0").get_properties())
    print(CFSHS("25x25x2.0").get_properties())
    print("🐬")