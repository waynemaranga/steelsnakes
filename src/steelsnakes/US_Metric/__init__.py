"""
US-Metric Steel Sections Module.
"""

# Import base infrastructure
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US_Metric.database import USMetricSectionDatabase, get_US_Metric_database
from steelsnakes.US_Metric.factory import USMetricSectionFactory, get_US_Metric_factory

# -- Beams --
from steelsnakes.US_Metric.beams import (
    Beam,
    StandardBeam,
    MiscellaneousBeam,
    WideFlangeBeam,
)

# -- Channels --
from steelsnakes.US_Metric.channels import (
    Channel,
    StandardChannel,
    MiscellaneousChannel,
    DoubleStandardChannel,
    DoubleMiscellaneousChannel,
)

# -- Angles --
from steelsnakes.US_Metric.angles import (
    Angle,
    EqualAngle,
    UnequalAngle,
    DoubleAngle,
    BackToBackEqualAngle,
    LongLegBackToBackUnequalAngle,
    ShortLegBackToBackUnequalAngle,
)

# -- Hollow Structural Sections --
from steelsnakes.US_Metric.hollow import (
    HollowStructuralSection,
    RectangularHSS,
    SquareHSS,
    RoundHSS,
)

# -- Piles --
from steelsnakes.US_Metric.piles import BearingPile

# __all__ = []