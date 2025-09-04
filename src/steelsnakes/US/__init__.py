"""
US Steel Sections Module.
"""

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.database import USSectionDatabase, get_US_database
from steelsnakes.US.factory import USSectionFactory, get_US_factory
from steelsnakes.US.checks import Classification, classify_compression, classify_flexure

# -- Beams --
from steelsnakes.US.beams import (
    Beam,
    StandardBeam,
    MiscellaneousBeam,
    WideFlangeBeam,
)

# -- Channels --
from steelsnakes.US.channels import (
    Channel,
    StandardChannel,
    MiscellaneousChannel,
    DoubleStandardChannel,
    DoubleMiscellaneousChannel,
)

# -- Angles --
from steelsnakes.US.angles import (
    Angle,
    EqualAngle,
    UnequalAngle,
    DoubleAngle,
    BackToBackEqualAngle,
    LongLegBackToBackUnequalAngle,
    ShortLegBackToBackUnequalAngle,
)

# -- Hollow Structural Sections --
from steelsnakes.US.hollow import (
    HollowStructuralSection,
    RectangularHSS,
    SquareHSS,
    RoundHSS,
)

# -- Piles --
from steelsnakes.US.piles import BearingPile

__all__ = [
    "BaseSection",
    "SectionType",
    "USSectionDatabase",
    "get_US_database",
    "USSectionFactory",
    "get_US_factory",
    "Classification",
    "classify_compression",
    "classify_flexure",
]