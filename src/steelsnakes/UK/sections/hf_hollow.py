"""
Hot Finished Hollow sections for UK module.
This module implements Hot Finished Circular, Square, Rectangular,
and Elliptical Hollow Sections.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


@dataclass
class HotFinishedCircularHollowSection(BaseSection):
    """Hot Finished Circular Hollow Section (HFCHS)."""
    
    # Basic properties - to be expanded based on actual data structure
    mass_per_metre: float = 0.0
    A: float = 0.0  # Cross-sectional area (cm²)
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
        return SectionType.HFCHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class HotFinishedSquareHollowSection(BaseSection):
    """Hot Finished Square Hollow Section (HFSHS)."""
    
    mass_per_metre: float = 0.0
    hxh: str = ""
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
        return SectionType.HFSHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class HotFinishedRectangularHollowSection(BaseSection):
    """Hot Finished Rectangular Hollow Section (HFRHS)."""
    
    mass_per_metre: float = 0.0
    hxb: str = ""
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
        return SectionType.HFRHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class HotFinishedEllipticalHollowSection(BaseSection):
    """Hot Finished Elliptical Hollow Section (HFEHS)."""
    
    mass_per_metre: float = 0.0
    hxb: str = ""
    t: float = 0.0
    is_additional: float = 0.0
    mass_per_metre: float = 0.0
    A: float = 0.0
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
        return SectionType.HFEHS
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


# Convenience functions
def HFCHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedCircularHollowSection:
    """Create a Hot Finished Circular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.HFCHS) # Older implementation; raised Pylance[reportReturnType]
    return cast(HotFinishedCircularHollowSection, factory.create_section(designation, SectionType.HFCHS))


def HFSHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedSquareHollowSection:
    """Create a Hot Finished Square Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.HFSHS)
    return cast(HotFinishedSquareHollowSection, factory.create_section(designation, SectionType.HFSHS))


def HFRHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedRectangularHollowSection:
    """Create a Hot Finished Rectangular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.HFRHS)
    return cast(HotFinishedRectangularHollowSection, factory.create_section(designation, SectionType.HFRHS))


def HFEHS(designation: str, data_directory: Optional[Path] = None) -> HotFinishedEllipticalHollowSection:
    """Create a Hot Finished Elliptical Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.HFEHS)
    return cast(HotFinishedEllipticalHollowSection, factory.create_section(designation, SectionType.HFEHS))

if __name__ == "__main__":
    print(HFCHS("48.3x3.6").get_properties())
    print(HFEHS("300x150x12.5").get_properties())
    print(HFRHS("50x30x4.0").get_properties())
    print(HFSHS("50x50x3.2").get_properties())
    print("🐬")