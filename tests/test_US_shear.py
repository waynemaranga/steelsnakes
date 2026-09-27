from __future__ import annotations

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.base.sections import SectionType
from steelsnakes.US import shear
from steelsnakes.US.checks.flexure import BendingAxis
from steelsnakes.US.checks.shear import (
    calculate_beta_v,
    calculate_Cv1,
    calculate_Cv2,
    calculate_de,
    calculate_kv,
    check_end_panel_shear,
    check_rectangular_hss_shear,
    check_round_hss_shear,
    check_symmetric_member_shear,
    check_tension_field_shear,
    check_transverse_stiffener,
    check_web_shear,
    shear_utilisation,
    transverse_stiffeners_required,
)
from steelsnakes.US.sections.angles import L2L_LLBB, L_UNEQUAL
from steelsnakes.US.sections.beams import W_beam
from steelsnakes.US.sections.channels import C_channel
from steelsnakes.US.sections.hollow import HSS_RCT, HSS_RND
from steelsnakes.US.sections.tees import WT


def test_kv_and_Cv_coefficients() -> None:
    assert calculate_kv() == pytest.approx(5.34)
    assert calculate_kv(42.0, 33.0) == pytest.approx(8.09, rel=2e-3)
    assert calculate_kv(120.0, 33.0) == pytest.approx(5.34)
    assert calculate_Cv1(20.0, 5.34, 50.0) == pytest.approx(1.0)
    assert calculate_Cv2(106.0, 5.67, 50.0) == pytest.approx(0.442, rel=3e-3) # G2-11
    assert calculate_Cv2(70.0, 5.34, 50.0) == pytest.approx(1.10 * (5.34 * 29000.0 / 50.0) ** 0.5 / 70.0) # G2-10


# AISC Design Examples (v16.0)
def test_example_G1B_W24x62_rolled_web() -> None:
    result = shear(section=W_beam("W24X62"), Fy=50.0)

    assert result.phi_v == pytest.approx(1.0)
    assert result.limit_state == LimitState.SHEAR_YIELDING
    assert result.phi_v_Vn == pytest.approx(306.0, rel=3e-3)


def test_example_G2B_C15x33_9_channel_uses_phi_0_90() -> None:
    result = shear(section=C_channel("C15X33.9"), Fy=50.0)

    assert result.phi_v == pytest.approx(0.90)
    assert result.Vn == pytest.approx(180.0, rel=3e-3)
    assert result.phi_v_Vn == pytest.approx(162.0, rel=3e-3)


def test_example_G3_L5x3x1_4_long_leg() -> None:
    from steelsnakes.US.checks.shear import check_single_angle_or_tee_shear

    result = check_single_angle_or_tee_shear(Fy=50.0, b=5.0, t=0.25)
    assert result.Cv2 == pytest.approx(1.0)
    assert result.phi_v_Vn == pytest.approx(33.8, rel=3e-3)


def test_example_G4_HSS6x4x3_8() -> None:
    result = shear(section=HSS_RCT("HSS6X4X3/8"), Fy=50.0)

    assert result.h == pytest.approx(4.95, rel=3e-3)
    assert result.Aw == pytest.approx(3.46, rel=3e-3)
    assert result.phi_v_Vn == pytest.approx(93.6, rel=3e-3)


def test_example_G5_HSS16x0_375() -> None:
    result = shear(section=HSS_RND("HSS16.000X0.375"), Fy=50.0, Lv=192.0)

    assert result.metadata["Fcr_G5-2a"] == pytest.approx(112.0, rel=5e-3)
    assert result.metadata["Fcr_G5-2b"] == pytest.approx(73.0, rel=5e-3)
    assert result.Fcr == pytest.approx(30.0)
    assert result.phi_v_Vn == pytest.approx(232.0, rel=3e-3)


def test_example_G6_W21x48_minor_axis() -> None:
    result = shear(section=W_beam("W21X48"), Fy=50.0, axis="minor")

    assert result.axis == BendingAxis.MINOR
    assert result.h_tw == pytest.approx(9.47, rel=3e-3)
    assert result.phi_v_Vn == pytest.approx(189.0, rel=3e-3)


def test_example_G7_C9x20_minor_axis() -> None:
    result = shear(section=C_channel("C9X20"), Fy=50.0, axis=BendingAxis.MINOR)

    assert result.h_tw == pytest.approx(6.42, rel=3e-3)
    assert result.Vn == pytest.approx(65.7, rel=3e-3)


def test_example_G8B_built_up_girder_end_and_second_panel() -> None:
    end_panel = check_web_shear(Fy=50.0, d=36.0, tw=5 / 16, h_tw=106.0, rolled=False, a=42.0) # the example rounds h/tw to 106
    second_panel = check_tension_field_shear(Fy=50.0, d=36.0, tw=5 / 16, h=33.0, a=90.0, Afc=16.0 * 1.5, Aft=16.0 * 1.5, bfc=16.0, bft=16.0)

    assert end_panel.Cv1 == pytest.approx(0.710, rel=3e-3)
    assert end_panel.Vn == pytest.approx(241.0, rel=5e-3)
    assert second_panel.reference is not None and second_panel.reference.equation == "G2-7"
    assert second_panel.Vn == pytest.approx(206.0, rel=5e-3)


def test_example_G8A_unstiffened_girder_requires_stiffeners() -> None:
    unstiffened = check_web_shear(Fy=50.0, d=36.0, tw=5 / 16, h_tw=106.0, rolled=False) # the example rounds h/tw to 106

    assert unstiffened.Cv1 == pytest.approx(0.577, rel=3e-3)
    assert unstiffened.phi_v_Vn == pytest.approx(176.0, rel=5e-3)
    assert transverse_stiffeners_required(106.0, 50.0, Vu=210.0, d=36.0, tw=5 / 16, rolled=False) is True
    assert transverse_stiffeners_required(40.0, 50.0) is False


def test_tension_field_otherwise_G2_8_and_a_h_limit() -> None:
    result = check_tension_field_shear(Fy=50.0, d=36.0, tw=5 / 16, h=33.0, a=90.0, Afc=2.0, Aft=2.0, bfc=4.0, bft=4.0)
    assert result.reference is not None and result.reference.equation == "G2-8"
    with pytest.raises(ValueError):
        check_tension_field_shear(Fy=50.0, d=36.0, tw=5 / 16, h=33.0, a=120.0, Afc=24.0, Aft=24.0, bfc=16.0, bft=16.0)


def test_end_panel_tension_field_G2_3() -> None:
    Cv2 = calculate_Cv2(33.0 / 0.3125, calculate_kv(42.0, 33.0), 50.0)
    beta_v = calculate_beta_v(Mpf=200.0, Mpm=150.0, Mpst=150.0, h=33.0, Fyw=50.0, tw=0.3125, Cv2=Cv2)
    result = check_end_panel_shear(Fyw=50.0, d=36.0, tw=0.3125, h=33.0, a=42.0, beta_v=beta_v)

    assert 0.0 < beta_v <= 1.0
    assert result.tension_field is True
    assert result.Vn >= 0.6 * 50.0 * 36.0 * 0.3125 * Cv2
    assert calculate_de(0.3125, 0.9) == 0.0
    assert calculate_de(0.3125, 0.5) == pytest.approx(35.0 * 0.3125 * 0.09)


def test_transverse_stiffener_G2_4() -> None:
    result = check_transverse_stiffener(Fyw=50.0, Fyst=50.0, b_t_st=10.0, Ist=30.0, h=33.0, a=90.0, tw=0.3125, Vr=184.0, Vc1=185.0, Vc2=0.9 * 0.6 * 50.0 * 11.3 * 0.442)

    assert result.b_t_limit == pytest.approx(0.56 * (29000.0 / 50.0) ** 0.5)
    assert 0.0 <= result.rho_w <= 1.0
    assert result.Ist_required == pytest.approx(result.Ist2 + (result.Ist1 - result.Ist2) * result.rho_w)
    assert result.adequacy == "OK"
    assert check_transverse_stiffener(Fyw=50.0, Fyst=50.0, b_t_st=20.0, Ist=30.0, h=33.0, a=90.0, tw=0.3125).adequacy == "FAILS"


def test_tee_angle_and_double_angle_dispatch() -> None:
    tee = shear(section=WT("WT7X34"), Fy=50.0)
    tee_minor = shear(section=WT("WT7X34"), Fy=50.0, axis="minor")
    angle = shear(section=L_UNEQUAL("L5X3X1/2"), Fy=50.0)
    double = shear(section=L2L_LLBB("2L4X3-1/2X3/8X3/4LLBB"), Fy=50.0)

    assert tee.reference is not None and tee.reference.clause == "G3"
    assert tee_minor.metadata["n_elements"] == 1
    assert angle.Aw == pytest.approx(5.0 * 0.5)
    assert double.Aw == pytest.approx(2 * 4.0 * 0.375)


def test_rolled_I_shape_with_stiffeners_takes_larger_of_G2_1_and_G2_2() -> None:
    properties = {**W_beam("W24X62").get_properties(), "h_tw": 120.0}
    without = shear(section_type=SectionType.W, properties=properties, Fy=50.0, a=40.0)
    with_field = shear(section_type=SectionType.W, properties=properties, Fy=50.0, a=40.0, tension_field=True)
    assert with_field.phi_v_Vn >= without.phi_v_Vn


def test_other_symmetric_members_and_round_hss_without_Lv() -> None:
    assert check_symmetric_member_shear(Fy=50.0, d=20.0, tw=0.5, h=18.0, n_webs=2).Aw == pytest.approx(20.0)
    assert check_rectangular_hss_shear(Fy=50.0, h=4.95, t=0.349).Cv2 == pytest.approx(1.0)
    no_Lv = check_round_hss_shear(Fy=100.0, Ag=10.0, D=20.0, t=0.1)
    assert no_Lv.limit_state == LimitState.SHEAR_BUCKLING
    assert no_Lv.metadata["Fcr_G5-2a"] is None


def test_shear_utilisation() -> None:
    assert shear_utilisation(180.0, 232.0).adequacy == "OK"
    assert shear_utilisation(-300.0, 232.0).adequacy == "FAILS"
