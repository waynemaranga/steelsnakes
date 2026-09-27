"""
Tests for the US Metric steel sections module.

The US Metric module carries the same AISC shapes as the US module in SI units and designations
(e.g W310X38.7 for W12X26); these tests check it is wired into the shared database and factory.
"""

# pyright: reportAttributeAccessIssue=false

import pytest
from typing import Callable

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.database import SectionDatabase
from steelsnakes.US_Metric.database import USMetricSectionDatabase, get_US_Metric_database
from steelsnakes.US_Metric.factory import USMetricSectionFactory, get_US_Metric_factory
from steelsnakes.US_Metric.sections import angles, beams, channels, hollow, piles, pipes, tees


# Every US Metric section type, with the class the factory should build and a designation from the packaged data
US_METRIC_SECTIONS: list[tuple[SectionType, type[BaseSection], Callable[[str], BaseSection], str]] = [
    (SectionType.W, beams.WideFlangeBeam, beams.W, "W310X38.7"),
    (SectionType.S, beams.StandardBeam, beams.S, "S610X180"),
    (SectionType.M, beams.MiscellaneousBeam, beams.M, "M318X18.5"),
    (SectionType.C, channels.StandardChannel, channels.C, "C380X74"),
    (SectionType.MC, channels.MiscellaneousChannel, channels.MC, "MC460X86"),
    (SectionType.L_EQUAL, angles.EqualAngle, angles.L_EQUAL, "L305X305X34.9"),
    (SectionType.L_UNEQUAL, angles.UnequalAngle, angles.L_UNEQUAL, "L203X152X25.4"),
    (SectionType.L2L_EQUAL, angles.BackToBackEqualAngle, angles.L2L_EQUAL, "2L305X305X34.9"),
    (SectionType.L2L_LLBB, angles.LongLegBackToBackUnequalAngle, angles.L2L_LLBB, "2L203X152X25.4LLBB"),
    (SectionType.L2L_SLBB, angles.ShortLegBackToBackUnequalAngle, angles.L2L_SLBB, "2L203X152X25.4SLBB"),
    (SectionType.HSS_RCT, hollow.RectangularHSS, hollow.HSS_RCT, "HSS863.6X254X25.4"),
    (SectionType.HSS_SQR, hollow.SquareHSS, hollow.HSS_SQR, "HSS558.8X558.8X25.4"),
    (SectionType.HSS_RND, hollow.RoundHSS, hollow.HSS_RND, "HSS711.2X25.4"),
    (SectionType.HP, piles.BearingPile, piles.HP, "HP460X304"),
    (SectionType.PIPE, pipes.Pipe, pipes.PIPE, "Pipe650STD"),
    (SectionType.ST, tees.StandardTee, tees.ST, "ST305X90"),
    (SectionType.MT, tees.MiscellaneousTee, tees.MT, "MT159X9.25"),
    (SectionType.WT, tees.WideFlangeTee, tees.WT, "WT550X303.5"),
]


@pytest.fixture(scope="module")
def us_metric_factory():
    """Create one US Metric factory over the packaged data for the whole module."""
    return get_US_Metric_factory()


class TestUSMetricDatabase:
    """Test the US Metric database finds and loads its data."""

    def test_database_region_and_directory(self):
        """Test the US_METRIC region resolves to the US_Metric package folder."""
        db = get_US_Metric_database()
        assert isinstance(db, USMetricSectionDatabase)
        assert db.region == "US_METRIC"
        assert db.data_directory.name == "data"
        assert db.data_directory.parent.name == "US_Metric"

    def test_supported_types_match_US(self):
        """Test US Metric supports the same section types as US."""
        us_types = SectionDatabase(region="US").get_supported_types()
        assert get_US_Metric_database().get_supported_types() == us_types

    def test_every_supported_type_has_data(self):
        """Test every supported type has sections loaded from the packaged JSON files."""
        db = get_US_Metric_database()
        assert db.get_available_section_types() == db.get_supported_types()

    def test_sections_are_in_SI_units(self, us_metric_factory):
        """Test W310X38.7 carries SI values, not the imperial W12X26 values."""
        section = us_metric_factory.create_section("W310X38.7", SectionType.W)
        assert section.d == pytest.approx(310.0)  # mm, 12.2 in. in the US module
        assert section.A == pytest.approx(4940.0)  # mm^2, 7.65 in^2 in the US module


class TestUSMetricFactory:
    """Test the US Metric factory registers and creates US Metric classes."""

    def test_factory_without_database(self):
        """Test factory initialization without providing database."""
        factory = USMetricSectionFactory()
        assert isinstance(factory.database, USMetricSectionDatabase)

    @pytest.mark.parametrize(("section_type", "section_class", "constructor", "designation"), US_METRIC_SECTIONS)
    def test_factory_registers_US_Metric_class(self, us_metric_factory, section_type, section_class, constructor, designation):
        """Test each type maps to the US Metric class, not the imperial US class of the same name."""
        assert us_metric_factory._section_classes[section_type] is section_class

    @pytest.mark.parametrize(("section_type", "section_class", "constructor", "designation"), US_METRIC_SECTIONS)
    def test_convenience_function_creates_section(self, section_type, section_class, constructor, designation):
        """Test W(), C(), L_EQUAL() etc. create sections from the packaged data."""
        section = constructor(designation)

        assert isinstance(section, section_class)
        assert section.designation == designation
        assert section.get_section_type() == section_type
        assert section.get_properties()["designation"] == designation

    def test_miscellaneous_tee_with_workable_gauge(self, us_metric_factory):
        """Test the one MT shape that lists a workable gauge can be created."""
        section = us_metric_factory.create_section("MT65X14.05", SectionType.MT)
        assert section.WGi == pytest.approx(69.9)

    def test_long_leg_suggestions_stay_long_leg(self, us_metric_factory):
        """Test an SLBB designation asked for as LLBB suggests LLBB sections and notes the SLBB match."""
        with pytest.raises(ValueError) as exc_info:
            us_metric_factory.create_section("2L203X152X25.4X19SLBB", SectionType.L2L_LLBB)

        error_msg = str(exc_info.value)
        suggestions = error_msg.split("Similar sections: ")[1].split("\n")[0]
        assert "SLBB" not in suggestions
        assert "Note: '2L203X152X25.4X19SLBB' exists as type 'L2L_SLBB'." in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
