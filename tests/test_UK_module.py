"""
Comprehensive tests for the UK steel sections module.

Tests all UK-specific functionality including database, factory, section types,
and module-level integration.
"""

# pyright: reportAttributeAccessIssue=false

import pytest
import json
from pathlib import Path
from typing import Any, Callable

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.base.exceptions import SectionNotFoundError, SectionTypeNotRegisteredError
from steelsnakes.UK.database import UKSectionDatabase, get_UK_database
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory

# Import all UK section classes for testing
from steelsnakes.UK.sections.universal import (
    UniversalSection, UniversalBeam, UniversalColumn, UniversalBearingPile,
    UB, UC, UBP
)
from steelsnakes.UK.sections.channels import ParallelFlangeChannel, PFC
from steelsnakes.UK.sections.angles import (
    EqualAngle, UnequalAngle, EqualAngleBackToBack, UnequalAngleBackToBack,
    L_EQUAL, L_UNEQUAL, L_EQUAL_B2B, L_UNEQUAL_B2B
)
from steelsnakes.UK.sections.cf_hollow import (
    ColdFormedCircularHollowSection, ColdFormedSquareHollowSection,
    ColdFormedRectangularHollowSection, CFCHS, CFSHS, CFRHS
)
from steelsnakes.UK.sections.hf_hollow import (
    HotFinishedCircularHollowSection, HotFinishedSquareHollowSection,
    HotFinishedRectangularHollowSection, HotFinishedEllipticalHollowSection,
    HFCHS, HFSHS, HFRHS, HFEHS
)
# from steelsnakes.UK.sections.preloaded_bolts import (
#     PreloadedBolt88, PreloadedBolt109, BOLT_PRE_88, BOLT_PRE_109
# )
# from steelsnakes.UK.sections.welds import WeldSpecification, WELD

# Import module-level functions
import steelsnakes.UK as uk_module
from steelsnakes.UK import create_section


# Every UK section type, with the class the factory should build for it
UK_SECTION_CLASSES: list[tuple[SectionType, type[BaseSection]]] = [
    (SectionType.UB, UniversalBeam),
    (SectionType.UC, UniversalColumn),
    (SectionType.UBP, UniversalBearingPile),
    (SectionType.PFC, ParallelFlangeChannel),
    (SectionType.L_EQUAL, EqualAngle),
    (SectionType.L_UNEQUAL, UnequalAngle),
    (SectionType.L_EQUAL_B2B, EqualAngleBackToBack),
    (SectionType.L_UNEQUAL_B2B, UnequalAngleBackToBack),
    (SectionType.HFCHS, HotFinishedCircularHollowSection),
    (SectionType.HFSHS, HotFinishedSquareHollowSection),
    (SectionType.HFRHS, HotFinishedRectangularHollowSection),
    (SectionType.HFEHS, HotFinishedEllipticalHollowSection),
    (SectionType.CFCHS, ColdFormedCircularHollowSection),
    (SectionType.CFSHS, ColdFormedSquareHollowSection),
    (SectionType.CFRHS, ColdFormedRectangularHollowSection),
]


# Test fixtures
@pytest.fixture
def mock_uk_data_dir(tmp_path):
    """Create a temporary UK data directory with mock JSON files."""
    data_dir = tmp_path / "uk_data"
    data_dir.mkdir()

    mock_data: dict[str, dict[str, dict[str, Any]]] = {
        "UB": {
            "457x191x67": {
                "designation": "457x191x67",
                "serial_size": "457x191",
                "mass_per_metre": 67.1,
                "h": 457.0,
                "b": 191.0,
                "tw": 8.5,
                "tf": 12.7,
                "r": 10.2,
                "d": 407.6,
                "A": 85.5,
                "I_yy": 21500.0,
                "I_zz": 1290.0,
                "W_el_yy": 940.0,
                "W_el_zz": 135.0,
                "i_yy": 15.9,
                "i_zz": 3.88
            },
            "305x305x137": {
                "designation": "305x305x137",
                "serial_size": "305x305",
                "mass_per_metre": 137.0,
                "h": 305.0,
                "b": 305.0,
                "tw": 10.7,
                "tf": 15.4,
                "A": 175.0,
                "I_yy": 29000.0,
                "I_zz": 29000.0
            }
        },
        "UC": {
            "203x203x46": {
                "designation": "203x203x46",
                "serial_size": "203x203",
                "mass_per_metre": 46.0,
                "h": 203.1,
                "b": 203.6,
                "tw": 7.2,
                "tf": 11.0,
                "A": 58.8,
                "I_yy": 5700.0,
                "I_zz": 1970.0
            }
        },
        "PFC": {
            "430x100x64": {
                "designation": "430x100x64",
                "serial_size": "430x100",
                "mass_per_metre": 64.0,
                "h": 430.0,
                "b": 100.0,
                "tw": 11.0,
                "tf": 16.0,
                "A": 81.5,
                "I_yy": 12500.0,
                "I_zz": 385.0
            }
        },
        "L_EQUAL": {
            "200x200x24": {
                "designation": "200x200x24",
                "hxh": "200x200",
                "t": 24.0,
                "mass_per_metre": 71.1,
                "r_1": 18.0,
                "r_2": 9.0,
                "c": 56.6,
                "I_yy": 4790.0,
                "I_zz": 4790.0,
                "I_uu": 7660.0,
                "I_vv": 1920.0
            }
        },
        "L_EQUAL_B2B": {
            "200x200x24": {
                "designation": "200x200x24",
                "hxh": "200x200",
                "t": 24.0,
                "total_mass_per_metre": 142.2,
                "total_area": 181.0,
                "i_zz": {"0": 8.42, "8": 8.7, "10": 8.77, "12": 8.84, "15": 8.95}
            }
        },
        "CFCHS": {
            "168.3x5.0": {
                "designation": "168.3x5.0",
                "mass_per_metre": 20.1,
                "A": 25.6
            }
        },
    }
    for section_type, sections in mock_data.items():
        with open(data_dir / f"{section_type}.json", "w") as f:
            json.dump(sections, f)

    return data_dir


@pytest.fixture
def uk_database(mock_uk_data_dir):
    """Create a UK database instance with mock data."""
    return UKSectionDatabase(data_directory=mock_uk_data_dir)


@pytest.fixture
def uk_factory(uk_database):
    """Create a UK factory instance with mock database."""
    return UKSectionFactory(database=uk_database)


class TestUKSectionDatabase:
    """Test UK-specific database functionality."""

    def test_database_initialization(self, mock_uk_data_dir):
        """Test UK database initialization."""
        db = UKSectionDatabase(data_directory=mock_uk_data_dir)
        assert db.data_directory == mock_uk_data_dir.resolve()
        assert db.region == "UK"
        assert not db.use_sqlite
        assert isinstance(db._cache, dict)

    def test_resolve_data_directory_provided(self, tmp_path):
        """Test data directory resolution when provided."""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()

        db = UKSectionDatabase(data_directory=test_dir)
        assert db._resolve_data_directory(test_dir, "UK") == test_dir.resolve()

    def test_resolve_data_directory_auto_discovery(self):
        """Test auto-discovery of the packaged UK data directory."""
        db = UKSectionDatabase()
        assert isinstance(db.data_directory, Path)
        assert db.data_directory.name == "data"
        assert db.data_directory.parent.name == "UK"

    @pytest.mark.parametrize(("section_type", "section_class"), UK_SECTION_CLASSES)
    def test_get_supported_types(self, uk_database, section_type, section_class):
        """Test that all UK section types are supported."""
        assert section_type in uk_database.get_supported_types()

    def test_get_UK_database_uses_given_directory(self, mock_uk_data_dir):
        """Test the convenience constructor passes the data directory through."""
        db = get_UK_database(mock_uk_data_dir)
        assert isinstance(db, UKSectionDatabase)
        assert db.data_directory == mock_uk_data_dir.resolve()
        assert db.list_sections(SectionType.UB) == ["457x191x67", "305x305x137"]

    @pytest.mark.parametrize(
        "designation",
        [
            "457X191X67",  # case-insensitive
            "457 x 191 x 67",  # spaces ignored
            " 457x191x67 ",  # surrounding whitespace
            "457191x67",  # missing separator, caught by difflib
        ],
    )
    def test_fuzzy_find_section(self, uk_database, designation):
        """Test fuzzy finding tolerates case, spacing and small typos."""
        result = uk_database._fuzzy_find_section(designation)
        assert result is not None
        section_type, data = result
        assert section_type == SectionType.UB
        assert data["designation"] == "457x191x67"

    def test_fuzzy_find_section_not_found(self, uk_database):
        """Test fuzzy finding when section doesn't exist."""
        assert uk_database._fuzzy_find_section("999x999x999") is None
        assert uk_database.find_section("999x999x999") is None

    def test_database_with_nonexistent_directory(self, tmp_path):
        """Test database handling of non-existent directory."""
        nonexistent_dir = tmp_path / "does_not_exist"
        db = UKSectionDatabase(data_directory=nonexistent_dir)

        # Should not raise error, but cache should be empty
        assert db.data_directory == nonexistent_dir.resolve()
        assert db.get_available_section_types() == []
        for section_type in db.get_supported_types():
            assert db.list_sections(section_type) == []


class TestUKSectionFactory:
    """Test UK-specific factory functionality."""

    @pytest.mark.parametrize(("section_type", "section_class"), UK_SECTION_CLASSES)
    def test_factory_registers_UK_classes(self, uk_factory, section_type, section_class):
        """Test that every UK section type is registered with its UK class."""
        assert uk_factory._section_classes[section_type] is section_class

    def test_factory_initialization(self, uk_database):
        """Test UK factory initialization."""
        factory = UKSectionFactory(database=uk_database)
        assert factory.database is uk_database
        assert len(factory.get_registered_types()) == len(UK_SECTION_CLASSES)

    def test_factory_without_database(self):
        """Test factory initialization without providing database."""
        factory = UKSectionFactory()
        assert isinstance(factory.database, UKSectionDatabase)
        assert factory.database.region == "UK"

    def test_get_UK_factory_uses_given_directory(self, mock_uk_data_dir):
        """Test the convenience constructor passes the data directory through."""
        factory = get_UK_factory(mock_uk_data_dir)
        assert isinstance(factory, UKSectionFactory)
        assert factory.database.data_directory == mock_uk_data_dir.resolve()


class TestSectionTypes:
    """Test that each UK section class reports its own section type."""

    @pytest.mark.parametrize(("section_type", "section_class"), UK_SECTION_CLASSES)
    def test_section_class_reports_section_type(self, section_type, section_class):
        """Test get_section_type() on the class and on an instance."""
        assert section_class.get_section_type() == section_type
        assert section_class(designation="TEST").get_section_type() == section_type

    def test_universal_sections_share_base_class(self):
        """Test UB, UC and UBP all inherit UniversalSection."""
        for section_class in (UniversalBeam, UniversalColumn, UniversalBearingPile):
            assert issubclass(section_class, UniversalSection)


class TestSectionCreation:
    """Test creating UK sections from the mock database."""

    def test_universal_beam_creation(self, uk_factory):
        """Test creating Universal Beam section."""
        beam = uk_factory.create_section("457x191x67", SectionType.UB)

        assert isinstance(beam, UniversalBeam)
        assert beam.designation == "457x191x67"
        assert beam.serial_size == "457x191"
        assert beam.mass_per_metre == 67.1
        assert beam.h == 457.0
        assert beam.b == 191.0
        assert beam.tw == 8.5
        assert beam.tf == 12.7
        assert beam.A == 85.5
        assert beam.I_yy == 21500.0
        assert beam.I_zz == 1290.0

    def test_universal_column_creation(self, uk_factory):
        """Test creating Universal Column section."""
        column = uk_factory.create_section("203x203x46", SectionType.UC)

        assert isinstance(column, UniversalColumn)
        assert column.serial_size == "203x203"
        assert column.h == 203.1
        assert column.b == 203.6
        assert column.A == 58.8

    def test_universal_section_get_properties(self, uk_factory):
        """Test getting properties from universal section."""
        props = uk_factory.create_section("457x191x67", SectionType.UB).get_properties()

        assert props["designation"] == "457x191x67"
        assert props["mass_per_metre"] == 67.1
        assert props["A"] == 85.5
        assert props["I_yy"] == 21500.0
        # Metadata added by the database is not a section property
        assert "_section_type" not in props
        assert "_region" not in props

    def test_parallel_flange_channel_creation(self, uk_factory):
        """Test creating Parallel Flange Channel section."""
        channel = uk_factory.create_section("430x100x64", SectionType.PFC)

        assert isinstance(channel, ParallelFlangeChannel)
        assert channel.serial_size == "430x100"
        assert channel.tw == 11.0
        assert channel.tf == 16.0
        assert channel.A == 81.5

    def test_equal_angle_creation(self, uk_factory):
        """Test creating Equal Angle section."""
        angle = uk_factory.create_section("200x200x24", SectionType.L_EQUAL)

        assert isinstance(angle, EqualAngle)
        assert angle.hxh == "200x200"
        assert angle.t == 24.0
        assert angle.r_1 == 18.0
        assert angle.r_2 == 9.0
        assert angle.c == 56.6
        assert angle.I_uu == 7660.0
        assert angle.I_vv == 1920.0

    def test_equal_angle_back_to_back_reads_i_zz_per_spacing(self, uk_factory):
        """Test i_zz of back-to-back angles is keyed by the spacing between them."""
        angles = uk_factory.create_section("200x200x24", SectionType.L_EQUAL_B2B)

        assert isinstance(angles, EqualAngleBackToBack)
        assert angles.total_area == 181.0
        assert angles.i_zz["0"] == 8.42
        assert angles.i_zz["15"] == 8.95

    @pytest.mark.parametrize("section_class", [EqualAngleBackToBack, UnequalAngleBackToBack])
    def test_back_to_back_i_zz_default_is_not_shared(self, section_class):
        """Test each back-to-back instance gets its own i_zz dictionary."""
        first = section_class(designation="A")
        second = section_class(designation="B")
        first.i_zz["10"] = 1.0

        assert second.i_zz == {}

    def test_cold_formed_circular_hollow_section(self, uk_factory):
        """Test creating Cold Formed Circular Hollow Section."""
        section = uk_factory.create_section("168.3x5.0", SectionType.CFCHS)

        assert isinstance(section, ColdFormedCircularHollowSection)
        assert section.mass_per_metre == 20.1
        assert section.A == 25.6

    @pytest.mark.parametrize(
        ("constructor", "designation", "section_class"),
        [
            (UB, "457x191x67", UniversalBeam),
            (UC, "203x203x46", UniversalColumn),
            (PFC, "430x100x64", ParallelFlangeChannel),
            (L_EQUAL, "200x200x24", EqualAngle),
            (L_EQUAL_B2B, "200x200x24", EqualAngleBackToBack),
            (CFCHS, "168.3x5.0", ColdFormedCircularHollowSection),
        ],
    )
    def test_convenience_function_reads_given_data_directory(
        self, mock_uk_data_dir, constructor: Callable[..., BaseSection], designation, section_class
    ):
        """Test UB(), PFC(), L_EQUAL() etc. build sections from the data directory passed in."""
        section = constructor(designation, mock_uk_data_dir)

        assert isinstance(section, section_class)
        assert section.designation == designation

    @pytest.mark.parametrize(
        ("constructor", "designation", "section_class"),
        [
            (UB, "457x191x67", UniversalBeam),
            (UC, "305x305x137", UniversalColumn),
            (UBP, "203x203x45", UniversalBearingPile),
            (PFC, "430x100x64", ParallelFlangeChannel),
            (L_EQUAL, "200x200x24.0", EqualAngle),  # packaged L_EQUAL keeps the ".0"; L_EQUAL_B2B doesn't
            (L_UNEQUAL, "200x150x18", UnequalAngle),
            (L_EQUAL_B2B, "200x200x24", EqualAngleBackToBack),
            (L_UNEQUAL_B2B, "200x150x18", UnequalAngleBackToBack),
            (HFCHS, "42.4x3.2", HotFinishedCircularHollowSection),
            (HFSHS, "40x40x3.2", HotFinishedSquareHollowSection),
            (HFRHS, "50x30x3.2", HotFinishedRectangularHollowSection),
            (CFCHS, "168.3x5.0", ColdFormedCircularHollowSection),
        ],
    )
    def test_convenience_function_reads_packaged_data(
        self, constructor: Callable[..., BaseSection], designation, section_class
    ):
        """Test the convenience functions against the packaged UK data."""
        section = constructor(designation)

        assert isinstance(section, section_class)
        assert section.designation == designation

    def test_elliptical_and_cold_formed_rhs_shs_from_packaged_data(self):
        """Test the remaining hollow constructors using the first packaged designation."""
        database = get_UK_database()
        for constructor, section_type, section_class in [
            (HFEHS, SectionType.HFEHS, HotFinishedEllipticalHollowSection),
            (CFSHS, SectionType.CFSHS, ColdFormedSquareHollowSection),
            (CFRHS, SectionType.CFRHS, ColdFormedRectangularHollowSection),
        ]:
            designation = database.list_sections(section_type)[0]
            assert isinstance(constructor(designation), section_class)


class TestModuleIntegration:
    """Test module-level integration and convenience functions."""

    def test_module_level_create_section(self):
        """Test module-level create_section function."""
        section = create_section("457x191x67", SectionType.UB)
        assert isinstance(section, UniversalBeam)
        assert section.designation == "457x191x67"

    def test_module_level_create_section_auto_detect(self):
        """Test module-level create_section with auto-detection."""
        section = create_section("430x100x64")
        assert isinstance(section, ParallelFlangeChannel)

    def test_module_level_create_section_accepts_type_value(self):
        """Test the section type may be given as its string value."""
        section = create_section("457x191x67", "UB")
        assert isinstance(section, UniversalBeam)

    def test_all_exports_available(self):
        """Test that all items in __all__ are importable."""
        for item_name in uk_module.__all__:
            assert hasattr(uk_module, item_name), f"{item_name} not available in module"

    def test_auto_register_function_success(self, capsys):
        """Test auto-registration function succeeds silently."""
        uk_module._register_all_uk_sections()
        assert "Warning" not in capsys.readouterr().out

    def test_auto_register_function_handles_exception(self, monkeypatch, capsys):
        """Test auto-registration handles exceptions gracefully."""
        def broken_factory():
            raise RuntimeError("Test error")

        monkeypatch.setattr(uk_module, "get_UK_factory", broken_factory)
        uk_module._register_all_uk_sections()

        output = capsys.readouterr().out
        assert "Warning: Could not auto-register UK section classes" in output
        assert "Test error" in output


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_section_creation_with_invalid_designation(self, uk_factory):
        """Test error handling for invalid section designation."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            uk_factory.create_section("INVALID_SECTION", SectionType.UB)

        assert "Section 'INVALID_SECTION' of type 'UB' not found" in str(exc_info.value)

    def test_section_creation_with_other_region_type(self, uk_factory):
        """Test a US section type finds nothing, but points to the UK type that has the designation."""
        with pytest.raises(SectionNotFoundError) as exc_info:
            uk_factory.create_section("457x191x67", SectionType.W)

        error_msg = str(exc_info.value)
        assert "Section '457x191x67' of type 'W' not found" in error_msg
        assert "exists as type 'UB'" in error_msg

    def test_section_creation_with_unknown_type_value(self, uk_factory):
        """Test an unknown section type string raises SectionTypeNotRegisteredError."""
        with pytest.raises(SectionTypeNotRegisteredError) as exc_info:
            uk_factory.create_section("457x191x67", "NOT_A_TYPE")

        assert "Unknown section type 'NOT_A_TYPE'" in str(exc_info.value)
        assert "'UB'" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
