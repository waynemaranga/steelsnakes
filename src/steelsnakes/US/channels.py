from dataclasses import dataclass, asdict
from steelsnakes.base import BaseSection, SectionType
from typing import Any, cast, Optional
from steelsnakes.US.factory import USSectionFactory, get_US_factory

@dataclass
class Channel(BaseSection):
    # Identification
    designation: str
    section_type: str # read as 'type' in database # TODO: change to section_type in database
    EDI_Std_Nomenclature: str = ""
    
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
    kdet: float = 0.0 #
    x: float = 0.0 #
    eo: float = 0.0 #
    xp: float = 0.0 #
    b_t: float = 0.0 # 
    h_tw: float = 0.0 #

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
    Wno: float = 0.0 #
    Sw1: float = 0.0 #
    Sw2: float = 0.0 #
    Sw3: float = 0.0 #
    Qf: float = 0.0 #
    Qw: float = 0.0 #
    ro: float = 0.0 #
    H: float = 0.0 #
    rts: float = 0.0 #
    ho: float = 0.0 #
    PA: float = 0.0 #
    PB: float = 0.0 #
    PC: float = 0.0 #
    PD: float = 0.0 #
    T: float = 0.0 #
    WGi: float = 0.0 #

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self)



@dataclass
class StandardChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.C

@dataclass
class MiscellaneousChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MC

@dataclass
class DoubleStandardChannel(Channel):
    # TODO: Find way to implement Double Channel properties
    pass

@dataclass
class DoubleMiscellaneousChannel(Channel):
    pass

def C(designation: str) -> Channel:
    return cast(Channel, get_US_factory().create_section(designation, SectionType.C))

def MC(designation: str) -> MiscellaneousChannel:
    return cast(MiscellaneousChannel, get_US_factory().create_section(designation, SectionType.MC))

if __name__ == "__main__":
    print(C("C6X10.5").get_properties())
    print(MC("MC6X6.5").get_properties())
    print("🐬")