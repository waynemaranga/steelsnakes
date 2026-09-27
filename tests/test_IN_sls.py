"""IS 800:2025 (draft) 12.6 serviceability limit states: the Table 6 deflection limits, the Table 4 serviceability load
factors, and Annex C (floor vibration); ISMB 300 (Izz 8603.6 cm⁴) as the beam."""

import math

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.IN.checks.sls import (
    HORIZONTAL_DEFLECTION_LIMITS,
    VERTICAL_DEFLECTION_LIMITS,
    beam_deflection,
    check_beam_deflection,
    check_crane_rail_displacement,
    check_horizontal_deflection,
    check_vertical_deflection,
    check_vibration,
    combined_floor_frequency,
    effective_floor_width,
    floor_frequency,
    heel_impact_acceleration,
    recommended_camber,
    serviceability_load,
)
from steelsnakes.IN.sections import MediumWeightBeam

E = 2.0e5
ISMB_300 = MediumWeightBeam(designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26, I_zz=8603.6, I_yy=453.9)


def test_table_6_limits() -> None:
    assert (VERTICAL_DEFLECTION_LIMITS["purlin_elastic"], VERTICAL_DEFLECTION_LIMITS["purlin_brittle"]) == (150.0, 180.0)
    assert (VERTICAL_DEFLECTION_LIMITS["industrial_beam_elastic"], VERTICAL_DEFLECTION_LIMITS["industrial_cantilever_elastic"]) == (240.0, 120.0)
    assert [VERTICAL_DEFLECTION_LIMITS[key] for key in ("gantry_manual", "gantry_electric_up_to_50t", "gantry_electric_over_50t")] == [500.0, 750.0, 1_000.0]
    assert (VERTICAL_DEFLECTION_LIMITS["floor_not_susceptible"], VERTICAL_DEFLECTION_LIMITS["floor_susceptible"]) == (300.0, 360.0)
    assert (HORIZONTAL_DEFLECTION_LIMITS["column_elastic"], HORIZONTAL_DEFLECTION_LIMITS["column_brittle"]) == (150.0, 240.0)
    assert (HORIZONTAL_DEFLECTION_LIMITS["building_brittle"], HORIZONTAL_DEFLECTION_LIMITS["inter_storey_drift"]) == (500.0, 300.0)


def test_serviceability_loads_of_table_4() -> None:
    assert serviceability_load(imposed=10.0) == 10.0
    assert serviceability_load("DL+IL+CL+WL/EL", imposed=10.0, wind=5.0) == pytest.approx(0.8 * 15.0)
    assert serviceability_load("DL+WL/EL", wind=5.0, dead=2.0) == pytest.approx(7.0)


def test_beam_deflection_of_ismb_300() -> None:
    # 10 kN/m over 6 m: 5wL⁴/(384EI) = 9.81 mm against span/360 = 16.7 mm
    delta: float = 5.0 * 10.0 * 6000.0**4 / (384.0 * E * 8603.6e4)
    assert beam_deflection(10.0, 6000.0, 8603.6) == pytest.approx(delta)
    result = check_beam_deflection(ISMB_300, L=6000.0, imposed=10.0, member="floor_susceptible")
    assert (result.delta, result.limit, result.span_ratio) == pytest.approx((delta, 6000.0 / 360.0, 360.0))
    assert result.utilisation.adequacy == "OK" and result.limit_state == LimitState.VERTICAL_DEFLECTION
    cantilever = check_beam_deflection(ISMB_300, L=2000.0, imposed=10.0, support="cantilever", loading="concentrated")
    assert cantilever.case == "cantilever_not_susceptible" and cantilever.delta == pytest.approx(10e3 * 2000.0**3 / (3.0 * E * 8603.6e4))
    minor = check_beam_deflection(ISMB_300, L=3000.0, imposed=2.0, axis="y", span_ratio=250.0)
    assert minor.metadata["I"] == 453.9 and minor.limit == pytest.approx(12.0)
    with pytest.raises(ValueError, match="axis"):
        check_beam_deflection(ISMB_300, L=3000.0, axis="x") # type: ignore[arg-type]
    with pytest.raises(ValueError, match="No deflection coefficient"):
        beam_deflection(1.0, 1000.0, 100.0, "propped") # type: ignore[arg-type]


def test_deflection_checks() -> None:
    assert check_vertical_deflection(30.0, 6000.0, "gantry_electric_up_to_50t").utilisation.adequacy == "FAILS" # 8 mm
    assert check_vertical_deflection(20.0, 6000.0, span_ratio=300.0).utilisation.utilisation == pytest.approx(1.0)
    drift = check_horizontal_deflection(9.0, 3500.0, "inter_storey_drift")
    assert drift.limit == pytest.approx(3500.0 / 300.0) and drift.limit_state == LimitState.HORIZONTAL_DEFLECTION
    assert check_horizontal_deflection(20.0, 8000.0, "column_brittle").utilisation.utilisation == pytest.approx(20.0 / (8000.0 / 240.0))
    rails = check_crane_rail_displacement(20.0)
    assert (rails.limit, rails.span_ratio, rails.utilisation.utilisation) == (25.0, None, pytest.approx(0.8))
    assert check_crane_rail_displacement(30.0).utilisation.adequacy == "FAILS"
    with pytest.raises(ValueError, match="Unknown case"):
        check_vertical_deflection(10.0, 6000.0, "beam")
    with pytest.raises(ValueError, match="span_ratio"):
        check_vertical_deflection(10.0, 6000.0, None)


def test_camber() -> None:
    assert recommended_camber(40.0, 30.0) == pytest.approx(55.0) # 12.6.1.1: dead load plus half the imposed load


def test_floor_vibration_of_annex_c() -> None:
    # C-3: f1 = 156(E IT/(W L⁴))^0.5 with IT = 40 000 cm⁴, W = 8 N/mm, L = 9 m
    f1: float = 156.0 * math.sqrt(E * 4.0e8 / (8.0 * 9000.0**4))
    assert floor_frequency(40_000.0, 8.0, 9000.0) == pytest.approx(f1) # 6.09 Hz
    assert combined_floor_frequency(6.0, 8.0) == pytest.approx(4.8) # 1/fr² = 1/f1² + 1/f2²
    assert effective_floor_width(100.0) == 4000.0 and effective_floor_width(100.0, one_side=True) == 2000.0 # C-5
    assert heel_impact_acceleration(5.0, 100.0) == pytest.approx(0.03) # 600 fr/W, W in N
    normal = check_vibration(I_T_cm4=40_000.0, W_kN_m=8.0, L_mm=9000.0)
    assert (normal.f, normal.f_min, normal.utilisation.adequacy) == (pytest.approx(f1), 5.0, "OK")
    rhythmic = check_vibration(I_T_cm4=40_000.0, W_kN_m=8.0, L_mm=9000.0, activity="rhythmic")
    assert rhythmic.utilisation.utilisation == pytest.approx(8.0 / f1) and rhythmic.utilisation.adequacy == "FAILS"
    supported = check_vibration(I_T_cm4=40_000.0, W_kN_m=8.0, L_mm=9000.0, f2=8.0, W_total_kN=150.0)
    assert supported.f == pytest.approx(combined_floor_frequency(f1, 8.0)) and supported.f1 == pytest.approx(f1)
    assert supported.a0_g == pytest.approx(600.0 * supported.f / 150e3)
    assert any("0.5 % g" in note for note in supported.metadata["notes"])
    short = check_vibration(f=12.0, W_total_kN=150.0, L_mm=6000.0)
    assert any("C-5 applies" in note for note in short.metadata["notes"])
    with pytest.raises(ValueError, match="Pass f"):
        check_vibration(I_T_cm4=40_000.0)
    with pytest.raises(ValueError, match="activity"):
        check_vibration(f=6.0, activity="dance") # type: ignore[arg-type]
