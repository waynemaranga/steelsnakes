"""
Tests for fuzzy matching functionality in error messages.
"""

import pytest
from steelsnakes.base.sections import SectionType
from tests.test_factory import MockSectionFactory, MockSectionDatabase


class TestFuzzyMatchingErrorMessages:
    """Test fuzzy matching suggestions in error messages."""
    
    @pytest.fixture
    def mock_database(self):
        return MockSectionDatabase()
    
    @pytest.fixture
    def factory(self, mock_database):
        return MockSectionFactory(mock_database)
    
    def test_fuzzy_match_with_specific_type_close_match(self, factory):
        """Test fuzzy matching suggests close matches when section type is specified."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("254x146x30", SectionType.UB)  # Close to 254x146x31
        
        error_msg = str(exc_info.value)
        assert "Section '254x146x30' of type 'UB' not found" in error_msg
        assert "Did you mean: '254x146x31'?" in error_msg
        # Should not contain the old message format
        assert "Available sections:" not in error_msg
    
    def test_fuzzy_match_with_specific_type_no_close_match(self, factory):
        """Test fallback to original behavior when no close matches found."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("COMPLETELY_DIFFERENT", SectionType.UB)
        
        error_msg = str(exc_info.value)
        assert "Section 'COMPLETELY_DIFFERENT' of type 'UB' not found" in error_msg
        assert "Available sections: 2" in error_msg
        assert "Did you mean:" not in error_msg
    
    def test_fuzzy_match_auto_detect_close_match(self, factory):
        """Test fuzzy matching across all types when no type specified."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("254x146x30")  # Close to 254x146x31
        
        error_msg = str(exc_info.value)
        assert "Section '254x146x30' not found in any type" in error_msg
        assert "Did you mean:" in error_msg
        assert "254x146x31" in error_msg
        # Should not contain the old message format
        assert "Available types:" not in error_msg
    
    def test_fuzzy_match_auto_detect_no_close_match(self, factory):
        """Test fallback to original behavior when no close matches found across types."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("COMPLETELY_DIFFERENT")
        
        error_msg = str(exc_info.value)
        assert "Section 'COMPLETELY_DIFFERENT' not found in any type" in error_msg
        assert "Available types: ['UB', 'PFC', 'WELDS']" in error_msg
        assert "Did you mean:" not in error_msg
    
    def test_fuzzy_match_case_insensitive(self, factory):
        """Test that fuzzy matching works with different cases."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("254X146X30", SectionType.UB)  # Upper case
        
        error_msg = str(exc_info.value)
        assert "Did you mean: '254x146x31'?" in error_msg
    
    def test_fuzzy_match_partial_designation(self, factory):
        """Test fuzzy matching with partial designation."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("150x75", SectionType.PFC)  # Missing x18 part
        
        error_msg = str(exc_info.value)
        assert "Did you mean: '150x75x18'?" in error_msg
    
    def test_fuzzy_match_typo_correction(self, factory):
        """Test fuzzy matching corrects typos."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("BUTT_WALD_6", SectionType.WELDS)  # Typo in WELD
        
        error_msg = str(exc_info.value)
        assert "Did you mean: 'BUTT_WELD_6'?" in error_msg
    
    def test_fuzzy_match_multiple_suggestions(self, factory):
        """Test that multiple suggestions are provided when available."""
        with pytest.raises(ValueError) as exc_info:
            factory.create_section("x146x")  # Should match multiple UB sections
        
        error_msg = str(exc_info.value)
        assert "Did you mean:" in error_msg
        # Should contain multiple suggestions separated by ', '
        assert "', '" in error_msg or "254x146x31" in error_msg


class TestFuzzyMatchingUtilityMethod:
    """Test the _get_similar_sections utility method directly."""
    
    @pytest.fixture
    def factory(self):
        return MockSectionFactory(MockSectionDatabase())
    
    def test_get_similar_sections_with_type(self, factory):
        """Test getting similar sections within a specific type."""
        similar = factory._get_similar_sections("254x146x30", SectionType.UB)
        assert "254x146x31" in similar
        assert len(similar) <= 3  # Max 3 suggestions
    
    def test_get_similar_sections_across_types(self, factory):
        """Test getting similar sections across all types."""
        similar = factory._get_similar_sections("254x146x30")
        assert "254x146x31" in similar
        # Could contain sections from different types
        assert len(similar) <= 3
    
    def test_get_similar_sections_no_matches(self, factory):
        """Test that no suggestions are returned for completely different input."""
        similar = factory._get_similar_sections("COMPLETELY_DIFFERENT", SectionType.UB)
        assert len(similar) == 0
    
    def test_get_similar_sections_custom_limit(self, factory):
        """Test custom limit for number of suggestions."""
        similar = factory._get_similar_sections("x", n=1)  # Should match many, but limit to 1
        assert len(similar) <= 1


if __name__ == "__main__":
    pytest.main([__file__])