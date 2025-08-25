"""
Weld specifications for UK module.

This module implements Weld specifications using the new base system.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_uk_factory


@dataclass
class WeldSpecification(BaseSection):
    """Weld specification section."""
    
    # Basic weld properties - to be expanded based on actual data structure
    weld_type: str = ""
    size: float = 0.0  # Weld size (mm)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WELDS
    
    def get_properties(self) -> dict[str, Any]:
        return {
            'designation': self.designation,
            'weld_type': self.weld_type,
            'size': self.size
        }


# Convenience function
def WELD(designation: str, data_directory: Optional[Path] = None) -> WeldSpecification:
    """Create a Weld specification by designation."""
    factory: UKSectionFactory = get_uk_factory(data_directory)
    # return factory.create_section(designation, SectionType.WELDS)
    return cast(WeldSpecification, factory.create_section(designation, SectionType.WELDS))
