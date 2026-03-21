"""
US-Metric Steel Sections Module.
"""

# Import base infrastructure
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US_Metric.database import USMetricSectionDatabase, get_US_Metric_database
from steelsnakes.US_Metric.factory import USMetricSectionFactory, get_US_Metric_factory

# -- Beams --
from steelsnakes.US_Metric.sections.beams import (
    Beam,
    StandardBeam,
    MiscellaneousBeam,
    WideFlangeBeam,
)

# -- Channels --
from steelsnakes.US_Metric.sections.channels import (
    Channel,
    StandardChannel,
    MiscellaneousChannel,
    DoubleStandardChannel,
    DoubleMiscellaneousChannel,
)

# -- Angles --
from steelsnakes.US_Metric.sections.angles import (
    Angle,
    EqualAngle,
    UnequalAngle,
    DoubleAngle,
    BackToBackEqualAngle,
    LongLegBackToBackUnequalAngle,
    ShortLegBackToBackUnequalAngle,
)

# -- Hollow Structural Sections --
from steelsnakes.US_Metric.sections.hollow import (
    HollowStructuralSection,
    RectangularHSS,
    SquareHSS,
    RoundHSS,
)

# -- Piles --
from steelsnakes.US_Metric.sections.piles import BearingPile

__all__ = [
    "BaseSection",
    "SectionType",
    "USMetricSectionDatabase",
    "get_US_Metric_database",
    "USMetricSectionFactory",
    "get_US_Metric_factory",
    # Beams
    "Beam",
    "StandardBeam",
    "MiscellaneousBeam",
    "WideFlangeBeam",
    # Channels
    "Channel",
    "StandardChannel",
    "MiscellaneousChannel",
    "DoubleStandardChannel",
    "DoubleMiscellaneousChannel",
    # Angles
    "Angle",
    "EqualAngle",
    "UnequalAngle",
    "DoubleAngle",
    "BackToBackEqualAngle",
    "LongLegBackToBackUnequalAngle",
    "ShortLegBackToBackUnequalAngle",
    # Hollow Structural Sections
    "HollowStructuralSection",
    "RectangularHSS",
    "SquareHSS",
    "RoundHSS",
    # Piles
    "BearingPile",
]