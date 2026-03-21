from __future__ import annotations

import pytest

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.exceptions import SectionClass4Error
from steelsnakes.base.sections import SectionType
from steelsnakes.UK import (
    StressPattern as PublicStressPattern,
    HFCHS,
    HFEHS,
    HFRHS,
    HFSHS,
    UB,
    classify_section as public_classify_section,
)
from steelsnakes.UK.checks.classification import (
    ElementStressCase,
    StressPattern,
    classify_section,
    classify_section_from_dict,
)
from steelsnakes.UK.sections.angles import EqualAngle
from steelsnakes.UK.sections.cf_hollow import CFRHS
from steelsnakes.UK.sections.channels import ParallelFlangeChannel
from steelsnakes.UK.sections.universal import UniversalBeam


def test_classify_section_uk_universal_beam_extracts_web_and_flange() -> None:
    section = UniversalBeam(designation="TEST-UB", b=191.0, tw=8.6, tf=13.7, d=410.0)

    result = classify_section(section=section, fy_mpa=355.0)

    assert {item.name for item in result.elements} == {"web", "flange"}
    assert result.section_class in {
        SectionClass.CLASS_1,
        SectionClass.CLASS_2,
        SectionClass.CLASS_3,
        SectionClass.CLASS_4,
    }


def test_classify_section_uk_channel_major_axis_bending_sets_web_to_bending() -> None:
    section = ParallelFlangeChannel(designation="TEST-PFC", b=100.0, tw=9.0, tf=16.5, d=237.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressCase.BENDING
    assert stress_cases["flange"] == ElementStressCase.COMPRESSION


def test_classify_section_uk_angle_extracts_two_outstand_legs() -> None:
    section = EqualAngle(designation="100x100x10", hxh="100x100", t=10.0)

    result = classify_section(section=section, fy_mpa=355.0)

    assert {item.name for item in result.elements} == {"leg_1", "leg_2"}
    assert {item.kind for item in result.elements} == {"outstand"}


def test_classify_section_from_dict_supports_uk_section_types() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.UB,
        data={"d": 410.0, "tw": 8.6, "b": 191.0, "tf": 13.7},
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases == {
        "web": ElementStressCase.BENDING,
        "flange": ElementStressCase.COMPRESSION,
    }


def test_public_uk_api_exports_classification_helpers() -> None:
    section = UB("457x191x67")

    result = public_classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=PublicStressPattern.MAJOR_AXIS_BENDING,
    )

    assert {item.name for item in result.elements} == {"web", "flange"}
    assert {item.stress for item in result.elements} == {
        ElementStressCase.BENDING,
        ElementStressCase.COMPRESSION,
    }


def test_hfrhs_classify_compression() -> None:
    section = HFRHS("50x30x3.2")

    result = classify_section(section=section, fy_mpa=355.0)

    assert result.section_class == SectionClass.CLASS_1
    assert {item.name for item in result.elements} == {"web_wall", "flange_wall"}


def test_hfrhs_classify_major_bending() -> None:
    section = HFRHS("50x30x3.2")

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases == {
        "web_wall": ElementStressCase.BENDING,
        "flange_wall": ElementStressCase.COMPRESSION,
    }


def test_hfrhs_classify_minor_bending() -> None:
    section = HFRHS("50x30x3.2")

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=StressPattern.MINOR_AXIS_BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases == {
        "web_wall": ElementStressCase.COMPRESSION,
        "flange_wall": ElementStressCase.BENDING,
    }


def test_hfshs_classify() -> None:
    section = HFSHS("40x40x3.2")

    result = classify_section(section=section, fy_mpa=355.0)

    assert result.section_class == SectionClass.CLASS_1
    assert {item.name for item in result.elements} == {"web_wall", "flange_wall"}


def test_hfchs_classify() -> None:
    section = HFCHS("42.4x3.2")

    result = classify_section(section=section, fy_mpa=355.0)

    assert result.section_class == SectionClass.CLASS_1
    assert result.governing_elements == ["wall"]


def test_cfrhs_class4_raises() -> None:
    section = CFRHS("180x80x3.0")

    with pytest.raises(SectionClass4Error, match="EN 1993-1-3"):
        classify_section(section=section, fy_mpa=355.0)


def test_hfehs_not_implemented() -> None:
    section = HFEHS("300x150x8.0")

    with pytest.raises(NotImplementedError):
        classify_section(section=section, fy_mpa=355.0)
