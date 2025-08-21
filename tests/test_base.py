"""
Tests for the base section system including SectionType, BaseSection, 
SectionDatabase, and SectionFactory.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

from steelsnakes.core.sections.UK.Base import (
    SectionType, 
    BaseSection, 
    SectionDatabase, 
    SectionFactory,
    get_database,
    get_factory
)


class TestSectionType:
    """Test the SectionType enumeration."""
    
    def test_section_type_values(self):
        """Test that SectionType enum has expected values."""
        assert SectionType.UB == "UB"
        assert SectionType.UC == "UC"
        assert SectionType.PFC == "PFC"
        assert SectionType.L_EQUAL == "L_EQUAL"
        assert SectionType.CFCHS == "CFCHS"
        assert SectionType.HFCHS == "HFCHS"
        assert SectionType.WELDS == "WELDS"
    
    def test_section_type_count(self):
        """Test that we have the expected number of section types."""
        # Should have 18 section types based on the codebase
        section_types = list(SectionType)
        assert len(section_types) >= 15  # At least 15 types


class MockSection(BaseSection):
    """Mock section class for testing."""
    
    def __init__(self, designation: str, mass_per_metre: float = 50.0, **kwargs):
        self.designation = designation
        self.mass_per_metre = mass_per_metre
        # Accept any additional kwargs to match database data
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UB


class TestBaseSection:
    """Test the BaseSection abstract base class."""
    
    def test_base_section_creation(self):
        """Test creating a mock section."""
        section = MockSection("457x191x67")
        assert section.designation == "457x191x67"
        assert section.mass_per_metre == 50.0
    
    def test_base_section_str(self):
        """Test string representation."""
        section = MockSection("457x191x67")
        assert str(section) == "457x191x67"
    
    def test_base_section_repr(self):
        """Test repr representation."""
        section = MockSection("457x191x67")
        assert "MockSection" in repr(section)
        assert "457x191x67" in repr(section)
    
    def test_from_dict(self):
        """Test creating section from dictionary."""
        data = {"designation": "457x191x67", "mass_per_metre": 67.1}
        section = MockSection.from_dict(data)
        assert section.designation == "457x191x67"
        assert section.mass_per_metre == 67.1


class TestSectionDatabase:
    """Test the SectionDatabase class."""
    
    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create a temporary data directory with mock JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create mock UB.json
        ub_data = {
            "457x191x67": {
                "mass_per_metre": 67.1,
                "h": 457,
                "b": 191,
                "I_yy": 21500.0
            },
            "305x305x137": {
                "mass_per_metre": 137.0,
                "h": 305,
                "b": 305,
                "I_yy": 29000.0
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)
        
        # Create mock PFC.json
        pfc_data = {
            "430x100x64": {
                "mass_per_metre": 64.0,
                "h": 430,
                "b": 100,
                "I_yy": 12500.0
            }
        }
        with open(data_dir / "PFC.json", "w") as f:
            json.dump(pfc_data, f)
        
        return data_dir
    
    def test_database_init_with_directory(self, mock_data_dir):
        """Test database initialization with specific directory."""
        db = SectionDatabase(mock_data_dir)
        assert db.data_directory == mock_data_dir
    
    def test_database_loads_sections(self, mock_data_dir):
        """Test that database loads sections from JSON files."""
        db = SectionDatabase(mock_data_dir)
        
        # Check UB sections loaded
        ub_sections = db.list_sections(SectionType.UB)
        assert "457x191x67" in ub_sections
        assert "305x305x137" in ub_sections
        
        # Check PFC sections loaded
        pfc_sections = db.list_sections(SectionType.PFC)
        assert "430x100x64" in pfc_sections
    
    def test_get_section_data(self, mock_data_dir):
        """Test getting specific section data."""
        db = SectionDatabase(mock_data_dir)
        
        data = db.get_section_data(SectionType.UB, "457x191x67")
        assert data is not None
        assert data["mass_per_metre"] == 67.1
        assert data["h"] == 457
        assert data["section_type"] == SectionType.UB
    
    def test_find_section(self, mock_data_dir):
        """Test finding section across all types."""
        db = SectionDatabase(mock_data_dir)
        
        result = db.find_section("457x191x67")
        assert result is not None
        section_type, data = result
        assert section_type == SectionType.UB
        assert data["mass_per_metre"] == 67.1
    
    def test_find_section_not_found(self, mock_data_dir):
        """Test finding non-existent section."""
        db = SectionDatabase(mock_data_dir)
        
        result = db.find_section("999x999x999")
        assert result is None
    
    def test_search_sections_greater_than(self, mock_data_dir):
        """Test searching sections with greater than criteria."""
        db = SectionDatabase(mock_data_dir)
        
        results = db.search_sections(SectionType.UB, mass_per_metre__gt=100)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "305x305x137"
    
    def test_search_sections_less_than(self, mock_data_dir):
        """Test searching sections with less than criteria."""
        db = SectionDatabase(mock_data_dir)
        
        results = db.search_sections(SectionType.UB, mass_per_metre__lt=100)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
    
    def test_search_sections_exact_match(self, mock_data_dir):
        """Test searching sections with exact match."""
        db = SectionDatabase(mock_data_dir)
        
        results = db.search_sections(SectionType.UB, h=457)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
    
    def test_get_available_types(self, mock_data_dir):
        """Test getting available section types."""
        db = SectionDatabase(mock_data_dir)
        
        types = db.get_available_types()
        assert SectionType.UB in types
        assert SectionType.PFC in types
        # Types without data files should not be included
        assert len(types) == 2


class TestSectionFactory:
    """Test the SectionFactory class."""
    
    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create a temporary data directory with mock JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create mock UB.json
        ub_data = {
            "457x191x67": {
                "mass_per_metre": 67.1,
                "h": 457,
                "b": 191,
                "I_yy": 21500.0
            },
            "305x305x137": {
                "mass_per_metre": 137.0,
                "h": 305,
                "b": 305,
                "I_yy": 29000.0
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)
        
        # Create mock PFC.json
        pfc_data = {
            "430x100x64": {
                "mass_per_metre": 64.0,
                "h": 430,
                "b": 100,
                "I_yy": 12500.0
            }
        }
        with open(data_dir / "PFC.json", "w") as f:
            json.dump(pfc_data, f)
        
        return data_dir
    
    @pytest.fixture
    def mock_database(self, mock_data_dir):
        """Create a mock database for testing."""
        return SectionDatabase(mock_data_dir)
    
    @pytest.fixture
    def factory(self, mock_database):
        """Create a factory with mock database."""
        factory = SectionFactory(mock_database)
        factory.register_section_class(MockSection)
        return factory
    
    def test_factory_init(self, mock_database):
        """Test factory initialization."""
        factory = SectionFactory(mock_database)
        assert factory.database == mock_database
    
    def test_register_section_class(self, factory):
        """Test registering section class."""
        # MockSection should be registered from fixture
        assert SectionType.UB in factory._section_classes
        assert factory._section_classes[SectionType.UB] == MockSection
    
    def test_create_section_with_type(self, factory):
        """Test creating section with explicit type."""
        section = factory.create_section("457x191x67", SectionType.UB)
        assert isinstance(section, MockSection)
        assert section.designation == "457x191x67"
    
    def test_create_section_auto_detect(self, factory):
        """Test creating section with auto-detection."""
        section = factory.create_section("457x191x67")
        assert isinstance(section, MockSection)
        assert section.designation == "457x191x67"
    
    def test_create_section_not_found(self, factory):
        """Test creating section that doesn't exist."""
        with pytest.raises(ValueError, match="Section '999x999x999' not found"):
            factory.create_section("999x999x999", SectionType.UB)
    
    def test_create_section_type_not_registered(self, mock_database):
        """Test creating section with unregistered type."""
        factory = SectionFactory(mock_database)
        # Don't register any section classes
        
        with pytest.raises(ValueError, match="No section class registered"):
            factory.create_section("430x100x64", SectionType.PFC)


class TestGlobalFunctions:
    """Test global database and factory functions."""
    
    def test_get_database_singleton(self):
        """Test that get_database returns singleton."""
        db1 = get_database()
        db2 = get_database()
        assert db1 is db2
    
    def test_get_factory_singleton(self):
        """Test that get_factory returns singleton."""
        factory1 = get_factory()
        factory2 = get_factory()
        assert factory1 is factory2
    
    def test_get_database_with_custom_directory(self, tmp_path):
        """Test get_database with custom directory."""
        custom_db = get_database(tmp_path)
        assert custom_db.data_directory == tmp_path
    
    def test_get_factory_with_custom_directory(self, tmp_path):
        """Test get_factory with custom directory."""
        custom_factory = get_factory(tmp_path)
        assert custom_factory.database.data_directory == tmp_path
