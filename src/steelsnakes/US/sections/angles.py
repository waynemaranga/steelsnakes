from dataclasses import dataclass, asdict
from steelsnakes.base import BaseSection, SectionType
from typing import Any, Optional, cast
from steelsnakes.US.factory import get_US_factory, USSectionFactory

@dataclass
class Angle(BaseSection):
    section_type: float = 0.0
    EDI_Std_Nomenclature: float = 0.0
    W: float = 0.0
    A: float = 0.0
    d: float = 0.0
    b: float = 0.0
    t: float = 0.0
    kdes: float = 0.0
    kdet: float = 0.0
    x: float = 0.0
    y: float = 0.0
    xp: float = 0.0
    yp: float = 0.0
    b_t: float = 0.0
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    Iz: float = 0.0
    rz: float = 0.0
    Sz: float = 0.0
    J: float = 0.0
    Cw: float = 0.0
    ro: float = 0.0
    #// H: float = 0.0 # Only for Equal Angles
    tan_alpha: float = 0.0
    Iw: float = 0.0
    zA: float = 0.0
    zB: float = 0.0
    zC: float = 0.0
    wA: float = 0.0
    wB: float = 0.0
    wC: float = 0.0
    SwA: float = 0.0
    #// SwB: float = 0.0 # Only for Unequal Angles
    SwC: float = 0.0
    SzA: float = 0.0
    SzB: float = 0.0
    SzC: float = 0.0
    PA: float = 0.0
    PA2: float = 0.0
    PB: float = 0.0

    def get_properties(self) -> dict[str, float]:
        """Return all section properties as a dictionary."""
        return asdict(self)

@dataclass
class DoubleAngle(BaseSection):
    section_type: str = ""
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0
    A: float = 0.0
    d: float = 0.0
    b: float = 0.0
    t: float = 0.0
    y: float = 0.0
    yp: float = 0.0
    b_t: float = 0.0
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    ro: float = 0.0
    H: float = 0.0

    def get_properties(self) -> dict[str, float]:
        """Return all section properties as a dictionary."""
        return asdict(self)
    

@dataclass
class EqualAngle(Angle):
    H: float = 0.0
   
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL

@dataclass
class UnequalAngle(Angle):
    SwB: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL


@dataclass
class BackToBackEqualAngle(DoubleAngle):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L2L_EQUAL
    
@dataclass
class LongLegBackToBackUnequalAngle(DoubleAngle):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L2L_LLBB
    
@dataclass
class ShortLegBackToBackUnequalAngle(DoubleAngle):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L2L_SLBB


def L_EQUAL(designation: str) -> EqualAngle:
    """Create an Equal Angle section by designation."""
    return cast(EqualAngle, get_US_factory().create_section(designation, SectionType.L_EQUAL))

def L_UNEQUAL(designation: str) -> UnequalAngle:
    """Create an Unequal Angle section by designation."""
    return cast(UnequalAngle, get_US_factory().create_section(designation, SectionType.L_UNEQUAL))

def L2L_EQUAL(designation: str) -> BackToBackEqualAngle:
    """Create a Back-to-Back Equal Angle section by designation."""
    return cast(BackToBackEqualAngle, get_US_factory().create_section(designation, SectionType.L2L_EQUAL))

def L2L_LLBB(designation: str) -> LongLegBackToBackUnequalAngle:
    """Create a Long Leg Back-to-Back Unequal Angle section by designation."""
    return cast(LongLegBackToBackUnequalAngle, get_US_factory().create_section(designation, SectionType.L2L_LLBB))

def L2L_SLBB(designation: str) -> ShortLegBackToBackUnequalAngle:
    """Create a Short Leg Back-to-Back Unequal Angle section by designation."""
    return cast(ShortLegBackToBackUnequalAngle, get_US_factory().create_section(designation, SectionType.L2L_SLBB))


if __name__ == "__main__":
    print(L_EQUAL("L4X4X1/2").get_properties())
    print(L_UNEQUAL("L6X4X1/2").get_properties())
    print(L2L_EQUAL("2L4X4X1/2X3/8").get_properties())
    print(L2L_LLBB("2L6X4X1/2X3/8LLBB").get_properties())
    print(L2L_SLBB("2L7X4X1/2X3/8SLBB").get_properties())

