"""
Preloaded bolt specifications for UK module.

This module implements Preloaded Bolt specifications using the new base system.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import get_uk_factory


@dataclass
class PreloadedBolt88(BaseSection):
    """Preloaded Bolt Grade 8.8 specification."""
    
    # Basic bolt properties - to be expanded based on actual data structure
    diameter: float = 0.0  # Bolt diameter (mm)
    grade: str = "8.8"
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.BOLT_PRE_88
    
    def get_properties(self) -> dict[str, any]:
        return {
            'designation': self.designation,
            'diameter': self.diameter,
            'grade': self.grade
        }


@dataclass
class PreloadedBolt109(BaseSection):
    """Preloaded Bolt Grade 10.9 specification."""
    
    diameter: float = 0.0
    grade: str = "10.9"
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.BOLT_PRE_109
    
    def get_properties(self) -> dict[str, any]:
        return {
            'designation': self.designation,
            'diameter': self.diameter,
            'grade': self.grade
        }


# Convenience functions
def BOLT_PRE_88(designation: str, data_directory: Optional[Path] = None) -> PreloadedBolt88:
    """Create a Grade 8.8 Preloaded Bolt by designation."""
    factory = get_uk_factory(data_directory)
    return factory.create_section(designation, SectionType.BOLT_PRE_88)


def BOLT_PRE_109(designation: str, data_directory: Optional[Path] = None) -> PreloadedBolt109:
    """Create a Grade 10.9 Preloaded Bolt by designation."""
    factory = get_uk_factory(data_directory)
    return factory.create_section(designation, SectionType.BOLT_PRE_109)
