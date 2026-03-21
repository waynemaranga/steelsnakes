"""
UK Steel Sections Module.
"""

from typing import Optional

# Import base infrastructure
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.database import UKSectionDatabase, get_UK_database
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


# Auto-register all section classes on import
def _register_all_uk_sections():
    """Register all UK section classes with the global factory."""
    try:
        factory = get_UK_factory()
        # Factory constructor automatically calls _register_default_classes()
        # which registers all available section classes
    except Exception as e:
        print(f"Warning: Could not auto-register UK section classes: {e}")


# Initialize on import
_register_all_uk_sections()


# Convenience function for creating sections without specifying type
def create_section(designation: str, section_type: Optional[SectionType] = None):
    """
    Create a section instance by designation, with optional type.
    
    Args:
        designation: Section designation (e.g., "457x191x67")
        section_type: Optional section type. If None, auto-detects.
    
    Returns:
        Section instance of appropriate type
    """
    factory = get_UK_factory()
    return factory.create_section(designation, section_type)


# Add create_section to exports
# __all__.append("create_section")
