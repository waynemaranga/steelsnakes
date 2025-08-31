"""EU-specific database implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sections import SectionType


class EUSectionDatabase(SectionDatabase):
    """EU-specific steel section database. EN 10365:2017"""

    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Resolve the EU data directory path."""
        if data_directory is not None:
            return data_directory
            
        # Auto-discovery for EU sections
        current_file: Path = Path(__file__).resolve()
        possible_paths: list[Path] = [          
            Path.cwd() / "src/steelsnakes/EU/data/", # from project root
            current_file.parent / "data/", # from package installation
            current_file.parent.parent.parent / "data/EU/", # from development environment
            current_file.parent.parent.parent / "src/steelsnakes/EU/data/", # from source directory
            current_file.parent.parent.parent.parent / "data/EU/" # from parent directory
        ]
        
        for path in possible_paths:
            resolved_path: Path = path.resolve()
            if resolved_path.exists() and resolved_path.is_dir():
                return resolved_path
                
        # Fallback
        return current_file.parent / "data/"

    def get_supported_types(self) -> list[SectionType]:
        """Return all EU-supported section types."""
        return [
            # Beams
            SectionType.IPE, # Parallel Flange I-sections
            SectionType.HE, # Wide Flange Beams
            SectionType.HL, # Extra Wide Flange Beams # TODO: clarify HL and HLZ are only split at HL/HZ level but are together as Extra Wide Flange Beams
            SectionType.HLZ, # Extra Wide Flange Beams # TODO: clarify HL and HLZ are only split at HL/HZ level but are together as Extra Wide Flange Beams
            SectionType.UB, # Universal Beams
           
            # Columns
            SectionType.HD, # Wide Flange Columns
            SectionType.UC, # Universal Columns

            # Bearing Piles
            SectionType.HP, # Wide Flange Bearing Piles
            SectionType.UBP, # Universal Bearing Piles
            
            # Channels
            SectionType.UPE, # Parallel Flange Channels (EU)
            SectionType.UPN, # Tapered Flange Channels
            SectionType.PFC, # Parallel Flange Channels (UK)
            
            # Angles
            SectionType.L_EQUAL, # Equal Angles
            SectionType.L_UNEQUAL, # Unequal Angles
            SectionType.L_EQUAL_B2B, # Back to Back Equal Angles
            SectionType.L_UNEQUAL_B2B, # Back to Back Unequal Angles
            
            # Flats
            SectionType.Sigma, # SIGMA
            SectionType.Zed, # Zed-butted Sections
            
            # Connection components
            # SectionType.WELDS, # Welds # Not Implemented
            # SectionType.BOLT_PRE_88, # Bolt Pre-88 # Not Implemented
            # SectionType.BOLT_PRE_109, # Bolt Pre-109 # Not Implemented

        ]

    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """
        EU-specific fuzzy section finding with case-insensitive matching.
        
        Handles common EU designation variations and formats.
        """
        designation_lower: str = designation.lower().strip()
        
        # Try case-insensitive search across all types
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                if stored_designation.lower() == designation_lower:
                    return section_type, section_data
                    
        # Try partial matches for common patterns
        for section_type in self.get_supported_types():
            sections: dict[str, dict[str, Any]] = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                # Remove spaces and try again
                if stored_designation.lower().replace(" ", "") == designation_lower.replace(" ", ""):
                    return section_type, section_data
                    
                # Try without 'x' separators (e.g., "457191x67" vs "457x191x67")
                if "x" in designation_lower and "x" in stored_designation.lower():
                    clean_input: str = designation_lower.replace("x", "")
                    clean_stored: str = stored_designation.lower().replace("x", "")
                    if clean_input == clean_stored:
                        return section_type, section_data

                if "." in designation_lower and "." in stored_designation.lower():
                    clean_input = designation_lower.replace(".", "")
                    clean_stored = stored_designation.lower().replace(".", "")
                    if clean_input == clean_stored:
                        return section_type, section_data

                if "-" in designation_lower and "-" in stored_designation.lower():
                    clean_input = designation_lower.replace("-", "")
                    clean_stored = stored_designation.lower().replace("-", "")
                    if clean_input == clean_stored:
                        return section_type, section_data
        
        return None


# Global instance for convenience
_global_EU_database: Optional[EUSectionDatabase] = None


def get_EU_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> EUSectionDatabase:
    """Get or create global EU database instance. Uses JSON by default."""
    global _global_EU_database
    if _global_EU_database is None or data_directory is not None:
        _global_EU_database = EUSectionDatabase(data_directory, use_sqlite=use_sqlite)
    return _global_EU_database

if __name__ == "__main__":
    db: EUSectionDatabase = get_EU_database()
    # print([i.value for i in db.get_supported_types() if type(i) == SectionType]) # Ruff[E721] https://docs.astral.sh/ruff/rules/type-comparison
    # print([i.value for i in db.get_supported_types() if type(i) is SectionType])
    print([i.value for i in db.get_supported_types() if isinstance(i, SectionType)])