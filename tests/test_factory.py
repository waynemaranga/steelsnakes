"""
Essential tests for the base factory system.
Tests SectionFactory initialization and section creation.
"""

# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

import pytest
import json
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.exceptions import SectionNotFoundError, SectionTypeNotRegisteredError


# Mock Section Class for Testing
class MockUniversalBeam(BaseSection):
    """Mock Universal Beam section class for testing."""

    def __init__(self, designation: str, mass_per_metre: float = 100.0, **kwargs):
        super().__init__(designation=designation)
        self.mass_per_metre = mass_per_metre
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


class TestSectionFactoryInitialization:
    """Test SectionFactory initialization."""

    @pytest.fixture
    def mock_database(self, tmp_path):
        """Create a mock database."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        ub_data = {
            "254x146x31": {
                "designation": "254x146x31",
                "mass_per_metre": 31.0,
                "h": 254.0,
                "b": 146.0
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)

        # Use UK region which has UB in supported types
        return SectionDatabase(data_directory=data_dir, region="UK")

    def test_factory_initialization_with_classes(self, mock_database):
        """Test factory initialization with section classes."""
        section_classes = {
            SectionType.UB: MockUniversalBeam,
        }
        factory = SectionFactory(mock_database, section_classes)

        assert factory.database is mock_database
        assert isinstance(factory._section_classes, dict)
        assert SectionType.UB in factory._section_classes
        assert factory._section_classes[SectionType.UB] is MockUniversalBeam

    def test_register_section_class(self, mock_database):
        """Test manual registration of section classes."""
        factory = SectionFactory(mock_database, {})

        # Register a class
        factory.register_section_class(SectionType.UB, MockUniversalBeam)

        # Verify registration
        assert SectionType.UB in factory._section_classes
        assert factory._section_classes[SectionType.UB] is MockUniversalBeam


class TestSectionCreation:
    """Test section creation functionality."""

    @pytest.fixture
    def factory(self, tmp_path):
        """Create a factory with mock data."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        ub_data = {
            "254x146x31": {
                "designation": "254x146x31",
                "mass_per_metre": 31.0,
                "h": 254.0,
                "b": 146.0
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)

        # Use UK region which has UB in supported types
        database = SectionDatabase(data_directory=data_dir, region="UK")
        section_classes = {SectionType.UB: MockUniversalBeam}
        return SectionFactory(database, section_classes)

    def test_create_section_with_specified_type(self, factory):
        """Test creating section with explicitly specified type."""
        section = factory.create_section("254x146x31", SectionType.UB)

        assert isinstance(section, MockUniversalBeam)
        assert section.designation == "254x146x31"
        assert section.mass_per_metre == 31.0
        assert section.h == 254.0

    def test_create_section_filters_metadata(self, factory):
        """Test that metadata fields starting with '_' are filtered out."""
        section = factory.create_section("254x146x31", SectionType.UB)

        # _section_type should not be passed to constructor
        assert not hasattr(section, '_section_type')
        assert section.designation == "254x146x31"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def factory(self, tmp_path):
        """Create a factory with mock data."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        ub_data = {
            "254x146x31": {
                "designation": "254x146x31",
                "mass_per_metre": 31.0
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)

        # Use UK region which has UB in supported types
        database = SectionDatabase(data_directory=data_dir, region="UK")
        section_classes = {SectionType.UB: MockUniversalBeam}
        return SectionFactory(database, section_classes)

    def test_section_not_found_with_type(self, factory):
        """Test error when section not found with specified type."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("NONEXISTENT", SectionType.UB)

        assert "Section 'NONEXISTENT' of type 'UB' not found" in str(exc_info.value)

    def test_unregistered_section_type(self, tmp_path):
        """Test error when section type not registered."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        uc_data = {"203x203x46": {"designation": "203x203x46", "mass_per_metre": 46.0}}
        with open(data_dir / "UC.json", "w") as f:
            json.dump(uc_data, f)

        # Use UK region which has UC in supported types
        database = SectionDatabase(data_directory=data_dir, region="UK")
        # Create factory without registering UC type
        factory = SectionFactory(database, {SectionType.UB: MockUniversalBeam})

        with pytest.raises(SectionTypeNotRegisteredError) as exc_info:
            factory.create_section("203x203x46", SectionType.UC)

        assert "No registered class for section type 'UC'" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
