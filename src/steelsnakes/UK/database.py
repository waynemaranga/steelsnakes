"""UK-specific database implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
import threading

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sections import SectionType

# TODO: do the uppercase renaming _uk_ to _UK_ later...

class UKSectionDatabase(SectionDatabase):
    """
    UK-specific steel section database.
    
    Handles UK steel sections from BS EN standards, including all section types
    from Universal Beams to Hollow Sections and Connection Components.
    
    Uses JSON files by default for maximum compatibility and simplicity.
    """

    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Resolve the UK data directory path."""
        if data_directory is not None:
            return data_directory
            
        # Auto-discovery for UK sections
        current_file: Path = Path(__file__).resolve()
        possible_paths: list[Path] = [          
            Path.cwd() / "src/steelsnakes/UK/data/", # from project root
            current_file.parent / "data/", # from package installation
            current_file.parent.parent.parent / "data/UK/", # from development environment
            current_file.parent.parent.parent / "src/steelsnakes/UK/data/", # from source directory
            current_file.parent.parent.parent.parent / "data/UK/" # from parent directory
        ]
        
        for path in possible_paths:
            resolved_path = path.resolve()
            if resolved_path.exists() and resolved_path.is_dir():
                return resolved_path
                
        # Fallback
        return current_file.parent / "data/"

    def get_supported_types(self) -> list[SectionType]:
        """Return all UK-supported section types."""
        return [
            # Universal sections
            SectionType.UB,
            SectionType.UC, 
            SectionType.UBP,
            
            # Channel sections
            SectionType.PFC,
            
            # Angle sections
            SectionType.L_EQUAL,
            SectionType.L_UNEQUAL,
            SectionType.L_EQUAL_B2B,
            SectionType.L_UNEQUAL_B2B,
            
            # Hot Finished Hollow sections
            SectionType.HFCHS,
            SectionType.HFRHS,
            SectionType.HFSHS,
            SectionType.HFEHS,
            
            # Cold Formed Hollow sections
            SectionType.CFCHS,
            SectionType.CFRHS,
            SectionType.CFSHS,
            
            # Connection components
            SectionType.WELDS,
            SectionType.BOLT_PRE_88,
            SectionType.BOLT_PRE_109,
        ]

    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """
        UK-specific fuzzy section finding with case-insensitive matching.
        
        Handles common UK designation variations and formats.
        """
        designation_lower = designation.lower().strip()
        
        # Try case-insensitive search across all types
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                if stored_designation.lower() == designation_lower:
                    return section_type, section_data
                    
        # Try partial matches for common patterns
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                # Remove spaces and try again
                if stored_designation.lower().replace(" ", "") == designation_lower.replace(" ", ""):
                    return section_type, section_data
                    
                # Try without 'x' separators (e.g., "457191x67" vs "457x191x67")
                if "x" in designation_lower and "x" in stored_designation.lower():
                    clean_input = designation_lower.replace("x", "")
                    clean_stored = stored_designation.lower().replace("x", "")
                    if clean_input == clean_stored:
                        return section_type, section_data
        
        return None


# Global instance for convenience
_global_uk_database: Optional[UKSectionDatabase] = None
_database_lock = threading.Lock()


def get_uk_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> UKSectionDatabase:
    """Get or create global UK database instance. Uses JSON by default.
    
    Args:
        data_directory: Optional path to data directory. If provided, returns a new
                       database instance without updating the global singleton.
        use_sqlite: Whether to use SQLite database format.
    
    Returns:
        UKSectionDatabase instance - either the global singleton or a new instance.
    """
    global _global_uk_database
    
    # If data_directory is provided, always return a new instance
    if data_directory is not None:
        return UKSectionDatabase(data_directory, use_sqlite=use_sqlite)
    
    # For global singleton, use double-checked locking pattern
    if _global_uk_database is None:
        with _database_lock:
            if _global_uk_database is None:
                _global_uk_database = UKSectionDatabase(None, use_sqlite=use_sqlite)
    
    return _global_uk_database

if __name__ == "__main__":
    db = get_uk_database()
    # print([i.value for i in db.get_supported_types() if type(i) == SectionType]) # Ruff[E721] https://docs.astral.sh/ruff/rules/type-comparison
    # print([i.value for i in db.get_supported_types() if type(i) is SectionType])
    print([i.value for i in db.get_supported_types() if isinstance(i, SectionType)])