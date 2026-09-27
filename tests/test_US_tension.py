from __future__ import annotations

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.base.sections import SectionType
from steelsnakes.US import tension
from steelsnakes.US.checks.tension import (
    ShearLagCase,
    calculate_effective_net_area,
    calculate_net_area,
    check_eyebar,
    check_pin_connected_member,
    check_tension_slenderness,
    shear_lag_factor,
    tension_utilisation,
)
from steelsnakes.US.sections.beams import W_beam


# AISC Design Example D.1 (v16.0): W8x21, bolted through both flanges, 13/16 in. holes
def test_net_area_example_D1() -> None:
    assert calculate_net_area(6.16, 0.400, hole_diameters=[13 / 16] * 4) == pytest.approx(4.76, rel=1e-3)


def test_net_area_adds_s2_4g_for_staggered_chain() -> None:
    An = calculate_net_area(10.0, 0.5, hole_diameters=[0.8125, 0.8125], staggers=[(3.0, 2.5)])
    assert An == pytest.approx(10.0 - 2 * 0.875 * 0.5 + 9.0 / 10.0 * 0.5)


def test_shear_lag_case7_takes_larger_case2_value_example_D1() -> None:
    U_case7 = shear_lag_factor(ShearLagCase.CASE_7, bf=5.27, d=8.28, n=3)
    U_larger = shear_lag_factor("case7", bf=5.27, d=8.28, n=3, x_bar=0.831, l=9.00)

    assert U_case7 == pytest.approx(0.85)
    assert U_larger == pytest.approx(0.908, rel=1e-3)


def test_shear_lag_open_section_lower_bound() -> None:
    U = shear_lag_factor("case2", x_bar=0.831, l=1.5, A_connected=2 * 5.27 * 0.400, Ag=6.16)
    assert U == pytest.approx(2 * 5.27 * 0.400 / 6.16)


@pytest.mark.parametrize(
    ("case", "kwargs", "expected"),
    [
        ("case1", {}, 1.0),
        ("case4", {"x_bar": 0.5, "l": 6.0, "w": 4.0}, 3 * 36 / (3 * 36 + 16) * (1 - 0.5 / 6.0)),
        ("case6", {"B": 6.0, "H": 6.0, "l": 8.0}, 3 * 64 / (3 * 64 + 36)),
        ("case8", {"n": 4}, 0.80),
        ("case8", {"n": 3}, 0.60),
        ("case7", {"connected": "web", "n": 4}, 0.70),
    ],
)
def test_shear_lag_factor_cases(case: str, kwargs: dict[str, float], expected: float) -> None:
    assert shear_lag_factor(case, **kwargs) == pytest.approx(expected)


def test_shear_lag_case5_round_and_rectangular_hss() -> None:
    round_U = shear_lag_factor("case5", R=3.0, theta=1.5, tp=0.5, l=8.0)
    rect_U = shear_lag_factor("case5", b=3.0, H=8.0, t=0.25, l=8.0)

    assert 0.0 < round_U <= 1.0
    x_bar = 3.0 - (2 * 9.0 + 0.25 * 8.0 - 2 * 0.0625) / (16.0 + 12.0 - 1.0)
    assert rect_U == pytest.approx(1.0 - x_bar / 8.0)


def test_shear_lag_rejects_too_few_fasteners_and_bad_case() -> None:
    with pytest.raises(ValueError):
        shear_lag_factor("case8", n=2)
    with pytest.raises(ValueError):
        shear_lag_factor("case9")


def test_effective_net_area() -> None:
    assert calculate_effective_net_area(4.76, 0.908) == pytest.approx(4.32, rel=1e-3)


def test_tension_example_D1_rupture_governs() -> None:
    result = tension(section=W_beam("W8X21"), Fy=50.0, Fu=65.0, An=4.76, U=0.908, L=25 * 12)

    assert result.limit_state == LimitState.TENSILE_RUPTURE
    assert result.Ae == pytest.approx(4.32, rel=1e-3)
    assert result.Pn == pytest.approx(281.0, rel=2e-3)
    assert result.phi_t_Pn == pytest.approx(211.0, rel=2e-3)
    assert result.metadata["phi_t_Pn_yielding"] == pytest.approx(277.0, rel=2e-3)
    assert result.L_r == pytest.approx(238.0, rel=2e-3)


def test_tension_without_holes_yielding_governs_and_accepts_properties() -> None:
    result = tension(section_type=SectionType.W, properties={"A": 10.0, "rx": 4.0, "ry": 2.0})

    assert result.limit_state == LimitState.TENSILE_YIELDING
    assert result.An == result.Ag == pytest.approx(10.0)
    assert result.phi_t_Pn == pytest.approx(0.9 * 50.0 * 10.0)
    assert result.r == pytest.approx(2.0)


def test_tension_rejects_net_area_above_gross_area() -> None:
    with pytest.raises(ValueError):
        tension(Ag=5.0, An=6.0)


def test_pin_connected_member_tensile_rupture_governs() -> None:
    result = check_pin_connected_member(Fy=50.0, Fu=65.0, t=1.0, d=4.0, dh=4.0 + 1 / 32, a=3.5, w=8.25)

    assert result.be == pytest.approx((8.25 - 4.03125) / 2)
    assert result.Cr == pytest.approx(1.0)
    assert result.Asf == pytest.approx(2.0 * 1.0 * (3.5 + 2.0))
    assert result.limit_state == LimitState.TENSILE_RUPTURE
    assert result.phi_Pn == pytest.approx(0.75 * 65.0 * 2.0 * 1.0 * result.be)
    assert result.dimensional_requirements_met is True


def test_pin_connected_member_Cr_and_clearance_limits() -> None:
    reduced = check_pin_connected_member(Fy=50.0, Fu=65.0, t=1.0, d=4.0, dh=4.0 + 3 / 64, a=3.5, w=8.25)
    assert reduced.Cr == pytest.approx(0.95)

    with pytest.raises(ValueError):
        check_pin_connected_member(Fy=50.0, Fu=65.0, t=1.0, d=4.0, dh=4.1, a=3.5, w=8.25)


def test_eyebar_limits_body_width_to_eight_thicknesses() -> None:
    result = check_eyebar(Fy=50.0, Fu=65.0, t=1.0, w=10.0, d=9.0, dh=9.0 + 1 / 32)

    assert result.Ag == pytest.approx(8.0)
    assert result.phi_t_Pn == pytest.approx(0.9 * 50.0 * 8.0)
    assert all(result.metadata["dimensional_requirements"].values())


def test_tension_utilisation_and_slenderness() -> None:
    assert tension_utilisation(180.0, 211.0).adequacy == "OK"
    assert tension_utilisation(250.0, 211.0).adequacy == "FAILS"
    assert check_tension_slenderness(300.0, 1.26).utilisation == pytest.approx(238.1 / 300.0, rel=1e-3)
    assert check_tension_slenderness(400.0, 1.0).adequacy == "FAILS"


# --- AISC Design Examples D.2 to D.9 (v16.0) ---
def _us_section(section_type: SectionType, designation: str):
    from steelsnakes.US.factory import get_US_factory

    return get_US_factory().create_section(designation, section_type)


def test_example_D2_single_angle_case8_vs_case2() -> None:
    angle = _us_section(SectionType.L_EQUAL, "L4X4X1/2")
    U = shear_lag_factor("case8", n=4, x_bar=angle.x, l=9.0, A_connected=0.5 * angle.A, Ag=angle.A)
    assert U == pytest.approx(0.869, abs=5e-4)
    An = calculate_net_area(angle.A, 0.5, hole_diameters=[13 / 16])
    assert An == pytest.approx(3.31, abs=5e-3)
    result = tension(section=angle, An=An, U=U, L=300 * 0.776)
    assert result.r == pytest.approx(0.776) # least r is rz
    assert result.limit_state == LimitState.TENSILE_RUPTURE
    assert result.phi_t_Pn == pytest.approx(140.0, abs=0.5)
    assert result.L_r == pytest.approx(300.0) # Lmax = 300rz = 19.4 ft


def test_example_D3_WT_welded_case4() -> None:
    tee = _us_section(SectionType.WT, "WT6X20")
    U = shear_lag_factor("case4", x_bar=tee.y, l=16.0, w=tee.bf, A_connected=tee.bf * tee.tf, Ag=tee.A)
    assert U == pytest.approx(0.860, abs=5e-4)
    result = tension(section=tee, U=U)
    assert result.Ae == pytest.approx(5.02, abs=5e-3)
    assert result.phi_t_Pn == pytest.approx(245.0, abs=0.5)
    assert result.metadata["phi_t_Pn_yielding"] == pytest.approx(263.0, abs=0.5)


def test_example_D4_rectangular_hss_single_gusset_case5() -> None:
    U = shear_lag_factor("case5", b=(4.0 - 0.5) / 2.0, H=6.0, t=0.349, l=16.0) # b = (B - tp)/2
    assert U == pytest.approx(0.919, abs=5e-4)
    An = 6.18 - 2 * (0.5 + 1 / 16) * 0.349 # slot with a 1/16 in. fit-up gap
    result = tension(Fy=50.0, Fu=62.0, Ag=6.18, An=An, U=U)
    assert result.Ae == pytest.approx(5.32, abs=5e-3)
    assert result.phi_t_Pn == pytest.approx(248.0, rel=3e-3)


def test_example_D5_round_hss_single_gusset_case5() -> None:
    import math

    theta = math.pi / 2 - math.asin((0.5 / 2) / (6.0 / 2))
    assert theta == pytest.approx(1.49, abs=5e-3)
    U = shear_lag_factor("case5", R=3.0, theta=theta, tp=0.5, l=16.0)
    assert U == pytest.approx(0.991, abs=5e-4)
    result = tension(Fy=50.0, Fu=62.0, Ag=8.09, An=8.09 - 2 * (0.5 + 1 / 16) * 0.465, U=U)
    assert result.Ae == pytest.approx(7.50, abs=5e-3)
    assert result.phi_t_Pn == pytest.approx(349.0, abs=0.5)


def test_example_D6_double_angle() -> None:
    double_angle = _us_section(SectionType.L2L_EQUAL, "2L4X4X1/2X3/8")
    U = shear_lag_factor("case8", n=8, x_bar=1.18, l=21.0)
    assert U == pytest.approx(0.944, abs=5e-4)
    An = calculate_net_area(double_angle.A, 0.5, hole_diameters=[13 / 16, 13 / 16])
    assert An == pytest.approx(6.63, abs=5e-3)
    result = tension(section=double_angle, An=An, U=U, L=25 * 12)
    assert result.phi_t_Pn == pytest.approx(305.0, abs=0.5)
    assert result.metadata["phi_t_Pn_yielding"] == pytest.approx(338.0, abs=0.5)


def test_example_D7_pin_connected_bearing_governs() -> None:
    result = check_pin_connected_member(Fy=50.0, Fu=65.0, t=0.5, d=1.0, dh=1.03, a=2.25, w=4.25)
    assert result.be == pytest.approx(1.61) # less than 2t + 0.63 = 1.63
    assert result.Cr == 1.0
    assert result.Asf == pytest.approx(2.75)
    assert 0.75 * result.Pn_tensile_rupture == pytest.approx(78.8, rel=5e-3) # Pn rounded to 105 kips in the example
    assert 0.75 * result.Pn_shear_rupture == pytest.approx(80.3, abs=0.2)
    assert result.limit_state == LimitState.BEARING
    assert result.phi_Pn == pytest.approx(33.8, abs=0.1)
    assert result.dimensional_requirements_met


def test_example_D8_eyebar_yielding_governs() -> None:
    result = check_eyebar(Fy=50.0, Fu=65.0, t=0.625, w=3.0, d=3.0, dh=3.03)
    assert result.limit_state == LimitState.TENSILE_YIELDING
    assert result.phi_t_Pn == pytest.approx(84.6, rel=3e-3) # Ag rounded to 1.88 in.² in the example
    assert all(result.metadata["dimensional_requirements"].values())


def test_example_D9_plate_with_staggered_bolts() -> None:
    straight = calculate_net_area(7.0, 0.5, hole_diameters=[13 / 16] * 2) # line A-B-E-F
    staggered = calculate_net_area(7.0, 0.5, hole_diameters=[13 / 16] * 4, staggers=[(2.5, 3.0), (2.5, 3.0)]) # A-B-C-D-E-F
    assert straight == pytest.approx(12.25 * 0.5)
    assert staggered == pytest.approx(11.54 * 0.5, abs=5e-3) # w = 11.5 in., An = 5.75 in.²
