"""Generic database system for all regions in `steelsnakes`."""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from pathlib import Path
import json
import sqlite3
from typing import Any, Optional

from steelsnakes.base.sections import SectionType
from steelsnakes.base.sqlite3db import SQLiteJSONInterface

logger: logging.Logger = logging.getLogger(__name__)



class SectionDatabase(ABC):
    """Abstract base class for section databases. Region-specific databases inherit from this and:
    - call `super().__init__(data_directory)`
    - override `_resolve_data_directory()`
    - override `get_supported_types()`
    - override `_fuzzy_find_section()`
    """

    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False) -> None:
        """Initialize the database with the data directory.
        
        Args:
            data_directory: Path to data directory containing JSON files
            use_sqlite: If `True`, prefer SQLite database over JSON files (experimental)
        """
        self.data_directory: Path = self._resolve_data_directory(data_directory=data_directory)
        self.use_sqlite: bool = use_sqlite
        self._cache: dict[SectionType, dict[str, dict[str, Any]]] = {}
        self._sqlite_db_path: Optional[Path] = None
        self._load_sections()

    # ------- Abstract Methods -------
    # -
    @abstractmethod
    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Resolve the data directory path; unique to each region."""
        # Override in region-specific databases
        pass

    # -
    @abstractmethod
    def get_supported_types(self) -> list[SectionType]:
        """Return a tuple of supported section types for given region."""
        # Override in region-specific databases
        pass

    # -
    @abstractmethod
    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """Country-specific fuzzy section finding. Each country has different designation formats and needs
        custom logic for parsing and matching."""
        pass
 
    # ------- Standard Interface Methods -------
    # 🌟 - Loading sections from database
    def _load_sections(self) -> None:
        """Load all supported section types into the cache."""
        if not self.data_directory.is_dir(): # .is_dir() implies .exists()
            # raise FileNotFoundError(f"Data directory '{self.data_directory}' does not exist.") # TODO: compare raise vs log warning and return
            logger.warning(f"Data directory '{self.data_directory}' does not exist.")
            return

        loaded_count: int = 0

        for section_type in self.get_supported_types(): # .get_supported_types() is overridden in region-specific databases
            try:
                section_data = self._load_section_type(section_type)
                if section_data:
                    # Adding metadata for each section...
                    for designation, properties in section_data.items():
                        properties["_section_type"] = section_type.value

                    self._cache[section_type] = section_data
                    # logger.info(f"Loaded {len(section_data)} {section_type.value} sections") # TODO: consider silent logging for success
                    loaded_count += 1

                else:
                    self._cache[section_type] = {}

            except Exception as e:
                logger.error(f"Error loading {section_type.value} sections: {e}")
                self._cache[section_type] = {}

        # logger.info(f"Loaded {loaded_count} section types into cache.") # TODO: consider silent logging for success
    
    # -
    def _load_section_type(self, section_type: SectionType) -> Optional[dict[str, dict[str, Any]]]:
        """Load a specific section type. Can be overridden for custom loading; defaults to JSON"""
        
        # Load from JSON (primary method)
        json_path: Path = self.data_directory / f"{section_type.value}.json"
        
        if json_path.exists():
            with open(json_path, mode="r", encoding="utf-8") as filepath:
                return json.load(fp=filepath)
        
        # Try SQLite if enabled (experimental)
        if self.use_sqlite:
            sqlite_data = self._load_from_sqlite(section_type)
            if sqlite_data is not None:
                return sqlite_data
            
        # Try alternative formats if JSON not found
        return self._try_alternative_formats(section_type=section_type)

    # -
    # @abstractmethod # TODO: consider abstracting this
    def _try_alternative_formats(self, section_type: SectionType) -> Optional[dict[str, dict[str, Any]]]:
        """Try to load from alternative formats (SQLite, CSV, etc.). Override in regions."""
        # TODO: Implement alternative formats i.e SQLite, CSV, etc.
        return None
    
    # - 🌟 Get section data
    def get_section_data(self, designation: str, section_type: SectionType) -> Optional[dict[str, Any]]:
        """Retrieve section data by designation and type."""
        return self._cache.get(section_type, {}).get(designation)
    
    # -
    def list_sections(self, section_type: SectionType) -> list[str]:
        """List all section designations for a given type."""
        return list(self._cache.get(section_type, {}).keys())
    
    # 🌟 - Find section # TODO: redocument
    def find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """Find a section by designation across all types."""
        # Try exact match first...
        for section_type in self.get_supported_types():
            section_data: Optional[dict[str, Any]] = self.get_section_data(designation=designation, section_type=section_type)
            if section_data:
                return section_type, section_data
            
        # If not found, try fuzzy match (case-insensitive)
        return self._fuzzy_find_section(designation=designation)

    # -
    def get_available_section_types(self) -> list[SectionType]:
        """Return a list of section types that have data loaded."""
        return [
            section_type for section_type 
            in self.get_supported_types()
            if section_type in self._cache and self._cache[section_type]
            ]
    
    # 🌟 - Search sections from cache; is independent of database impl.
    def search_sections(
            self,
            section_type: SectionType,
            **criteria: Any
        ) -> list[tuple[str, dict[str, Any]]]:

        """Search sections by criteria with comparison operators."""
        sections: dict[str, dict[str, Any]] = self._cache.get(section_type, {})
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
                    
                    # Perform the comparison...
                    try:
                        if operator == "gt" and not (prop_value > value): # greater than
                            match = False
                        elif operator == "lt" and not (prop_value < value): # less than
                            match = False
                        elif operator == "gte" and not (prop_value >= value): # greater than or equal
                            match = False
                        elif operator == "lte" and not (prop_value <= value): # less than or equal
                            match = False
                        elif operator == "eq" and not (prop_value == value): # equal
                            match = False
                        elif operator == "ne" and not (prop_value != value): # not equal
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

    # ------- SQLite Methods -------
    # - 🪶 SQLite: Get database path
    def _get_sqlite_db_path(self) -> Path:
        """Get the SQLite database path for this region."""
        if self._sqlite_db_path is None:
            # Default to {data_directory}_sections.sqlite3
            db_name = f"{self.data_directory.name}_sections.sqlite3"
            self._sqlite_db_path = self.data_directory.parent / db_name
        return self._sqlite_db_path

    # - 🪶 SQLite: Ensure database exists
    def _ensure_sqlite_database(self) -> bool:
        """Ensure SQLite database exists, creating it from JSON files if needed."""
        sqlite_path = self._get_sqlite_db_path()
        
        if sqlite_path.exists():
            return True
            
        # Create SQLite database from JSON files
        try:
            logger.info(f"Creating SQLite database from JSON files at: {sqlite_path}")
            self._build_sqlite_from_json(sqlite_path, self.data_directory)
            return True
        except Exception as e:
            logger.error(f"Failed to create SQLite database: {e}")
            return False

    # - 🌟 | 🪶 SQLite: Load from SQLite
    def _load_from_sqlite(self, section_type: SectionType) -> Optional[dict[str, dict[str, Any]]]:
        """Load section data from SQLite database."""
        if not self._ensure_sqlite_database():
            return None
            
        sqlite_path = self._get_sqlite_db_path()
        
        try:
            with sqlite3.connect(sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Table name is the section type in uppercase
                table_name = section_type.value.upper()
                
                # Check if table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                if not cursor.fetchone():
                    return None
                
                # Load all sections from the table
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                sections = {}
                for row in rows:
                    # Parse the JSON data column which contains the full section data
                    section_data = json.loads(row['data'])
                    designation = row['designation']
                    sections[designation] = section_data
                    
                return sections
                
        except Exception as e:
            logger.error(f"Error loading {section_type.value} from SQLite: {e}")
            return None

    # - 🪶 SQLite: Build from JSON
    def _build_sqlite_from_json(self, db_path: Path, source_dir: Path) -> None:
        """Build SQLite database from JSON files using the SQLite JSON interface."""
        
        # Use the SQLite JSON interface to build the database
        interface = SQLiteJSONInterface(db_path)
        interface.convert_directory(source_dir)

    # - 🪶 SQLite: Build from JSON
    def build_sqlite_database(self, force_rebuild: bool = False) -> Path:
        """Manually build SQLite database from JSON files. Takes force_rebuild: If `True`,
        rebuild even if database exists. Returns: `Path` to the created SQLite database
        """
        sqlite_path = self._get_sqlite_db_path()
        
        if force_rebuild and sqlite_path.exists():
            sqlite_path.unlink()
            
        if not self._ensure_sqlite_database():
            raise RuntimeError(f"Failed to create SQLite database at {sqlite_path}")
            
        return sqlite_path



if __name__ == "__main__":    
    logger.info("🐬")