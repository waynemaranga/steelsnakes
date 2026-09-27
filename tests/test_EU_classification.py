from __future__ import annotations

import pytest
from pydantic import ValidationError

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.exceptions import SectionClass4Error
from steelsnakes.base.sections import SectionType
from steelsnakes.EU import IPE, classify_section as public_classify_section
from steelsnakes.EU.checks.classification import (
    ElementInput,
    ElementStressDistribution,
    classify_circular_hollow,
    classify_element,
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
        stress=ElementStressDistribution.BENDING,
    )

    assert result.stress == ElementStressDistribution.BENDING
    assert result.section_class == SectionClass.CLASS_1


def test_classify_internal_part_in_combined_loading_uses_alpha() -> None:
    result = classify_internal_part(
        c_mm=360.4,
        t_mm=7.7,
        fy_mpa=275.0,
        name="web",
        stress=ElementStressDistribution.COMBINED,
        alpha=0.70,
    )

    assert result.stress == ElementStressDistribution.COMBINED
    assert result.section_class == SectionClass.CLASS_2
    assert result.class_3_limit is None


def test_classify_internal_part_in_combined_loading_requires_psi_for_class_3_limit() -> None:
    with pytest.raises(ValueError):
        classify_internal_part(
            c_mm=420.0,
            t_mm=7.7,
            fy_mpa=275.0,
            name="web",
            stress=ElementStressDistribution.COMBINED,
            alpha=0.70,
        )


def test_classify_outstand_flange_bending_uses_same_limits_as_compression() -> None:
    compression_result = classify_outstand_flange(
        c_mm=60.0,
        t_mm=10.0,
        fy_mpa=355.0,
        name="flange",
        stress=ElementStressDistribution.COMPRESSION,
    )
    bending_result = classify_outstand_flange(
        c_mm=60.0,
        t_mm=10.0,
        fy_mpa=355.0,
        name="flange",
        stress=ElementStressDistribution.BENDING,
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


def test_classify_section_beam_bending_sets_all_elements_to_bending() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=ElementStressDistribution.BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressDistribution.BENDING
    assert stress_cases["flange"] == ElementStressDistribution.BENDING


def test_classify_section_beam_accepts_string_stress_pattern() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressDistribution.BENDING
    assert stress_cases["flange"] == ElementStressDistribution.BENDING


def test_classify_section_accepts_string_typo_for_compression() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern="comprression",
    )

    assert {item.stress for item in result.elements} == {ElementStressDistribution.COMPRESSION}


def test_classify_section_angle_extracts_one_angle_element() -> None:
    section = EqualAngle(designation="100x100x10", hxh="100x100", t=10.0)

    result = classify_section(section=section, fy_mpa=355.0)

    assert [item.name for item in result.elements] == ["angle"]
    assert {item.kind for item in result.elements} == {"angle"}
    assert result.section_class in {SectionClass.CLASS_3, SectionClass.CLASS_4}


def test_angle_custom_element_uses_sheet_3_limits() -> None:
    result = classify_section(
        custom_elements=[
            ElementInput(
                name="angle",
                kind="angle",
                c_mm=100.0,
                h_mm=100.0,
                b_mm=75.0,
                t_mm=10.0,
            )
        ],
        fy_mpa=355.0,
    )

    assert result.section_class == SectionClass.CLASS_3
    assert result.elements[0].metadata["h_over_t_limit"] > 0.0
    assert result.elements[0].metadata["b_plus_h_over_2t_limit"] > 0.0


def test_angle_custom_element_reports_governing_ratio_in_result_fields() -> None:
    result = classify_element(
        ElementInput(
            name="angle",
            kind="angle",
            c_mm=100.0,
            h_mm=100.0,
            b_mm=130.0,
            t_mm=10.0,
        ),
        fy_mpa=355.0,
    )

    assert result.section_class == SectionClass.CLASS_4
    assert result.metadata["governing_check"] == "b_plus_h_over_2t"
    assert result.c_over_t == pytest.approx(float(result.metadata["b_plus_h_over_2t"]))
    assert result.class_3_limit == pytest.approx(
        float(result.metadata["b_plus_h_over_2t_limit"])
    )
    assert result.c_mm == pytest.approx(115.0)


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
        stress_pattern=ElementStressDistribution.BENDING,
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressDistribution.BENDING
    assert stress_cases["flange"] == ElementStressDistribution.BENDING


def test_classify_section_from_dict_accepts_string_stress_pattern() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 360.4, "tw": 7.7, "b": 177.7, "tf": 10.9},
        fy_mpa=275.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web"] == ElementStressDistribution.BENDING
    assert stress_cases["flange"] == ElementStressDistribution.BENDING


def test_classify_section_accepts_minor_axis_alias_as_bending() -> None:
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)

    result = classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern="bending-minor-axis",
    )

    assert {item.stress for item in result.elements} == {ElementStressDistribution.BENDING}


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


def test_classify_section_from_dict_angle_bending_uses_outstand_legs() -> None:
    # Table 5.2 Sheet 3/3 refers angles to the outstand flanges of Sheet 2/3; each full leg against 9ε, 10ε and 14ε
    result = classify_section_from_dict(
        section_type=SectionType.L_EQUAL,
        data={"h": 100.0, "t": 10.0},
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )

    assert {item.name: item.kind for item in result.elements} == {"leg_h": "outstand", "leg_b": "outstand"}
    assert result.elements[0].c_over_t == pytest.approx(10.0)
    assert result.section_class == SectionClass.CLASS_3 # 10ε = 8.14 < 10 <= 14ε = 11.4
    with pytest.raises(NotImplementedError):
        classify_section_from_dict(SectionType.L_EQUAL, {"h": 100.0, "t": 10.0}, fy_mpa=355.0, stress_pattern="combined")


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
        stress=ElementStressDistribution.COMBINED,
        alpha=0.70,
    )

    assert payload.model_dump()["stress"] == ElementStressDistribution.COMBINED
    assert payload.model_dump()["alpha"] == 0.70


def test_element_input_requires_positive_dimensions() -> None:
    with pytest.raises(ValidationError):
        ElementInput(name="web", kind="internal", c_mm=0.0, t_mm=7.7)


def test_public_eu_api_exports_classification_helpers() -> None:
    section = IPE("IPE-750x220")

    result = public_classify_section(
        section=section,
        fy_mpa=355.0,
        stress_pattern=ElementStressDistribution.BENDING,
    )

    assert result.section_class == SectionClass.CLASS_1
    assert result.elements[0].stress == ElementStressDistribution.BENDING


def test_chs_class1_s275() -> None:
    result = classify_circular_hollow(d_t=40.0, fy_mpa=275.0)
    assert result.section_class == SectionClass.CLASS_1


def test_chs_class2_s275() -> None:
    result = classify_circular_hollow(d_t=55.0, fy_mpa=275.0)
    assert result.section_class == SectionClass.CLASS_2


def test_chs_class3_s275() -> None:
    result = classify_circular_hollow(d_t=75.0, fy_mpa=275.0)
    assert result.section_class == SectionClass.CLASS_3


def test_chs_class4_raises() -> None:
    with pytest.raises(SectionClass4Error):
        classify_circular_hollow(d_t=100.0, fy_mpa=275.0)


def test_custom_tubular_element_in_bending_uses_d_over_t() -> None:
    result = classify_element(
        ElementInput(
            name="tube",
            kind="tubular",
            c_mm=42.4,
            dia_mm=42.4,
            t_mm=3.2,
            stress=ElementStressDistribution.BENDING,
        ),
        fy_mpa=355.0,
    )

    assert result.section_class == SectionClass.CLASS_1
    assert result.c_mm == pytest.approx(42.4)
    assert result.c_over_t == pytest.approx(42.4 / 3.2)
    assert result.metadata["diameter_mm"] == pytest.approx(42.4)


def test_rhs_compression_s275() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.HFRHS,
        data={"cw_t": 28.0, "cf_t": 22.0, "t": 10.0},
        fy_mpa=275.0,
    )

    assert result.section_class == SectionClass.CLASS_1


def test_rhs_bending() -> None:
    # Table 5.2 Sheet 1/3: an axis-free "bending" is major-axis bending; the h walls bend, the b walls are in compression
    result = classify_section_from_dict(
        section_type=SectionType.HFRHS,
        data={"cw_t": 50.0, "cf_t": 18.0, "t": 10.0},
        fy_mpa=275.0,
        stress_pattern=ElementStressDistribution.BENDING,
    )

    assert {item.name for item in result.elements} == {"web_wall", "flange_wall"}
    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web_wall"] == ElementStressDistribution.BENDING
    assert stress_cases["flange_wall"] == ElementStressDistribution.COMPRESSION
    assert result.section_class == SectionClass.CLASS_1


def test_rhs_bending_keeps_the_flange_walls_in_compression() -> None:
    # cf/t = 30 at S355 (ε = 0.814): Class 2 as a flange in compression, 33ε = 26.8 < 30 <= 38ε = 30.9, where the bending
    # ... limits (72ε = 58.6) would have made it Class 1
    result = classify_section_from_dict(
        section_type=SectionType.HFRHS,
        data={"cw_t": 40.0, "cf_t": 30.0, "t": 5.0},
        fy_mpa=355.0,
        stress_pattern="bending",
    )

    flange = next(item for item in result.elements if item.name == "flange_wall")
    assert flange.stress == ElementStressDistribution.COMPRESSION
    assert flange.section_class == SectionClass.CLASS_2
    assert result.section_class == SectionClass.CLASS_2


def test_rhs_major_axis_alias_rotates_bending_to_web_wall() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.HFRHS,
        data={"cw_t": 50.0, "cf_t": 18.0, "t": 10.0},
        fy_mpa=275.0,
        stress_pattern="bending-major-axis",
    )

    stress_cases = {item.name: item.stress for item in result.elements}
    assert stress_cases["web_wall"] == ElementStressDistribution.BENDING
    assert stress_cases["flange_wall"] == ElementStressDistribution.COMPRESSION


def test_rhs_minor_axis_alias_can_raise_class4_when_web_wall_returns_to_compression() -> None:
    with pytest.raises(SectionClass4Error):
        classify_section_from_dict(
            section_type=SectionType.HFRHS,
            data={"cw_t": 50.0, "cf_t": 18.0, "t": 10.0},
            fy_mpa=275.0,
            stress_pattern="bending-minor-axis",
        )


def test_shs_compression() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.HFSHS,
        data={"c_t": 30.0, "t": 10.0},
        fy_mpa=355.0,
    )

    assert result.section_class == SectionClass.CLASS_2


def test_shs_axis_aliases_are_equivalent() -> None:
    major = classify_section_from_dict(
        section_type=SectionType.HFSHS,
        data={"c_t": 30.0, "t": 10.0},
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )
    minor = classify_section_from_dict(
        section_type=SectionType.HFSHS,
        data={"c_t": 30.0, "t": 10.0},
        fy_mpa=355.0,
        stress_pattern="bending-minor-axis",
    )

    assert major.section_class == SectionClass.CLASS_2
    assert minor.section_class == SectionClass.CLASS_2
    assert {item.stress for item in major.elements} == {
        ElementStressDistribution.BENDING,
        ElementStressDistribution.COMPRESSION,
    }
    assert {item.stress for item in minor.elements} == {
        ElementStressDistribution.BENDING,
        ElementStressDistribution.COMPRESSION,
    }


def test_classify_section_from_dict_chs() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.HFCHS,
        data={"d_t": 55.0},
        fy_mpa=275.0,
    )

    assert result.section_class == SectionClass.CLASS_2


# --- StressPattern presets, Table 5.2 Sheet 2/3 combined outstands, 5.5.2(9) and 5.5.2(11) ---
def test_stress_pattern_enum_is_public_and_matches_string_aliases() -> None:
    from steelsnakes.EU import StressPattern
    from steelsnakes.UK import StressPattern as UKStressPattern

    assert UKStressPattern is StressPattern
    section = ParallelFlangeBeam(designation="TEST-BEAM", b=200.0, tw=8.0, tf=12.0, d=300.0)
    by_enum = classify_section(section=section, fy_mpa=355.0, stress_pattern=StressPattern.MAJOR_AXIS_BENDING)
    by_string = classify_section(section=section, fy_mpa=355.0, stress_pattern="bending-major-axis")
    assert by_enum == by_string
    rhs = classify_section_from_dict(SectionType.HFRHS, {"cw_t": 30.0, "cf_t": 20.0, "t": 5.0}, fy_mpa=355.0, stress_pattern=StressPattern.MINOR_AXIS_BENDING)
    assert {item.name: item.stress for item in rhs.elements} == {
        "web_wall": ElementStressDistribution.COMPRESSION,
        "flange_wall": ElementStressDistribution.BENDING,
    }


def test_outstand_buckling_factor_en_1993_1_5_table_4_2() -> None:
    from steelsnakes.EU import outstand_buckling_factor

    assert outstand_buckling_factor(1.0, "compression") == pytest.approx(0.43)
    assert outstand_buckling_factor(0.0, "compression") == pytest.approx(0.57)
    assert outstand_buckling_factor(-1.0, "compression") == pytest.approx(0.85)
    assert outstand_buckling_factor(1.0, "tension") == pytest.approx(0.43, abs=2e-3)
    assert outstand_buckling_factor(0.0, "tension") == pytest.approx(1.70, abs=2e-3)
    assert outstand_buckling_factor(-1.0, "tension") == pytest.approx(23.8)
    with pytest.raises(ValueError):
        outstand_buckling_factor(-4.0, "compression")
    with pytest.raises(ValueError):
        outstand_buckling_factor(-1.5, "tension")


def test_combined_outstand_uses_alpha_and_k_sigma() -> None:
    eps = (235.0 / 355.0) ** 0.5
    tip_compression = classify_element(
        ElementInput(name="flange", kind="outstand", c_mm=80.0, t_mm=10.0, stress=ElementStressDistribution.COMBINED, alpha=0.8, psi=0.0),
        fy_mpa=355.0,
    )
    assert tip_compression.class_1_limit == pytest.approx(9.0 * eps / 0.8)
    assert tip_compression.class_2_limit == pytest.approx(10.0 * eps / 0.8)
    assert tip_compression.class_3_limit == pytest.approx(21.0 * eps * 0.57**0.5)
    assert tip_compression.section_class == SectionClass.CLASS_1 # 8.0 <= 9eps/alpha = 9.15

    tip_tension = classify_element(
        ElementInput(name="flange", kind="outstand", c_mm=80.0, t_mm=5.0, stress=ElementStressDistribution.COMBINED, alpha=0.6, psi=-0.5, tip="tension"),
        fy_mpa=355.0,
    )
    assert tip_tension.class_1_limit == pytest.approx(9.0 * eps / (0.6 * 0.6**0.5))
    assert tip_tension.metadata["k_sigma"] == pytest.approx(8.475)
    assert tip_tension.section_class == SectionClass.CLASS_2

    no_psi = classify_element(
        ElementInput(name="flange", kind="outstand", c_mm=80.0, t_mm=10.0, stress=ElementStressDistribution.COMBINED, alpha=0.8),
        fy_mpa=355.0,
    )
    assert no_psi.class_3_limit == pytest.approx(14.0 * eps)
    no_alpha = classify_element(
        ElementInput(name="flange", kind="outstand", c_mm=80.0, t_mm=10.0, stress=ElementStressDistribution.COMBINED),
        fy_mpa=355.0,
    )
    assert no_alpha.class_1_limit == pytest.approx(9.0 * eps)


def test_clause_5_5_2_9_relaxes_class_4_with_sigma_com_ed() -> None:
    web = ElementInput(name="web", kind="internal", c_mm=500.0, t_mm=10.0) # 50 > 42eps = 34.2
    assert classify_element(web, 355.0).section_class == SectionClass.CLASS_4
    relaxed = classify_element(web.model_copy(update={"sigma_com_ed_mpa": 150.0}), 355.0) # 42eps*sqrt(355/150) = 52.6
    assert relaxed.section_class == SectionClass.CLASS_3
    assert relaxed.metadata["clause"] == "5.5.2(9)"
    still_class_4 = classify_element(web.model_copy(update={"sigma_com_ed_mpa": 300.0}), 355.0)
    assert still_class_4.section_class == SectionClass.CLASS_4

    tube = ElementInput(name="wall", kind="tubular", c_mm=100.0, t_mm=1.0, dia_mm=100.0, sigma_com_ed_mpa=200.0) # 100 > 90eps^2 = 59.6
    assert classify_element(tube, 355.0).section_class == SectionClass.CLASS_3 # 59.6*355/200 = 105.8

    angle = ElementInput(name="angle", kind="angle", c_mm=200.0, h_mm=200.0, b_mm=200.0, t_mm=12.0, sigma_com_ed_mpa=100.0) # factor 1.88
    assert classify_element(angle.model_copy(update={"sigma_com_ed_mpa": None}), 355.0).section_class == SectionClass.CLASS_4
    assert classify_element(angle, 355.0).section_class == SectionClass.CLASS_3

    result = classify_elements([web.model_copy(update={"sigma_com_ed_mpa": 150.0})], 355.0)
    assert any("5.5.2(10)" in note for note in result.notes)


def test_clause_5_5_2_11_note_for_class_3_web_with_class_1_or_2_flanges() -> None:
    result = classify_elements(
        [
            ElementInput(name="web", kind="internal", c_mm=320.0, t_mm=10.0), # 32: Class 3 in compression at S355
            ElementInput(name="flange", kind="outstand", c_mm=50.0, t_mm=10.0),
        ],
        355.0,
    )
    assert result.section_class == SectionClass.CLASS_3
    assert any("5.5.2(11)" in note for note in result.notes)
    flange_governs = classify_elements(
        [
            ElementInput(name="web", kind="internal", c_mm=200.0, t_mm=10.0),
            ElementInput(name="flange", kind="outstand", c_mm=110.0, t_mm=10.0),
        ],
        355.0,
    )
    assert flange_governs.notes == []


# --- Table 5.2 Sheet 2/3: c of rolled outstands excludes the root radius ---
def test_rolled_flange_outstand_is_measured_from_the_root_radius() -> None:
    # IPE 300: c = (b - tw - 2r)/2 = (150 - 7.1 - 30)/2 = 56.45 mm; c/t = 5.28 as tabulated (cf/tf)
    section = IPE("IPE-300")
    flange = next(item for item in classify_section(section=section, fy_mpa=355.0).elements if item.name == "flange")

    assert flange.c_mm == pytest.approx(56.45)
    assert flange.c_over_t == pytest.approx(section.cf_tf, abs=0.01)


def test_channel_flange_outstand_excludes_one_root_radius() -> None:
    from steelsnakes.EU.sections.channels import PFC

    # PFC 430x100x64: c = b - tw - r = 100 - 11 - 15 = 74 mm; c/t = 3.89 as tabulated
    section = PFC("430x100x64")
    flange = next(item for item in classify_section(section=section, fy_mpa=355.0).elements if item.name == "flange")
    assert flange.c_mm == pytest.approx(74.0)
    assert flange.c_over_t == pytest.approx(section.cf_tf, abs=0.01)


def test_i_section_elements_without_root_radius_stay_conservative() -> None:
    from steelsnakes.EU.checks.classification import channel_section_elements, i_section_elements

    assert i_section_elements(248.6, 7.1, 150.0, 10.7)[1].c_mm == pytest.approx((150.0 - 7.1) / 2.0)
    assert i_section_elements(248.6, 7.1, 150.0, 10.7, r_mm=15.0)[1].c_mm == pytest.approx(56.45)
    assert channel_section_elements(362.0, 11.0, 100.0, 19.0, r_mm=15.0)[1].c_mm == pytest.approx(74.0)
