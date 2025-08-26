"""UK-specific factory implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging
import traceback

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import SectionType
from steelsnakes.UK.database import UKSectionDatabase, get_uk_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
logger: logging.Logger = logging.getLogger(__name__)

class UKSectionFactory(SectionFactory):
    """UK-specific steel section factory.
    Automatically registers all UK section classes and provides 
    convenient creation methods for UK steel sections.
    """

    def __init__(self, database: Optional[UKSectionDatabase] = None) -> None:
        """Initialize UK factory with UK database."""
        if database is None:
            database = get_uk_database()
        super().__init__(database)

    def _register_default_classes(self) -> None:
        """Register mappings from section types to their classes for lazy loading."""
        # Register mappings from section types to module paths and class names
        self._section_mappings = {
            # Universal sections
            SectionType.UB: ('steelsnakes.UK.universal', 'UniversalBeam'),
            SectionType.UC: ('steelsnakes.UK.universal', 'UniversalColumn'),
            SectionType.UBP: ('steelsnakes.UK.universal', 'UniversalBearingPile'),
            
            # Channel sections 
            SectionType.PFC: ('steelsnakes.UK.channels', 'ParallelFlangeChannel'),
            
            # Angle sections
            SectionType.L_EQUAL: ('steelsnakes.UK.angles', 'EqualAngle'),
            SectionType.L_UNEQUAL: ('steelsnakes.UK.angles', 'UnequalAngle'),
            SectionType.L_EQUAL_B2B: ('steelsnakes.UK.angles', 'EqualAngleBackToBack'),
            SectionType.L_UNEQUAL_B2B: ('steelsnakes.UK.angles', 'UnequalAngleBackToBack'),
            
            # Hot Finished Hollow sections
            SectionType.HFCHS: ('steelsnakes.UK.hf_hollow', 'HotFinishedCircularHollowSection'),
            SectionType.HFSHS: ('steelsnakes.UK.hf_hollow', 'HotFinishedSquareHollowSection'),
            SectionType.HFRHS: ('steelsnakes.UK.hf_hollow', 'HotFinishedRectangularHollowSection'),
            SectionType.HFEHS: ('steelsnakes.UK.hf_hollow', 'HotFinishedEllipticalHollowSection'),
            
            # Cold Formed Hollow sections
            SectionType.CFCHS: ('steelsnakes.UK.cf_hollow', 'ColdFormedCircularHollowSection'),
            SectionType.CFSHS: ('steelsnakes.UK.cf_hollow', 'ColdFormedSquareHollowSection'),
            SectionType.CFRHS: ('steelsnakes.UK.cf_hollow', 'ColdFormedRectangularHollowSection'),
            
            # Connection components
            SectionType.WELDS: ('steelsnakes.UK.welds', 'WeldSpecification'),
            SectionType.BOLT_PRE_88: ('steelsnakes.UK.preloaded_bolts', 'PreloadedBolt88'),
            SectionType.BOLT_PRE_109: ('steelsnakes.UK.preloaded_bolts', 'PreloadedBolt109'),
        }
        
        # For backward compatibility and testing, we can optionally try to preload some classes
        # but gracefully handle any import failures with better error logging
        try:
            # Try to load a few common section types to verify modules are available
            # This is optional and mainly for compatibility with existing tests
            from steelsnakes.UK.universal import UniversalBeam
            self.register_section_class(UniversalBeam)
        except ImportError as e:
            # Log full traceback for debugging import issues
            logger.warning(f"Could not preload UniversalBeam class: {e}")
            logger.debug(f"Full traceback:\n{traceback.format_exc()}")


# Global instance for convenience
_global_uk_factory: Optional[UKSectionFactory] = None


def get_uk_factory(data_directory: Optional[Path] = None) -> UKSectionFactory:
    """Get or create global UK factory instance."""
    global _global_uk_factory
    if _global_uk_factory is None or data_directory is not None:
        database = get_uk_database(data_directory) if data_directory else None
        _global_uk_factory = UKSectionFactory(database)
    return _global_uk_factory

if __name__ == "__main__":
    factory = get_uk_factory()
    logger.info(factory.create_section("457x191x67"))