"""BS 5950-1:2000 Section 3.5 classification; limits from Tables 11 and 12 (codes/BS5950-CLASSIF.pdf)."""

import json
import math
from pathlib import Path

import pytest

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.BS import (
    CFRHS,
    HFCHS,
    HFRHS,
    L_EQUAL,
    L_EQUAL_B2B,
    L_UNEQUAL,
    PFC,
    UB,
    UC,
    ElementInput,
    ElementKind,
    ElementStressDistribution,
    StressPattern,
    classify_element,
    classify_section,
    classify_section_from_dict,
    compound_flange_elements,
    design_strength,
    effective_plastic_modulus,
    effective_plastic_modulus_i_section,
    element_limits,
    epsilon,
    render_classification,
    stress_ratios,
)

C = ElementStressDistribution.COMPRESSION
B = ElementStressDistribution.BENDING
M = ElementStressDistribution.COMBINED


# --- Table 9 and epsilon ---
@pytest.mark.parametrize(
    ("t", "grade", "py"),
    [(12.7, "S275", 275.0), (16.0, "S275", 275.0), (21.7, "S275", 265.0), (140.0, "S275", 225.0), (12.7, "s355 j2h", 355.0), (45.0, "S355", 335.0), (30.0, "S460", 440.0)],
)
def test_design_strength_table_9(t: float, grade: str, py: float) -> None:
    assert design_strength(t, grade) == py


def test_design_strength_rejects_unknown_grade_and_out_of_range_thickness() -> None:
    with pytest.raises(ValueError, match="Unknown steel_grade"):
        design_strength(10.0, "S235")
    with pytest.raises(ValueError, match="does not cover"):
        design_strength(120.0, "S460")
    with pytest.raises(ValueError, match="positive"):
        design_strength(0.0)


def test_epsilon_is_root_275_over_py() -> None:
    assert epsilon(275.0) == pytest.approx(1.0)
    assert epsilon(355.0) == pytest.approx(0.8801, abs=1e-4)


# --- Table 11 rows ---
@pytest.mark.parametrize(
    ("kind", "stress", "limits"),
    [
        (ElementKind.OUTSTAND_FLANGE_ROLLED, B, (9.0, 10.0, 15.0)),
        (ElementKind.OUTSTAND_FLANGE_WELDED, B, (8.0, 9.0, 13.0)),
        (ElementKind.INTERNAL_FLANGE, B, (28.0, 32.0, 40.0)),
        (ElementKind.INTERNAL_FLANGE, C, (None, None, 40.0)),
        (ElementKind.WEB, B, (80.0, 100.0, 120.0)),
        (ElementKind.WEB, C, (None, None, 40.0)),
        (ElementKind.CHANNEL_WEB, B, (40.0, 40.0, 40.0)),
        (ElementKind.ANGLE_LEG, B, (9.0, 10.0, 15.0)),
        (ElementKind.ANGLE_OUTSTAND_LEG, C, (9.0, 10.0, 15.0)),
        (ElementKind.TEE_STEM, B, (8.0, 9.0, 18.0)),
    ],
)
def test_table_11_limits_at_s275(kind: ElementKind, stress: ElementStressDistribution, limits: tuple) -> None:
    result = element_limits(ElementInput(name="e", kind=kind, stress=stress, b_mm=10.0, t_mm=1.0), py=275.0)
    assert (result.class_1_limit, result.class_2_limit, result.class_3_limit) == limits


def test_table_11_web_generally_positive_r1_and_40_epsilon_floor() -> None:
    limits = element_limits(ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=10.0, t_mm=1.0, r1=0.5, r2=0.25), py=275.0)
    assert limits.class_1_limit == pytest.approx(80.0 / 1.5)
    assert limits.class_2_limit == pytest.approx(100.0 / 1.75)
    assert limits.class_3_limit == pytest.approx(120.0 / 1.5)

    floored = element_limits(ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=10.0, t_mm=1.0, r1=1.0, r2=1.0), py=275.0)
    assert (floored.class_1_limit, floored.class_2_limit, floored.class_3_limit) == (40.0, 40.0, 40.0)


def test_table_11_web_generally_negative_r1_uses_100_over_1_plus_r1() -> None:
    limits = element_limits(ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=10.0, t_mm=1.0, r1=-0.5, r2=-0.2), py=275.0)
    assert limits.class_1_limit == pytest.approx(160.0)
    assert limits.class_2_limit == pytest.approx(200.0)
    assert limits.class_3_limit == pytest.approx(200.0)


def test_web_generally_requires_r1_and_handles_webs_in_tension() -> None:
    with pytest.raises(ValueError, match="r1"):
        element_limits(ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=10.0, t_mm=1.0), py=275.0)
    tension = element_limits(ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=10.0, t_mm=1.0, r1=-1.0, r2=-0.6), py=275.0)
    assert math.isinf(tension.class_1_limit) and math.isinf(tension.class_3_limit)


def test_single_angle_axial_compression_checks_all_three_criteria() -> None:
    within = classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=150.0, t_mm=10.0, leg_mm=90.0), py_mpa=275.0)
    assert within.section_class == SectionClass.CLASS_3
    assert within.metadata["(b+d)/t"] == pytest.approx(24.0)

    too_wide = classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=140.0, t_mm=10.0, leg_mm=110.0), py_mpa=275.0)
    assert too_wide.section_class == SectionClass.CLASS_4
    assert too_wide.metadata["governing_check"] == "(b+d)/t"

    with pytest.raises(ValueError, match="leg_mm"):
        classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=100.0, t_mm=10.0), py_mpa=275.0)


# --- Table 12 rows ---
def test_table_12_chs_uses_epsilon_squared_and_separates_axial_and_bending() -> None:
    bending = element_limits(ElementInput(name="wall", kind=ElementKind.CHS, stress=B, b_mm=10.0, t_mm=1.0), py=355.0)
    eps2 = 275.0 / 355.0
    assert (bending.class_1_limit, bending.class_2_limit, bending.class_3_limit) == pytest.approx((40.0 * eps2, 50.0 * eps2, 140.0 * eps2))
    axial = element_limits(ElementInput(name="wall", kind=ElementKind.CHS, stress=C, b_mm=10.0, t_mm=1.0), py=355.0)
    assert axial.class_1_limit is None and axial.class_3_limit == pytest.approx(80.0 * eps2)
    with pytest.raises(ValueError, match="separately"):
        element_limits(ElementInput(name="wall", kind=ElementKind.CHS, stress=M, b_mm=10.0, t_mm=1.0), py=355.0)


def test_table_12_rhs_flange_limits_depend_on_web_d_t() -> None:
    # HF: 28ε but <= 80ε - d/t; 32ε but <= 62ε - 0.5d/t; 40ε
    hf = element_limits(ElementInput(name="f", kind=ElementKind.HF_RHS_FLANGE, stress=B, b_mm=10.0, t_mm=1.0, web_d_mm=60.0), py=275.0)
    assert (hf.class_1_limit, hf.class_2_limit, hf.class_3_limit) == pytest.approx((20.0, 32.0, 40.0))
    # CF: 26ε but <= 72ε - d/t; 28ε but <= 54ε - 0.5d/t; 35ε
    cf = element_limits(ElementInput(name="f", kind=ElementKind.CF_RHS_FLANGE, stress=B, b_mm=10.0, t_mm=1.0, web_d_mm=60.0), py=275.0)
    assert (cf.class_1_limit, cf.class_2_limit, cf.class_3_limit) == pytest.approx((12.0, 24.0, 35.0))
    with pytest.raises(ValueError, match="web_d_mm"):
        element_limits(ElementInput(name="f", kind=ElementKind.HF_RHS_FLANGE, stress=B, b_mm=10.0, t_mm=1.0), py=275.0)


def test_table_12_rhs_web_rows() -> None:
    hf_mid = element_limits(ElementInput(name="w", kind=ElementKind.HF_RHS_WEB, stress=B, b_mm=10.0, t_mm=1.0), py=275.0)
    assert (hf_mid.class_1_limit, hf_mid.class_2_limit, hf_mid.class_3_limit) == (64.0, 80.0, 120.0)
    cf_gen = element_limits(ElementInput(name="w", kind=ElementKind.CF_RHS_WEB, stress=M, b_mm=10.0, t_mm=1.0, r1=0.5, r2=0.5), py=275.0)
    assert (cf_gen.class_1_limit, cf_gen.class_2_limit, cf_gen.class_3_limit) == pytest.approx((56.0 / 1.3, 70.0 / 1.5, 52.5))
    cf_axial = element_limits(ElementInput(name="w", kind=ElementKind.CF_RHS_WEB, stress=C, b_mm=10.0, t_mm=1.0), py=275.0)
    assert cf_axial.class_3_limit == pytest.approx(35.0)


# --- 3.5.5 stress ratios ---
def test_stress_ratios_equal_flanges_box_and_unequal_flanges() -> None:
    equal = stress_ratios(Fc_kN=500.0, d_mm=407.6, t_mm=8.5, pyw_mpa=275.0, Ag_cm2=85.5)
    assert equal.r1 == pytest.approx(500e3 / (407.6 * 8.5 * 275.0))
    assert equal.r2 == pytest.approx(500e3 / (8550.0 * 275.0))

    box = stress_ratios(Fc_kN=100.0, d_mm=185.0, t_mm=5.0, pyw_mpa=355.0, Ag_cm2=28.7, case="box")
    assert box.r1 == pytest.approx(100e3 / (2 * 185.0 * 5.0 * 355.0))

    unequal = stress_ratios(
        Fc_kN=200.0, d_mm=400.0, t_mm=10.0, pyw_mpa=275.0, case="unequal-flanges",
        Bt_mm=300.0, Tt_mm=20.0, Bc_mm=200.0, Tc_mm=20.0, f1_mpa=200.0, f2_mpa=-100.0,
    )
    assert unequal.r1 == pytest.approx(200e3 / 1.1e6 + (6000.0 - 4000.0) * 275.0 / 1.1e6)
    assert unequal.r2 == pytest.approx(100.0 / 550.0)


def test_stress_ratios_clamp_r1_and_validate_inputs() -> None:
    assert stress_ratios(Fc_kN=5000.0, d_mm=100.0, t_mm=5.0, pyw_mpa=275.0, Ag_cm2=10.0).r1 == 1.0
    assert stress_ratios(Fc_kN=-5000.0, d_mm=100.0, t_mm=5.0, pyw_mpa=275.0, Ag_cm2=10.0).r1 == -1.0
    with pytest.raises(ValueError, match="Ag_cm2"):
        stress_ratios(Fc_kN=10.0, d_mm=100.0, t_mm=5.0, pyw_mpa=275.0)
    with pytest.raises(ValueError, match="Unequal flanges"):
        stress_ratios(Fc_kN=10.0, d_mm=100.0, t_mm=5.0, pyw_mpa=275.0, case="unequal-flanges")
    with pytest.raises(ValueError, match="pyw"):
        stress_ratios(Fc_kN=10.0, d_mm=100.0, t_mm=5.0, pyw_mpa=355.0, pyf_mpa=275.0, case="unequal-flanges", Bt_mm=1, Tt_mm=1, Bc_mm=1, Tc_mm=1, f1_mpa=1, f2_mpa=1)


# --- Section adapters (Figure 5) ---
def test_ub_457x191x67_s275_plastic_in_bending_and_slender_web_in_compression() -> None:
    beam = UB("457x191x67")
    bending = classify_section(beam, stress_pattern="bending-major-axis")
    assert bending.section_class == SectionClass.CLASS_1
    assert bending.class_name == "plastic"
    flange = next(item for item in bending.elements if item.name == "flange")
    assert flange.ratio == pytest.approx(189.9 / 2.0 / 12.7) # Figure 5: rolled I-section b = B/2

    compression = classify_section(beam)
    assert compression.section_class == SectionClass.CLASS_4
    assert compression.is_slender
    assert compression.governing_elements == ["web"]
    assert any("r2 = 1.0" in note for note in compression.notes)


def test_ub_axial_force_moves_web_to_generally_row() -> None:
    beam = UB("457x191x67")
    combined = classify_section(beam, stress_pattern=StressPattern.COMBINED, Fc_kN=500.0)
    web = next(item for item in combined.elements if item.name == "web")
    assert web.stress == M
    assert web.class_1_limit == pytest.approx(80.0 / (1.0 + combined.r1))
    assert combined.section_class == SectionClass.CLASS_1

    major_with_force = classify_section(beam, stress_pattern="bending", Fc_kN=500.0)
    assert next(item for item in major_with_force.elements if item.name == "web").stress == M

    with pytest.raises(ValueError, match="Fc_kN"):
        classify_section(beam, stress_pattern="combined")


def test_minor_axis_bending_skips_web_unless_axial_compression_acts() -> None:
    column = UC("305x305x137")
    minor = classify_section(column, stress_pattern="bending-minor-axis")
    assert [item.name for item in minor.elements] == ["flange"]
    minor_with_force = classify_section(column, stress_pattern="bending-minor-axis", Fc_kN=1000.0)
    assert [item.stress for item in minor_with_force.elements] == [B, C]


def test_uc_in_compression_is_not_slender_and_py_from_flange_thickness() -> None:
    result = classify_section(UC("305x305x137"))
    assert result.py_mpa == 265.0 # T = 21.7 mm
    assert result.section_class == SectionClass.CLASS_3
    assert not result.is_slender
    assert any("not applicable" in note for note in result.notes)


def test_pfc_uses_full_flange_width_and_channel_web_row() -> None:
    result = classify_section(PFC("430x100x64"), stress_pattern="bending")
    flange, web = result.elements
    assert flange.ratio == pytest.approx(100.0 / 19.0)
    assert web.kind == ElementKind.CHANNEL_WEB
    assert result.section_class == SectionClass.CLASS_1


def test_hot_finished_rhs_axes_swap_flange_and_web() -> None:
    rhs = HFRHS("200x100x5.0")
    major = classify_section(rhs, steel_grade="S355", stress_pattern="bending-major-axis")
    by_name = {item.name: item for item in major.elements}
    assert by_name["web_wall"].ratio == pytest.approx(37.0) # d = D - 3t
    assert by_name["flange_wall"].ratio == pytest.approx(17.0) # b = B - 3t
    assert major.section_class == SectionClass.CLASS_1

    minor = classify_section(rhs, steel_grade="S355", stress_pattern="bending-minor-axis")
    assert {item.name: item.ratio for item in minor.elements} == pytest.approx({"flange_wall": 37.0, "web_wall": 17.0})
    assert minor.section_class == SectionClass.CLASS_4

    combined = classify_section(rhs, steel_grade="S355", stress_pattern="combined", Fc_kN=200.0)
    assert combined.r1 == pytest.approx(200e3 / (2 * 185.0 * 5.0 * 355.0))


def test_cold_formed_rhs_uses_d_equals_D_minus_5t() -> None:
    result = classify_section(CFRHS("200x100x5.0"), steel_grade="S355", stress_pattern="bending")
    assert {item.name: item.ratio for item in result.elements} == pytest.approx({"flange_wall": 15.0, "web_wall": 35.0})
    assert result.elements[0].kind == ElementKind.CF_RHS_FLANGE


def test_chs_classified_separately_for_bending_and_compression() -> None:
    chs = HFCHS("168.3x5.0")
    assert classify_section(chs, steel_grade="S355", stress_pattern="bending").section_class == SectionClass.CLASS_2
    assert classify_section(chs, steel_grade="S355").section_class == SectionClass.CLASS_3
    with pytest.raises(ValueError, match="separately"):
        classify_section(chs, stress_pattern="combined")


def test_angles_single_and_back_to_back() -> None:
    assert classify_section(L_UNEQUAL("150x90x10")).section_class == SectionClass.CLASS_3 # (b + d)/t = 24 = 24ε
    assert classify_section(L_UNEQUAL("150x90x10"), steel_grade="S355").section_class == SectionClass.CLASS_4
    bending = classify_section(L_EQUAL("100x100x10.0"), stress_pattern="bending")
    assert [item.kind for item in bending.elements] == [ElementKind.ANGLE_LEG, ElementKind.ANGLE_LEG]
    assert bending.section_class == SectionClass.CLASS_2
    b2b = classify_section(L_EQUAL_B2B("100x100x10"))
    assert b2b.elements[0].kind == ElementKind.ANGLE_OUTSTAND_LEG
    assert b2b.section_class == SectionClass.CLASS_2


def test_classify_section_from_dict_accepts_bs_notation() -> None:
    data = json.loads((Path(__file__).parents[1] / "src/steelsnakes/BS/data/UC.json").read_text())["356x406x1299"]
    result = classify_section_from_dict(SectionType.UC, data, stress_pattern="bending")
    assert result.py_mpa == 225.0 # T = 140 mm
    assert {item.name: round(item.ratio, 2) for item in result.elements} == {"flange": 1.7, "web": 2.9}


def test_classify_section_from_dict_rhs_from_hxb_and_chs_from_d_t() -> None:
    rhs = classify_section_from_dict(SectionType.HFRHS, {"hxb": "200x100", "t": 5.0}, py_mpa=355.0, stress_pattern="bending")
    assert rhs.section_class == SectionClass.CLASS_1
    chs = classify_section_from_dict(SectionType.CFCHS, {"d_t": 30.0, "t": 4.0}, py_mpa=275.0, stress_pattern="bending")
    assert chs.elements[0].ratio == pytest.approx(30.0)


def test_unsupported_inputs_raise() -> None:
    with pytest.raises(NotImplementedError, match="elliptical"):
        classify_section_from_dict(SectionType.HFEHS, {"t": 5.0}, py_mpa=275.0)
    with pytest.raises(NotImplementedError, match="adapter"):
        classify_section_from_dict(SectionType.IPE, {"t": 5.0}, py_mpa=275.0)
    with pytest.raises(ValueError, match="Did you mean"):
        classify_section(UB("457x191x67"), stress_pattern="compresion")
    with pytest.raises(ValueError, match="Missing"):
        classify_section_from_dict(SectionType.UB, {"b": 100.0}, py_mpa=275.0)
    with pytest.raises(ValueError, match="py_mpa"):
        classify_section(custom_elements=[ElementInput(name="e", kind=ElementKind.TEE_STEM, b_mm=100.0, t_mm=10.0)])
    with pytest.raises(ValueError, match="Provide"):
        classify_section()


def test_compound_flange_elements_figure_6() -> None:
    elements = compound_flange_elements(b_mm=95.0, T_mm=10.0, bp_mm=200.0, tp_mm=8.0, bo_mm=70.0)
    result = classify_section(custom_elements=elements, py_mpa=275.0)
    by_name = {item.name: item for item in result.elements}
    assert by_name["compound_flange_outstand"].section_class == SectionClass.CLASS_2 # 9.5: rolled outstand, 9 < b/T <= 10
    assert by_name["flange_plate_internal"].section_class == SectionClass.CLASS_1 # 25 <= 28
    assert by_name["flange_plate_outstand"].section_class == SectionClass.CLASS_2 # 8.75: welded outstand, 8 < b/T <= 9
    assert result.section_class == SectionClass.CLASS_2
    assert len(compound_flange_elements(b_mm=90.0, T_mm=10.0, bp_mm=200.0, tp_mm=8.0)) == 2


# --- 3.5.6 effective plastic modulus ---
def test_effective_plastic_modulus_semi_compact_uc_s355() -> None:
    column = UC("152x152x23") # b/T = 11.19 > 10ε = 8.80: semi-compact flange in S355
    assert classify_section(column, steel_grade="S355", stress_pattern="bending").section_class == SectionClass.CLASS_3
    flange_factor = (13.2021 / (152.2 / 2 / 6.8) - 1.0) / (15.0 / 10.0 - 1.0)
    major = effective_plastic_modulus(column, steel_grade="S355")
    assert major.S_eff == pytest.approx(164.0 + (182.0 - 164.0) * flange_factor, rel=1e-4)
    minor = effective_plastic_modulus(column, steel_grade="S355", axis="minor")
    assert minor.S_eff == pytest.approx(52.6 + (80.1 - 52.6) * flange_factor, rel=1e-4)


def test_effective_plastic_modulus_compact_other_and_formula() -> None:
    assert effective_plastic_modulus(UB("457x191x67")).S_eff == 1470.0 # plastic: Seff = S
    rhs = effective_plastic_modulus(HFRHS("200x100x5.0"), steel_grade="S355")
    assert rhs.S_eff == rhs.Z == 149.0 # 3.5.6.1
    Sx, Sy, web, flange = effective_plastic_modulus_i_section(Sx=100.0, Zx=80.0, Sy=50.0, Zy=30.0, b_T=12.0, d_t=110.0, beta_2f=10.0, beta_3f=15.0, beta_2w=100.0, beta_3w=120.0)
    assert web == pytest.approx(((120 / 110) ** 2 - 1) / ((1.2) ** 2 - 1))
    assert Sx == pytest.approx(80.0 + 20.0 * min(web, flange))
    assert Sy == pytest.approx(30.0 + 20.0 * flange)
    with pytest.raises(ValueError, match="exceed"):
        effective_plastic_modulus_i_section(Sx=1, Zx=1, Sy=1, Zy=1, b_T=1, d_t=1, beta_2f=15, beta_3f=10, beta_2w=100, beta_3w=120)


def test_render_classification_rows() -> None:
    block = render_classification(classify_section(UB("457x191x67"), stress_pattern="combined", Fc_kN=500.0))
    assert block.passed
    assert block.rows[1].clause == "3.5.5"
    assert block.rows[-1].badge == "Class 1 — Plastic"
    assert "\\frac{b}{T}" in block.rows[2].expr
