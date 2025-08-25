"""
Tests for the base factory system including SectionFactory.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Optional, Any, Dict, Type

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase


# Mock Section Classes for Testing
class MockUniversalBeam(BaseSection):
    """Mock Universal Beam section class for testing."""
    
    def __init__(self, designation: str, mass_per_metre: float = 100.0, **kwargs):
        super().__init__(designation=designation)
        self.mass_per_metre = mass_per_metre
        # Store any additional properties for testing
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UB
    
    def get_properties(self) -> dict[str, Any]:
        return {
            'designation': self.designation,
            'mass_per_metre': self.mass_per_metre,
            'section_type': self.get_section_type().value
        }


class MockParallelFlangeChannel(BaseSection):
    """Mock Parallel Flange Channel section class for testing."""
    
    def __init__(self, designation: str, mass_per_metre: float = 50.0, **kwargs):
        super().__init__(designation=designation)
        self.mass_per_metre = mass_per_metre
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PFC
    
    def get_properties(self) -> dict[str, Any]:
        return {
            'designation': self.designation,
            'mass_per_metre': self.mass_per_metre,
            'section_type': self.get_section_type().value
        }


class MockWeldSpecification(BaseSection):
    """Mock Weld Specification class for testing designation addition."""
    
    def __init__(self, designation: str = "", weld_type: str = "BUTT", **kwargs):
        super().__init__(designation=designation)
        self.weld_type = weld_type
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.WELDS
    
    def get_properties(self) -> dict[str, Any]:
        return {
            'designation': self.designation,
            'weld_type': self.weld_type,
            'section_type': self.get_section_type().value
        }


# Mock Database Class
class MockSectionDatabase(SectionDatabase):
    """Mock implementation of SectionDatabase for testing."""
    
    def __init__(self, data_directory: Optional[Any] = None, use_sqlite: bool = False):
        # Skip the parent __init__ to avoid file system operations
        self.data_directory = data_directory or Mock()
        self.use_sqlite = use_sqlite
        self._cache: dict[SectionType, dict[str, dict[str, Any]]] = {}
        
        # Set up test data
        self._setup_test_data()
    
    def _setup_test_data(self):
        """Set up mock section data for testing."""
        self._cache[SectionType.UB] = {
            "254x146x31": {
                "designation": "254x146x31",
                "mass_per_metre": 31.0,
                "depth": 254,
                "width": 146,
                "_section_type": "UB"
            },
            "305x165x40": {
                "designation": "305x165x40", 
                "mass_per_metre": 40.0,
                "depth": 305,
                "width": 165,
                "_section_type": "UB"
            }
        }
        
        self._cache[SectionType.PFC] = {
            "150x75x18": {
                "designation": "150x75x18",
                "mass_per_metre": 18.0,
                "depth": 150,
                "width": 75,
                "_section_type": "PFC"
            }
        }
        
        self._cache[SectionType.WELDS] = {
            "BUTT_WELD_6": {
                "weld_type": "BUTT",
                "throat_thickness": 6.0,
                "_section_type": "WELDS"
                # Note: No 'designation' field to test auto-addition
            }
        }
    
    def _resolve_data_directory(self, data_directory):
        return data_directory or Mock()
    
    def get_supported_types(self) -> list[SectionType]:
        return [SectionType.UB, SectionType.PFC, SectionType.WELDS]
    
    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        # Simple case-insensitive search for testing
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            for key, data in sections.items():
                if key.lower() == designation.lower():
                    return section_type, data
        return None
    
    def get_section_data(self, designation: str, section_type: SectionType) -> Optional[dict[str, Any]]:
        """Get section data by designation and type."""
        return self._cache.get(section_type, {}).get(designation)
    
    def find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """Find section across all types."""
        for section_type in self.get_supported_types():
            data = self.get_section_data(designation, section_type)
            if data:
                return section_type, data
        
        # Try fuzzy search
        return self._fuzzy_find_section(designation)
    
    def list_sections(self, section_type: SectionType) -> list[str]:
        """List sections of given type."""
        return list(self._cache.get(section_type, {}).keys())
    
    def get_available_section_types(self) -> list[SectionType]:
        """Get available section types."""
        return [st for st in self.get_supported_types() if st in self._cache and self._cache[st]]


# Concrete Factory Implementation for Testing
class MockSectionFactory(SectionFactory):
    """Concrete implementation of SectionFactory for testing."""
    
    def __init__(self, database: SectionDatabase):
        super().__init__(database)
    
    def _register_default_classes(self) -> None:
        """Register mock section classes for testing."""
        self.register_section_class(MockUniversalBeam)
        self.register_section_class(MockParallelFlangeChannel)
        self.register_section_class(MockWeldSpecification)


class TestSectionFactoryBase:
    """Test base functionality of SectionFactory."""
    
    @pytest.fixture
    def mock_database(self):
        """Fixture providing a mock database."""
        return MockSectionDatabase()
    
    @pytest.fixture
    def factory(self, mock_database):
        """Fixture providing a test factory."""
        return MockSectionFactory(mock_database)
    
    def test_factory_initialization(self, mock_database):
        """Test factory initialization."""
        factory = MockSectionFactory(mock_database)
        
        assert factory.database is mock_database
        assert isinstance(factory._section_classes, dict)
        
        # Check that default classes were registered
        assert SectionType.UB in factory._section_classes
        assert SectionType.PFC in factory._section_classes
        assert SectionType.WELDS in factory._section_classes
        
        assert factory._section_classes[SectionType.UB] is MockUniversalBeam
        assert factory._section_classes[SectionType.PFC] is MockParallelFlangeChannel
        assert factory._section_classes[SectionType.WELDS] is MockWeldSpecification
    
    def test_register_section_class(self, factory):
        """Test manual registration of section classes."""
        
        # Create a new mock class
        class MockColumn(BaseSection):
            @classmethod
            def get_section_type(cls):
                return SectionType.UC
            
            def get_properties(self):
                return {}
        
        # Register it
        factory.register_section_class(MockColumn)
        
        # Verify registration
        assert SectionType.UC in factory._section_classes
        assert factory._section_classes[SectionType.UC] is MockColumn
    
    def test_abstract_factory_cannot_instantiate(self):
        """Test that abstract SectionFactory cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SectionFactory(Mock()) # FIXME: Cannot instantiate abstract class "SectionFactory"; "SectionFactory._register_default_classes" is not implemented


class TestSectionCreation:
    """Test section creation functionality."""
    
    @pytest.fixture
    def mock_database(self):
        return MockSectionDatabase()
    
    @pytest.fixture 
    def factory(self, mock_database):
        return MockSectionFactory(mock_database)
    
    def test_create_section_with_specified_type(self, factory):
        """Test creating section with explicitly specified type."""
        section = factory.create_section("254x146x31", SectionType.UB)
        
        assert isinstance(section, MockUniversalBeam)
        assert section.designation == "254x146x31"
        assert section.mass_per_metre == 31.0
        assert section.depth == 254
        assert section.width == 146
    
    def test_create_section_with_auto_detection(self, factory):
        """Test creating section with automatic type detection."""
        section = factory.create_section("150x75x18")
        
        assert isinstance(section, MockParallelFlangeChannel)
        assert section.designation == "150x75x18"
        assert section.mass_per_metre == 18.0
        assert section.depth == 150
        assert section.width == 75
    
    def test_create_section_with_missing_designation(self, factory):
        """Test creating section where designation needs to be added."""
        section = factory.create_section("BUTT_WELD_6", SectionType.WELDS)
        
        assert isinstance(section, MockWeldSpecification)
        assert section.designation == "BUTT_WELD_6"  # Should be added automatically
        assert section.weld_type == "BUTT"
        assert section.throat_thickness == 6.0
    
    def test_create_section_filters_metadata(self, factory):
        """Test that metadata fields starting with '_' are filtered out."""
        section = factory.create_section("254x146x31", SectionType.UB)
        
        # _section_type should not be passed to constructor
        assert not hasattr(section, '_section_type')
        assert section.designation == "254x146x31"
        assert section.mass_per_metre == 31.0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def mock_database(self):
        return MockSectionDatabase()
    
    @pytest.fixture
    def factory(self, mock_database):
        return MockSectionFactory(mock_database)
    
    def test_section_not_found_with_type(self, factory):
        """Test error when section not found with specified type."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("NONEXISTENT", SectionType.UB)
        
        assert "Section 'NONEXISTENT' of type 'UB' not found" in str(exc_info.value)
        assert "Available sections: 2" in str(exc_info.value)
    
    def test_section_not_found_auto_detect(self, factory):
        """Test error when section not found in any type."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("TOTALLY_NONEXISTENT")
        
        assert "Section 'TOTALLY_NONEXISTENT' not found in any type" in str(exc_info.value)
        assert "Available types:" in str(exc_info.value)
    
    def test_unregistered_section_type(self, mock_database):
        """Test error when section type not registered."""
        # Create factory without registering UC type
        factory = MockSectionFactory(mock_database)
        
        # Manually add data for UC type but don't register class
        mock_database._cache[SectionType.UC] = {
            "203x203x46": {"designation": "203x203x46", "mass_per_metre": 46.0}
        }
        
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("203x203x46", SectionType.UC)
        
        assert "No registered class for section type 'UC'" in str(exc_info.value)
        assert "Available types:" in str(exc_info.value)
    
    def test_database_returns_none(self, factory):
        """Test handling when database returns None."""
        # Mock the database to return None
        factory.database.get_section_data = Mock(return_value=None)
        factory.database.list_sections = Mock(return_value=["254x146x31", "305x165x40"])
        
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("MISSING", SectionType.UB)
        
        assert "Section 'MISSING' of type 'UB' not found" in str(exc_info.value)
    
    def test_database_find_section_returns_none(self, factory):
        """Test handling when database find_section returns None."""
        factory.database.find_section = Mock(return_value=None)
        factory.database.get_available_section_types = Mock(return_value=[SectionType.UB, SectionType.PFC])
        
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("MISSING")
        
        assert "Section 'MISSING' not found in any type" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    @pytest.fixture
    def mock_database(self):
        return MockSectionDatabase()
    
    @pytest.fixture
    def factory(self, mock_database):
        return MockSectionFactory(mock_database)
    
    def test_section_data_with_no_designation_field(self, factory):
        """Test section creation when data has no designation field."""
        # This should add designation automatically
        section = factory.create_section("BUTT_WELD_6", SectionType.WELDS)
        
        assert section.designation == "BUTT_WELD_6"
        assert section.weld_type == "BUTT"
    
    def test_section_data_with_existing_designation_field(self, factory):
        """Test section creation when data already has designation field."""
        section = factory.create_section("254x146x31", SectionType.UB)
        
        # Should use the designation from data, not override it
        assert section.designation == "254x146x31"
    
    def test_case_insensitive_search(self, factory):
        """Test that fuzzy search works case-insensitively."""
        # Modify database to return case-insensitive match
        factory.database._cache[SectionType.UB]["254X146X31"] = factory.database._cache[SectionType.UB]["254x146x31"].copy()
        
        section = factory.create_section("254X146X31")
        assert isinstance(section, MockUniversalBeam)
        assert section.designation == "254x146x31"
    
    def test_extra_properties_passed_through(self, factory):
        """Test that extra properties in data are passed to section constructor."""
        # Add extra properties to test data
        test_data = factory.database._cache[SectionType.UB]["254x146x31"].copy()
        test_data["extra_property"] = "test_value"
        factory.database._cache[SectionType.UB]["254x146x31"] = test_data
        
        section = factory.create_section("254x146x31", SectionType.UB)
        
        assert hasattr(section, "extra_property")
        assert section.extra_property == "test_value"


if __name__ == "__main__":
    pytest.main([__file__])
