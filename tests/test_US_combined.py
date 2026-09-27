from __future__ import annotations

import math

import pytest

from steelsnakes.base.checks import LimitState
from steelsnakes.US import check_axial_flexure_interaction, compression, flexure, hss_torsion
from steelsnakes.US.checks.combined import (
    calculate_Cb_tension_factor,
    calculate_Pey,
    calculate_rectangular_hss_torsional_constant,
    calculate_round_hss_torsional_constant,
    check_flange_rupture_interaction,
    check_hss_combined_torsion,
    check_non_hss_torsion,
    check_out_of_plane_interaction,
    check_rectangular_hss_torsion,
    check_round_hss_torsion,
    check_stress_interaction,
)
from steelsnakes.US.sections.beams import W_beam
from steelsnakes.US.sections.hollow import HSS_RCT, HSS_RND
from steelsnakes.US.sections.pipes import PIPE


# AISC Design Examples (v16.0)
def test_example_H1B_W14x99_biaxial_interaction() -> None:
    result = check_axial_flexure_interaction(Pr=400.0, Pc=1130.0, Mrx=250.0 * 12, Mcx=642.0 * 12, Mry=80.0 * 12, Mcy=311.0 * 12)

    assert result.reference is not None and result.reference.equation == "H1-1a"
    assert result.utilisation == pytest.approx(0.929, rel=2e-3)
    assert result.adequacy == "OK"


def test_example_H1B_capacities_from_chapters_E_and_F() -> None:
    section = W_beam("W14X99")
    Pc = compression(section=section, Fy=50.0, L=14 * 12).phi_c_Pn
    Mcx = flexure(section=section, Fy=50.0, Lb=14 * 12).phi_b_Mn
    Mcy = flexure(section=section, Fy=50.0, axis="minor").phi_b_Mn

    assert Pc == pytest.approx(1130.0, rel=5e-3)
    assert Mcx == pytest.approx(642.0 * 12, rel=5e-3)
    assert Mcy == pytest.approx(311.0 * 12, rel=5e-3)


def test_H1_1b_for_low_axial_ratio_and_tension() -> None:
    result = check_axial_flexure_interaction(Pr=50.0, Pc=500.0, Mrx=100.0, Mcx=200.0, axial="tension")
    assert result.reference is not None and result.reference.equation == "H1-1b"
    assert result.reference.clause == "H1.2"
    assert result.utilisation == pytest.approx(0.05 + 0.5)
    with pytest.raises(ValueError):
        check_axial_flexure_interaction(Pr=50.0, Pc=500.0, Mrx=100.0)


def test_H1_2_Cb_multiplier_and_H1_3() -> None:
    Pey = calculate_Pey(Iy=100.0, Lb=240.0)
    assert Pey == pytest.approx(math.pi**2 * 29000.0 * 100.0 / 240.0**2)
    assert calculate_Cb_tension_factor(100.0, Pey) == pytest.approx(math.sqrt(1.0 + 100.0 / Pey))

    result = check_out_of_plane_interaction(Pr=300.0, Pcy=900.0, Mrx=3000.0, Mcx=5000.0, Cb=1.14)
    expected = (1 / 3) * (1.5 - 0.5 / 3) + (3000.0 / (1.14 * 5000.0)) ** 2
    assert result.utilisation == pytest.approx(expected)
    with pytest.raises(ValueError):
        check_out_of_plane_interaction(Pr=300.0, Pcy=900.0, Mrx=3000.0, Mcx=5000.0, Mry=100.0, Mcy=1000.0)


def test_H2_signed_stress_interaction() -> None:
    result = check_stress_interaction(fra=10.0, Fca=30.0, frbw=-5.0, Fcbw=40.0, frbz=8.0, Fcbz=35.0)
    assert result.utilisation == pytest.approx(abs(10 / 30 - 5 / 40 + 8 / 35))


def test_example_H5A_rectangular_hss_torsion() -> None:
    result = hss_torsion(section=HSS_RCT("HSS6X4X1/4"), Fy=50.0)

    assert result.slenderness == pytest.approx(22.8, rel=3e-3)
    assert result.limit_state == LimitState.TORSIONAL_YIELDING
    assert result.phi_T_Tn == pytest.approx(273.0, rel=3e-3)


def test_example_H5B_round_hss_torsion() -> None:
    result = hss_torsion(section=HSS_RND("HSS5.000X0.250"), Fy=50.0, L=14 * 12)

    assert result.metadata["Fcr_H3-2a"] == pytest.approx(133.0, rel=5e-3)
    assert result.metadata["Fcr_H3-2b"] == pytest.approx(175.0, rel=5e-3)
    assert result.phi_T_Tn == pytest.approx(215.0, rel=3e-3)


def test_rectangular_hss_torsion_buckling_ranges_and_pipe_constant() -> None:
    inelastic = check_rectangular_hss_torsion(Fy=50.0, C=10.0, h=65.0 * 0.1, t=0.1)
    elastic = check_rectangular_hss_torsion(Fy=50.0, C=10.0, h=100.0 * 0.1, t=0.1)
    assert inelastic.reference is not None and inelastic.reference.equation == "H3-4"
    assert elastic.Fcr == pytest.approx(0.458 * math.pi**2 * 29000.0 / 100.0**2)
    with pytest.raises(ValueError):
        check_rectangular_hss_torsion(Fy=50.0, C=10.0, h=30.0, t=0.1)

    pipe_section = PIPE("Pipe8STD") # no tabulated C for pipes; the User Note expression is used
    pipe = hss_torsion(section=pipe_section, Fy=35.0)
    assert pipe.C == pytest.approx(calculate_round_hss_torsional_constant(pipe_section.OD, pipe_section.tdes))
    assert calculate_rectangular_hss_torsional_constant(6.0, 4.0, 0.233) == pytest.approx(10.1, rel=5e-2)
    assert check_round_hss_torsion(Fy=50.0, C=7.95, D=5.0, t=0.233).L is None


def test_example_H5C_combined_torsion_at_support() -> None:
    result = check_hss_combined_torsion(Pr=0.0, Pc=100.0, Tr=66.2, Tc=273.0, Vr=11.0, Vc=66.7)
    assert result.reference is not None and result.reference.equation == "H3-6"
    assert result.utilisation == pytest.approx(0.166, rel=5e-3)


def test_combined_torsion_below_20_percent_uses_H1() -> None:
    result = check_hss_combined_torsion(Pr=50.0, Pc=500.0, Tr=10.0, Tc=273.0, Mrx=100.0, Mcx=200.0)
    assert result.reference is not None and result.reference.clause == "H1.1"
    assert "Tr/Tc" in result.metadata


def test_non_hss_torsion_and_flange_rupture() -> None:
    torsion = check_non_hss_torsion(Fy=50.0, fn=30.0, fv=20.0, Fcr=40.0, fcr=30.0)
    assert torsion.utilisation == pytest.approx(max(30 / 45, 20 / 27, 30 / 36))

    rupture = check_flange_rupture_interaction(Pr=-50.0, Pc=300.0, Mrx=2000.0, Mcx=2500.0)
    assert rupture.utilisation == pytest.approx(-50 / 300 + 2000 / 2500)


def test_example_H3_W14x82_tension_and_biaxial_flexure() -> None:
    from steelsnakes.US import tension

    section = W_beam("W14X82")
    Pey = calculate_Pey(Iy=section.Iy, Lb=30 * 12)
    assert Pey == pytest.approx(327.0, rel=3e-3)
    factor = calculate_Cb_tension_factor(Pr=174.0, Pey=Pey)
    assert factor == pytest.approx(1.24, abs=5e-3)
    Cb = round(1.14 * factor, 2) # 1.41

    Pc = tension(section=section, Fy=50.0).phi_t_Pn
    Mcx = flexure(section=section, Fy=50.0, Lb=30 * 12, Cb=Cb).phi_b_Mn
    Mcy = flexure(section=section, Fy=50.0, axis="minor").phi_b_Mn
    assert Pc == pytest.approx(1080.0)
    assert Mcx == pytest.approx(0.90 * 6560.0, rel=3e-3)
    assert Mcy == pytest.approx(0.90 * 2240.0, rel=3e-3)

    check = check_axial_flexure_interaction(Pr=174.0, Pc=Pc, Mrx=192.0 * 12, Mcx=Mcx, Mry=67.6 * 12, Mcy=Mcy, axial="tension")
    assert check.reference.equation == "H1-1b"
    assert check.utilisation == pytest.approx(0.873, abs=3e-3)
