from __future__ import annotations

import pytest

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.US import (
    ClassificationContext as PublicClassificationContext,
    StressPattern as PublicStressPattern,
    classify_section as public_classify_section,
)
from steelsnakes.US.checks.classification import (
    ClassificationContext,
    CompressionCase,
    ElementInput,
    FlexureCase,
    StressPattern,
    angle_section_elements,
    classify_compression,
    classify_elements,
    classify_flexure,
    classify_section,
    classify_section_from_dict,
)
from steelsnakes.US.sections.angles import EqualAngle
from steelsnakes.US.sections.beams import WideFlangeBeam
from steelsnakes.US.sections.channels import StandardChannel
from steelsnakes.US.sections.hollow import RectangularHSS, RoundHSS
from steelsnakes.US.sections.tees import WideFlangeTee


def test_classify_compression_case1_returns_nonslender_element() -> None:
    result = classify_compression("case1", E=29000.0, Fy=50.0, b=6.0, t=0.75)

    assert result.section_class == SectionClass.NONSLENDER_ELEMENT
    assert result.metadata["case"] == "case1"


def test_case_enums_expose_string_values_and_descriptions() -> None:
    assert CompressionCase.CASE_1.value == "case1"
    assert CompressionCase.CASE_1.label == "case1"
    assert "Flanges of rolled I-shaped sections" in CompressionCase.CASE_1.description
    assert FlexureCase.CASE_10.value == "case10"
    assert FlexureCase.CASE_10.label == "case10"
    assert "compression flanges" in FlexureCase.CASE_10.description.lower()


def test_case11_requires_explicit_built_up_information() -> None:
    with pytest.raises(ValueError):
        classify_flexure(FlexureCase.CASE_11, E=29000.0, Fy=50.0, b=6.0, t=0.75, h=20.0, tw=0.5)


def test_case11_can_compute_fl_from_slender_web_flag() -> None:
    result = classify_flexure(
        FlexureCase.CASE_11,
        E=29000.0,
        Fy=50.0,
        b=6.0,
        t=0.75,
        h=20.0,
        tw=0.5,
        web_is_slender=True,
    )

    assert result.metadata["Fl"] == pytest.approx(35.0)


def test_case11_can_compute_fl_from_section_moduli_ratio() -> None:
    result = classify_flexure(
        FlexureCase.CASE_11,
        E=29000.0,
        Fy=50.0,
        b=6.0,
        t=0.75,
        h=20.0,
        tw=0.5,
        web_is_slender=False,
        Sxt=4.0,
        Sxc=10.0,
    )

    assert result.metadata["Fl"] == pytest.approx(25.0)


def test_classify_compression_case9_returns_slender_element() -> None:
    result = classify_compression("case9", E=29000.0, Fy=50.0, D=42.0, t=0.5)

    assert result.section_class == SectionClass.SLENDER_ELEMENT
    assert result.metadata["lambda_r"] == pytest.approx(63.8, rel=1e-3)


def test_classify_flexure_case10_returns_compact() -> None:
    result = classify_flexure(FlexureCase.CASE_10, E=29000.0, Fy=50.0, b=6.0, t=0.75)

    assert result.section_class == SectionClass.COMPACT
    assert result.metadata["lambda_p"] == pytest.approx(9.152, rel=1e-3)


def test_classify_flexure_case20_uses_linear_round_hss_limits() -> None:
    result = classify_flexure("case20", E=29000.0, Fy=50.0, D=25.0, t=0.5)

    assert result.section_class == SectionClass.NONCOMPACT
    assert result.metadata["lambda_p"] == pytest.approx(40.6, rel=1e-3)
    assert result.metadata["lambda_r"] == pytest.approx(179.8, rel=1e-3)


def test_classify_elements_governing_class_is_worst_for_major_axis_bending() -> None:
    elements = [
        ElementInput(name="web", ratio_label="h/tw", wttr=40.0, compression_case="case5", flexure_case="case15"), # pyright: ignore[reportArgumentType] # FIXME: Literal vs CustomType
        ElementInput(name="flange", ratio_label="bf/2tf", wttr=14.0, compression_case="case1", flexure_case="case10"), # pyright: ignore[reportArgumentType] # FIXME: Literal vs CustomType
    ]

    result = classify_elements(elements, E_ksi=29000.0, Fy_ksi=50.0, stress_pattern=StressPattern.MAJOR_AXIS_BENDING)

    assert result.section_class == SectionClass.NONCOMPACT
    assert "flange" in result.governing_elements


def test_classification_context_and_stress_pattern_aliases_match() -> None:
    assert ClassificationContext.AXIAL_COMPRESSION == StressPattern.COMPRESSION
    assert ClassificationContext.FLEXURE_MAJOR_AXIS == StressPattern.MAJOR_AXIS_BENDING


def test_angle_helper_supports_continuous_contact_case() -> None:
    elements = angle_section_elements(leg_1_over_t=8.0, leg_2_over_t=8.0, continuous_contact=True)
    assert {element.compression_case for element in elements} == {CompressionCase.CASE_1}


def test_classify_section_beam_extracts_web_and_flange() -> None:
    section = WideFlangeBeam(
        designation="TEST-W",
        section_type="W",
        h_tw=32.0,
        bf_2tf=8.0,
    )

    result = classify_section(section=section, E_ksi=29000.0, Fy_ksi=50.0)

    assert {item.name for item in result.elements} == {"web", "flange"}
    assert result.section_class == SectionClass.NONSLENDER_ELEMENT


def test_classify_section_beam_major_axis_bending_uses_flexure_cases() -> None:
    section = WideFlangeBeam(
        designation="TEST-W",
        section_type="W",
        h_tw=32.0,
        bf_2tf=8.0,
    )

    result = classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    cases = {item.name: item.case for item in result.elements}
    assert cases == {"web": FlexureCase.CASE_15, "flange": FlexureCase.CASE_10}
    assert result.section_class == SectionClass.COMPACT


def test_classify_section_beam_minor_axis_bending_filters_to_flange_case13() -> None:
    section = WideFlangeBeam(
        designation="TEST-W",
        section_type="W",
        h_tw=32.0,
        bf_2tf=8.0,
    )

    result = classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        classification_context=ClassificationContext.FLEXURE_MINOR_AXIS,
    )

    assert [item.name for item in result.elements] == ["flange"]
    assert result.elements[0].case == FlexureCase.CASE_13
    assert result.section_class == SectionClass.COMPACT


def test_classify_section_channel_minor_axis_bending_filters_to_flange_case13() -> None:
    section = StandardChannel(
        designation="TEST-C",
        section_type="C",
        h_tw=28.0,
        b_t=7.5,
    )

    result = classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        classification_context=ClassificationContext.FLEXURE_MINOR_AXIS,
    )

    assert [item.name for item in result.elements] == ["flange"]
    assert result.elements[0].case == FlexureCase.CASE_13


def test_classify_section_round_hss_extracts_wall() -> None:
    section = RoundHSS(
        designation="TEST-HSS",
        section_type="HSS_RND",
        D_t=30.0,
    )

    result = classify_section(section=section, E_ksi=29000.0, Fy_ksi=50.0)

    assert [item.name for item in result.elements] == ["wall"]
    assert result.section_class == SectionClass.NONSLENDER_ELEMENT


def test_classify_section_rectangular_hss_major_axis_bending_extracts_web_and_flange() -> None:
    section = RectangularHSS(
        designation="TEST-RHSS",
        section_type="HSS_RCT",
        h_tdes=42.0,
        b_tdes=18.0,
    )

    result = classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    assert {item.name for item in result.elements} == {"web", "flange"}
    assert {item.case for item in result.elements} == {FlexureCase.CASE_17, FlexureCase.CASE_19}


def test_rectangular_hss_can_fall_back_to_outside_dimensions() -> None:
    section = RectangularHSS(
        designation="TEST-RHSS",
        section_type="HSS_RCT",
        Ht=10.0,
        B=6.0,
        tdes=0.5,
    )

    elements = section.classification_elements()
    ratios = {element.name: element.wttr for element in elements}

    assert ratios["web"] == pytest.approx((10.0 - 1.5) / 0.5)
    assert ratios["flange"] == pytest.approx((6.0 - 1.5) / 0.5)


def test_classify_section_tee_extracts_stem_and_flange_and_uses_case10_for_flange_flexure() -> None:
    section = WideFlangeTee(
        designation="TEST-WT",
        D_t=10.0,
        bf_2tf=6.0,
    )

    result = classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
    )

    cases = {item.name: item.case for item in result.elements}
    assert cases == {"stem": FlexureCase.CASE_14, "flange": FlexureCase.CASE_10}


def test_classify_section_angle_is_compression_only_for_now() -> None:
    section = EqualAngle(
        designation="L4X4X1/2",
        d=4.0,
        b=4.0,
        t=0.5,
    )

    compression = classify_section(section=section, E_ksi=29000.0, Fy_ksi=50.0)
    assert {item.name for item in compression.elements} == {"leg_1", "leg_2"}

    with pytest.raises(NotImplementedError):
        classify_section(
            section=section,
            E_ksi=29000.0,
            Fy_ksi=50.0,
            stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
        )


def test_classify_section_rejects_i_shape_without_h_tw() -> None:
    section = WideFlangeBeam(
        designation="TEST-W",
        section_type="W",
        d=20.0,
        tw=0.5,
        bf_2tf=8.0,
    )

    with pytest.raises(ValueError):
        classify_section(section=section, E_ksi=29000.0, Fy_ksi=50.0)


def test_classify_section_from_dict_for_i_section_major_axis_bending() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.W,
        data={"h_tw": 32.0, "bf_2tf": 8.0},
        E_ksi=29000.0,
        Fy_ksi=50.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )

    assert result.section_class == SectionClass.COMPACT
    assert {item.case for item in result.elements} == {FlexureCase.CASE_10, FlexureCase.CASE_15}


def test_classify_section_from_dict_rejects_missing_h_tw_for_i_shape() -> None:
    with pytest.raises(ValueError):
        classify_section_from_dict(
            section_type=SectionType.W,
            data={"d": 20.0, "tw": 0.5, "bf_2tf": 8.0},
            E_ksi=29000.0,
            Fy_ksi=50.0,
        )


def test_classify_section_from_dict_rectangular_hss_accepts_outside_dimensions() -> None:
    result = classify_section_from_dict(
        section_type=SectionType.HSS_RCT,
        data={"Ht": 10.0, "B": 6.0, "tdes": 0.5},
        E_ksi=29000.0,
        Fy_ksi=46.0,
        classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
    )

    ratios = {item.name: item.wttr for item in result.elements}
    assert ratios["web"] == pytest.approx((10.0 - 1.5) / 0.5)
    assert ratios["flange"] == pytest.approx((6.0 - 1.5) / 0.5)


def test_public_us_api_exports_section_classifier() -> None:
    section = WideFlangeBeam(designation="TEST-W", section_type="W", h_tw=32.0, bf_2tf=8.0)

    result = public_classify_section(
        section=section,
        E_ksi=29000.0,
        Fy_ksi=50.0,
        classification_context=PublicClassificationContext.FLEXURE_MAJOR_AXIS,
    )

    assert result.section_class == SectionClass.COMPACT
    assert result.classification_context == PublicStressPattern.MAJOR_AXIS_BENDING
