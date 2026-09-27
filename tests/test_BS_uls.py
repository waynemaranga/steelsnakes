"""BS 5950-1:2000 ultimate limit states; formulas against the code's own tables (Tables 4, 16, 17, 20, 21 and 24) and hand
calculations on UK sections (UB 457x191x67 and UC 254x254x73 in S275 unless stated)."""

import math

import pytest

from steelsnakes.base.checks import LimitState, SectionClass
from steelsnakes.base.sections import SectionType
from steelsnakes.BS import CFCHS, CFSHS, HFCHS, HFRHS, HFSHS, L_EQUAL, L_EQUAL_B2B, L_UNEQUAL, PFC, UB, UC
from steelsnakes.BS.checks.uls import (
    _as_section_class,
    amplification_factor,
    amplified_moment,
    angle_buckling_resistance_moment,
    angle_equivalent_slenderness,
    beam_effective_length,
    bending_strength,
    box_equivalent_slenderness,
    buckling_parameter,
    cantilever_effective_length,
    channel_slenderness,
    charpy_temperature,
    check_angle_strut,
    check_bending,
    check_brittle_fracture,
    check_compression,
    check_compression_and_bending,
    check_lateral_torsional_buckling,
    check_shear,
    check_simple_column,
    check_single_angle_compression_and_bending,
    check_sway_stability,
    check_tension,
    check_tension_and_bending,
    check_web_bearing,
    chs_effective_ratios,
    compressive_strength,
    critical_shear_strength,
    double_angle_slenderness,
    effective_length,
    effective_net_area,
    effective_net_area_coefficient,
    effective_section,
    elastic_critical_load_factor,
    elastic_shear_stress_limit,
    equivalent_slenderness,
    equivalent_uniform_moment_factor_m,
    equivalent_uniform_moment_factor_mLT,
    factored_load,
    internal_moment_at,
    lateral_restraint_forces,
    lateral_torsional_internal_moment,
    limiting_equivalent_slenderness,
    limiting_slenderness,
    limiting_thickness,
    load_factor,
    minimum_horizontal_wind_load,
    monosymmetry_index,
    net_area,
    notched_end_moment_capacity,
    notional_horizontal_force,
    plate_equivalent_slenderness,
    reduced_design_strength,
    reduced_plastic_moduli,
    restraint_reduction_factor,
    rhs_limiting_slenderness,
    rhs_torsion_constant,
    segment_effective_length,
    shear_area,
    shear_buckling_strength,
    simple_column_eccentricity,
    single_angle_slenderness,
    slender_web_effective_width,
    slenderness_factor,
    strut_action_moment,
    strut_curve,
    tee_slenderness,
    tension_flange_holes_negligible,
    tie_force,
    torsional_index,
)

EPS_355 = math.sqrt(275.0 / 355.0)


# --- 2.4.1 Table 2 and load combinations ---
def test_load_factors_and_combinations() -> None:
    assert load_factor("imposed") == 1.6
    assert load_factor("wind_with_imposed") == 1.2
    with pytest.raises(ValueError, match="Unknown load"):
        load_factor("snow")
    assert factored_load(1, dead=10.0, imposed=5.0).factored == pytest.approx(1.4 * 10 + 1.6 * 5)
    assert factored_load(2, dead=10.0, wind=-8.0, dead_counteracts=True).factored == pytest.approx(10.0 - 1.4 * 8) # uplift
    assert factored_load(3, dead=10.0, imposed=5.0, wind=4.0).factored == pytest.approx(1.2 * 19.0)
    with pytest.raises(ValueError, match="1, 2 or 3"):
        factored_load(4) # type: ignore[arg-type]


# --- 2.4.2 Stability ---
def test_notional_forces_and_sway_stability() -> None:
    assert notional_horizontal_force(2000.0) == pytest.approx(10.0) # 0.5 %
    assert minimum_horizontal_wind_load(-3000.0) == pytest.approx(30.0) # 1.0 %
    assert elastic_critical_load_factor(3500.0, 3.0) == pytest.approx(3500.0 / 600.0)
    # λcr = 5.83: clad λ/(1.15λ - 1.5) = 1.120; unclad λ/(λ - 1) = 1.207
    frame = check_sway_stability([4000.0, 3500.0], [2.0, 3.0])
    assert (frame.lambda_cr, frame.governing_storey, frame.non_sway) == (pytest.approx(5.8333, rel=1e-4), 1, False)
    assert frame.k_amp == pytest.approx(5.8333 / (1.15 * 5.8333 - 1.5), rel=1e-4)
    assert check_sway_stability([3500.0], [3.0], clad=False).k_amp == pytest.approx(5.8333 / 4.8333, rel=1e-4)
    assert check_sway_stability([4000.0], [1.0]).non_sway and check_sway_stability([4000.0], [1.0]).k_amp == 1.0 # λcr = 20
    assert not check_sway_stability([4000.0], [1.0], stiffening_taken_into_account=True).non_sway
    assert amplification_factor(40.0) == 1.0 # λ/(1.15λ - 1.5) < 1
    weak = check_sway_stability([3000.0], [5.0]) # λcr = 3
    assert weak.second_order_required and weak.k_amp is None
    with pytest.raises(ValueError, match="second-order"):
        amplification_factor(3.0)
    with pytest.raises(ValueError, match="one deflection"):
        check_sway_stability([3000.0], [])


def test_restraint_forces() -> None:
    assert restraint_reduction_factor(1) == 1.0
    assert restraint_reduction_factor(4) == pytest.approx(math.sqrt(0.45))
    with pytest.raises(ValueError):
        restraint_reduction_factor(0)
    # 2.5 % of 400 kN = 10 kN, shared in proportion to spacing; with 3 restraints each >= 1 % = 4 kN
    assert lateral_restraint_forces(400.0, [2000.0, 2000.0]) == pytest.approx([5.0, 5.0])
    assert lateral_restraint_forces(400.0, [1000.0, 1000.0, 2000.0]) == pytest.approx([4.0, 4.0, 5.0])
    assert lateral_restraint_forces(400.0, [4000.0, 4000.0], torsional=True) == pytest.approx([5.0, 5.0])
    assert lateral_restraint_forces(400.0, [7000.0, 1000.0], torsional=True) == pytest.approx([8.75, 4.0])
    with pytest.raises(ValueError):
        lateral_restraint_forces(400.0, [])


# --- 2.4.4 Brittle fracture: Table 4 values from the formula ---
@pytest.mark.parametrize(
    ("grade", "T_min", "t1"),
    [
        ("S275JR", -5.0, 30.0), # T27J > Tmin + 20: the (35 + Tmin - T27J)/15 branch
        ("S275J0", -15.0, 54.0),
        ("S355J2", -15.0, 55.0),
        ("S355J2", -45.0, 21.0),
        ("S355K2", -5.0, 79.0),
        ("S275NL", -45.0, 78.0),
        ("S355ML", -25.0, 79.0),
        ("S460Q", -45.0, 15.0),
        ("S355J2H", -35.0, 38.0), # Table 5
    ],
)
def test_limiting_thickness_table_4(grade: str, T_min: float, t1: float) -> None:
    Y_nom = float(grade[1:4])
    assert limiting_thickness(T_min, charpy_temperature(grade), Y_nom) == pytest.approx(t1, abs=0.6)


def test_check_brittle_fracture() -> None:
    welded = check_brittle_fracture(40.0, "S355J2", T_min=-15.0)
    assert (welded.K, welded.utilisation.adequacy) == (1.0, "OK") # 40 <= 1 x 54.8
    cover_plate = check_brittle_fracture(40.0, "S355J2", T_min=-15.0, detail="cover_plate_ends")
    assert cover_plate.K == 0.5 and cover_plate.utilisation.adequacy == "FAILS"
    assert check_brittle_fracture(20.0, "S275J0", detail="plain", stress="no_tension", plastic_deformation=True).K == 2.0
    assert check_brittle_fracture(30.0, None, T27J=0.0, Y_nom=275.0, K=1.0, t2=25.0).t_max == 25.0
    with pytest.raises(ValueError, match="Table 7"):
        charpy_temperature("S355")
    with pytest.raises(ValueError, match="detail"):
        check_brittle_fracture(10.0, detail="riveted")
    with pytest.raises(ValueError, match="T27J"):
        check_brittle_fracture(10.0, None)


def test_tie_force() -> None:
    # 2.4.5.3 a): internal 0.5(1.4 x 4 + 1.6 x 5)(6 m)(9 m) = 367.2 kN; edge 183.6 kN; at least 75 kN
    assert tie_force(4.0, 5.0, 6000.0, 9000.0) == pytest.approx(367.2)
    assert tie_force(4.0, 5.0, 6000.0, 9000.0, edge=True) == pytest.approx(183.6)
    assert tie_force() == 75.0
    assert tie_force(column_load=9000.0) == pytest.approx(90.0) # 2.4.5.3 b): 1 % of the column load


# --- 3.4 Net areas ---
def test_net_area_figure_3_and_effective_net_area() -> None:
    # 200 x 10 plate, 22 mm holes: line A t(b - 2D) = 15.6 cm²; line B t(b - 3D + 0.25s²/g) with s = 50, g = 60
    assert net_area(20.0, 10.0, 22.0, n_holes=2) == pytest.approx(15.6)
    assert net_area(20.0, 10.0, 22.0, n_holes=2, staggers=[(50.0, 60.0), (0.0, 60.0)]) == pytest.approx(20.0 - (66.0 - 0.25 * 2500.0 / 60.0) / 10.0)
    assert net_area(20.0, 10.0, 22.0, n_holes=2, staggers=[(200.0, 60.0)]) == pytest.approx(15.6) # a wide stagger does not govern
    with pytest.raises(ValueError, match="positive"):
        net_area(1.0, 10.0, 22.0, n_holes=1)
    with pytest.raises(ValueError, match="negative"):
        net_area(20.0, 10.0, 22.0, n_holes=-1)
    assert effective_net_area_coefficient("S275") == 1.2
    assert effective_net_area_coefficient("s355 j2") == 1.1
    assert effective_net_area_coefficient("S460") == 1.0
    assert effective_net_area_coefficient("S420", py=420.0, Us=520.0) == pytest.approx(520.0 / 1.2 / 420.0)
    with pytest.raises(ValueError, match="Us"):
        effective_net_area_coefficient("S420")
    assert effective_net_area(10.0, 11.0, 1.2) == 11.0 # ae <= ag
    assert effective_net_area(8.0, 11.0, 1.2) == pytest.approx(9.6)
    assert tension_flange_holes_negligible(10.0, 8.4, 1.2) and not tension_flange_holes_negligible(10.0, 8.0, 1.2)


# --- 3.6 Slender cross-sections ---
def test_effective_section_hot_finished_shs() -> None:
    # SHS 300x300x6.3 S275: b/t = (300 - 3 x 6.3)/6.3 = 44.62 > 40ε, so each wall keeps 40εt = 252 mm of its 281.1 mm
    shs = HFSHS("300x300x6.3")
    area = effective_section(shs)
    assert area.method == "3.6.2.2" and area.slender_elements == ["flange_wall", "web_wall"]
    assert area.A_eff == pytest.approx(73.6 - 4 * 6.3 * (281.1 - 252.0) / 100.0)
    # Zeff: the non-effective 29.1 mm strip of the compression flange, 146.85 mm from the centroid, is removed
    modulus = effective_section(shs, stress_pattern="bending-major-axis")
    strip, y, own = 29.1 * 6.3 / 100.0, 14.685, 29.1 * 6.3**3 / 12.0 / 1e4
    e = strip * y / (73.6 - strip)
    I_eff = 10500.0 - strip * y**2 - own - (73.6 - strip) * e**2
    assert modulus.method == "3.6.2.3" and modulus.Z_eff == pytest.approx(I_eff / (15.0 + e))
    reduced = effective_section(shs, method="reduced_strength")
    assert reduced.method == "3.6.5" and reduced.py_r == pytest.approx((40.0 / (281.1 / 6.3)) ** 2 * 275.0)
    with pytest.raises(ValueError, match="compression"):
        effective_section(shs, stress_pattern="combined")


def test_effective_section_i_chs_angle_and_fallbacks() -> None:
    # UB 457x191x67 web in axial compression with r2 = 1: 20εt either side, Aeff = 85.5 - 8.5(407.6 - 340)/100
    assert effective_section(UB("457x191x67")).A_eff == pytest.approx(85.5 - 8.5 * 67.6 / 100.0)
    assert effective_section(UB("457x191x67"), Fc_kN=500.0).method == "not slender" # r2 = 0.21 raises the limit
    assert effective_section(UB("457x191x67"), stress_pattern="bending-major-axis").Z_eff == 1300.0
    # CHS 508x6 S355: D/t = 84.7 > 80ε²; Aeff/A = (80/(D/t) x 275/355)^0.5 = 0.8555
    chs = effective_section(CFCHS("508.0x6.0"), steel_grade="S355")
    assert chs.method == "3.6.6" and chs.A_eff / chs.A == pytest.approx(math.sqrt(80.0 / (508.0 / 6.0) * 275.0 / 355.0))
    assert chs_effective_ratios(100.0, 275.0) == pytest.approx((math.sqrt(0.8), 1.0))
    with pytest.raises(ValueError, match="240"):
        chs_effective_ratios(200.0, 355.0)
    # 3.6.4 equal angle in S460 (py = 460 at 16 mm): b/t = 200/16 = 12.5 > 12ε = 9.28
    angle = effective_section(L_EQUAL("200x200x16.0"), steel_grade="S460")
    assert angle.method == "3.6.4" and angle.A_eff / angle.A == pytest.approx(12.0 * math.sqrt(275.0 / 460.0) / 12.5)
    # Unequal angles have no effective-width rule here: 3.6.5 over every failing criterion
    unequal = effective_section(L_UNEQUAL("200x100x10"), steel_grade="S355")
    assert unequal.method == "3.6.5" and unequal.metadata["notes"]
    assert unequal.py_r == pytest.approx(355.0 * min((15.0 * EPS_355 / 20.0) ** 2, (24.0 * EPS_355 / 30.0) ** 2))
    assert reduced_design_strength(355.0, 30.0, 40.0) == pytest.approx(355.0 * 0.5625)
    # 3.6.2.4: 120εt/[(1 + (fcw - ftw)/pyw)(1 + ftw/fcw)] = 60εt for a symmetric web at py
    assert slender_web_effective_width(275.0, 275.0, 275.0, 10.0) == pytest.approx(600.0)


# --- 4.2 Bending: shear and moment capacity ---
def test_shear_capacity_and_areas() -> None:
    beam = UB("457x191x67")
    result = check_shear(beam, Fv_kN=500.0) # Pv = 0.6 x 275 x 8.5 x 453.4 = 635.9 kN
    assert result.Pv == pytest.approx(0.6 * 275.0 * 8.5 * 453.4 / 1e3)
    assert (result.high_shear, result.shear_buckling, result.utilisation.adequacy) == (True, False, "OK")
    assert result.rho == pytest.approx((2 * 500.0 / result.Pv - 1.0) ** 2)
    assert check_shear(beam, Fv_kN=300.0).rho == 0.0 # Fv <= 0.6Pv
    assert shear_area(beam, direction="flanges") == pytest.approx(0.9 * 2 * 189.9 * 12.7 / 100.0)
    assert shear_area(beam, welded=True) == pytest.approx(8.5 * 407.6 / 100.0)
    rhs = HFRHS("200x100x5.0")
    assert shear_area(rhs) == pytest.approx(28.7 * 200.0 / 300.0)
    assert shear_area(rhs, direction="flanges") == pytest.approx(28.7 * 100.0 / 300.0)
    assert shear_area(HFCHS("219.1x5.0")) == pytest.approx(0.6 * 33.6)
    assert shear_area(L_EQUAL("80x80x8.0")) == pytest.approx(0.9 * 80.0 * 8.0 / 100.0)
    assert check_shear(beam, Av_cm2=10.0).Pv == pytest.approx(0.6 * 275.0 * 10.0 / 10.0)
    assert elastic_shear_stress_limit(275.0) == pytest.approx(192.5)
    with pytest.raises(NotImplementedError):
        shear_area(section_type=SectionType.HFEHS, properties={"A": 10.0})


@pytest.mark.parametrize(("d_t", "a_d", "qw"), [(60.0, math.inf, 165.0), (70.0, math.inf, 155.0), (100.0, 1.0, 147.0), (85.0, 1.0, 162.0), (130.0, 0.6, 156.0), (120.0, 2.0, 105.0), (110.0, 1.4, 124.0), (120.0, math.inf, 96.0)])
def test_shear_buckling_strength_table_21(d_t: float, a_d: float, qw: float) -> None:
    # Table 21 (S275, py 275) is H.1 for welded webs
    assert shear_buckling_strength(d_t, 275.0, a_d, welded=True) == pytest.approx(qw, abs=0.6)


def test_shear_buckling_of_a_welded_plate_girder() -> None:
    # Web 960 x 8, py 275: d/t = 120 > 62ε; qw = 0.9pv/λw, λw = (165/(1000/120)²)^0.5 = 1.54 -> 96.3 N/mm²
    girder = {"D": 1000.0, "d": 960.0, "t": 8.0, "B": 300.0, "T": 20.0, "A": 196.8}
    result = check_shear(py_mpa=275.0, Fv_kN=600.0, welded=True, properties=girder)
    q_w = 0.9 * 165.0 / math.sqrt(165.0 / (1000.0 / 120.0) ** 2)
    assert result.shear_buckling and result.qw == pytest.approx(q_w)
    assert result.Vw == pytest.approx(960.0 * 8.0 * q_w / 1e3) and result.capacity == result.Vw
    assert result.Pv == pytest.approx(0.6 * 275.0 * 76.8 / 10.0)
    assert result.Vcr == pytest.approx((result.Vw / 0.9) ** 2 / result.Pv) # 4.4.5.4, Vw <= 0.72Pv
    stiffened = check_shear(py_mpa=275.0, welded=True, a_mm=960.0, properties=girder) # a/d = 1
    assert stiffened.qw == pytest.approx(shear_buckling_strength(120.0, 275.0, 1.0, welded=True))
    assert shear_buckling_strength(70.0, 275.0) == 165.0 # rolled, λw = 0.899 <= 0.9
    assert shear_buckling_strength(120.0, 275.0) == pytest.approx(q_w) # rolled and welded coincide above λw = 1.25
    # H.2: qcr = pv/λw² for λw >= 1.25, and the intermediate branches
    assert critical_shear_strength(120.0, 275.0) == pytest.approx(165.0 * (1000.0 / 120.0) ** 2 / 165.0)
    assert critical_shear_strength(70.0, 275.0) == 165.0
    assert critical_shear_strength(90.0, 275.0) == pytest.approx((8.1 / 1.1560 - 2.0) / 7.0 * 165.0, rel=1e-3) # λw = 1.156
    assert critical_shear_strength(90.0, 275.0, welded=True) == pytest.approx((1.64 - 0.8 * 1.1560) * 165.0, rel=1e-3)
    assert critical_shear_strength(60.0, 275.0, welded=True) == 165.0
    # RHS webs are checked with H.1 as well
    assert check_shear(CFSHS("400x400x6.0"), steel_grade="S460").shear_buckling # d/t = (400 - 5 x 6)/6 = 61.7 > 70ε = 54.1


def test_moment_capacity_low_and_high_shear() -> None:
    beam = UB("457x191x67")
    low = check_bending(beam, M_kNm=300.0, Fv_kN=250.0)
    assert (low.Mc, low.modulus, low.high_shear) == (pytest.approx(275.0 * 1470.0 / 1e3), "S", False) # 404.25 kNm
    assert low.Mc_limit == pytest.approx(1.2 * 275.0 * 1300.0 / 1e3)
    # 4.2.5.3: Fv = 500 > 0.6Pv; Sv = tD²/4 = 436.8 cm³; Mc = py(S - ρSv)
    high = check_bending(beam, Fv_kN=500.0)
    rho = (2 * 500.0 / (0.6 * 275.0 * 8.5 * 453.4 / 1e3) - 1.0) ** 2
    assert high.Sv == pytest.approx(8.5 * 453.4**2 / 4 / 1e3)
    assert high.Mc == pytest.approx(275.0 * (1470.0 - rho * high.Sv) / 1e3)
    # 4.2.5.1: the minor axis of a UC is limited by 1.2pyZ (simple spans) or 1.5pyZ
    column = UC("254x254x73")
    assert check_bending(column, axis="y").Mc == pytest.approx(1.2 * 275.0 * 307.0 / 1e3)
    assert check_bending(column, axis="y", simple_span=False).Mc == pytest.approx(1.5 * 275.0 * 307.0 / 1e3) # Sy/Zy = 1.515 > 1.5
    assert check_bending(column, axis="y", Fv_kN=1000.0).Sv == pytest.approx(0.9 * 2 * 14.2 * 254.6**2 / 4 / 1e3)
    with pytest.raises(ValueError, match="axis"):
        check_bending(beam, axis="z") # type: ignore[arg-type]


def test_moment_capacity_semi_compact_slender_and_hollow() -> None:
    # Class 3 CHS 219.1x5.0 S355: Seff (3.5.6.4) = 221.1 cm³
    chs = check_bending(HFCHS("219.1x5.0"), steel_grade="S355", simple_span=False)
    assert (chs.section_class, chs.modulus) == (SectionClass.CLASS_3, "Seff")
    assert chs.Mc == pytest.approx(355.0 * 221.1126 / 1e3, rel=1e-5)
    assert check_bending(HFCHS("219.1x5.0"), steel_grade="S355").Mc == pytest.approx(1.2 * 355.0 * 176.0 / 1e3) # 4.2.5.1 governs
    assert check_bending(HFCHS("219.1x5.0"), steel_grade="S355", use_Seff=False).modulus == "Z"
    assert check_bending(HFCHS("219.1x5.0"), steel_grade="S355", Fv_kN=500.0).Sv == pytest.approx(4 * ((219.1 - 5.0) / 2) ** 2 * 5.0 * (1 - math.cos(0.3 * math.pi)) / 1e3)
    # Class 4 SHS: pyZeff, or pyr Z with 3.6.5; high shear takes ρSv/1.5
    shs = HFSHS("300x300x6.3")
    slender = check_bending(shs, M_kNm=150.0)
    zeff = effective_section(shs, stress_pattern="bending-major-axis").Z_eff
    assert (slender.section_class, slender.modulus, slender.Mc) == (SectionClass.CLASS_4, "Zeff", pytest.approx(275.0 * zeff / 1e3))
    reduced = check_bending(shs, class_4_method="reduced_strength")
    assert reduced.py == pytest.approx((40.0 / (281.1 / 6.3)) ** 2 * 275.0) and reduced.modulus == "Z"
    sheared = check_bending(shs, Fv_kN=600.0)
    A_v = 73.6 * 0.5
    rho = (2 * 600.0 / (0.6 * 275.0 * A_v / 10.0) - 1.0) ** 2
    assert sheared.Mc == pytest.approx(275.0 * (zeff - rho * A_v * 30.0 / 4.0 / 1.5) / 1e3)
    assert check_bending(shs, Z_eff_cm3=600.0).Mc == pytest.approx(275.0 * 0.6)
    # Class 1 and 2 angles have no tabulated S
    assert check_bending(L_EQUAL("80x80x8.0")).metadata["notes"]
    # A user class of 3 on a class 4 section falls back to Z
    assert check_bending(shs, section_class=3).modulus == "Z"


def test_notched_ends() -> None:
    assert notched_end_moment_capacity(275.0, "single", Z=100.0) == pytest.approx(27.5)
    assert notched_end_moment_capacity(275.0, "single", Z=100.0, F_v=90.0, P_v=100.0) == pytest.approx(1.5 * 27.5 * (1 - 0.81))
    assert notched_end_moment_capacity(275.0, "double", t=8.0, d=300.0) == pytest.approx(275.0 * 8.0 * 300.0**2 / 6.0 / 1e6)
    assert notched_end_moment_capacity(275.0, "double", t=8.0, d=300.0, F_v=90.0, P_v=100.0) == pytest.approx(275.0 * 8.0 * 300.0**2 / 4.0 * 0.19 / 1e6)


# --- 4.3 Lateral-torsional buckling ---
def test_effective_lengths_tables_13_and_14() -> None:
    assert beam_effective_length(6000.0, "both_flanges_fully_restrained") == pytest.approx(4200.0)
    assert beam_effective_length(6000.0, "compression_flange_partially_restrained", "destabilizing") == pytest.approx(6000.0)
    assert beam_effective_length(6000.0, "bottom_flange_bearing", "destabilizing", D=500.0) == pytest.approx(1.4 * 6000.0 + 1000.0)
    with pytest.raises(ValueError, match="restraint"):
        beam_effective_length(6000.0, "free")
    assert segment_effective_length(2000.0, "destabilizing") == pytest.approx(2400.0)
    assert segment_effective_length(2000.0, support_restraint="both_flanges_fully_restrained") == pytest.approx(0.5 * (2000.0 + 1400.0))
    assert cantilever_effective_length(3000.0, "continuous_lateral", "free", "destabilizing") == pytest.approx(22500.0)
    assert cantilever_effective_length(3000.0, "built_in", "lateral_torsional") == pytest.approx(1500.0)
    assert cantilever_effective_length(3000.0, "built_in", "free", tip_moment=True) == pytest.approx(max(1.3 * 2400.0, 2400.0 + 900.0))
    with pytest.raises(ValueError, match="support"):
        cantilever_effective_length(3000.0, "fixed")


@pytest.mark.parametrize(("beta", "mLT", "m"), [(1.0, 1.0, 1.0), (0.5, 0.8, 0.8), (0.0, 0.6, 0.6), (-0.1, 0.56, 0.58), (-0.3, 0.48, 0.54), (-0.4, 0.46, 0.52), (-0.6, 0.44, 0.48), (-1.0, 0.44, 0.40)])
def test_equivalent_uniform_moment_factors_tables_18_and_26(beta: float, mLT: float, m: float) -> None:
    # the tables round half up, e.g 0.455 -> 0.46
    assert equivalent_uniform_moment_factor_mLT(beta) == pytest.approx(mLT, abs=0.0051)
    assert equivalent_uniform_moment_factor_m(beta) == pytest.approx(m, abs=0.0051)


def test_equivalent_uniform_moment_factor_specific_cases() -> None:
    # Uniform load, M2 = M4 = 0.75Mmax: mLT = 0.925, m = 0.95; central point load, M2 = M4 = 0.5Mmax: 0.850 and 0.90
    assert equivalent_uniform_moment_factor_mLT(M2=0.75, M3=1.0, M4=0.75, M_max=1.0) == pytest.approx(0.925)
    assert equivalent_uniform_moment_factor_mLT(M2=0.5, M3=1.0, M4=0.5, M_max=1.0) == pytest.approx(0.85)
    assert equivalent_uniform_moment_factor_m(M2=0.75, M3=1.0, M4=0.75, M_max=1.0) == pytest.approx(0.95)
    assert equivalent_uniform_moment_factor_m(M2=0.5, M3=1.0, M4=0.5, M_max=1.0) == pytest.approx(0.90)
    assert equivalent_uniform_moment_factor_m(M2=-0.5, M3=-1.0, M4=-0.5, M_max=1.0) == pytest.approx(0.90) # the other side
    assert equivalent_uniform_moment_factor_mLT(0.5, cantilever=True) == 1.0
    assert equivalent_uniform_moment_factor_mLT(0.5, loading="destabilizing") == 1.0
    with pytest.raises(ValueError, match="beta"):
        equivalent_uniform_moment_factor_mLT()
    with pytest.raises(ValueError, match="beta"):
        equivalent_uniform_moment_factor_m()
    with pytest.raises(ValueError, match="between"):
        equivalent_uniform_moment_factor_m(1.5)


@pytest.mark.parametrize(
    ("lambda_LT", "py", "welded", "pb"),
    [
        (30.0, 275.0, False, 275.0), (40.0, 275.0, False, 262.0), (60.0, 275.0, False, 213.0), (100.0, 275.0, False, 125.0), (150.0, 275.0, False, 67.0),
        (40.0, 355.0, False, 325.0), (60.0, 355.0, False, 257.0), (100.0, 355.0, False, 139.0),
        (40.0, 460.0, False, 404.0), (60.0, 460.0, False, 304.0), (100.0, 460.0, False, 151.0), (150.0, 460.0, False, 75.0),
        (40.0, 275.0, True, 250.0), (60.0, 275.0, True, 180.0), (100.0, 275.0, True, 123.0), (115.0, 275.0, True, 102.0),
        (40.0, 355.0, True, 301.0), (60.0, 355.0, True, 212.0), (80.0, 355.0, True, 179.0), (60.0, 460.0, True, 269.0),
    ],
)
def test_bending_strength_tables_16_and_17(lambda_LT: float, py: float, welded: bool, pb: float) -> None:
    assert bending_strength(lambda_LT, py, welded) == pytest.approx(pb, abs=0.6)


def test_limiting_slenderness_rows_of_tables_16_and_17() -> None:
    for py, lambda_L0 in ((235.0, 37.1), (275.0, 34.3), (355.0, 30.2), (460.0, 26.5)):
        assert limiting_equivalent_slenderness(py) == pytest.approx(lambda_L0, abs=0.06)
    with pytest.raises(ValueError, match="negative"):
        bending_strength(-1.0, 275.0)


@pytest.mark.parametrize(("slenderness", "D_T", "pb"), [(60.0, 10.0, 258.0), (90.0, 20.0, 193.0), (120.0, 50.0, 123.0), (45.0, 15.0, 269.0), (100.0, 5.0, 257.0)])
def test_table_20_is_u_0_9_and_x_D_over_T(slenderness: float, D_T: float, pb: float) -> None:
    lambda_LT = equivalent_slenderness(0.9, slenderness_factor(slenderness / D_T), slenderness)
    assert bending_strength(lambda_LT, 275.0) == pytest.approx(pb, abs=0.6)


def test_buckling_parameter_and_torsional_index_b_2_3() -> None:
    # UB 457x191x67: hs = D - T = 440.7 mm; the tables give u = 0.872, x = 37.9
    beam = UB("457x191x67")
    assert buckling_parameter(Sx=1470.0, A=85.5, Ix=29400.0, Iy=1450.0, h_s=440.7) == pytest.approx(0.872, abs=0.002)
    assert torsional_index(A=85.5, J=37.1, h_s=440.7) == pytest.approx(37.9, abs=0.05)
    assert beam.get_properties()["U"] == 0.872
    # PFC 300x100x46: channel formulae against the tabulated U and X
    channel = PFC("300x100x46").get_properties()
    u = buckling_parameter(Sx=channel["W_pl_yy"], A=channel["A"], Ix=channel["I_yy"], Iy=channel["I_zz"], H=channel["I_w"])
    x = torsional_index(A=channel["A"], J=channel["I_t"], H=channel["I_w"], Iy=channel["I_zz"])
    assert (u, x) == (pytest.approx(channel["U"], rel=0.01), pytest.approx(channel["X"], rel=0.01))


def test_slenderness_factor_and_monosymmetry() -> None:
    assert slenderness_factor(0.0) == 1.0
    assert slenderness_factor(3.0) == pytest.approx((1 + 0.05 * 9) ** -0.25) # Table 19, equal flanges
    assert slenderness_factor(3.0, 0.8, monosymmetry_index(0.8)) < slenderness_factor(3.0) # larger flange in compression
    assert monosymmetry_index(0.8) == pytest.approx(0.8 * 0.6)
    assert monosymmetry_index(0.3, D_L_over_D=0.2) == pytest.approx(1.0 * -0.4 * 1.1)
    with pytest.raises(ValueError, match="0.1"):
        monosymmetry_index(0.95)


def test_lateral_torsional_buckling_universal_beam() -> None:
    # UB 457x191x67, LE = 4.0 m: λ = 4000/41.2 = 97.09, λ/x = 2.562, v = 0.9315, λLT = 0.872 x 0.9315 x 97.09 = 78.86;
    # Table 16 between 75 (176) and 80 (165): pb = 167.5; Mb = pbSx
    beam = UB("457x191x67")
    result = check_lateral_torsional_buckling(beam, LE_mm=4000.0, Mx_kNm=200.0, mLT=0.925)
    assert result.lambda_LT == pytest.approx(0.872 * 0.93152 * 4000.0 / 41.2, rel=1e-4)
    assert result.pb == pytest.approx(176.0 - (result.lambda_LT - 75.0) / 5.0 * 11.0, abs=0.6)
    assert result.Mb == pytest.approx(result.pb * 1470.0 / 1e3)
    assert result.governing == "mLT Mx/Mb (4.3.6.2)" and result.utilisation.utilisation == pytest.approx(0.925 * 200.0 / result.Mb)
    assert result.limit_state == LimitState.LATERAL_TORSIONAL_BUCKLING
    # 4.3.7 simple method, x = D/T = 35.7 and u = 0.9: Table 20 at (97.1, 35.7) interpolates to 163.2
    simple = check_lateral_torsional_buckling(beam, LE_mm=4000.0, approximate=True)
    assert simple.method == "4.3.7" and simple.pb == pytest.approx(163.2, abs=0.6)
    # Destabilizing loading takes mLT = 1.0; a short segment has pb = py
    assert check_lateral_torsional_buckling(beam, LE_mm=4000.0, mLT=0.6, loading="destabilizing").mLT == 1.0
    stocky = check_lateral_torsional_buckling(beam, LE_mm=1000.0)
    assert stocky.pb == 275.0 and stocky.Mb == pytest.approx(404.25)
    # u and x from B.2.3 when not tabulated, and the 4.3.6.8 approximations when they cannot be computed
    props = {key: value for key, value in beam.get_properties().items() if key not in ("U", "X")}
    computed = check_lateral_torsional_buckling(section_type=SectionType.UB, LE_mm=4000.0, properties=props)
    assert computed.u == pytest.approx(0.872, abs=0.002) and computed.x == pytest.approx(37.9, abs=0.05)
    fallback = check_lateral_torsional_buckling(section_type=SectionType.UB, LE_mm=4000.0, properties={**props, "I_t": 0.0})
    assert (fallback.u, fallback.x) == (0.9, pytest.approx(453.4 / 12.7)) and fallback.metadata["notes"]
    assert check_lateral_torsional_buckling(beam, LE_mm=4000.0, u=0.9, x=30.0, welded=True).u == 0.9


def test_lateral_torsional_buckling_channel_semi_compact_and_hollow() -> None:
    channel = check_lateral_torsional_buckling(PFC("300x100x46"), LE_mm=3000.0)
    assert (channel.u, channel.x) == (0.944, 17.0)
    assert channel.lambda_LT == pytest.approx(0.944 * slenderness_factor(channel.slenderness / 17.0) * channel.slenderness)
    # Class 3: βW = Sx,eff/Sx (or Zx/Sx) and Mb = pbSx,eff
    semi = check_lateral_torsional_buckling(UC("152x152x23"), steel_grade="S355", LE_mm=3000.0)
    assert semi.section_class == SectionClass.CLASS_3 and semi.modulus == "Seff"
    assert semi.beta_W == pytest.approx(semi.W / 182.0) and semi.Mb == pytest.approx(semi.pb * semi.W / 1e3)
    assert check_lateral_torsional_buckling(UC("152x152x23"), steel_grade="S355", LE_mm=3000.0, use_Seff=False).beta_W == pytest.approx(164.0 / 182.0)
    # CHS and SHS are not susceptible; RHS only beyond Table 15
    assert not check_lateral_torsional_buckling(HFCHS("219.1x5.0"), LE_mm=9000.0).susceptible
    assert not check_lateral_torsional_buckling(HFSHS("300x300x6.3"), LE_mm=9000.0).susceptible
    rhs = HFRHS("400x200x10.0") # D/B = 2.0: LE/ry <= 340
    assert not check_lateral_torsional_buckling(rhs, LE_mm=12000.0).susceptible
    long = check_lateral_torsional_buckling(rhs, LE_mm=40000.0)
    p = rhs.get_properties()
    lambda_LT = box_equivalent_slenderness(p["W_pl_yy"], p["A"], p["I_t"], p["I_yy"], p["I_zz"], 40000.0 / (p["i_zz"] * 10.0))
    assert long.method == "B.2.6" and long.lambda_LT == pytest.approx(lambda_LT)
    assert rhs_limiting_slenderness(1.0, 275.0) == math.inf
    assert rhs_limiting_slenderness(1.2, 275.0) == 770.0
    assert rhs_limiting_slenderness(1.6, 355.0) == pytest.approx(435.0 * 275.0 / 355.0) # the next higher D/B row
    assert rhs_limiting_slenderness(5.0, 275.0) is None
    assert rhs_torsion_constant(200.0, 100.0, 5.0) == pytest.approx(p_rhs_J := 1.0e-4 * (4 * (195.0 * 95.0) ** 2 * 5.0 / 580.0 + 580.0 * 125.0 / 3.0))
    assert p_rhs_J == pytest.approx(HFRHS("200x100x5.0").get_properties()["I_t"], rel=0.05)


def test_lateral_torsional_buckling_angles_and_plates() -> None:
    # 4.3.8.3 L 80x80x8, LE = 2 m, rv = 1.56 cm: heel in tension pyZx(1350ε - LE/rv)/(1625ε)
    angle = L_EQUAL("80x80x8.0")
    tension = check_lateral_torsional_buckling(angle, LE_mm=2000.0, heel_in_compression=False)
    assert tension.method == "4.3.8.3" and tension.Mb == pytest.approx(275.0 * 12.6 * (1350.0 - 2000.0 / 15.6) / 1625.0 / 1e3)
    assert check_lateral_torsional_buckling(angle, LE_mm=2000.0).Mb == pytest.approx(0.8 * 275.0 * 12.6 / 1e3)
    assert angle_buckling_resistance_moment(275.0, 12.6, 100.0, 1.56, False) == pytest.approx(0.8 * 275.0 * 12.6 / 1e3) # capped
    with pytest.raises(NotImplementedError, match="4.3.8.2"):
        check_lateral_torsional_buckling(L_UNEQUAL("200x100x10"), LE_mm=2000.0)
    with pytest.raises(ValueError, match="15ε"):
        check_lateral_torsional_buckling(L_EQUAL("200x200x16.0"), steel_grade="S460", LE_mm=2000.0)
    with pytest.raises(NotImplementedError):
        check_lateral_torsional_buckling(L_EQUAL_B2B("90x90x12"), LE_mm=2000.0)
    # B.2.7 and B.2.9
    assert plate_equivalent_slenderness(2000.0, 200.0, 10.0) == pytest.approx(2.8 * math.sqrt(2000.0 * 200.0 / 100.0))
    assert angle_equivalent_slenderness(2.94, 2000.0, 1.56) == pytest.approx(2.25 * math.sqrt(2.94 * 2000.0 / 15.6))
    assert angle_equivalent_slenderness(4.79, 2000.0, 1.59, psi_a=8.6) > angle_equivalent_slenderness(4.79, 2000.0, 1.59)


# --- 4.5 Web bearing and buckling ---
def test_web_bearing_and_buckling_at_a_support() -> None:
    # b1 = 50 mm at the end (be = 0): k = T + r = 22.9, n = 2, Pbw = (50 + 45.8) x 8.5 x 275 = 223.9 kN;
    # Px = 25εt/((b1 + nk)d)^0.5 Pbw = 240.8 kN, x (ae + 0.7d)/(1.4d) = 0.5438 with ae = 25 mm
    beam = UB("457x191x67")
    result = check_web_bearing(beam, Fx_kN=150.0, b1_mm=50.0, be_mm=0.0, ae_mm=25.0)
    assert (result.k, result.n) == (pytest.approx(22.9), 2.0)
    assert result.Pbw == pytest.approx(95.8 * 8.5 * 275.0 / 1e3)
    buckling = 25.0 * 8.5 / math.sqrt(95.8 * 407.6) * result.Pbw
    assert result.Px == pytest.approx(buckling * (25.0 + 0.7 * 407.6) / (1.4 * 407.6))
    assert result.governing == "buckling (4.5.3.1)" and result.utilisation.adequacy == "FAILS"
    interior = check_web_bearing(beam, b1_mm=50.0)
    assert interior.n == 5.0 and interior.Px == pytest.approx(25.0 * 8.5 / math.sqrt((50.0 + 114.5) * 407.6) * interior.Pbw)
    free = check_web_bearing(beam, b1_mm=50.0, flange_restrained=False, LE_mm=407.6)
    assert free.Px == pytest.approx(0.7 * interior.Px) and free.metadata["notes"]
    assert check_web_bearing(beam, b1_mm=50.0, welded=True).k == 12.7


# --- 4.6 Tension ---
def test_tension_capacity_and_effective_net_area() -> None:
    beam = UB("457x191x67")
    plain = check_tension(beam, Ft_kN=1000.0)
    assert (plain.Pt, plain.method, plain.Ae) == (pytest.approx(275.0 * 85.5 / 10.0), "4.6.1", 85.5)
    # With An alone, Ke is not applied; with the elements, ae = Ke an <= ag
    holed = check_tension(beam, An_cm2=80.0)
    assert holed.Ae == 80.0 and holed.metadata["notes"]
    flanges = [(24.1, 24.1 - 2 * 2.2 * 1.27), (24.1, 24.1), (37.3, 37.3)]
    by_element = check_tension(beam, elements=flanges)
    assert by_element.Ae == pytest.approx(1.2 * (24.1 - 5.588) + 24.1 + 37.3)
    assert check_tension(beam, elements=[(10.0, 5.0)], properties={"A": 10.0}).Ae == pytest.approx(6.0) # <= 1.2An
    with pytest.raises(ValueError, match="exceed"):
        check_tension(beam, An_cm2=90.0)


def test_simple_ties_4_6_3() -> None:
    # L 80x80x8 bolted by one leg with one 22 mm hole: a1 = 6.4, a2 = 5.9, connected leg ae = min(1.2 x 4.64, 6.4) = 5.568;
    # Pt = py(Ae - 0.5a2) = 275(11.468 - 2.95) = 234.2 kN; welded py(Ag - 0.3a2) = 289.6 kN
    angle = L_EQUAL("80x80x8.0")
    bolted = check_tension(angle, Ft_kN=200.0, An_cm2=12.3 - 2.2 * 0.8, connection="bolted")
    assert (bolted.a1, bolted.a2, bolted.Ae, bolted.method) == (pytest.approx(6.4), pytest.approx(5.9), pytest.approx(11.468), "4.6.3.1")
    assert bolted.Pt == pytest.approx(275.0 * (11.468 - 2.95) / 10.0)
    assert check_tension(angle, connection="welded").Pt == pytest.approx(275.0 * (12.3 - 0.3 * 5.9) / 10.0)
    # Back-to-back pair on both sides of a gusset (4.6.3.2 a)): per component Ae - 0.25a2
    pair = check_tension(L_EQUAL_B2B("90x90x12"), connection="welded", both_sides=True)
    a1 = 2 * 90.0 * 12.0 / 100.0
    assert pair.method == "4.6.3.2" and pair.Pt == pytest.approx(275.0 * (40.6 - 0.15 * (40.6 - a1)) / 10.0)
    assert check_tension(PFC("300x100x46"), connection="welded").a1 == pytest.approx(300.0 * 9.0 / 100.0)
    assert check_tension(angle, connection="welded", connected_leg="short", a1_cm2=5.0).a1 == 5.0
    with pytest.raises(ValueError, match="a1_cm2"):
        check_tension(UB("457x191x67"), connection="bolted")
    with pytest.raises(ValueError, match="less than"):
        check_tension(angle, connection="welded", a1_cm2=13.0)


# --- 4.7 Compression ---
@pytest.mark.parametrize(
    ("slenderness", "py", "curve", "pc"),
    [
        (40.0, 275.0, "a", 260.0), (70.0, 355.0, "a", 270.0), (100.0, 460.0, "a", 180.0),
        (40.0, 275.0, "b", 250.0), (50.0, 355.0, "b", 298.0), (80.0, 460.0, "b", 237.0), (120.0, 275.0, "b", 108.0),
        (30.0, 275.0, "c", 255.0), (50.0, 355.0, "c", 275.0), (60.0, 275.0, "c", 201.0), (108.0, 275.0, "c", 113.0), (150.0, 460.0, "c", 76.0),
        (40.0, 275.0, "d", 225.0), (58.0, 355.0, "d", 229.0), (120.0, 460.0, "d", 105.0),
        (15.0, 460.0, "d", 453.0), (10.0, 275.0, "c", 275.0),
    ],
)
def test_compressive_strength_table_24(slenderness: float, py: float, curve: str, pc: float) -> None:
    assert compressive_strength(slenderness, py, curve) == pytest.approx(pc, abs=0.6)


def test_compressive_strength_inputs_and_strut_curves() -> None:
    assert limiting_slenderness(275.0) == pytest.approx(17.15, abs=0.01)
    assert compressive_strength(0.0, 275.0) == 275.0
    with pytest.raises(ValueError, match="curve"):
        compressive_strength(50.0, 275.0, "e")
    with pytest.raises(ValueError, match="negative"):
        compressive_strength(-1.0, 275.0)
    # Table 23
    assert strut_curve(SectionType.UB, "x", T=12.7, D=453.4, B=189.9) == "a"
    assert strut_curve(SectionType.UB, "y", T=45.0, D=453.4, B=189.9) == "c"
    assert strut_curve(SectionType.UC, "y", T=14.2, D=254.1, B=254.6) == "c"
    assert strut_curve(SectionType.UC, "y", T=50.0, D=254.1, B=254.6) == "d"
    assert strut_curve(SectionType.HFRHS, "y") == "a" and strut_curve(SectionType.CFCHS, "x") == "c"
    assert strut_curve(SectionType.UB, "y", welded=True) == "c" and strut_curve(SectionType.HFRHS, welded=True, T=45.0) == "c"
    assert strut_curve(SectionType.L_EQUAL, "v") == "c" and strut_curve(shape="bar", T=50.0) == "c"
    with pytest.raises(ValueError, match="shape"):
        strut_curve(shape="tube")
    with pytest.raises(NotImplementedError):
        strut_curve(SectionType("Sigma"))
    assert effective_length(4000.0, "sway_free") == 8000.0 and effective_length(4000.0, "fixed_fixed") == pytest.approx(2800.0)
    with pytest.raises(ValueError, match="restraint"):
        effective_length(4000.0, "fixed")


def test_compression_resistance_universal_column() -> None:
    # UC 254x254x73: LEy = 64.8 x 60 = 3888 mm, λy = 60, curve c: Table 24 pc = 201; λx = 5000/111 = 45.05, curve b
    column = UC("254x254x73")
    result = check_compression(column, Fc_kN=1500.0, LEx_mm=5000.0, LEy_mm=3888.0)
    assert result.section_class == SectionClass.CLASS_3 and result.governing_axis == "y"
    mode_x, mode_y = result.modes
    assert (mode_x.curve, mode_y.curve) == ("b", "c")
    assert mode_y.slenderness == pytest.approx(60.0) and mode_y.pc == pytest.approx(201.0, abs=0.6)
    assert result.Pcy == pytest.approx(93.1 * mode_y.pc / 10.0) and result.Pc == result.Pcy
    assert result.Pcx == pytest.approx(93.1 * compressive_strength(5000.0 / 111.0, 275.0, "b") / 10.0)
    assert result.utilisation.utilisation == pytest.approx(1500.0 / result.Pc)
    assert result.limit_state == LimitState.FLEXURAL_BUCKLING
    # Welded sections take py - 20 (4.7.5); curves and slenderness can be overridden
    welded = check_compression(column, LEy_mm=3888.0, welded=True)
    assert welded.py_strut == 255.0 and welded.modes[0].pc == pytest.approx(compressive_strength(60.0, 255.0, "c"))
    assert check_compression(column, LEy_mm=3888.0, curves={"y": "d"}).modes[0].curve == "d"
    assert check_compression(column, slenderness={"x": 30.0}).modes[0].slenderness == 30.0
    with pytest.raises(ValueError, match="effective length"):
        check_compression(column)


def test_compression_resistance_slender_and_thick() -> None:
    # UB 457x191x67 with r2 = 1: slender web, Aeff = 79.754 cm², pcs at λ(Aeff/Ag)^0.5
    beam = UB("457x191x67")
    slender = check_compression(beam, LEx_mm=5000.0, LEy_mm=3000.0)
    assert slender.section_class == SectionClass.CLASS_4 and slender.A == pytest.approx(79.754)
    lambda_y = 3000.0 / 41.2 * math.sqrt(79.754 / 85.5)
    assert slender.modes[1].slenderness == pytest.approx(lambda_y)
    assert slender.Pcy == pytest.approx(79.754 * compressive_strength(lambda_y, 275.0, "b") / 10.0)
    assert check_compression(beam, Fc_kN=500.0, LEy_mm=3000.0).section_class == SectionClass.CLASS_3 # actual r2
    assert check_compression(beam, LEy_mm=3000.0, A_eff_cm2=80.0).A == 80.0
    reduced = check_compression(HFSHS("300x300x6.3"), LEx_mm=6000.0, class_4_method="reduced_strength")
    assert reduced.py == pytest.approx((40.0 / (281.1 / 6.3)) ** 2 * 275.0) and reduced.A == 73.6
    # 40 < T <= 50: average of both rows (Table 23 NOTE 1); UC 356x406x340 has T = 42.9 mm
    thick = check_compression(UC("356x406x340"), LEy_mm=4000.0)
    mode = thick.modes[0]
    ry = UC("356x406x340").get_properties()["i_zz"]
    py = thick.py
    assert mode.curve == "c/d"
    assert mode.pc == pytest.approx(0.5 * (compressive_strength(4000.0 / (ry * 10), py, "c") + compressive_strength(4000.0 / (ry * 10), py, "d")))


def test_angle_strut_slenderness_table_25() -> None:
    # Single L 80x80x8 by two bolts, L = 2 m: 0.85Lv/rv = 108.97 governs over 0.7Lv/rv + 15, 1.0La/ra, 0.7La/ra + 30
    angle = L_EQUAL("80x80x8.0")
    lam = single_angle_slenderness(2000.0, 1.56, 2000.0, 2.43, 2000.0, 2.43)
    assert lam == pytest.approx(0.85 * 2000.0 / 15.6)
    assert single_angle_slenderness(2000.0, 1.56, 2000.0, 2.43, 2000.0, 2.43, "single_bolt") == pytest.approx(2000.0 / 15.6)
    assert single_angle_slenderness(400.0, 1.56, 400.0, 2.43, 400.0, 2.43, alternate_restraint=True) == pytest.approx(1.2 * (0.7 * 400.0 / 24.3 + 30.0))
    strut = check_angle_strut(angle, Fc_kN=100.0, L_mm=2000.0)
    assert strut.modes[0].curve == "c" and strut.Pc == pytest.approx(12.3 * compressive_strength(lam, 275.0, "c") / 10.0)
    assert strut.reference.clause == "4.7.10"
    assert check_angle_strut(angle, L_mm=2000.0, connection="single_bolt").Pc == pytest.approx(0.8 * 12.3 * compressive_strength(2000.0 / 15.6, 275.0, "c") / 10.0)
    # Double angles: y-y [(0.85Ly/ry)² + λc²]^0.5 >= 1.4λc, x-x 1.0Lx/rx >= 0.7Lx/rx + 30
    assert double_angle_slenderness(2000.0, 2.71, 2000.0, 3.8, 20.0) == pytest.approx(0.7 * 2000.0 / 27.1 + 30.0) # x-x governs
    assert double_angle_slenderness(2000.0, 5.0, 4000.0, 2.0, 20.0) == pytest.approx(math.hypot(0.85 * 4000.0 / 20.0, 20.0)) # y-y governs
    assert double_angle_slenderness(1000.0, 2.71, 1000.0, 3.8, 60.0) == pytest.approx(1.4 * 60.0)
    assert double_angle_slenderness(6000.0, 2.71, 1000.0, 3.8, 10.0, "both_sides_bolts") == pytest.approx(0.85 * 6000.0 / 27.1) # 0.85λ > 0.7λ + 30 for λ > 200
    pair = check_angle_strut(L_EQUAL_B2B("90x90x12"), L_mm=2000.0, L_c_mm=600.0, back_to_back_gap_mm=10.0)
    lambda_c = 600.0 / (L_EQUAL("90x90x12.0").get_properties()["i_vv"] * 10.0)
    assert pair.metadata["slenderness"] == pytest.approx(double_angle_slenderness(2000.0, 2.71, 2000.0, 4.16, lambda_c))
    assert check_angle_strut(L_EQUAL_B2B("90x90x12"), L_mm=2000.0, L_c_mm=600.0, r_v_cm=1.76, connection="both_sides_single_bolt").metadata["connection"] == "both_sides_single_bolt"
    with pytest.raises(ValueError, match="channel"):
        check_angle_strut(PFC("300x100x46"), L_mm=2000.0)
    # Channels and tees (4.7.10.4, 4.7.10.5)
    assert channel_slenderness(3000.0, 10.0, 3000.0, 2.0) == pytest.approx(max(0.85 * 30.0, 150.0))
    assert channel_slenderness(3000.0, 1.0, 300.0, 2.0, "single_row") == pytest.approx(300.0)
    assert tee_slenderness(3000.0, 2.0, 3000.0, 1.0) == pytest.approx(max(150.0, 0.85 * 300.0))
    assert tee_slenderness(300.0, 2.0, 3000.0, 1.0, "single_row") == pytest.approx(300.0)


def test_back_to_back_radius_of_gyration_by_gap() -> None:
    # ry of L 90x90x12 pairs: 3.8 (0 mm), 4.09 (8 mm), 4.16 (10 mm); the smallest gap by default
    pair = L_EQUAL_B2B("90x90x12")
    assert check_compression(pair, LEy_mm=2000.0).modes[0].r == pytest.approx(3.8)
    assert check_compression(pair, LEy_mm=2000.0, back_to_back_gap_mm=9.0).modes[0].r == pytest.approx(4.125)
    assert check_compression(pair, LEy_mm=2000.0, back_to_back_gap_mm=40.0).modes[0].r == pytest.approx(4.36)


def test_simple_column_4_7_7() -> None:
    # UC 254x254x73: λLT = 0.5L/ry = 38.58; Table 16 between 35 (273) and 40 (262)
    column = UC("254x254x73")
    assert simple_column_eccentricity(column) == pytest.approx(254.1 / 2 + 100.0)
    assert simple_column_eccentricity(column, "y", bearing=300.0) == pytest.approx(8.6 / 2 + 150.0)
    result = check_simple_column(column, Fc_kN=1000.0, Mx_kNm=20.0, My_kNm=5.0, LEx_mm=5000.0, LEy_mm=5000.0)
    assert result.lambda_LT == pytest.approx(0.5 * 5000.0 / 64.8)
    pb = result.Mbs / 992.0 * 1e3
    assert pb == pytest.approx(273.0 - (result.lambda_LT - 35.0) / 5.0 * 11.0, abs=0.6)
    assert result.Mcy == pytest.approx(275.0 * 307.0 / 1e3)
    assert result.utilisation.utilisation == pytest.approx(1000.0 / result.Pc + 20.0 / result.Mbs + 5.0 / result.Mcy)
    hollow = check_simple_column(HFSHS("300x300x6.3"), Fc_kN=500.0, Mx_kNm=10.0, LEx_mm=5000.0, LEy_mm=5000.0)
    assert hollow.Mbs == pytest.approx(check_bending(HFSHS("300x300x6.3")).Mc) and hollow.section_class == SectionClass.CLASS_4


# --- 4.8 and Annex I: combined moment and axial force ---
def test_reduced_plastic_moduli_i_2() -> None:
    # UC 254x254x73, n = 1000/(93.1 x 27.5) = 0.3906 > t(D - 2T)/A = 0.2085: Srx = (A²/4B)(2BD/A - 1 + n)(1 - n)
    n = 1000.0 / (93.1 * 27.5)
    A, D, B, T, t = 93.1, 25.41, 25.46, 1.42, 0.86
    S_rx, S_ry = reduced_plastic_moduli(n, 93.1, 254.1, 254.6, 14.2, 8.6, 992.0, 465.0)
    assert S_rx == pytest.approx(A**2 / (4 * B) * (2 * B * D / A - 1 + n) * (1 - n))
    assert S_ry == pytest.approx(A**2 / (8 * T) * (4 * B * T / A - 1 + n) * (1 - n))
    small_x, small_y = reduced_plastic_moduli(0.05, 93.1, 254.1, 254.6, 14.2, 8.6, 992.0, 465.0)
    assert small_x == pytest.approx(992.0 - A**2 / (4 * t) * 0.05**2) and small_y == pytest.approx(465.0 - A**2 / (4 * D) * 0.05**2)
    assert reduced_plastic_moduli(1.0, 93.1, 254.1, 254.6, 14.2, 8.6, 992.0, 465.0) == (0.0, 0.0)


def test_tension_with_moments() -> None:
    # UB 457x191x67, Ft = 500, Mx = 200: 4.8.2.2 500/2351.25 + 200/404.25 = 0.707; 4.8.2.3 n = 0.2127 <= 0.4255,
    # Srx = 1470 - (85.5²/(4 x 0.85))n² = 1372.8, Mx/Mrx = 0.530
    beam = UB("457x191x67")
    result = check_tension_and_bending(beam, Ft_kN=500.0, Mx_kNm=200.0, LE_LT_mm=4000.0)
    assert result.utilisations["cross-section (4.8.2.2)"] == pytest.approx(500.0 / 2351.25 + 200.0 / 404.25)
    n = 500.0 / 2351.25
    assert result.Mrx == pytest.approx(275.0 * (1470.0 - 85.5**2 / 3.4 * n**2) / 1e3)
    assert result.method == "4.8.2.3" and result.utilisations["cross-section (4.8.2.3)"] == pytest.approx(200.0 / result.Mrx)
    assert result.governing == "lateral-torsional (4.8.2.1)" and result.utilisation.utilisation == pytest.approx(200.0 / result.Mb)
    # Biaxial: (Mx/Mrx)^2 + (My/Mry)^1 for I-sections (z1 = 2, z2 = 1)
    biaxial = check_tension_and_bending(beam, Ft_kN=500.0, Mx_kNm=200.0, My_kNm=10.0)
    assert biaxial.utilisations["cross-section (4.8.2.3)"] == pytest.approx((200.0 / biaxial.Mrx) ** 2 + 10.0 / biaxial.Mry)
    # Angles have no reduced moduli: 4.8.2.2 only
    assert list(check_tension_and_bending(L_EQUAL("80x80x8.0"), Ft_kN=100.0, Mx_kNm=1.0).utilisations) == ["cross-section (4.8.2.2)"]


def test_compression_with_moments_exact_i_section() -> None:
    column = UC("254x254x73")
    kwargs = dict(Fc_kN=1000.0, LEx_mm=5000.0, LEy_mm=5000.0, LE_LT_mm=5000.0)
    compression = check_compression(column, Fc_kN=1000.0, LEx_mm=5000.0, LEy_mm=5000.0)
    ltb = check_lateral_torsional_buckling(column, LE_mm=5000.0, Fc_kN=1000.0)
    rx, ry = 1000.0 / compression.Pcx, 1000.0 / compression.Pcy
    # 4.8.3.3.2 a): major axis only
    major = check_compression_and_bending(column, Mx_kNm=60.0, mx=0.9, mLT=0.925, **kwargs)
    assert major.section_class == SectionClass.CLASS_1 # combined classification, not axial compression alone (4.8.1)
    assert major.Mcx == pytest.approx(272.8) and major.Mb == pytest.approx(ltb.Mb)
    assert major.utilisations["major axis in-plane (4.8.3.3.2a)"] == pytest.approx(rx + 0.9 * 60.0 / 272.8 * (1 + 0.5 * rx))
    assert major.utilisations["out-of-plane (4.8.3.3.2a)"] == pytest.approx(ry + 0.925 * 60.0 / ltb.Mb)
    # 4.8.3.2 b): Mx/Mrx is more favourable than Fc/(Ag py) + Mx/Mcx for class 1
    assert major.utilisations["cross-section (4.8.3.2b)"] == pytest.approx(60.0 / major.Mrx)
    # b) minor axis only, and c) both
    minor = check_compression_and_bending(column, My_kNm=10.0, **kwargs)
    Mcy = minor.Mcy
    assert minor.utilisations["minor axis in-plane (4.8.3.3.2b)"] == pytest.approx(ry + 10.0 / Mcy * (1 + ry))
    assert minor.utilisations["out-of-plane (4.8.3.3.2b)"] == pytest.approx(rx + 0.5 * 10.0 / Mcy)
    both = check_compression_and_bending(column, Mx_kNm=60.0, My_kNm=10.0, **kwargs)
    Mb, Mcx, Mcy = both.Mb, 272.8, both.Mcy
    assert both.utilisations["major axis (4.8.3.3.2c)"] == pytest.approx(rx + 60.0 / Mcx * (1 + 0.5 * rx) + 0.5 * 10.0 / Mcy)
    assert both.utilisations["lateral-torsional (4.8.3.3.2c)"] == pytest.approx(ry + 60.0 / Mb + 10.0 / Mcy * (1 + ry))
    assert both.utilisations["interactive (4.8.3.3.2c)"] == pytest.approx(60.0 * (1 + 0.5 * rx) / (Mcx * (1 - rx)) + 10.0 * (1 + ry) / (Mcy * (1 - ry)))
    assert both.governing == "lateral-torsional (4.8.3.3.2c)"


def test_compression_with_moments_simplified_and_stocky() -> None:
    column = UC("254x254x73")
    kwargs = dict(Fc_kN=1000.0, LEx_mm=5000.0, LEy_mm=5000.0, LE_LT_mm=5000.0)
    simple = check_compression_and_bending(column, Mx_kNm=60.0, My_kNm=10.0, method="simplified", **kwargs)
    Pc, Pcy, Mb = simple.Pc, simple.Pcy, simple.Mb
    assert simple.utilisations["flexural (4.8.3.3.1)"] == pytest.approx(1000.0 / Pc + 60.0 / (275.0 * 898.0 / 1e3) + 10.0 / (275.0 * 307.0 / 1e3))
    assert simple.utilisations["lateral-torsional (4.8.3.3.1)"] == pytest.approx(1000.0 / Pcy + 60.0 / Mb + 10.0 / (275.0 * 307.0 / 1e3))
    # I.1 stocky members, major axis: Max between Mox and Mrx for 17.15ε < λx < 85.8ε
    stocky = check_compression_and_bending(column, Mx_kNm=60.0, method="stocky", **kwargs)
    rx = 1000.0 / stocky.Pcx
    M_ox = 272.8 * (1 - rx) / (1 + 0.5 * rx)
    lambda_x = 5000.0 / 111.0
    assert stocky.Max == pytest.approx(M_ox + (85.8 - lambda_x) / 68.65 * (stocky.Mrx - M_ox))
    assert stocky.utilisations["major axis in-plane (I.1a)"] == pytest.approx(60.0 / stocky.Max)
    assert stocky.Mab is not None and stocky.Mab <= stocky.Mrx
    # I.1 needs a class 1 or 2 section: a moment about the minor axis with axial force puts the UC web in compression
    with pytest.raises(ValueError, match="I.1"):
        check_compression_and_bending(column, Mx_kNm=60.0, My_kNm=10.0, method="stocky", **kwargs)
    with pytest.raises(ValueError, match="I.1"):
        check_compression_and_bending(PFC("300x100x46"), Mx_kNm=10.0, method="stocky", Fc_kN=100.0, LEx_mm=3000.0, LEy_mm=3000.0)


def test_compression_with_moments_hollow_and_other_shapes() -> None:
    # 4.8.3.3.3 CHS: no lateral-torsional buckling, out-of-plane 0.5mLT MLT/Mcx, and (1 + 0.5Fc/Pcy)
    tube = HFCHS("219.1x5.0")
    result = check_compression_and_bending(tube, Fc_kN=300.0, Mx_kNm=30.0, My_kNm=10.0, LEx_mm=4000.0, LEy_mm=4000.0)
    rx, ry = 300.0 / result.Pcx, 300.0 / result.Pcy
    Mc = result.Mcx
    assert result.utilisations["lateral-torsional (4.8.3.3.3c)"] == pytest.approx(ry + 0.5 * 30.0 / Mc + 10.0 / Mc * (1 + 0.5 * ry))
    assert result.utilisations["interactive (4.8.3.3.3c)"] == pytest.approx(30.0 * (1 + 0.5 * rx) / (Mc * (1 - rx)) + 10.0 * (1 + 0.5 * ry) / (Mc * (1 - ry)))
    stocky = check_compression_and_bending(HFRHS("200x100x10.0"), Fc_kN=200.0, My_kNm=5.0, LEx_mm=3000.0, LEy_mm=3000.0, method="stocky")
    assert stocky.May is not None and "out-of-plane (I.1b)" in stocky.utilisations
    rhs = check_compression_and_bending(HFRHS("200x100x5.0"), Fc_kN=200.0, Mx_kNm=20.0, LEx_mm=3000.0, LEy_mm=3000.0, LE_LT_mm=3000.0)
    assert "out-of-plane (4.8.3.3.3a)" in rhs.utilisations
    # Channels fall back to the simplified method; biaxial bending without axial force is 4.9
    channel = check_compression_and_bending(PFC("300x100x46"), Fc_kN=100.0, Mx_kNm=20.0, LEx_mm=3000.0, LEy_mm=3000.0, LE_LT_mm=3000.0)
    assert channel.method == "simplified" and channel.metadata["notes"]
    biaxial = check_compression_and_bending(UB("457x191x67"), Mx_kNm=150.0, My_kNm=10.0)
    assert biaxial.reference.clause == "4.9" and biaxial.Pc is None and biaxial.metadata["notes"]
    slender = check_compression_and_bending(HFSHS("300x300x6.3"), Fc_kN=500.0, Mx_kNm=50.0, LEx_mm=5000.0, LEy_mm=5000.0)
    assert slender.section_class == SectionClass.CLASS_4 and "cross-section (4.8.3.2c)" in slender.utilisations
    with pytest.raises(ValueError, match="compression"):
        check_compression_and_bending(tube, Fc_kN=-10.0)
    with pytest.raises(ValueError, match="LEx_mm"):
        check_compression_and_bending(tube, Fc_kN=10.0, Mx_kNm=1.0)


def test_single_angle_simplified_i_4_3() -> None:
    angle = L_EQUAL("80x80x8.0")
    result = check_single_angle_compression_and_bending(angle, Fc_kN=50.0, Mx_kNm=1.0, My_kNm=0.5, LEx_mm=2000.0, LEy_mm=2000.0, mLTx=0.4)
    M_b = 0.8 * 275.0 * 12.6 / 1e3
    assert result.utilisation.utilisation == pytest.approx(50.0 / result.Pc + 0.6 * 1.0 / M_b + 1.0 * 0.5 / M_b) # mLTx >= 0.6
    with pytest.raises(ValueError, match="equal"):
        check_single_angle_compression_and_bending(L_UNEQUAL("200x100x10"), Fc_kN=50.0, LEx_mm=2000.0, LEy_mm=2000.0)


# --- Annexes B.3, C.3 and I.5 ---
def test_internal_moments() -> None:
    assert strut_action_moment(100.0, 200.0, 275.0, 500.0) == pytest.approx((275.0 / 200.0 - 1.0) * 100.0 * 0.5)
    assert lateral_torsional_internal_moment(275.0, 200.0, 400.0, 100.0, 300.0, 0.9) == pytest.approx(0.375 * 0.25 * 0.9 * 300.0)
    p_E = math.pi**2 * 205_000.0 / 100.0**2
    assert amplified_moment(50.0, 100.0, 100.0, 0.9) == pytest.approx(0.9 * 50.0 / (p_E / 100.0 - 1.0))
    assert amplified_moment(50.0, 0.0, 100.0) == 0.0
    with pytest.raises(ValueError, match="unstable"):
        amplified_moment(50.0, 300.0, 100.0)
    assert internal_moment_at(10.0, 2500.0, 5000.0) == pytest.approx(10.0)


def test_section_class_inputs() -> None:
    assert _as_section_class(2) == SectionClass.CLASS_2
    assert _as_section_class("semi-compact") == SectionClass.CLASS_3
    assert _as_section_class("CLASS_4") == SectionClass.CLASS_4
    assert _as_section_class(SectionClass.CLASS_1) == SectionClass.CLASS_1
    with pytest.raises(ValueError, match="classes 1 to 4"):
        _as_section_class(SectionClass.COMPACT)
    with pytest.raises(ValueError, match="Unrecognised"):
        _as_section_class("class 5")
    with pytest.raises(ValueError, match="py_mpa"):
        check_shear(properties={"A": 10.0}, direction="flanges", Av_cm2=5.0)
    with pytest.raises(ValueError, match="section_class"):
        check_bending(properties={"W_el_yy": 100.0}, py_mpa=275.0)


def test_package_exports() -> None:
    import steelsnakes.BS as BS
    import steelsnakes.BS.checks as checks

    assert {"check_bending", "check_compression_and_bending", "check_beam_deflection"} <= set(BS.__all__)
    assert all(hasattr(checks, name) for name in checks.__all__)
