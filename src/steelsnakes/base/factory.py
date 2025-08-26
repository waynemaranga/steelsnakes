"""Generic factory system to create section objects in `steelsnakes`."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, Tuple
import logging
import importlib
import traceback

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase

# -
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
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
        self._section_mappings: dict[SectionType, Tuple[str, str]] = {}
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

    def _get_section_class(self, section_type: SectionType) -> Type[BaseSection]:
        """Get section class, using lazy loading if needed."""
        # Check if already loaded
        if section_type in self._section_classes:
            return self._section_classes[section_type]
        
        # Try lazy loading if mapping exists
        if section_type in self._section_mappings:
            module_path, class_name = self._section_mappings[section_type]
            try:
                module = importlib.import_module(module_path)
                section_class = getattr(module, class_name)
                self._section_classes[section_type] = section_class
                return section_class
            except (ImportError, AttributeError) as e:
                # Log full traceback for debugging
                logger.error(f"Failed to import {class_name} from {module_path}: {e}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                raise ValueError(f"Failed to load section class for type '{section_type.value}': {e}") from e
        
        raise ValueError(f"No registered class for section type '{section_type.value}'. Available types: {[t.value for t in self._section_classes.keys()]}")

    # 🌟 - Create section
    def create_section(self, designation: str, section_type: Optional[SectionType] = None) -> BaseSection:
        """Create a section instance given its designation and optional type."""

        if section_type:
            # Use specified type
            section_data: Optional[dict[str, Any]] = self.database.get_section_data(designation=designation, section_type=section_type)
            if not section_data:
                available: list[str] = self.database.list_sections(section_type=section_type)
                raise ValueError(f"Section '{designation}' of type '{section_type.value}' not found. Available sections: {len(available)}") # TODO: paginate if too many
                # TODO: compare raise vs log warning + return None
        
        else:
            # -
            result = self.database.find_section(designation=designation)
            if not result:
                available_types: list[SectionType] = self.database.get_available_section_types()
                raise ValueError(f"Section '{designation}' not found in any type. Available types: {[t.value for t in available_types]}")
         
            section_type, section_data = result

        # Get the section class using lazy loading
        section_class: Type[BaseSection] = self._get_section_class(section_type)

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