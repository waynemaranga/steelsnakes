"""
Channel steel sections for EU module.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast, Union

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.factory import EUSectionFactory, get_EU_factory


@dataclass
class ParallelFlangeChannel(BaseSection):
    """
    Parallel Flange Channel (PFC) section.
    
    C-shaped section with parallel flanges, commonly used for 
    secondary beams, purlins, and cladding rails.
    
    Supports both PFC and UPE section types through factory registration.
    The factory will register this class for both SectionType.PFC and SectionType.UPE.
    """
    
    # Identification
    serial_size: str = ""
    histar_fy: bool = False
    mass_per_metre: float = 0.0
    h: float = 0.0
    b: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    r: float = 0.0
    d: float = 0.0
    cw_tw: float = 0.0
    cf_tf: float = 0.0
    e0: float = 0.0
    C: float = 0.0
    N: float = 0.0
    n: float = 0.0
    surface_area_per_metre: float = 0.0
    surface_area_per_tonne: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    W_pl_yy: float = 0.0
    W_pl_zz: float = 0.0
    U: float = 0.0
    X: float = 0.0
    I_w: float = 0.0
    I_t: float = 0.0
    A: float = 0.0
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        #// return cast(SectionType, Union[SectionType.PFC, SectionType.UPE])
        # Return PFC as the primary type - factory will handle both PFC and UPE registration
        return SectionType.PFC
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)


@dataclass
class TaperedFlangeChannel(BaseSection):
    
    serial_size: str = ""
    histar_fy: bool = False
    
    # 
    mass_per_metre: float = 0.0
    h: float = 0.0
    b: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    r_1: float = 0.0
    r_2: float = 0.0
    d: float = 0.0
    cw_tw: float = 0.0
    cf_tf: float = 0.0
    e0: float = 0.0
    C: float = 0.0
    N: float = 0.0
    n: float = 0.0
    surface_area_per_metre: float = 0.0
    surface_area_per_tonne: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    W_pl_yy: float = 0.0
    W_pl_zz: float = 0.0
    U: float = 0.0
    X: float = 0.0
    I_w: float = 0.0
    I_t: float = 0.0
    A: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return cast(SectionType, SectionType.UPN) # FIXME: check if Unions are the ussue
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)

# Convenience function for direct instantiation
def PFC(designation: str, data_directory: Optional[Path] = None) -> ParallelFlangeChannel:
    """Create a Parallel Flange Channel section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    # return factory.create_section(designation, SectionType.PFC)
    return cast(ParallelFlangeChannel, factory.create_section(designation, SectionType.PFC))

def UPE(designation: str, data_directory: Optional[Path] = None) -> ParallelFlangeChannel:
    """Create a Parallel Flange Channel section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    # return factory.create_section(designation, SectionType.UPE)
    return cast(ParallelFlangeChannel, factory.create_section(designation, SectionType.UPE))


def UPN(designation: str, data_directory: Optional[Path] = None) -> TaperedFlangeChannel:
    """Create a Parallel Flange Channel section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    # return factory.create_section(designation, SectionType.UPN)
    return cast(TaperedFlangeChannel, factory.create_section(designation, SectionType.UPN))

if __name__ == "__main__":
    print(PFC("430x100x64").get_properties())
    print(UPE("UPE-400").get_properties())
    print(UPN("UPN-400").get_properties())
    print("🐬")