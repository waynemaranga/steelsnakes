"""Polars-based search engine for vectorized operations."""

from __future__ import annotations
import logging
from typing import Any, Optional

from steelsnakes.base.sections import SectionType

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None

logger = logging.getLogger(__name__)


class PolarsSearchEngine:
    """High-performance search engine using Polars for vectorized operations.
    
    Converts cached section data to Polars DataFrames and performs O(n) filtering
    using columnar Arrow format with Rust-based SIMD optimizations.
    """
    
    def __init__(self) -> None:
        if not POLARS_AVAILABLE:
            raise ImportError("Polars is required but not available. Install with: pip install polars>=1.17.0")
        
        self._dataframes: dict[SectionType, pl.DataFrame] = {}
        self._cache_version: dict[SectionType, int] = {}
    
    def _cache_to_dataframe(self, 
                           section_type: SectionType, 
                           sections: dict[str, dict[str, Any]]) -> pl.DataFrame:
        """Convert cached section data to Polars DataFrame.
        
        Args:
            section_type: The section type being converted
            sections: Dictionary of section data from cache
            
        Returns:
            Polars DataFrame with sections as rows and properties as columns
        """
        if not sections:
            return pl.DataFrame()
        
        # Convert nested dict to list of records
        records = []
        for designation, properties in sections.items():
            # Create a flat record starting with the properties
            record = dict(properties)
            # Ensure we have the key designation stored separately for filtering
            # The original designation field (if any) remains in the data
            record["_key_designation"] = designation
            records.append(record)
        
        # Create DataFrame from records
        try:
            df = pl.DataFrame(records)
            logger.debug(f"Created DataFrame for {section_type.value} with {df.height} rows and {df.width} columns")
            return df
        except Exception as e:
            logger.error(f"Failed to create DataFrame for {section_type.value}: {e}")
            return pl.DataFrame()
    
    def update_cache(self, 
                     section_type: SectionType, 
                     sections: dict[str, dict[str, Any]],
                     cache_version: int = 0) -> None:
        """Update the internal DataFrame cache for a section type.
        
        Args:
            section_type: The section type to update
            sections: Dictionary of section data from cache
            cache_version: Version number to track cache updates
        """
        current_version = self._cache_version.get(section_type, -1)
        if current_version >= cache_version and section_type in self._dataframes:
            return  # Already up to date
        
        self._dataframes[section_type] = self._cache_to_dataframe(section_type, sections)
        self._cache_version[section_type] = cache_version
    
    def search_sections(self,
                       section_type: SectionType,
                       sections: dict[str, dict[str, Any]],
                       **criteria: Any) -> list[tuple[str, dict[str, Any]]]:
        """Search sections using Polars vectorized operations.
        
        Args:
            section_type: The section type to search
            sections: Dictionary of section data from cache
            **criteria: Search criteria with comparison operators
            
        Returns:
            List of (designation, data) tuples matching the criteria
        """
        if not criteria:
            return []
        
        # Ensure we have an up-to-date DataFrame
        self.update_cache(section_type, sections)
        df = self._dataframes.get(section_type)
        
        if df is None or df.height == 0:
            return []
        
        # Build filter expressions using Polars
        filters = []
        
        for key, value in criteria.items():
            try:
                if "__" in key:
                    # Handle comparison operators
                    prop, operator = key.split("__", 1)
                    
                    # Check if column exists
                    if prop not in df.columns:
                        # Column doesn't exist, this is a non-match (same as prop_value is None)
                        filters.append(pl.lit(False))  # Force no matches
                        continue
                    
                    # Build filter expression based on operator
                    if operator == "gt":
                        filters.append(pl.col(prop) > value)
                    elif operator == "lt":
                        filters.append(pl.col(prop) < value)
                    elif operator == "gte":
                        filters.append(pl.col(prop) >= value)
                    elif operator == "lte":
                        filters.append(pl.col(prop) <= value)
                    elif operator == "eq":
                        filters.append(pl.col(prop) == value)
                    elif operator == "ne":
                        filters.append(pl.col(prop) != value)
                    # Unknown operators are ignored (same as original implementation)
                else:
                    # Exact match
                    if key not in df.columns:
                        # Column doesn't exist, this is a non-match (same as data.get(key) != value)
                        filters.append(pl.lit(False))  # Force no matches
                    else:
                        filters.append(pl.col(key) == value)
                    
            except Exception as e:
                # Skip invalid criteria (same as original implementation)
                logger.debug(f"Skipping invalid criteria {key}={value}: {e}")
                continue
        
        if not filters:
            # No valid filters means all sections should be returned
            # (same behavior as original when all criteria are invalid/unknown)
            results = []
            for row in df.iter_rows(named=True):
                designation = row["_key_designation"]
                # Reconstruct the data dict, excluding our internal key designation
                data = {k: v for k, v in row.items() if k != "_key_designation"}
                results.append((designation, data))
            return results
        
        try:
            # Combine all filters with AND logic
            combined_filter = filters[0]
            for f in filters[1:]:
                combined_filter = combined_filter & f
            
            # Apply filter and get results
            filtered_df = df.filter(combined_filter)
            
            # Convert back to the expected format
            results = []
            for row in filtered_df.iter_rows(named=True):
                designation = row["_key_designation"]
                # Reconstruct the data dict, excluding our internal key designation
                data = {k: v for k, v in row.items() if k != "_key_designation"}
                results.append((designation, data))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Polars search: {e}")
            return []
    
    def get_available_columns(self, section_type: SectionType) -> list[str]:
        """Get available columns for a section type.
        
        Args:
            section_type: The section type to query
            
        Returns:
            List of available column names (excluding internal fields)
        """
        df = self._dataframes.get(section_type)
        if df is None:
            return []
        return [col for col in df.columns if col != "_key_designation"]
    
    def clear_cache(self, section_type: Optional[SectionType] = None) -> None:
        """Clear cached DataFrames.
        
        Args:
            section_type: Specific section type to clear, or None to clear all
        """
        if section_type is None:
            self._dataframes.clear()
            self._cache_version.clear()
        else:
            self._dataframes.pop(section_type, None)
            self._cache_version.pop(section_type, None)