from __future__ import annotations
from dataclasses import dataclass, asdict
from steelsnakes.base import BaseSection, SectionType
from typing import Optional, cast, Any
from pathlib import Path
# from steelsnakes.IN.factory import INSectionFactory, get_IN_factory

@dataclass
class Beam(BaseSection):
    M: float = 0.0 # Mass per metre (kg/m)
    area: float = 0.0 # Area (x100 mm²)
    D: float = 0.0 # Depth (mm) # TODO: rework DB to rename elements to IS808:2021 names e.g h to D
    B: float = 0.0 # Width (mm)
    t: float = 0.0 # Web thickness (mm)
    T: float = 0.0 # Flange thickness (mm)
    alpha: float = 0.0 # Flange slope (deg)
    R1: float = 0.0 # Root radius (mm)
    R2: float = 0.0 # Toe radius (mm), for tapered flanges # TODO: check other stuff
    
    I_yy: float = 0.0 # Second moment of area, y-axis (x10⁴ mm⁴) # TODO: 
    r_y: float = 0.0 # Radius of gyration, y-axis (mm) # FIXME: database seems ridden with errors (or units issues; consider finding new db, shipping without db, or user-defined sections)
    Z_yy: float = 0.0 # Elastic section modulus, y-axis (x10³ mm³)
    Z_py: float = 0.0 # Plastic section modulus, y-axis (x10³ mm³)

    I_zz: float = 0.0 # Second moment of area, z-axis (x10⁴ mm⁴)
    r_z: float = 0.0 # Radius of gyration, z-axis (mm)
    Z_zz: float = 0.0 # Elastic section modulus, z-axis (x10³ mm³)
    Z_pz: float = 0.0 # Plastic section modulus, z-axis (x10³ mm³)

    I_t: float = 0.0 # Torsional constant (x10⁴ mm⁴)
    I_w: float = 0.0 # Warping constant (x10⁶ mm⁶)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self)


@dataclass
class JuniorBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.JB

@dataclass
class LightWeightBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.LWB

@dataclass
class MediumWeightBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MWB

@dataclass
class WideFlangeBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WFB

@dataclass
class NarrowParallelFlangeBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.NPB

@dataclass
class WideParallelFlangeBeam(Beam):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WPB



def JB(designation: str, data_directory: Optional[Path] = None) -> JuniorBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(JuniorBeam, factory.create_section(designation, SectionType.ISJB))
    raise NotImplementedError("ISJB section creation not implemented yet.")

def LWB(designation: str, data_directory: Optional[Path] = None) -> LightWeightBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(LightWeightBeam, factory.create_section(designation, SectionType.ISLWB))
    raise NotImplementedError("ISLWB section creation not implemented yet.")

def MWB(designation: str, data_directory: Optional[Path] = None) -> MediumWeightBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(MediumWeightBeam, factory.create_section(designation, SectionType.ISMWB))
    raise NotImplementedError("ISMWB section creation not implemented yet.")

def WFB(designation: str, data_directory: Optional[Path] = None) -> WideFlangeBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(WideFlangeBeam, factory.create_section(designation, SectionType.ISWFB))
    raise NotImplementedError("ISWFB section creation not implemented yet.")

def NPB(designation: str, data_directory: Optional[Path] = None) -> NarrowParallelFlangeBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(NarrowParallelFlangeBeam, factory.create_section(designation, SectionType.ISNPB))
    raise NotImplementedError("ISNPB section creation not implemented yet.")

def WPB(designation: str, data_directory: Optional[Path] = None) -> WideParallelFlangeBeam:
    # factory: INSectionFactory = get_IN_factory(data_directory)
    # return cast(WideParallelFlangeBeam, factory.create_section(designation, SectionType.ISWPB))
    raise NotImplementedError("ISWPB section creation not implemented yet.")


if __name__ == "__main__":
   print("🐬")