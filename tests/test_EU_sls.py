from __future__ import annotations

import math

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.base.sections import SectionType
from steelsnakes.EU import IPE, check_beam_deflection as public_check_beam_deflection
from steelsnakes.EU.checks.sls import (
    DEFLECTION_COEFFICIENTS,
    F_MIN,
    GRAVITY,
    beam_deflection,
    check_beam_deflection,
    check_horizontal_deflection,
    check_serviceability_stresses,
    check_vertical_deflection,
    check_vibration,
    line_load_from_mass,
    mass_from_line_load,
    natural_frequency,
    natural_frequency_from_deflection,
    psi_factors,
    serviceability_stress_utilisations,
    sls_combination,
)
from steelsnakes.UK import HFRHS

FY = 355.0
E = 210_000.0
I_IPE_300 = 8360e4 # mm⁴, I_y from the tables (8360 cm⁴)


# --- EN 1990 Table A1.1 and 6.5.3 ---
def test_psi_factors_table_A1_1() -> None:
    assert psi_factors("B") == (0.7, 0.5, 0.3)
    assert psi_factors("E") == (1.0, 0.9, 0.8)
    assert psi_factors("snow") == (0.5, 0.2, 0.0)
    assert psi_factors("wind") == (0.6, 0.2, 0.0)
    with pytest.raises(ValueError):
        psi_factors("Z")


def test_sls_combinations_6_14b_to_6_16b() -> None:
    # G = 2.0; Q_B = 7.5 (offices), Q_snow = 1.2
    variable = [(7.5, "B"), (1.2, "snow")]
    # characteristic: B leading 2 + 7.5 + 0.5*1.2 = 10.1 > snow leading 2 + 1.2 + 0.7*7.5 = 8.45
    assert sls_combination([2.0], variable) == pytest.approx(10.1)
    assert sls_combination([2.0], variable, leading=1) == pytest.approx(8.45)
    # frequent: 2 + 0.5*7.5 + 0*1.2 = 5.75; quasi-permanent: 2 + 0.3*7.5 + 0*1.2 = 4.25
    assert sls_combination(2.0, variable, "frequent") == pytest.approx(5.75)
    assert sls_combination([1.5, 0.5], variable, "quasi-permanent") == pytest.approx(4.25)
    assert sls_combination(2.0, P=1.0) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        sls_combination(2.0, variable, leading=2)
    with pytest.raises(ValueError):
        sls_combination(2.0, variable, "rare") # type: ignore[arg-type]


# --- 7.2.1 Vertical deflections ---
def test_beam_deflection_formulae() -> None:
    # IPE 300, 6 m: 5wL⁴/(384EI) = 5*10*6000⁴/(384*210000*8360e4) = 9.612 mm; PL³/(48EI) = 5.126 mm for P = 20 kN
    assert beam_deflection(10.0, 6000.0, I_IPE_300) == pytest.approx(9.6120984, rel=1e-6)
    assert beam_deflection(20e3, 6000.0, I_IPE_300, loading="concentrated") == pytest.approx(5.1264525, rel=1e-6)
    assert beam_deflection(10.0, 6000.0, I_IPE_300, "both_ends_fixed") == pytest.approx(9.6120984 / 5.0, rel=1e-6)
    assert beam_deflection(2.0, 2000.0, I_IPE_300, "cantilever") == pytest.approx(2.0 * 2000.0**4 / (8.0 * E * I_IPE_300))
    assert beam_deflection(-10.0, 6000.0, I_IPE_300) < 0.0 # uplift
    with pytest.raises(ValueError):
        beam_deflection(10.0, 6000.0, I_IPE_300, "pinned") # type: ignore[arg-type]
    with pytest.raises(ValueError):
        beam_deflection(10.0, 0.0, I_IPE_300)


def test_propped_cantilever_coefficients_from_the_elastic_curve() -> None:
    # Pinned at x = 0, fixed at x = L; sample the elastic curves and compare the maxima with the tabulated coefficients
    L, EI = 1.0, 1.0
    xs = [L * i / 20000 for i in range(20001)]
    udl = max(x * (L**3 - 3.0 * L * x**2 + 2.0 * x**3) / 48.0 for x in xs) # w = 1
    point = max(x * (3.0 * L**2 - 5.0 * x**2) / 96.0 for x in xs if x <= L / 2.0) # P = 1 at mid-span
    assert DEFLECTION_COEFFICIENTS[("one_end_fixed", "uniform")] == pytest.approx(udl, rel=1e-4)
    assert DEFLECTION_COEFFICIENTS[("one_end_fixed", "concentrated")] == pytest.approx(point, rel=1e-6)


def test_vertical_deflection_figure_A1_1() -> None:
    # w_1 = 6, w_3 = 12, w_c = 5 mm over 6 m: w_tot = 18, w_max = 13; L/360 = 16.67 mm, L/250 = 24 mm
    result = check_vertical_deflection(6000.0, 12.0, w_1=6.0, w_c=5.0, member="brittle_finish", span_ratio_w_max=250.0)
    assert (result.w_tot, result.w_max) == (18.0, 13.0)
    assert result.w_3_limit == pytest.approx(6000.0 / 360.0)
    assert result.utilisations["w_3"] == pytest.approx(0.72)
    assert result.utilisations["w_max"] == pytest.approx(13.0 / 24.0)
    assert result.governing == "w_3" and result.utilisation.adequacy == "OK"
    assert result.limit_state == LimitState.VERTICAL_DEFLECTION
    assert result.reference is not None and result.reference.clause == "7.2.1"

    beam = check_vertical_deflection(6000.0, 32.0) # other beams: span/200 = 30 mm
    assert beam.utilisation.utilisation == pytest.approx(32.0 / 30.0) and beam.utilisation.adequacy == "FAILS"
    assert check_vertical_deflection(6000.0, 10.0, member=None, span_ratio_w_3=300.0).w_3_limit == pytest.approx(20.0)
    w_max_only = check_vertical_deflection(6000.0, 10.0, w_1=5.0, member=None, span_ratio_w_max=250.0) # 15/24
    assert list(w_max_only.utilisations) == ["w_max"] and w_max_only.utilisation.utilisation == pytest.approx(0.625)
    with pytest.raises(ValueError):
        check_vertical_deflection(6000.0, 10.0, member="purlin") # to suit the cladding
    with pytest.raises(ValueError):
        check_vertical_deflection(6000.0, 10.0, member="rafter")


def test_beam_deflection_check_ipe_300() -> None:
    # IPE 300, 6 m, G_k = 5 kN/m plus self weight 42.2*9.81 = 0.414 kN/m, Q_k = 10 kN/m
    result = check_beam_deflection(IPE("IPE-300"), L=6000.0, G_k=5.0, Q_k=10.0, member="brittle_finish", self_weight=True)
    assert result.w_3 == pytest.approx(9.6120984, rel=1e-6)
    assert result.w_1 == pytest.approx(4.8060492 + 0.3979236, rel=1e-6)
    assert result.utilisation.utilisation == pytest.approx(9.6120984 / (6000.0 / 360.0), rel=1e-6) # 0.577
    assert result.metadata["g_self"] == pytest.approx(42.2 * GRAVITY / 1e3)

    cantilever = public_check_beam_deflection(IPE("IPE-300"), L=2000.0, Q_k=2.0, support="cantilever")
    assert cantilever.member == "cantilever" and cantilever.w_3_limit == pytest.approx(2000.0 / 180.0)
    assert cantilever.w_3 == pytest.approx(0.2278423, rel=1e-6)

    minor = check_beam_deflection(IPE("IPE-300"), L=3000.0, Q_k=1.0, axis="z")
    assert minor.metadata["I"] == pytest.approx(604e4)
    plain = check_beam_deflection(L=6000.0, Q_k=10.0, section_type=SectionType.IPE, properties={"I_yy": 8360.0})
    assert plain.w_3 == pytest.approx(9.6120984, rel=1e-6)
    with pytest.raises(ValueError):
        check_beam_deflection(L=6000.0, Q_k=10.0, properties={"I_yy": 8360.0}, self_weight=True) # no mass per metre
    with pytest.raises(ValueError):
        check_beam_deflection(IPE("IPE-300"), L=6000.0, Q_k=10.0, axis="v") # type: ignore[arg-type]


# --- 7.2.2 Horizontal deflections ---
def test_horizontal_deflection_figure_A1_2() -> None:
    # Three storeys of 3.5 m: H_i/300 = 11.67 mm; overall 24.5 mm against H/500 = 21 mm
    result = check_horizontal_deflection([8.0, 9.5, 7.0], [3500.0, 3500.0, 3500.0], height_ratio_u=500.0)
    assert (result.u, result.H) == (24.5, 10500.0)
    assert result.utilisations["u_2"] == pytest.approx(9.5 / (3500.0 / 300.0))
    assert result.governing == "u" and result.utilisation.utilisation == pytest.approx(24.5 / 21.0)
    assert result.utilisation.adequacy == "FAILS"
    assert result.limit_state == LimitState.HORIZONTAL_DEFLECTION

    single = check_horizontal_deflection(10.0, 4000.0, "single_storey") # height/300 = 13.33 mm
    assert single.utilisation.utilisation == pytest.approx(0.75)
    assert check_horizontal_deflection(10.0, 4000.0, "portal_frame", height_ratio_u_i=150.0).utilisation.utilisation == pytest.approx(0.375)
    with pytest.raises(ValueError):
        check_horizontal_deflection(10.0, 4000.0, "portal_frame") # to suit the cladding
    with pytest.raises(ValueError):
        check_horizontal_deflection([8.0, 9.5], [3500.0])


# --- 7.2.3 Dynamic effects ---
def test_natural_frequency_matches_the_deflection_method() -> None:
    # f = (π/2)sqrt(EI/(mL⁴)) and f = (π/2)sqrt(5g/(384δ)) = 17.75/sqrt(δ) for the same simply supported beam
    m = 551.884 # kg/m
    f = natural_frequency(I_IPE_300, m, 6000.0)
    delta = beam_deflection(line_load_from_mass(m), 6000.0, I_IPE_300)
    coefficient = math.pi / 2.0 * math.sqrt(5.0 * GRAVITY * 1e3 / 384.0)
    assert coefficient == pytest.approx(17.75, abs=0.01)
    assert f == pytest.approx(natural_frequency_from_deflection(delta, coefficient), rel=1e-9)
    assert natural_frequency_from_deflection(9.0) == pytest.approx(6.0) # 18/sqrt(9)
    assert mass_from_line_load(line_load_from_mass(m)) == pytest.approx(m)
    with pytest.raises(ValueError):
        natural_frequency(I_IPE_300, m, 6000.0, "pinned") # type: ignore[arg-type]


def test_vibration_check_ipe_300() -> None:
    # IPE 300, 6 m, w = 5 kN/m: m = 5000/9.81 + 42.2 = 551.9 kg/m, f = (π/2)sqrt(1.7556e7/(551.9*6⁴)) = 7.78 Hz
    result = check_vibration(IPE("IPE-300"), L=6000.0, w=5.0)
    assert result.m == pytest.approx(551.884, rel=1e-5)
    assert result.f == pytest.approx(7.7822694, rel=1e-6)
    assert result.utilisation.utilisation == pytest.approx(F_MIN / 7.7822694, rel=1e-6)
    assert result.limit_state == LimitState.VIBRATION and not result.metadata

    cantilever = check_vibration(IPE("IPE-300"), L=3000.0, w=5.0, support="cantilever") # K = 3.516
    assert cantilever.f == pytest.approx(11.0895871, rel=1e-6)

    stiff_floor = check_vibration(IPE("IPE-300"), L=6000.0, w=5.0, f_min=10.0)
    assert stiff_floor.utilisation.adequacy == "FAILS" and "A1.4.4(5)" in stiff_floor.metadata["notes"][0]
    given = check_vibration(f=2.5)
    assert given.utilisation.utilisation == pytest.approx(1.2) and given.m is None and given.support is None
    with pytest.raises(ValueError):
        check_vibration(IPE("IPE-300"), w=5.0) # no span


# --- 7.1(4) Plastic redistribution at the serviceability limit state ---
def test_serviceability_stresses_ipe_300() -> None:
    # M_y = 100 kNm: σ = 100e6/557e3 = 179.5 N/mm²; V_z = 100 kN on A_w = (300 - 2*10.7)*7.1 = 1978 mm²: τ = 50.6 N/mm²
    result = check_serviceability_stresses(IPE("IPE-300"), FY, M_y_Ed_ser=100e6, V_z_Ed_ser=100e3)
    assert result.sigma_Ed_ser == pytest.approx(179.5332136, rel=1e-6)
    assert result.tau_Ed_ser == pytest.approx(50.5545838, rel=1e-6)
    assert result.utilisations["tau (7.2)"] == pytest.approx(0.2466566, rel=1e-6)
    assert result.governing == "sigma + tau (7.3)"
    assert result.utilisation.utilisation == pytest.approx(0.5626719, rel=1e-6)
    assert result.utilisation.reference is not None and result.utilisation.reference.equation == "7.3"
    assert result.utilisation.reference.notes == "EN 1993-2 7.3"
    assert result.limit_state == LimitState.SERVICEABILITY_STRESS

    # RHS under V_z: A_v = A*h/(b + h) = 5490*200/300 = 3660 mm² (6.2.6(3)f)
    rhs = check_serviceability_stresses(HFRHS("200x100x10.0"), FY, M_y_Ed_ser=20e6, V_z_Ed_ser=50e3)
    assert rhs.tau_Ed_ser == pytest.approx(50e3 / 3660.0)
    assert rhs.sigma_Ed_ser == pytest.approx(20e6 / 266e3)

    yielding = check_serviceability_stresses(IPE("IPE-300"), FY, sigma_Ed_ser=400.0, tau_Ed_ser=0.0)
    assert yielding.utilisation.adequacy == "FAILS"
    assert serviceability_stress_utilisations(0.0, FY / math.sqrt(3.0), FY)["tau (7.2)"] == pytest.approx(1.0)
