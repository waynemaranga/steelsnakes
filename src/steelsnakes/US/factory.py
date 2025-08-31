"""US-specific factory implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import SectionType
from steelsnakes.US.database import USSectionDatabase, get_US_database

logger: logging.Logger = logging.getLogger(__name__)

class USSectionFactory(SectionFactory):
    """US-specific steel section factory.
    Automatically registers all US section classes and provides 
    convenient creation methods for US steel sections.
    """

    def __init__(self, database: Optional[USSectionDatabase] = None) -> None:
        """Initialize US factory with US database."""
        if database is None:
            database = get_US_database()
        super().__init__(database)

    def _register_default_classes(self) -> None:
        """Register all US section classes automatically."""
        # Import and register all US section classes
        try:
            # --- Beams ---
            from steelsnakes.US.beams import (
                StandardBeam,
                MiscellaneousBeam,
                WideFlangeBeam,
            )
            self.register_section_class(StandardBeam)
            self.register_section_class(MiscellaneousBeam)
            self.register_section_class(WideFlangeBeam)

            # --- Channels ---
            from steelsnakes.US.channels import (
                StandardChannel,
                MiscellaneousChannel,
                # DoubleStandardChannel,
                # DoubleMiscellaneousChannel,
            )
            self.register_section_class(StandardChannel)
            self.register_section_class(MiscellaneousChannel)
            # self.register_section_class(DoubleStandardChannel)
            # self.register_section_class(DoubleMiscellaneousChannel)

            #  --- Angles ---
            from steelsnakes.US.angles import (
                EqualAngle,
                UnequalAngle,
                BackToBackEqualAngle,
                LongLegBackToBackUnequalAngle,
                ShortLegBackToBackUnequalAngle,
            )
            self.register_section_class(EqualAngle)
            self.register_section_class(UnequalAngle)
            self.register_section_class(BackToBackEqualAngle)
            self.register_section_class(LongLegBackToBackUnequalAngle)
            self.register_section_class(ShortLegBackToBackUnequalAngle)

            # --- Piles ---
            from steelsnakes.US.piles import BearingPile
            self.register_section_class(BearingPile)

            # --- Hollow Sections ---
            from steelsnakes.US.hollow import (
                RectangularHSS,
                SquareHSS,
                RoundHSS,
            )
            self.register_section_class(RectangularHSS)
            self.register_section_class(SquareHSS)
            self.register_section_class(RoundHSS)

            # --- Tees ---
            from steelsnakes.US.tees import (
                StandardTee,
                MiscellaneousTee,
                WideFlangeTee,
            )
            self.register_section_class(StandardTee)
            self.register_section_class(MiscellaneousTee)
            self.register_section_class(WideFlangeTee)

            # --- Pipes ---
            from steelsnakes.US.pipes import Pipe
            self.register_section_class(Pipe)

        except ImportError as e:
            # Some section modules may not exist yet - gracefully handle
            logger.warning(f"Warning: Could not import some US section classes: {e}")


# Global instance for convenience
_global_US_factory: Optional[USSectionFactory] = None


def get_US_factory(data_directory: Optional[Path] = None) -> USSectionFactory:
    """Get or create global US factory instance."""
    global _global_US_factory
    if _global_US_factory is None or data_directory is not None:
        database: USSectionDatabase | None = get_US_database(data_directory) if data_directory else None
        _global_US_factory = USSectionFactory(database)
    return _global_US_factory

if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    factory: USSectionFactory = get_US_factory()
    # Trigger fuzzy matching with a close-but-incorrect designation
    try:
        section = factory.create_section("W36x350", SectionType.W)
    except SectionNotFoundError as e:
        logger.error(e)
    else:
        logger.info(section.get_properties())