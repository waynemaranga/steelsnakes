"""
Channel steel sections (PFC) implementation.

This module implements Parallel Flange Channels with complete property definitions
matching the JSON data structure, using the new generic base system.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from steelsnakes.core.sections.UK.Base import BaseSection, SectionType, get_database, get_factory


@dataclass
class ParallelFlangeChannel(BaseSection):
    """
    Parallel Flange Channel (PFC) section.
    
    Complete implementation with all properties from the UK database.
    PFC sections are open sections with parallel flanges, commonly used
    for structural framing and support applications.
    """
    
    # Identification
    serial_size: str
    is_additional: bool = False
    
    # Physical properties - dimensions
    mass_per_metre: float = 0.0
    h: float = 0.0  # Overall depth (mm)
    b: float = 0.0  # Overall width (mm)
    tw: float = 0.0  # Web thickness (mm)
    tf: float = 0.0  # Flange thickness (mm)
    r: float = 0.0  # Root radius (mm)
    d: float = 0.0  # Depth between fillets (mm)
    
    # Ratios - slenderness
    cw_tw: float = 0.0  # Web slenderness ratio (cw/tw)
    cf_tf: float = 0.0  # Flange slenderness ratio (cf/tf)
    
    # Channel-specific geometry
    e0: float = 0.0  # Distance from centroidal axis to back of web (mm)
    
    # Clearances - detailing dimensions
    C: float = 0.0  # End clearance (mm)
    N: float = 0.0  # Big notch clearance (mm)
    n: float = 0.0  # Small notch clearance (mm)
    
    # Surface areas - for painting/coating
    surface_area_per_metre: float = 0.0  # Surface area per metre (m²/m)
    surface_area_per_tonne: float = 0.0  # Surface area per tonne (m²/t)
    
    # Second moments of area - bending resistance
    I_yy: float = 0.0  # Second moment of area, major axis (cm⁴)
    I_zz: float = 0.0  # Second moment of area, minor axis (cm⁴)
    
    # Radii of gyration - buckling analysis
    i_yy: float = 0.0  # Radius of gyration, major axis (cm)
    i_zz: float = 0.0  # Radius of gyration, minor axis (cm)
    
    # Section moduli - stress calculation
    W_el_yy: float = 0.0  # Elastic section modulus, major axis (cm³)
    W_el_zz: float = 0.0  # Elastic section modulus, minor axis (cm³)
    W_pl_yy: float = 0.0  # Plastic section modulus, major axis (cm³)
    W_pl_zz: float = 0.0  # Plastic section modulus, minor axis (cm³)
    
    # Buckling and torsion properties - advanced analysis
    U: float = 0.0  # Buckling parameter
    X: float = 0.0  # Torsional index
    I_w: float = 0.0  # Warping constant (cm⁶)
    I_t: float = 0.0  # Torsional constant (cm⁴)
    A: float = 0.0  # Cross-sectional area (cm²)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PFC
    



# Convenience function for direct instantiation
def PFC(designation: str, data_directory: Optional[Path] = None) -> ParallelFlangeChannel:
    """
    Create a Parallel Flange Channel section by designation.
    
    Args:
        designation: Section designation (e.g., "430x100x64")
        data_directory: Optional path to data directory
        
    Returns:
        ParallelFlangeChannel instance with actual float values
        
    Raises:
        ValueError: If designation not found in database
        
    Example usage:
        channel = PFC("430x100x64")
        print(f"Channel depth: {channel.h} mm")
        print(f"Shear center: {channel.e0} mm from web")
    """
    factory = get_factory(data_directory)
    
    # Register the class if not already registered
    if SectionType.PFC not in factory._section_classes:
        factory.register_section_class(ParallelFlangeChannel)
        
    # Create and return the section directly from factory
    return factory.create_section(designation, SectionType.PFC)


# Auto-register class when module is imported
def _register_channel_sections():
    """Register channel section classes with the global factory."""
    factory = get_factory()
    factory.register_section_class(ParallelFlangeChannel)


# Register on import
_register_channel_sections()


# Usage example and testing
if __name__ == "__main__":
    try:
        print("🔧 Testing Channel Sections...")
        
        # Create channel section
        channel = PFC("430x100x64")
        
        print(f"✅ Created channel: {channel} (type: {channel.get_section_type()})")
        print(f"   Dimensions: {channel.h}x{channel.b} mm")
        print(f"   Mass: {channel.mass_per_metre} kg/m")
        print(f"   Shear center distance (e0): {channel.e0} mm")
        
        # Test properties methods
               
        # Test database queries
        database = get_database()
        pfc_sections = database.list_sections(SectionType.PFC)
        print(f"\n📊 Available PFC sections: {len(pfc_sections)} total")
        
        # Search examples
        print("\n🔍 Search Examples:")
        
        # Lightweight channels
        light_channels = database.search_sections(SectionType.PFC, mass_per_metre__lt=20)
        print(f"   Lightweight channels (<20 kg/m): {len(light_channels)} found")
        
        # Deep channels
        deep_channels = database.search_sections(SectionType.PFC, h__gt=300)
        print(f"   Deep channels (>300mm): {len(deep_channels)} found")
        
        # Wide flange channels
        wide_channels = database.search_sections(SectionType.PFC, b__gt=100)
        print(f"   Wide flange channels (>100mm): {len(wide_channels)} found")
        
        if light_channels:
            designation, data = light_channels[0]
            print(f"   Lightest example: {designation} - {data['mass_per_metre']} kg/m")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()