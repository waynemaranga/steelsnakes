from __future__ import annotations

import math
from typing import Optional

import pytest

from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.exceptions import SectionClass4Error
from steelsnakes.base.sections import SectionType
from steelsnakes.EU import HD, IPE, PFC, UB, L_EQUAL, check_cross_section as public_check_cross_section
from steelsnakes.EU.checks.uls import (
    E_STEEL,
    InteractionFactors,
    MomentDiagram,
    _as_section_class,
    axial_force_negligible,
    biaxial_bending_exponents,
    biaxial_bending_utilisation,
    box_reduced_moment_resistances,
    buckling_curve,
    buckling_negligible,
    buckling_reduction_factor,
    characteristic_resistances,
    check_bending,
    check_bending_and_axial_compression,
    check_buckling_resistance,
    check_compression,
    check_cross_section,
    check_general_method,
    check_lateral_torsional_buckling,
    check_restrained_beam,
    check_shear,
    check_tension,
    chs_reduced_moment_resistance,
    class_4_interaction_utilisation,
    correction_factor_kc,
    elastic_critical_moment,
    elastic_shear_stress,
    elastic_shear_utilisation,
    elastic_torsional_buckling_force,
    elastic_torsional_flexural_buckling_force,
    equivalent_compression_flange_radius,
    equivalent_moment_factor_A2,
    equivalent_moment_factor_B3,
    flexural_slenderness,
    hollow_section_torsional_resistance,
    i_section_reduced_moment_resistances,
    i_section_shear_reduced_moment_resistance,
    imperfection_factor,
    interaction_factors_method_1,
    interaction_factors_method_2,
    lambda_1,
    linear_interaction_utilisation,
    longitudinal_stress,
    longitudinal_stress_utilisation,
    ltb_curve,
    ltb_modification_factor,
    ltb_reduction_factor,
    member_interaction_utilisations,
    net_area,
    polar_radius_of_gyration,
    rectangular_reduced_moment_resistance,
    reduced_yield_strength,
    section_modulus_for_class,
    shear_area,
    shear_buckling_check_required,
    shear_reduction_factor,
    shear_resistance_with_torsion,
    stable_length,
    st_venant_shear_stress,
    steel_material,
    tension_flange_holes_negligible,
    torsion_utilisation,
    web_shear_stress,
    yield_criterion_utilisation,
)
from steelsnakes.UK import CFRHS, HFCHS, HFRHS, HFSHS

FY = 355.0
EPSILON = math.sqrt(235.0 / FY)


# --- 3.2 Table 3.1 ---
@pytest.mark.parametrize(
    ("grade", "t", "standard", "expected"),
    [
        ("S355", 16.0, None, ("EN 10025-2", 355.0, 490.0)),
        ("S355J2", 50.0, None, ("EN 10025-2", 335.0, 470.0)),
        ("S 275 JR", 12.0, None, ("EN 10025-2", 275.0, 430.0)),
        ("S355NL", 20.0, None, ("EN 10025-3", 355.0, 490.0)),
        ("S460ML", 60.0, None, ("EN 10025-4", 430.0, 530.0)),
        ("S355J2W", 10.0, None, ("EN 10025-5", 355.0, 490.0)),
        ("S460QL1", 45.0, None, ("EN 10025-6", 440.0, 550.0)),
        ("S355J2H", 10.0, None, ("EN 10210-1", 355.0, 510.0)),
        ("S355NH", 10.0, "EN 10219-1", ("EN 10219-1", 355.0, 470.0)),
    ],
)
def test_steel_material_table_3_1(grade: str, t: float, standard: Optional[str], expected: tuple[str, float, float]) -> None:
    material = steel_material(grade, t, standard)
    assert (material.standard, material.fy, material.fu) == expected
    assert material.epsilon == pytest.approx(math.sqrt(235.0 / material.fy))


def test_steel_material_rejects_uncovered_cases() -> None:
    with pytest.raises(ValueError):
        steel_material("S355", 90.0) # Table 3.1 stops at 80 mm
    with pytest.raises(ValueError):
        steel_material("S355H", 50.0, "EN 10219-1") # cold formed, t <= 40 mm only
    with pytest.raises(ValueError):
        steel_material("S690")
    with pytest.raises(ValueError):
        steel_material("grade 50")
    with pytest.raises(ValueError):
        steel_material("S355", 10.0, "EN 10025-9")


def test_section_class_inputs() -> None:
    assert _as_section_class(2) == SectionClass.CLASS_2
    assert _as_section_class("class 3") == SectionClass.CLASS_3
    assert _as_section_class("CLASS_4") == SectionClass.CLASS_4
    assert _as_section_class(SectionClass.CLASS_1) == SectionClass.CLASS_1
    with pytest.raises(ValueError):
        _as_section_class(5)
    with pytest.raises(ValueError):
        _as_section_class(SectionClass.COMPACT)


# --- 6.2.1 General ---
def test_yield_criterion_6_1() -> None:
    check = yield_criterion_utilisation(200.0, 0.0, 100.0, FY)
    assert check.utilisation == pytest.approx((200.0 / FY) ** 2 + 3.0 * (100.0 / FY) ** 2)
    assert check.adequacy == "OK"
    assert check.reference is not None and check.reference.equation == "6.1"


def test_linear_interaction_6_2() -> None:
    check = linear_interaction_utilisation(500e3, 2000e3, M_y_Ed=100e6, M_y_Rd=400e6)
    assert check.utilisation == pytest.approx(0.5)
    with pytest.raises(ValueError):
        linear_interaction_utilisation(500e3, 2000e3, M_z_Ed=10e6)


# --- 6.2.2.2 Net area ---
def test_net_area_takes_greater_of_straight_and_staggered_deduction() -> None:
    assert net_area(3000.0, 10.0, 22.0, n_holes=2) == pytest.approx(3000.0 - 440.0)
    # three-hole chain: t(n*d0 - Σ s²/4p) = 10(66 - 2*2500/240) = 451.7 > 440
    assert net_area(3000.0, 10.0, 22.0, n_holes=2, staggers=[(50.0, 60.0), (50.0, 60.0)]) == pytest.approx(3000.0 - 10.0 * (66.0 - 5000.0 / 240.0))
    with pytest.raises(ValueError):
        net_area(300.0, 10.0, 22.0, n_holes=2)
    with pytest.raises(ValueError):
        net_area(3000.0, 10.0, 22.0, n_holes=-1)


# --- 6.2.3 Tension ---
def test_tension_net_section_rupture_governs() -> None:
    # UB 457x191x67 S355: N_pl,Rd = 8550*355; N_u,Rd = 0.9*7000*490/1.25
    result = check_tension(UB("457x191x67"), fy=FY, fu=490.0, N_Ed=2000e3, A_net=7000.0)
    assert result.N_pl_Rd == pytest.approx(8550.0 * 355.0)
    assert result.N_u_Rd == pytest.approx(0.9 * 7000.0 * 490.0 / 1.25)
    assert result.N_t_Rd == pytest.approx(result.N_u_Rd)
    assert result.limit_state == LimitState.TENSILE_RUPTURE
    assert result.ductile is False
    assert result.utilisation is not None
    assert result.utilisation.utilisation == pytest.approx(2000e3 / result.N_u_Rd)


def test_tension_gross_yielding_and_category_c() -> None:
    gross = check_tension(A=5000.0, fy=275.0, fu=430.0)
    assert gross.N_t_Rd == pytest.approx(5000.0 * 275.0) # 0.9*430/1.25 = 309.6 > 275
    assert gross.limit_state == LimitState.TENSILE_YIELDING
    assert gross.utilisation is None

    category_c = check_tension(A=5000.0, fy=275.0, fu=430.0, A_net=4000.0, category_C=True)
    assert category_c.N_net_Rd == pytest.approx(4000.0 * 275.0)
    assert category_c.N_t_Rd == pytest.approx(4000.0 * 275.0)
    assert category_c.reference is not None and category_c.reference.equation == "6.8"
    with pytest.raises(ValueError):
        check_tension(A=5000.0, A_net=6000.0)


# --- 6.2.4 Compression ---
def test_compression_class_1_to_3_and_class_4() -> None:
    # IPE 300 web c/t = 248.6/7.1 = 35.0: Class 2 in S275 (38ε = 35.1), Class 4 in S355 (42ε = 34.2)
    result = check_compression(IPE("IPE-300"), fy=275.0, N_Ed=1000e3)
    assert result.section_class == SectionClass.CLASS_2
    assert result.N_c_Rd == pytest.approx(5380.0 * 275.0)
    assert result.utilisation is not None and result.utilisation.utilisation == pytest.approx(1000e3 / (5380.0 * 275.0))

    with pytest.raises(SectionClass4Error):
        check_compression(IPE("IPE-300"), fy=FY)
    class_4 = check_compression(IPE("IPE-300"), fy=FY, A_eff=4800.0)
    assert class_4.section_class == SectionClass.CLASS_4
    assert class_4.N_c_Rd == pytest.approx(4800.0 * FY)
    assert class_4.reference is not None and class_4.reference.equation == "6.11"


def test_compression_from_plain_properties() -> None:
    result = check_compression(section_type=SectionType.IPE, properties={"A": 53.8, "d": 248.6, "tw": 7.1, "b": 150.0, "tf": 10.7}, fy=275.0)
    assert result.N_c_Rd == pytest.approx(5380.0 * 275.0)
    with pytest.raises(ValueError):
        check_compression(A=5000.0, fy=FY) # nothing to classify


# --- 6.2.5 Bending ---
def test_bending_major_and_minor_axis() -> None:
    # UB 457x191x67 S355 is Class 1 in bending: M_c,y,Rd = 1470 cm³ * 355
    major = check_bending(UB("457x191x67"), fy=FY, M_Ed=400e6)
    assert major.section_class == SectionClass.CLASS_1
    assert major.M_c_Rd == pytest.approx(1470e3 * FY)
    assert major.utilisation is not None and major.utilisation.utilisation == pytest.approx(400e6 / (1470e3 * FY))

    minor = check_bending(UB("457x191x67"), fy=FY, axis="z")
    assert minor.M_c_Rd == pytest.approx(237e3 * FY)

    elastic = check_bending(UB("457x191x67"), fy=FY, section_class=3)
    assert elastic.M_c_Rd == pytest.approx(1300e3 * FY)
    assert elastic.reference is not None and elastic.reference.equation == "6.14"

    effective = check_bending(UB("457x191x67"), fy=FY, section_class=4, W_eff=1200e3)
    assert effective.M_c_Rd == pytest.approx(1200e3 * FY)
    with pytest.raises(ValueError):
        check_bending(UB("457x191x67"), axis="x") # type: ignore[arg-type]


def test_section_modulus_and_tension_flange_holes() -> None:
    assert section_modulus_for_class(2, W_pl=100.0, W_el=90.0) == (100.0, "6.13")
    with pytest.raises(SectionClass4Error):
        section_modulus_for_class(4, W_pl=100.0)
    # (6.16): 0.9*A_f,net*fu/γM2 >= A_f*fy/γM0
    assert tension_flange_holes_negligible(2400.0, 2200.0, 355.0, 490.0) is False
    assert tension_flange_holes_negligible(2400.0, 2200.0, 275.0, 430.0) is True


# --- 6.2.6 Shear ---
def test_shear_area_rolled_sections() -> None:
    # (a) UB 457x191x67: A - 2b*tf + (tw + 2r)tf = 8550 - 4823.46 + 28.5*12.7 > eta*hw*tw = 428*8.5
    assert shear_area(UB("457x191x67")) == pytest.approx(8550.0 - 2 * 189.9 * 12.7 + (8.5 + 20.0) * 12.7)
    # (e) by analogy, load parallel to the flanges: A - hw*tw
    assert shear_area(UB("457x191x67"), direction="y") == pytest.approx(8550.0 - (453.4 - 25.4) * 8.5)
    # (b) PFC 430x100x64: A - 2b*tf + (tw + r)tf
    assert shear_area(PFC("430x100x64")) == pytest.approx(8210.0 - 2 * 100.0 * 19.0 + (11.0 + 15.0) * 19.0)


def test_shear_area_hollow_sections() -> None:
    rhs = HFRHS("200x100x10.0") # (f) A*h/(b + h) and A*b/(b + h)
    assert shear_area(rhs) == pytest.approx(5490.0 * 200.0 / 300.0)
    assert shear_area(rhs, direction="y") == pytest.approx(5490.0 * 100.0 / 300.0)
    assert shear_area(HFSHS("200x200x10.0")) == pytest.approx(7490.0 / 2.0)
    assert shear_area(HFCHS("168.3x10.0")) == pytest.approx(2.0 * 4970.0 / math.pi) # (g)


@pytest.mark.parametrize(
    ("shape", "direction", "expected"),
    [
        ("rolled_T", "z", 5000.0 - 150.0 * 12.0 + (8.0 + 20.0) * 12.0 / 2.0),
        ("welded_T", "z", 8.0 * (200.0 - 6.0)),
        ("welded_I", "z", 176.0 * 8.0),
        ("welded_box", "z", 2.0 * 176.0 * 8.0),
        ("welded_box", "y", 5000.0 - 2.0 * 176.0 * 8.0),
        ("welded_channel", "y", 5000.0 - 176.0 * 8.0),
    ],
)
def test_shear_area_shape_overrides(shape: str, direction: str, expected: float) -> None:
    properties = {"A": 50.0, "h": 200.0, "b": 150.0, "tf": 12.0, "tw": 8.0, "r": 10.0}
    assert shear_area(properties=properties, shape=shape, direction=direction) == pytest.approx(expected) # type: ignore[arg-type]


def test_shear_area_not_covered() -> None:
    with pytest.raises(NotImplementedError):
        shear_area(L_EQUAL("100x100x16.0"))
    with pytest.raises(NotImplementedError):
        shear_area(properties={"A": 50.0, "h": 200.0, "b": 150.0, "tf": 12.0, "tw": 8.0}, shape="rolled_T", direction="y")


def test_check_shear_high_shear_and_web_slenderness() -> None:
    result = check_shear(UB("457x191x67"), fy=FY, V_Ed=500e3)
    V_pl_Rd = 4088.49 * FY / math.sqrt(3.0)
    assert result.V_pl_Rd == pytest.approx(V_pl_Rd)
    assert result.high_shear is True
    assert result.rho == pytest.approx((2.0 * 500e3 / V_pl_Rd - 1.0) ** 2)
    assert result.h_w_over_t_w == pytest.approx(428.0 / 8.5)
    assert result.shear_buckling_check_required is False # 50.4 < 72ε = 58.6
    assert result.utilisation is not None and result.utilisation.reference is not None
    assert result.utilisation.reference.equation == "6.17"


def test_check_shear_with_torsion_and_given_area() -> None:
    result = check_shear(HFRHS("200x100x10.0"), fy=FY, V_Ed=100e3, tau_t_Ed=50.0)
    f_v = FY / math.sqrt(3.0)
    assert result.V_pl_T_Rd == pytest.approx((1.0 - 50.0 / f_v) * result.V_pl_Rd) # (6.28)
    assert result.V_c_Rd == pytest.approx(result.V_pl_T_Rd)
    assert result.utilisation is not None and result.utilisation.reference is not None
    assert result.utilisation.reference.equation == "6.25"

    given = check_shear(fy=FY, A_v=1000.0)
    assert given.V_pl_Rd == pytest.approx(1000.0 * FY / math.sqrt(3.0))
    assert given.rho is None


def test_elastic_shear_and_web_shear_stress() -> None:
    tau = elastic_shear_stress(100e3, S=500e3, I=100e6, t=10.0)
    assert tau == pytest.approx(50.0)
    assert elastic_shear_utilisation(tau, FY).utilisation == pytest.approx(50.0 / (FY / math.sqrt(3.0)))
    assert web_shear_stress(300e3, A_f=2400.0, A_w=3600.0) == pytest.approx(300e3 / 3600.0)
    with pytest.raises(ValueError):
        web_shear_stress(300e3, A_f=1000.0, A_w=3600.0)
    assert shear_buckling_check_required(1200.0, 10.0, FY) is True
    assert shear_buckling_check_required(400.0, 10.0, FY) is False


# --- 6.2.7 Torsion ---
def test_torsion_helpers() -> None:
    assert st_venant_shear_stress(10e6, W_t=295e3) == pytest.approx(10e6 / 295e3)
    assert st_venant_shear_stress(1e6, I_t=37.1e4, t=12.7) == pytest.approx(1e6 * 12.7 / 37.1e4)
    with pytest.raises(ValueError):
        st_venant_shear_stress(1e6)
    T_Rd = hollow_section_torsional_resistance(295e3, FY)
    assert T_Rd == pytest.approx(295e3 * FY / math.sqrt(3.0))
    assert torsion_utilisation(10e6, T_Rd).utilisation == pytest.approx(10e6 / T_Rd)


def test_shear_resistance_with_torsion_6_26_to_6_28() -> None:
    f_v = FY / math.sqrt(3.0)
    assert shear_resistance_with_torsion(1000.0, FY, 50.0, shape="I") == pytest.approx(math.sqrt(1.0 - 50.0 / (1.25 * f_v)) * 1000.0)
    assert shear_resistance_with_torsion(1000.0, FY, 50.0, 20.0, shape="channel") == pytest.approx(
        (math.sqrt(1.0 - 50.0 / (1.25 * f_v)) - 20.0 / f_v) * 1000.0
    )
    assert shear_resistance_with_torsion(1000.0, FY, 50.0, shape="hollow") == pytest.approx((1.0 - 50.0 / f_v) * 1000.0)
    assert shear_resistance_with_torsion(1000.0, FY, 400.0, shape="hollow") == 0.0
    with pytest.raises(ValueError):
        shear_resistance_with_torsion(1000.0, FY, 50.0, shape="box") # type: ignore[arg-type]


# --- 6.2.8 Bending and shear ---
def test_shear_reduction_factor_6_29() -> None:
    assert shear_reduction_factor(400.0, 1000.0) == 0.0
    assert shear_reduction_factor(750.0, 1000.0) == pytest.approx(0.25)
    assert reduced_yield_strength(FY, 0.25) == pytest.approx(0.75 * FY)
    with pytest.raises(ValueError):
        reduced_yield_strength(FY, 1.5)


def test_i_section_shear_reduced_moment_6_30() -> None:
    A_w = 428.0 * 8.5
    M = i_section_shear_reduced_moment_resistance(1470e3, A_w, 8.5, FY, 0.5)
    assert M == pytest.approx((1470e3 - 0.5 * A_w**2 / (4.0 * 8.5)) * FY)
    assert i_section_shear_reduced_moment_resistance(1470e3, A_w, 8.5, FY, 0.0, M_y_c_Rd=500e6) == pytest.approx(500e6)


# --- 6.2.9 Bending and axial force ---
def test_i_section_reduced_moments_6_36_to_6_38() -> None:
    # UC 254x254x73: a = (A - 2b*tf)/A = (9310 - 2*254.6*14.2)/9310
    a = (9310.0 - 2 * 254.6 * 14.2) / 9310.0
    M_N_y, M_N_z = i_section_reduced_moment_resistances(100.0, 50.0, 0.4, 1.0, 9310.0, 254.6, 14.2)
    assert M_N_y == pytest.approx(100.0 * 0.6 / (1.0 - 0.5 * a))
    assert M_N_z == pytest.approx(50.0 * (1.0 - ((0.4 - a) / (1.0 - a)) ** 2))
    assert i_section_reduced_moment_resistances(100.0, 50.0, 0.1, 1.0, 9310.0, 254.6, 14.2) == pytest.approx((100.0, 50.0))


def test_box_chs_and_rectangular_reduced_moments() -> None:
    a_w = (5490.0 - 2 * 100.0 * 10.0) / 5490.0
    a_f = min((5490.0 - 2 * 200.0 * 10.0) / 5490.0, 0.5)
    M_N_y, M_N_z = box_reduced_moment_resistances(100.0, 60.0, 0.5, 1.0, 5490.0, 100.0, 200.0, 10.0)
    assert M_N_y == pytest.approx(min(100.0 * 0.5 / (1.0 - 0.5 * min(a_w, 0.5)), 100.0))
    assert M_N_z == pytest.approx(min(60.0 * 0.5 / (1.0 - 0.5 * a_f), 60.0))
    assert chs_reduced_moment_resistance(100.0, 0.5, 1.0) == pytest.approx(100.0 * (1.0 - 0.5**1.7))
    assert rectangular_reduced_moment_resistance(100.0, 0.5, 1.0) == pytest.approx(75.0)


def test_axial_force_negligible_6_33_to_6_35() -> None:
    web = 428.0 * 8.5 * FY
    assert axial_force_negligible(0.4 * web, 3000e3, 428.0, 8.5, FY, "y") is True
    assert axial_force_negligible(0.6 * web, 3000e3, 428.0, 8.5, FY, "y") is False
    assert axial_force_negligible(0.9 * web, 3000e3, 428.0, 8.5, FY, "z") is True


@pytest.mark.parametrize(
    ("shape", "n", "expected"),
    [
        ("I", 0.1, (2.0, 1.0)),
        ("I", 0.4, (2.0, 2.0)),
        ("CHS", 0.4, (2.0, 2.0)),
        ("RHS", 0.4, (1.66 / (1.0 - 1.13 * 0.16),) * 2),
        ("RHS", 0.95, (6.0, 6.0)),
        ("channel", 0.4, (1.0, 1.0)),
    ],
)
def test_biaxial_bending_exponents(shape: str, n: float, expected: tuple[float, float]) -> None:
    assert biaxial_bending_exponents(shape, n) == pytest.approx(expected)


def test_biaxial_and_elastic_and_class_4_interactions() -> None:
    assert biaxial_bending_utilisation(50.0, 30.0, 100.0, 60.0, 2.0, 1.0).utilisation == pytest.approx(0.25 + 0.5)
    sigma = longitudinal_stress(100e3, 5000.0, 50e6, 500e3, 10e6, 100e3)
    assert sigma == pytest.approx(20.0 + 100.0 + 100.0)
    assert longitudinal_stress_utilisation(sigma, FY).utilisation == pytest.approx(220.0 / FY)
    check = class_4_interaction_utilisation(100e3, 4000.0, FY, 50e6, 400e3, e_N_y=10.0, e_N_z=5.0, W_eff_z_min=100e3)
    assert check.utilisation == pytest.approx((100e3 / 4000.0 + 51e6 / 400e3 + 0.5e6 / 100e3) / FY)


# --- 6.2 combined ---
def test_cross_section_ipe_bending_axial_and_shear() -> None:
    # IPE 300 S355, N = 150 kN, My = 120 kNm, Vz = 90 kN: 6.33 and 6.34 hold, so M_y,Rd = W_pl,y*fy
    result = public_check_cross_section(IPE("IPE-300"), FY, N_Ed=150e3, M_y_Ed=120e6, V_z_Ed=90e3)
    assert result.section_class == SectionClass.CLASS_1
    assert result.method == "plastic"
    assert result.N_Rd == pytest.approx(5380.0 * FY)
    assert result.M_y_Rd == pytest.approx(628e3 * FY)
    assert result.governing == "M_y (6.31)"
    assert result.utilisation.utilisation == pytest.approx(120e6 / (628e3 * FY))
    assert result.rho_z == 0.0


def test_cross_section_high_shear_uses_6_30() -> None:
    # UB 457x191x67 S355, Vz = 700 kN > 0.5*V_pl,Rd = 419 kN; rho = 0.4498, M_y,V,Rd = 459.7 kNm
    result = check_cross_section(UB("457x191x67"), FY, M_y_Ed=300e6, V_z_Ed=700e3)
    assert result.rho_z == pytest.approx(0.44983280, rel=1e-6)
    assert result.M_y_Rd == pytest.approx(459.687862e6, rel=1e-6)
    assert result.utilisations["M_y (6.31)"] == pytest.approx(0.65261675, rel=1e-6)
    assert result.governing == "V_z (6.17)"
    assert result.metadata["notes"]


def test_cross_section_i_axial_with_biaxial_bending() -> None:
    column = HD("HD-320x158")
    result = check_cross_section(column, FY, N_Ed=2000e3, M_y_Ed=300e6, M_z_Ed=80e6)
    N_pl = 20100.0 * FY
    n = 2000e3 / N_pl
    M_N_y, M_N_z = i_section_reduced_moment_resistances(2720e3 * FY, 1190e3 * FY, 2000e3, N_pl, 20100.0, 303.0, 25.5)
    assert result.alpha == 2.0 and result.beta == pytest.approx(max(5.0 * n, 1.0))
    assert result.utilisations["M_y + M_z (6.41)"] == pytest.approx((300e6 / M_N_y) ** 2 + (80e6 / M_N_z) ** result.beta)


def test_cross_section_hollow_and_channel_methods() -> None:
    rhs = check_cross_section(HFRHS("200x100x10.0"), FY, N_Ed=500e3, M_y_Ed=60e6)
    assert rhs.method == "plastic" and "M_y (6.31)" in rhs.utilisations
    chs = check_cross_section(HFCHS("168.3x10.0"), FY, N_Ed=500e3, M_y_Ed=40e6, M_z_Ed=10e6)
    assert chs.alpha == 2.0 and chs.beta == 2.0
    assert chs.M_y_Rd == pytest.approx(chs_reduced_moment_resistance(251e3 * FY, 500e3, 4970.0 * FY))
    channel = check_cross_section(PFC("430x100x64"), FY, N_Ed=300e3, M_y_Ed=200e6)
    assert channel.method == "linear"
    assert channel.utilisations["N + M (6.2)"] == pytest.approx(300e3 / (8210.0 * FY) + 200e6 / (1220e3 * FY))


def test_cross_section_tension_shear_only_and_empty() -> None:
    tension = check_cross_section(IPE("IPE-300"), FY, N_Ed=-500e3, V_z_Ed=50e3)
    assert tension.section_class is None
    assert tension.utilisations["N (6.5)"] == pytest.approx(500e3 / (5380.0 * FY))
    bending = check_cross_section(IPE("IPE-300"), FY, N_Ed=-500e3, M_y_Ed=50e6, M_z_Ed=5e6)
    assert bending.section_class == SectionClass.CLASS_1
    empty = check_cross_section(IPE("IPE-300"), FY)
    assert empty.governing == "none" and empty.utilisation.utilisation == 0.0


def test_cross_section_class_3_and_class_4() -> None:
    elastic = check_cross_section(IPE("IPE-300"), FY, N_Ed=200e3, M_y_Ed=100e6, section_class=3)
    assert elastic.method == "elastic"
    assert elastic.utilisations["N + M (6.42)"] == pytest.approx((200e3 / 5380.0 + 100e6 / 557e3) / FY)

    with pytest.raises(SectionClass4Error):
        check_cross_section(IPE("IPE-300"), FY, N_Ed=200e3, section_class=4)
    effective = check_cross_section(IPE("IPE-300"), FY, N_Ed=200e3, M_y_Ed=100e6, section_class=4, A_eff=5000.0, W_eff_y=540e3)
    assert effective.method == "effective"
    assert effective.utilisations["N + M (6.44)"] == pytest.approx((200e3 / 5000.0 + 100e6 / 540e3) / FY)


# --- 6.3.1 Uniform members in compression ---
@pytest.mark.parametrize(
    ("lambda_bar", "curve", "expected"),
    [
        (0.5, "a0", 0.9513),
        (1.0, "a", 0.6656),
        (1.0, "b", 0.5970),
        (1.0, "c", 0.5399),
        (1.0, "d", 0.4671),
        (0.2, "d", 1.0),
    ],
)
def test_buckling_reduction_factor_figure_6_4(lambda_bar: float, curve: str, expected: float) -> None:
    assert buckling_reduction_factor(lambda_bar, curve) == pytest.approx(expected, abs=5e-5)


def test_imperfection_factor_and_slenderness() -> None:
    assert imperfection_factor("c") == 0.49
    with pytest.raises(ValueError):
        imperfection_factor("e")
    with pytest.raises(ValueError):
        buckling_reduction_factor(-0.1, "a")
    assert lambda_1(235.0) == pytest.approx(93.9, abs=0.02)
    assert flexural_slenderness(6000.0, 76.7, FY) == pytest.approx(6000.0 / 76.7 / lambda_1(FY))
    assert buckling_negligible(0.15) is True
    assert buckling_negligible(0.5, 100.0, 5000.0) is True
    assert buckling_negligible(0.5, 1000.0, 5000.0) is False


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"section_type": SectionType.IPE, "axis": "y", "h": 300.0, "b": 150.0, "t_f": 10.7}, "a"),
        ({"section_type": SectionType.IPE, "axis": "z", "h": 300.0, "b": 150.0, "t_f": 10.7}, "b"),
        ({"section_type": SectionType.IPE, "axis": "z", "h": 300.0, "b": 150.0, "t_f": 10.7, "steel_grade": "S460"}, "a0"),
        ({"section_type": SectionType.HL, "axis": "y", "h": 1000.0, "b": 400.0, "t_f": 60.0}, "b"),
        ({"section_type": SectionType.HL, "axis": "z", "h": 1000.0, "b": 400.0, "t_f": 60.0, "fy": 460.0}, "a"),
        ({"section_type": SectionType.HD, "axis": "y", "h": 330.0, "b": 303.0, "t_f": 25.5}, "b"),
        ({"section_type": SectionType.HD, "axis": "z", "h": 330.0, "b": 303.0, "t_f": 25.5}, "c"),
        ({"section_type": SectionType.HD, "axis": "z", "h": 500.0, "b": 454.0, "t_f": 125.0}, "d"),
        ({"section_type": SectionType.HD, "axis": "z", "h": 500.0, "b": 454.0, "t_f": 125.0, "steel_grade": "S460"}, "c"),
        ({"section_type": SectionType.UB, "axis": "y", "t_f": 30.0, "welded": True}, "b"),
        ({"section_type": SectionType.UB, "axis": "z", "t_f": 50.0, "welded": True}, "d"),
        ({"section_type": SectionType.HFRHS}, "a"),
        ({"section_type": SectionType.HFCHS, "steel_grade": "S460NH"}, "a0"),
        ({"section_type": SectionType.CFRHS}, "c"),
        ({"shape": "welded_box"}, "b"),
        ({"shape": "welded_box", "thick_welds": True}, "c"),
        ({"section_type": SectionType.UPE}, "c"),
        ({"section_type": SectionType.L_EQUAL, "axis": "v"}, "b"),
        ({"section_type": SectionType.IPE, "axis": "T", "h": 300.0, "b": 150.0, "t_f": 10.7}, "b"),
    ],
)
def test_buckling_curve_table_6_2(kwargs: dict[str, object], expected: str) -> None:
    assert buckling_curve(**kwargs) == expected # type: ignore[arg-type]


def test_buckling_curve_rejects_uncovered_cases() -> None:
    with pytest.raises(ValueError):
        buckling_curve(SectionType.IPE, "y")
    with pytest.raises(ValueError):
        buckling_curve(SectionType.HL, "y", h=1100.0, b=400.0, t_f=110.0)
    with pytest.raises(ValueError):
        buckling_curve(SectionType.UB, "y", welded=True)
    with pytest.raises(NotImplementedError):
        buckling_curve(SectionType.Sigma)


def test_buckling_resistance_hd_column() -> None:
    # HD 320x158 S355, L_cr = 6 m about both axes: curves b (y) and c (z), h/b <= 1.2 and t_f <= 100 mm
    result = check_buckling_resistance(HD("HD-320x158"), FY, L_cr_y=6000.0, L_cr_z=6000.0, N_Ed=2500e3)
    y, z = result.modes
    assert (y.curve, z.curve) == ("b", "c")
    assert y.N_cr == pytest.approx(math.pi**2 * E_STEEL * 39600e4 / 6000.0**2)
    assert y.chi == pytest.approx(0.85689947, rel=1e-6)
    assert z.lambda_bar == pytest.approx(1.02485620, rel=1e-6)
    assert result.chi == pytest.approx(0.52565112, rel=1e-6)
    assert result.N_b_Rd == pytest.approx(0.52565112 * 20100.0 * FY, rel=1e-6)
    assert result.governing_mode == "z"
    assert result.limit_state == LimitState.FLEXURAL_BUCKLING
    assert result.buckling_negligible is False
    assert result.utilisation is not None and result.utilisation.utilisation == pytest.approx(2500e3 / result.N_b_Rd)


def test_buckling_resistance_torsional_modes() -> None:
    column = HD("HD-320x158")
    i_0 = polar_radius_of_gyration(140.0, 76.7)
    torsional = check_buckling_resistance(column, FY, L_cr_T=6000.0)
    assert torsional.modes[0].axis == "T"
    assert torsional.modes[0].N_cr == pytest.approx(elastic_torsional_buckling_force(425e4, 2.74e12, 6000.0, i_0))
    assert torsional.limit_state == LimitState.TORSIONAL_BUCKLING

    channel = check_buckling_resistance(PFC("300x100x46"), FY, L_cr_y=3000.0, L_cr_T=3000.0, y_0=60.0, curves={"TF": "c"})
    tf = channel.modes[-1]
    assert tf.axis == "TF"
    assert tf.N_cr <= min(channel.modes[0].N_cr, elastic_torsional_buckling_force(36.8e4, 0.0813e12, 3000.0, tf.i or 1.0))
    assert channel.governing_mode in ("y", "TF")


def test_torsional_flexural_force_reduces_to_lesser_without_offset() -> None:
    assert elastic_torsional_flexural_buckling_force(1000.0, 800.0, 0.0, 50.0) == pytest.approx(800.0)
    assert elastic_torsional_flexural_buckling_force(1000.0, 800.0, 20.0, 50.0) < 800.0


def test_buckling_resistance_class_4_and_errors() -> None:
    result = check_buckling_resistance(IPE("IPE-300"), FY, L_cr_z=3000.0, section_class=4, A_eff=5000.0)
    assert result.A == 5000.0
    assert result.reference is not None and result.reference.equation == "6.48"
    with pytest.raises(ValueError):
        check_buckling_resistance(IPE("IPE-300"), FY)
    angle = check_buckling_resistance(L_EQUAL("100x100x16.0"), 275.0, L_cr_v=2000.0)
    assert angle.modes[0].curve == "b"


# --- 6.3.2 Uniform members in bending ---
def test_correction_factor_kc_table_6_6() -> None:
    assert correction_factor_kc(MomentDiagram.UNIFORM) == 1.0
    assert correction_factor_kc("linear", 0.0) == pytest.approx(1.0 / 1.33)
    assert correction_factor_kc("linear", -1.0) == pytest.approx(1.0 / 1.66)
    assert correction_factor_kc("udl-simply-supported") == 0.94
    assert correction_factor_kc(MomentDiagram.POINT_LOAD_SIMPLY_SUPPORTED) == 0.86
    assert correction_factor_kc(MomentDiagram.POINT_LOAD_BOTH_ENDS_FIXED) == 0.77
    with pytest.raises(ValueError):
        correction_factor_kc("linear", 1.5)


def test_ltb_curves_tables_6_4_and_6_5() -> None:
    assert ltb_curve(SectionType.IPE, 300.0, 150.0, "rolled") == "b"
    assert ltb_curve(SectionType.UB, 453.4, 189.9, "rolled") == "c"
    assert ltb_curve(SectionType.IPE, 300.0, 150.0, "general") == "a"
    assert ltb_curve(SectionType.UB, 453.4, 189.9, "general") == "b"
    assert ltb_curve(SectionType.UB, 300.0, 200.0, "rolled", welded=True) == "c"
    assert ltb_curve(SectionType.UB, 600.0, 200.0, "general", welded=True) == "d"
    assert ltb_curve(SectionType.HFRHS, method="general") == "d"
    with pytest.raises(ValueError):
        ltb_curve(SectionType.HFRHS, method="rolled")


def test_ltb_reduction_factor_6_56_to_6_58() -> None:
    # rolled, curve b, lambda_LT = 1.0: Phi = 0.5(1 + 0.34*0.6 + 0.75) = 0.977
    assert ltb_reduction_factor(1.0, "b") == pytest.approx(1.0 / (0.977 + math.sqrt(0.977**2 - 0.75)))
    assert ltb_reduction_factor(1.0, "a", "general") == pytest.approx(buckling_reduction_factor(1.0, 0.21))
    assert ltb_reduction_factor(0.3, "b") == 1.0 # plateau, lambda_LT <= 0.4
    assert ltb_reduction_factor(2.5, "b") <= 1.0 / 2.5**2
    f = ltb_modification_factor(0.94, 1.0)
    assert f == pytest.approx(1.0 - 0.5 * 0.06 * (1.0 - 2.0 * 0.04))
    assert ltb_reduction_factor(1.0, "b", f=f) == pytest.approx(ltb_reduction_factor(1.0, "b") / f)
    assert ltb_modification_factor(0.94, 3.0) == 1.0


def test_elastic_critical_moment_ipe_300() -> None:
    # IPE 300, L = 4 m, fork supports, C_1 = 1: M_cr = 159.3 kNm
    M_cr = elastic_critical_moment(604e4, 19.9e4, 4000.0, 0.126e12)
    assert M_cr == pytest.approx(159.3177506e6, rel=1e-6)
    destabilising = elastic_critical_moment(604e4, 19.9e4, 4000.0, 0.126e12, C_1=1.13, C_2=0.454, z_g=150.0)
    assert destabilising < 1.13 * M_cr


def test_lateral_torsional_buckling_ipe_300_udl() -> None:
    # IPE 300 S355, L = 4 m, UDL: C_1 = 0.94⁻², lambda_LT = 1.112, curve b, f = 0.9758, chi_LT,mod = 0.6470
    result = check_lateral_torsional_buckling(IPE("IPE-300"), FY, L=4000.0, M_Ed=120e6, diagram=MomentDiagram.UDL_SIMPLY_SUPPORTED)
    assert result.C_1 == pytest.approx(0.94**-2)
    assert result.M_cr == pytest.approx(159.3177506e6 / 0.94**2, rel=1e-6)
    assert result.lambda_bar_LT == pytest.approx(1.11196155, rel=1e-6)
    assert result.curve == "b"
    assert result.f == pytest.approx(0.97583920, rel=1e-6)
    assert result.chi_LT_unmodified == pytest.approx(0.63133436, rel=1e-6)
    assert result.chi_LT == pytest.approx(0.64696556, rel=1e-6)
    assert result.M_b_Rd == pytest.approx(144.2345022e6, rel=1e-6)
    assert result.ltb_negligible is False
    assert result.utilisation is not None and result.utilisation.utilisation == pytest.approx(120e6 / result.M_b_Rd)


def test_lateral_torsional_buckling_short_beam_and_general_method() -> None:
    short = check_lateral_torsional_buckling(IPE("IPE-300"), FY, L=500.0, M_Ed=100e6, apply_f=False)
    assert short.chi_LT == 1.0 and short.ltb_negligible is True
    general = check_lateral_torsional_buckling(IPE("IPE-300"), FY, L=4000.0, method="general")
    assert general.curve == "a" and general.f == 1.0
    given = check_lateral_torsional_buckling(IPE("IPE-300"), FY, M_cr=200e6, k_c=0.9)
    assert given.M_cr == 200e6 and given.k_c == 0.9


def test_lateral_torsional_buckling_hollow_channel_and_angle() -> None:
    chs = check_lateral_torsional_buckling(HFCHS("168.3x10.0"), FY, L=6000.0, M_Ed=50e6)
    assert chs.susceptible is False and chs.chi_LT == 1.0
    assert chs.M_b_Rd == pytest.approx(251e3 * FY)
    assert check_lateral_torsional_buckling(HFSHS("200x200x10.0"), FY, L=6000.0).susceptible is False

    rhs = check_lateral_torsional_buckling(CFRHS("200x100x10.0"), FY, L=6000.0)
    assert rhs.method == "general" and rhs.curve == "d"
    assert rhs.metadata["notes"]

    channel = check_lateral_torsional_buckling(PFC("300x100x46"), FY, L=3000.0)
    assert any("channel" in note for note in channel.metadata["notes"])

    with pytest.raises(ValueError):
        check_lateral_torsional_buckling(L_EQUAL("100x100x16.0"), 275.0, L=2000.0, section_class=3)
    with pytest.raises(ValueError):
        check_lateral_torsional_buckling(IPE("IPE-300"), FY)


# --- 6.3.2.4 and 6.3.5.3 ---
def test_restrained_beam_equivalent_compression_flange() -> None:
    # UB 457x191x67 S355, M_Ed = 400 kNm: i_f,z = 49.02 mm; limit = 0.5*521.85/400 = 0.652
    beam = UB("457x191x67")
    assert equivalent_compression_flange_radius(189.9, 12.7, 428.0, 8.5) == pytest.approx(49.0166763, rel=1e-6)
    stable = check_restrained_beam(beam, FY, L_c=2000.0, M_Ed=400e6)
    assert stable.lambda_bar_f == pytest.approx(0.53399943, rel=1e-6)
    assert stable.not_susceptible is True
    assert stable.M_b_Rd == pytest.approx(1470e3 * FY)

    long = check_restrained_beam(beam, FY, L_c=4000.0, M_Ed=400e6)
    assert long.not_susceptible is False
    assert long.curve == "c"
    assert long.chi == pytest.approx(0.50153480, rel=1e-6)
    assert long.M_b_Rd == pytest.approx(287.8985272e6, rel=1e-6)
    assert long.utilisation is not None and long.utilisation.adequacy == "FAILS"

    with pytest.raises(NotImplementedError):
        check_restrained_beam(PFC("300x100x46"), FY, L_c=2000.0, M_Ed=100e6)


def test_stable_length_6_68() -> None:
    assert stable_length(41.2, FY, 1.0) == pytest.approx(35.0 * EPSILON * 41.2)
    assert stable_length(41.2, FY, 0.0) == pytest.approx(60.0 * EPSILON * 41.2)
    assert stable_length(41.2, FY, 0.625) == pytest.approx(stable_length(41.2, FY, 0.6249999), rel=1e-6)
    with pytest.raises(ValueError):
        stable_length(41.2, FY, -1.5)


# --- 6.3.3 Uniform members in bending and axial compression ---
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"psi": 1.0}, 1.0),
        ({"psi": 0.0}, 0.6),
        ({"psi": -1.0}, 0.4),
        ({"alpha_s": 0.5}, 0.6),
        ({"alpha_s": -0.5, "psi": 0.5}, 0.5),
        ({"alpha_s": -0.5, "psi": 0.5, "loading": "concentrated"}, 0.4),
        ({"alpha_s": -0.5, "psi": -0.5}, 0.55),
        ({"alpha_s": -0.75, "psi": -0.5, "loading": "concentrated"}, 0.7),
        ({"alpha_h": 0.0}, 0.95),
        ({"alpha_h": 0.0, "loading": "concentrated"}, 0.90),
        ({"alpha_h": -0.5, "psi": -0.25}, 0.95 - 0.05 * 0.5 * 0.5),
        ({"alpha_h": -0.5, "psi": 0.5, "loading": "concentrated"}, 0.85),
        ({"sway": True}, 0.9),
    ],
)
def test_equivalent_moment_factor_table_B3(kwargs: dict[str, object], expected: float) -> None:
    assert equivalent_moment_factor_B3(**kwargs) == pytest.approx(expected) # type: ignore[arg-type]


def test_equivalent_moment_factor_B3_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        equivalent_moment_factor_B3(1.5)
    with pytest.raises(ValueError):
        equivalent_moment_factor_B3(alpha_s=0.5, alpha_h=0.5)
    with pytest.raises(ValueError):
        equivalent_moment_factor_B3(alpha_s=1.5)
    with pytest.raises(ValueError):
        equivalent_moment_factor_B3(alpha_h=-1.5)


def test_equivalent_moment_factor_table_A2() -> None:
    assert equivalent_moment_factor_A2(200.0, 1000.0, 1.0) == pytest.approx(0.79 + 0.21 + 0.36 * 0.67 * 0.2)
    assert equivalent_moment_factor_A2(200.0, 1000.0, loading="uniform") == pytest.approx(1.0 - 0.18 * 0.2)
    assert equivalent_moment_factor_A2(200.0, 1000.0, loading="concentrated") == pytest.approx(1.0 + 0.03 * 0.2)
    # simply supported UDL: π²EI*δ/(L²M) = π²*5/48 ≈ 1.028
    general = equivalent_moment_factor_A2(200.0, 1000.0, delta_x=5.0 * 4000.0**4 / (384.0 * E_STEEL * 1e8), M_i_Ed=4000.0**2 / 8.0, I_i=1e8, L=4000.0)
    assert general == pytest.approx(1.0 + (math.pi**2 * 5.0 / 48.0 - 1.0) * 0.2)
    with pytest.raises(ValueError):
        equivalent_moment_factor_A2(200.0, 1000.0, psi=2.0)
    with pytest.raises(ValueError):
        equivalent_moment_factor_A2(200.0, 1000.0, loading="parabolic") # type: ignore[arg-type]


def test_characteristic_resistances_table_6_7() -> None:
    assert characteristic_resistances(1, FY, 5000.0, 600e3, 100e3, 550e3, 80e3) == pytest.approx((5000.0 * FY, 600e3 * FY, 100e3 * FY))
    assert characteristic_resistances(3, FY, 5000.0, 600e3, 100e3, 550e3, 80e3) == pytest.approx((5000.0 * FY, 550e3 * FY, 80e3 * FY))
    N_Rk, M_y_Rk, M_z_Rk = characteristic_resistances(4, FY, 5000.0, A_eff=4500.0, W_eff_y=500e3)
    assert (N_Rk, M_y_Rk, M_z_Rk) == pytest.approx((4500.0 * FY, 500e3 * FY, None))


def test_interaction_factors_method_2_tables_B1_B2() -> None:
    common = {"N_Ed": 500e3, "N_Rk": 2000e3, "chi_y": 0.9, "chi_z": 0.6, "lambda_bar_y": 0.5, "lambda_bar_z": 1.0, "C_my": 0.8, "C_mz": 0.9}
    n_y, n_z = 500e3 / (0.9 * 2000e3), 500e3 / (0.6 * 2000e3)

    elastic = interaction_factors_method_2(**common, section_class=3, susceptible_to_torsion=False)
    assert elastic.k_yy == pytest.approx(0.8 * min(1.0 + 0.6 * 0.5 * n_y, 1.0 + 0.6 * n_y))
    assert elastic.k_zz == pytest.approx(0.9 * min(1.0 + 0.6 * 1.0 * n_z, 1.0 + 0.6 * n_z))
    assert elastic.k_yz == elastic.k_zz and elastic.k_zy == pytest.approx(0.8 * elastic.k_yy)

    plastic_rhs = interaction_factors_method_2(**common, shape="RHS", susceptible_to_torsion=False)
    assert plastic_rhs.k_zz == pytest.approx(0.9 * min(1.0 + 0.8 * n_z, 1.0 + 0.8 * n_z))
    assert plastic_rhs.k_yz == pytest.approx(0.6 * plastic_rhs.k_zz)

    plastic_i = interaction_factors_method_2(**common, C_mLT=0.6)
    assert plastic_i.k_zz == pytest.approx(0.9 * min(1.0 + 1.4 * n_z, 1.0 + 1.4 * n_z))
    assert plastic_i.k_zy == pytest.approx(max(1.0 - 0.1 * n_z / 0.35, 1.0 - 0.1 * n_z / 0.35))
    stocky = interaction_factors_method_2(**{**common, "lambda_bar_z": 0.3}, C_mLT=0.6)
    assert stocky.k_zy == pytest.approx(min(0.9, 1.0 - 0.1 * 0.3 * n_z / 0.35)) # lambda_z < 0.4
    elastic_torsion = interaction_factors_method_2(**common, section_class=3, C_mLT=0.6)
    assert elastic_torsion.k_zy == pytest.approx(max(1.0 - 0.05 * n_z / 0.35, 1.0 - 0.05 * n_z / 0.35))


def test_interaction_factors_method_1_limits() -> None:
    common = {
        "M_y_Ed": 100e6, "M_z_Ed": 0.0, "N_cr_y": 20e6, "N_cr_z": 6e6, "chi_y": 0.85, "chi_z": 0.5,
        "lambda_bar_y": 0.56, "lambda_bar_z": 1.02, "A": 20100.0, "fy": FY, "W_el_y": 2400e3, "W_el_z": 782e3,
        "W_pl_y": 2720e3, "W_pl_z": 1190e3, "I_y": 39600e4,
    }
    # elastic, not susceptible (lambda_bar_0 = 0): k_yy = C_my*mu_y/(1 - N/N_cr,y)
    elastic = interaction_factors_method_1(N_Ed=2000e3, section_class=3, C_my_0=0.9, **common)
    r_y = 2000e3 / 20e6
    mu_y = (1.0 - r_y) / (1.0 - 0.85 * r_y)
    assert elastic.k_yy == pytest.approx(0.9 * mu_y / (1.0 - r_y))
    assert elastic.C_mLT == 1.0

    # plastic without axial force: n_pl = 0 and b_LT = 0, so C_yy = 1 and k_yy = C_my*C_mLT
    plastic = interaction_factors_method_1(N_Ed=0.0, C_my_0=0.8, **common)
    assert plastic.metadata["C_yy"] == pytest.approx(1.0)
    assert plastic.k_yy == pytest.approx(0.8)

    # torsionally susceptible: lambda_bar_0 above the limit raises C_my towards 1 and C_mLT >= 1
    susceptible = interaction_factors_method_1(N_Ed=2000e3, N_cr_T=15e6, lambda_bar_0=0.8, chi_LT=0.7, C_my_0=0.6, I_t=425e4, **common)
    assert 0.6 < susceptible.C_my < 1.0
    assert susceptible.C_mLT >= 1.0
    with pytest.raises(ValueError):
        interaction_factors_method_1(N_Ed=7e6, **common)
    with pytest.raises(SectionClass4Error):
        interaction_factors_method_1(N_Ed=2000e3, section_class=4, **common)


def test_member_interaction_utilisations_6_61_6_62() -> None:
    factors = InteractionFactors(k_yy=1.0, k_yz=0.6, k_zy=0.8, k_zz=1.2, method="B", C_my=1.0, C_mz=1.0, C_mLT=1.0)
    u_y, u_z = member_interaction_utilisations(500e3, 100e6, 20e6, 0.9, 0.6, 0.8, 2000e3, 500e6, 200e6, factors)
    assert u_y == pytest.approx(500e3 / (0.9 * 2000e3) + 100e6 / (0.8 * 500e6) + 0.6 * 20e6 / 200e6)
    assert u_z == pytest.approx(500e3 / (0.6 * 2000e3) + 0.8 * 100e6 / (0.8 * 500e6) + 1.2 * 20e6 / 200e6)
    assert member_interaction_utilisations(500e3, 0.0, 0.0, 0.9, 0.6, 1.0, 2000e3, None, None, factors) == pytest.approx((500e3 / 1.8e6, 500e3 / 1.2e6))


def test_beam_column_method_2_hd_column() -> None:
    # HD 320x158 S355, L_cr = 6 m, N = 2500 kN, My = 150 kNm with psi = 0: C_my = C_mLT = 0.6, chi_LT = 1.0
    result = check_bending_and_axial_compression(HD("HD-320x158"), FY, N_Ed=2500e3, M_y_Ed=150e6, L_cr_y=6000.0, L_cr_z=6000.0, psi_y=0.0)
    assert result.section_class == SectionClass.CLASS_1
    assert result.factors.C_my == pytest.approx(0.6) and result.factors.C_mLT == pytest.approx(0.6)
    assert result.chi_LT == 1.0
    assert result.factors.k_yy == pytest.approx(0.68817953, rel=1e-6)
    assert result.factors.k_zz == pytest.approx(1.93313836, rel=1e-6)
    assert result.factors.k_zy == pytest.approx(0.80956360, rel=1e-6)
    assert result.utilisation_y == pytest.approx(0.51577489, rel=1e-6)
    assert result.utilisation_z == pytest.approx(0.79228811, rel=1e-6)
    assert result.utilisation.reference is not None and result.utilisation.reference.equation == "6.62"


def test_beam_column_method_1_and_hollow_sections() -> None:
    method_1 = check_bending_and_axial_compression(HD("HD-320x158"), FY, N_Ed=2500e3, M_y_Ed=150e6, L_cr_y=6000.0, L_cr_z=6000.0, psi_y=0.0, method="A")
    assert method_1.factors.method == "A"
    assert 0.6 < method_1.utilisation.utilisation < 0.8 # Method 2 gives 0.79

    rhs = check_bending_and_axial_compression(HFRHS("200x100x10.0"), FY, N_Ed=500e3, M_y_Ed=30e6, M_z_Ed=5e6, L_cr_y=4000.0, L_cr_z=4000.0)
    assert rhs.susceptible_to_torsion is False and rhs.chi_LT == 1.0
    assert rhs.factors.metadata["table"] == "B.1"

    channel = check_bending_and_axial_compression(PFC("300x100x46"), FY, N_Ed=100e3, M_y_Ed=20e6, L_cr_y=3000.0, L_cr_z=3000.0)
    assert any("doubly symmetric" in note for note in channel.metadata["notes"])
    with pytest.raises(ValueError):
        check_bending_and_axial_compression(HD("HD-320x158"), FY, N_Ed=-10.0, L_cr_y=6000.0, L_cr_z=6000.0)


def test_beam_column_class_4_additional_moments() -> None:
    result = check_bending_and_axial_compression(
        IPE("IPE-300"), FY, N_Ed=300e3, M_y_Ed=30e6, L_cr_y=3000.0, L_cr_z=3000.0, section_class=4,
        A_eff=5000.0, W_eff_y=540e3, W_eff_z=70e3, e_N_y=5.0, M_cr=300e6,
    )
    assert result.delta_M_y_Ed == pytest.approx(5.0 * 300e3)
    assert result.N_Rk == pytest.approx(5000.0 * FY)


# --- 6.3.4 General method ---
def test_general_method_6_63_to_6_66() -> None:
    # alpha_ult,k = 1.5, alpha_cr,op = 2.0: lambda_op = 0.866; chi (b) = 0.6829, chi_LT (c, general) = 0.6208
    result = check_general_method(1.5, 2.0, "b", "c")
    assert result.lambda_bar_op == pytest.approx(math.sqrt(0.75))
    assert result.chi_op == pytest.approx(0.62083919, rel=1e-6)
    assert result.utilisation.utilisation == pytest.approx(1.07381537, rel=1e-6)
    assert result.utilisation.adequacy == "FAILS"

    interpolated = check_general_method(1.5, 2.0, "b", "c", interpolate=True, N_Ed=400e3, N_Rk=1000e3, M_y_Ed=100e6, M_y_Rk=375e6)
    expected = 400e3 / (0.68294993 * 1000e3) + 100e6 / (0.62083919 * 375e6)
    assert interpolated.utilisation.utilisation == pytest.approx(expected, rel=1e-6)
    assert interpolated.utilisation.reference is not None and interpolated.utilisation.reference.equation == "6.66"
    with pytest.raises(ValueError):
        check_general_method(1.5, 2.0, "b", "c", interpolate=True)
