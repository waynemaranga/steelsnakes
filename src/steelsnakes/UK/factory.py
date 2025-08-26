"""UK-specific factory implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging
import threading

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
        """Register all UK section classes automatically."""
        # Import and register all UK section classes
        try:
            # Universal sections
            from steelsnakes.UK.universal import (
                UniversalBeam, UniversalColumn, UniversalBearingPile
            )
            self.register_section_class(UniversalBeam)
            self.register_section_class(UniversalColumn)
            self.register_section_class(UniversalBearingPile)
            
            # Channel sections 
            from steelsnakes.UK.channels import ParallelFlangeChannel
            self.register_section_class(ParallelFlangeChannel)
            
            # Angle sections
            from steelsnakes.UK.angles import (
                EqualAngle, UnequalAngle, EqualAngleBackToBack, UnequalAngleBackToBack
            )
            self.register_section_class(EqualAngle)
            self.register_section_class(UnequalAngle)
            self.register_section_class(EqualAngleBackToBack)
            self.register_section_class(UnequalAngleBackToBack)
            
            # Hot Finished Hollow sections
            from steelsnakes.UK.hf_hollow import (
                HotFinishedCircularHollowSection,
                HotFinishedSquareHollowSection,
                HotFinishedRectangularHollowSection,
                HotFinishedEllipticalHollowSection
            )
            self.register_section_class(HotFinishedCircularHollowSection)
            self.register_section_class(HotFinishedSquareHollowSection)
            self.register_section_class(HotFinishedRectangularHollowSection)
            self.register_section_class(HotFinishedEllipticalHollowSection)
            
            # Cold Formed Hollow sections
            from steelsnakes.UK.cf_hollow import (
                ColdFormedCircularHollowSection,
                ColdFormedSquareHollowSection,
                ColdFormedRectangularHollowSection
            )
            self.register_section_class(ColdFormedCircularHollowSection)
            self.register_section_class(ColdFormedSquareHollowSection)
            self.register_section_class(ColdFormedRectangularHollowSection)
            
            # Connection components
            from steelsnakes.UK.welds import WeldSpecification
            from steelsnakes.UK.preloaded_bolts import PreloadedBolt88, PreloadedBolt109
            self.register_section_class(WeldSpecification)
            self.register_section_class(PreloadedBolt88)
            self.register_section_class(PreloadedBolt109)
            
        except ImportError as e:
            # Some section modules may not exist yet - gracefully handle
            logger.warning(f"Warning: Could not import some UK section classes: {e}")


# Global instance for convenience
_global_uk_factory: Optional[UKSectionFactory] = None
_factory_lock = threading.Lock()


def get_uk_factory(data_directory: Optional[Path] = None) -> UKSectionFactory:
    """Get or create global UK factory instance.
    
    Args:
        data_directory: Optional path to data directory. If provided, returns a new
                       factory instance without updating the global singleton.
    
    Returns:
        UKSectionFactory instance - either the global singleton or a new instance.
    """
    global _global_uk_factory
    
    # If data_directory is provided, always return a new instance
    if data_directory is not None:
        database = get_uk_database(data_directory)
        return UKSectionFactory(database)
    
    # For global singleton, use double-checked locking pattern
    if _global_uk_factory is None:
        with _factory_lock:
            if _global_uk_factory is None:
                _global_uk_factory = UKSectionFactory()
    
    return _global_uk_factory

if __name__ == "__main__":
    factory = get_uk_factory()
    logger.info(factory.create_section("457x191x67"))