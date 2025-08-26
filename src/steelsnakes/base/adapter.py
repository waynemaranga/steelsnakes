"""Data adapter for transforming section data before object creation."""

from __future__ import annotations
from typing import Any
import logging

logger: logging.Logger = logging.getLogger(__name__)


class SectionDataAdapter:
    """Handles data transformation for section creation.
    
    This class is responsible for cleaning and preparing section data
    before it is passed to section constructors, separating data
    transformation concerns from the factory logic.
    """

    @staticmethod
    def transform_section_data(
        section_data: dict[str, Any], 
        designation: str
    ) -> dict[str, Any]:
        """Transform section data for object creation.
        
        Applies the following transformations:
        1. Filters out metadata fields (starting with '_')
        2. Adds missing designation field if not present
        
        Args:
            section_data: Raw section data from database
            designation: Section designation to use if missing from data
            
        Returns:
            Transformed data ready for section constructor
        """
        # Create a copy to avoid modifying original data
        clean_data = section_data.copy()
        
        # Apply transformations
        clean_data = SectionDataAdapter._filter_metadata(clean_data)
        clean_data = SectionDataAdapter._ensure_designation(clean_data, designation)
        
        return clean_data

    @staticmethod
    def _filter_metadata(data: dict[str, Any]) -> dict[str, Any]:
        """Remove metadata fields (starting with '_') from section data.
        
        Args:
            data: Section data dictionary
            
        Returns:
            Data with metadata fields removed
        """
        return {k: v for k, v in data.items() if not k.startswith('_')}

    @staticmethod
    def _ensure_designation(data: dict[str, Any], designation: str) -> dict[str, Any]:
        """Ensure designation field is present in section data.
        
        Args:
            data: Section data dictionary
            designation: Designation value to add if missing
            
        Returns:
            Data with designation field guaranteed to be present
        """
        if 'designation' not in data:
            data['designation'] = designation
        return data