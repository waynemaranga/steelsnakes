# TODO: rework, if necessary
# """
# Tests for the base sections module including SectionType enum and BaseSection abstract class.
# """

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
        # Accept any additional kwargs to match real section properties
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
            "mass_per_metre": getattr(self, "mass_per_metre", None),
            "section_type": self.get_section_type().value
        }
        
        # Add any additional attributes that were set
        for attr_name in dir(self):
            if not attr_name.startswith("_") and attr_name not in ["designation", "mass_per_metre"]:
                attr_value = getattr(self, attr_name)
                if not callable(attr_value):
                    properties[attr_name] = attr_value
        
        return properties


class AnotherMockSection(BaseSection):
    """Another mock section with different type for testing."""
    
    def __init__(self, designation: str):
        super().__init__(designation=designation)
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        """Return the section type for this mock section."""
        return SectionType.PFC
    
    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        return {
            "designation": self.designation,
            "section_type": self.get_section_type().value
        }


# class TestBaseSection:
#     """Test the BaseSection abstract base class."""
    
#     def test_base_section_is_abstract(self):
#         """Test that BaseSection is an abstract class."""
#         assert issubclass(BaseSection, ABC)
        
#         # Should not be able to instantiate BaseSection directly
#         with pytest.raises(TypeError):
#             BaseSection("test")  # type: ignore
    
#     def test_base_section_dataclass(self):
#         """Test that BaseSection is a dataclass."""
#         # BaseSection should have dataclass characteristics
#         section = MockSection("457x191x67")
#         assert hasattr(section, "__dataclass_fields__")
#         assert "designation" in section.__dataclass_fields__
    
#     def test_concrete_section_creation(self):
#         """Test creating concrete section instances."""
#         section = MockSection("457x191x67")
#         assert section.designation == "457x191x67"
#         assert section.mass_per_metre == 50.0
    
#     def test_concrete_section_with_kwargs(self):
#         """Test creating concrete section with additional properties."""
#         section = MockSection(
#             "457x191x67", 
#             mass_per_metre=67.1,
#             h=457.0,
#             b=191.0,
#             I_yy=21500.0
#         )
#         assert section.designation == "457x191x67"
#         assert section.mass_per_metre == 67.1
#         assert section.h == 457.0
#         assert section.b == 191.0
#         assert section.I_yy == 21500.0
    
#     def test_section_str_representation(self):
#         """Test string representation of section."""
#         section = MockSection("457x191x67")
#         assert str(section) == "457x191x67"
    
#     def test_section_repr_representation(self):
#         """Test repr representation of section."""
#         section = MockSection("457x191x67")
#         repr_str = repr(section)
#         assert "MockSection" in repr_str
#         assert "457x191x67" in repr_str
    
#     def test_get_section_type_method(self):
#         """Test get_section_type class method."""
#         assert MockSection.get_section_type() == SectionType.UB
#         assert AnotherMockSection.get_section_type() == SectionType.PFC
        
#         # Test on instances too
#         section1 = MockSection("test1")
#         section2 = AnotherMockSection("test2")
#         assert section1.get_section_type() == SectionType.UB
#         assert section2.get_section_type() == SectionType.PFC
    
#     def test_get_properties_method(self):
#         """Test get_properties method."""
#         section = MockSection(
#             "457x191x67",
#             mass_per_metre=67.1,
#             h=457.0,
#             b=191.0
#         )
        
#         properties = section.get_properties()
#         assert isinstance(properties, dict)
#         assert properties["designation"] == "457x191x67"
#         assert properties["mass_per_metre"] == 67.1
#         assert properties["section_type"] == "UB"
#         assert properties["h"] == 457.0
#         assert properties["b"] == 191.0
    
#     def test_from_dictionary_method(self):
#         """Test from_dictionary class method."""
#         data = {
#             "designation": "457x191x67",
#             "mass_per_metre": 67.1,
#             "h": 457.0,
#             "b": 191.0
#         }
        
#         section = MockSection.from_dictionary(data)
#         assert isinstance(section, MockSection)
#         assert section.designation == "457x191x67"
#         assert section.mass_per_metre == 67.1
#         assert section.h == 457.0
#         assert section.b == 191.0
    
#     def test_from_dictionary_minimal_data(self):
#         """Test from_dictionary with minimal data."""
#         data = {"designation": "test_section"}
#         section = MockSection.from_dictionary(data)
#         assert section.designation == "test_section"
#         # Should use default values for other properties
#         assert section.mass_per_metre == 50.0
    
#     def test_multiple_section_types(self):
#         """Test multiple concrete implementations."""
#         ub_section = MockSection("457x191x67")
#         pfc_section = AnotherMockSection("430x100x64")
        
#         assert ub_section.get_section_type() == SectionType.UB
#         assert pfc_section.get_section_type() == SectionType.PFC
#         assert ub_section.get_section_type() != pfc_section.get_section_type()


# class TestAbstractMethods:
#     """Test abstract method enforcement."""
    
#     def test_abstract_method_enforcement(self):
#         """Test that abstract methods must be implemented."""
        
#         # This should fail because abstract methods are not implemented
#         class IncompleteSection(BaseSection):
#             def __init__(self, designation: str):
#                 super().__init__(designation=designation)
#             # Missing get_section_type and get_properties implementations
        
#         with pytest.raises(TypeError):
#             IncompleteSection("test")  # type: ignore
    
#     def test_partial_implementation_fails(self):
#         """Test that partial implementation still fails."""
        
#         class PartialSection(BaseSection):
#             def __init__(self, designation: str):
#                 super().__init__(designation=designation)
            
#             @classmethod
#             def get_section_type(cls) -> SectionType:
#                 return SectionType.UB
#             # Missing get_properties implementation
        
#         with pytest.raises(TypeError):
#             PartialSection("test")  # type: ignore


class TestInheritance:
    """Test inheritance behavior."""
    
    def test_inheritance_chain(self):
        """Test that MockSection properly inherits from BaseSection."""
        section = MockSection("test")
        assert isinstance(section, BaseSection)
        assert isinstance(section, MockSection)
    
    def test_method_resolution_order(self):
        """Test method resolution order."""
        mro = MockSection.__mro__
        assert BaseSection in mro
        assert ABC in mro
    
    def test_abstract_base_class_registration(self):
        """Test ABC registration."""
        assert issubclass(MockSection, BaseSection)
        assert issubclass(AnotherMockSection, BaseSection)


# class TestEdgeCases:
#     """Test edge cases and error conditions."""
    
#     def test_empty_designation(self):
#         """Test section with empty designation."""
#         section = MockSection("")
#         assert section.designation == ""
#         assert str(section) == ""
    
#     def test_none_properties(self):
#         """Test section with None properties."""
#         section = MockSection("test", mass_per_metre=None)
#         properties = section.get_properties()
#         assert properties["mass_per_metre"] is None
    
#     def test_special_characters_in_designation(self):
#         """Test section with special characters in designation."""
#         designation = "457×191×67-TEST_SECTION"
#         section = MockSection(designation)
#         assert section.designation == designation
#         assert str(section) == designation
    
#     def test_very_long_designation(self):
#         """Test section with very long designation."""
#         long_designation = "A" * 1000
#         section = MockSection(long_designation)
#         assert section.designation == long_designation


if __name__ == "__main__":
    pytest.main([__file__])
