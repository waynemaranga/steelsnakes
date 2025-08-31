"""US-specific database implementation."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sections import SectionType


class USSectionDatabase(SectionDatabase):
    """US-specific steel section database. EN 10365:2017"""

    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Resolve the US data directory path."""
        if data_directory is not None:
            return data_directory
            
        # Auto-discovery for US sections
        current_file: Path = Path(__file__).resolve()
        possible_paths: list[Path] = [          
            Path.cwd() / "src/steelsnakes/US/data/", # from project root
            current_file.parent / "data/", # from package installation
            current_file.parent.parent.parent / "data/US/", # from development environment
            current_file.parent.parent.parent / "src/steelsnakes/US/data/", # from source directory
            current_file.parent.parent.parent.parent / "data/US/" # from parent directory
        ]
        
        for path in possible_paths:
            resolved_path: Path = path.resolve()
            if resolved_path.exists() and resolved_path.is_dir():
                return resolved_path
                
        # Fallback
        return current_file.parent / "data/"

    def get_supported_types(self) -> list[SectionType]:
        """Return all US-supported section types."""
        return [
            # Beams
            SectionType.W,  # Wide Flange Beas
            SectionType.S,  # Standard Beams
            SectionType.M,  # Miscellaneous Beams #
            # SectionType.HP, # Bearing Piles # TODO: decide whether in Beams or Bearing Piles
           
            # Channels
            SectionType.C,  # Standard Channels
            SectionType.MC, # Miscellaneous Channels
            SectionType.C2C, # Back-to-Back Channels # TODO: propagate C2C throughout the codebase
            SectionType.MC2C, # Back-to-back Channels # TODO: propagate MC2C throughout the codebase

            # Angles
            SectionType.L_EQUAL, # Standard Angles, Equal legs
            SectionType.L_UNEQUAL, # Standard Angles, Unequal legs
            SectionType.L2L_EQUAL, # Back-to-back Standard Angles, Equal legs
            SectionType.L2L_LLBB, # Back-to-back Standard Angles, Unequal legs, Long Leg Back-to-Back
            SectionType.L2L_SLBB, # Back-to-back Standard Angles, Unequal legs, Short Leg Back-to-Back
            
            # Tees
            SectionType.WT, # cut from W shapes
            SectionType.ST, # cut from S shapes
            SectionType.MT, # cut from M shapes
            
            # Bearing Piles
            SectionType.HP, # Bearing Piles # also in Beams # TODO: resolve this with EU vs US
            
            # Hollow sections
            # SectionType.HSS, # Hollow Structural Sections --- IGNORE ---
            SectionType.HSS_RCT, # Rectangular Hollow Structural Sections
            SectionType.HSS_SQR, # Square Hollow Structural Sections
            SectionType.HSS_RND, # Round Hollow Structural Sections

            # Pipes
            SectionType.PIPE, # Pipes

            ]

    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """
        US-specific fuzzy section finding with case-insensitive matching.
        
        Handles common US designation variations and formats.
        """
        designation_upper: str = designation.upper().strip()
        
        # Try case-insensitive search across all types
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                if stored_designation.upper() == designation_upper:
                    return section_type, section_data
                    
        # Try partial matches for common patterns
        for section_type in self.get_supported_types():
            sections: dict[str, dict[str, Any]] = self._cache.get(section_type, {})
            
            for stored_designation, section_data in sections.items():
                # Remove spaces and try again
                if stored_designation.upper().replace(" ", "") == designation_upper.replace(" ", ""):
                    return section_type, section_data
                    
                # Try without 'x' separators (e.g., "457191x67" vs "457x191x67")
                if "x" in designation_upper and "x" in stored_designation.upper():
                    clean_input: str = designation_upper.replace("x", "")
                    clean_stored: str = stored_designation.upper().replace("x", "")
                    if clean_input == clean_stored:
                        return section_type, section_data

                if "." in designation_upper and "." in stored_designation.upper():
                    clean_input = designation_upper.replace(".", "")
                    clean_stored = stored_designation.upper().replace(".", "")
                    if clean_input == clean_stored:
                        return section_type, section_data

                if "-" in designation_upper and "-" in stored_designation.upper():
                    clean_input = designation_upper.replace("-", "")
                    clean_stored = stored_designation.upper().replace("-", "")
                    if clean_input == clean_stored:
                        return section_type, section_data

        return None

# Global instance for convenience
_global_US_database: Optional[USSectionDatabase] = None


def get_US_database(data_directory: Optional[Path] = None, use_sqlite: bool = False) -> USSectionDatabase:
    """Get or create global US database instance. Uses JSON by default."""
    global _global_US_database
    if _global_US_database is None or data_directory is not None:
        _global_US_database = USSectionDatabase(data_directory, use_sqlite=use_sqlite)
    return _global_US_database

if __name__ == "__main__":
    db: USSectionDatabase = get_US_database()
    # print([i.value for i in db.get_supported_types() if type(i) == SectionType]) # Ruff[E721] https://docs.astral.sh/ruff/rules/type-comparison
    # print([i.value for i in db.get_supported_types() if type(i) is SectionType])
    print([i.value for i in db.get_supported_types() if isinstance(i, SectionType)])


    