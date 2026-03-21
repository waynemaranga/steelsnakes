from dataclasses import dataclass, asdict
from typing import Any, Optional, cast
from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import SectionFactory, get_US_factory

@dataclass
class Tee(BaseSection):
    section_type: str = ""
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0
    A: float = 0.0
    d: float = 0.0
    ddet: float = 0.0
    bf: float = 0.0
    bfdet: float = 0.0
    tw: float = 0.0
    twdet: float = 0.0
    twdet_2: float = 0.0
    tf: float = 0.0
    tfdet: float = 0.0
    kdes: float = 0.0
    kdet: float = 0.0
    y: float = 0.0
    yp: float = 0.0
    bf_2tf: float = 0.0
    D_t: float = 0.0
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    J: float = 0.0
    Cw: float = 0.0
    ro: float = 0.0
    H: float = 0.0

    def get_properties(self) -> dict[str, Any]:
        return asdict(self)
    

@dataclass
class StandardTee(Tee):
    WGi: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.ST

@dataclass
class MiscellaneousTee(Tee):
    T_F: str = ""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MT

@dataclass
class WideFlangeTee(Tee):
    T_F: str = ""
    H: float =  0.0
    PA: float = 0.0
    PB: float = 0.0
    PC: float = 0.0
    PD: float = 0.0
    WGi: float = 0.0
    WGo: float = 0.0


    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WT


def ST(designation: str) -> StandardTee:
    return cast(StandardTee, get_US_factory().create_section(designation, SectionType.ST))

def MT(designation: str) -> MiscellaneousTee:
    return cast(MiscellaneousTee, get_US_factory().create_section(designation, SectionType.MT))

def WT(designation: str) -> WideFlangeTee:
    return cast(WideFlangeTee, get_US_factory().create_section(designation, SectionType.WT))


if __name__ == "__main__":
    print(ST("ST12X60.5").get_properties())
    print(MT("MT6.25X6.2").get_properties())
    print(WT("WT22X184").get_properties())
    print("🐬")