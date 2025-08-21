"""
Universal steel sections (UB, UC, UBP) implementation.

This module consolidates the best features from both Universal.py implementations
and uses the new generic base system for consistency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class UniversalSection(BaseSection):
    """Base class for all universal steel sections (UB, UC, UBP)."""
    
    # Identification  
    serial_size: str
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0
    h: float = 0.0  # Overall depth (mm)
    b: float = 0.0  # Overall width (mm)
    tw: float = 0.0  # Web thickness (mm)
    tf: float = 0.0  # Flange thickness (mm)
    r: float = 0.0  # Root radius (mm)
    d: float = 0.0  # Depth between fillets (mm)
    
    # Ratios
    cw_tw: float = 0.0  # Web slenderness ratio
    cf_tf: float = 0.0  # Flange slenderness ratio
    
    # Clearances
    C: float = 0.0  # End clearance (mm)
    N: float = 0.0  # Notch clearance (mm)
    n: float = 0.0  # Alternative notch clearance (mm)
    
    # Surface areas
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    # Second moments of area
    I_yy: float = 0.0  # Second moment of area, major axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, minor axis (cm⁴)
    
    # Radii of gyration
    i_yy: float = 0.0  # Radius of gyration, major axis (cm)
    i_zz: float = 0.0  # Radius of gyration, minor axis (cm)
    
    # Section moduli
    W_el_yy: float = 0.0  # Elastic section modulus, major axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, minor axis (cm³)
    W_pl_yy: float = 0.0  # Plastic section modulus, major axis (cm³)
    W_pl_zz: float = 0.0  # Plastic section modulus, minor axis (cm³)
    
    # Buckling and torsion properties
    U: float = 0.0  # Buckling parameter
    X: float = 0.0  # Torsional index
    I_w: float = 0.0  # Warping constant (cm⁶)
    I_t: float = 0.0  # Torsional constant (cm⁴)
    A: float = 0.0  # Cross-sectional area (cm²)


class UniversalBeam(UniversalSection):
    """Universal Beam (UB) section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UB


class UniversalColumn(UniversalSection):
    """Universal Column (UC) section."""
    
    @classmethod  
    def get_section_type(cls) -> SectionType:
        return SectionType.UC


class UniversalBearingPile(UniversalSection):
    """Universal Bearing Pile (UBP) section."""
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UBP


# Convenience functions for direct instantiation
def UB(designation: str, data_directory: Optional[Path] = None) -> UniversalBeam:
    """
    Create a Universal Beam section by designation.
    
    Args:
        designation: Section designation (e.g., "457x191x67")
        data_directory: Optional path to data directory
        
    Returns:
        UniversalBeam instance with actual float values
    """
    factory = get_factory(data_directory)
    
    # Register the class if not already registered
    if SectionType.UB not in factory._section_classes:
        factory.register_section_class(UniversalBeam)
        
    # Create and return the section directly from factory
    return factory.create_section(designation, SectionType.UB)


def UC(designation: str, data_directory: Optional[Path] = None) -> UniversalColumn:
    """
    Create a Universal Column section by designation.
    
    Args:
        designation: Section designation (e.g., "305x305x137")
        data_directory: Optional path to data directory
        
    Returns:
        UniversalColumn instance with actual float values
    """
    factory = get_factory(data_directory)
    
    # Register the class if not already registered
    if SectionType.UC not in factory._section_classes:
        factory.register_section_class(UniversalColumn)
        
    # Create and return the section directly from factory
    return factory.create_section(designation, SectionType.UC)


def UBP(designation: str, data_directory: Optional[Path] = None) -> UniversalBearingPile:
    """
    Create a Universal Bearing Pile section by designation.
    
    Args:
        designation: Section designation (e.g., "203x203x45")
        data_directory: Optional path to data directory
        
    Returns:
        UniversalBearingPile instance with actual float values
    """
    factory = get_factory(data_directory)
    
    # Register the class if not already registered
    if SectionType.UBP not in factory._section_classes:
        factory.register_section_class(UniversalBearingPile)
        
    # Create and return the section directly from factory
    return factory.create_section(designation, SectionType.UBP)


# Auto-register classes when module is imported
def _register_universal_sections():
    """Register all universal section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(UniversalBeam)
    factory.register_section_class(UniversalColumn)
    factory.register_section_class(UniversalBearingPile)


# Register on import
_register_universal_sections()


# Usage example and testing
if __name__ == "__main__":
    try:
        print("🔧 Testing Universal Sections...")
        
        # Create sections using convenience classes
        beam = UB("457x191x67")
        column = UC("305x305x137")
        
        print(f"✅ Created beam: {beam} (type: {beam.get_section_type()})")
        print(f"✅ Created column: {column} (type: {column.get_section_type()})")
        print(f"   Beam I_yy: {beam.I_yy} cm⁴")
        print(f"   Column I_yy: {column.I_yy} cm⁴")
        
        # Test factory usage
        factory = get_factory()
        database = get_database()
        
        # Auto-detect section type
        auto_section = factory.create_section("457x191x67")
        print(f"✅ Auto-detected: {auto_section} as {auto_section.get_section_type()}")
        
        # List available sections
        ub_sections = database.list_sections(SectionType.UB)
        uc_sections = database.list_sections(SectionType.UC)
        ubp_sections = database.list_sections(SectionType.UBP)
        
        print("📊 Available sections:")
        print(f"   UB: {len(ub_sections)} sections")
        print(f"   UC: {len(uc_sections)} sections") 
        print(f"   UBP: {len(ubp_sections)} sections")
        
        # Test search functionality
        heavy_beams = database.search_sections(SectionType.UB, mass_per_metre__gt=200)
        print(f"🔍 Heavy beams (>200 kg/m): {len(heavy_beams)} found")
        
        if heavy_beams:
            designation, data = heavy_beams[0]
            print(f"   Example: {designation} - {data['mass_per_metre']} kg/m")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()