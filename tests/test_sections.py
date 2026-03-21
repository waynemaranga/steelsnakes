"""
Essential tests for the base sections module.
Tests SectionType enum and BaseSection abstract class.
"""

# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

import pytest
from abc import ABC
from typing import Any

from steelsnakes.base.sections import SectionType, BaseSection


# Mock concrete implementation for testing BaseSection
class MockSection(BaseSection):
    """Mock concrete implementation of BaseSection for testing."""

    def __init__(self, designation: str, mass_per_metre: float = 50.0, **kwargs):
        super().__init__(designation=designation)
        self.mass_per_metre = mass_per_metre
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def get_section_type(cls) -> SectionType:
        """Return the section type for this mock section."""
        return SectionType.UB

    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        properties = {
            "designation": self.designation,
            "mass_per_metre": self.mass_per_metre,
            "section_type": self.get_section_type().value
        }

        # Add any additional attributes that were set
        for attr_name in dir(self):
            if not attr_name.startswith("_") and attr_name not in ["designation", "mass_per_metre"]:
                attr_value = getattr(self, attr_name)
                if not callable(attr_value):
                    properties[attr_name] = attr_value

        return properties


class TestSectionType:
    """Test the SectionType enum."""

    def test_section_type_enum_exists(self):
        """Test that SectionType enum is defined."""
        assert SectionType is not None

    def test_uk_section_types(self):
        """Test UK section types are defined."""
        assert SectionType.UB == SectionType.UB
        assert SectionType.UC == SectionType.UC
        assert SectionType.PFC == SectionType.PFC
        assert SectionType.L_EQUAL == SectionType.L_EQUAL

    def test_section_type_values(self):
        """Test section type values are strings."""
        assert SectionType.UB.value == "UB"
        assert SectionType.UC.value == "UC"
        assert SectionType.PFC.value == "PFC"


class TestBaseSection:
    """Test the BaseSection abstract base class."""

    def test_base_section_is_abstract(self):
        """Test that BaseSection is an abstract class."""
        assert issubclass(BaseSection, ABC)

        # Should not be able to instantiate BaseSection directly
        with pytest.raises(TypeError):
            BaseSection("test")  # type: ignore

    def test_concrete_section_creation(self):
        """Test creating concrete section instances."""
        section = MockSection("457x191x67")
        assert section.designation == "457x191x67"
        assert section.mass_per_metre == 50.0

    def test_concrete_section_with_kwargs(self):
        """Test creating concrete section with additional properties."""
        section = MockSection(
            "457x191x67",
            mass_per_metre=67.1,
            h=457.0,
            b=191.0
        )
        assert section.designation == "457x191x67"
        assert section.mass_per_metre == 67.1
        assert section.h == 457.0
        assert section.b == 191.0

    def test_section_str_representation(self):
        """Test string representation of section."""
        section = MockSection("457x191x67")
        assert str(section) == "457x191x67"

    def test_get_section_type_method(self):
        """Test get_section_type class method."""
        assert MockSection.get_section_type() == SectionType.UB

        # Test on instance too
        section = MockSection("test")
        assert section.get_section_type() == SectionType.UB

    def test_get_properties_method(self):
        """Test get_properties method."""
        section = MockSection(
            "457x191x67",
            mass_per_metre=67.1,
            h=457.0,
            b=191.0
        )

        properties = section.get_properties()
        assert isinstance(properties, dict)
        assert properties["designation"] == "457x191x67"
        assert properties["mass_per_metre"] == 67.1
        assert properties["section_type"] == "UB"
        assert properties["h"] == 457.0
        assert properties["b"] == 191.0

    def test_from_dictionary_method(self):
        """Test from_dictionary class method."""
        data = {
            "designation": "457x191x67",
            "mass_per_metre": 67.1,
            "h": 457.0,
            "b": 191.0
        }

        section = MockSection.from_dictionary(data)
        assert isinstance(section, MockSection)
        assert section.designation == "457x191x67"
        assert section.mass_per_metre == 67.1
        assert section.h == 457.0
        assert section.b == 191.0

    def test_list_properties_method(self):
        """Test list_properties method returns property names."""
        section = MockSection("test", mass_per_metre=50.0, h=100.0)
        props_list = section.list_properties()

        assert isinstance(props_list, list)
        assert "designation" in props_list
        assert "mass_per_metre" in props_list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
