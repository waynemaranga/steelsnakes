"""Generic factory system to create section objects in `steelsnakes`."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional, Type
import logging
import difflib

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.exceptions import SectionNotFoundError, SectionTypeNotRegisteredError

# -
logger: logging.Logger = logging.getLogger(__name__)

# -
class SectionFactory(ABC):
    """Abstract base class for section factories.
    Region-specific factories inherit from this and implement:
    _register_default_classes() to register all section classes for this region
    create_section() to create a section instance given its designation and optional type
    """

    # -
    def __init__(self, database: SectionDatabase) -> None:
        """Initialize the factory with a section database."""
        self.database: SectionDatabase = database
        self._section_classes: dict[SectionType, Type[BaseSection]] = {}
        self._register_default_classes()

    # -
    @abstractmethod
    def _register_default_classes(self) -> None:
        """Register default section classes for this country.
        Override in country-specific factories to auto-register classes."""
        pass

    # -
    def register_section_class(self, section_class: Type[BaseSection]) -> None:
        """Register a section class for automatic creation."""
        section_type: SectionType = section_class.get_section_type()
        self._section_classes[section_type] = section_class

    def _get_similar_sections(self, designation: str, section_type: Optional[SectionType] = None, n: int = 3) -> list[str]:
        """Get similar section designations using fuzzy matching.
        
        Args:
            designation: The section designation to find similar matches for
            section_type: Optional section type to limit search to
            n: Maximum number of suggestions to return
        Returns:
            List of similar section designations
        """
        all_sections = []
        
        if section_type:
            # Search within specific type
            sections = self.database.list_sections(section_type)
            all_sections = sections
        else:
            # Search across all types
            for st in self.database.get_available_section_types():
                sections = self.database.list_sections(st)
                all_sections.extend(sections)
        
        # Use difflib to find close matches
        close_matches = difflib.get_close_matches(
            designation, 
            all_sections, 
            n=n, 
            cutoff=0.6  # Stricter cutoff to avoid noisy suggestions
        )
        
        return close_matches

    # 🌟 - Create section
    def create_section(self, designation: str, section_type: Optional[SectionType] = None) -> BaseSection:
        """Create a section instance given its designation and optional type."""

        if section_type:
            # Use specified type
            section_data: Optional[dict[str, Any]] = self.database.get_section_data(designation=designation, section_type=section_type)
            if not section_data:
                available: list[str] = self.database.list_sections(section_type=section_type)
                similar_sections = self._get_similar_sections(designation, section_type, n=5)
                # Check if the designation exists under a different section type
                cross_type_note = ""
                try:
                    cross_result = self.database.find_section(designation=designation)
                except Exception:
                    cross_result = None
                if cross_result is not None:
                    found_type, found_data = cross_result
                    if found_type != section_type:
                        cross_type_note = f"\nNote: designation exists under type '{found_type.value}'."
                
                error_msg = f"Section '{designation}' of type '{section_type.value}' not found"
                if similar_sections:
                    # For a specific type, suggest up to top 5 close matches
                    suggestions = "', '".join(similar_sections[:5])
                    error_msg += f".\nTry: '{suggestions}'?"
                else:
                    error_msg += f". Available sections: {len(available)}"
                if cross_type_note:
                    error_msg += cross_type_note

                raise SectionNotFoundError(error_msg) # TODO: paginate if too many

                # TODO: compare raise vs log warning + return None
        
        else:
            # -
            result = self.database.find_section(designation=designation)
            if not result:
                available_types: list[SectionType] = self.database.get_available_section_types()
                similar_sections = self._get_similar_sections(designation)
                
                error_msg = f"Section '{designation}' not found in any type"
                if similar_sections:
                    suggestions = "', '".join(similar_sections)
                    error_msg += f".\nTry: '{suggestions}'?"
                else:
                    error_msg += f". Available types: {[t.value for t in available_types]}"

                raise SectionNotFoundError(error_msg)

         
            section_type, section_data = result

        # Get the section class
        section_class: Optional[Type[BaseSection]] = self._section_classes.get(section_type)
        if not section_class:
            raise SectionTypeNotRegisteredError(f"No registered class for section type '{section_type.value}'. Available types: {[t.value for t in self._section_classes.keys()]}")
            # TODO: compare raise vs log warning + return None
            # FIXME: fix error message: doesn't show list of available types

        # Create and return instance
        # Remove metadata from data as it's not part of the dataclass
        clean_data: dict[str, Any] = {k: v for k, v in section_data.items() if not k.startswith('_')}
        
        # Add designation if not present (e.g., for WELDS)
        if 'designation' not in clean_data:
            clean_data['designation'] = designation
            
        return section_class(**clean_data)


if __name__ == "__main__":
    # TODO: add tests here
    logger.info("🐬")
