"""
Cold Formed Hollow sections for UK module.
This module implements Cold Formed Circular, Square, and Rectangular Hollow Sections.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


@dataclass
class ColdFormedCircularHollowSection(BaseSection):
    """Cold Formed Circular Hollow Section (CFCHS)."""
    
    mass_per_metre: float = 0.0
    A: float = 0.0  # Cross-sectional area (cm²)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFCHS
    
    def get_properties(self) -> dict[str, Any]:
        return {'designation': self.designation, 'mass_per_metre': self.mass_per_metre, 'A': self.A}


@dataclass
class ColdFormedSquareHollowSection(BaseSection):
    """Cold Formed Square Hollow Section (CFSHS)."""
    
    mass_per_metre: float = 0.0
    A: float = 0.0
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFSHS
    
    def get_properties(self) -> dict[str, Any]:
        return {'designation': self.designation, 'mass_per_metre': self.mass_per_metre, 'A': self.A}


@dataclass
class ColdFormedRectangularHollowSection(BaseSection):
    """Cold Formed Rectangular Hollow Section (CFRHS)."""
    
    mass_per_metre: float = 0.0
    A: float = 0.0
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.CFRHS
    
    def get_properties(self) -> dict[str, Any]:
        return {'designation': self.designation, 'mass_per_metre': self.mass_per_metre, 'A': self.A}


# Convenience functions
def CFCHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedCircularHollowSection:
    """Create a Cold Formed Circular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFCHS)
    return cast(ColdFormedCircularHollowSection, factory.create_section(designation, SectionType.CFCHS))


def CFSHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedSquareHollowSection:
    """Create a Cold Formed Square Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFSHS)
    return cast(ColdFormedSquareHollowSection, factory.create_section(designation, SectionType.CFSHS))


def CFRHS(designation: str, data_directory: Optional[Path] = None) -> ColdFormedRectangularHollowSection:
    """Create a Cold Formed Rectangular Hollow Section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    # return factory.create_section(designation, SectionType.CFRHS)
    return cast(ColdFormedRectangularHollowSection, factory.create_section(designation, SectionType.CFRHS))
