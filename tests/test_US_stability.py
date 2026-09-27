"""AISC 360-22 Chapter C and Appendices 7 and 8; values from the AISC Design Examples (v16.0)."""

import math

import pytest

from steelsnakes.US.checks import (
    ALPHA_ASD,
    amplified_required_strengths,
    calculate_B1,
    calculate_B2,
    calculate_Cm,
    calculate_Pe1,
    calculate_Pe_story,
    calculate_RM,
    check_first_order_method,
    effective_length_method_permitted,
    first_order_additional_lateral_load,
    k_equals_one_permitted,
    moment_redistribution_Lm,
    notional_load,
    notional_loads,
    notional_loads_required_with_lateral_loads,
    p_delta_negligible,
    reduced_stiffness,
    stiffness_reduction_tau_b,
    tau_b_notional_load,
)


# --- C2.2b Notional loads ---
def test_example_C1A_notional_loads() -> None:
    assert notional_load(288.0) == pytest.approx(0.576) # LRFD, Yi = 120 ft x 2.40 kip/ft
    assert notional_load(192.0, alpha=ALPHA_ASD) == pytest.approx(0.614, abs=5e-4) # ASD, 0.002(1.6)(192 kips)


def test_notional_load_coefficient_scales_with_out_of_plumbness_and_levels() -> None:
    assert notional_load(1000.0, out_of_plumbness=1 / 1000) == pytest.approx(1.0) # C2.2b(c)
    assert notional_loads([100.0, 200.0]) == pytest.approx([0.2, 0.4])
    with pytest.raises(ValueError, match="alpha"):
        notional_load(100.0, alpha=1.5)
    with pytest.raises(ValueError, match="negative"):
        notional_load(-1.0)
    with pytest.raises(ValueError, match="out_of_plumbness"):
        notional_load(1.0, out_of_plumbness=0.0)


def test_notional_loads_with_lateral_loads_and_p_delta_conditions() -> None:
    assert not notional_loads_required_with_lateral_loads(1.60) # Example C.1A drift ratio, LRFD
    assert notional_loads_required_with_lateral_loads(1.75)
    assert p_delta_negligible(drift_ratio=1.5, moment_frame_gravity_fraction=0.25)
    assert not p_delta_negligible(drift_ratio=1.6, moment_frame_gravity_fraction=0.5) # Example C.1A: half the gravity load


# --- C2.3 Adjustments to stiffness ---
def test_example_C1A_tau_b_is_one() -> None:
    Pns = 50.0 * 19.1 # W12x65, nonslender: Pns = Fy*Ag = 955 kips
    assert 72.6 / Pns == pytest.approx(0.0760, abs=1e-4)
    assert stiffness_reduction_tau_b(72.6, Pns) == 1.0
    assert stiffness_reduction_tau_b(48.4, Pns, alpha=ALPHA_ASD) == 1.0


def test_tau_b_C2_2b_and_reduced_stiffness() -> None:
    assert stiffness_reduction_tau_b(Pr=75.0, Pns=100.0) == pytest.approx(4 * 0.75 * 0.25)
    with pytest.raises(ValueError, match="cannot carry"):
        stiffness_reduction_tau_b(Pr=120.0, Pns=100.0)
    stiffness = reduced_stiffness(EI=1000.0, EA=500.0, Pr=75.0, Pns=100.0)
    assert stiffness.EI_star == pytest.approx(0.8 * 0.75 * 1000.0)
    assert stiffness.EA_star == pytest.approx(400.0)
    assert reduced_stiffness(EI=1000.0).tau_b == 1.0
    assert tau_b_notional_load(288.0) == pytest.approx(0.288) # C2.3(c): 0.001*alpha*Yi


# --- Appendix 7 ---
def test_example_C1C_first_order_additional_lateral_load() -> None:
    assert first_order_additional_lateral_load(288.0, delta_over_L=0.0) == pytest.approx(1.21, abs=5e-3) # 0.0042Yi governs
    assert first_order_additional_lateral_load(192.0, delta_over_L=0.0, alpha=ALPHA_ASD) == pytest.approx(0.806, abs=5e-4)
    assert first_order_additional_lateral_load(100.0, delta_over_L=0.01) == pytest.approx(2.1)
    with pytest.raises(ValueError, match="negative"):
        first_order_additional_lateral_load(-1.0, 0.0)


def test_example_C1C_first_order_method_limitations() -> None:
    check = check_first_order_method(drift_ratio=1.48, column_Pr=72.8, column_Pns=955.0, beam_Pr=1.21, beam_I=612.0, L=360.0)
    Pe = math.pi**2 * 29000.0 * 612.0 / 360.0**2
    assert 0.08 * Pe == pytest.approx(108.0, rel=5e-3)
    assert check.adequacy == "OK"
    assert check.metadata["governing"] == "drift_ratio/1.5"
    assert check_first_order_method(drift_ratio=1.54, column_Pr=48.4, column_Pns=955.0, alpha=ALPHA_ASD).adequacy == "FAILS" # ASD invalid


def test_effective_length_method_and_k_equals_one() -> None:
    assert effective_length_method_permitted(1.5)
    assert not effective_length_method_permitted(1.6)
    assert k_equals_one_permitted(1.1)
    assert not k_equals_one_permitted(1.2)


# --- Appendix 8.1 ---
def test_example_C1B_and_C1C_RM() -> None:
    assert calculate_RM(Pmf=144.0, Pstory=288.0) == pytest.approx(0.925)
    assert calculate_RM(Pmf=0.0, Pstory=288.0) == 1.0 # braced frame
    with pytest.raises(ValueError, match="negative"):
        calculate_RM(Pmf=-1.0, Pstory=10.0)


def test_example_C1C_B2() -> None:
    RM = calculate_RM(Pmf=144.0, Pstory=288.0)
    Pe_story = calculate_Pe_story(H=1.21, L=240.0, delta_H=0.304, RM=RM)
    assert Pe_story == pytest.approx(884.0, rel=2e-3)
    assert calculate_B2(288.0, Pe_story) == pytest.approx(1.48, abs=5e-3)
    Pe_story_asd = calculate_Pe_story(H=0.800, L=240.0, delta_H=0.203, RM=RM)
    assert Pe_story_asd == pytest.approx(875.0, rel=2e-3)
    assert calculate_B2(192.0, Pe_story_asd, alpha=ALPHA_ASD) == pytest.approx(1.54, abs=5e-3)
    with pytest.raises(ValueError, match="unstable"):
        calculate_B2(1000.0, Pe_story)


def test_example_part_III_W14x90_B1_and_B2() -> None:
    Pe1 = calculate_Pe1(I=999.0, Lc1=13.5 * 12.0) # EI* = 0.8*τb*EI, direct analysis
    assert Pe1 == pytest.approx(8720.0, rel=2e-3)
    Cm = calculate_Cm(M1=134.0, M2=211.0, curvature="reverse")
    assert Cm == pytest.approx(0.346, abs=5e-4)
    assert calculate_B1(Cm, Pr=316.0, Pe1=Pe1) == 1.0 # 0.359 < 1, use 1
    RM = calculate_RM(Pmf=2240.0, Pstory=5410.0)
    assert RM == pytest.approx(0.938, abs=5e-4)
    Pe_story = calculate_Pe_story(H=178.0, L=13.5 * 12.0, delta_H=0.650, RM=RM)
    assert Pe_story == pytest.approx(41600.0, rel=2e-3)
    B2 = calculate_B2(5410.0, Pe_story)
    assert B2 == pytest.approx(1.15, abs=5e-3)
    amplified = amplified_required_strengths(Mnt=0.0, Mlt=211.0, B1=1.0, B2=B2)
    assert amplified.Mr == pytest.approx(B2 * 211.0)


def test_example_H4_effective_length_B1() -> None:
    Pe1x = calculate_Pe1(I=171.0, Lc1=14.0 * 12.0, direct_analysis=False)
    assert Pe1x == pytest.approx(1730.0, rel=6e-3)
    assert calculate_B1(1.0, 30.0, Pe1x) == pytest.approx(1.02, abs=5e-3)
    Pe1y = calculate_Pe1(I=36.6, Lc1=14.0 * 12.0, direct_analysis=False)
    assert Pe1y == pytest.approx(371.0, rel=2e-3)
    assert calculate_B1(1.0, 30.0, Pe1y) == pytest.approx(1.09, abs=5e-3)
    assert calculate_B1(1.0, 20.0, Pe1y, alpha=ALPHA_ASD) == pytest.approx(1.09, abs=5e-3)


def test_Cm_conventions_and_B1_edge_cases() -> None:
    assert calculate_Cm(M1=-50.0, M2=100.0) == pytest.approx(0.8) # signed: single curvature
    assert calculate_Cm(M1=50.0, M2=100.0, curvature="single") == pytest.approx(0.8)
    assert calculate_Cm(transverse_loading=True) == 1.0
    with pytest.raises(ValueError, match="smaller"):
        calculate_Cm(M1=200.0, M2=100.0)
    with pytest.raises(ValueError, match="zero"):
        calculate_Cm(M1=0.0, M2=0.0)
    assert calculate_B1(0.6, Pr=0.0, Pe1=100.0) == 1.0 # not in compression
    with pytest.raises(ValueError, match="unstable"):
        calculate_B1(1.0, Pr=100.0, Pe1=100.0)
    with pytest.raises(ValueError, match="not less than"):
        amplified_required_strengths(Mnt=1.0, B1=0.9)


def test_amplified_axial_strength_A_8_2() -> None:
    result = amplified_required_strengths(Mnt=100.0, Mlt=50.0, Pnt=200.0, Plt=40.0, B1=1.1, B2=1.2)
    assert result.Mr == pytest.approx(170.0)
    assert result.Pr == pytest.approx(248.0)


# --- Appendix 8.2 ---
def test_moment_redistribution_Lm() -> None:
    assert moment_redistribution_Lm(M1=-50.0, M2=100.0, ry=2.0, Fy=50.0) == pytest.approx((0.12 - 0.038) * 580.0 * 2.0)
    assert moment_redistribution_Lm(M1=-100.0, M2=100.0, ry=2.0, Fy=50.0, shape="box") == pytest.approx(0.10 * 580.0 * 2.0)
    with pytest.raises(ValueError, match="65 ksi"):
        moment_redistribution_Lm(M1=0.0, M2=1.0, ry=1.0, Fy=70.0)
    with pytest.raises(ValueError, match="larger"):
        moment_redistribution_Lm(M1=2.0, M2=1.0, ry=1.0, Fy=50.0)
