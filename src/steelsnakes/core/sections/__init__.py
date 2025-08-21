"""
Steel sections module with regional support.

This module provides access to steel section databases organized by region:
- UK: British/European steel sections (BS EN standards)
- US: American steel sections (AISC standards) - Future
- AUS: Australian steel sections (AS standards) - Future

The default import provides UK sections for backward compatibility.
"""

# Import UK sections as the default (backward compatibility)
# from .UK import * # FIXME: Uncomment after fixing backwards compatibility

# Regional imports for explicit access
from steelsnakes.core.sections import UK

# Make regional modules available
__all__ = [
    # Re-export all UK sections as default
    *UK.__all__,
    
    # Regional modules
    "UK",
]

# Future regional imports (when implemented):
# from . import US, AUS
# __all__.extend(["US", "AUS"])