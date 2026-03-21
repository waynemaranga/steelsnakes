from dataclasses import dataclass, asdict
from typing import Any, Optional, cast
from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US_Metric.factory import USMetricSectionFactory, get_US_Metric_factory


@dataclass
class Pile(BaseSection):
    # Identification
    section_type: str #
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
        return asdict(self) # SAFE: applies recursively to field values that are dataclass instances.

@dataclass
class BearingPile(Pile):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HP
    
def HP(designation: str) -> BearingPile:
    return cast(BearingPile, get_US_Metric_factory().create_section(designation, SectionType.HP))
    

if __name__ == "__main__":
    # Example usage
    pile = HP("HP360X108")
    if pile:
        print(f"Successfully created pile: {pile.designation}")
        print(pile.get_properties())
    else:
        print("Pile not found.")