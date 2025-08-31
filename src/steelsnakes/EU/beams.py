"""European Beam sections"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Union, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.factory import EUSectionFactory, SectionFactory, get_EU_factory

@dataclass
class Beam(BaseSection):
    """Base class for all European steel beam sections."""
    
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
class ParallelFlangeBeam(Beam):
    """Parallel Flange I-beam section."""
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.IPE

@dataclass
class WideFlangeBeam(Beam):
    """Wide Flange Beam section."""
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HE

@dataclass
class ExtraWideFlangeBeam(Beam):
    """Extra Wide Flange Beam section."""
    @classmethod
    def get_section_type(cls) -> SectionType:
        # return Union[SectionType.HL, SectionType.HLZ] # Pylance[reportReturnType]: https://github.com/microsoft/pylance-release/blob/main/docs/diagnostics/reportReturnType.md
        return cast(SectionType, Union[SectionType.HL, SectionType.HLZ]) # FIXME: see if Unions bring issues...

@dataclass
class UniversalBeam(Beam):
    """Universal Beam section."""
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UB

# ------------------------------------------------------------


def IPE(designation: str) -> ParallelFlangeBeam:
    """IPE section - inherits IPE type from parent."""
    factory: EUSectionFactory = get_EU_factory()
    return cast(ParallelFlangeBeam, factory.create_section(designation, SectionType.IPE))


def HE(designation: str) -> WideFlangeBeam:
    """HE section - inherits HE type from parent."""
    factory: EUSectionFactory = get_EU_factory()
    return cast(WideFlangeBeam, factory.create_section(designation, SectionType.HE))


def HL(designation: str) -> ExtraWideFlangeBeam:
    """HL section - inherits HL type from parent."""
    # TODO: handle HL/HLZ differentiator, since file-name factory system expects HL.json and HLZ.json
    factory: EUSectionFactory = get_EU_factory()
    return cast(ExtraWideFlangeBeam, factory.create_section(designation, SectionType.HL))


def HLZ(designation: str) -> ExtraWideFlangeBeam:
    """HLZ section."""
    # TODO: handle HL/HLZ differentiator, since file-name factory system expects HL.json and HLZ.json
    factory: EUSectionFactory = get_EU_factory()
    return cast(ExtraWideFlangeBeam, factory.create_section(designation, SectionType.HLZ))
    

def UB(designation: str) -> UniversalBeam:
    """UB section - inherits UB type from parent."""
    # factory: EUSectionFactory = get_EU_factory()
    return cast(UniversalBeam, get_EU_factory().create_section(designation, SectionType.UB))


if __name__ == "__main__":
    # factory: EUSectionFactory = get_EU_factory()
    # test_section = factory.create_section("1100x400x607", section_type=SectionType.UB)
    # print(test_section.get_properties())

    print(UB("1100x400x433").get_properties())
    # print(HL("HL-1100-M").get_properties()) # FIXME: Why doesn't this work?
    # print(HLZ("HLZ-1100").get_properties()) # FIXME: Why doesn't this work?
    print(IPE("IPE-750x220").get_properties())
    
    
    print("🐬")