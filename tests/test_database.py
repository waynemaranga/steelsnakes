"""
Essential tests for the base database system.
Tests SectionDatabase initialization and basic operations.
"""

import pytest
import json
from pathlib import Path
from typing import Optional, Any

from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.sqlite3db import build_regional_sqlite_db
from steelsnakes.base.sections import SectionType


class TestSectionDatabaseInitialization:
    """Test SectionDatabase initialization and setup."""

    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create a temporary data directory with mock JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create mock UB.json
        ub_data = {
            "457x191x67": {
                "mass_per_metre": 67.1,
                "h": 457.0,
                "b": 191.0,
                "designation": "457x191x67"
            },
            "305x305x137": {
                "mass_per_metre": 137.0,
                "h": 305.0,
                "b": 305.0,
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
                "designation": "203x203x46"
            }
        }
        with open(data_dir / "UC.json", "w") as f:
            json.dump(uc_data, f)

        return data_dir

    def test_database_init_with_directory(self, mock_data_dir):
        """Test database initialization with specific directory."""
        db = SectionDatabase(data_directory=mock_data_dir, region="UK")
        assert db.data_directory == mock_data_dir.resolve()
        assert not db.use_sqlite
        assert isinstance(db._cache, dict)

    def test_database_init_region(self, mock_data_dir):
        """Test database initialization stores region."""
        db = SectionDatabase(data_directory=mock_data_dir, region="UK")
        assert db.region == "UK"

    def test_supported_types_method(self, mock_data_dir):
        """Test get_supported_types method."""
        db = SectionDatabase(data_directory=mock_data_dir, region="UK")
        types = db.get_supported_types()
        assert isinstance(types, list)
        assert len(types) > 0
        assert SectionType.UB in types
        assert SectionType.UC in types


class TestDataRetrieval:
    """Test data retrieval methods."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create a database instance with mock data."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        ub_data = {
            "457x191x67": {
                "mass_per_metre": 67.1,
                "h": 457.0,
                "b": 191.0,
                "designation": "457x191x67"
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)

        return SectionDatabase(data_directory=data_dir, region="UK")

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

    def test_list_sections(self, database):
        """Test listing sections for a given type."""
        sections = database.list_sections(SectionType.UB)
        assert "457x191x67" in sections
        assert isinstance(sections, list)

    def test_get_available_section_types(self, database):
        """Test getting available section types."""
        types = database.get_available_section_types()
        assert SectionType.UB in types
        assert isinstance(types, list)


class TestSearchFunctionality:
    """Test search functionality."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create a database with multiple sections."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        ub_data = {
            "457x191x67": {
                "mass_per_metre": 67.1,
                "h": 457.0,
                "designation": "457x191x67"
            },
            "305x305x137": {
                "mass_per_metre": 137.0,
                "h": 305.0,
                "designation": "305x305x137"
            }
        }
        with open(data_dir / "UB.json", "w") as f:
            json.dump(ub_data, f)

        return SectionDatabase(data_directory=data_dir, region="UK")

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

    def test_search_sections_no_results(self, database):
        """Test searching sections with criteria that match nothing."""
        results = database.search_sections(SectionType.UB, h=999.0)
        assert len(results) == 0


class TestSQLiteFallback:
    """Test the experimental SQLite fallback for section types without a JSON file."""

    @pytest.fixture
    def sqlite_db_path(self, tmp_path):
        """Build a SQLite database from a JSON directory holding one UC section."""
        json_dir = tmp_path / "json"
        json_dir.mkdir()
        uc_data = {"203x203x46": {"designation": "203x203x46", "mass_per_metre": 46.1, "h": 203.2}}
        with open(json_dir / "UC.json", "w") as f:
            json.dump(uc_data, f)

        return build_regional_sqlite_db(tmp_path / "sqlite" / "TABLES.db", json_dir)

    @pytest.fixture
    def empty_data_dir(self, tmp_path):
        """Create a data directory with no JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return data_dir

    def test_sqlite_db_path_is_honoured(self, empty_data_dir, sqlite_db_path):
        """Test sections load from the injected SQLite database when their JSON file is missing."""
        db = SectionDatabase(data_directory=empty_data_dir, region="UK", use_sqlite=True, sqlite_db_path=sqlite_db_path)

        data = db.get_section_data("203x203x46", SectionType.UC)
        assert data is not None
        assert data["mass_per_metre"] == 46.1  # original JSON keys, not the lower-cased SQLite columns
        assert data["_section_type"] == "UC"

    def test_sqlite_ignored_unless_enabled(self, empty_data_dir, sqlite_db_path):
        """Test the SQLite database is not read when use_sqlite is False."""
        db = SectionDatabase(data_directory=empty_data_dir, region="UK", sqlite_db_path=sqlite_db_path)
        assert db.get_section_data("203x203x46", SectionType.UC) is None

    def test_missing_sqlite_file_is_not_created(self, empty_data_dir, tmp_path):
        """Test a missing SQLite path loads nothing, and no empty database is left behind."""
        missing_path = tmp_path / "missing.db"
        db = SectionDatabase(data_directory=empty_data_dir, region="UK", use_sqlite=True, sqlite_db_path=missing_path)

        assert db.get_available_section_types() == []
        assert not missing_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
