#!/usr/bin/env python3
"""
CLI tools for steelsnakes section search and properties.

This module provides command-line utilities for searching steel sections
and displaying their properties across all supported regions.
"""

import argparse
import sys
import importlib
from pathlib import Path
from typing import Optional, Any

def _get_available_regions() -> list[str]:
    """Discover available regions by checking for database and create_section implementations."""
    available_regions = []
    steelsnakes_path = Path(__file__).parent
    
    # Check each region directory
    for region_dir in steelsnakes_path.iterdir():
        if (region_dir.is_dir() and 
            not region_dir.name.startswith('_') and 
            region_dir.name not in ['base', 'data', 'engine']):
            
            region_name = region_dir.name.upper()
            
            # Check if region has database.py and a create_section function in __init__.py
            database_file = region_dir / "database.py"
            init_file = region_dir / "__init__.py"
            
            if database_file.exists() and init_file.exists():
                try:
                    # Try to import the region module to verify it's working
                    module = importlib.import_module(f"steelsnakes.{region_dir.name}")
                    if hasattr(module, 'create_section'):
                        available_regions.append(region_name)
                except ImportError:
                    continue  # Skip regions that can't be imported
    
    return sorted(available_regions)

def _get_region_components(region: str) -> tuple[Any, Any]:
    """Get database and create_section function for a region."""
    region_lower = region.lower()
    
    try:
        region_module = importlib.import_module(f"steelsnakes.{region_lower}") # Import the region module
        database_module = importlib.import_module(f"steelsnakes.{region_lower}.database") # Import the database module
        database_getter_name = f"get_{region_lower}_database" # Get the database getter function
        database_getter = getattr(database_module, database_getter_name) # Get the database getter function
        create_section = getattr(region_module, 'create_section') # Get the create_section function
        
        return database_getter, create_section
        
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Region '{region}' is not properly implemented: {e}")

def search_section(designation: str, region: str = "UK") -> None:
    """Search for a steel section and show its properties."""
    available_regions = _get_available_regions()
    
    if region.upper() not in available_regions:
        print(f"✗ Region '{region}' not supported.")
        print(f"Available regions: {', '.join(available_regions)}")
        sys.exit(1)
    
    try:
        database_getter, create_section = _get_region_components(region.upper())
        section = create_section(designation) # Create the section
        
        if section is None:
            print(f"✗ Section '{designation}' not found in {region.upper()} database")
            sys.exit(1)
        
        # Display section properties
        print(f"=== {designation} ({region.upper()}) Properties ===")
        print(f"Type: {section.section_type.value}")
        print(f"Designation: {section.designation}")
        
        # Get all properties
        if hasattr(section, 'get_properties'):
            properties = section.get_properties()
        else:
            # Fallback to dataclass fields
            properties = {field: getattr(section, field) 
                        for field in section.__dataclass_fields__.keys() 
                        if not field.startswith('_')}
        
        # Display properties in organized format
        _display_properties(properties)
        
    except Exception as e:
        print(f"✗ Error searching for section: {e}")
        sys.exit(1)

def list_sections(section_type: Optional[str] = None, region: str = "UK", limit: int = 20) -> None:
    """List available sections, optionally filtered by type."""
    available_regions = _get_available_regions()
    
    if region.upper() not in available_regions:
        print(f"✗ Region '{region}' not supported.")
        print(f"Available regions: {', '.join(available_regions)}")
        sys.exit(1)
    
    try:
        from steelsnakes.base.sections import SectionType
        
        database_getter, _ = _get_region_components(region.upper())
        db = database_getter()
        
        if section_type:
            # Convert string to SectionType enum
            try:
                type_enum = SectionType(section_type.upper())
                sections = db.list_sections(type_enum)
                print(f"=== {region.upper()} {type_enum.value} Sections ({len(sections)} total) ===")
                for i, designation in enumerate(sections[:limit], 1):
                    print(f"  {i:3d}. {designation}")
                if len(sections) > limit:
                    print(f"  ... and {len(sections) - limit} more")
            except ValueError:
                print(f"✗ Unknown section type '{section_type}'")
                print("Available types:", ", ".join([t.value for t in db.get_supported_types()]))
                sys.exit(1)
        else:
            # List all types with counts
            print(f"=== {region.upper()} Available Section Types ===")
            for i, section_type_enum in enumerate(db.get_supported_types(), 1):
                sections = db.list_sections(section_type_enum)
                print(f"  {i:2d}. {section_type_enum.value:<15} ({len(sections)} sections)")
                
    except Exception as e:
        print(f"✗ Error listing sections: {e}")
        sys.exit(1)

def list_regions() -> None:
    """List all available regions with their implementation status."""
    available_regions = _get_available_regions()
    
    print("=== Available Steel Section Regions ===")
    if not available_regions:
        print("  No regions currently implemented.")
        return
    
    for i, region in enumerate(available_regions, 1):
        try:
            database_getter, _ = _get_region_components(region)
            db = database_getter()
            supported_types = db.get_supported_types()
            total_sections = sum(len(db.list_sections(st)) for st in supported_types)
            
            print(f"  {i:2d}. {region:<4} - {len(supported_types)} section types, {total_sections} total sections")
        except Exception:
            print(f"  {i:2d}. {region:<4} - Error loading region data")
    
    print(f"\nTotal regions available: {len(available_regions)}")
    print("Use --region <REGION> to specify a region (default: UK)")

def _display_properties(properties: dict[str, Any]) -> None:
    """Display section properties in a simple format."""
    # Skip internal/meta fields
    skip_fields = {'designation', 'section_type', 'is_additional'}
    
    # Filter and display properties
    displayed_props = {k: v for k, v in properties.items() 
                      if k not in skip_fields and v != 0.0 and v != ""}
    
    if not displayed_props:
        print("  No additional properties available.")
        return
    
    print("\nProperties:")
    for key, value in sorted(displayed_props.items()):
        if isinstance(value, float):
            print(f"  {key:<25} = {value:.3f}")
        elif isinstance(value, (int, str, bool)):
            print(f"  {key:<25} = {value}")
        else:
            print(f"  {key:<25} = {str(value)}")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SteelSnakes Section Search and Properties CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search "457x191x67"              # Search UK section (default)
  %(prog)s search "457x191x67" --region EU  # Search in EU database
  %(prog)s list                              # List all UK section types
  %(prog)s list --type UB --region UK       # List UK Universal Beams
  %(prog)s list --type IPE --region EU      # List EU IPE sections
  %(prog)s regions                           # Show all available regions
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for a steel section and show properties')
    search_parser.add_argument('designation', help='Section designation (e.g., "457x191x67")')
    search_parser.add_argument('--region', default='UK', 
                             help='Region to search in (default: UK)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available sections')
    list_parser.add_argument('--type', dest='section_type',
                           help='Filter by section type (e.g., UB, UC, PFC, IPE)')
    list_parser.add_argument('--region', default='UK',
                           help='Region to list sections for (default: UK)')
    list_parser.add_argument('--limit', type=int, default=20,
                           help='Maximum number of sections to display (default: 20)')
    
    # Regions command
    regions_parser = subparsers.add_parser('regions', help='List all available regions')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'search':
        search_section(args.designation, args.region)
    elif args.command == 'list':
        list_sections(args.section_type, args.region, args.limit)
    elif args.command == 'regions':
        list_regions()

if __name__ == "__main__":
    main()