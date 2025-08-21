"""
Demonstration of the new steelsnakes section system.

This shows how the refactored architecture provides a clean, consistent
interface for working with all types of steel sections.
"""

from steelsnakes.core.sections.UK import (
    UB, UC, UBP, PFC, L_EQUAL, L_UNEQUAL, 
    CFCHS, CFSHS, CFRHS, HFCHS, HFSHS, HFRHS, HFEHS,
    WELD, get_database, get_factory, SectionType
)



def demo_basic_usage():
    """Demonstrate basic section creation and usage."""
    print("🏗️  SteelSnakes Section Demo")
    print("=" * 50)
    
    # Create sections using simple constructors
    beam = UB("457x191x67")
    column = UC("305x305x137") 
    channel = PFC("430x100x64")
    
    print(f"✅ Universal Beam: {beam}")
    print(f"   I_yy = {beam.I_yy} cm⁴")
    print(f"   Mass = {beam.mass_per_metre} kg/m")
    print(f"   Dimensions = {beam.h}x{beam.b} mm")
    
    print(f"✅ Universal Column: {column}")
    print(f"   I_yy = {column.I_yy} cm⁴") 
    print(f"   Mass = {column.mass_per_metre} kg/m")
    print(f"   Dimensions = {column.h}x{column.b} mm")
    
    print(f"✅ Parallel Flange Channel: {channel}")
    print(f"   I_yy = {channel.I_yy} cm⁴")
    print(f"   Mass = {channel.mass_per_metre} kg/m")
    print(f"   Dimensions = {channel.h}x{channel.b} mm")
    print(f"   Shear center (e0) = {channel.e0} mm")

def demo_various_sections():
    """Demonstrate various section types available."""
    print("\n🔧 Various Section Types Demo")
    print("=" * 50)
    
    # Test different section types
    try:
        # Channel
        channel = PFC("380x100x54")
        print(f"✅ Channel: {channel}")
        print(f"   Dimensions: {channel.h}x{channel.b} mm, e0: {channel.e0} mm")
        
        # Equal angle
        angle = L_EQUAL("200x200x24.0")
        print(f"✅ Equal Angle: {angle}")
        print(f"   Legs: {angle.hxh}, Thickness: {angle.t} mm")
        print(f"   Principal moments: I_uu={angle.I_uu}, I_vv={angle.I_vv} cm⁴")
        
        # Unequal angle  
        unequal_angle = L_UNEQUAL("200x150x12")
        print(f"✅ Unequal Angle: {unequal_angle}")
        print(f"   Legs: {unequal_angle.hxb}, Thickness: {unequal_angle.t} mm")
        
        # Cold formed hollow sections
        cf_chs = CFCHS("48.3x4.0")
        print(f"✅ CF Circular: {cf_chs}")
        print(f"   Diameter: {cf_chs.d} mm, Thickness: {cf_chs.t} mm")
        
        cf_shs = CFSHS("100x100x4.0")
        print(f"✅ CF Square: {cf_shs}")
        print(f"   Size: {cf_shs.hxh}, Thickness: {cf_shs.t} mm")
        
        # Hot finished hollow sections
        hf_chs = HFCHS("42.4x3.6")
        print(f"✅ HF Circular: {hf_chs}")
        print(f"   Diameter: {hf_chs.d} mm, Thickness: {hf_chs.t} mm")
        
        # Weld specification
        weld = WELD("6.0")
        print(f"✅ Weld: {weld}")
        print(f"   Throat size: {weld.s} mm, Throat area: {weld.a} mm²/mm")
        
    except Exception as e:
        print(f"⚠️  Some sections may not be available: {e}")
        print("   (This is expected if certain section data files are missing)")

def demo_database_features():
    """Demonstrate database and search capabilities."""
    print("\n📊 Database Features")
    print("=" * 50)
    
    database = get_database()
    
    # Show available section types
    available_types = database.get_available_types()
    print(f"Available section types: {[t.value for t in available_types]}")
    
    # Count sections
    for section_type in available_types:
        count = len(database.list_sections(section_type))
        print(f"   {section_type.value}: {count} sections")
    
    # Search examples
    print("\n🔍 Advanced Search Examples:")
    
    # Heavy beams
    heavy_beams = database.search_sections(SectionType.UB, mass_per_metre__gt=200)
    print(f"   Heavy beams (>200 kg/m): {len(heavy_beams)} found")
    
    # Light channels  
    light_channels = database.search_sections(SectionType.PFC, mass_per_metre__lt=20)
    print(f"   Light channels (<20 kg/m): {len(light_channels)} found")
    
    # Deep channels
    deep_channels = database.search_sections(SectionType.PFC, h__gt=300)
    print(f"   Deep channels (>300mm): {len(deep_channels)} found")
    
    # Wide flange channels
    wide_channels = database.search_sections(SectionType.PFC, b__gt=100)
    print(f"   Wide flange channels (>100mm): {len(wide_channels)} found")
    
    if heavy_beams:
        designation, data = heavy_beams[0]
        print(f"   Heaviest beam example: {designation} - {data['mass_per_metre']} kg/m")
        
    if light_channels:
        designation, data = light_channels[0]
        print(f"   Lightest channel example: {designation} - {data['mass_per_metre']} kg/m")

def demo_factory_usage():
    """Demonstrate factory pattern usage."""
    print("\n🏭 Factory Pattern Demo")
    print("=" * 50)
    
    factory = get_factory()
    
    # Auto-detection
    auto_section = factory.create_section("457x191x67")
    print(f"Auto-detected section: {auto_section} as {auto_section.get_section_type().value}")
    
    # Explicit type specification
    explicit_section = factory.create_section("305x305x137", SectionType.UC)
    print(f"Explicit creation: {explicit_section} as {explicit_section.get_section_type().value}")
    
    # Channel creation
    channel_section = factory.create_section("430x100x64", SectionType.PFC)
    print(f"Channel creation: {channel_section} as {channel_section.get_section_type().value}")

def demo_comparison():
    """Demonstrate section comparison capabilities."""
    print("\n⚖️  Section Comparison Demo")
    print("=" * 50)
    
    # Compare different beam sizes
    beam_small = UB("203x133x25")
    beam_medium = UB("457x191x67")
    beam_large = UB("914x305x201")
    
    beams = [beam_small, beam_medium, beam_large]
    
    print("Beam comparison:")
    for beam in beams:
        print(f"   {beam.designation}: I_yy={beam.I_yy} cm⁴, Mass={beam.mass_per_metre} kg/m")
    
    # Compare channel vs beam
    print("\nChannel vs Beam comparison:")
    channel = PFC("430x100x64")
    beam = UB("457x191x67")
    
    print(f"   Channel {channel.designation}: I_yy={channel.I_yy} cm⁴, Mass={channel.mass_per_metre} kg/m")
    print(f"   Beam {beam.designation}: I_yy={beam.I_yy} cm⁴, Mass={beam.mass_per_metre} kg/m")
    print(f"   Beam is {beam.I_yy / channel.I_yy:.1f}x stiffer in major axis")

if __name__ == "__main__":
    try:
        demo_basic_usage()
        demo_various_sections()
        demo_database_features()
        demo_factory_usage()
        demo_comparison()
        
        print("\n🎉 All demos completed successfully!")
        print("\n💡 The refactored system provides:")
        print("   • Unified interface for all section types")
        print("   • 18 different section types automatically loaded")
        print("   • Advanced search capabilities")
        print("   • Type-safe section properties")
        print("   • Easy extensibility for new section types")
        print("   • Comprehensive steel section database")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()