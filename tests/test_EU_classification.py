from __future__ import annotations

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.EU.checks.classification import (
    ElementInput,
    classify_elements,
    classify_internal_part,
    classify_outstand_flange,
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


def test_classify_elements_governing_class_is_worst() -> None:
    elements = [
        ElementInput(name="web", kind="internal", c_mm=220.0, t_mm=10.0),
        ElementInput(name="flange", kind="outstand", c_mm=120.0, t_mm=10.0),
    ]

    result = classify_elements(elements, fy_mpa=355.0)

    assert result.section_class == SectionClass.CLASS_4
    assert "flange" in result.governing_elements


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


def test_classify_section_from_dict_for_custom_column() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.UC,
        data={"d": 420.0, "tw": 14.0, "b": 320.0, "tf": 24.0},
        fy_mpa=355.0,
    )

    assert {item.name for item in result.elements} == {"web", "flange"}


def test_classify_section_custom_elements_for_hollow_profile() -> None:
    # SHS-style example: internal wall only, no outstand element.
    result = classify_section(
        custom_elements=[ElementInput(name="wall", kind="internal", c_mm=120.0, t_mm=8.0)],
        fy_mpa=355.0,
    )

    assert len(result.elements) == 1
    assert result.elements[0].name == "wall"
    assert result.elements[0].kind == "internal"
