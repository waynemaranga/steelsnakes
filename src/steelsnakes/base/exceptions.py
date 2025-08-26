"""Custom exception classes for steelsnakes section factory."""


class SectionFactoryError(Exception):
    """Base exception class for section factory errors.
    
    This serves as the base class for all section factory-related errors,
    allowing callers to catch any factory error or specific subtypes.
    """
    pass


class SectionNotFoundError(SectionFactoryError):
    """Exception raised when a requested section cannot be found.
    
    This includes cases where:
    - A section with a specific type is not found
    - A section is not found in any registered type during auto-detection
    """
    pass


class SectionTypeNotRegisteredError(SectionFactoryError):
    """Exception raised when no class is registered for a section type.
    
    This occurs when a section is found in the database but there is no
    corresponding section class registered in the factory to create instances.
    """
    pass