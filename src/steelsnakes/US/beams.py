from dataclasses import dataclass
from typing import Any, Optional, cast
from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import USSectionFactory, get_US_factory

@dataclass
class Beam(BaseSection):
    # Identification
    section_type: str # implement section type in all json
    EDI_Std_Nomenclature: str = ""
    T_F: str = ""

    # 
    W: float = 0.0 # Nominal weight (lb/ft)
    A: float = 0.0 # Area (in²)
    d: float = 0.0 # Depth (in)
    ddet: float = 0.0 #
    bf: float = 0.0 # Flange width (in)
    bfdet: float = 0.0 # 
    tw: float = 0.0 # Web thickness (in)
    twdet: float = 0.0 #
    twdet_2: float = 0.0 #
    tf: float = 0.0 # Flange thickness (in)
    tfdet: float = 0.0
    kdes: float = 0.0 #
    kdet: float = 0.0 
    k1: float = 0.0 #

    # Compact section criteria
    bf_2tf: float = 0.0 #
    h_tw: float = 0.0

    Ix: float = 0.0 # Moment of inertia, major axis (in^4)
    Zx: float = 0.0 # Plastic section modulus, major axis (in^3)
    Sx: float = 0.0 # Elastic section modulus, major axis (in^3)
    rx: float = 0.0 # Radius of gyration

    Iy: float = 0.0 # Moment of inertia, minor axis (in^4)
    Zy: float = 0.0 # Plastic section modulus, minor axis (in^3)
    Sy: float = 0.0 # Elastic section modulus, minor axis (in^3)
    ry: float = 0.0 # Radius of gyration

    J: float = 0.0 # Torsional constant (in^4)
    Cw: float = 0.0 # Warping constant (in^6)
    Wno: float = 0.0
    Sw1: float = 0.0
    Qf: float = 0.0
    Qw: float = 0.0
    rts: float = 0.0
    ho: float = 0.0
    PA: float = 0.0
    PB: float = 0.0
    PC: float = 0.0
    PD: float = 0.0
    T: float = 0.0
    WGi: float = 0.0
    WGo: float = 0.0

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self) # SAFE: applies recursively to field values that are dataclass instances.


@dataclass
class WideFlangeBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.W


@dataclass
class StandardBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.S

@dataclass
class MiscellaneousBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.M


def W(designation: str) -> WideFlangeBeam:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(WideFlangeBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.W))

def S(designation: str) -> StandardBeam:
    """Note: case insensitive - accepts both "x" and "X" separators"""
    return cast(StandardBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.S))

def M(designation: str) -> MiscellaneousBeam:
    """Note: case insensitive - accepts both "x" and "X" separators"""
    return cast(MiscellaneousBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.M))

if __name__ == "__main__":
    print(W("W36x350").get_properties())
    print(S("S10X35").get_properties())
    print(M("M12x10.8").get_properties())