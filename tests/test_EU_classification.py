from __future__ import annotations

import pytest

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.EU import IPE, StressPattern as PublicStressPattern, classify_section as public_classify_section
from steelsnakes.EU.checks.classification import (
    ElementInput,
    ElementStressCase,
    StressPattern,
    classify_elements,
    classify_outstand_flange,
    classify_internal_part,
    classify_section,
    classify_section_from_dict,
)
from steelsnakes.EU.sections.angles import EqualAngle
from steelsnakes.EU.sections.beams import ParallelFlangeBeam
from steelsnakes.EU.sections.columns import UniversalColumn
from steelsnakes.EU.sections.piles import UniversalBearingPile


def test_classify_internal_part_class_boundaries() -> None:
    result = classify_internal_part(c_mm=240.0, t_mm=10.0, fy_mpa=355.0, name="web")
    assert result.kind == "internal"
    assert result.section_class == SectionClass.CLASS_1


def test_classify_outstand_flange_class_boundaries() -> None:
    result = classify_outstand_flange(c_mm=120.0, t_mm=10.0, fy_mpa=355.0, name="flange")
    assert result.kind == "outstand"
    assert result.section_class == SectionClass.CLASS_4


def test_classify_internal_part_in_bending_uses_bending_limits() -> None:
    result = classify_internal_part(
        c_mm=360.4,
        t_mm=7.7,
        fy_mpa=275.0,
        name="web",
        stress=ElementStressCase.BENDING,
    )

    assert result.stress == ElementStressCase.BENDING
    assert result.section_class == SectionClass.CLASS_1


def test_classify_internal_part_in_combined_loading_uses_alpha() -> None:
    result = classify_internal_part(
        c_mm=360.4,
        t_mm=7.7,
        fy_mpa=275.0,
        name="web",
        stress=ElementStressCase.COMBINED,
        alpha=0.70,
    )

    assert result.stress == ElementStressCase.COMBINED
    assert result.section_class == SectionClass.CLASS_2
    assert result.class_3_limit is None


def test_classify_internal_part_in_combined_loading_requires_psi_for_class_3_limit() -> None:
    with pytest.raises(ValueError):
        classify_internal_part(
            c_mm=420.0,
            t_mm=7.7,
            fy_mpa=275.0,
            name="web",
            stress=ElementStressCase.COMBINED,
            alpha=0.70,
        )


def test_classify_outstand_flange_bending_uses_same_limits_as_compression() -> None:
    compression_result = classify_outstand_flange(
        c_mm=60.0,
        t_mm=10.0,
        fy_mpa=355.0,
        name="flange",
        stress=ElementStressCase.COMPRESSION,
    )
    bending_result = classify_outstand_flange(
        c_mm=60.0,
        t_mm=10.0,
        fy_mpa=355.0,
        name="flange",
        stress=ElementStressCase.BENDING,
    )

    assert compression_result.section_class == bending_result.section_class
    assert compression_result.class_1_limit == bending_result.class_1_limit
    assert compression_result.class_2_limit == bending_result.class_2_limit
    assert compression_result.class_3_limit == bending_result.class_3_limit


def test_classify_elements_governing_class_is_worst() -> None:
    elements = [
        ElementInput(name="web", kind="internal", c_mm=220.0, t_mm=10.0),
        ElementInput(name="flange", kind="outstand", c_mm=120.0, t_mm=10.0),
    ]

    result = classify_elements(elements, fy_mpa=355.0)

    assert result.section_class == SectionClass.CLASS_4
    assert "flange" in result.governing_elements


def test_classify_elements_requires_at_least_one_element() -> None:
    with pytest.raises(ValueError):
        classify_elements([], fy_mpa=355.0)


def test_classify_section_beam_extracts_web_and_flange() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(section=section, fy_mpa=355.0)

    names = {item.name for item in result.elements}
    assert names == {"web", "flange"}
    assert result.section_class in {
        SectionClass.CLASS_1,
        SectionClass.CLASS_2,
        SectionClass.CLASS_3,
        SectionClass.CLASS_4,
    }


def test_classify_section_beam_major_axis_bending_sets_web_to_bending() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressCase.BENDING
    assert stress_cases["flange"] == ElementStressCase.COMPRESSION


def test_classify_section_beam_accepts_string_stress_pattern() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressCase.BENDING
    assert stress_cases["flange"] == ElementStressCase.COMPRESSION


def test_classify_section_accepts_string_typo_for_compression() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern="comprression",
    )

    assert {item.stress for item in result.elements} == {ElementStressCase.COMPRESSION}


def test_classify_section_angle_extracts_two_outstand_legs() -> None:
    section = EqualAngle(designation="100x100x10", hxh="100x100", t=10.0)

    result = classify_section(section=section, fy_mpa=355.0)

    names = {item.name for item in result.elements}
    kinds = {item.kind for item in result.elements}
    assert names == {"leg_1", "leg_2"}
    assert kinds == {"outstand"}


def test_classify_section_column_reuses_i_section_adapter() -> None:
    section = UniversalColumn(designation="TEST-COLUMN", b=320.0, tw=14.0, tf=24.0, d=420.0)

    result = classify_section(section=section, fy_mpa=355.0)

    assert {item.name for item in result.elements} == {"web", "flange"}


def test_classify_section_bearing_pile_reuses_i_section_adapter() -> None:
    section = UniversalBearingPile(designation="TEST-PILE", b=300.0, tw=12.0, tf=18.0, d=380.0)

    result = classify_section(section=section, fy_mpa=355.0)

    assert {item.name for item in result.elements} == {"web", "flange"}


def test_classify_section_from_dict_for_custom_beam() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 300.0, "tw": 8.0, "b": 200.0, "tf": 12.0},
        fy_mpa=355.0,
    )

    assert len(result.elements) == 2
    assert result.section_class in {
        SectionClass.CLASS_1,
        SectionClass.CLASS_2,
        SectionClass.CLASS_3,
        SectionClass.CLASS_4,
    }


def test_classify_section_from_dict_for_bending_beam() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 360.4, "tw": 7.7, "b": 177.7, "tf": 10.9},
        fy_mpa=275.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressCase.BENDING
    assert stress_cases["flange"] == ElementStressCase.COMPRESSION


def test_classify_section_from_dict_accepts_string_stress_pattern() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 360.4, "tw": 7.7, "b": 177.7, "tf": 10.9},
        fy_mpa=275.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressCase.BENDING
    assert stress_cases["flange"] == ElementStressCase.COMPRESSION


def test_classify_section_rejects_unimplemented_minor_axis_pattern() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    with pytest.raises(NotImplementedError):
        classify_section(
            section=section,
            fy_mpa=355.0,
            stress_pattern="bending-minor-axis",
        )


def test_classify_section_rejects_invalid_stress_pattern_string() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    with pytest.raises(ValueError):
        classify_section(
            section=section,
            fy_mpa=355.0,
            stress_pattern="sideways",
        )


def test_classify_section_rejects_combined_pattern_without_custom_elements() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    with pytest.raises(NotImplementedError):
        classify_section(
            section=section,
            fy_mpa=355.0,
            stress_pattern="combined",
        )


def test_classify_section_requires_section_or_custom_elements() -> None:
    with pytest.raises(ValueError):
        classify_section(fy_mpa=355.0)


def test_classify_section_from_dict_for_custom_column() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.UC,
        data={"d": 420.0, "tw": 14.0, "b": 320.0, "tf": 24.0},
        fy_mpa=355.0,
    )

    assert {item.name for item in result.elements} == {"web", "flange"}


def test_classify_section_from_dict_rejects_bending_for_angle_sections() -> None:
    with pytest.raises(NotImplementedError):
        classify_section_from_dict(
            section_type=SectionType.L_EQUAL,
            data={"h": 100.0, "t": 10.0},
            fy_mpa=355.0,
            stress_pattern="bending-major-axis",
        )


def test_classify_section_from_dict_rejects_unsupported_section_type() -> None:
    with pytest.raises(NotImplementedError):
        classify_section_from_dict(
            section_type=SectionType.Sigma,
            data={"hw": 140.0, "tn": 1.0},
            fy_mpa=355.0,
        )


def test_classify_section_custom_elements_for_hollow_profile() -> None:
    # SHS-style example: internal wall only, no outstand element.
    result = classify_section(
        custom_elements=[ElementInput(name="wall", kind="internal", c_mm=120.0, t_mm=8.0)],
        fy_mpa=355.0,
    )

    assert len(result.elements) == 1
    assert result.elements[0].name == "wall"
    assert result.elements[0].kind == "internal"


def test_element_input_is_pydantic_friendly() -> None:
    payload = ElementInput(
        name="web",
        kind="internal",
        c_mm=360.4,
        t_mm=7.7,
        stress=ElementStressCase.COMBINED,
        alpha=0.70,
    )

    assert payload.model_dump()["stress"] == ElementStressCase.COMBINED
    assert payload.model_dump()["alpha"] == 0.70


def test_public_eu_api_exports_classification_helpers() -> None:
    section = IPE("IPE-750x220")

    result = public_classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=PublicStressPattern.MAJOR_AXIS_BENDING,
    )

    assert result.section_class == SectionClass.CLASS_1
    assert result.elements[0].stress in {ElementStressCase.BENDING, ElementStressCase.COMPRESSION}
