"""
Tests for the AISC 360-22 checks in SI units on US_Metric sections.

The AISC Design Examples v16.0 are in US customary units; each is reproduced here on the metric twin of its section
(the US and US_Metric tables list the same shapes row by row, e.g W14X90 = W360X134), with the expected value converted
to N or N-mm. The metric tables round to three significant figures, so results agree to about 1%.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

import steelsnakes.US as US
from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.US.checks.compression import TorsionalBucklingResult
from steelsnakes.US.factory import get_US_factory
from steelsnakes.US_Metric import FU_A992, FY_A992, compression, flexure, hss_torsion, shear, tension
from steelsnakes.US_Metric.checks import (
    E_STEEL,
    G_STEEL,
    ClassificationContext,
    FlexureCase,
    angle_beta_w,
    calculate_net_area,
    calculate_Pe1,
    calculate_Pey,
    check_eyebar,
    check_pin_connected_member,
    classify_section,
    classify_section_from_dict,
    metric_properties,
    moment_redistribution_Lm,
)
from steelsnakes.US_Metric.factory import get_US_Metric_factory
from steelsnakes.US_Metric.sections.angles import L2L_LLBB, L_EQUAL, L_UNEQUAL
from steelsnakes.US_Metric.sections.beams import W
from steelsnakes.US_Metric.sections.hollow import HSS_RCT, HSS_RND
from steelsnakes.US_Metric.sections.tees import WT

KIP = 4448.2216 # N
KIP_IN = 112_984.83 # N-mm
IN = 25.4 # mm
KSI = 6.894757 # MPa
DATA = Path(__file__).resolve().parents[1] / "src" / "steelsnakes"


# --- Section data in mm units ---
def test_metric_properties_scale_the_section_tables_to_mm() -> None:
    section_type, data = metric_properties(W("W360X134"))

    assert section_type == SectionType.W
    assert data["A"] == pytest.approx(17_100.0) # mm²
    assert data["Ix"] == pytest.approx(416e6) # 10⁶ mm⁴ -> mm⁴
    assert data["Zx"] == pytest.approx(2570e3) # 10³ mm³ -> mm³
    assert data["J"] == pytest.approx(1690e3) # 10³ mm⁴ -> mm⁴
    assert data["Cw"] == pytest.approx(4300e9) # 10⁹ mm⁶ -> mm⁶
    assert data["h_tw"] == pytest.approx(25.9) # ratios are unchanged
    # properties passed as overrides use the section-table units too
    assert metric_properties(W("W360X134"), properties={"J": 1000.0})[1]["J"] == pytest.approx(1e6)


# --- B4.1 Classification ---
def test_classification_W360X134_noncompact_flange_in_flexure() -> None:
    # User Note F2: W14X90 has noncompact flanges for Fy = 50 ksi [345 MPa]
    result = classify_section(W("W360X134"), classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS)

    assert result.E_MPa == pytest.approx(E_STEEL)
    assert result.Fy_MPa == pytest.approx(FY_A992)
    assert result.section_class == SectionClass.NONCOMPACT
    assert result.governing_elements == ["flange"]
    flange = next(item for item in result.elements if item.name == "flange")
    assert flange.lambda_p == pytest.approx(0.38 * (E_STEEL / FY_A992) ** 0.5)


def test_classification_from_dict_and_minor_axis_hss() -> None:
    result = classify_section_from_dict(SectionType.HSS_RCT, {"h_tdes": 22.8, "b_tdes": 14.2, "tdes": 11.8}, classification_context="flexure_minor_axis")
    cases = {item.name: (item.case, item.wttr) for item in result.elements}

    assert cases == {"web": (FlexureCase.CASE_19, 14.2), "flange": (FlexureCase.CASE_17, 22.8)} # the h walls become the flanges
    assert result.section_class == SectionClass.COMPACT


# --- D. Tension ---
def test_tension_W200X31_3_gross_yielding() -> None:
    result = tension(W("W200X31.3"))

    assert result.phi_t_Pn == pytest.approx(0.90 * FY_A992 * 3970.0, rel=1e-3) # D2-1, N
    assert result.limit_state == LimitState.TENSILE_YIELDING


def test_net_area_uses_the_2_mm_hole_allowance() -> None:
    # B4.3b: a 22 mm hole in a 10 mm plate removes (22 + 2) x 10 mm²
    assert calculate_net_area(1000.0, 10.0, hole_diameters=[22.0]) == pytest.approx(760.0)


def test_pin_connected_member_uses_the_si_constants() -> None:
    # D5.1: be = 2t + 16 mm; Cr = 0.95 for 1 mm < dh - d <= 2 mm
    result = check_pin_connected_member(Fy=345.0, Fu=450.0, t=25.0, d=100.0, dh=101.5, a=90.0, w=210.0)

    assert result.be == pytest.approx(min(2.0 * 25.0 + 16.0, (210.0 - 101.5) / 2.0))
    assert result.Cr == pytest.approx(0.95)
    with pytest.raises(ValueError):
        check_pin_connected_member(Fy=345.0, Fu=450.0, t=25.0, d=100.0, dh=102.5, a=90.0, w=210.0)


def test_eyebar_dimensional_requirements_in_si() -> None:
    # D6.2: t >= 13 mm, dh <= d + 1 mm, and dh <= 5t for Fy > 485 MPa
    result = check_eyebar(Fy=690.0, Fu=760.0, t=12.0, w=100.0, d=90.0, dh=90.5)
    requirements: dict[str, Any] = result.metadata["dimensional_requirements"]

    assert requirements["t >= 13 mm (else external nuts required), D6.2(e)"] is False
    assert requirements["dh <= d + 1 mm, D6.2(c)"] is True
    assert requirements["dh <= 5t for Fy > 485 MPa, D6.2(d)"] is False


# --- E. Compression ---
def test_example_E1D_W360X134() -> None:
    # W14X90, Lcx = 30 ft [9.14 m], Lcy = Lcz = 15 ft [4.57 m]; phi_c*Pn = 927 kips
    result = compression(W("W360X134"), Lx=9144.0, Ly=4572.0, Lz=4572.0)

    assert result.limit_state == LimitState.FLEXURAL_BUCKLING
    assert getattr(result, "axis") == "x"
    assert result.phi_c_Pn == pytest.approx(927.0 * KIP, rel=1e-2)


def test_example_E8_WT180X22_flexural_torsional_buckling() -> None:
    # WT7X15, L = 20 ft [6.10 m]; FTB governs, phi_c*Pn = 36.6 kips
    result = compression(WT("WT180X22"), L=6096.0)

    assert isinstance(result, TorsionalBucklingResult)
    assert result.limit_state == LimitState.TORSIONAL_FLEXURAL_BUCKLING
    assert result.phi_c_Pn == pytest.approx(36.6 * KIP, rel=1e-2)


def test_example_E5_double_angle_with_properties_in_table_units() -> None:
    # 2L4X3-1/2X3/8X3/4LLBB, L = 8 ft, a = 32 in., ri = 0.719 in., J = 2 x 0.132 in⁴ [2 x 54.9 x 10³ mm⁴]; 157 kips
    result = compression(
        L2L_LLBB("2L102X89X9.5X19LLBB"), L=96.0 * IN, a=32.0 * IN, ri=0.719 * IN, connectors="welded", properties={"J": 2.0 * 54.9}
    )

    assert result.phi_c_Pn == pytest.approx(157.0 * KIP, rel=1e-2)


# --- F. Flexure ---
def test_example_F1_2B_W460X74_inelastic_ltb() -> None:
    # W18X50, Lb = 11.7 ft [3.57 m], Cb = 1.01; Mn = 4 060 kip-in.
    result = flexure(W("W460X74"), Lb=11.7 * 12 * IN, Cb=1.01)

    assert result.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    assert result.Mn == pytest.approx(4060.0 * KIP_IN, rel=1e-2)


def test_example_F11A_L102X102X6_4_geometric_axis() -> None:
    # L4X4X1/4 bent about a geometric axis, no LTB restraint, Lb = 6 ft, Cb = 1.14; Mn = 49.2 kip-in. (LTB)
    result = flexure(L_EQUAL("L102X102X6.4"), Lb=72.0 * IN, Cb=1.14, geometric_axis=True)

    assert result.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    assert result.Mn == pytest.approx(49.2 * KIP_IN, rel=1e-2)


def test_unequal_angle_uses_the_metric_beta_w() -> None:
    # Commentary Table C-F10.1: L8x4 [L203x102], beta_w = 5.48 in. [139 mm]; negative with the long leg in compression
    assert angle_beta_w(203.0, 102.0) == pytest.approx(139.0)
    assert angle_beta_w(102.0, 102.0) == 0.0
    metric = flexure(L_UNEQUAL("L203X102X25.4"), Lb=3000.0)
    imperial = US.flexure(section=get_US_factory().create_section("L8X4X1", SectionType.L_UNEQUAL), Fy=50.0, Lb=3000.0 / IN)

    assert getattr(metric, "beta_w") == pytest.approx(-139.0)
    assert metric.Mn == pytest.approx(imperial.Mn * KIP_IN, rel=1e-2)
    with pytest.raises(ValueError):
        angle_beta_w(300.0, 100.0)


# --- G. Shear ---
def test_example_G1B_W610X92_rolled_web() -> None:
    # W24X62: G2.1(a), phi_v = 1.00; phi_v*Vn = 306 kips
    result = shear(W("W610X92"))

    assert result.phi_v == pytest.approx(1.0)
    assert result.phi_v_Vn == pytest.approx(306.0 * KIP, rel=1e-2)


def test_example_G5_HSS406_4X9_5_round() -> None:
    # HSS16.000X0.375, Lv = 16 ft; Fcr = 0.6Fy governs
    result = shear(HSS_RND("HSS406.4X9.5"), Lv=192.0 * IN)

    assert result.Fcr == pytest.approx(0.6 * FY_A992)


# --- H. Combined forces and torsion ---
def test_example_H5A_HSS152_4X101_6X6_4_torsion() -> None:
    # HSS6X4X1/4: phi_T*Tn = 273 kip-in.; C is read in 10³ mm³
    result = hss_torsion(HSS_RCT("HSS152.4X101.6X6.4"))

    assert result.C == pytest.approx(166e3)
    assert result.phi_T_Tn == pytest.approx(273.0 * KIP_IN, rel=1e-2)


# --- C. Stability; Appendices 7 and 8 ---
def test_stability_helpers_default_to_si() -> None:
    assert calculate_Pe1(416e6, 4000.0, direct_analysis=False) == pytest.approx(3.14159**2 * E_STEEL * 416e6 / 4000.0**2, rel=1e-5)
    assert calculate_Pey(151e6, 4000.0) == pytest.approx(3.14159**2 * E_STEEL * 151e6 / 4000.0**2, rel=1e-5)
    assert moment_redistribution_Lm(0.0, 1.0, ry=94.0, Fy=345.0) == pytest.approx(0.12 * E_STEEL / 345.0 * 94.0)
    with pytest.raises(ValueError):
        moment_redistribution_Lm(0.0, 1.0, ry=94.0, Fy=485.0) # App. 8.2: Fy <= 450 MPa


def test_defaults_are_the_si_values() -> None:
    assert (E_STEEL, G_STEEL, FY_A992, FU_A992) == (200_000.0, 77_200.0, 345.0, 450.0)


# --- Metric against imperial, row by row ---
def _twins(section_type: SectionType, stride: int) -> list[tuple[str, str]]:
    us: list[str] = list(json.loads((DATA / "US" / "data" / f"{section_type.value}.json").read_text()))
    metric: list[str] = list(json.loads((DATA / "US_Metric" / "data" / f"{section_type.value}.json").read_text()))
    return list(zip(us, metric))[::stride]


CHECKS: dict[str, tuple[Callable[..., Any], Callable[..., Any], float]] = {
    # name: (imperial check, metric check, unit factor to N or N-mm)
    "compression": (lambda s: US.compression(section=s, Fy=50.0, L=120.0).phi_c_Pn, lambda s: compression(s, Fy=50.0 * KSI, E=29_000.0 * KSI, G=11_200.0 * KSI, L=120.0 * IN).phi_c_Pn, KIP),
    "flexure": (lambda s: US.flexure(section=s, Fy=50.0, Lb=60.0).phi_b_Mn, lambda s: flexure(s, Fy=50.0 * KSI, E=29_000.0 * KSI, Lb=60.0 * IN).phi_b_Mn, KIP_IN),
    "shear": (lambda s: US.shear(section=s, Fy=50.0).phi_v_Vn, lambda s: shear(s, Fy=50.0 * KSI, E=29_000.0 * KSI).phi_v_Vn, KIP),
}


@pytest.mark.parametrize("section_type", [SectionType.W, SectionType.C, SectionType.WT, SectionType.L_EQUAL, SectionType.L2L_EQUAL, SectionType.HSS_RCT, SectionType.HSS_RND, SectionType.PIPE])
@pytest.mark.parametrize("check", list(CHECKS))
def test_metric_twins_match_the_imperial_checks(section_type: SectionType, check: str) -> None:
    imperial_check, metric_check, unit = CHECKS[check]
    us_factory, metric_factory = get_US_factory(), get_US_Metric_factory()
    for us_name, metric_name in _twins(section_type, stride=25):
        us_section = us_factory.create_section(us_name, section_type)
        metric_section = metric_factory.create_section(metric_name, section_type)
        # 1.5%: the metric tables round to three significant figures, e.g C100X9.3 (C4X6.25) ry +0.4%, eo +0.4%, A +0.2% in FTB
        assert metric_check(metric_section) == pytest.approx(imperial_check(us_section) * unit, rel=1.5e-2), (us_name, metric_name)
