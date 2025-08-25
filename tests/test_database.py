"""
Tests for the base database system including SectionDatabase.
"""

import pytest
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Optional, Any

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sections import SectionType


class MockSectionDatabase(SectionDatabase):
    """Mock implementation of SectionDatabase for testing."""
    
    def __init__(self, data_directory: Optional[Path] = None, use_sqlite: bool = False):
        # Override _resolve_data_directory to prevent it from being called during super().__init__
        self._mock_data_directory = data_directory
        super().__init__(data_directory=data_directory, use_sqlite=use_sqlite)
    
    def _resolve_data_directory(self, data_directory: Optional[Path]) -> Path:
        """Mock implementation that returns the provided directory or a default."""
        if data_directory is not None:
            return data_directory
        if self._mock_data_directory is not None:
            return self._mock_data_directory
        # Return a default path for testing
        return Path(__file__).parent / "mock_data"
    
    def get_supported_types(self) -> list[SectionType]:
        """Return mock supported section types."""
        return [SectionType.UB, SectionType.UC, SectionType.PFC, SectionType.L_EQUAL]
    
    def _fuzzy_find_section(self, designation: str) -> Optional[tuple[SectionType, dict[str, Any]]]:
        """Mock fuzzy find implementation."""
        # Simple case-insensitive search
        designation_lower = designation.lower()
        for section_type in self.get_supported_types():
            sections = self._cache.get(section_type, {})
            for designation_key, data in sections.items():
                if designation_key.lower() == designation_lower:
                    return section_type, data
        return None


# Global fixtures that can be used by all test classes
@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary data directory with mock JSON files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create mock UB.json
    ub_data = {
        "457x191x67": {
            "mass_per_metre": 67.1,
            "h": 457.0,
            "b": 191.0,
            "I_yy": 21500.0,
            "designation": "457x191x67"
        },
        "305x305x137": {
            "mass_per_metre": 137.0,
            "h": 305.0,
            "b": 305.0,
            "I_yy": 29000.0,
            "designation": "305x305x137"
        }
    }
    with open(data_dir / "UB.json", "w") as f:
        json.dump(ub_data, f)
    
    # Create mock UC.json
    uc_data = {
        "203x203x46": {
            "mass_per_metre": 46.0,
            "h": 203.1,
            "b": 203.6,
            "I_yy": 5700.0,
            "designation": "203x203x46"
        }
    }
    with open(data_dir / "UC.json", "w") as f:
        json.dump(uc_data, f)
    
    # Create mock PFC.json
    pfc_data = {
        "430x100x64": {
            "mass_per_metre": 64.0,
            "h": 430.0,
            "b": 100.0,
            "I_yy": 12500.0,
            "designation": "430x100x64"
        }
    }
    with open(data_dir / "PFC.json", "w") as f:
        json.dump(pfc_data, f)
    
    return data_dir


@pytest.fixture
def database(mock_data_dir):
    """Create a mock database instance."""
    return MockSectionDatabase(data_directory=mock_data_dir)


class TestSectionDatabase:
    """Test the SectionDatabase abstract base class."""


class TestSectionDatabaseInitialization:
    """Test SectionDatabase initialization and setup."""
    
    def test_database_init_with_directory(self, mock_data_dir):
        """Test database initialization with specific directory."""
        db = MockSectionDatabase(data_directory=mock_data_dir)
        assert db.data_directory == mock_data_dir
        assert not db.use_sqlite
        assert isinstance(db._cache, dict)
    
    def test_database_init_with_sqlite_enabled(self, mock_data_dir):
        """Test database initialization with SQLite enabled."""
        db = MockSectionDatabase(data_directory=mock_data_dir, use_sqlite=True)
        assert db.use_sqlite is True
    
    def test_database_init_nonexistent_directory(self, tmp_path):
        """Test database initialization with non-existent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        db = MockSectionDatabase(data_directory=nonexistent_dir)
        # Should not raise an error, but cache should be empty
        assert db.data_directory == nonexistent_dir
        assert all(not sections for sections in db._cache.values())
    
    def test_supported_types_method(self, database):
        """Test get_supported_types method."""
        types = database.get_supported_types()
        assert SectionType.UB in types
        assert SectionType.UC in types
        assert SectionType.PFC in types
        assert SectionType.L_EQUAL in types


class TestSectionLoading:
    """Test section loading methods."""
    
    def test_load_section_type_json_exists(self, database):
        """Test loading section type when JSON file exists."""
        data = database._load_section_type(SectionType.UB)
        assert data is not None
        assert "457x191x67" in data
        assert data["457x191x67"]["mass_per_metre"] == 67.1
    
    def test_load_section_type_json_not_exists(self, database):
        """Test loading section type when JSON file doesn't exist."""
        data = database._load_section_type(SectionType.L_EQUAL)
        assert data is None
    
    def test_load_sections_populates_cache(self, database):
        """Test that _load_sections populates the cache correctly."""
        # Cache should already be populated from __init__
        assert SectionType.UB in database._cache
        assert SectionType.UC in database._cache
        assert SectionType.PFC in database._cache
        
        # Check that metadata was added
        ub_data = database._cache[SectionType.UB]["457x191x67"]
        assert ub_data["_section_type"] == "UB"
    
    def test_load_sections_handles_errors(self, tmp_path):
        """Test that _load_sections handles errors gracefully."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create invalid JSON file
        with open(data_dir / "UB.json", "w") as f:
            f.write("invalid json content")
        
        db = MockSectionDatabase(data_directory=data_dir)
        # Should not raise an error, but UB cache should be empty
        assert db._cache.get(SectionType.UB, {}) == {}


class TestDataRetrieval:
    """Test data retrieval methods."""
    
    def test_get_section_data_exists(self, database):
        """Test getting section data that exists."""
        data = database.get_section_data("457x191x67", SectionType.UB)
        assert data is not None
        assert data["mass_per_metre"] == 67.1
        assert data["h"] == 457.0
        assert data["_section_type"] == "UB"
    
    def test_get_section_data_not_exists(self, database):
        """Test getting section data that doesn't exist."""
        data = database.get_section_data("999x999x999", SectionType.UB)
        assert data is None
    
    def test_get_section_data_wrong_type(self, database):
        """Test getting section data with wrong section type."""
        data = database.get_section_data("457x191x67", SectionType.PFC)
        assert data is None
    
    def test_find_section_exact_match(self, database):
        """Test finding section with exact match."""
        result = database.find_section("457x191x67")
        assert result is not None
        section_type, data = result
        assert section_type == SectionType.UB
        assert data["mass_per_metre"] == 67.1
    
    def test_find_section_fuzzy_match(self, database):
        """Test finding section with fuzzy matching."""
        result = database.find_section("457X191X67")  # Different case
        assert result is not None
        section_type, data = result
        assert section_type == SectionType.UB
        assert data["mass_per_metre"] == 67.1
    
    def test_find_section_not_found(self, database):
        """Test finding section that doesn't exist."""
        result = database.find_section("999x999x999")
        assert result is None


class TestSectionSearch:
    """Test search functionality."""
    
    def test_search_sections_exact_match(self, database):
        """Test searching sections with exact match criteria."""
        results = database.search_sections(SectionType.UB, h=457.0)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
        assert data["h"] == 457.0
    
    def test_search_sections_greater_than(self, database):
        """Test searching sections with greater than criteria."""
        results = database.search_sections(SectionType.UB, mass_per_metre__gt=100)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "305x305x137"
        assert data["mass_per_metre"] == 137.0
    
    def test_search_sections_less_than(self, database):
        """Test searching sections with less than criteria."""
        results = database.search_sections(SectionType.UB, mass_per_metre__lt=100)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
        assert data["mass_per_metre"] == 67.1
    
    def test_search_sections_greater_than_equal(self, database):
        """Test searching sections with greater than or equal criteria."""
        results = database.search_sections(SectionType.UB, mass_per_metre__gte=137.0)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "305x305x137"
    
    def test_search_sections_less_than_equal(self, database):
        """Test searching sections with less than or equal criteria."""
        results = database.search_sections(SectionType.UB, mass_per_metre__lte=67.1)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
    
    def test_search_sections_not_equal(self, database):
        """Test searching sections with not equal criteria."""
        results = database.search_sections(SectionType.UB, mass_per_metre__ne=67.1)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "305x305x137"
    
    def test_search_sections_equal_operator(self, database):
        """Test searching sections with explicit equal operator."""
        results = database.search_sections(SectionType.UB, mass_per_metre__eq=67.1)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
    
    def test_search_sections_multiple_criteria(self, database):
        """Test searching sections with multiple criteria."""
        results = database.search_sections(SectionType.UB, h=457.0, b=191.0)
        assert len(results) == 1
        designation, data = results[0]
        assert designation == "457x191x67"
    
    def test_search_sections_no_results(self, database):
        """Test searching sections with criteria that match nothing."""
        results = database.search_sections(SectionType.UB, h=999.0)
        assert len(results) == 0
    
    def test_search_sections_unknown_operator(self, database):
        """Test searching sections with unknown operator."""
        # Should skip unknown operators
        results = database.search_sections(SectionType.UB, mass_per_metre__unknown=67.1)
        # Should return all sections since unknown operator is ignored
        assert len(results) == 2
    
    def test_search_sections_type_error(self, database):
        """Test searching sections with comparison type error."""
        # Try to compare string with number
        results = database.search_sections(SectionType.UB, designation__gt=100)
        # Should return no results due to type error
        assert len(results) == 0


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_list_sections(self, database):
        """Test listing sections for a given type."""
        sections = database.list_sections(SectionType.UB)
        assert "457x191x67" in sections
        assert "305x305x137" in sections
        assert len(sections) == 2
    
    def test_list_sections_empty_type(self, database):
        """Test listing sections for empty type."""
        sections = database.list_sections(SectionType.L_EQUAL)
        assert len(sections) == 0
    
    def test_get_available_section_types(self, database):
        """Test getting available section types."""
        types = database.get_available_section_types()
        assert SectionType.UB in types
        assert SectionType.UC in types  
        assert SectionType.PFC in types
        # L_EQUAL should not be included as it has no data
        assert SectionType.L_EQUAL not in types


class TestSQLiteFunctionality:
    """Test SQLite-related functionality."""
    
    def test_get_sqlite_db_path(self, database):
        """Test SQLite database path generation."""
        sqlite_path = database._get_sqlite_db_path()
        expected_name = f"{database.data_directory.name}_sections.sqlite3"
        assert sqlite_path.name == expected_name
        assert sqlite_path.parent == database.data_directory.parent
    
    def test_get_sqlite_db_path_caching(self, database):
        """Test that SQLite database path is cached."""
        path1 = database._get_sqlite_db_path()
        path2 = database._get_sqlite_db_path()
        assert path1 == path2
        assert database._sqlite_db_path == path1
    
    @patch('steelsnakes.base.database.logger')
    def test_ensure_sqlite_database_exists(self, mock_logger, database, tmp_path):
        """Test ensuring SQLite database exists when it already does."""
        # Create a mock SQLite file
        sqlite_path = tmp_path / "test.sqlite3"
        sqlite_path.touch()
        database._sqlite_db_path = sqlite_path
        
        result = database._ensure_sqlite_database()
        assert result is True
    
    @patch('steelsnakes.base.database.logger')
    @patch.object(MockSectionDatabase, '_build_sqlite_from_json')
    def test_ensure_sqlite_database_creates(self, mock_build, mock_logger, database, tmp_path):
        """Test ensuring SQLite database creates when it doesn't exist."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        result = database._ensure_sqlite_database()
        assert result is True
        mock_build.assert_called_once()
    
    @patch('steelsnakes.base.database.logger')
    @patch.object(MockSectionDatabase, '_build_sqlite_from_json')
    def test_ensure_sqlite_database_build_fails(self, mock_build, mock_logger, database, tmp_path):
        """Test ensuring SQLite database handles build failure."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        mock_build.side_effect = Exception("Build failed")
        
        result = database._ensure_sqlite_database()
        assert result is False
        mock_logger.error.assert_called_once()
    
    def test_build_sqlite_database_manual(self, database, tmp_path):
        """Test manually building SQLite database."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        with patch.object(database, '_ensure_sqlite_database', return_value=True):
            result_path = database.build_sqlite_database()
            assert result_path == sqlite_path
    
    def test_build_sqlite_database_force_rebuild(self, database, tmp_path):
        """Test force rebuilding SQLite database."""
        sqlite_path = tmp_path / "test.sqlite3"
        sqlite_path.touch()  # Create existing file
        database._sqlite_db_path = sqlite_path
        
        with patch.object(database, '_ensure_sqlite_database', return_value=True):
            result_path = database.build_sqlite_database(force_rebuild=True)
            assert result_path == sqlite_path
    
    def test_build_sqlite_database_fails(self, database, tmp_path):
        """Test building SQLite database when creation fails."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        with patch.object(database, '_ensure_sqlite_database', return_value=False):
            with pytest.raises(RuntimeError, match="Failed to create SQLite database"):
                database.build_sqlite_database()
    
    @patch('steelsnakes.base.database.logger')
    def test_load_from_sqlite_success(self, mock_logger, database, tmp_path):
        """Test loading from SQLite database successfully."""
        # Create a mock SQLite database
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        # Create the SQLite database with test data
        with sqlite3.connect(sqlite_path) as conn:
            conn.execute("""
                CREATE TABLE UB (
                    id INTEGER PRIMARY KEY,
                    designation TEXT,
                    data TEXT
                )
            """)
            conn.execute("""
                INSERT INTO UB (designation, data) VALUES 
                ('test_section', '{"mass_per_metre": 50.0, "h": 200.0}')
            """)
            conn.commit()
        
        result = database._load_from_sqlite(SectionType.UB)
        assert result is not None
        assert "test_section" in result
        assert result["test_section"]["mass_per_metre"] == 50.0
    
    @patch('steelsnakes.base.database.logger')
    def test_load_from_sqlite_table_not_exists(self, mock_logger, database, tmp_path):
        """Test loading from SQLite when table doesn't exist."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        # Create empty SQLite database
        with sqlite3.connect(sqlite_path) as conn:
            conn.execute("SELECT 1")  # Just create the database
        
        with patch.object(database, '_ensure_sqlite_database', return_value=True):
            result = database._load_from_sqlite(SectionType.UB)
            assert result is None
    
    @patch('steelsnakes.base.database.logger')
    def test_load_from_sqlite_error(self, mock_logger, database, tmp_path):
        """Test loading from SQLite with database error."""
        sqlite_path = tmp_path / "test.sqlite3"
        database._sqlite_db_path = sqlite_path
        
        # Create a corrupted SQLite database that will cause an error
        with open(sqlite_path, 'w') as f:
            f.write("this is not a valid sqlite database")
        
        with patch.object(database, '_ensure_sqlite_database', return_value=True):
            result = database._load_from_sqlite(SectionType.UB)
            assert result is None
            mock_logger.error.assert_called_once()


class TestAlternativeFormats:
    """Test alternative format loading."""
    
    def test_try_alternative_formats_default(self, database):
        """Test that default implementation returns None."""
        result = database._try_alternative_formats(SectionType.UB)
        assert result is None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_file(self, tmp_path):
        """Test handling of invalid JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create invalid JSON file
        with open(data_dir / "UB.json", "w") as f:
            f.write("{ invalid json content")
        
        # Should not raise an error
        db = MockSectionDatabase(data_directory=data_dir)
        assert SectionType.UB in db._cache
        assert len(db._cache[SectionType.UB]) == 0
    
    def test_empty_data_directory(self, tmp_path):
        """Test handling of empty data directory."""
        data_dir = tmp_path / "empty_data"
        data_dir.mkdir()
        
        db = MockSectionDatabase(data_directory=data_dir)
        # Should have empty cache for all types
        for section_type in db.get_supported_types():
            assert len(db._cache.get(section_type, {})) == 0


if __name__ == "__main__":
    pytest.main([__file__])