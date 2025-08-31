"""
UK Steel Sections Module.
"""

from typing import Optional

# Import base infrastructure
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.database import UKSectionDatabase, get_uk_database
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory

# Import Universal sections
from steelsnakes.UK.universal import (
    UniversalSection,
    UniversalBeam,
    UniversalColumn,
    UniversalBearingPile,
    UB,
    UC,
    UBP,
)

# Import Channel sections
from steelsnakes.UK.channels import (
    ParallelFlangeChannel,
    PFC,
)

# Import Angle sections
from steelsnakes.UK.angles import (
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
from steelsnakes.UK.cf_hollow import (
    ColdFormedCircularHollowSection,
    ColdFormedSquareHollowSection,
    ColdFormedRectangularHollowSection,
    CFCHS,
    CFSHS,
    CFRHS,
)

# Import Hot Finished Hollow sections
from steelsnakes.UK.hf_hollow import (
    HotFinishedCircularHollowSection,
    HotFinishedSquareHollowSection,
    HotFinishedRectangularHollowSection,
    HotFinishedEllipticalHollowSection,
    HFCHS,
    HFSHS,
    HFRHS,
    HFEHS,
)


__all__ = [
    # Base classes and infrastructure
    "BaseSection",
    "SectionType",
    "UKSectionDatabase",
    "UKSectionFactory",
    "get_uk_database",
    "get_UK_factory",
    
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
]


# Auto-register all section classes on import
def _register_all_uk_sections():
    """Register all UK section classes with the global factory."""
    try:
        factory = get_UK_factory()
        # Factory constructor automatically calls _register_default_classes()
        # which registers all available section classes
    except Exception as e:
        print(f"Warning: Could not auto-register UK section classes: {e}")


# Initialize on import
_register_all_uk_sections()


# Convenience function for creating sections without specifying type
def create_section(designation: str, section_type: Optional[SectionType] = None):
    """
    Create a section instance by designation, with optional type.
    
    Args:
        designation: Section designation (e.g., "457x191x67")
        section_type: Optional section type. If None, auto-detects.
    
    Returns:
        Section instance of appropriate type
    """
    factory = get_UK_factory()
    return factory.create_section(designation, section_type)


# Add create_section to exports
__all__.append("create_section")
