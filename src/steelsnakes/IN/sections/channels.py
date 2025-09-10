from __future__ import annotations
from dataclasses import dataclass
from steelsnakes.base import BaseSection, SectionType
from typing import Optional
from pathlib import Path

@dataclass
class Channel(BaseSection):
    M: float = 0.0 # Mass per metre (kg/m)
    area: float = 0.0 # Area (x10² mm²)
    D: float = 0.0 # Depth (mm)
    B: float = 0.0 # Width (mm)
    t: float = 0.0 # Web thickness (mm)
    T: float = 0.0 # Flange thickness (mm)
    alpha: float = 0.0 # Flange slope (deg)
    R1: float = 0.0 # Root radius (mm)
    R2: float = 0.0 # Toe radius (mm), for tapered flanges # TODO: check other stuff
    C_y: float = 0.0 # B - ey (mm)
    
    I_yy: float = 0.0 # Second moment of area, y-axis (x10⁴ mm⁴)
    r_y: float = 0.0 # Radius of gyration, y-axis (mm)
    Z_yy: float = 0.0 # Elastic section modulus, y-axis (x10³ mm³)
    Z_py: float = 0.0 # Plastic section modulus, y-axis (x10³ mm³)

    I_zz: float = 0.0 # Second moment of area, z-axis (x10⁴ mm⁴)
    r_z: float = 0.0 # Radius of gyration, z-axis (mm)
    Z_zz: float = 0.0 # Elastic section modulus, z-axis (x10³ mm³)
    Z_pz: float = 0.0 # Plastic section modulus, z-axis (x10³ mm³)

    I_t: float = 0.0 # Torsional constant (x10⁴ mm⁴)
    I_w: float = 0.0 # Warping constant (x10⁶ mm⁶)


@dataclass
class JuniorChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.JC

@dataclass
class LightWeightChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.LWC

@dataclass
class MediumWeightChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MWC

@dataclass
class MediumWeightParallelFlangeChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MPC

def JC(designation: str, data_directory: Optional[Path] = None) -> JuniorChannel:
    raise NotImplementedError("ISJC section creation not implemented yet.")

def LWC(designation: str, data_directory: Optional[Path] = None) -> LightWeightChannel:
    raise NotImplementedError("ISLC section creation not implemented yet.")

def MWC(designation: str, data_directory: Optional[Path] = None) -> MediumWeightChannel:
    raise NotImplementedError("ISMC section creation not implemented yet.")

def MPC(designation: str, data_directory: Optional[Path] = None) -> MediumWeightParallelFlangeChannel:
    raise NotImplementedError("ISMPC section creation not implemented yet.")

if __name__ == "__main__":
    print("🐬")