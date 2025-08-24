"""Base section for all steel sections"""

# Instance, class and static methods: https://realpython.com/instance-class-and-static-methods-demystified/
# Instance v Static v Class v Abstract Methods: https://medium.com/nerd-for-tech/python-instance-vs-static-vs-class-vs-abstract-methods-1952a5c77d9d

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
logger: logging.Logger = logging.getLogger(__name__)

class SectionType(Enum):
    """Global enumeration of all section types available in steelsnakes"""
    
    # --- 🇬🇧 UK ---
    # TODO: Add info here... Provided by Steel Construction Institute (SCI) via Blue Book
    # Universal Sections
    UB = "UB"   # Universal Beam
    UC = "UC"   # Universal Column
    UBP = "UBP" # Universal Beam with Parallel Flange

    # Channels
    PFC = "PFC" # Parallel Flange Channel

    # Angles
    L_EQUAL = "L_EQUAL"             # Equal Angle
    L_UNEQUAL = "L_UNEQUAL"         # Unequal Angle
    L_EQUAL_B2B = "L_EQUAL_B2B"     # Equal Angle Back-to-Back
    L_UNEQUAL_B2B = "L_UNEQUAL_B2B" # Unequal Angle Back-to-Back
    
    # Hollow sections (Hot Finished)
    HFCHS = "HFCHS"     # Hot Finished Circular Hollow Section
    HFRHS = "HFRHS"     # Hot Finished Rectangular Hollow Section
    HFSHS = "HFSHS"     # Hot Finished Square Hollow Section
    HFEHS = "HFEHS"     # Hot Finished Elliptical Hollow Section
    
    # Hollow sections (Cold Formed)
    CFCHS = "CFCHS"     # Cold Formed Circular Hollow Section
    CFRHS = "CFRHS"     # Cold Formed Rectangular Hollow Section
    CFSHS = "CFSHS"     # Cold Formed Square Hollow Section
    
    # Connection components
    WELDS = "WELDS"                 # Weld details
    BOLT_PRE_88 = "BOLT_PRE_88"     # Pre-loaded bolts (8.8 grade)
    BOLT_PRE_109 = "BOLT_PRE_109"   # Pre-loaded bolts (10.9 grade)
    # TODO: Implement non-preloaded bolts
    # BOLT_NON_PRE_CS_46 = "BOLT_NON_PRE_CS_46" # Countersunk, 4.6 grade
    # BOLT_NON_PRE_CS_88 = "BOLT_NON_PRE_CS_88" # Countersunk, 8.8 grade
    # BOLT_NON_PRE_CS_109 = "BOLT_NON_PRE_CS_109" # Countersunk, 10.9 grade
    # BOLT_NON_PRE_HEX_46 = "BOLT_NON_PRE_HEX_46" # Hexagon, 4.6 grade
    # BOLT_NON_PRE_HEX_88 = "BOLT_NON_PRE_HEX_88" # Hexagon, 8.8 grade
    # BOLT_NON_PRE_HEX_109 = "BOLT_NON_PRE_HEX_109" # Hexagon, 10.9 grade

    # --- 🇪🇺 EU ---
    # TODO: Add info here... Provided by ArcelorMittal via Orange Book
    #  Beams 
    IPE = "IPE"   # Parallel Flange I-beams
    HE = "HE"     # Wide Flange Beams
    HL = "HL"     # Extra Wide Flange Beams
    HLZ = "HLZ"   # Extra Wide Flange Beams
    # UB = "UB"   # Universal Beams (also in UK)

    #  Columns 
    HD = "HD"     # Wide Flange Columns
    # UB = "UB"   # Universal Columns (also in UK)      

    #  Bearing Piles 
    HP = "HP"     # Wide Flange Bearing Piles
    # UBP = "UBP" # Universal Bearing Piles (also in UK)

    #  Channels 
    UPE = "UPE"   # Parallel Flange Channels (EU)
    UPN = "UPN"   # Tapered Flange Channels
    # PFC = "PFC" # Parallel Flange Channels (UK) (also in UK)

    #  Angles 
    # L_EQUAL = "L_EQUAL"             # Equal Angles (also in UK)
    # L_UNEQUAL = "L_UNEQUAL"         # Unequal Angles (also in UK)
    # L_EQUAL_B2B = "L_EQUAL_B2B"     # Back to Back Equal Angles (also in UK)
    # L_UNEQUAL_B2B = "L_UNEQUAL_B2B" # Back to Back Unequal Angles (also in UK)    

    #  Flats 
    Sigma = "Sigma"     # SIGMA # TODO: review with ArcelorMittal database; for effective properties
    Zed = "Zed"         # Zed-butted Sections # TODO: review with ArcelorMittal database; for effective properties

    # --- 🇺🇸 US ---
    # TODO: Add info here... from AISC Steel Construction Manual v16
    #  Beams 
    W = "W" # Wide Flange Beams
    S = "S" # Standard Beams
    M = "M" # Miscellaneous Beams
    # HP = "HP" # Bearing Piles # also in EU # TODO: resolve this with EU vs US

    #  Channels 
    C = "C"  # Standard Channels
    MC = "MC" # Miscellaneous Channels
    C2C = "C2C" # Back-to-Back Channels # TODO: propagate C2C throughout the codebase
    MC2C = "MC2C" # Back-to-Back Miscellaneous Channels # TODO: propagate MC2C throughout the codebase

    #  Angles 
    L = "L"   # Standard Angles
    L2L = "L2L" # Back-to-Back Angles

    #  Structural Tees 
    WT = "WT" # cut from W shapes
    ST = "ST" # cut from S shapes
    MT = "MT" # cut from M shapes

    #  Hollow sections 
    HSS = "HSS" # Hollow Structural Sections

    #  Pipes 
    PIPE = "PIPE" # Pipes


@dataclass
class BaseSection(ABC):
    """Abstract base class for all steel sections"""

    designation: str # TODO: find other properties e.g mass/weight present in all sections
    # section_type: SectionType # TODO: implement section_type as Enum in all sections

    def __str__(self) -> str:
        return self.designation
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(designation={self.designation})"
    
    @classmethod # A classmetho
    @abstractmethod
    def get_section_type(cls) -> SectionType:
        """Return the section type as a `SectionType` enum"""
        # TODO: implement...
        pass

    @classmethod
    def from_dictionary(cls, data: dict[str, Any]) -> BaseSection:
        """Create a section instance from a dictionary"""
        return cls(**data)

    @abstractmethod
    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        # TODO: implement...
        pass


if __name__ == "__main__":
    
    logger.info("🐬")