# H: DESIGN OF MEMBERS FOR COMBINED FORCES AND TORSION
# H1. Doubly and Singly Symmetric Members Subjected to Flexure and Axial Force
# H2. Unsymmetric and Other Members Subjected to Flexure and Axial Force
# H3. Members Subjected to Torsion and Combined Torsion, Flexure, Shear, and/or Axial Force
# H4. Rupture of Flanges with Bolt Holes and Subjected to Tension
# User Note: For composite members, see Chapter I.
# NOTE: required forces and moments must include second-order effects per Chapter C; no amplification is applied here.
# NOTE: all terms in H1-1a, H1-1b, H1-3 and H3-6 are taken as positive.

from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, UtilisationCheck
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import RECT_HSS_SECTION_TYPES, ROUND_HSS_SECTION_TYPES, _positive_value, _require_positive, _section_properties
from steelsnakes.US.checks.compression import E_STEEL

PHI_T_TORSION = 0.90 # H3.1 and H3.3; NOTE: phi_T (torsion) != phi_t (tension) # TODO: resolve in docs i.e tricky_symbols.md


def _ratio(demand: float, capacity: Optional[float]) -> float:
    if capacity is None:
        if demand:
            raise ValueError("A capacity is required for every non-zero demand.")
        return 0.0
    return abs(demand) / _require_positive(capacity, "capacity")


# --- H1. Doubly and Singly Symmetric Members Subjected to Flexure and Axial Force ---
def check_axial_flexure_interaction(
    Pr: float,
    Pc: float,
    Mrx: float = 0.0,
    Mcx: Optional[float] = None,
    Mry: float = 0.0,
    Mcy: Optional[float] = None,
    axial: Literal["compression", "tension"] = "compression",
) -> UtilisationCheck:
    """AISC 360-22 Sections H1.1 (compression) and H1.2 (tension): Interaction of flexure and axial force.

    (a) Pr/Pc >= 0.2: Pr/Pc + 8/9*(Mrx/Mcx + Mry/Mcy) <= 1.0 (H1-1a)
    (b) Pr/Pc < 0.2: Pr/(2Pc) + (Mrx/Mcx + Mry/Mcy) <= 1.0 (H1-1b)

    Args:
        Pr: Required axial strength (kips)
        Pc: Available axial strength, phi_c*Pn (Chapter E) or phi_t*Pn (Chapter D) (kips)
        Mrx, Mry: Required flexural strengths (kip-in.)
        Mcx, Mcy: Available flexural strengths, phi_b*Mn (Chapter F) (kip-in.)
        axial: "compression" (H1.1) or "tension" (H1.2)
    """
    # NOTE: Section H2 may be used in lieu of the provisions of this section.
    axial_ratio = _ratio(Pr, Pc)
    flexure_ratio = _ratio(Mrx, Mcx) + _ratio(Mry, Mcy)
    if axial_ratio >= 0.2:
        utilisation, equation = axial_ratio + 8.0 / 9.0 * flexure_ratio, "H1-1a"
    else:
        utilisation, equation = axial_ratio / 2.0 + flexure_ratio, "H1-1b"
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pr/Pc": axial_ratio, "Mrx/Mcx": _ratio(Mrx, Mcx), "Mry/Mcy": _ratio(Mry, Mcy), "axial": axial},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H1.1" if axial == "compression" else "H1.2", equation=equation, title="Flexure and axial force"),
    )


def calculate_Pey(Iy: float, Lb: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation H1-2: Pey = pi^2*E*Iy/Lb^2."""
    return math.pi**2 * E * _require_positive(Iy, "Iy") / _require_positive(Lb, "Lb") ** 2


def calculate_Cb_tension_factor(Pr: float, Pey: float, alpha: float = 1.0) -> float:
    """AISC 360-22 Section H1.2: For doubly symmetric members, Cb in Chapter F is permitted to be multiplied by
    sqrt(1 + alpha*Pr/Pey) when axial tension acts concurrently with flexure; alpha = 1.0 (LRFD).
    """
    return math.sqrt(1.0 + alpha * abs(Pr) / _require_positive(Pey, "Pey"))


def check_out_of_plane_interaction(
    Pr: float,
    Pcy: float,
    Mrx: float,
    Mcx: float,
    Cb: float = 1.0,
    Mry: float = 0.0,
    Mcy: Optional[float] = None,
) -> UtilisationCheck:
    """AISC 360-22 Section H1.3(b): Doubly symmetric rolled compact members in single-axis flexure and compression,
    out-of-plane buckling and lateral-torsional buckling.

    Pr/Pcy*(1.5 - 0.5*Pr/Pcy) + (Mrx/(Cb*Mcx))^2 <= 1.0 (H1-3)
    where Mcx is the available LTB strength for major-axis flexure with Cb = 1.0, and Pcy the available compressive
    strength out of the plane of bending. Applies where Lcz <= Lcy; for Mry/Mcy >= 0.05, H1.1 shall be followed.
    In-plane instability (H1.3(a)) is checked with check_axial_flexure_interaction() using Mcx for yielding.
    """
    if Mry and _ratio(Mry, Mcy) >= 0.05:
        raise ValueError("For members with Mry/Mcy >= 0.05, the provisions of Section H1.1 shall be followed.")
    axial_ratio = _ratio(Pr, Pcy)
    flexure_ratio = _ratio(Mrx, Cb * _require_positive(Mcx, "Mcx"))
    utilisation = axial_ratio * (1.5 - 0.5 * axial_ratio) + flexure_ratio**2
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pr/Pcy": axial_ratio, "Mrx/(Cb*Mcx)": flexure_ratio, "Cb": Cb},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H1.3", equation="H1-3", title="Out-of-plane buckling and lateral-torsional buckling"),
    )


# --- H2. Unsymmetric and Other Members Subjected to Flexure and Axial Force ---
def check_stress_interaction(fra: float, Fca: float, frbw: float = 0.0, Fcbw: Optional[float] = None, frbz: float = 0.0, Fcbz: Optional[float] = None) -> UtilisationCheck:
    """AISC 360-22 Section H2: |fra/Fca + frbw/Fcbw + frbz/Fcbz| <= 1.0 (H2-1) at a point of the cross section.

    Evaluated about the principal axes (w major, z minor), considering the sense of the flexural stresses at the critical
    point: pass signed stresses, e.g compression positive and tension negative. It is permitted for any shape in lieu of H1.

    Args:
        fra: Required axial stress at the point of consideration (ksi)
        Fca: Available axial stress (Chapter E or D2) (ksi)
        frbw, frbz: Required flexural stresses at the point (ksi); signed
        Fcbw, Fcbz: Available flexural stresses (Chapter F) using S for the specific location (ksi)
    """
    def _signed(demand: float, capacity: Optional[float]) -> float:
        return 0.0 if capacity is None and not demand else demand / _require_positive(capacity, "capacity")

    terms = {"fra/Fca": _signed(fra, Fca), "frbw/Fcbw": _signed(frbw, Fcbw), "frbz/Fcbz": _signed(frbz, Fcbz)}
    utilisation = abs(sum(terms.values()))
    return UtilisationCheck(
        utilisation=utilisation,
        metadata=terms,
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H2", equation="H2-1", title="Unsymmetric and other members subjected to flexure and axial force"),
    )


# --- H3. Members Subjected to Torsion and Combined Torsion, Flexure, Shear, and/or Axial Force ---
def calculate_round_hss_torsional_constant(D: float, t: float) -> float:
    """AISC 360-22 Section H3.1 (User Note): C = pi*(D - t)^2*t/2, conservatively, for round HSS."""
    return math.pi * (_require_positive(D, "D") - t) ** 2 * _require_positive(t, "t") / 2.0


def calculate_rectangular_hss_torsional_constant(B: float, H: float, t: float) -> float:
    """AISC 360-22 Section H3.1 (User Note): C = 2(B - t)(H - t)t - 4.5(4 - pi)t^3, conservatively, for rectangular HSS."""
    t = _require_positive(t, "t")
    return 2.0 * (_require_positive(B, "B") - t) * (_require_positive(H, "H") - t) * t - 4.5 * (4.0 - math.pi) * t**3


class TorsionResult(BaseModel):
    # H3.1 Round and Rectangular HSS Subjected to Torsion; limit states of torsional yielding and torsional buckling
    phi_T: float = PHI_T_TORSION # torsional resistance factor
    Tn: float # nominal torsional strength, Fcr*C, kip-in. [N-mm]; H3-1
    phi_T_Tn: float # design torsional strength, kip-in. [N-mm]
    limit_state: LimitState # TORSIONAL_YIELDING or TORSIONAL_BUCKLING
    Fcr: float # critical stress, ksi [MPa]; H3-2a, H3-2b (round) or H3-3, H3-4, H3-5 (rectangular)
    C: float # HSS torsional constant, in^3 [mm^3]
    Fy: float
    E: float = E_STEEL
    shape: Literal["round", "rectangular"] = "round"
    slenderness: float # D/t (round) or h/t (rectangular)
    L: Optional[float] = None # length of member, in. [mm]; round HSS
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_round_hss_torsion(Fy: float, C: float, D: float, t: float, L: Optional[float] = None, E: float = E_STEEL) -> TorsionResult:
    """AISC 360-22 Section H3.1(a): Round HSS in torsion, Tn = Fcr*C (H3-1).

    Fcr is the larger of 1.23E/(sqrt(L/D)*(D/t)^(5/4)) (H3-2a) and 0.60E/(D/t)^(3/2) (H3-2b), but not exceeding 0.6Fy.
    Where L is not given, H3-2a is omitted, which is conservative.
    """
    D_t = _require_positive(D, "D") / _require_positive(t, "t")
    Fcr_a = 1.23 * E / (math.sqrt(_require_positive(L, "L") / D) * D_t**1.25) if L is not None else 0.0 # H3-2a
    Fcr_b = 0.60 * E / D_t**1.5 # H3-2b
    Fcr = min(max(Fcr_a, Fcr_b), 0.6 * Fy)
    Tn = Fcr * _require_positive(C, "C")
    return TorsionResult(
        Tn=Tn, phi_T_Tn=PHI_T_TORSION * Tn, limit_state=LimitState.TORSIONAL_YIELDING if Fcr >= 0.6 * Fy else LimitState.TORSIONAL_BUCKLING,
        Fcr=Fcr, C=C, Fy=Fy, E=E, shape="round", slenderness=D_t, L=L,
        reference=Reference(code=DesignCode.AISC_360, clause="H3.1", equation="H3-1", title="Round HSS subjected to torsion"),
        metadata={"Fcr_H3-2a": Fcr_a if L is not None else None, "Fcr_H3-2b": Fcr_b},
    )


def check_rectangular_hss_torsion(Fy: float, C: float, h: float, t: float, E: float = E_STEEL) -> TorsionResult:
    """AISC 360-22 Section H3.1(b): Rectangular HSS in torsion, Tn = Fcr*C (H3-1).

    (1) h/t <= 2.45*sqrt(E/Fy): Fcr = 0.6Fy (H3-3)
    (2) 2.45*sqrt(E/Fy) < h/t <= 3.07*sqrt(E/Fy): Fcr = 0.6Fy*(2.45*sqrt(E/Fy))/(h/t) (H3-4)
    (3) 3.07*sqrt(E/Fy) < h/t <= 260: Fcr = 0.458*pi^2*E/(h/t)^2 (H3-5)

    Args:
        h: Flat width of the longer side, per B4.1b(d) (in)
    """
    h_t = _require_positive(h, "h") / _require_positive(t, "t")
    root = math.sqrt(E / Fy)
    if h_t <= 2.45 * root:
        Fcr, equation = 0.6 * Fy, "H3-3"
    elif h_t <= 3.07 * root:
        Fcr, equation = 0.6 * Fy * 2.45 * root / h_t, "H3-4"
    elif h_t <= 260.0:
        Fcr, equation = 0.458 * math.pi**2 * E / h_t**2, "H3-5"
    else:
        raise ValueError(f"H3.1(b) applies to rectangular HSS with h/t <= 260 (h/t = {h_t:.1f}).")
    Tn = Fcr * _require_positive(C, "C")
    return TorsionResult(
        Tn=Tn, phi_T_Tn=PHI_T_TORSION * Tn, limit_state=LimitState.TORSIONAL_YIELDING if equation == "H3-3" else LimitState.TORSIONAL_BUCKLING,
        Fcr=Fcr, C=C, Fy=Fy, E=E, shape="rectangular", slenderness=h_t,
        reference=Reference(code=DesignCode.AISC_360, clause="H3.1", equation=equation, title="Rectangular HSS subjected to torsion"),
    )


def hss_torsion(
    section: Optional[BaseSection] = None,
    Fy: float = 50.0,
    L: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TorsionResult:
    """AISC 360-22 Section H3.1: Design torsional strength, phi_T*Tn, of round and rectangular HSS and pipe.

    C is taken from the section database where available, otherwise from the conservative User Note expressions.

    Args:
        section: US HSS or pipe section object
        Fy: Specified minimum yield stress (ksi); default 50 ksi
        L: Length of member (in); round HSS (H3-2a)
        E: Modulus of elasticity (ksi)
        section_type, properties: Section as a plain dictionary, or property overrides
    """
    section_type_, data = _section_properties(section, section_type, properties)
    t = _require_positive(_positive_value(data, "tdes", "tnom"), "tdes")
    if section_type_ in ROUND_HSS_SECTION_TYPES:
        D = _require_positive(_positive_value(data, "OD", "D"), "OD")
        C = _positive_value(data, "C") or calculate_round_hss_torsional_constant(D, t)
        return check_round_hss_torsion(Fy, C, D, t, L, E)
    if section_type_ in RECT_HSS_SECTION_TYPES:
        Ht = _require_positive(_positive_value(data, "Ht", "H"), "Ht")
        B = _require_positive(_positive_value(data, "B"), "B")
        C = _positive_value(data, "C") or calculate_rectangular_hss_torsional_constant(B, Ht, t)
        h = max(_positive_value(data, "h_tdes"), _positive_value(data, "b_tdes")) * t or (max(Ht, B) - 3.0 * t) # flat width of the longer side
        return check_rectangular_hss_torsion(Fy, C, h, t, E)
    raise NotImplementedError(f"H3.1 torsion applies to round and rectangular HSS only, not '{section_type_.value}'; see check_non_hss_torsion().")


def check_hss_combined_torsion(
    Pr: float,
    Pc: float,
    Tr: float,
    Tc: float,
    Mrx: float = 0.0,
    Mcx: Optional[float] = None,
    Mry: float = 0.0,
    Mcy: Optional[float] = None,
    Vr: float = 0.0,
    Vc: Optional[float] = None,
    axial: Literal["compression", "tension"] = "compression",
) -> UtilisationCheck:
    """AISC 360-22 Section H3.2: HSS subjected to combined torsion, shear, flexure and axial force.

    Tr <= 0.2Tc: torsional effects may be neglected and H1 applies
    Tr > 0.2Tc: (Pr/Pc + Mrx/Mcx + Mry/Mcy) + (Vr/Vc + Tr/Tc)^2 <= 1.0 (H3-6)
    Vr/Vc shall be taken as the larger value for the x- or y-axis.

    Args:
        Pr, Pc: Required and available axial strengths (kips)
        Tr, Tc: Required and available torsional strengths (kip-in.)
        Mrx, Mcx, Mry, Mcy: Required and available flexural strengths (kip-in.)
        Vr, Vc: Required and available shear strengths (kips)
        axial: "compression" or "tension", for the H1 path
    """
    torsion_ratio = _ratio(Tr, Tc)
    if torsion_ratio <= 0.2:
        result = check_axial_flexure_interaction(Pr, Pc, Mrx, Mcx, Mry, Mcy, axial)
        return result.model_copy(update={"metadata": {**result.metadata, "Tr/Tc": torsion_ratio, "note": "Tr <= 0.2Tc; torsional effects neglected per H3.2."}})
    first = _ratio(Pr, Pc) + _ratio(Mrx, Mcx) + _ratio(Mry, Mcy)
    second = (_ratio(Vr, Vc) + torsion_ratio) ** 2
    utilisation = first + second
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pr/Pc": _ratio(Pr, Pc), "Mrx/Mcx": _ratio(Mrx, Mcx), "Mry/Mcy": _ratio(Mry, Mcy), "Vr/Vc": _ratio(Vr, Vc), "Tr/Tc": torsion_ratio},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H3.2", equation="H3-6", title="HSS subjected to combined torsion, shear, flexure and axial force"),
    )


def check_non_hss_torsion(Fy: float, fn: float = 0.0, fv: float = 0.0, Fcr: Optional[float] = None, fcr: float = 0.0) -> UtilisationCheck:
    """AISC 360-22 Section H3.3: Non-HSS members subjected to torsion and combined stress; phi_T = 0.90.

    Lowest of the limit states of yielding under normal stress, Fn = Fy (H3-7), shear yielding under shear stress,
    Fn = 0.6Fy (H3-8), and buckling, Fn = Fcr (H3-9, Fcr by analysis). Constrained local yielding is permitted adjacent to elastic areas.

    Args:
        Fy: Specified minimum yield stress (ksi)
        fn: Required normal stress (ksi), from an elastic analysis e.g AISC Design Guide 9
        fv: Required shear stress (ksi)
        Fcr: Buckling stress for the section by analysis (ksi)
        fcr: Required stress compared with the buckling stress (ksi)
    """
    ratios = {
        "yielding under normal stress (H3-7)": abs(fn) / (PHI_T_TORSION * Fy),
        "shear yielding under shear stress (H3-8)": abs(fv) / (PHI_T_TORSION * 0.6 * Fy),
    }
    if Fcr is not None:
        ratios["buckling (H3-9)"] = abs(fcr) / (PHI_T_TORSION * _require_positive(Fcr, "Fcr"))
    utilisation = max(ratios.values())
    return UtilisationCheck(
        utilisation=utilisation,
        metadata=ratios,
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H3.3", title="Non-HSS members subjected to torsion and combined stress"),
    )


# --- H4. Rupture of Flanges with Bolt Holes and Subjected to Tension ---
def check_flange_rupture_interaction(Pr: float, Pc: float, Mrx: float, Mcx: float) -> UtilisationCheck:
    """AISC 360-22 Section H4: Flange tensile rupture at bolt holes under combined axial force and major-axis flexure.

    Pr/Pc + Mrx/Mcx <= 1.0 (H4-1); each flange subjected to tension checked separately.

    Args:
        Pr: Required axial strength at the bolt holes (kips); positive in tension, negative in compression
        Pc: Available axial strength for tensile rupture of the net section at the bolt holes, phi_t*Pn per D2(b) (kips)
        Mrx: Required flexural strength at the bolt holes (kip-in.); positive for tension, negative for compression in the flange considered
        Mcx: Available flexural strength for tensile rupture of the flange per F13.1, or Mp where it does not apply (kip-in.)
    """
    utilisation = Pr / _require_positive(Pc, "Pc") + Mrx / _require_positive(Mcx, "Mcx")
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pr/Pc": Pr / Pc, "Mrx/Mcx": Mrx / Mcx},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="H4", equation="H4-1", title="Rupture of flanges with bolt holes subjected to tension"),
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.hollow import HSS_RCT

    # AISC Design Example H.1B: W14x99; 0.929
    print(check_axial_flexure_interaction(Pr=400.0, Pc=1130.0, Mrx=250.0 * 12, Mcx=642.0 * 12, Mry=80.0 * 12, Mcy=311.0 * 12).model_dump())
    # AISC Design Example H.5A: HSS6x4x1/4; phi_T*Tn = 273 kip-in.
    print(hss_torsion(section=HSS_RCT("HSS6X4X1/4"), Fy=50.0).model_dump())
    print("🐬")
