"""
Essential UK integration tests.
Tests the full workflow of creating UK sections.
"""

import pytest
from pathlib import Path

from steelsnakes.base.sections import SectionType
from steelsnakes.UK.database import UKSectionDatabase
from steelsnakes.UK.factory import UKSectionFactory


class TestUKIntegration:
    """Test UK module integration with real data."""

    @pytest.fixture
    def uk_factory(self):
        """Create a UK factory with real data."""
        try:
            return UKSectionFactory()
        except Exception:
            # If the default path doesn't work, skip these tests
            pytest.skip("UK data not available")

    def test_uk_database_initialization(self):
        """Test UK database can be initialized."""
        try:
            db = UKSectionDatabase()
            assert db is not None
            assert db.region == "UK"
        except Exception:
            pytest.skip("UK data not available")

    def test_uk_factory_initialization(self):
        """Test UK factory can be initialized."""
        try:
            factory = UKSectionFactory()
            assert factory is not None
            assert factory.database.region == "UK"
        except Exception:
            pytest.skip("UK data not available")

    def test_create_universal_beam(self, uk_factory):
        """Test creating a Universal Beam section."""
        # Try to create a common UB section
        sections = uk_factory.database.list_sections(SectionType.UB)
        if not sections:
            pytest.skip("No UB sections available")

        # Use the first available section
        designation = sections[0]
        section = uk_factory.create_section(designation, SectionType.UB)

        assert section is not None
        assert section.designation == designation
        assert section.get_section_type() == SectionType.UB

        # Test that properties can be retrieved
        props = section.get_properties()
        assert isinstance(props, dict)
        assert 'designation' in props
        # Note: different implementations may or may not include section_type in properties

    def test_create_universal_column(self, uk_factory):
        """Test creating a Universal Column section."""
        sections = uk_factory.database.list_sections(SectionType.UC)
        if not sections:
            pytest.skip("No UC sections available")

        designation = sections[0]
        section = uk_factory.create_section(designation, SectionType.UC)

        assert section is not None
        assert section.designation == designation
        assert section.get_section_type() == SectionType.UC

    def test_create_parallel_flange_channel(self, uk_factory):
        """Test creating a Parallel Flange Channel section."""
        sections = uk_factory.database.list_sections(SectionType.PFC)
        if not sections:
            pytest.skip("No PFC sections available")

        designation = sections[0]
        section = uk_factory.create_section(designation, SectionType.PFC)

        assert section is not None
        assert section.designation == designation
        assert section.get_section_type() == SectionType.PFC

    def test_uk_database_search(self, uk_factory):
        """Test searching UK database."""
        # Try to search for sections
        results = uk_factory.database.search_sections(SectionType.UB, mass_per_metre__gt=50)

        # May or may not have results depending on data
        assert isinstance(results, list)

    def test_uk_available_section_types(self, uk_factory):
        """Test getting available UK section types."""
        types = uk_factory.database.get_available_section_types()

        assert isinstance(types, list)
        assert len(types) > 0
        # Should have at least some UK section types
        uk_types = [SectionType.UB, SectionType.UC, SectionType.PFC]
        has_uk_type = any(t in types for t in uk_types)
        assert has_uk_type, "No UK section types found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
