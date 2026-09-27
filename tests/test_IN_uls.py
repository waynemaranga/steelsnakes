"""IS 800:2025 (draft) ultimate limit states; formulas against the draft's own tables (Tables 4, 5, 7 to 18 and 42, with
the fcd of Table 9) and hand calculations on IS 808 sections built from their properties, as the IN module ships no data
yet. ISMB 300 in E250 (fy = 250, fu = 410 MPa) unless stated; I_t = Σbt³/3 and I_w = Iy hf²/4."""

import math

import pytest

from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.IN.checks.uls import (
    GAMMA_M0,
    GAMMA_M1,
    _as_section_class,
    angle_strut_modification_factor,
    annex_e_constants,
    beam_effective_length,
    block_shear_strength,
    buckling_class,
    buckling_shape,
    cantilever_effective_length,
    check_angle_strut,
    check_bending,
    check_compression,
    check_compression_and_bending,
    check_lateral_torsional_buckling,
    check_shear,
    check_slenderness,
    check_tension,
    check_tension_and_bending,
    connection_safety_factor,
    critical_bending_stress,
    design_compressive_stress,
    effective_length,
    effective_sectional_area,
    elastic_critical_moment,
    elastic_critical_moment_general,
    elastic_critical_shear_stress,
    elastic_torsional_buckling_stress,
    elastic_torsional_flexural_buckling_stress,
    equivalent_uniform_moment_factor,
    euler_buckling_stress,
    factored_load,
    flange_reduced_plastic_moment,
    frame_effective_length_factor,
    high_shear_design_moment,
    interaction_exponents,
    lateral_torsional_imperfection_factor,
    lateral_torsional_reduction_factor,
    load_factors,
    moment_gradient_factor,
    monosymmetry_constant,
    net_area,
    non_dimensional_slenderness,
    reduced_flexural_strength,
    segment_effective_length,
    shear_area,
    shear_buckling_coefficient,
    shear_buckling_required,
    shear_buckling_stress,
    shear_holes_negligible,
    shear_lag_factor,
    shear_lag_negligible,
    stiffness_ratio,
    stress_reduction_factor,
    tension_field_shear_resistance,
    tension_flange_holes_negligible,
    torsional_flexural_reduction_factor,
    warping_constant_mono_i,
    web_shear_slenderness,
)
from steelsnakes.IN.sections import EqualAngle, MediumWeightBeam, MediumWeightChannel, UnequalAngle

ROOT3 = math.sqrt(3.0)
E = 2.0e5
G = 0.769e5

# ISMB 300: D 300, B 140, t 7.5, T 12.4, R1 14 mm; A 56.26 cm², Izz 8603.6, Iyy 453.9 cm⁴, Zez 573.6, Zey 64.8, Zpz 651.7,
# Zpy 111.0 cm³; I_t = (2 x 140 x 12.4³ + 275.2 x 7.5³)/3 = 21.7 cm⁴, I_w = 453.9e4 x 287.6²/4 = 93 870 cm⁶
ISMB_300 = MediumWeightBeam(
    designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26,
    I_zz=8603.6, I_yy=453.9, Z_zz=573.6, Z_yy=64.8, Z_pz=651.7, Z_py=111.0, I_t=21.7, I_w=93_870.0,
)
RY_MM: float = math.sqrt(453.9 / 56.26) * 10.0 # 28.40 mm
ISMC_200 = MediumWeightChannel(
    designation="ISMC 200", D=200.0, B=75.0, t=6.1, T=11.4, R1=11.0, area=28.21,
    I_zz=1819.3, I_yy=140.4, Z_zz=181.9, Z_yy=26.3, Z_pz=211.2, Z_py=50.4,
)
# ISA 100x75x8 (unequal) and ISA 100x100x10 (equal); A from the legs, (a + b - t)t
ISA_100_75_8 = UnequalAngle(designation="ISA 100x75x8", a=100.0, b=75.0, t=8.0, area=13.36, I_zz=133.2, I_yy=64.1, I_uu=162.0, I_vy=35.3)
ISA_100_100_10 = EqualAngle(designation="ISA 100x100x10", a=100.0, b=100.0, t=10.0, area=19.0, I_zz=177.0, I_yy=177.0, I_uu=280.7, I_vy=73.3)


def _chi(lambda_bar: float, alpha: float) -> float:
    phi: float = 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar**2)
    return 1.0 / (phi + math.sqrt(phi**2 - lambda_bar**2))


# --- 9.2.4, 12.3.3 and 12.4.1: Tables 4 and 5 ---
def test_partial_safety_factors() -> None:
    assert (GAMMA_M0, GAMMA_M1) == (1.10, 1.25)
    assert connection_safety_factor("welds", "field") == 1.50
    assert connection_safety_factor("friction_bolts") == 1.25
    with pytest.raises(ValueError):
        connection_safety_factor("nails")


def test_load_combinations_of_table_4() -> None:
    assert load_factors("DL+IL+CL") == {"DL": 1.5, "IL_leading": 1.5, "IL_accompanying": 1.05}
    assert factored_load("DL+IL+CL", dead=10.0, imposed=20.0, imposed_accompanying=5.0).factored == pytest.approx(1.5 * 10.0 + 1.5 * 20.0 + 1.05 * 5.0)
    assert factored_load("DL+IL+CL+WL/EL", dead=10.0, imposed=20.0, wind=8.0).factored == pytest.approx(1.2 * 10.0 + 1.2 * 20.0 + 0.6 * 8.0)
    assert factored_load("DL+IL+CL+WL/EL (WL/EL leading)", dead=10.0, imposed=20.0, imposed_accompanying=4.0, wind=8.0).factored == pytest.approx(12.0 + 24.0 + 0.53 * 4.0 + 1.2 * 8.0)
    assert factored_load("DL+WL/EL", dead=10.0, wind=-12.0, dead_stabilising=True).factored == pytest.approx(0.9 * 10.0 - 1.5 * 12.0) # note 2
    assert factored_load("DL+IL+FL", dead=10.0, imposed=20.0, fire=5.0, storage=False).factored == pytest.approx(10.0 + 0.5 * 20.0 + 5.0) # note 3
    assert factored_load("DL+IL+AL", dead=10.0, imposed=20.0, accidental=50.0).factored == pytest.approx(10.0 + 0.35 * 20.0 + 50.0)
    assert factored_load("DL+IL+CL+WL/EL", imposed=20.0, wind=8.0, limit_state="serviceability").factored == pytest.approx(0.8 * 28.0)
    with pytest.raises(ValueError, match="no serviceability"):
        load_factors("DL+ER", "serviceability")
    with pytest.raises(ValueError, match="Unknown combination"):
        load_factors("DL+SL")


def test_maximum_slenderness_of_table_3() -> None:
    assert check_slenderness(170.0).adequacy == "OK"
    assert check_slenderness(200.0).adequacy == "FAILS" # 180
    assert check_slenderness(200.0, "compression_wind_earthquake").utilisation == pytest.approx(0.8) # 250
    assert check_slenderness(390.0, "tension").adequacy == "OK" # 400
    with pytest.raises(ValueError):
        check_slenderness(100.0, "strut")


# --- 13 Tension members ---
def test_net_area_with_staggered_holes() -> None:
    # 200 x 10 plate, two 22 mm holes and one inclined leg ps = 50, g = 60: [200 - 44 + 50²/240] x 10
    assert net_area(200.0, 10.0, 2, 22.0, [(50.0, 60.0)]) == pytest.approx((200.0 - 44.0 + 2500.0 / 240.0) * 10.0 / 100.0)
    assert net_area(200.0, 10.0, 2, 22.0, punched=True) == pytest.approx((200.0 - 48.0) * 10.0 / 100.0) # 2 mm more
    with pytest.raises(ValueError, match="net width"):
        net_area(40.0, 10.0, 2, 22.0)


def test_shear_lag_factor_and_block_shear() -> None:
    beta: float = 1.4 - 0.076 * (75.0 / 8.0) * (250.0 / 410.0) * (122.0 / 150.0)
    assert shear_lag_factor(75.0, 8.0, 250.0, 410.0, 122.0, 150.0) == pytest.approx(beta) # 1.0466
    assert shear_lag_factor(75.0, 8.0, 250.0, 410.0, 10.0, 500.0) == pytest.approx(0.9 * 410.0 * 1.1 / (250.0 * 1.25)) # upper bound
    assert shear_lag_factor(150.0, 6.0, 250.0, 410.0, 200.0, 50.0) == 0.7 # lower bound
    T_db1: float = 1500.0 * 250.0 / (ROOT3 * 1.1) + 0.9 * 400.0 * 410.0 / 1.25
    T_db2: float = 0.9 * 1100.0 * 410.0 / (ROOT3 * 1.25) + 600.0 * 250.0 / 1.1
    assert block_shear_strength(1500.0, 1100.0, 600.0, 400.0, 250.0, 410.0) == pytest.approx(min(T_db1, T_db2) / 1e3)


def test_tension_of_ismb_300_and_of_an_angle_connected_through_one_leg() -> None:
    result = check_tension(ISMB_300, T_kN=1000.0)
    assert result.Tdg == pytest.approx(5626.0 * 250.0 / 1.1 / 1e3) # 1278.6 kN
    assert result.Tdn == pytest.approx(0.9 * 5626.0 * 410.0 / 1.25 / 1e3)
    assert (result.governing, result.method, result.limit_state) == ("yielding", "13.3.1", LimitState.TENSILE_YIELDING)
    assert result.utilisation.utilisation == pytest.approx(1000.0 / result.Tdg) # type: ignore[union-attr]

    # ISA 100x75x8, long leg bolted, one 20 mm hole, gauge 55 mm, three bolts over Lc = 150 mm
    angle = check_tension(ISA_100_75_8, An_cm2=13.36 - 1.6, Lc_mm=150.0, g_mm=55.0)
    A_go: float = (75.0 - 4.0) * 8.0 # mm²
    A_nc: float = 1176.0 - A_go
    beta: float = 1.4 - 0.076 * (75.0 / 8.0) * (250.0 / 410.0) * ((75.0 + 55.0 - 8.0) / 150.0)
    assert angle.beta == pytest.approx(beta)
    assert angle.Tdn == pytest.approx((0.9 * A_nc * 410.0 / 1.25 + beta * A_go * 250.0 / 1.1) / 1e3) # 314.6 kN
    assert angle.Tdg == pytest.approx(1336.0 * 250.0 / 1.1 / 1e3) # 303.6 kN governs
    assert (angle.method, angle.governing) == ("13.3.3", "yielding")
    welded = check_tension(ISA_100_75_8, Lc_mm=150.0, connection="welded", connected_leg="short")
    assert welded.Ago == pytest.approx((100.0 - 4.0) * 8.0 / 100.0) # the long leg is the outstand
    # block shear governs a short end connection
    short = check_tension(ISA_100_75_8, Avg_mm2=800.0, Avn_mm2=600.0, Atg_mm2=280.0, Atn_mm2=200.0)
    assert short.governing == "block shear"
    assert short.Td == pytest.approx(block_shear_strength(800.0, 600.0, 280.0, 200.0, 250.0, 410.0))
    rod = check_tension(section_type=SectionType.MWB, properties={"area": 3.53, "t": 1.0, "T": 1.0}, threaded_rod=True, An_cm2=2.45)
    assert (rod.method, rod.Tdn) == ("13.3.2", pytest.approx(0.9 * 245.0 * 410.0 / 1.25 / 1e3))


def test_tension_errors() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        check_tension(ISMB_300, An_cm2=60.0)
    with pytest.raises(ValueError, match="g_mm"):
        check_tension(ISA_100_75_8, Lc_mm=150.0)
    with pytest.raises(ValueError, match="Avg_mm2"):
        check_tension(ISMB_300, Avg_mm2=100.0)
    with pytest.raises(ValueError, match="Ago_cm2"):
        check_tension(ISMB_300, Lc_mm=150.0)


# --- 14 Compression members ---
def test_stress_reduction_factor_against_table_8() -> None:
    # Table 8(b) class a, fy = 250 MPa: 0.994 (KL/r = 20), 0.579 (100); Table 8(c) class b, fy = 200 MPa: 0.593 (100)
    assert stress_reduction_factor(non_dimensional_slenderness(20.0, 250.0), 0.21) == pytest.approx(0.994, abs=5e-4)
    assert stress_reduction_factor(non_dimensional_slenderness(100.0, 250.0), 0.21) == pytest.approx(0.579, abs=5e-4)
    assert stress_reduction_factor(non_dimensional_slenderness(100.0, 200.0), 0.34) == pytest.approx(0.593, abs=5e-4)
    assert stress_reduction_factor(0.1, 0.49) == 1.0
    assert non_dimensional_slenderness(100.0, 250.0) == pytest.approx(math.sqrt(250.0 / euler_buckling_stress(100.0)))
    with pytest.raises(ValueError):
        stress_reduction_factor(-0.1, 0.34)


@pytest.mark.parametrize(
    ("class_", "fy", "KL_r", "fcd"),
    [
        ("a0", 250.0, 50.0, 213.0), # Table 9(a)
        ("a", 250.0, 100.0, 132.0), # Table 9(b)
        ("a", 250.0, 150.0, 68.9),
        ("b", 250.0, 50.0, 194.0), # Table 9(c)
        ("b", 250.0, 100.0, 118.0),
        ("b", 250.0, 150.0, 64.0),
        ("b", 300.0, 100.0, 126.0),
        ("b", 450.0, 100.0, 139.0),
        ("c", 250.0, 50.0, 183.0), # Table 9(d)
        ("c", 250.0, 100.0, 107.0),
        ("c", 250.0, 150.0, 59.2),
        ("d", 250.0, 50.0, 167.0), # Table 9(e)
        ("d", 250.0, 100.0, 92.6),
        ("d", 250.0, 150.0, 52.6),
        ("b", 250.0, 10.0, 227.0), # fy/γm0
    ],
)
def test_design_compressive_stress_against_table_9(class_: str, fy: float, KL_r: float, fcd: float) -> None:
    assert design_compressive_stress(KL_r, fy, class_) == pytest.approx(fcd, abs=0.51 if fcd >= 100.0 else 0.051)


def test_buckling_classes_of_table_10() -> None:
    assert (buckling_class("rolled_I_tf_40", "z"), buckling_class("rolled_I_tf_40", "y")) == ("a", "b")
    assert (buckling_class("rolled_I_tf_40", "z", 450.0), buckling_class("rolled_I_tf_40", "y", 450.0)) == ("a0", "a")
    assert (buckling_class("rolled_H_tf_100", "y"), buckling_class("rolled_H_thick", "z", 450.0)) == ("c", "c")
    assert (buckling_class("welded_I_thick", "z"), buckling_class("welded_I_thick", "y")) == ("c", "d")
    assert (buckling_class("hot_rolled_hollow"), buckling_class("hot_rolled_hollow", fy_mpa=450.0)) == ("a", "a0")
    assert (buckling_class("cold_formed_hollow"), buckling_class("cold_formed_hollow", fy_mpa=450.0)) == ("b", "c")
    assert (buckling_class("rolled_angle", "v"), buckling_class("rolled_angle", "v", 450.0), buckling_class("channel_tee_solid")) == ("b", "a", "c")
    assert buckling_shape(SectionType.MWB, 300.0, 140.0, 12.4) == "rolled_I_tf_40" # h/bf = 2.14
    assert buckling_shape(SectionType.MWB, 300.0, 140.0, 45.0) == "rolled_I_tf_100"
    assert buckling_shape(SectionType.SC, 200.0, 200.0, 15.0) == "rolled_H_tf_100"
    assert buckling_shape(SectionType.SC, 500.0, 300.0, 110.0) == "rolled_H_thick"
    assert buckling_shape(SectionType.WPB, 300.0, 140.0, 12.4, welded=True) == "welded_I_tf_40"
    assert buckling_shape(SectionType.CFRHS) == "cold_formed_hollow"
    assert buckling_shape(SectionType.HFCHS, welded=True, thick_welds=True) == "welded_box_thick_welds"
    assert (buckling_shape(SectionType.MWC), buckling_shape(SectionType.UA, welded=True)) == ("channel_tee_solid", "welded_angle")
    with pytest.raises(NotImplementedError):
        buckling_shape(SectionType.UB)
    with pytest.raises(ValueError):
        buckling_class("tube")


def test_effective_lengths_of_table_11_and_annex_d() -> None:
    assert [effective_length(1000.0, key) for key in ("fixed_fixed", "fixed_pinned", "pinned_pinned", "fixed_sway_fixed", "fixed_free")] == [650.0, 800.0, 1000.0, 1200.0, 2000.0]
    with pytest.raises(ValueError):
        effective_length(1000.0, "hinged")
    # D-1: β = 0 fixed, 1 pinned
    assert frame_effective_length_factor(0.0, 0.0) == pytest.approx(0.5)
    assert frame_effective_length_factor(1.0, 1.0) == pytest.approx(1.0)
    assert frame_effective_length_factor(0.0, 0.0, sway=True) == pytest.approx(1.0)
    assert frame_effective_length_factor(1.0, 0.0, sway=True) == pytest.approx(2.0)
    assert stiffness_ratio(2.0, 6.0) == pytest.approx(0.25)
    with pytest.raises(ValueError, match="mechanism"):
        frame_effective_length_factor(1.0, 1.0, sway=True)
    with pytest.raises(ValueError):
        frame_effective_length_factor(1.2, 0.0)


def test_compression_of_ismb_300() -> None:
    # KL = 4 m about both axes: y-y governs, KL/r = 4000/28.40 = 140.8, class b (Table 10), χ = 0.313
    result = check_compression(ISMB_300, P_kN=350.0, KLz_mm=4000.0, KLy_mm=4000.0)
    lambda_y: float = 4000.0 / RY_MM / math.pi * math.sqrt(250.0 / E)
    P_dy: float = 5626.0 * _chi(lambda_y, 0.34) * 250.0 / 1.1 / 1e3
    assert result.Pdy == pytest.approx(P_dy) # 400.0 kN
    assert result.Pd == result.Pdy and result.governing_axis == "y"
    modes = {mode.axis: mode for mode in result.modes}
    assert (modes["z"].buckling_class, modes["y"].buckling_class) == ("a", "b")
    assert result.section_class == SectionClass.CLASS_2 # the web, 32.96 > 32ε
    assert result.utilisation.utilisation == pytest.approx(350.0 / P_dy) # type: ignore[union-attr]
    welded = check_compression(ISMB_300, KLy_mm=4000.0, welded=True)
    assert welded.modes[0].buckling_class == "c"
    override = check_compression(ISMB_300, KLy_mm=4000.0, buckling_classes={"y": "d"}, A_holes_cm2=2.0)
    assert override.Ae == pytest.approx(54.26) and override.modes[0].alpha == 0.76 # 14.3.2: holes not fitted
    slender = check_compression(ISMB_300, KLy_mm=6000.0)
    assert any("Table 3" in note for note in slender.metadata["notes"]) # 211 > 180
    with pytest.raises(ValueError, match="at least one"):
        check_compression(ISMB_300)


def test_class_4_effective_area() -> None:
    # A thin rolled web: d = 556 mm, t = 6 mm; 10.8.2 d): the width beyond 40.7εt = 244.2 mm is deducted
    data = {"D": 600.0, "B": 210.0, "t": 6.0, "T": 12.0, "R1": 10.0, "area": 83.0, "I_zz": 45_000.0, "I_yy": 1_860.0}
    effective = effective_sectional_area(section_type=SectionType.MWB, properties=data, fy_mpa=250.0)
    assert effective.section_class == SectionClass.CLASS_4
    assert effective.deductions == pytest.approx({"web": (556.0 - 244.2) * 6.0 / 100.0})
    assert effective.Ae == pytest.approx(83.0 - 18.708)
    result = check_compression(section_type=SectionType.MWB, properties=data, fy_mpa=250.0, KLy_mm=3000.0)
    assert result.Ae == pytest.approx(effective.Ae) and "10.8.2 d)" in result.metadata["notes"][0]
    assert check_compression(section_type=SectionType.MWB, properties=data, fy_mpa=250.0, KLy_mm=3000.0, A_eff_cm2=60.0).Ae == 60.0
    # a slender angle: ISA 100x100x8, (b + d)/t = 25 > 22.3 -> the longer leg loses (25 - 22.3) x 8 = 21.6 mm
    angle = effective_sectional_area(EqualAngle(designation="ISA 100x100x8", t=8.0, area=15.39))
    assert angle.deductions == pytest.approx({"angle": (200.0 - 22.3 * 8.0) * 8.0 / 100.0})


def test_torsional_flexural_buckling() -> None:
    # With λTF = λy and A fy ip²/(6.25 G IT) = 1, 14.1.2.2 reduces to the flexural buckling of 14.1.2.1
    A, fy, i_p = 5000.0, 250.0, 50.0
    I_T: float = A * fy * i_p**2 / (6.25 * G)
    assert torsional_flexural_reduction_factor(1.2, 1.2, 0.34, A, fy, i_p, I_T) == pytest.approx(stress_reduction_factor(1.2, 0.34))
    assert torsional_flexural_reduction_factor(0.9, 1.2, 0.34, A, fy, i_p, I_T, d_y_mm=30.0) < 1.0
    # classical elastic stresses
    f_cr_T: float = elastic_torsional_buckling_stress(56.26, 453.9, 8603.6, 21.7, 93_870.0, 4000.0)
    i0_sq: float = (453.9 + 8603.6) * 1e4 / 5626.0
    assert f_cr_T == pytest.approx((G * 21.7e4 + math.pi**2 * E * 93_870.0e6 / 4000.0**2) / (5626.0 * i0_sq))
    assert elastic_torsional_flexural_buckling_stress(300.0, 200.0, 0.0, 50.0) == pytest.approx(200.0) # y0 = 0: the lower
    assert elastic_torsional_flexural_buckling_stress(300.0, 200.0, 25.0, 50.0) < 200.0
    result = check_compression(ISMB_300, KLy_mm=4000.0, f_cr_TF_mpa=f_cr_T)
    assert result.Pd_TF is not None and result.Pd == min(result.Pdy, result.Pd_TF) # type: ignore[type-var]
    with pytest.raises(ValueError, match="y-y mode"):
        check_compression(ISMB_300, KLz_mm=4000.0, f_cr_TF_mpa=f_cr_T)
    with pytest.raises(ValueError, match="smaller than i0"):
        elastic_torsional_flexural_buckling_stress(300.0, 200.0, 60.0, 50.0)


# --- 14.5 Angle struts ---
def test_angle_strut_constants_of_table_12() -> None:
    # λaa = 1.0, λφ = 0.15
    assert angle_strut_modification_factor(1.0, 0.15, "welded", "fixed") == pytest.approx(0.798 + 0.563 - 2.072 * 0.15)
    assert angle_strut_modification_factor(1.0, 0.15, "two_bolts", "hinged") == pytest.approx(0.401 + 0.420 - 1.040 * 0.15)
    assert angle_strut_modification_factor(1.0, 0.15, "single_bolt", "fixed") == pytest.approx(0.418 + 0.547 - 1.400 * 0.15)
    assert angle_strut_modification_factor(1.0, 0.15, "single_bolt", "hinged") == pytest.approx(0.374 + 0.415 - 2.072 * 0.15)
    midway: float = angle_strut_modification_factor(1.0, 0.15, "welded", 0.5) # note 1: interpolated
    assert midway == pytest.approx(0.5 * (1.0502 + 0.665))
    with pytest.raises(ValueError):
        angle_strut_modification_factor(1.0, 0.15, "welded", 1.5)
    with pytest.raises(ValueError):
        angle_strut_modification_factor(1.0, 0.15, "welded", "pinned") # type: ignore[arg-type]


def test_single_angle_struts() -> None:
    scale: float = math.sqrt(math.pi**2 * E / 250.0) # ε = 1 at 250 MPa
    concentric = check_angle_strut(ISA_100_100_10, P_kN=100.0, L_mm=2000.0, loading="concentric")
    r_v: float = math.sqrt(73.3 / 19.0) * 10.0
    assert concentric.lambda_bar == pytest.approx(2000.0 / r_v / scale)
    assert concentric.fcd == pytest.approx(_chi(2000.0 / r_v / scale, 0.34) * 250.0 / 1.1) # class b, rolled angle
    one_leg = check_angle_strut(ISA_100_100_10, P_kN=100.0, L_mm=2000.0, connection="two_bolts", fixity="hinged")
    r_aa: float = math.sqrt(177.0 / 19.0) * 10.0
    lambda_aa: float = 2000.0 / r_aa / scale
    lambda_phi: float = (200.0 / 20.0) / scale
    K_f: float = 0.401 + 0.420 * lambda_aa - 1.040 * lambda_phi
    assert (one_leg.lambda_bar, one_leg.lambda_phi, one_leg.Kf) == pytest.approx((lambda_aa, lambda_phi, K_f))
    assert one_leg.Pd == pytest.approx(1900.0 * K_f * _chi(lambda_aa, 0.34) * 250.0 / 1.1 / 1e3)
    # an unequal angle on its long leg buckles about the axis parallel to it, with the smaller rectangular I
    unequal = check_angle_strut(ISA_100_75_8, L_mm=1500.0, connected_leg="long")
    assert unequal.r == pytest.approx(math.sqrt(64.1 / 13.36) * 10.0)
    assert check_angle_strut(ISA_100_75_8, L_mm=1500.0, connected_leg="short").r == pytest.approx(math.sqrt(133.2 / 13.36) * 10.0)
    with pytest.raises(ValueError, match="single angles"):
        check_angle_strut(ISMB_300, L_mm=1500.0)


# --- 15.4 Shear ---
def test_shear_areas() -> None:
    assert shear_area(ISMB_300) == pytest.approx(300.0 * 7.5 / 100.0) # hot rolled h tw
    assert shear_area(ISMB_300, welded=True) == pytest.approx(275.2 * 7.5 / 100.0) # welded d tw
    assert shear_area(ISMB_300, axis="y") == pytest.approx(2.0 * 140.0 * 12.4 / 100.0) # 2b tf
    rhs = {"D": 200.0, "B": 100.0, "t": 5.0, "A": 28.4}
    assert shear_area(section_type=SectionType.HFRHS, properties=rhs) == pytest.approx(28.4 * 200.0 / 300.0)
    assert shear_area(section_type=SectionType.HFRHS, properties=rhs, axis="y") == pytest.approx(28.4 * 100.0 / 300.0)
    assert shear_area(section_type=SectionType.HFCHS, properties={"D": 219.1, "t": 5.0, "A": 33.6}) == pytest.approx(2.0 * 33.6 / math.pi)
    with pytest.raises(NotImplementedError):
        shear_area(ISA_100_75_8)


def test_shear_of_ismb_300() -> None:
    result = check_shear(ISMB_300, V_kN=200.0)
    assert result.Vp == pytest.approx(2250.0 * 250.0 / ROOT3 / 1e3)
    assert result.Vd == pytest.approx(result.Vp / 1.1) # 295.2 kN
    assert not result.shear_buckling and result.d_tw == pytest.approx(275.2 / 7.5)
    assert result.high_shear # 200 > 0.6 x 295.2
    assert result.limit_state == LimitState.SHEAR_YIELDING
    # 15.4.1.1 NOTE: holes count where Avn < (fy/fu)(γm1/γm0)Av/0.9 = 0.770Av
    assert shear_holes_negligible(18.0, 22.5, 250.0, 410.0) and not shear_holes_negligible(17.0, 22.5, 250.0, 410.0)
    holes = check_shear(ISMB_300, Avn_cm2=15.0)
    assert holes.Av == pytest.approx(0.9 * 15.0 * (410.0 / 250.0) * (1.1 / 1.25)) and holes.metadata["notes"]
    assert check_shear(ISMB_300, Avn_cm2=20.0).Av == pytest.approx(22.5)


def test_shear_buckling_simple_post_critical_and_tension_field() -> None:
    assert shear_buckling_coefficient() == 5.35
    assert shear_buckling_coefficient(0.5) == pytest.approx(4.0 + 5.35 / 0.25)
    assert shear_buckling_coefficient(2.0) == pytest.approx(5.35 + 1.0)
    assert shear_buckling_required(70.0, 250.0) and not shear_buckling_required(66.0, 250.0)
    assert not shear_buckling_required(90.0, 250.0, Kv=shear_buckling_coefficient(0.5)) # 67 x (25.4/5.35)^0.5 = 146
    assert shear_buckling_stress(0.5, 250.0) == pytest.approx(250.0 / ROOT3)
    assert shear_buckling_stress(1.0, 250.0) == pytest.approx(0.84 * 250.0 / ROOT3)
    assert shear_buckling_stress(1.5, 250.0) == pytest.approx(250.0 / (ROOT3 * 2.25))

    # Plate girder web 960 x 8, fy = 250 MPa: d/tw = 120 > 67
    girder = {"D": 1000.0, "B": 300.0, "t": 8.0, "T": 20.0, "R1": 0.0, "area": 196.8}
    tau_cr: float = 5.35 * math.pi**2 * E / (12.0 * (1.0 - 0.09) * 120.0**2)
    assert elastic_critical_shear_stress(120.0) == pytest.approx(tau_cr) # 67.2 MPa
    lambda_w: float = math.sqrt(250.0 / (ROOT3 * tau_cr))
    assert web_shear_slenderness(120.0, 250.0) == pytest.approx(lambda_w) # 1.466
    post = check_shear(section_type=SectionType.WPB, properties=girder, fy_mpa=250.0, V_kN=400.0, welded=True)
    A_v: float = 960.0 * 8.0 # welded d tw
    assert post.shear_buckling and post.method == "15.4.2.2 a)"
    assert post.Vcr == pytest.approx(A_v * 250.0 / (ROOT3 * lambda_w**2) / 1e3) # Av τb
    assert post.Vd == pytest.approx(post.Vcr / 1.1) # type: ignore[operator]
    assert post.limit_state == LimitState.SHEAR_BUCKLING
    tension_field = check_shear(section_type=SectionType.WPB, properties=girder, fy_mpa=250.0, welded=True, c_mm=1200.0, method="tension_field")
    assert tension_field.method == "15.4.2.2 b)"
    assert tension_field.Vcr < tension_field.Vn <= tension_field.Vp # type: ignore[operator]
    assert flange_reduced_plastic_moment(300.0, 20.0, 250.0) == pytest.approx(0.25 * 300.0 * 400.0 * 250.0 / 1e6)
    assert flange_reduced_plastic_moment(300.0, 20.0, 250.0, Nf_kN=300.0 * 20.0 * 250.0 / 1.1 / 1e3) == pytest.approx(0.0)
    with pytest.raises(ValueError, match="c/d >= 1.0"):
        tension_field_shear_resistance(960.0, 8.0, 600.0, 250.0, 76.8, 7.5, 7.5)
    with pytest.raises(ValueError, match="intermediate stiffeners"):
        check_shear(section_type=SectionType.WPB, properties=girder, fy_mpa=250.0, method="tension_field")


# --- 15.2.1 Laterally supported beams and 16.2 high shear ---
def test_bending_of_ismb_300() -> None:
    result = check_bending(ISMB_300, M_kNm=120.0)
    assert result.Md == pytest.approx(651.7 * 250.0 / 1.1 / 1e3) # 148.1 kNm
    assert result.Md_limit == pytest.approx(1.2 * 573.6 * 250.0 / 1.1 / 1e3)
    assert (result.section_class, result.beta_b, result.modulus) == (SectionClass.CLASS_1, 1.0, "Zp")
    # minor axis: βb Zp fy/γm0 = 25.2 kNm exceeds 1.2 Ze fy/γm0 = 17.7 kNm, which governs
    minor = check_bending(ISMB_300, axis="y")
    assert minor.Md == pytest.approx(1.2 * 64.8 * 250.0 / 1.1 / 1e3)
    assert check_bending(ISMB_300, axis="y", cantilever=True).Md == pytest.approx(1.5 * 64.8 * 250.0 / 1.1 / 1e3) # 22.1 < 25.2 kNm
    semi = check_bending(ISMB_300, section_class="semi-compact")
    assert (semi.Md, semi.beta_b) == (pytest.approx(573.6 * 250.0 / 1.1 / 1e3), pytest.approx(573.6 / 651.7))
    assert check_bending(ISMB_300, section_class=4, Z_eff_cm3=500.0).Md == pytest.approx(500.0 * 250.0 / 1.1 / 1e3)
    slender_shear = check_bending(ISMB_300, section_class=4, Z_eff_cm3=500.0, V_kN=250.0)
    assert slender_shear.Md == pytest.approx(500.0 * 250.0 / 1.1 / 1e3) and any("15.2.1.1" in note for note in slender_shear.metadata["notes"])
    with pytest.raises(ValueError, match="Z_eff_cm3"):
        check_bending(ISMB_300, section_class=4)
    with pytest.raises(ValueError, match="axis"):
        check_bending(ISMB_300, axis="x") # type: ignore[arg-type]


def test_bending_under_high_shear() -> None:
    # V = 250 kN > 0.6Vd = 177.1 kN; β = (2V/Vd - 1)², Mfd = (Zp - tw D²/4) fy/γm0
    V_d: float = 2250.0 * 250.0 / ROOT3 / 1.1 / 1e3
    beta: float = (2.0 * 250.0 / V_d - 1.0) ** 2
    M_d: float = 651.7 * 250.0 / 1.1 / 1e3
    M_fd: float = (651.7 - 7.5 * 300.0**2 / 4.0 / 1e3) * 250.0 / 1.1 / 1e3
    result = check_bending(ISMB_300, M_kNm=100.0, V_kN=250.0)
    assert (result.high_shear, result.beta, result.Mfd) == (True, pytest.approx(beta), pytest.approx(M_fd))
    assert result.Md == pytest.approx(M_d - beta * (M_d - M_fd)) # 129.7 kNm
    assert result.reference.clause == "16.2.2" # type: ignore[union-attr]
    assert not check_bending(ISMB_300, V_kN=150.0).high_shear
    assert high_shear_design_moment(148.0, 110.0, 250.0, V_d, 573.6, 250.0, 3) == pytest.approx(573.6 * 250.0 / 1.1 / 1e3) # semi-compact
    assert high_shear_design_moment(150.0, 120.0, V_d, V_d, 573.6, 250.0) == pytest.approx(120.0) # β = 1: Mfd
    assert high_shear_design_moment(200.0, 190.0, V_d, V_d, 573.6, 250.0) == pytest.approx(1.2 * 573.6 * 250.0 / 1.1 / 1e3) # capped


def test_holes_and_shear_lag_in_flanges() -> None:
    limit: float = (250.0 / 410.0) * (1.25 / 1.1) / 0.9 # 0.770
    assert tension_flange_holes_negligible(0.78, 250.0, 410.0)
    assert not tension_flange_holes_negligible(limit - 0.01, 250.0, 410.0)
    assert shear_lag_negligible(150.0, 3000.0) and not shear_lag_negligible(160.0, 3000.0) # L0/20
    assert shear_lag_negligible(300.0, 3000.0, "internal") # L0/10


# --- 15.3 Effective lengths for lateral torsional buckling ---
def test_effective_lengths_of_tables_15_and_16() -> None:
    assert beam_effective_length(6000.0) == 6000.0
    assert beam_effective_length(6000.0, "no_warping_restraint", "destabilizing") == pytest.approx(7200.0)
    assert beam_effective_length(6000.0, "both_flanges_fully_restrained") == pytest.approx(4200.0)
    assert beam_effective_length(6000.0, "bottom_flange_bearing", "destabilizing", D=300.0) == pytest.approx(1.4 * 6000.0 + 600.0)
    assert cantilever_effective_length(2000.0) == 6000.0
    assert cantilever_effective_length(2000.0, "built_in", "torsional", "destabilizing") == pytest.approx(1200.0)
    assert segment_effective_length(2000.0, "destabilizing") == pytest.approx(2400.0)
    assert segment_effective_length(2000.0, partial=True) == pytest.approx(2400.0)
    with pytest.raises(ValueError):
        beam_effective_length(6000.0, "free")
    with pytest.raises(ValueError):
        cantilever_effective_length(2000.0, "built_in", "fixed")
    with pytest.raises(ValueError, match="D must be positive"):
        beam_effective_length(6000.0, "bottom_flange_connected")


# --- 15.2.2 Laterally unsupported beams, Tables 13 and 14, Annex E ---
def test_elastic_critical_moment() -> None:
    L: float = 4000.0
    M_cr: float = math.sqrt(math.pi**2 * E * 453.9e4 / L**2 * (G * 21.7e4 + math.pi**2 * E * 93_870.0e6 / L**2)) / 1e6
    assert elastic_critical_moment(453.9, 21.7, 93_870.0, L) == pytest.approx(M_cr) # 125.8 kNm
    assert elastic_critical_moment_general(453.9, 21.7, 93_870.0, L) == pytest.approx(M_cr) # c1 = 1, K = Kw = 1, yg = yj = 0
    # destabilizing load on the top flange lowers Mcr; K = 0.5 raises it
    assert elastic_critical_moment_general(453.9, 21.7, 93_870.0, L, 1.132, 0.459, 0.525, yg_mm=150.0) < 1.132 * M_cr
    assert elastic_critical_moment_general(453.9, 21.7, 93_870.0, L, K=0.5) > M_cr
    slenderness: float = L / RY_MM
    f_crb: float = 1.1 * math.pi**2 * E / slenderness**2 * math.sqrt(1.0 + (slenderness / (287.6 / 12.4)) ** 2 / 20.0)
    assert critical_bending_stress(L, RY_MM, 287.6, 12.4) == pytest.approx(f_crb)


def test_annex_e_constants_of_table_42() -> None:
    assert annex_e_constants(1.0) == (1.0, 0.0, 1.0)
    assert annex_e_constants(0.0, 0.5) == (2.150, 0.0, 2.150)
    assert annex_e_constants(-1.0, 0.7) == (3.063, 0.0, 0.000)
    c1, _, c3 = annex_e_constants(0.625) # between ψ = 3/4 and 1/2
    assert (c1, c3) == pytest.approx((0.5 * (1.141 + 1.323), 0.5 * (0.998 + 0.992)))
    assert annex_e_constants("udl_simply_supported") == (1.132, 0.459, 0.525)
    assert annex_e_constants("point_load_fixed_ends", 0.5) == (0.938, 0.715, 4.800)
    for bad in ((1.5, 1.0), (0.0, 0.6), ("udl_simply_supported", 0.7), ("cantilever", 1.0)):
        with pytest.raises(ValueError):
            annex_e_constants(*bad) # type: ignore[arg-type]
    assert monosymmetry_constant(0.5, 400.0) == 0.0
    assert monosymmetry_constant(0.75, 400.0) == pytest.approx(0.8 * 0.5 * 200.0)
    assert monosymmetry_constant(0.25, 400.0, lipped=True, hL_mm=40.0, h_mm=400.0) == pytest.approx(-0.5 * 1.1 * 200.0)
    assert warping_constant_mono_i(0.5, 453.9, 287.6) == pytest.approx(453.9e4 * 287.6**2 / 4.0 / 1e6)


def test_imperfection_parameter_of_table_13() -> None:
    assert lateral_torsional_imperfection_factor("rolled_I", 300.0, 140.0, 12.4, 573.6, 64.8) == 0.34 # 0.12 x 2.98, capped
    assert lateral_torsional_imperfection_factor("rolled_I", 300.0, 140.0, 12.4, 400.0, 100.0) == pytest.approx(0.24)
    assert lateral_torsional_imperfection_factor("rolled_I", 900.0, 400.0, 45.0, 400.0, 100.0) == pytest.approx(0.32) # 0.16 x 2
    assert lateral_torsional_imperfection_factor("rolled_I", 300.0, 300.0, 45.0, 400.0, 100.0) == pytest.approx(0.24) # h/b <= 1.2
    assert lateral_torsional_imperfection_factor("welded_I", 900.0, 300.0, 50.0, 900.0, 100.0) == 0.34
    assert lateral_torsional_imperfection_factor("rolled_unequal_I", 400.0, 200.0) == 0.21
    assert lateral_torsional_imperfection_factor("welded_unequal_I", 600.0, 200.0) == 0.76
    assert lateral_torsional_imperfection_factor("other_rolled") == 0.76
    with pytest.raises(ValueError):
        lateral_torsional_imperfection_factor("tee")


def test_moment_gradient_factor_of_table_14() -> None:
    assert moment_gradient_factor() == 1.0
    assert [moment_gradient_factor("end_moments", psi) for psi in (1.0, 0.0, -1.0)] == pytest.approx([1.0, 1.25, 1.2])
    assert (moment_gradient_factor("udl"), moment_gradient_factor("point_load")) == (1.05, 1.10)
    assert moment_gradient_factor("udl_with_end_moments", M0_Mh=1.0) == pytest.approx(2.02)
    assert moment_gradient_factor("udl_with_end_moment", M0_Mh=1.0) == pytest.approx(1.475)
    assert moment_gradient_factor("point_load_with_end_moments", M0_Mh=1.0) == pytest.approx(1.95)
    assert moment_gradient_factor("point_load_with_end_moment", M0_Mh=1.0) == pytest.approx(1.40)
    # the polynomials meet the constants at their limits
    for case, limit, constant in (("udl_with_end_moments", 2.0, 1.05), ("udl_with_end_moment", 1.47, 1.05), ("point_load_with_end_moments", 2.0, 1.10), ("point_load_with_end_moment", 1.5, 1.10)):
        assert moment_gradient_factor(case, M0_Mh=limit - 1e-9) == pytest.approx(constant, abs=0.015)
        assert moment_gradient_factor(case, M0_Mh=limit) == constant
    assert moment_gradient_factor("udl_with_end_moments", M0_Mh=-0.5) == 1.0 # M0/Mh < 0
    for bad in (("end_moments", 1.5, None), ("udl_with_end_moments", 1.0, None), ("wind", 1.0, None)):
        with pytest.raises(ValueError):
            moment_gradient_factor(*bad) # type: ignore[arg-type]


def test_lateral_torsional_reduction_factor() -> None:
    general: float = lateral_torsional_reduction_factor(1.1, 0.34)
    assert general == pytest.approx(_chi(1.1, 0.34))
    # λy = λLT and fm = 1 make the doubly symmetric formula the general one
    assert lateral_torsional_reduction_factor(1.1, 0.34, 1.0, 1.1) == pytest.approx(general)
    assert lateral_torsional_reduction_factor(1.1, 0.34, 1.25, 1.6) > lateral_torsional_reduction_factor(1.1, 0.34, 1.0, 1.6)
    assert lateral_torsional_reduction_factor(0.2, 0.34, 1.25, 0.5) == 1.0
    with pytest.raises(ValueError):
        lateral_torsional_reduction_factor(-0.1, 0.34)


def test_lateral_torsional_buckling_of_ismb_300() -> None:
    # LLT = 4 m, uniform load (fm = 1.05): Mcr = 125.8 kNm, λLT = 1.138, λy = 1.585, αLT = 0.34
    L: float = 4000.0
    M_cr: float = elastic_critical_moment(453.9, 21.7, 93_870.0, L)
    lambda_LT: float = math.sqrt(651.7 * 250.0 / 1e3 / M_cr)
    lambda_y: float = L / RY_MM / math.pi * math.sqrt(250.0 / E)
    phi: float = 0.5 * (1.0 + 1.05 * ((lambda_LT / lambda_y) ** 2 * 0.34 * (lambda_y - 0.2) + lambda_LT**2))
    chi: float = 1.05 / (phi + math.sqrt(phi**2 - 1.05 * lambda_LT**2))
    result = check_lateral_torsional_buckling(ISMB_300, LLT_mm=L, Mz_kNm=80.0, fm=1.05)
    assert (result.Mcr, result.lambda_LT, result.lambda_y, result.alpha_LT) == pytest.approx((M_cr, lambda_LT, lambda_y, 0.34))
    assert result.chi_LT == pytest.approx(chi) # 0.553
    assert result.Md == pytest.approx(651.7 * chi * 250.0 / 1.1 / 1e3) # 81.9 kNm
    assert result.utilisation.utilisation == pytest.approx(80.0 / result.Md) # type: ignore[union-attr]
    approximate = check_lateral_torsional_buckling(ISMB_300, LLT_mm=L, approximate=True)
    assert approximate.Mcr == pytest.approx(651.7 * critical_bending_stress(L, RY_MM, 287.6, 12.4) / 1e3)
    no_torsion = check_lateral_torsional_buckling(ISMB_300, LLT_mm=L, properties={"I_t": 0.0, "I_w": 0.0})
    assert no_torsion.fcrb is not None and any("approximate" in note for note in no_torsion.metadata["notes"])
    stocky = check_lateral_torsional_buckling(ISMB_300, LLT_mm=500.0, Mz_kNm=100.0) # λLT < 0.4
    assert (stocky.susceptible, stocky.method, stocky.Md) == (False, "15.2.2 c)", pytest.approx(stocky.Md_supported))
    given = check_lateral_torsional_buckling(ISMB_300, LLT_mm=L, Mcr_kNm=250.0, alpha_LT=0.49)
    assert (given.Mcr, given.alpha_LT) == (250.0, 0.49)


def test_lateral_torsional_buckling_of_other_sections() -> None:
    # a channel takes αLT = 0.76 and the general formula, without fm
    channel = check_lateral_torsional_buckling(ISMC_200, LLT_mm=3000.0, fm=1.1, approximate=True)
    assert channel.alpha_LT == 0.76 and channel.lambda_y is None
    assert channel.chi_LT == pytest.approx(_chi(channel.lambda_LT, 0.76)) # type: ignore[arg-type]
    assert any("fm" in note for note in channel.metadata["notes"])
    rhs = check_lateral_torsional_buckling(section_type=SectionType.HFRHS, properties={"D": 200.0, "B": 100.0, "t": 5.0, "A": 28.4, "Z_zz": 142.0, "Z_pz": 174.0}, fy_mpa=250.0, LLT_mm=6000.0)
    assert (rhs.susceptible, rhs.method) == (False, "15.2.2 b)")
    with pytest.raises(NotImplementedError, match="Mcr_kNm"):
        check_lateral_torsional_buckling(ISA_100_75_8, LLT_mm=2000.0, section_class=3, properties={"Z_zz": 19.0})
    # data with the major axis under the y keys (EN-style) is read as z-z
    swapped = {"D": 300.0, "B": 140.0, "t": 7.5, "T": 12.4, "R1": 14.0, "area": 56.26, "I_yy": 8603.6, "I_zz": 453.9, "Z_yy": 573.6, "Z_zz": 64.8, "Z_py": 651.7, "Z_pz": 111.0}
    assert check_bending(section_type=SectionType.MWB, properties=swapped).Md == pytest.approx(651.7 * 250.0 / 1.1 / 1e3)


# --- 16 Combined forces ---
def test_reduced_flexural_strength_of_16_3_1_2() -> None:
    assert reduced_flexural_strength("rolled_I", 0.1, 20.0, 150.0) == pytest.approx((20.0, 1.11 * 0.9 * 150.0))
    assert reduced_flexural_strength("rolled_I", 0.5, 20.0, 150.0) == pytest.approx((1.56 * 20.0 * 0.5 * 1.1, 1.11 * 0.5 * 150.0))
    a: float = (5626.0 - 2.0 * 140.0 * 12.4) / 5626.0 # 0.383
    M_ndy, M_ndz = reduced_flexural_strength("welded_I", 0.6, 20.0, 150.0, 56.26, 140.0, 12.4)
    assert M_ndy == pytest.approx(20.0 * (1.0 - ((0.6 - a) / (1.0 - a)) ** 2))
    assert M_ndz == pytest.approx(min(150.0 * 0.4 / (1.0 - 0.5 * a), 150.0))
    assert reduced_flexural_strength("welded_I", 0.2, 20.0, 150.0, 56.26, 140.0, 12.4)[0] == 20.0 # n < a
    assert reduced_flexural_strength("CHS", 0.5, 50.0, 50.0) == pytest.approx((1.04 * 50.0 * (1.0 - 0.5**1.7),) * 2)
    assert reduced_flexural_strength("plate", 0.5, 10.0, 10.0) == pytest.approx((7.5, 7.5))
    a_w: float = min((2840.0 - 2.0 * 100.0 * 5.0) / 2840.0, 0.5)
    assert reduced_flexural_strength("RHS", 0.4, 30.0, 40.0, 28.4, 100.0, 5.0, 200.0, 5.0)[1] == pytest.approx(min(40.0 * 0.6 / (1.0 - 0.5 * a_w), 40.0))
    with pytest.raises(ValueError):
        reduced_flexural_strength("angle", 0.5, 1.0, 1.0)


def test_constants_of_table_17() -> None:
    assert interaction_exponents("I", 0.1) == (1.0, 2.0)
    assert interaction_exponents("channel", 0.4) == (2.0, 2.0)
    assert interaction_exponents("CHS", 0.7) == (2.0, 2.0)
    assert interaction_exponents("RHS", 0.5) == pytest.approx((1.66 / (1.0 - 1.13 * 0.25),) * 2)
    assert interaction_exponents("RHS", 0.95) == (6.0, 6.0)
    assert interaction_exponents("solid_rectangle", 0.5) == pytest.approx((1.955, 1.955))
    with pytest.raises(ValueError):
        interaction_exponents("tee", 0.5)


def test_equivalent_uniform_moment_factor_of_table_18() -> None:
    assert [equivalent_uniform_moment_factor(psi) for psi in (1.0, 0.0, -1.0)] == pytest.approx([1.0, 0.6, 0.4])
    assert equivalent_uniform_moment_factor(1.0, alpha_s=0.5) == pytest.approx(0.6)
    assert equivalent_uniform_moment_factor(0.5, alpha_s=-0.5) == pytest.approx(0.5)
    assert equivalent_uniform_moment_factor(0.5, alpha_s=-0.4, loading="concentrated") == pytest.approx(0.4) # -0.8αs >= 0.4
    assert equivalent_uniform_moment_factor(-0.5, alpha_s=-0.5) == pytest.approx(0.1 * 1.5 + 0.4)
    assert equivalent_uniform_moment_factor(-0.5, alpha_s=-0.5, loading="concentrated") == pytest.approx(0.2 * 1.5 + 0.4) # as printed
    assert equivalent_uniform_moment_factor(1.0, alpha_h=0.5) == pytest.approx(0.925) # 0.95 - 0.05αh, as printed
    assert equivalent_uniform_moment_factor(1.0, alpha_h=0.5, loading="concentrated") == pytest.approx(0.95)
    assert equivalent_uniform_moment_factor(0.5, alpha_h=-0.5) == pytest.approx(0.925)
    assert equivalent_uniform_moment_factor(-0.5, alpha_h=-0.5, loading="concentrated") == pytest.approx(0.90) # (1 + 2ψ) = 0
    assert equivalent_uniform_moment_factor(0.3, sway=True) == 0.9
    for bad in ({"psi": 1.2}, {"alpha_s": 1.5}, {"alpha_h": -1.5}):
        with pytest.raises(ValueError):
            equivalent_uniform_moment_factor(**bad) # type: ignore[arg-type]


def test_tension_and_bending_of_ismb_300() -> None:
    # T = 300 kN, Mz = 60 kNm: n = 300/1278.6; Mndz = 1.11 Mdz (1 - n); (Mz/Mndz)² against the linear form
    T_d: float = 5626.0 * 250.0 / 1.1 / 1e3
    M_dz: float = 651.7 * 250.0 / 1.1 / 1e3
    n: float = 300.0 / T_d
    M_ndz: float = min(1.11 * M_dz * (1.0 - n), M_dz)
    result = check_tension_and_bending(ISMB_300, T_kN=300.0, Mz_kNm=60.0, LLT_mm=4000.0)
    assert (result.Nd, result.Mdz, result.Mndz, result.alpha_2) == pytest.approx((T_d, M_dz, M_ndz, 2.0))
    assert result.utilisations["section (16.3.1.1)"] == pytest.approx((60.0 / M_ndz) ** 2)
    assert result.utilisations["section, conservative (16.3.1.1)"] == pytest.approx(n + 60.0 / M_dz)
    # 16.3.2.1: Meff = M - T Zec/A
    assert result.Meff == pytest.approx(60.0 - 300.0 * 573.6 / 56.26 / 100.0)
    assert result.utilisations["member, Meff/Md (16.3.2.1)"] == pytest.approx(result.Meff / result.Md_LT) # type: ignore[operator]
    independent = check_tension_and_bending(ISMB_300, T_kN=300.0, Mz_kNm=60.0, LLT_mm=4000.0, independent=True)
    assert independent.Meff == pytest.approx(60.0 - 0.8 * 300.0 * 573.6 / 56.26 / 100.0)
    semi = check_tension_and_bending(ISMB_300, T_kN=300.0, Mz_kNm=60.0, My_kNm=5.0, section_class=3)
    assert semi.method == "16.3.1.3" and semi.Mndz is None


def test_compression_and_bending_of_ismb_300() -> None:
    # P = 300 kN, Mz = 60 kNm, My = 3 kNm; KL = LLT = 4 m, Cmy = Cmz = CmLT = 1.0
    result = check_compression_and_bending(ISMB_300, P_kN=300.0, My_kNm=3.0, Mz_kNm=60.0, KLy_mm=4000.0, KLz_mm=4000.0, LLT_mm=4000.0)
    compression = check_compression(ISMB_300, KLz_mm=4000.0, KLy_mm=4000.0)
    modes = {mode.axis: mode for mode in compression.modes}
    ltb = check_lateral_torsional_buckling(ISMB_300, LLT_mm=4000.0, P_kN=300.0)
    M_dy: float = check_bending(ISMB_300, axis="y", P_kN=300.0).Md
    n_y, n_z = 300.0 / compression.Pdy, 300.0 / compression.Pdz # type: ignore[operator]
    K_y: float = min(1.0 + (modes["y"].lambda_bar - 0.2) * n_y, 1.0 + 0.8 * n_y)
    K_z: float = min(1.0 + (modes["z"].lambda_bar - 0.2) * n_z, 1.0 + 0.8 * n_z)
    K_LT: float = max(1.0 - 0.1 * ltb.lambda_LT * n_y / 0.75, 1.0 - 0.1 * n_y / 0.75) # type: ignore[operator]
    assert (result.Pdy, result.Pdz, result.Md_LT) == pytest.approx((compression.Pdy, compression.Pdz, ltb.Md))
    assert (result.Ky, result.Kz, result.KLT) == pytest.approx((K_y, K_z, K_LT))
    assert result.utilisations["member, y-y (16.3.2.2)"] == pytest.approx(n_y + K_y * 3.0 / M_dy + K_LT * 60.0 / ltb.Md)
    assert result.utilisations["member, z-z (16.3.2.2)"] == pytest.approx(n_z + 0.6 * K_y * 3.0 / M_dy + K_z * 60.0 / ltb.Md)
    assert result.governing == "member, y-y (16.3.2.2)" and result.utilisation.adequacy == "FAILS"
    # 16.3.1: the section, rolled I-section approximations with Nd = Ag fy/γm0
    N_d: float = 5626.0 * 250.0 / 1.1 / 1e3
    assert result.Nd == pytest.approx(N_d)
    M_ndy, M_ndz = reduced_flexural_strength("rolled_I", 300.0 / N_d, result.Mdy, result.Mdz) # type: ignore[arg-type]
    alpha_1: float = max(5.0 * 300.0 / N_d, 1.0)
    assert result.utilisations["section (16.3.1.1)"] == pytest.approx((3.0 / M_ndy) ** alpha_1 + (60.0 / M_ndz) ** 2)
    section_only = check_compression_and_bending(ISMB_300, P_kN=300.0, Mz_kNm=60.0)
    assert list(section_only.utilisations) == ["section, conservative (16.3.1.1)", "section (16.3.1.1)"]
    assert any("KLy_mm" in note for note in section_only.metadata["notes"])
    axial_only = check_compression_and_bending(ISMB_300, P_kN=300.0)
    assert axial_only.utilisations["section (16.3.1.1)"] == pytest.approx(300.0 / N_d)
    channel = check_compression_and_bending(ISMC_200, P_kN=100.0, Mz_kNm=10.0)
    assert channel.method == "16.3.1.1 (conservative)" # no 16.3.1.2 approximation for channels


def test_section_class_input() -> None:
    assert _as_section_class("compact") == SectionClass.CLASS_2
    assert _as_section_class("Class 3") == SectionClass.CLASS_3
    assert _as_section_class(SectionClass.CLASS_1) == SectionClass.CLASS_1
    with pytest.raises(ValueError):
        _as_section_class("class 5")


# --- Other sections and paths ---
RHS_200_100_5 = {"D": 200.0, "B": 100.0, "t": 5.0, "A": 28.4, "I_zz": 1470.0, "I_yy": 497.0, "Z_zz": 147.0, "Z_yy": 99.4, "Z_pz": 181.0, "Z_py": 113.0}


def test_tension_of_a_channel_connected_by_its_web() -> None:
    # 13.3.4: ISMC 200 on a gusset through its web; the flanges are the outstanding elements
    beta: float = 1.4 - 0.076 * (75.0 / 11.4) * (250.0 / 410.0) * (110.0 / 200.0)
    result = check_tension(ISMC_200, Lc_mm=200.0, Ago_cm2=17.1, w_mm=75.0, t_mm=11.4, bs_mm=110.0)
    assert (result.method, result.beta) == ("13.3.4", pytest.approx(beta))
    assert result.Tdn == pytest.approx((0.9 * (2821.0 - 1710.0) * 410.0 / 1.25 + beta * 1710.0 * 250.0 / 1.1) / 1e3)
    with pytest.raises(ValueError, match="bs_mm"):
        check_tension(ISMC_200, Lc_mm=200.0, Ago_cm2=17.1, w_mm=75.0, t_mm=11.4)
    with pytest.raises(ValueError, match="Anc"):
        check_tension(ISMC_200, Lc_mm=200.0, Ago_cm2=30.0, w_mm=75.0, t_mm=11.4, bs_mm=110.0, An_cm2=28.0)


def test_hollow_sections_in_shear_bending_and_combined_forces() -> None:
    shear = check_shear(section_type=SectionType.HFRHS, properties=RHS_200_100_5, fy_mpa=250.0)
    assert shear.Av == pytest.approx(28.4 * 200.0 / 300.0) and shear.d_tw == pytest.approx(37.0) # webs D - 3t
    # high shear: Mfd = (Zp - Av D/4) fy/γm0
    V_d: float = shear.Vd
    bending = check_bending(section_type=SectionType.HFRHS, properties=RHS_200_100_5, fy_mpa=250.0, V_kN=0.8 * V_d)
    A_v: float = 2840.0 * 200.0 / 300.0
    assert bending.Mfd == pytest.approx((181.0 - A_v * 200.0 / 4.0 / 1e3) * 250.0 / 1.1 / 1e3)
    combined = check_compression_and_bending(section_type=SectionType.HFRHS, properties=RHS_200_100_5, fy_mpa=250.0, P_kN=200.0, Mz_kNm=20.0)
    n: float = 200.0 / (2840.0 * 250.0 / 1.1 / 1e3)
    M_ndz: float = reduced_flexural_strength("RHS", n, combined.Mdy or 0.0, combined.Mdz, 28.4, 100.0, 5.0, 200.0, 5.0)[1] # type: ignore[arg-type]
    exponent: float = interaction_exponents("RHS", n)[1]
    assert (combined.method, combined.Mndz, combined.alpha_2) == ("16.3.1.1", pytest.approx(M_ndz), pytest.approx(exponent))
    # CHS given with d, the outside diameter, and RHS sizes from the designation
    assert shear_area(section_type=SectionType.HFCHS, properties={"d": 219.1, "t": 5.0, "A": 33.6}) == pytest.approx(2.0 * 33.6 / math.pi)
    assert shear_area(section_type=SectionType.HFRHS, properties={"designation": "RHS 200x100x5", "t": 5.0, "A": 28.4}) == pytest.approx(28.4 * 200.0 / 300.0)


def test_bending_paths() -> None:
    # minor axis high shear: Av = 2b tf, Mfd from the web alone
    V_d: float = 3472.0 * 250.0 / ROOT3 / 1.1 / 1e3
    minor = check_bending(ISMB_300, axis="y", V_kN=350.0)
    M_d: float = 1.2 * 64.8 * 250.0 / 1.1 / 1e3
    M_fd: float = 275.2 * 7.5**2 / 4.0 / 1e3 * 250.0 / 1.1 / 1e3
    beta: float = (700.0 / V_d - 1.0) ** 2
    assert (minor.Mfd, minor.Md) == pytest.approx((M_fd, M_d - beta * (M_d - M_fd)))
    assert check_bending(ISMB_300, V_kN=250.0, Mfd_kNm=100.0).Mfd == 100.0
    # a deep thin web: d/tw = 960/8 = 120 > 67ε (15.2.1.1), semi-compact in bending
    girder = {"D": 1000.0, "B": 300.0, "t": 8.0, "T": 20.0, "R1": 0.0, "area": 196.8, "Z_zz": 6_900.0, "Z_pz": 7_700.0}
    deep = check_bending(section_type=SectionType.WPB, properties=girder, fy_mpa=250.0)
    assert deep.section_class == SectionClass.CLASS_3 and any("15.2.1.1" in note for note in deep.metadata["notes"])
    # an angle has no Zp: Ze for a compact section
    angle = check_bending(ISA_100_75_8, properties={"Z_zz": 19.0})
    assert (angle.modulus, angle.Md) == ("Ze", pytest.approx(19.0 * 250.0 / 1.1 / 1e3))
    compact = check_bending(ISA_100_75_8, section_class=1, properties={"Z_zz": 19.0}) # no Zp is tabulated for angles
    assert compact.modulus == "Ze" and any("conservative" in note for note in compact.metadata["notes"])
    long = check_lateral_torsional_buckling(ISMB_300, LLT_mm=9000.0)
    assert any("exceeds 300" in note for note in long.metadata["notes"]) # 9000/28.4 = 317


def test_compression_paths() -> None:
    # r from the tables (mm) where I is not given
    tabulated = {"D": 300.0, "B": 140.0, "t": 7.5, "T": 12.4, "area": 56.26, "r_y": 28.4, "r_z": 123.7}
    result = check_compression(section_type=SectionType.MWB, properties=tabulated, KLy_mm=2840.0)
    assert result.modes[0].KL_r == pytest.approx(100.0)
    assert check_compression(ISMB_300, KLy_mm=4000.0, section_class=3).section_class == SectionClass.CLASS_3
    slender = EqualAngle(designation="ISA 100x100x8", t=8.0, area=15.39, I_zz=145.0, I_yy=145.0, I_vy=59.9)
    assert any("Slender angle" in note for note in check_angle_strut(slender, L_mm=1000.0).metadata["notes"])
    with pytest.raises(ValueError, match="I_zz and I_yy"):
        check_angle_strut(EqualAngle(designation="ISA 100x100x8", t=8.0, area=15.39), L_mm=1000.0)
    with pytest.raises(ValueError, match="negative"):
        non_dimensional_slenderness(-1.0, 250.0)
    with pytest.raises(ValueError, match="Unknown buckling class"):
        design_compressive_stress(100.0, 250.0, "e")
    with pytest.raises(ValueError, match="Table 1"):
        check_compression(properties={"area": 50.0}, KLy_mm=1000.0)
    with pytest.raises(ValueError, match="to classify"):
        check_compression(properties={"area": 50.0, "t": 8.0}, KLy_mm=1000.0)
