"""EU-specific factory implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import SectionType
from steelsnakes.EU.database import EUSectionDatabase, get_EU_database

logger: logging.Logger = logging.getLogger(__name__)

class EUSectionFactory(SectionFactory):
    """EU-specific steel section factory.
    Automatically registers all EU section classes and provides 
    convenient creation methods for EU steel sections.
    """

    def __init__(self, database: Optional[EUSectionDatabase] = None) -> None:
        """Initialize EU factory with EU database."""
        if database is None:
            database = get_EU_database()
        super().__init__(database)

    def _register_default_classes(self) -> None:
        """Register all EU section classes automatically."""
        # Import and register all EU section classes
        try:
            # --- Beams ---
            from steelsnakes.EU.beams import (
                ParallelFlangeBeam,
                WideFlangeBeam,
                ExtraWideFlangeBeam,
                UniversalBeam,
            )
            self.register_section_class(ParallelFlangeBeam)
            self.register_section_class(WideFlangeBeam)
            self.register_section_class(ExtraWideFlangeBeam)
            self.register_section_class(UniversalBeam)

            # --- Columns ---
            from steelsnakes.EU.columns import (
                WideFlangeColumn,
                UniversalColumn,
            )
            self.register_section_class(WideFlangeColumn)
            self.register_section_class(UniversalColumn)

            # --- Bearing Piles ---
            from steelsnakes.EU.piles import (
                WideFlangeBearingPile,
                UniversalBearingPile,
            )
            self.register_section_class(WideFlangeBearingPile)
            self.register_section_class(UniversalBearingPile)

            # --- Channels ---
            from steelsnakes.EU.channels import (
                ParallelFlangeChannel, # TODO: compare properties of UPE and PFC
                TaperedFlangeChannel,

            )
            self.register_section_class(ParallelFlangeChannel)
            self.register_section_class(TaperedFlangeChannel)

            # --- Angles ---
            from steelsnakes.EU.angles import (
                EqualAngle,
                UnequalAngle,
                EqualAngleBackToBack,
                UnequalAngleBackToBack,
            )
            self.register_section_class(EqualAngle)
            self.register_section_class(UnequalAngle)
            self.register_section_class(EqualAngleBackToBack)
            self.register_section_class(UnequalAngleBackToBack)

            # --- Flats ---
            from steelsnakes.EU.flats import (
                Sigma,
                Zed,
            )
            self.register_section_class(Sigma)
            self.register_section_class(Zed)

        except ImportError as e:
            # Some section modules may not exist yet - gracefully handle
            logger.warning(f"Warning: Could not import some EU section classes: {e}")


# Global instance for convenience
_global_EU_factory: Optional[EUSectionFactory] = None


def get_EU_factory(data_directory: Optional[Path] = None) -> EUSectionFactory:
    """Get or create global EU factory instance."""
    global _global_EU_factory
    if _global_EU_factory is None or data_directory is not None:
        database: EUSectionDatabase | None = get_EU_database(data_directory) if data_directory else None
        _global_EU_factory = EUSectionFactory(database)
    return _global_EU_factory

if __name__ == "__main__":
    from steelsnakes.base.exceptions import SectionNotFoundError
    factory: EUSectionFactory = get_EU_factory()
    # Trigger fuzzy matching with a close-but-incorrect designation
    # try:
    #     test_1 = factory.create_section("IPE-750x220", SectionType.IPE)
    #     print(test_1.get_properties())
    # except Exception as e: # Working :D
    #     # logger.error(f"{e} -- {type(e)}") # prints out SectionNotFoundError, so, accurate :D
    #     logger.error(f"{e}") 

    # print("---------------------------------")
    
    # try:
    #     test_2 = factory.create_section("HD-1000x584", SectionType.HD)
    #     print(test_2.get_properties())
    # except Exception as e: # Working :D
    #     # logger.error(f"{e} -- {type(e)}") # prints out SectionNotFoundError, so, accurate :D
    #     logger.error(f"{e}") 
    
    # print("---------------------------------")
    
    # try:
    #     test_3 = factory.create_section("356x406x990", SectionType.UC)
    #     print(test_3.get_properties())
    # except Exception as e: # Working :D
    #     # logger.error(f"{e} -- {type(e)}") # prints out SectionNotFoundError, so, accurate :D
    #     logger.error(f"{e}") 
    try:
        test_4 = factory.create_section("200x100x10", SectionType.L_UNEQUAL)
        print(test_4.get_properties())
    except Exception as e: # Working :D
        # logger.error(f"{e} -- {type(e)}") # prints out SectionNotFoundError, so, accurate :D
        logger.error(f"{e}") 