"""Generic database system for all regions in `steelsnakes`."""

from __future__ import annotations
import logging
from pathlib import Path
import json
import difflib
from typing import Any, Optional

from steelsnakes.base.sections import SectionType

logger: logging.Logger = logging.getLogger(__name__)


class SectionDatabase:
    """Simplified steel section database for all regions.
    This concrete implementation handles data loading, caching, and searching
    for steel sections across different regions.
    """

    def __init__(self, data_directory: Optional[Path] = None, region: str = "EU", use_sqlite: bool = False) -> None:
        """Initialize the database with the data directory.
        
        Args:
            data_directory: Path to data directory containing JSON files
            region: Region code (EU, UK, US, etc.) for auto-discovery
            use_sqlite: If `True`, prefer SQLite database over JSON files (experimental)
        """
        self.region = region.upper()
        self.data_directory: Path = self._resolve_data_directory(data_directory, region)
        self.use_sqlite: bool = use_sqlite
        self._cache: dict[SectionType, dict[str, dict[str, Any]]] = {}
        self._supported_types: list[SectionType] = self._get_region_supported_types()
        self._load_sections()

    def _resolve_data_directory(self, data_directory: Optional[Path], region: str) -> Path:
        """Resolve the data directory path for the given region."""
        if data_directory is not None:
            return data_directory.resolve()
            
        # Auto-discovery based on region
        current_file: Path = Path(__file__).resolve()
        region_upper = region.upper()
        
        possible_paths: list[Path] = [          
            Path.cwd() / f"src/steelsnakes/{region_upper}/data/",  # from project root
            current_file.parent.parent / f"{region_upper}/data/",  # from package installation
            current_file.parent.parent.parent / f"data/{region_upper}/",  # from development environment
            current_file.parent.parent.parent / f"src/steelsnakes/{region_upper}/data/",  # from source directory
            current_file.parent.parent.parent.parent / f"data/{region_upper}/"  # from parent directory
        ]
        
        for path in possible_paths:
            resolved_path = path.resolve()
            if resolved_path.exists() and resolved_path.is_dir():
                return resolved_path
                
        # Fallback - create region-specific path
        return current_file.parent.parent / f"{region_upper}/data/"

    def _get_region_supported_types(self) -> list[SectionType]:
        """Get supported section types for the region."""
        # Define region-specific supported types
        region_types = {
            # TODO: double-check...
            "EU": [
                # Beams
                SectionType.IPE, SectionType.HE, SectionType.HL, SectionType.HLZ, SectionType.UB,
                # Angles
                SectionType.L_EQUAL, SectionType.L_UNEQUAL, SectionType.L_EQUAL_B2B, 
                SectionType.L_UNEQUAL_B2B, 
                # Channels
                SectionType.PFC, SectionType.UPN, SectionType.UPE, 
                # Flats
                SectionType.Sigma, SectionType.Zed, 
                # Columns
                SectionType.HD, SectionType.UC,
                # Bearing Piles
                SectionType.HP, SectionType.UBP,
                # Flats
                SectionType.Sigma, SectionType.Zed, 
            ],
            "UK": [
                # Universal
                SectionType.UB, SectionType.UC, SectionType.UBP,
                # Channels
                SectionType.PFC,
                # Angles
                SectionType.L_EQUAL, SectionType.L_UNEQUAL,
                SectionType.L_EQUAL_B2B, SectionType.L_UNEQUAL_B2B,
                # Hot-finished Hollow Sections
                SectionType.HFCHS, SectionType.HFRHS, SectionType.HFSHS, SectionType.HFEHS, 
                # Cold Formed Hollow Sections
                SectionType.CFCHS, SectionType.CFRHS, SectionType.CFSHS
            ],
            "US": [
                # Beams
                SectionType.W, SectionType.S, SectionType.M,
                # Bearing Piles
                SectionType.HP,
                # Channels
                SectionType.C, SectionType.MC,
                # Angles
                SectionType.L_EQUAL, SectionType.L_UNEQUAL,
                SectionType.L2L_EQUAL, SectionType.L2L_LLBB, SectionType.L2L_SLBB,
                # Hollow Sections
                SectionType.HSS_RCT, SectionType.HSS_RND, SectionType.HSS_SQR,
                SectionType.PIPE, SectionType.WT, SectionType.MT, SectionType.ST
            ],
            "IN": [
                # Beams
                SectionType.JB, SectionType.LWB, SectionType.MWB, SectionType.WFB, SectionType.NPB, SectionType.WPB,
                # Columns/Heavy-weight Beams
                SectionType.SC, SectionType.HWB,
                # Channels
                SectionType.JC, SectionType.LWC, SectionType.MWC, SectionType.MPC,
                # Angles
                SectionType.EA, SectionType.UA,
                # Bearing Piles
                SectionType.PBP,
            ],
        #     "AU": [
        #         SectionType.UB, SectionType.UC, SectionType.PFC, SectionType.EA
        #     ],
        #     "NZ": [
        #         SectionType.UB, SectionType.UC, SectionType.PFC, SectionType.EA
        #     ]
        #     "JP":[],
        #     "MX":[],
        #     "SA":[],
        #     "CN":[],
        #     "CA":[],
        #     "KR":[],
        }
        
        return region_types.get(self.region, [])

    # ------- Standard Interface Methods -------
    # 🌟 - Loading sections from database
    def _load_sections(self) -> None:
        """Load all supported section types into the cache."""
        if not self.data_directory.is_dir():
            logger.warning(f"Data directory '{self.data_directory}' does not exist.")
            return

        loaded_count: int = 0

        for section_type in self._supported_types:
            try:
                section_data = self._load_section_type(section_type)
                if section_data:
                    # Adding metadata for each section...
                    for designation, properties in section_data.items():
                        properties["_section_type"] = section_type.value
                        properties["_region"] = self.region

                    self._cache[section_type] = section_data
                    loaded_count += 1
                else:
                    self._cache[section_type] = {}

            except Exception as e:
                logger.error(f"Error loading {section_type.value} sections: {e}")
                self._cache[section_type] = {}

        logger.info(f"Loaded {loaded_count} section types for region {self.region}")
    
    def _load_section_type(self, section_type: SectionType) -> Optional[dict[str, dict[str, Any]]]:
        """Load a specific section type from JSON files."""
        json_path: Path = self.data_directory / f"{section_type.value}.json"
        
        if json_path.exists():
            try:
                with open(json_path, mode="r", encoding="utf-8") as filepath:
                    return json.load(fp=filepath)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Error parsing JSON file {json_path}: {e}")
                return None
        
        # Try SQLite if enabled (experimental; keeping  existing SQLite support)
        if self.use_sqlite:
            sqlite_data = self._load_from_sqlite(section_type)
            if sqlite_data is not None:
                return sqlite_data
            
        return None

    def _load_from_sqlite(self, section_type: SectionType) -> Optional[dict[str, dict[str, Any]]]:
        """Load section data from SQLite database (if SQLite support is enabled)."""
        # Simplified implementation - can be extended later if needed
        if not hasattr(self, '_sqlite_db_path') or self._sqlite_db_path is None:  # type: ignore[reportAttributeAccess]
            # FIXME: handle sqlite_db_path properly
            return None
            
        try:
            import sqlite3
            with sqlite3.connect(self._sqlite_db_path) as conn: # type: ignore[reportAttributeAccess]
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
                    import json
                    section_data = json.loads(row['data'])
                    designation = row['designation']
                    sections[designation] = section_data
                    
                return sections
                
        except Exception as e:
            logger.error(f"Error loading {section_type.value} from SQLite: {e}")
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
        """Find a section by designation across all types with robust fuzzy matching."""
        # Try exact match first
        for section_type in self._supported_types:
            section_data: Optional[dict[str, Any]] = self.get_section_data(designation=designation, section_type=section_type)
            if section_data:
                return section_type, section_data
            
        # Try fuzzy match with robust matching strategies
        return self._fuzzy_find_section(designation)

    # - Fuzzy find section
    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """Robust fuzzy section finding with multiple strategies."""
        designation_clean = designation.strip()
        
        # 1: Case-insensitive exact match
        for section_type in self._supported_types:
            sections = self._cache.get(section_type, {})
            for stored_designation, section_data in sections.items():
                if stored_designation.lower() == designation_clean.lower():
                    return section_type, section_data
        
        # 2: Normalize spaces, hyphens, and separators
        normalized_input = self._normalize_designation(designation_clean)
        for section_type in self._supported_types:
            sections = self._cache.get(section_type, {})
            for stored_designation, section_data in sections.items():
                if self._normalize_designation(stored_designation) == normalized_input:
                    return section_type, section_data
        
        # 3: Difflib-based similarity matching (robust but controlled)
        all_designations = []
        designation_map = {}
        
        for section_type in self._supported_types:
            sections = self._cache.get(section_type, {})
            for stored_designation, section_data in sections.items():
                all_designations.append(stored_designation)
                designation_map[stored_designation] = (section_type, section_data)
        
        # Find close matches with reasonable cutoff
        close_matches = difflib.get_close_matches(
            designation_clean, 
            all_designations, 
            n=1, 
            cutoff=0.8  # High cutoff to avoid false positives
        )
        
        if close_matches:
            best_match = close_matches[0]
            return designation_map[best_match]
        
        return None

    def _normalize_designation(self, designation: str) -> str:
        """Normalize designation for fuzzy matching."""
        # Convert to lowercase and normalize common separators
        normalized = designation.lower().strip()
        # Replace various separators with standard format
        normalized = normalized.replace(' ', '').replace('-', '').replace('_', '')
        # Handle 'x' separators consistently  
        normalized = normalized.replace('×', 'x')
        return normalized

    def get_supported_types(self) -> list[SectionType]:
        """Return supported section types for this region."""
        return self._supported_types.copy()
    
    def get_available_section_types(self) -> list[SectionType]:
        """Return a list of section types that have data loaded."""
        return [
            section_type for section_type 
            in self._supported_types
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

    # - Get similar sections using fuzzy matching
    def get_similar_sections(self, designation: str, section_type: Optional[SectionType] = None, n: int = 5) -> list[str]:
        """Get similar section designations using fuzzy matching."""
        all_sections = []
        
        if section_type:
            # Search within specific type
            sections = self.list_sections(section_type)
            all_sections = sections
        else:
            # Search across all types
            for st in self.get_available_section_types():
                sections = self.list_sections(st)
                all_sections.extend(sections)
        
        # Use difflib to find close matches
        close_matches = difflib.get_close_matches(
            designation, 
            all_sections, 
            n=n, 
            cutoff=0.6  # Balanced cutoff for suggestions
        )
        
        return close_matches


if __name__ == "__main__":    
    logger.info("🐬")