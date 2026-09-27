from __future__ import annotations

import math

import pytest

from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.US import flexure
from steelsnakes.US.checks.flexure import (
    BendingAxis,
    CompactIShapeFlexureResult,
    NoncompactFlangeIShapeFlexureResult,
    NoncompactWebIShapeFlexureResult,
    SlenderWebIShapeFlexureResult,
    angle_beta_w,
    calculate_Cb,
    calculate_effective_section_modulus,
    calculate_hss_effective_width,
    calculate_Rpg,
    calculate_singly_symmetric_web_lambda_p,
    check_bar_flexure,
    check_double_angle_flexure,
    check_i_shape_proportions,
    check_noncompact_web_i_shape_flexure,
    check_single_angle_flexure,
    check_slender_web_i_shape_flexure,
    check_tee_flexure,
    check_tension_flange_rupture,
    check_unsymmetric_flexure,
    flexure_utilisation,
)
from steelsnakes.US.sections.angles import L2L_LLBB, L_EQUAL, L_UNEQUAL
from steelsnakes.US.sections.beams import W_beam
from steelsnakes.US.sections.channels import C_channel
from steelsnakes.US.sections.hollow import HSS_RCT, HSS_SQR
from steelsnakes.US.sections.pipes import PIPE
from steelsnakes.US.sections.tees import WT


@pytest.mark.parametrize(("moments", "Cb"), [((1.00, 0.972, 1.00, 0.972), 1.01), ((1.00, 0.438, 0.750, 0.938), 1.30), ((0.889, 0.306, 0.556, 0.750), 1.46)])
def test_calculate_Cb_examples_F1(moments: tuple[float, float, float, float], Cb: float) -> None:
    assert calculate_Cb(*moments) == pytest.approx(Cb, abs=5e-3)


# AISC Design Examples (v16.0)
def test_example_F1_2B_W18x50_inelastic_ltb() -> None:
    result = flexure(section=W_beam("W18X50"), Fy=50.0, Lb=11.7 * 12, Cb=1.01)

    assert isinstance(result, CompactIShapeFlexureResult)
    assert result.Lp == pytest.approx(69.9, rel=2e-3)
    assert result.Lr == pytest.approx(203.0, rel=3e-3)
    assert result.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    assert result.Mn == pytest.approx(4060.0, rel=3e-3)


def test_example_F1_3B_W18x50_elastic_ltb_with_moments() -> None:
    result = flexure(section=W_beam("W18X50"), Fy=50.0, Lb=17.5 * 12, moments=(1.00, 0.438, 0.750, 0.938))

    assert result.Cb == pytest.approx(1.30, abs=5e-3)
    assert result.MA == pytest.approx(0.438)
    assert getattr(result, "Fcr") == pytest.approx(43.2, rel=5e-3)
    assert result.Mn == pytest.approx(3840.0, rel=5e-3)


def test_example_F2_2B_C15x33_9_channel() -> None:
    result = flexure(section=C_channel("C15X33.9"), Fy=50.0, Lb=60.0, Cb=1.0)

    assert isinstance(result, CompactIShapeFlexureResult)
    assert result.c_coeff != 1.0
    assert result.Lp == pytest.approx(3.18 * 12, rel=5e-3)
    assert result.Lr == pytest.approx(11.2 * 12, rel=5e-3)
    assert result.Mn == pytest.approx(2300.0, rel=5e-3)


def test_example_F3B_W21x48_noncompact_flange() -> None:
    result = flexure(section=W_beam("W21X48"), Fy=50.0)

    assert isinstance(result, NoncompactFlangeIShapeFlexureResult)
    assert result.section_class == SectionClass.NONCOMPACT
    assert result.limit_state == LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING
    assert result.Mn == pytest.approx(5310.0, rel=3e-3)
    assert result.phi_b_Mn == pytest.approx(398.0 * 12, rel=3e-3)


def test_example_F5_W12x58_minor_axis() -> None:
    result = flexure(section=W_beam("W12X58"), Fy=50.0, axis="minor")

    assert result.axis == BendingAxis.MINOR
    assert result.Mn == pytest.approx(1630.0, rel=5e-3)


def test_channel_minor_axis_uses_full_flange_width() -> None:
    result = flexure(section=C_channel("C15X33.9"), Fy=50.0, axis=BendingAxis.MINOR)
    assert getattr(result, "lambda_f") == pytest.approx(C_channel("C15X33.9").b_t, rel=2e-2)


def test_example_F7B_HSS10x6x3_16_noncompact_flange() -> None:
    result = flexure(section=HSS_RCT("HSS10X6X3/16"), Fy=50.0, Lb=252.0, Cb=1.14)

    assert result.limit_state == LimitState.FLANGE_LOCAL_BUCKLING
    assert getattr(result, "Lp") == pytest.approx(210.0, rel=3e-3)
    assert getattr(result, "Lr") == pytest.approx(5580.0, rel=3e-3)
    assert result.limit_states[LimitState.LATERAL_TORSIONAL_BUCKLING.value] == pytest.approx(900.0)
    assert result.Mn == pytest.approx(796.0, rel=3e-3)


def test_example_F8B_HSS8x8x3_16_slender_flange() -> None:
    result = flexure(section=HSS_SQR("HSS8X8X3/16"), Fy=50.0)

    assert result.section_class == SectionClass.SLENDER_ELEMENT
    assert getattr(result, "be") == pytest.approx(6.33, rel=3e-3)
    # the example removes the ineffective width from both flanges (Se = 12.1 in.3, conservative); the neutral-axis shift gives slightly more
    assert 605.0 <= result.Mn <= 625.0


def test_rectangular_hss_minor_axis_has_no_ltb() -> None:
    result = flexure(section=HSS_RCT("HSS10X6X3/16"), Fy=50.0, Lb=600.0, axis="minor")
    assert LimitState.LATERAL_TORSIONAL_BUCKLING.value not in result.limit_states


def test_example_F9B_pipe8_xs() -> None:
    result = flexure(section=PIPE("Pipe8XS"), Fy=35.0)
    assert result.limit_state == LimitState.PLASTIC_MOMENT_YIELDING
    assert result.phi_b_Mn == pytest.approx(81.4 * 12, rel=5e-3)


def test_round_hss_noncompact_and_slender_walls() -> None:
    from steelsnakes.US.checks.flexure import check_round_hss_flexure

    noncompact = check_round_hss_flexure(Fy=50.0, Z=10.0, S=8.0, D=10.0, t=0.2)
    slender = check_round_hss_flexure(Fy=50.0, Z=10.0, S=8.0, D=10.0, t=0.05)
    assert noncompact.limit_states[LimitState.LOCAL_BUCKLING.value] == pytest.approx((0.021 * 29000.0 / 50.0 + 50.0) * 8.0)
    assert slender.Fcr == pytest.approx(0.33 * 29000.0 / 200.0)
    with pytest.raises(ValueError):
        check_round_hss_flexure(Fy=50.0, Z=10.0, S=8.0, D=10.0, t=0.01)


def test_example_F10_WT5x6_continuously_braced() -> None:
    result = flexure(section=WT("WT5X6"), Fy=50.0)

    assert result.limit_states[LimitState.FLANGE_LOCAL_BUCKLING.value] >= result.Mn
    assert result.Mn == pytest.approx(97.6, rel=3e-3)


def test_tee_stem_in_compression_uses_stem_local_buckling_and_negative_B() -> None:
    result = flexure(section=WT("WT5X6"), Fy=50.0, Lb=72.0, stem_in_compression=True)

    assert getattr(result, "B") < 0.0
    assert LimitState.LOCAL_BUCKLING.value in result.limit_states
    assert result.Mn <= getattr(result, "My")


def test_tee_ltb_elastic_and_inelastic_ranges() -> None:
    tee = WT("WT5X6")
    props = dict(Fy=50.0, Zx=tee.Zx, Sx=tee.Sx, Ix=tee.Ix, y=tee.y, Iy=tee.Iy, J=tee.J, d=tee.d, tw=tee.tw, bf=tee.bf, tf=tee.tf, ry=tee.ry)
    short = check_tee_flexure(Lb=40.0, **props)
    long = check_tee_flexure(Lb=2000.0, **props)
    assert short.Lp is not None and short.Lr is not None
    assert long.limit_states[LimitState.LATERAL_TORSIONAL_BUCKLING.value] == pytest.approx(long.Mcr)


def test_double_angle_flexure_web_legs_in_tension_and_compression() -> None:
    tension_side = flexure(section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), Fy=50.0, Lb=96.0)
    compression_side = flexure(section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), Fy=50.0, Lb=96.0, stem_in_compression=True)

    assert getattr(tension_side, "shape") == "double_angle"
    assert compression_side.Mn <= 1.5 * getattr(compression_side, "My")
    assert compression_side.Mn < tension_side.Mn
    with pytest.raises(NotImplementedError):
        flexure(section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), axis="minor")


def test_double_angle_flexure_continuously_braced_standalone() -> None:
    result = check_double_angle_flexure(Fy=50.0, Zx=5.32, Sx=2.96, Ix=8.3, y=1.2, Iy=15.3, J=0.264, d=4.0, b=3.5, t=0.375, ry=1.69)
    assert result.Mn == pytest.approx(min(50.0 * 5.32, 1.6 * 50.0 * 2.96))


def test_example_F11A_equal_angle_geometric_axis() -> None:
    result = flexure(section=L_EQUAL("L4X4X1/4"), Fy=50.0, Lb=72.0, Cb=1.14, geometric_axis=True)

    assert getattr(result, "Mcr") == pytest.approx(107.0, rel=5e-3)
    assert result.limit_states[LimitState.PLASTIC_MOMENT_YIELDING.value] == pytest.approx(77.3, rel=3e-3)
    assert result.limit_states[LimitState.LEG_LOCAL_BUCKLING.value] == pytest.approx(53.0, rel=3e-3)
    assert result.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    assert result.Mn == pytest.approx(49.2, rel=3e-3)


def test_example_F11C_equal_angle_principal_axes() -> None:
    major = flexure(section=L_EQUAL("L4X4X1/4"), Fy=50.0, Lb=72.0, Cb=1.14)
    minor = flexure(section=L_EQUAL("L4X4X1/4"), Fy=50.0, Lb=72.0, axis="minor")

    assert getattr(major, "Mcr") == pytest.approx(195.0, rel=5e-3)
    assert major.Mn == pytest.approx(99.8, rel=3e-3)
    assert major.limit_states[LimitState.LEG_LOCAL_BUCKLING.value] == pytest.approx(113.0, rel=5e-3)
    assert minor.limit_states[LimitState.PLASTIC_MOMENT_YIELDING.value] == pytest.approx(58.4, rel=3e-3)
    assert minor.Mn == pytest.approx(55.1, rel=3e-3)


def test_unequal_angle_major_axis_uses_negative_beta_w_by_default() -> None:
    result = flexure(section=L_UNEQUAL("L5X3X1/2"), Fy=50.0, Lb=120.0)
    assert getattr(result, "beta_w") == pytest.approx(-2.99)
    assert angle_beta_w(3.0, 5.0) == pytest.approx(2.99)
    assert angle_beta_w(4.0, 4.0) == 0.0
    with pytest.raises(ValueError):
        angle_beta_w(9.0, 4.0)
    with pytest.raises(NotImplementedError):
        flexure(section=L_UNEQUAL("L5X3X1/2"), geometric_axis=True)


def test_single_angle_geometric_restrained_and_toe_in_tension() -> None:
    restrained = check_single_angle_flexure(50.0, 1.03, 4.0, 0.25, "geometric", Lb=72.0, Cb=1.14, restrained_at_max_moment=True)
    toe_tension = check_single_angle_flexure(50.0, 1.03, 4.0, 0.25, "geometric", Lb=72.0, Cb=1.14, toe_in_compression=False)
    assert restrained.My_ltb == pytest.approx(restrained.My)
    assert LimitState.LEG_LOCAL_BUCKLING.value not in toe_tension.limit_states
    assert toe_tension.Mcr is not None and toe_tension.Mcr > 107.0


def test_example_F12_rectangular_bar_and_F13_round_bar() -> None:
    bar = check_bar_flexure(Fy=50.0, d=5.0, t=3.0, Lb=72.0)
    rod = check_bar_flexure(Fy=50.0, d=1.0, shape="round")

    assert bar.Lb_d_t2 == pytest.approx(40.0)
    assert bar.Mn == pytest.approx(938.0, rel=2e-3)
    assert rod.Mn == pytest.approx(7.86, rel=3e-3)


def test_rectangular_bar_ltb_ranges() -> None:
    inelastic = check_bar_flexure(Fy=50.0, d=6.0, t=0.5, Lb=10.0)
    elastic = check_bar_flexure(Fy=50.0, d=6.0, t=0.5, Lb=100.0)
    assert inelastic.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    assert elastic.Fcr == pytest.approx(1.9 * 29000.0 / (100.0 * 6.0 / 0.25))


def test_noncompact_web_I_shape_F4_and_slender_web_F5() -> None:
    f4 = check_noncompact_web_i_shape_flexure(
        Fy=50.0, Zx=250.0, Sxc=220.0, Sxt=220.0, Iy=100.0, Iyc=50.0, J=3.0, ho=35.0, hc=33.0, tw=0.3, bfc=10.0, tfc=0.8, Lb=240.0
    )
    f5 = check_slender_web_i_shape_flexure(Fy=50.0, Sxc=1100.0, Sxt=1100.0, hc=66.0, tw=0.375, bfc=18.0, tfc=1.25, Lb=240.0)

    assert isinstance(f4, NoncompactWebIShapeFlexureResult)
    assert f4.lambda_pw < f4.lambda_w <= f4.lambda_rw
    assert 1.0 <= f4.Rpc <= f4.Mp / f4.Myc
    assert isinstance(f5, SlenderWebIShapeFlexureResult)
    assert f5.Rpg == pytest.approx(calculate_Rpg(f5.aw, 66.0 / 0.375, 50.0))
    assert f5.Rpg < 1.0


def test_singly_symmetric_F4_includes_tension_flange_yielding() -> None:
    result = check_noncompact_web_i_shape_flexure(
        Fy=50.0, Zx=250.0, Sxc=240.0, Sxt=150.0, Iy=100.0, Iyc=70.0, J=3.0, ho=35.0, hc=40.0, tw=0.35, bfc=12.0, tfc=0.9, Lb=0.0,
        lambda_pw=calculate_singly_symmetric_web_lambda_p(40.0, 30.0, 250.0 * 50.0, 150.0 * 50.0, 50.0),
    )
    assert result.FL == pytest.approx(max(50.0 * 150.0 / 240.0, 25.0))
    assert LimitState.TENSION_FLANGE_YIELDING.value in result.limit_states


def test_dispatcher_selects_F4_and_F5_for_i_shapes_from_properties() -> None:
    base = W_beam("W18X50").get_properties()
    f4 = flexure(section_type=SectionType.W, properties={**base, "h_tw": 100.0})
    f5 = flexure(section_type=SectionType.W, properties={**base, "h_tw": 150.0})
    assert isinstance(f4, NoncompactWebIShapeFlexureResult)
    assert isinstance(f5, SlenderWebIShapeFlexureResult)


def test_hss_effective_width_and_section_modulus() -> None:
    be = calculate_hss_effective_width(7.48, 0.174, 50.0)
    assert be == pytest.approx(6.33, rel=3e-3)
    assert calculate_hss_effective_width(7.48, 0.174, 50.0, box=True) > be
    assert calculate_effective_section_modulus(54.4, 5.37, 8.0, 0.174, 7.48, 7.48) == pytest.approx(54.4 / 4.0)


def test_tension_flange_rupture_F13_1() -> None:
    assert check_tension_flange_rupture(Fy=50.0, Fu=65.0, Afg=4.0, Afn=3.5, Sx=100.0) is None
    rupture = check_tension_flange_rupture(Fy=50.0, Fu=65.0, Afg=4.0, Afn=2.5, Sx=100.0)
    assert rupture is not None and rupture.Mn == pytest.approx(65.0 * 2.5 / 4.0 * 100.0)

    beam = W_beam("W18X50")
    result = flexure(section=beam, Fy=50.0, Afn=0.5 * beam.bf * beam.tf)
    assert result.limit_state == LimitState.TENSILE_RUPTURE


def test_unsymmetric_flexure_F12_and_proportions_F13_2() -> None:
    result = check_unsymmetric_flexure(Fy=50.0, Smin=10.0, Fcr_ltb=30.0)
    assert result.Fn == pytest.approx(30.0)
    assert check_i_shape_proportions(50.0, h_tw=200.0, Iyc=50.0, Iy=100.0).adequacy == "OK"
    assert check_i_shape_proportions(50.0, h_tw=300.0, slender_web=True, a_h=1.0).adequacy == "FAILS"


def test_flexure_utilisation_and_axis_validation() -> None:
    assert flexure_utilisation(266.0 * 12, 304.0 * 12).adequacy == "OK"
    with pytest.raises(ValueError):
        flexure(section=W_beam("W18X50"), axis="diagonal")
    assert math.isclose(calculate_Cb(-10.0, 10.0, 10.0, 10.0), 1.0)


def test_example_F6_HSS3_5x3_5x1_8_noncompact_flange() -> None:
    result = flexure(section=HSS_SQR("HSS3-1/2X3-1/2X1/8"), Fy=50.0)
    assert result.limit_state == LimitState.FLANGE_LOCAL_BUCKLING
    assert result.phi_b_Mn == pytest.approx(7.20 * 12, rel=3e-3)


def test_example_F11B_equal_angle_restrained_at_midspan() -> None:
    result = flexure(section=L_EQUAL("L4X4X1/4"), Fy=50.0, Lb=36.0, Cb=1.30, geometric_axis=True, restrained_at_max_moment=True)
    assert getattr(result, "Mcr") == pytest.approx(176.0, rel=3e-3) # 1.25 x F10-5a
    assert getattr(result, "My_ltb") == pytest.approx(51.5, rel=3e-3) # geometric section modulus, not 0.8Sx
    assert result.limit_states[LimitState.LATERAL_TORSIONAL_BUCKLING.value] == pytest.approx(66.3, rel=3e-3)
    # The example conservatively reuses leg local buckling from F.11A (0.80Sc, 53.0 kip-in.); with restraint Sc = Sx
    assert result.limit_states[LimitState.LEG_LOCAL_BUCKLING.value] >= 53.0
    assert result.phi_b_Mn >= 3.98 * 12


def test_built_up_F4_and_F5_flanges_use_table_B4_1b_case_11() -> None:
    # Case 11: lambda_rf = 0.95sqrt(kc*E/FL), below case 10's 1.0sqrt(E/Fy); h/tw = 176 gives kc = 0.35 (lower bound)
    rolled = check_slender_web_i_shape_flexure(Fy=50.0, Sxc=1100.0, Sxt=1100.0, hc=66.0, tw=0.375, bfc=18.0, tfc=0.75)
    built_up = check_slender_web_i_shape_flexure(Fy=50.0, Sxc=1100.0, Sxt=1100.0, hc=66.0, tw=0.375, bfc=18.0, tfc=0.75, built_up=True)

    assert rolled.lambda_rf == pytest.approx(math.sqrt(29000.0 / 50.0))
    assert built_up.lambda_rf == pytest.approx(0.95 * math.sqrt(0.35 * 29000.0 / (0.7 * 50.0))) # FL = 0.7Fy for slender webs
    assert built_up.limit_state == LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING
    assert built_up.Mn < rolled.Mn # F5-8 interpolates over the shorter range

    f4 = check_noncompact_web_i_shape_flexure(
        Fy=50.0, Zx=250.0, Sxc=220.0, Sxt=220.0, Iy=100.0, Iyc=50.0, J=3.0, ho=35.0, hc=33.0, tw=0.3, bfc=10.0, tfc=0.5, built_up=True
    )
    assert f4.lambda_rf == pytest.approx(0.95 * math.sqrt(max(4.0 / math.sqrt(110.0), 0.35) * 29000.0 / f4.FL))


def test_angle_beta_w_matches_soft_converted_legs() -> None:
    # Commentary Table C-F10.1: L8x4 is L203x102; 203/25.4 = 7.99 in. still finds beta_w = 5.48 in.
    assert angle_beta_w(203.0 / 25.4, 102.0 / 25.4) == pytest.approx(5.48)
