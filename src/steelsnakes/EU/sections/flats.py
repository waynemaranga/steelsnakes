from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Union, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.factory import EUSectionFactory, SectionFactory, get_EU_factory

@dataclass
class Sigma(BaseSection):
    serial_size: str = ""
    hw: float = 0.0
    tn: float = 0.0
    b: float = 0.0
    bw0: float = 0.0
    bw1: float = 0.0
    bw2: float = 0.0
    bw3: float = 0.0
    bw4: float = 0.0
    c: float = 0.0
    d: float = 0.0
    Ag: float = 0.0
    m: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    Z_yy: float = 0.0
    Z_zz: float = 0.0
    dy: float = 0.0
    I_t: float = 0.0
    I_w: float = 0.0
    histar_fy: bool = False

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.Sigma

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)
    

@dataclass
class Zed(BaseSection):
    serial_size: str = ""
    hw: float = 0.0 
    tn: float = 0.0
    B1: float = 0.0 
    B2: float = 0.0 
    C: float = 0.0 
    Ag: float = 0.0 
    m: float = 0.0
    I_yy: float = 0.0 
    I_zz: float = 0.0 
    i_yy: float = 0.0
    i_zz: float = 0.0
    W_yy: float = 0.0 
    W_zz: float = 0.0 
    ygc: float = 0.0
    zgc: float = 0.0
    y0: float = 0.0
    z0: float = 0.0
    I_t: float = 0.0 
    I_w: float = 0.0 
    histar_fy: bool = False

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.Zed
    
    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict
        return asdict(self)
  
    

def S_section(designation: str) -> Sigma:
    factory: EUSectionFactory = get_EU_factory()
    return cast(Sigma, factory.create_section(designation, SectionType.Sigma))

def Z_section(designation: str) -> Zed:
    factory: EUSectionFactory = get_EU_factory()
    return cast(Zed, factory.create_section(designation, SectionType.Zed))

if __name__ == "__main__":
    print(S_section("A140100").get_properties())
    print(Z_section("Z140100").get_properties())
    print("🐬")