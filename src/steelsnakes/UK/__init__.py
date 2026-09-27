"""UK Steel Sections Module."""

from __future__ import annotations

from typing import Optional

# Import base infrastructure
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.database import UKSectionDatabase, get_UK_database
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory
from steelsnakes.UK.sections import angles, channels, cf_hollow, hf_hollow, universal
from steelsnakes.UK.sections.angles import (
    EqualAngle,
    EqualAngleBackToBack,
    L_EQUAL,
    L_EQUAL_B2B,
    L_UNEQUAL,
    L_UNEQUAL_B2B,
    UnequalAngle,
    UnequalAngleBackToBack,
)
from steelsnakes.UK.sections.cf_hollow import (
    CFCHS,
    CFRHS,
    CFSHS,
    ColdFormedCircularHollowSection,
    ColdFormedRectangularHollowSection,
    ColdFormedSquareHollowSection,
)
from steelsnakes.UK.sections.channels import PFC, ParallelFlangeChannel
from steelsnakes.UK.sections.hf_hollow import (
    HFCHS,
    HFEHS,
    HFRHS,
    HFSHS,
    HotFinishedCircularHollowSection,
    HotFinishedEllipticalHollowSection,
    HotFinishedRectangularHollowSection,
    HotFinishedSquareHollowSection,
)
from steelsnakes.UK.sections.universal import (
    UB,
    UBP,
    UC,
    UniversalBeam,
    UniversalBearingPile,
    UniversalColumn,
    UniversalSection,
)


def _register_all_uk_sections() -> None:
    """Register all UK section classes with the global factory."""
    try:
        get_UK_factory()
    except Exception as e:
        print(f"Warning: Could not auto-register UK section classes: {e}")


_register_all_uk_sections()


def create_section(designation: str, section_type: Optional[SectionType] = None):
    """Create a UK section instance by designation, with optional type."""
    factory = get_UK_factory()
    return factory.create_section(designation, section_type)


# Add create_section to exports
# __all__.append("create_section")
