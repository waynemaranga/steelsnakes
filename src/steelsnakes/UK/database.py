"""UK-specific database implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sections import SectionType


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
            # From UK module to data/sections/UK
            current_file.parent / "../data/sections/UK",
            current_file.parent.parent / "data/sections/UK", 
            current_file.parent.parent.parent / "data/sections/UK",
            # From project root
            Path.cwd() / "data/sections/UK",
            Path.cwd() / "src/steelsnakes/data/sections/UK",
        ]
        
        for path in possible_paths:
            resolved_path = path.resolve()
            if resolved_path.exists() and resolved_path.is_dir():
                return resolved_path
                
        # Fallback
        return current_file.parent / "data/sections/UK"

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


def get_uk_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> UKSectionDatabase:
    """Get or create global UK database instance. Uses JSON by default."""
    global _global_uk_database
    if _global_uk_database is None or data_directory is not None:
        _global_uk_database = UKSectionDatabase(data_directory, use_sqlite=use_sqlite)
    return _global_uk_database
