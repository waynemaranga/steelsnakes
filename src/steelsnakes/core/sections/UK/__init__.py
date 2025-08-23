"""
UK Steel Sections Module.

This module provides access to UK/European steel sections conforming to BS EN standards.
All section data is based on UK steel section tables and specifications.
"""

# Import the base classes and infrastructure
from .base import (
    BaseSection,
    SectionType,
    SectionDatabase,
    SectionFactory,
    get_database,
    get_factory,
)

# Import Universal sections
from .universal import (
    UniversalSection,
    UniversalBeam,
    UniversalColumn,
    UniversalBearingPile,
    UB,
    UC,
    UBP,
)

# Import Channel sections
from .channels import (
    ParallelFlangeChannel,
    PFC,
)

# Import Angle sections
from .angles import (
    EqualAngle,
    UnequalAngle,
    EqualAngleBackToBack,
    UnequalAngleBackToBack,
    L_EQUAL,
    L_UNEQUAL,
    L_EQUAL_B2B,
    L_UNEQUAL_B2B,
)

# Import Cold Formed Hollow sections
from .cf_hollow import (
    ColdFormedCircularHollowSection,
    ColdFormedSquareHollowSection,
    ColdFormedRectangularHollowSection,
    CFCHS,
    CFSHS,
    CFRHS,
)

# Import Hot Finished Hollow sections
from .hf_hollow import (
    HotFinishedCircularHollowSection,
    HotFinishedSquareHollowSection,
    HotFinishedRectangularHollowSection,
    HotFinishedEllipticalHollowSection,
    HFCHS,
    HFSHS,
    HFRHS,
    HFEHS,
)

# Import Preloaded Bolt specifications
from .preloaded_bolts import (
    PreloadedBolt88,
    PreloadedBolt109,
    BOLT_PRE_88,
    BOLT_PRE_109,
)

# Import Weld specifications
from .welds import (
    WeldSpecification,
    Weld,
)

__all__ = [
    # Base classes
    "BaseSection",
    "SectionType", 
    "SectionDatabase",
    "SectionFactory",
    "get_database",
    "get_factory",
    
    # Universal sections
    "UniversalSection",
    "UniversalBeam",
    "UniversalColumn", 
    "UniversalBearingPile",
    "UB",
    "UC", 
    "UBP",
    
    # Channel sections
    "ParallelFlangeChannel",
    "PFC",
    
    # Angle sections
    "EqualAngle",
    "UnequalAngle", 
    "EqualAngleBackToBack",
    "UnequalAngleBackToBack",
    "L_EQUAL",
    "L_UNEQUAL",
    "L_EQUAL_B2B", 
    "L_UNEQUAL_B2B",
    
    # Cold Formed Hollow sections
    "ColdFormedCircularHollowSection",
    "ColdFormedSquareHollowSection",
    "ColdFormedRectangularHollowSection",
    "CFCHS",
    "CFSHS",
    "CFRHS",
    
    # Hot Finished Hollow sections
    "HotFinishedCircularHollowSection",
    "HotFinishedSquareHollowSection", 
    "HotFinishedRectangularHollowSection",
    "HotFinishedEllipticalHollowSection",
    "HFCHS",
    "HFSHS",
    "HFRHS",
    "HFEHS",
    
    # Preloaded Bolt specifications
    "PreloadedBolt88",
    "PreloadedBolt109",
    "BOLT_PRE_88",
    "BOLT_PRE_109",
    
    # Weld specifications
    "WeldSpecification",
    "Weld",
]
