"""
UK Steel Sections Module.

This module provides access to UK/European steel sections conforming to BS EN standards.
All section data is based on UK steel section tables and specifications.
"""

# Import the base classes and infrastructure
from .Base import (
    BaseSection,
    SectionType,
    SectionDatabase,
    SectionFactory,
    get_database,
    get_factory,
)

# Import Universal sections
from .Universal import (
    UniversalSection,
    UniversalBeam,
    UniversalColumn,
    UniversalBearingPile,
    UB,
    UC,
    UBP,
)

# Import Channel sections
from .Channel import (
    ParallelFlangeChannel,
    PFC,
)

# Import Angle sections
from .Angle import (
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
from .ColdFormedHollow import (
    ColdFormedCircularHollowSection,
    ColdFormedSquareHollowSection,
    ColdFormedRectangularHollowSection,
    CFCHS,
    CFSHS,
    CFRHS,
)

# Import Hot Finished Hollow sections
from .HotFinishedHollow import (
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
from .PreloadedBolt import (
    PreloadedBolt88,
    PreloadedBolt109,
    BOLT_PRE_88,
    BOLT_PRE_109,
)

# Import Weld specifications
from .Weld import (
    WeldSpecification,
    WELD,
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
    "WELD",
]
