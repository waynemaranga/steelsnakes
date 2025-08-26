"""
Tests for the SectionDataAdapter class.
"""

import pytest
from steelsnakes.base.adapter import SectionDataAdapter


class TestSectionDataAdapter:
    """Test the SectionDataAdapter data transformation functionality."""

    def test_transform_section_data_basic(self):
        """Test basic data transformation with clean data."""
        section_data = {
            'designation': 'UB_254x146x31',
            'mass_per_metre': 31.0,
            'depth': 254,
            'width': 146
        }
        designation = 'UB_254x146x31'
        
        result = SectionDataAdapter.transform_section_data(section_data, designation)
        
        assert result == section_data  # Should be unchanged
        assert result is not section_data  # Should be a copy

    def test_transform_section_data_filters_metadata(self):
        """Test that metadata fields starting with '_' are removed."""
        section_data = {
            'designation': 'UB_254x146x31',
            'mass_per_metre': 31.0,
            '_section_type': 'UB',
            '_internal_id': 123,
            'depth': 254
        }
        designation = 'UB_254x146x31'
        
        result = SectionDataAdapter.transform_section_data(section_data, designation)
        
        expected = {
            'designation': 'UB_254x146x31',
            'mass_per_metre': 31.0,
            'depth': 254
        }
        assert result == expected
        assert '_section_type' not in result
        assert '_internal_id' not in result

    def test_transform_section_data_adds_missing_designation(self):
        """Test that missing designation field is added."""
        section_data = {
            'weld_type': 'BUTT',
            'throat_thickness': 6.0,
            '_section_type': 'WELDS'
        }
        designation = 'BUTT_WELD_6'
        
        result = SectionDataAdapter.transform_section_data(section_data, designation)
        
        expected = {
            'designation': 'BUTT_WELD_6',
            'weld_type': 'BUTT',
            'throat_thickness': 6.0
        }
        assert result == expected
        assert result['designation'] == designation

    def test_transform_section_data_preserves_existing_designation(self):
        """Test that existing designation is preserved."""
        section_data = {
            'designation': 'EXISTING_DESIGNATION',
            'mass_per_metre': 31.0,
            '_metadata': 'should_be_removed'
        }
        designation = 'NEW_DESIGNATION'
        
        result = SectionDataAdapter.transform_section_data(section_data, designation)
        
        expected = {
            'designation': 'EXISTING_DESIGNATION',  # Should keep original
            'mass_per_metre': 31.0
        }
        assert result == expected
        assert result['designation'] == 'EXISTING_DESIGNATION'

    def test_transform_section_data_complex_case(self):
        """Test transformation with both metadata filtering and designation addition."""
        section_data = {
            'weld_type': 'FILLET',
            'leg_length': 8.0,
            '_section_type': 'WELDS',
            '_database_id': 456,
            '_created_at': '2023-01-01'
        }
        designation = 'FILLET_WELD_8'
        
        result = SectionDataAdapter.transform_section_data(section_data, designation)
        
        expected = {
            'designation': 'FILLET_WELD_8',
            'weld_type': 'FILLET',
            'leg_length': 8.0
        }
        assert result == expected
        assert all(not k.startswith('_') for k in result.keys())

    def test_filter_metadata_removes_underscore_fields(self):
        """Test that _filter_metadata correctly removes underscore fields."""
        data = {
            'normal_field': 'value1',
            '_metadata_field': 'value2',
            'another_field': 'value3',
            '_internal': 'value4'
        }
        
        result = SectionDataAdapter._filter_metadata(data)
        
        expected = {
            'normal_field': 'value1',
            'another_field': 'value3'
        }
        assert result == expected

    def test_filter_metadata_empty_dict(self):
        """Test that _filter_metadata handles empty dictionary."""
        data = {}
        result = SectionDataAdapter._filter_metadata(data)
        assert result == {}

    def test_filter_metadata_no_underscore_fields(self):
        """Test that _filter_metadata preserves all fields when none start with '_'."""
        data = {
            'field1': 'value1',
            'field2': 'value2'
        }
        result = SectionDataAdapter._filter_metadata(data)
        assert result == data

    def test_ensure_designation_adds_when_missing(self):
        """Test that _ensure_designation adds designation when missing."""
        data = {
            'field1': 'value1',
            'field2': 'value2'
        }
        designation = 'TEST_DESIGNATION'
        
        result = SectionDataAdapter._ensure_designation(data, designation)
        
        expected = {
            'designation': 'TEST_DESIGNATION',
            'field1': 'value1',
            'field2': 'value2'
        }
        assert result == expected

    def test_ensure_designation_preserves_existing(self):
        """Test that _ensure_designation preserves existing designation."""
        data = {
            'designation': 'EXISTING',
            'field1': 'value1'
        }
        designation = 'NEW_DESIGNATION'
        
        result = SectionDataAdapter._ensure_designation(data, designation)
        
        assert result['designation'] == 'EXISTING'
        assert len(result) == 2

    def test_ensure_designation_modifies_original(self):
        """Test that _ensure_designation modifies the original dictionary."""
        data = {'field1': 'value1'}
        designation = 'TEST'
        
        result = SectionDataAdapter._ensure_designation(data, designation)
        
        # Should modify and return the same dictionary object
        assert result is data
        assert data['designation'] == 'TEST'


if __name__ == "__main__":
    pytest.main([__file__])