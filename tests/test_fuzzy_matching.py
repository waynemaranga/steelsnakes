"""
Tests for fuzzy matching functionality in error messages.
"""

import pytest
import json

from steelsnakes.base.sections import SectionType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.exceptions import SectionNotFoundError


@pytest.fixture
def mock_database(tmp_path):
    """Create a UK database with two UB and two PFC sections."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    ub_data = {
        "254x146x31": {"designation": "254x146x31", "mass_per_metre": 31.1},
        "254x146x37": {"designation": "254x146x37", "mass_per_metre": 37.0},
    }
    with open(data_dir / "UB.json", "w") as f:
        json.dump(ub_data, f)

    pfc_data = {
        "150x75x18": {"designation": "150x75x18", "mass_per_metre": 17.9},
        "180x75x20": {"designation": "180x75x20", "mass_per_metre": 20.3},
    }
    with open(data_dir / "PFC.json", "w") as f:
        json.dump(pfc_data, f)

    return SectionDatabase(data_directory=data_dir, region="UK")


@pytest.fixture
def factory(mock_database):
    return SectionFactory(mock_database)


class TestFuzzyMatchingErrorMessages:
    """Test fuzzy matching suggestions in error messages."""

    def test_fuzzy_match_with_specific_type_close_match(self, factory):
        """Test fuzzy matching suggests close matches when section type is specified."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("254x146x30", SectionType.UB)  # Close to 254x146x31

        error_msg = str(exc_info.value)
        assert "Section '254x146x30' of type 'UB' not found" in error_msg
        assert "\nSimilar sections: " in error_msg
        assert "'254x146x31'" in error_msg
        # Suggestions replace the section count
        assert "Available sections:" not in error_msg

    def test_fuzzy_match_with_specific_type_no_close_match(self, factory):
        """Test fallback to the section count when no close matches found."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("COMPLETELY_DIFFERENT", SectionType.UB)

        error_msg = str(exc_info.value)
        assert "Section 'COMPLETELY_DIFFERENT' of type 'UB' not found" in error_msg
        assert "Available sections: 2 total" in error_msg
        assert "Similar sections:" not in error_msg

    def test_fuzzy_match_auto_detect_ambiguous_typo_raises(self, factory):
        """Test a typo equally close to two sections is not silently resolved to either."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("254x146x30")  # as close to 254x146x31 as to 254x146x37

        error_msg = str(exc_info.value)
        assert "Section '254x146x30' not found in any type" in error_msg
        assert "\nSimilar sections: " in error_msg
        assert "254x146x31" in error_msg
        assert "254x146x37" in error_msg
        # Suggestions replace the list of types
        assert "Available types:" not in error_msg

    def test_fuzzy_match_auto_detect_unambiguous_typo_resolves(self, factory):
        """Test auto-detection still resolves a typo with one clear nearest match."""
        section = factory.create_section("15Ox75x18")  # letter O for zero
        assert section.designation == "150x75x18"
        assert section.get_section_type() == SectionType.PFC

    def test_fuzzy_match_auto_detect_no_close_match(self, factory):
        """Test fallback to the list of types when no close matches found across types."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("COMPLETELY_DIFFERENT")

        error_msg = str(exc_info.value)
        assert "Section 'COMPLETELY_DIFFERENT' not found in any type" in error_msg
        assert "Available types: ['UB', 'PFC']" in error_msg
        assert "Similar sections:" not in error_msg

    def test_fuzzy_match_case_insensitive(self, factory):
        """Test that fuzzy matching works with different cases."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("254X146X30", SectionType.UB)  # Upper case

        assert "'254x146x31'" in str(exc_info.value)

    def test_fuzzy_match_partial_designation(self, factory):
        """Test fuzzy matching with partial designation."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("150x75", SectionType.PFC)  # Missing x18 part

        assert "\nSimilar sections: '150x75x18'" in str(exc_info.value)

    def test_fuzzy_match_typo_correction(self, factory):
        """Test fuzzy matching corrects typos."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("15Ox75x18", SectionType.PFC)  # letter O for zero

        assert "\nSimilar sections: '150x75x18'" in str(exc_info.value)

    def test_fuzzy_match_multiple_suggestions(self, factory):
        """Test that multiple suggestions are provided when available."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("x146x")  # Should match both UB sections

        error_msg = str(exc_info.value)
        assert "\nSimilar sections: " in error_msg
        assert "', '" in error_msg

    def test_wrong_type_exact_match_cross_type_note(self, factory):
        """If designation exists under different type, error should mention that type."""
        # Use a PFC designation but ask for UB
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("150x75x18", SectionType.UB)

        msg = str(exc_info.value)
        assert "Section '150x75x18' of type 'UB' not found" in msg
        assert "\nNote: '150x75x18' exists as type 'PFC'." in msg

    def test_wrong_type_case_insensitive_cross_type_note(self, factory):
        """Cross-type note should work case-insensitively."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            factory.create_section("150X75X18", SectionType.UB)

        assert "\nNote: '150X75X18' exists as type 'PFC'." in str(exc_info.value)

    def test_section_not_found_is_a_value_error(self, factory):
        """Test callers catching ValueError still catch missing sections."""
        with pytest.raises(ValueError):
            factory.create_section("COMPLETELY_DIFFERENT", SectionType.UB)


class TestFuzzyMatchingUtilityMethod:
    """Test the get_similar_sections utility method directly."""

    def test_get_similar_sections_with_type(self, mock_database):
        """Test getting similar sections within a specific type."""
        similar = mock_database.get_similar_sections("254x146x30", SectionType.UB)
        assert "254x146x31" in similar
        assert len(similar) <= 5  # Max 5 suggestions by default

    def test_get_similar_sections_across_types(self, mock_database):
        """Test getting similar sections across all types."""
        similar = mock_database.get_similar_sections("254x146x30")
        assert "254x146x31" in similar
        # PFC sections are too far away to be suggested
        assert "150x75x18" not in similar

    def test_get_similar_sections_no_matches(self, mock_database):
        """Test that no suggestions are returned for completely different input."""
        assert mock_database.get_similar_sections("COMPLETELY_DIFFERENT", SectionType.UB) == []

    def test_get_similar_sections_custom_limit(self, mock_database):
        """Test custom limit for number of suggestions."""
        similar = mock_database.get_similar_sections("254x146x3", n=1)  # Matches both UB sections, limited to 1
        assert len(similar) == 1


class TestFuzzyFindSection:
    """Test the matching strategies behind find_section()."""

    @pytest.mark.parametrize(
        ("designation", "expected"),
        [
            ("150X75X18", "150x75x18"),  # case-insensitive
            ("150 x 75 x 18", "150x75x18"),  # spaces ignored
            ("150×75×18", "150x75x18"),  # multiplication sign
            ("15Ox75x18", "150x75x18"),  # letter O for zero; one clear nearest match
        ],
    )
    def test_find_section_resolves(self, mock_database, designation, expected):
        """Test find_section() resolves unambiguous variants of a designation."""
        result = mock_database.find_section(designation)
        assert result is not None
        _, data = result
        assert data["designation"] == expected

    @pytest.mark.parametrize("designation", ["254x146x30", "254x146x3l"])
    def test_find_section_rejects_ambiguous_match(self, mock_database, designation):
        """Test find_section() returns None when 254x146x31 and 254x146x37 are equally close."""
        assert mock_database.find_section(designation) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
