"""Base section for all steel sections"""

# Instance, class and static methods: https://realpython.com/instance-class-and-static-methods-demystified/
# Instance v Static v Class v Abstract Methods: https://medium.com/nerd-for-tech/python-instance-vs-static-vs-class-vs-abstract-methods-1952a5c77d9d

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger: logging.Logger = logging.getLogger(__name__)

class SectionType(Enum):
    """Global enumeration of all section types available in steelsnakes.
    Currently supports 🇬🇧 UK, 🇪🇺 EU, 🇺🇸 US.
    Developing 🇮🇳 IS.
    Considering 🇦🇺 AU / 🇳🇿 NZ, 🇯🇵 JP, 🇲🇽 MX, 🇿🇦 SA, 🇨🇳 CN, 🇨🇦 CA, 🇰🇷 KR.
    """
    
    # --- 🇬🇧 UK ---
    # TODO: Add info here... Provided by Steel Construction Institute (SCI) via Blue Book
    # Universal Sections
    UB = "UB"   # Universal Beam
    UC = "UC"   # Universal Column
    UBP = "UBP" # Universal Beam with Parallel Flange

    # Channels
    PFC = "PFC" # Parallel Flange Channel

    # Angles
    L_EQUAL = "L_EQUAL"             # Equal Angle; also in EU & US
    L_UNEQUAL = "L_UNEQUAL"         # Unequal Angle; also in EU & US
    L_EQUAL_B2B = "L_EQUAL_B2B"     # Equal Angle Back-to-Back; also in EU, NOT in US
    L_UNEQUAL_B2B = "L_UNEQUAL_B2B" # Unequal Angle Back-to-Back; also in EU, NOT in US
    
    # Hollow sections (Hot Finished)
    HFCHS = "HFCHS"     # Hot Finished Circular Hollow Section
    HFRHS = "HFRHS"     # Hot Finished Rectangular Hollow Section
    HFSHS = "HFSHS"     # Hot Finished Square Hollow Section
    HFEHS = "HFEHS"     # Hot Finished Elliptical Hollow Section
    
    # Hollow sections (Cold Formed)
    CFCHS = "CFCHS"     # Cold Formed Circular Hollow Section
    CFRHS = "CFRHS"     # Cold Formed Rectangular Hollow Section
    CFSHS = "CFSHS"     # Cold Formed Square Hollow Section
    
    # Removed connection components (bolts and welds)

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
    # L_EQUAL = "L_EQUAL"             # Equal Angles (also in UK & US)
    # L_UNEQUAL = "L_UNEQUAL"         # Unequal Angles (also in UK & US)
    # L_EQUAL_B2B = "L_EQUAL_B2B"     # Back to Back Equal Angles (also in UK, NOT in US)
    # L_UNEQUAL_B2B = "L_UNEQUAL_B2B" # Back to Back Unequal Angles (also in UK, NOT in US)    

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
    # L_EQUAL = "L_EQUAL"             # Equal Angles (also in UK & EU)
    # L_UNEQUAL = "L_UNEQUAL"         # Unequal Angles (also in UK & EU)
    L2L_EQUAL = "L2L_EQUAL"           # Back-to-Back Equal Angles
    L2L_LLBB = "L2L_LLBB"             # Back-to-Back Unequal Angles, Long Leg Back-to-Back
    L2L_SLBB = "L2L_SLBB"             # Back-to-

    #  Structural Tees 
    WT = "WT" # cut from W shapes
    ST = "ST" # cut from S shapes
    MT = "MT" # cut from M shapes

    #  Hollow sections 
    # HSS = "HSS" # Hollow Structural Sections
    HSS_RCT = "HSS_RCT" # Rectangular Hollow Structural Sections
    HSS_SQR = "HSS_SQR" # Square Hollow Structural Sections
    HSS_RND = "HSS_RND" # Round Hollow Structural Sections

    #  Pipes 
    PIPE = "PIPE" # Pipes

    # --- 🇮🇳 IS ---
    # TODO: Add info here... from IS 808:2021
    # To reduce reduncancy, the IS for Indian Standard is omitted from section type naming.
    # so JB is ISJB, see IS 808:2021 clause 5.1
    # To prevent conflicts with US/Other regions, variations are used.
    # Beams
    JB = "JB"       # Junior Beam - ISJB
    LWB = "LWB"     # Light-weight Beam - ISLB
    MWB = "MWB"     # Medium-weight Beam - ISMB
    WFB = "WFB"     # Wide-flange Beam - ISWB
    NPB = "NPB"     # Narrow Parallel-flange Beam - ISNPB
    WPB = "WPB"     # Wide Parallel-flange Beam - ISWPB

    # Columns/Heavy-weight Beams
    SC = "SC" # Column Section - ISSC
    HB = "HB" # Heavy-weight Beam - ISHB # classified as such in IS 808:2021 clause 5.1

    # Channels
    JC = "JC" # Junior Channel - ISJC
    LWC = "LWC" # Light-weight Channel - ISLC
    MWC = "MWC" # Medium-weight Channel - ISMC
    MPC = "MPC" # Medium-weight Parallel-flange Channel - ISMPC

    # Angles
    # In IS 808:2021, angles are classified as "Equal Angles" and "Unequal Angles", but both
    # are designated ISA. Here, EA is Equal Angle and UA is Unequal Angle.
    EA = "EA" # Equal Angle - ISA
    UA = "UA" # Unequal Angle - also ISA
    # TODO: find IS back-to-back angles

    # Bearing Piles
    PBP = "PBP" # Parallel-flange Bearing Pile - ISPBP

    # --- 🇦🇺 AU / 🇳🇿 NZ ---
    # TODO: Add info here... from AS/NZS 3679.1:2010

    # --- 🇯🇵 JP ---
    # TODO: Add info here... from JIS G 3192:2014

    # --- 🇲🇽 MX ---
    # TODO: Add info here... from NMX standards

    # --- 🇿🇦 SA ---
    # TODO: Add info here... from SANS standards

    # --- 🇨🇳 CN ---
    # TODO: Add info here... from GB standards

    # --- 🇨🇦 CA ---
    # TODO: Add info here... from CSA standards

    # --- 🇰🇷 KR ---
    # TODO: Add info here... from KS standards (K004en.pdf available)


@dataclass
class BaseSection(ABC):
    """Abstract base class for all steel sections"""

    designation: str # TODO: find other properties e.g mass/weight present in all sections
    # section_type: SectionType # TODO: implement section_type as Enum in all sections

    def __str__(self) -> str:
        return self.designation
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(designation={self.designation})"
    
    # - 🌟 Get section type
    @classmethod # A classmethod is a method that is bound to the class and not the instance of the class
    @abstractmethod # An abstractmethod is a method that is declared, but contains no implementation; subclasses must override it
    def get_section_type(cls) -> SectionType:
        """Return the section type as a `SectionType` enum"""
        # TODO: implement...
        pass
    
    # - 🌟 Create section from dictionary
    @classmethod
    def from_dictionary(cls, data: dict[str, Any]) -> BaseSection:
        """Create a section instance from a dictionary"""
        return cls(**data)

    # - 🌟 Get section properties
    @abstractmethod
    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        # TODO: implement...
        pass

    def list_properties(self):
        """Print all section properties to the console."""
        properties = self.get_properties()
        properties_list = []
        for prop, value in properties.items():
            # return list of properties/keys only
            properties_list.append(prop)

        return properties_list

if __name__ == "__main__":
    
    logger.info("🐬")