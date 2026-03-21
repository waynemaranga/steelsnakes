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

    def classification_elements(self) -> list[Any]:
        """Return beam geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import i_section_elements

        if self.h_tw <= 0.0:
            raise ValueError(
                "Beam classification requires the exact AISC web slenderness h/tw. "
                "Populate 'h_tw' from the section database instead of substituting d/tw."
            )
        h_over_tw = self.h_tw
        bf_over_2tf = self.bf_2tf if self.bf_2tf > 0.0 else (self.bf / (2.0 * self.tf) if self.bf > 0.0 and self.tf > 0.0 else 0.0)
        return i_section_elements(h_over_tw=h_over_tw, bf_over_2tf=bf_over_2tf)

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


def W_beam(designation: str) -> WideFlangeBeam:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(WideFlangeBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.W))

def S_beam(designation: str) -> StandardBeam:
    """Note: case insensitive - accepts both "x" and "X" separators"""
    return cast(StandardBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.S))

def M_beam(designation: str) -> MiscellaneousBeam:
    """Note: case insensitive - accepts both "x" and "X" separators"""
    return cast(MiscellaneousBeam, get_US_factory().create_section(designation.upper().strip(), SectionType.M))

if __name__ == "__main__":
    from steelsnakes.US.checks.classification import ClassificationContext, classify_section

    section = W_beam("W36x350")
    print(section.get_properties())
    print(classify_section(section=section, Fy_ksi=50.0).model_dump())
    print(
        classify_section(
            section=section,
            Fy_ksi=50.0,
            classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
        ).model_dump()
    )
    print(
        classify_section(
            section=section,
            Fy_ksi=50.0,
            classification_context=ClassificationContext.FLEXURE_MINOR_AXIS,
        ).model_dump()
    )
