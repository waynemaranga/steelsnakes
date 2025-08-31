from dataclasses import dataclass, asdict
from typing import Any, cast, Optional
from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import get_US_factory, USSectionFactory

@dataclass
class HollowStructuralSection(BaseSection):
    designation: str
    section_type: str # read as 'type' in database # TODO: change to section_type in database
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0 # Nominal weight (lb/ft)
    A: float = 0.0 # Area (in²)

    tnom: float = 0.0
    tdes: float = 0.0
    
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    J: float = 0.0
    C: float = 0.0

    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        return asdict(self)
    
@dataclass
class RectangularHSS(HollowStructuralSection):
    Ht: float = 0.0
    h: float = 0.0
    B: float = 0.0
    b: float = 0.0
    b_tdes: float = 0.0
    h_tdes: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_RCT


@dataclass
class SquareHSS(HollowStructuralSection):
    Ht: float = 0.0
    h: float = 0.0
    B: float = 0.0
    b: float = 0.0
    b_tdes: float = 0.0
    h_tdes: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_SQR

@dataclass
class RoundHSS(HollowStructuralSection):
    OD: float = 0.0
    D_t: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_RND
    

# Convenience functions for direct instantiation
def HSS_RCT(designation: str) -> RectangularHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(RectangularHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_RCT))

def HSS_SQR(designation: str) -> SquareHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(SquareHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_SQR))

def HSS_RND(designation: str) -> RoundHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(RoundHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_RND))

if __name__ == "__main__":
    print(HSS_RCT("HSS10X6X1/2").get_properties())
    print(HSS_SQR("HSS8X8X3/8").get_properties())
    print(HSS_RND("HSS5.563X0.134").get_properties())