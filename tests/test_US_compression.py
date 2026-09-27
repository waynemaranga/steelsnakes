from __future__ import annotations

import math

import pytest

from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.US import compression
from steelsnakes.US.checks.compression import (
    BuiltUpCompressionResult,
    EffectiveWidthCase,
    SingleAngleCompressionResult,
    SlenderElementInput,
    TorsionalBucklingCase,
    TorsionalBucklingResult,
    _single_angle_shear_center,
    calculate_c2,
    calculate_modified_slenderness,
    calculate_single_angle_slenderness,
    check_compression_slenderness,
    check_flexural_buckling,
    check_slender_element_compression,
    check_torsional_buckling,
    compression_utilisation,
    effective_width,
    nominal_stress,
    round_hss_effective_area,
)
from steelsnakes.US.sections.angles import L2L_LLBB, L_UNEQUAL
from steelsnakes.US.sections.beams import W_beam
from steelsnakes.US.sections.hollow import HSS_RCT
from steelsnakes.US.sections.pipes import PIPE
from steelsnakes.US.sections.tees import WT


def test_nominal_stress_E3_2_and_E3_3() -> None:
    assert nominal_stress(50.0, 83.3) == pytest.approx(38.9, rel=2e-3) # E3-2
    assert nominal_stress(50.0, 16.2) == pytest.approx(0.877 * 16.2) # E3-3


def test_check_flexural_buckling_requires_length() -> None:
    with pytest.raises(ValueError):
        check_flexural_buckling(50.0, 10.0, 2.0)


# AISC Design Examples (v16.0)
def test_example_E1C_W14x132() -> None:
    result = compression(section=W_beam("W14X132"), Fy=50.0, L=30 * 12)

    assert result.limit_state == LimitState.FLEXURAL_BUCKLING
    assert result.section_class == SectionClass.NONSLENDER_ELEMENT
    assert result.phi_c_Pn == pytest.approx(892.0, rel=5e-3)


def test_example_E1D_W14x90_x_axis_governs() -> None:
    result = compression(section=W_beam("W14X90"), Fy=50.0, Lx=360.0, Ly=180.0, Lz=180.0)

    assert result.metadata["section_type"] == "W"
    assert getattr(result, "axis") == "x"
    assert result.Fe == pytest.approx(83.3, rel=2e-3)
    assert result.phi_c_Pn == pytest.approx(927.0, rel=2e-3)
    assert {check.limit_state for check in result.checks} == {LimitState.FLEXURAL_BUCKLING, LimitState.TORSIONAL_BUCKLING}


@pytest.mark.parametrize(("Lc", "Pn"), [(60.0, 349.0), (120.0, 210.0), (180.0, 96.8)])
def test_example_E1E_W16x31_slender_web(Lc: float, Pn: float) -> None:
    result = compression(section=W_beam("W16X31"), Fy=50.0, L=Lc)

    assert result.section_class == SectionClass.SLENDER_ELEMENT
    assert result.Pn == pytest.approx(Pn, rel=1e-2)


def test_example_E1E_effective_area_at_5ft() -> None:
    result = compression(section=W_beam("W16X31"), Fy=50.0, L=60.0)
    assert result.Ae == pytest.approx(8.44, rel=5e-3)
    assert result.metadata["effective_widths"]["web"] == pytest.approx(11.7, rel=5e-3)


def test_example_E5_double_angle_with_intermediate_connectors() -> None:
    result = compression(
        section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), Fy=50.0, L=96.0, a=32.0, ri=0.719, connectors="welded", properties={"J": 2 * 0.132}
    )

    built_up = next(check for check in result.checks if isinstance(check, BuiltUpCompressionResult))
    ftb = next(check for check in result.checks if isinstance(check, TorsionalBucklingResult))
    assert built_up.Lc_r_m == pytest.approx(61.0, rel=2e-3)
    assert built_up.Fe == pytest.approx(76.9, rel=2e-3)
    assert ftb.Fe == pytest.approx(60.5, rel=5e-3)
    assert result.Fe == pytest.approx(48.5, rel=2e-3)
    assert result.phi_c_Pn == pytest.approx(157.0, rel=3e-3)


def test_double_angle_approximates_J_when_missing() -> None:
    result = compression(section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), Fy=50.0, L=96.0)
    assert any("J approximated" in note for note in result.metadata["notes"])


def test_example_E7_WT7x34_x_axis_flexural_buckling_governs() -> None:
    result = compression(section=WT("WT7X34"), Fy=50.0, L=240.0)

    ftb = next(check for check in result.checks if isinstance(check, TorsionalBucklingResult))
    assert ftb.Fez == pytest.approx(165.0, rel=5e-3)
    assert ftb.Fe == pytest.approx(29.5, rel=5e-3)
    assert result.limit_state == LimitState.FLEXURAL_BUCKLING
    assert result.phi_c_Pn == pytest.approx(128.0, rel=5e-3)


def test_example_E8_WT7x15_flexural_torsional_buckling_governs() -> None:
    result = compression(section=WT("WT7X15"), Fy=50.0, L=240.0)

    assert isinstance(result, TorsionalBucklingResult)
    assert result.limit_state == LimitState.TORSIONAL_FLEXURAL_BUCKLING
    assert result.H == pytest.approx(0.771, rel=2e-3)
    assert result.Fe == pytest.approx(10.5, rel=5e-3)
    assert result.phi_c_Pn == pytest.approx(36.6, rel=3e-3)


def test_example_E10_HSS12x8x3_16_slender_walls() -> None:
    result = compression(section=HSS_RCT("HSS12X8X3/16"), Fy=50.0, L=24 * 12)

    assert result.Fn == pytest.approx(29.1, rel=3e-3)
    assert result.Ae == pytest.approx(5.77, rel=5e-3)
    assert result.phi_c_Pn == pytest.approx(151.0, rel=5e-3)


def test_example_E11_pipe10_std() -> None:
    result = compression(section=PIPE("Pipe10STD"), Fy=35.0, Lx=360.0, Ly=180.0, Lz=180.0)
    assert result.phi_c_Pn == pytest.approx(221.0, rel=5e-3)


def test_example_E14A_single_angle_E5() -> None:
    result = compression(section=L_UNEQUAL("L5X3X1/2"), Fy=50.0, L=60.0)

    assert isinstance(result, SingleAngleCompressionResult)
    assert result.equation == "E5-1"
    assert result.ra == pytest.approx(0.824)
    assert result.Lc_r == pytest.approx(126.6, rel=2e-3)
    # the example rounds Lc/r to 127 before computing Fe (17.7 ksi vs 17.86 ksi unrounded), hence the wider tolerance
    assert result.phi_c_Pn == pytest.approx(52.3, rel=1.5e-2)
    assert result.metadata["ftb_required"] is False


def test_single_angle_E3_method_uses_principal_axes() -> None:
    result = compression(section=L_UNEQUAL("L5X3X1/2"), Fy=50.0, L=60.0, single_angle_method="E3")
    assert {getattr(check, "axis") for check in result.checks} == {"z", "w"}
    assert getattr(result, "axis") == "z"


def test_single_angle_slenderness_variants() -> None:
    assert calculate_single_angle_slenderness(100.0, 1.0, 0.6, 5.0, 5.0)[1] == "E5-2"
    Lc_r, equation = calculate_single_angle_slenderness(60.0, 1.0, 0.6, 5.0, 3.0, connected_leg="short", truss="box")
    assert equation == "E5-3"
    assert Lc_r == pytest.approx(max(60.0 + 0.8 * 60.0 + 6.0 * ((5.0 / 3.0) ** 2 - 1.0), 0.82 * 100.0))


def test_single_angle_shear_center_reproduces_tabulated_ro() -> None:
    data = L_UNEQUAL("L5X3X1/2").get_properties()
    w0, z0 = _single_angle_shear_center(data)
    ro = math.sqrt(w0**2 + z0**2 + (data["Iw"] + data["Iz"]) / data["A"])
    assert ro == pytest.approx(data["ro"], rel=5e-3)


def test_torsional_buckling_E4_10_without_offset_matches_E4_2() -> None:
    kwargs = {"Fy": 50.0, "Ag": 26.5, "J": 4.06, "Lz": 180.0, "Ix": 999.0, "Iy": 362.0}
    ho = 13.3
    offset = check_torsional_buckling(TorsionalBucklingCase.MINOR_AXIS_BRACING_OFFSET, h0=ho, ya=0.0, **kwargs)
    doubly = check_torsional_buckling("E4-2", Cw=kwargs["Iy"] * ho**2 / 4, **kwargs)
    assert offset.Fe == pytest.approx(doubly.Fe)

    major = check_torsional_buckling("E4-12", h0=ho, xa=2.0, **kwargs)
    minor = check_torsional_buckling("E4-10", h0=ho, ya=2.0, **kwargs)
    assert major.limit_state == minor.limit_state == LimitState.TORSIONAL_BUCKLING
    assert major.r02 == pytest.approx(minor.r02)


def test_torsional_buckling_E4_4_reduces_to_E4_3_for_one_axis_of_symmetry() -> None:
    kwargs = {"Fy": 50.0, "Ag": 5.0, "J": 0.5, "Lz": 120.0, "Ix": 30.0, "Iy": 10.0, "rx": math.sqrt(6.0), "ry": math.sqrt(2.0), "Lx": 120.0, "Ly": 120.0}
    singly = check_torsional_buckling("E4-3", x0=1.2, y0=0.0, axis_of_symmetry="x", **kwargs)
    unsymmetric = check_torsional_buckling(TorsionalBucklingCase.UNSYMMETRIC, x0=1.2, y0=0.0, **kwargs)
    assert unsymmetric.Fe == pytest.approx(min(singly.Fe, singly.Fey))


def test_torsional_buckling_rejects_unknown_case() -> None:
    with pytest.raises(ValueError):
        check_torsional_buckling("E4-99", Fy=50.0, Ag=1.0, J=1.0, Lz=1.0)


def test_modified_slenderness_E6() -> None:
    assert calculate_modified_slenderness(100.0, 30.0, 1.0, "snug_tight") == (pytest.approx(math.hypot(100.0, 30.0)), "E6-1")
    assert calculate_modified_slenderness(100.0, 30.0, 1.0, "welded") == (100.0, "E6-2a")
    assert calculate_modified_slenderness(100.0, 50.0, 1.0, "pretensioned", Ki=0.5)[0] == pytest.approx(math.hypot(100.0, 25.0))


def test_effective_width_example_E1E_and_c2() -> None:
    lambda_r = 1.49 * math.sqrt(29000.0 / 50.0)
    he = effective_width(51.6 * 0.275, 51.6, lambda_r, 50.0, 41.3, EffectiveWidthCase.STIFFENED)
    assert he == pytest.approx(11.7, rel=5e-3)
    assert effective_width(10.0, 20.0, lambda_r, 50.0, 41.3) == pytest.approx(10.0)
    assert calculate_c2(0.18) == pytest.approx(1.31, abs=5e-3)


def test_round_hss_effective_area_and_limit() -> None:
    assert round_hss_effective_area(10.0, 0.1, 3.0, 50.0) == pytest.approx((0.038 * 580.0 / 100.0 + 2.0 / 3.0) * 3.0)
    assert round_hss_effective_area(10.0, 0.5, 3.0, 50.0) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        round_hss_effective_area(30.0, 0.1, 3.0, 50.0)


def test_check_slender_element_compression_standalone() -> None:
    elements = [SlenderElementInput(name="web", b=14.19, t=0.275, lambda_r=35.9, case=EffectiveWidthCase.STIFFENED)]
    result = check_slender_element_compression(50.0, 41.3, 9.13, elements=elements)
    assert result.Ae == pytest.approx(8.44, rel=5e-3)
    assert result.reference is not None and result.reference.equation == "E7-3"
    with pytest.raises(ValueError):
        check_slender_element_compression(50.0, 41.3, 9.13)


def test_compression_from_dict_and_length_validation() -> None:
    properties = W_beam("W14X90").get_properties()
    result = compression(section_type=SectionType.W, properties=properties, Lx=360.0, Ly=180.0, Lz=180.0)
    assert result.phi_c_Pn == pytest.approx(927.0, rel=2e-3)

    with pytest.raises(ValueError):
        compression(section=W_beam("W14X90"))


def test_compression_utilisation_and_slenderness() -> None:
    assert compression_utilisation(840.0, 927.0).adequacy == "OK"
    assert check_compression_slenderness(360.0, 1.5).adequacy == "FAILS"


def test_example_E6_double_angle_with_slender_elements() -> None:
    # J and Cw from Manual Table 1-7 are per angle; the double angle has twice each
    result = compression(
        section=L2L_LLBB("2L5X3X1/4X3/4LLBB"), Fy=50.0, L=96.0, a=32.0, ri=0.652, connectors="welded",
        properties={"J": 2 * 0.0438, "Cw": 2 * 0.0606},
    )
    built_up = next(check for check in result.checks if isinstance(check, BuiltUpCompressionResult))
    ftb = next(check for check in result.checks if isinstance(check, TorsionalBucklingResult))
    assert built_up.Lc_r_m == pytest.approx(76.3, rel=2e-3)
    assert built_up.Fe == pytest.approx(49.2, rel=2e-3)
    assert ftb.Fe == pytest.approx(26.8, rel=2e-3)
    assert result.limit_state == LimitState.TORSIONAL_FLEXURAL_BUCKLING
    assert result.Fn == pytest.approx(22.9, rel=2e-3)
    assert result.Ae == pytest.approx(3.58, rel=2e-3) # the 5 in. leg is slender: be = 4.39 in.
    assert result.phi_c_Pn == pytest.approx(0.90 * 22.9 * 3.58, rel=3e-3)


def test_example_E9_HSS12x10x3_8_without_slender_elements() -> None:
    result = compression(section=HSS_RCT("HSS12X10X3/8"), Fy=50.0, L=16 * 12) # K = 0.8 on 20 ft
    assert result.Fe == pytest.approx(125.0, rel=3e-3)
    assert result.Fn == pytest.approx(42.3, rel=2e-3)
    assert result.phi_c_Pn == pytest.approx(556.0, rel=2e-3)


def test_example_E1B_W14x90_x_axis_governs_by_specification() -> None:
    # The example uses Manual Table 4-1a at a conservative Lc = 19 ft (903 kips); the specification gives Lcx/rx = 58.6
    result = compression(section=W_beam("W14X90"), Fy=50.0, Lx=30 * 12, Ly=15 * 12, Lz=15 * 12)
    assert result.phi_c_Pn >= 903.0
    assert result.phi_c_Pn == pytest.approx(927.0, rel=3e-3)
