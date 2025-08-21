"""
Base classes and generic database system for steel sections.

This module provides the foundation for all section types with a unified
database and factory system that can automatically handle any section type.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union


class SectionType(str, Enum):
    """Enumeration of all supported section types."""
    
    # Universal sections
    UB = "UB"           # Universal Beam
    UC = "UC"           # Universal Column  
    UBP = "UBP"         # Universal Bearing Pile
    
    # Channel sections
    PFC = "PFC"         # Parallel Flange Channel
    
    # Angle sections
    L_EQUAL = "L_EQUAL"             # Equal Angle
    L_UNEQUAL = "L_UNEQUAL"         # Unequal Angle
    L_EQUAL_B2B = "L_EQUAL_B2B"     # Equal Angle Back-to-Back
    L_UNEQUAL_B2B = "L_UNEQUAL_B2B" # Unequal Angle Back-to-Back
    
    # Hollow sections - Hot Finished
    HFCHS = "HFCHS"     # Hot Finished Circular Hollow Section
    HFRHS = "HFRHS"     # Hot Finished Rectangular Hollow Section
    HFSHS = "HFSHS"     # Hot Finished Square Hollow Section
    HFEHS = "HFEHS"     # Hot Finished Elliptical Hollow Section
    
    # Hollow sections - Cold Formed
    CFCHS = "CFCHS"     # Cold Formed Circular Hollow Section
    CFRHS = "CFRHS"     # Cold Formed Rectangular Hollow Section
    CFSHS = "CFSHS"     # Cold Formed Square Hollow Section
    
    # Connection components
    WELDS = "WELDS"                 # Weld details
    BOLT_PRE_88 = "BOLT_PRE_88"     # Pre-loaded bolts (8.8 grade)
    BOLT_PRE_109 = "BOLT_PRE_109"   # Pre-loaded bolts (10.9 grade)


@dataclass
class BaseSection(ABC):
    """
    Abstract base class for all steel sections.
    
    All section types inherit from this and add their specific properties.
    """
    
    # Core identification - all sections must have designation
    designation: str
    
    def __str__(self) -> str:
        return self.designation
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(designation='{self.designation}')"
    
    @classmethod
    @abstractmethod
    def get_section_type(cls) -> SectionType:
        """Return the section type enum for this class."""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseSection':
        """Create section instance from dictionary data."""
        return cls(**data)


class SectionDatabase:
    """
    Generic database that automatically loads all available section types.
    
    This replaces the old approach with a unified system that discovers
    and loads section data automatically.
    """
    
    def __init__(self, data_directory: Optional[Path] = None):
        """
        Initialize database with automatic data directory discovery.
        
        Args:
            data_directory: Optional path to sections directory. 
                          If None, auto-discovers based on file location.
        """
        self.data_directory = self._resolve_data_directory(data_directory)
        self._cache: Dict[SectionType, Dict[str, Dict[str, Any]]] = {}
        self._load_all_sections()
    
    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Find the data directory using multiple fallback strategies."""
        if data_directory is not None:
            return data_directory
            
        # Auto-discovery based on current file location
        current_file = Path(__file__).resolve()
        possible_paths = [
            # From UK sections module to data/sections/UK
            current_file.parent / "../../../data/sections/UK",
            current_file.parent.parent / "../../data/sections/UK",
            current_file.parent.parent.parent / "data/sections/UK",
            current_file.parent.parent.parent.parent / "data/sections/UK",
            # From project root
            Path.cwd() / "data/sections/UK",
            Path.cwd() / "src/steelsnakes/data/sections/UK",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
                
        # Fallback - will be handled gracefully in loading
        return current_file.parent / "../../data/sections/UK"
    
    def _load_all_sections(self) -> None:
        """
        Scan for and load all available section JSON files.
        
        This automatically discovers section types by looking for JSON files
        matching the SectionType enum values.
        """
        if not self.data_directory.exists():
            print(f"⚠️  Warning: Data directory not found: {self.data_directory}")
            return
        
        loaded_count = 0
        
        # Try to load each section type
        for section_type in SectionType:
            filename = f"{section_type.value}.json"
            file_path = self.data_directory / filename
            
            try:
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    # Add section_type to each section's data
                    for designation, section_data in data.items():
                        section_data["section_type"] = section_type
                    
                    self._cache[section_type] = data
                    print(f"✅ Loaded {len(data)} {section_type.value} sections")
                    loaded_count += 1
                else:
                    self._cache[section_type] = {}
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON error in {filename}: {e}")
                self._cache[section_type] = {}
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
                self._cache[section_type] = {}
        
        print(f"📊 Loaded {loaded_count} section types total")
    
    def get_section_data(self, section_type: SectionType, designation: str) -> Optional[Dict[str, Any]]:
        """Get section data for specific designation and type."""
        return self._cache.get(section_type, {}).get(designation)
    
    def list_sections(self, section_type: SectionType) -> list[str]:
        """List all available sections of given type."""
        return list(self._cache.get(section_type, {}).keys())
    
    def find_section(self, designation: str) -> Optional[tuple[SectionType, Dict[str, Any]]]:
        """Find a section by designation across all types."""
        for section_type in SectionType:
            data = self.get_section_data(section_type, designation)
            if data:
                return section_type, data
        return None
    
    def get_available_types(self) -> list[SectionType]:
        """Get list of section types that have data loaded."""
        return [section_type for section_type, data in self._cache.items() if data]
    
    def search_sections(
        self, 
        section_type: SectionType, 
        **criteria: Any
    ) -> list[tuple[str, Dict[str, Any]]]:
        """
        Search sections by property criteria with comparison operators.
        
        Args:
            section_type: Type of section to search
            **criteria: Property filters. Supports operators like:
                       mass_per_metre__gt=50 (greater than)
                       h__lt=400 (less than)
                       b__gte=200 (greater than or equal)
        
        Returns:
            List of (designation, section_data) tuples matching criteria
        """
        sections = self._cache.get(section_type, {})
        results = []
        
        for designation, data in sections.items():
            match = True
            
            for key, value in criteria.items():
                if "__" in key:
                    # Handle comparison operators
                    prop, operator = key.split("__", 1)
                    prop_value = data.get(prop)
                    
                    if prop_value is None:
                        match = False
                        break
                    
                    try:
                        if operator == "gt" and not (prop_value > value):
                            match = False
                        elif operator == "lt" and not (prop_value < value):
                            match = False
                        elif operator == "gte" and not (prop_value >= value):
                            match = False
                        elif operator == "lte" and not (prop_value <= value):
                            match = False
                        elif operator == "eq" and not (prop_value == value):
                            match = False
                        elif operator == "ne" and not (prop_value != value):
                            match = False
                        else:
                            # Unknown operator, skip this criteria
                            continue
                    except (TypeError, ValueError):
                        # Can't compare, skip this item
                        match = False
                        break
                else:
                    # Exact match
                    if data.get(key) != value:
                        match = False
                        break
            
            if match:
                results.append((designation, data))
        
        return results


class SectionFactory:
    """
    Factory for creating section instances with automatic type registration.
    
    This factory automatically manages section class registration and
    provides clean interfaces for section creation.
    """
    
    def __init__(self, database: SectionDatabase):
        """Initialize factory with database instance."""
        self.database = database
        self._section_classes: Dict[SectionType, Type[BaseSection]] = {}
    
    def register_section_class(self, section_class: Type[BaseSection]) -> None:
        """Register a section class for automatic creation."""
        section_type = section_class.get_section_type()
        self._section_classes[section_type] = section_class
        
    def create_section(
        self, 
        designation: str, 
        section_type: Optional[SectionType] = None
    ) -> BaseSection:
        """
        Create a section instance from database.
        
        Args:
            designation: Section designation (e.g., "457x191x67")
            section_type: Optional section type. If None, auto-detects.
        
        Returns:
            Section instance of appropriate type
            
        Raises:
            ValueError: If section not found or type not registered
        """
        if section_type:
            # Use specified type
            section_data = self.database.get_section_data(section_type, designation)
            if not section_data:
                available = self.database.list_sections(section_type)
                raise ValueError(
                    f"Section '{designation}' not found in {section_type.value} database. "
                    f"Available sections: {len(available)}"
                )
        else:
            # Auto-detect by searching all types
            result = self.database.find_section(designation)
            if not result:
                available_types = self.database.get_available_types()
                raise ValueError(
                    f"Section '{designation}' not found in any database. "
                    f"Available types: {[t.value for t in available_types]}"
                )
            section_type, section_data = result
        
        # Get section class
        section_class = self._section_classes.get(section_type)
        if not section_class:
            raise ValueError(
                f"No section class registered for type {section_type.value}. "
                f"Available: {list(self._section_classes.keys())}"
            )
        
        # Create and return instance
        # Remove section_type from data as it's not part of the dataclass
        clean_data = {k: v for k, v in section_data.items() if k != 'section_type'}
        
        # Add designation if not present (e.g., for WELDS)
        if 'designation' not in clean_data:
            clean_data['designation'] = designation
            
        return section_class(**clean_data)


# Global instances for convenience
_global_database: Optional[SectionDatabase] = None
_global_factory: Optional[SectionFactory] = None


def get_database(data_directory: Optional[Path] = None) -> SectionDatabase:
    """Get or create global database instance."""
    global _global_database
    if _global_database is None or data_directory is not None:
        _global_database = SectionDatabase(data_directory)
    return _global_database


def get_factory(data_directory: Optional[Path] = None) -> SectionFactory:
    """Get or create global factory instance."""
    global _global_factory, _global_database
    if _global_factory is None or data_directory is not None:
        db = get_database(data_directory)
        _global_factory = SectionFactory(db)
    return _global_factory