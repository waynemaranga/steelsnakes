from __future__ import annotations
from typing import Optional, Union, Any, Literal, Callable
from enum import Enum
import logging
from abc import ABC, abstractmethod
import math
from pydantic import BaseModel, Field

logger: logging.Logger = logging.getLogger(__name__)

class DesignCode(Enum):
    """Global enumeration of all design codes available in steelsnakes."""
    EN_1993 = "EN_1993" # Eurocode 3, Part 1-1: General rules and rules for buildings
    BS_EN_1993_UKNA = "BS_EN_1993_UKNA" # Eurocode 3 with UK National Annex
    BS_5950_1 = "BS_5950_1" # British Standard: Loads for buildings, Part 1: General load cases
    AISC_360 = "AISC_360" # American Institute of Steel Construction: Specification for Structural Steel Buildings
    IS_800 = "IS_800" # Indian Standard: General Construction in Steel
    AS_4100 = "AS_4100" # Australian Standard: Steel Structures
    # TODO: Add more codes...

class LimitState(Enum):
    """Global enumeration of all limit states available in steelsnakes."""
    # EU/UK
    ULS = "ULS" # Ultimate Limit State # TODO: expound, like US
    SLS = "SLS" # Serviceability Limit State # TODO: expound, like US

    # US. Strictly LRFD
    TENSILE_YIELDING = "TENSILE_YIELDING"
    TENSILE_RUPTURE = "TENSILE_RUPTURE"
    FLEXURAL_BUCKLING = "FLEXURAL_BUCKLING"
    TORSIONAL_BUCKLING = "TORSIONAL_BUCKLING"
    TORSIONAL_FLEXURAL_BUCKLING = "TORSIONAL_FLEXURAL_BUCKLING"
    LATERAL_TORSIONAL_BUCKLING = "LATERAL_TORSIONAL_BUCKLING"
    PLASTIC_MOMENT_YIELDING = "PLASTIC_MOMENT_YIELDING"
    SHEAR_BUCKLING = "SHEAR_BUCKLING"
    COMPRESSION_FLANGE_LOCAL_BUCKLING = "COMPRESSION_FLANGE_LOCAL_BUCKLING"
    COMPRESSION_FLANGE_YIELDING = "COMPRESSION_FLANGE_YIELDING"
    TENSION_FLANGE_YIELDING = "TENSION_FLANGE_YIELDING"
    FLANGE_LOCAL_BUCKLING = "FLANGE_LOCAL_BUCKLING" # FIXME: Since only in metadata, just simplify the limit states, maybe specify for which flange in metadata?
    WEB_LOCAL_BUCKLING = "WEB_LOCAL_BUCKLING" # TODO: edit while editing module

class SectionClass(Enum):
    # TODO: [TRIVIAL] try, using classification methods/functions, to classify a section in one code and check in other codes. Also, do global classification of all sections in all codes into a one database and find conflicts e.g class 2 in one but class 1 in another.
    """Global enumeration of all section classes available in `steelsnakes`.
    
    References:
        - EN 1993-1-1:2005 Clause 5.5.2(1)
        - AISC 360-22 Section B4.1
        - IS 800:2007 Clause 3.7.2
    """
    # --- EU/UK: EN 1993-1-1:2005 Clause 5.5.2(1)
    CLASS_1 = "CLASS_1"     # Adequate rotation for plastic analysis without resistance reduction
    CLASS_2 = "CLASS_2"     # Can develop plastic moment resistance but are limited by local buckling
    CLASS_3 = "CLASS_3"     # Max. elastic stress... can reach yield stress but local buckling prevents plastic moment resistance
    CLASS_4 = "CLASS_4"     # Local buckling occurs before yielding in one or more parts of the x-section

    # --- US: AISC 360-22 Section B4.1
    # ... for axial compression
    NONSLENDER_ELEMENT = "NONSLENDER_ELEMENT"
    SLENDER_ELEMENT = "SLENDER_ELEMENT"
    # ... for bending
    COMPACT = "COMPACT"
    NONCOMPACT = "NONCOMPACT"
    # SLENDER_ELEMENT = "SLENDER_ELEMENT" # defined in axial compression

    # ---IS 800:2007 Clause 3.7.2 
    # Same as EU/UK; adding alt. definitions # FIXME: Remove or resolve.
    # PLASTIC = "CLASS_1"     # High rotation capacity
    # COMPACT = "CLASS_2"     # Limited rotation capacity
    # SEMI_COMPACT = "CLASS_3"# Local buckling prevents attainment of full plastic moment
    # SLENDER = "CLASS_4"     # Local buckling prevents attainment of yield moment


class Classification(BaseModel):
    """Simple classification result."""
    section_class: SectionClass
    metadata: dict[str, Any] = Field(default_factory=dict)
    reference: Optional["Reference"] = None

class Scalar(BaseModel):
    """Simple scalar value with optional units."""
    value: float
    units: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class BaseCheck(ABC):
    """Abstract base class for all checks."""
    pass




class UtilisationCheck(BaseModel):
    """Simple utilisation check result."""
    utilisation: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    adequacy: Literal["OK", "FAILS"] = "OK"
    reference: Optional["Reference"] = None


class Reference(BaseModel):
    code: DesignCode # or string?
    clause: Optional[str] = None
    # section: Optional[str] = None # for US # FIXME: may be problematic; retain clause
    equation: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None


# Simple formula helpers for common calculations
def compute_utilisation(demand: float, capacity: float) -> float:
    """Compute utilisation ratio, handling zero/negative capacity."""
    if capacity is None or capacity <= 0.0:
        return math.inf
    return demand / capacity

