"""BS 5950-1:2000 2.5 serviceability limit states: Table 8 deflection limits and 2.5.1 serviceability loads."""

import math

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.BS import UB, UC
from steelsnakes.BS.checks.sls import (
    beam_deflection,
    check_beam_deflection,
    check_horizontal_deflection,
    check_vertical_deflection,
    check_vibration,
    natural_frequency_from_deflection,
    serviceability_load,
)


def test_serviceability_loads_2_5_1() -> None:
    assert serviceability_load(imposed=5.0) == 5.0 # unfactored
    assert serviceability_load(imposed=5.0, wind=3.0) == pytest.approx(0.8 * 8.0) # 80 % with imposed and wind together
    assert serviceability_load(wind=3.0, dead=4.0) == pytest.approx(7.0)


def test_beam_deflection_formulae() -> None:
    # UB 457x191x67, Ix = 29400 cm⁴, 6 m span, 20 kN/m: 5wL⁴/(384EI) = 5.60 mm
    assert beam_deflection(20.0, 6000.0, 29400.0) == pytest.approx(5.0 * 20.0 * 6000.0**4 / (384.0 * 205_000.0 * 29400e4))
    assert beam_deflection(50.0, 6000.0, 29400.0, loading="concentrated") == pytest.approx(50e3 * 6000.0**3 / (48.0 * 205_000.0 * 29400e4))
    assert beam_deflection(10.0, 2000.0, 29400.0, "cantilever") == pytest.approx(10.0 * 2000.0**4 / (8.0 * 205_000.0 * 29400e4))
    with pytest.raises(ValueError, match="coefficient"):
        beam_deflection(10.0, 2000.0, 29400.0, "propped") # type: ignore[arg-type]


def test_vertical_deflection_table_8() -> None:
    # Brittle finish: span/360 = 16.7 mm for a 6 m span
    beam = UB("457x191x67")
    result = check_beam_deflection(beam, L=6000.0, imposed=20.0, member="brittle_finish")
    delta = 5.0 * 20.0 * 6000.0**4 / (384.0 * 205_000.0 * 29400e4)
    assert (result.delta, result.limit, result.span_ratio) == (pytest.approx(delta), pytest.approx(6000.0 / 360.0), 360.0)
    assert result.utilisation.utilisation == pytest.approx(delta / (6000.0 / 360.0)) and result.limit_state == LimitState.VERTICAL_DEFLECTION
    assert result.metadata["I"] == 29400.0
    # Defaults: "beam" (span/200) or "cantilever" (length/180); minor axis and I overrides
    assert check_beam_deflection(beam, L=6000.0, imposed=20.0).span_ratio == 200.0
    assert check_beam_deflection(beam, L=2000.0, imposed=5.0, support="cantilever").span_ratio == 180.0
    assert check_beam_deflection(UC("254x254x73"), L=4000.0, imposed=5.0, axis="y").metadata["I"] == 3910.0
    assert check_beam_deflection(beam, L=6000.0, imposed=20.0, I=10000.0).delta == pytest.approx(delta * 2.94)
    with pytest.raises(ValueError, match="axis"):
        check_beam_deflection(beam, L=6000.0, imposed=20.0, axis="z") # type: ignore[arg-type]
    # Crane girders span/600; purlins to suit the cladding
    assert check_vertical_deflection(8.0, 6000.0, "crane_girder").utilisation.utilisation == pytest.approx(0.8)
    assert check_vertical_deflection(8.0, 6000.0, "purlin", span_ratio=150.0).limit == pytest.approx(40.0)
    with pytest.raises(ValueError, match="no numerical limit"):
        check_vertical_deflection(8.0, 6000.0, "purlin")
    with pytest.raises(ValueError, match="Unknown case"):
        check_vertical_deflection(8.0, 6000.0, "joist")


def test_horizontal_deflection_table_8() -> None:
    storey = check_horizontal_deflection(9.0, 3500.0)
    assert (storey.limit, storey.limit_state) == (pytest.approx(3500.0 / 300.0), LimitState.HORIZONTAL_DEFLECTION)
    assert check_horizontal_deflection(9.0, 6000.0, "crane_girder").limit == pytest.approx(12.0)
    assert check_horizontal_deflection(20.0, 6000.0, "portal_frame", span_ratio=100.0).utilisation.adequacy == "OK"
    with pytest.raises(ValueError, match="no numerical limit"):
        check_horizontal_deflection(9.0, 6000.0, "crane_column")


def test_vibration_2_5_3() -> None:
    assert natural_frequency_from_deflection(9.0) == pytest.approx(6.0) # 18/√δ
    result = check_vibration(delta=36.0) # 3 Hz
    assert (result.f, result.utilisation.utilisation, result.limit_state) == (pytest.approx(3.0), pytest.approx(1.0), LimitState.VIBRATION)
    assert check_vibration(f=2.0).utilisation.adequacy == "FAILS"
    with pytest.raises(ValueError, match="delta or f"):
        check_vibration()
    assert math.isclose(check_vibration(f=6.0, f_min=5.0).utilisation.utilisation, 5.0 / 6.0)
