"""Generic factory system to create section objects in `steelsnakes`."""

from __future__ import annotations
from typing import Any, Optional, Type
import logging
import difflib

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.exceptions import SectionNotFoundError, SectionTypeNotRegisteredError

# -
logger: logging.Logger = logging.getLogger(__name__)

class SectionFactory:
    """Simplified steel section factory for all regions.
    
    Uses direct dictionary mapping instead of complex registration patterns.
    Region-specific factories can inherit and provide their own section mappings.
    """
    # -
    def __init__(self, database: SectionDatabase, section_classes: Optional[dict[SectionType, Type[BaseSection]]] = None) -> None:
        """Initialize the factory with a section database and optional class mappings.
        
        Args:
            database: SectionDatabase instance for data access
            section_classes: Optional dictionary mapping section types to classes
        """
        self.database: SectionDatabase = database
        self._section_classes: dict[SectionType, Type[BaseSection]] = section_classes or {}
        
        # Auto-register default classes if none provided
        if not self._section_classes:
            self._load_default_classes()

    def _load_default_classes(self) -> None:
        """Load default section classes based on region.
        
        This method attempts to import and map section classes automatically
        but gracefully handles missing imports.
        """
        region = self.database.region
        
        try:
            # 
            if region == "UK":
                self._load_UK_classes()
            elif region == "EU":
                self._load_EU_classes()
            elif region == "US":
                self._load_US_classes()
            elif region == "AU":
                self._load_AU_classes()
            elif region == "NZ":
                self._load_NZ_classes()
            else:
                logger.warning(f"No default classes defined for region: {region}")
                
        except ImportError as e:
            logger.warning(f"Could not import all section classes for {region}: {e}")

    # --- 🇬🇧 UK
    def _load_UK_classes(self) -> None:
        """Load UK section classes."""
        try:
            # Universal sections
            from steelsnakes.UK.sections.universal import UniversalBeam, UniversalColumn, UniversalBearingPile
            self._section_classes.update({
                SectionType.UB: UniversalBeam,
                SectionType.UC: UniversalColumn,
                SectionType.UBP: UniversalBearingPile,
            })
            
            # Channel sections 
            from steelsnakes.UK.sections.channels import ParallelFlangeChannel
            self._section_classes[SectionType.PFC] = ParallelFlangeChannel
            
            # Angle sections
            from steelsnakes.UK.sections.angles import EqualAngle, UnequalAngle, EqualAngleBackToBack, UnequalAngleBackToBack
            self._section_classes.update({
                SectionType.L_EQUAL: EqualAngle,
                SectionType.L_UNEQUAL: UnequalAngle,
                SectionType.L_EQUAL_B2B: EqualAngleBackToBack,
                SectionType.L_UNEQUAL_B2B: UnequalAngleBackToBack,
            })
            
            # Hot Finished Hollow sections
            from steelsnakes.UK.sections.hf_hollow import (
                HotFinishedCircularHollowSection, HotFinishedSquareHollowSection,
                HotFinishedRectangularHollowSection, HotFinishedEllipticalHollowSection
            )
            self._section_classes.update({
                SectionType.HFCHS: HotFinishedCircularHollowSection,
                SectionType.HFSHS: HotFinishedSquareHollowSection,
                SectionType.HFRHS: HotFinishedRectangularHollowSection,
                SectionType.HFEHS: HotFinishedEllipticalHollowSection,
            })
            
            # Cold Formed Hollow sections
            from steelsnakes.UK.sections.cf_hollow import (
                ColdFormedCircularHollowSection, ColdFormedSquareHollowSection,
                ColdFormedRectangularHollowSection
            )
            self._section_classes.update({
                SectionType.CFCHS: ColdFormedCircularHollowSection,
                SectionType.CFSHS: ColdFormedSquareHollowSection,
                SectionType.CFRHS: ColdFormedRectangularHollowSection,
            })
            
        except ImportError as e:
            logger.warning(f"Some UK section classes not available: {e}")

    # --- 🇪🇺 EU
    def _load_EU_classes(self) -> None:
        """Load EU section classes."""
        try:
            # Beams
            from steelsnakes.EU.sections.beams import Beam, ParallelFlangeBeam, WideFlangeBeam, ExtraWideFlangeBeam, UniversalBeam
            self._section_classes[SectionType.UB] = UniversalBeam # loaded in UK in also
            self._section_classes.update({
                SectionType.IPE: ParallelFlangeBeam,
                SectionType.HE: WideFlangeBeam, 
                SectionType.HL: ExtraWideFlangeBeam, # TODO: handle HL/HLZ differentiator, since file-name factory system expects HL.json and HLZ.json
                SectionType.HLZ: ExtraWideFlangeBeam,
            })
            # Columns
            from steelsnakes.EU.sections.columns import Column, WideFlangeColumn, UniversalColumn
            self._section_classes[SectionType.UC] = UniversalColumn # loaded in UK also
            self._section_classes[SectionType.HD] = WideFlangeColumn
            
            # Bearing Piles
            from steelsnakes.EU.sections.piles import BearingPile, WideFlangeBearingPile, UniversalBearingPile
            self._section_classes[SectionType.UBP] = UniversalBearingPile # loaded in UK also
            self._section_classes[SectionType.HP] = WideFlangeBearingPile
            
            # Channels
            from steelsnakes.EU.sections.channels import ParallelFlangeChannel, TaperedFlangeChannel
            self._section_classes[SectionType.PFC] = ParallelFlangeChannel # loaded in UK also
            self._section_classes[SectionType.UPE] = ParallelFlangeChannel
            self._section_classes[SectionType.UPN] = TaperedFlangeChannel
            
            # Angles
            from steelsnakes.EU.sections.angles import EqualAngle, UnequalAngle, EqualAngleBackToBack, UnequalAngleBackToBack
            self._section_classes[SectionType.L_EQUAL] = EqualAngle
            self._section_classes[SectionType.L_UNEQUAL] = UnequalAngle
            self._section_classes[SectionType.L_EQUAL_B2B] = EqualAngleBackToBack
            self._section_classes[SectionType.L_UNEQUAL_B2B] = UnequalAngleBackToBack
            
            # Flats
            from steelsnakes.EU.sections.flats import Sigma, Zed
            self._section_classes[SectionType.Sigma] = Sigma
            self._section_classes[SectionType.Zed] = Zed
            
        except ImportError as e:
            logger.warning(f"Some EU section classes not available: {e}")

    # --- 🇺🇸 US
    def _load_US_classes(self) -> None:
        """Load US section classes."""
        try:
            # Beams
            from steelsnakes.US.sections.beams import WideFlangeBeam, StandardBeam, MiscellaneousBeam
            self._section_classes.update({
                SectionType.W: WideFlangeBeam,
                SectionType.S: StandardBeam,
                SectionType.M: MiscellaneousBeam,
            })
            # Channels
            from steelsnakes.US.sections.channels import StandardChannel, MiscellaneousChannel
            self._section_classes.update({
                SectionType.C: StandardChannel,
                SectionType.MC: MiscellaneousChannel,
            })
            # Angles
            from steelsnakes.US.sections.angles import (
                EqualAngle,
                UnequalAngle,
                BackToBackEqualAngle,
                LongLegBackToBackUnequalAngle,
                ShortLegBackToBackUnequalAngle,
            )
            self._section_classes.update({
                SectionType.L_EQUAL: EqualAngle,
                SectionType.L_UNEQUAL: UnequalAngle,
                SectionType.L2L_EQUAL: BackToBackEqualAngle,
                SectionType.L2L_LLBB: LongLegBackToBackUnequalAngle,
                SectionType.L2L_SLBB: ShortLegBackToBackUnequalAngle,
            })
            # Channels
            from steelsnakes.US.sections.channels import (
                StandardChannel,
                MiscellaneousChannel,
                # DoubleStandardChannel,
                # DoubleMiscellaneousChannel
            )
            self._section_classes.update({
                SectionType.C: StandardChannel,
                SectionType.MC: MiscellaneousChannel,
            })
            # Hollow sections
            from steelsnakes.US.sections.hollow import (
                RectangularHSS,
                SquareHSS,
                RoundHSS,
            )
            self._section_classes.update({
                SectionType.HSS_RCT: RectangularHSS,
                SectionType.HSS_SQR: SquareHSS,
                SectionType.HSS_RND: RoundHSS,
            })
            # Bearing Piles
            from steelsnakes.US.sections.piles import BearingPile
            self._section_classes[SectionType.HP] = BearingPile
            # Pipes
            from steelsnakes.US.sections.pipes import Pipe
            self._section_classes[SectionType.PIPE] = Pipe
            # Tees
            from steelsnakes.US.sections.tees import (
                StandardTee,
                MiscellaneousTee,
                WideFlangeTee,
            )
            self._section_classes.update({
                SectionType.ST: StandardTee,
                SectionType.MT: MiscellaneousTee,
                SectionType.WT: WideFlangeTee,
            })

        except ImportError as e:
            logger.warning(f"Some US section classes not available: {e}")

    def _load_AU_classes(self) -> None:
        """Load AU section classes."""
        try:
            # AU section imports would go here
            # This is a placeholder for AU section class loading
            pass
        except ImportError as e:
            logger.warning(f"Some AU section classes not available: {e}")

    def _load_NZ_classes(self) -> None:
        """Load NZ section classes."""
        try:
            # NZ section imports would go here
            # This is a placeholder for NZ section class loading
            pass
        except ImportError as e:
            logger.warning(f"Some NZ section classes not available: {e}")

    def register_section_class(self, section_type: SectionType, section_class: Type[BaseSection]) -> None:
        """Register a section class for a specific type.
        
        Args:
            section_type: The section type to register
            section_class: The class to use for this section type
        """
        self._section_classes[section_type] = section_class

    def get_registered_types(self) -> list[SectionType]:
        """Get list of currently registered section types."""
        return list(self._section_classes.keys())

    # 🌟 - Create section
    def create_section(self, designation: str, section_type: Optional[SectionType] = None) -> BaseSection:
        """Create a section instance given its designation and optional type.
        
        Args:
            designation: Section designation (e.g., "457x191x67", "IPE200")
            section_type: Optional section type. If not provided, will search all types
            
        Returns:
            BaseSection instance
            
        Raises:
            SectionNotFoundError: If section designation not found
            SectionTypeNotRegisteredError: If section type has no registered class
        """
        
        if section_type:
            # Use specified type
            section_data: Optional[dict[str, Any]] = self.database.get_section_data(
                designation=designation, section_type=section_type
            )
            if not section_data:
                # Get suggestions for better error message
                similar_sections = self.database.get_similar_sections(designation, section_type, n=5)
                available: list[str] = self.database.list_sections(section_type=section_type)
                
                # Check if designation exists under different type
                cross_type_note = ""
                cross_result = self.database.find_section(designation=designation)
                if cross_result is not None:
                    found_type, _ = cross_result
                    if found_type != section_type:
                        cross_type_note = f"\nNote: '{designation}' exists as type '{found_type.value}'."
                
                error_msg = f"Section '{designation}' of type '{section_type.value}' not found"
                if similar_sections:
                    # For a specific type, suggest up to top 5 close matches
                    suggestions = "', '".join(similar_sections[:5])
                    error_msg += f".\nSimilar sections: '{suggestions}'"
                else:
                    error_msg += f". Available sections: {len(available)} total"
                if cross_type_note:
                    error_msg += cross_type_note

                raise SectionNotFoundError(error_msg)
        
        else:
            # Search across all types
            result = self.database.find_section(designation=designation)
            if not result:
                similar_sections = self.database.get_similar_sections(designation)
                available_types: list[SectionType] = self.database.get_available_section_types()
                
                error_msg = f"Section '{designation}' not found in any type"
                if similar_sections:
                    suggestions = "', '".join(similar_sections)
                    error_msg += f".\nSimilar sections: '{suggestions}'"
                else:
                    error_msg += f". Available types: {[t.value for t in available_types]}"

                raise SectionNotFoundError(error_msg)
         
            section_type, section_data = result

        # Get the section class
        section_class: Optional[Type[BaseSection]] = self._section_classes.get(section_type)
        if not section_class:
            available_types = [t.value for t in self._section_classes.keys()] # type: ignore[reportAssignmentType] 
            # FIXME: handle section class SectionType vs str properly
            raise SectionTypeNotRegisteredError(
                f"No registered class for section type '{section_type.value}'. "
                f"Available types: {available_types}"
            )

        # Create and return instance
        # Remove metadata from data as it's not part of the dataclass
        clean_data: dict[str, Any] = {k: v for k, v in section_data.items() if not k.startswith('_')}
        
        # Add designation if not present
        if 'designation' not in clean_data:
            clean_data['designation'] = designation
            
        return section_class(**clean_data)


# Convenience functions for creating region-specific factories
def get_UK_factory(data_directory: Optional[Any] = None, use_sqlite: bool = False) -> SectionFactory:
    """Create a factory configured for UK sections."""
    database = SectionDatabase(data_directory, region="UK", use_sqlite=use_sqlite)
    return SectionFactory(database)


def get_EU_factory(data_directory: Optional[Any] = None, use_sqlite: bool = False) -> SectionFactory:
    """Create a factory configured for EU sections."""
    database = SectionDatabase(data_directory, region="EU", use_sqlite=use_sqlite)
    return SectionFactory(database)


def get_US_factory(data_directory: Optional[Any] = None, use_sqlite: bool = False) -> SectionFactory:
    """Create a factory configured for US sections."""
    database = SectionDatabase(data_directory, region="US", use_sqlite=use_sqlite)
    return SectionFactory(database)


# def get_AU_factory(data_directory: Optional[Any] = None, use_sqlite: bool = False) -> SectionFactory:
#     """Create a factory configured for AU sections."""
#     database = SectionDatabase(data_directory, region="AU", use_sqlite=use_sqlite)
#     return SectionFactory(database)


# def get_NZ_factory(data_directory: Optional[Any] = None, use_sqlite: bool = False) -> SectionFactory:
#     """Create a factory configured for NZ sections."""
#     database = SectionDatabase(data_directory, region="NZ", use_sqlite=use_sqlite)
#     return SectionFactory(database)

if __name__ == "__main__":
    logger.info("🐬")