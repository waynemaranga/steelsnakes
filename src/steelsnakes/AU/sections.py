from __future__ import annotations
from steelsnakes.base.sections import BaseSection, SectionType
from dataclasses import dataclass, asdict
from typing import Any, cast, Optional, Union
from enum import Enum

class AustralianSection(BaseSection):
    serial_size: str = "" # e.g 610 UB or 610-UB # TODO: search/implement designation for AS/NZS
    mass_per_metre: float = 0.0  # mass per metre (kg/m)

    @classmethod
    def get_section_type(cls) -> Any:
        return super().get_section_type()
    
    def get_properties(self) -> dict[str, Any]:
        return asdict(self)

class I_Section(AustralianSection):
    # Parameters based on AS/NZS 3679.1:2010 Appendix D
    # Also, not that many sections, and not too many columns, so workable
    d: float = 0.0  # depth (mm)
    bf: float = 0.0  # flange width (mm)
    tf: float = 0.0  # flange thickness (mm)
    tw: float = 0.0  # web thickness (mm)
    d1: float = 0.0  # depth between flanges (mm); except for TFB where it is depth at midpoint of flanges # FIXME: implement independently??
    # TODO: implement other properties as needed using either sectionproperties module or manual calc
    # TODO: make AU/NZ implementation more interesting... ensure in docs

class UniversalBeam(I_Section):
    r: float = 0.0  # root radius (mm)

    @classmethod
    def get_section_type(cls):
        # return SectionType.UB # FIXME: properties are different from UK/EU Universal Beam, and parameters have different names
        return NotImplementedError("")
    
class UniversalColumn(I_Section):
    r: float = 0.0  # root radius (mm)

    @classmethod
    def get_section_type(cls):
        # return SectionType.UC # FIXME: properties are different from UK/EU Universal Column, and parameters have different names
        return NotImplementedError("")

class TaperedFlangeBeam(I_Section):
    d2: float = 0.0  # depth between fillets (mm)
    r1: float = 0.0  # root radius (mm)
    r2: float = 0.0  # toe radius (mm)

    @classmethod
    def get_section_type(cls):
        # return SectionType.TFB # FIXME: properties are different from UK/EU Tapered Flange Beam, and parameters have different names
        return NotImplementedError("")

class ParallelFlangeChannel(AustralianSection):
    d: float = 0.0  # depth (mm)
    bf: float = 0.0  # flange width (mm)
    tf: float = 0.0  # flange thickness (mm)
    tw: float = 0.0  # web thickness (mm)
    d1: float = 0.0  # depth between flanges (mm)   
    r: float = 0.0  # root radius (mm)

    @classmethod
    def get_section_type(cls):
        # return SectionType.PFC # FIXME: properties are different from UK/EU Parallel Flange Channel, and parameters have different names
        return NotImplementedError("")

class Angle(AustralianSection):
    axb: str = ""  # e.g. 200x200 # Implement breakdown in other dataprep for EU/UK and fix
    a: float = 0.0  # leg a length (mm)
    b: float = 0.0  # leg b length (mm); is shorter leg in unequal angles
    tnom: float = 0.0  # nominal thickness (mm)
    t: float = 0.0  # actual thickness (mm)
    r1: float = 0.0  # root radius (mm)
    r2: float = 0.0  # toe radius (mm)

    production: Enum # Either AU for Australian production, or NZ for New Zealand production
    # TODO: add Australian production to AU module, and NZ production to NZ module

    @classmethod
    def get_section_type(cls):
        # return SectionType.ANGLE # FIXME: properties are different from UK/EU Angle, and parameters have different names
        return NotImplementedError("")
    
class EqualAngle(Angle):
    @classmethod
    def get_section_type(cls):
        # return SectionType.EA # FIXME: properties are different from UK/EU Equal Angle, and parameters have different names
        return NotImplementedError("")
    
class UnequalAngle(Angle):
    @classmethod
    def get_section_type(cls):
        # return SectionType.UA # FIXME: properties are different from UK/EU Unequal Angle, and parameters have different names
        return NotImplementedError("")




if __name__ == "__main__":
    
    print("🐬")