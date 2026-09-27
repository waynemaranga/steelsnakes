# AISC 360-22 MEMBER CHECKS (LRFD) in SI units for the US_Metric sections
# D. Design of Members for Tension
# E. Design of Members for Compression
# F. Design of Members for Flexure
# G. Design of Members for Shear
# H. Design of Members for Combined Forces and Torsion
# C. Design for Stability; Appendices 7 and 8
# NOTE: the equations of steelsnakes.US.checks are dimensionally consistent, so they are reused here with N, mm and MPa;
# ... forces come out in N and moments in N-mm (1 kN = 1e3 N, 1 kN-m = 1e6 N-mm). The Specification prints an SI value
# ... next to every constant it states in inches or ksi, and those constants are the only values that change; see below.
# NOTE: section-table values are converted to mm on read; see steelsnakes.US_Metric.checks.classification.metric_properties().
# NOTE: the chapter building blocks of steelsnakes.US.checks (e.g check_flexural_buckling) default to E = 29,000 ksi;
# ... call them with E=E_STEEL (and G=G_STEEL) from this module when working in MPa.
from __future__ import annotations

import math
from typing import Any, Literal, Optional, Sequence

import steelsnakes.US.checks.combined as us_combined
import steelsnakes.US.checks.compression as us_compression
import steelsnakes.US.checks.flexure as us_flexure
import steelsnakes.US.checks.shear as us_shear
import steelsnakes.US.checks.stability as us_stability
import steelsnakes.US.checks.tension as us_tension
from steelsnakes.base.checks import UtilisationCheck
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.combined import TorsionResult
from steelsnakes.US.checks.compression import CompressionResult, SINGLE_ANGLE_SECTION_TYPES
from steelsnakes.US.checks.flexure import BendingAxis, FlexureResult, _normalize_axis
from steelsnakes.US.checks.shear import ShearResult
from steelsnakes.US.checks.stability import ALPHA_LRFD
from steelsnakes.US.checks.tension import PinConnectedMemberResult, TensionResult
from steelsnakes.US_Metric.checks.classification import E_STEEL, FU_A992, FY_A992, G_STEEL, metric_properties, to_mm_units

# SI values of the constants the Specification states in inches or ksi
HOLE_ALLOWANCE = 2.0 # mm [1/16 in.]; B4.3b, added to the nominal hole dimension
PIN_BE_OFFSET = 16.0 # mm [0.63 in.]; D5.1, be = 2t + 16 mm
PIN_CLEARANCES = (1.0, 2.0) # mm [(1/32, 1/16) in.]; D5.1(b), dh - d limits for Cr = 1.0 and Cr = 0.95
EYEBAR_T_MIN = 13.0 # mm [1/2 in.]; D6.2(e), thinner eyebars need external nuts
EYEBAR_HOLE_CLEARANCE = 1.0 # mm [1/32 in.]; D6.2(c), dh <= d + 1 mm
EYEBAR_FY_LIMIT = 485.0 # MPa [70 ksi]; D6.2(d), dh <= 5t above this Fy
REDISTRIBUTION_FY_LIMIT = 450.0 # MPa [65 ksi]; Appendix 8.2, no moment redistribution above this Fy

# Commentary Table C-F10.1: beta_w (mm) for single angles, keyed by (long leg, short leg) in mm; zero for equal legs
# NOTE: beta_w is positive with the short legs in compression and negative with the long legs in compression (F10.2(1))
BETA_W_ANGLES_MM: dict[tuple[float, float], float] = {
    (203.0, 152.0): 84.1, # L8x6
    (203.0, 102.0): 139.0, # L8x4
    (178.0, 102.0): 111.0, # L7x4
    (152.0, 102.0): 79.8, # L6x4
    (152.0, 89.0): 93.7, # L6x3-1/2
    (127.0, 89.0): 61.0, # L5x3-1/2
    (127.0, 76.0): 75.9, # L5x3
    (102.0, 89.0): 22.1, # L4x3-1/2
    (102.0, 76.0): 41.9, # L4x3
    (89.0, 76.0): 22.1, # L3-1/2x3
    (89.0, 64.0): 41.1, # L3-1/2x2-1/2
    (76.0, 64.0): 21.8, # L3x2-1/2
    (76.0, 51.0): 39.6, # L3x2
    (64.0, 51.0): 21.6, # L2-1/2x2
    (64.0, 38.0): 37.8, # L2-1/2x1-1/2
}


def _properties(
    section: Optional[BaseSection],
    section_type: Optional[SectionType],
    properties: Optional[dict[str, Any]],
) -> tuple[Optional[SectionType], Optional[dict[str, Any]]]:
    """(section_type, properties in mm units) for the steelsnakes.US.checks dispatchers; plain properties keep no type."""
    if section is None and section_type is None:
        return None, to_mm_units(properties) if properties is not None else None
    return metric_properties(section, section_type, properties)


# --- B4.3 Gross and Net Area Determination ---
def calculate_net_area(
    Ag: float,
    t: float,
    hole_diameters: Sequence[float] = (),
    staggers: Sequence[tuple[float, float]] = (),
    hole_allowance: float = HOLE_ALLOWANCE,
) -> float:
    """AISC 360-22 Section B4.3b: Net area, An = Ag - Σ(dh + 2 mm)*t + Σ(s²/4g)*t (mm²).

    Args:
        Ag: Gross area (mm²)
        t: Thickness of the element containing the holes (mm)
        hole_diameters: Nominal dimension of every hole in the chain (mm); 2 mm is added to each
        staggers: (s, g) for every gage space in a diagonal or zigzag chain; pitch s and gage g (mm)
        hole_allowance: Added to each nominal hole dimension; 2 mm
    """
    return us_tension.calculate_net_area(Ag, t, hole_diameters, staggers, hole_allowance)


# --- D. Design of Members for Tension ---
def tension(
    section: Optional[BaseSection] = None,
    Fy: float = FY_A992,
    Fu: float = FU_A992,
    Ag: Optional[float] = None,
    An: Optional[float] = None,
    U: float = 1.0,
    L: Optional[float] = None,
    r: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TensionResult:
    """AISC 360-22 Section D2: Design tensile strength, phi_t*Pn (N), the lower of tensile yielding in the gross section
    (D2-1, phi_t = 0.90) and tensile rupture in the net section (D2-2, phi_t = 0.75), with Ae = An*U (D3-1).

    Args:
        section: US_Metric section; A is taken as Ag and the least of rx, ry, rz as r
        Fy: Specified minimum yield stress (MPa); default 345 MPa (ASTM A992)
        Fu: Specified minimum tensile strength (MPa); default 450 MPa (ASTM A992)
        Ag: Gross area (mm²); overrides the section value
        An: Net area (mm²), see calculate_net_area(); defaults to Ag for members without holes
        U: Shear lag factor per Table D3.1; see steelsnakes.US.checks.shear_lag_factor()
        L: Fabricated length (mm); optional, for the D1 slenderness recommendation L/r <= 300
        r: Least radius of gyration (mm); overrides the section value
        section_type: Section type when passing plain properties
        properties: Plain properties, or overrides for the section's own, in section-table units
    """
    section_type_, data = _properties(section, section_type, properties)
    return us_tension.tension(Fy=Fy, Fu=Fu, Ag=Ag, An=An, U=U, L=L, r=r, section_type=section_type_, properties=data)


def check_pin_connected_member(
    Fy: float,
    Fu: float,
    t: float,
    d: float,
    dh: float,
    a: float,
    w: Optional[float] = None,
    Ag: Optional[float] = None,
    be_actual: Optional[float] = None,
) -> PinConnectedMemberResult:
    """AISC 360-22 Section D5: Pin-connected members, with be = 2t + 16 mm and Cr from dh - d <= 1 mm (1.0) or 2 mm (0.95).

    Lowest of tensile rupture (D5-1), shear rupture (D5-2), bearing on the projected area of the pin (J7-1) and yielding
    on the gross section (D2-1); N.

    Args:
        Fy, Fu: Specified minimum yield and tensile stresses (MPa)
        t: Thickness of plate (mm)
        d: Diameter of pin (mm)
        dh: Diameter of hole (mm)
        a: Shortest distance from edge of pin hole to edge of member, parallel to the force (mm)
        w: Width of plate at the pin hole (mm)
        Ag: Gross area of the member (mm²); defaults to w*t
        be_actual: Actual distance from edge of hole to edge of part normal to the force (mm); defaults to (w - dh)/2
    """
    return us_tension.check_pin_connected_member(Fy, Fu, t, d, dh, a, w, Ag, be_actual, be_offset=PIN_BE_OFFSET, clearances=PIN_CLEARANCES)


def check_eyebar(
    Fy: float,
    Fu: float,
    t: float,
    w: float,
    d: Optional[float] = None,
    dh: Optional[float] = None,
) -> TensionResult:
    """AISC 360-22 Section D6: Eyebars; D2 with Ag of the eyebar body, its width not more than 8t, and the D6.2
    dimensional requirements in SI: t >= 13 mm, dh <= d + 1 mm and, for Fy > 485 MPa, dh <= 5t.

    Args:
        Fy, Fu: Specified minimum yield and tensile stresses (MPa)
        t: Thickness of eyebar (mm)
        w: Width of eyebar body (mm)
        d: Pin diameter (mm); optional, for D6.2(c)
        dh: Pin-hole diameter (mm); optional, for D6.2(c) and D6.2(d)
    """
    return us_tension.check_eyebar(
        Fy, Fu, t, w, d, dh, t_min=EYEBAR_T_MIN, hole_clearance=EYEBAR_HOLE_CLEARANCE, Fy_limit=EYEBAR_FY_LIMIT, units=("mm", "MPa")
    )


# --- E. Design of Members for Compression ---
def compression(
    section: Optional[BaseSection] = None,
    Fy: float = FY_A992,
    L: Optional[float] = None,
    K: float = 1.0,
    Lx: Optional[float] = None,
    Ly: Optional[float] = None,
    Lz: Optional[float] = None,
    Kx: Optional[float] = None,
    Ky: Optional[float] = None,
    Kz: Optional[float] = None,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    single_angle_method: Literal["E5", "E3"] = "E5",
    connected_leg: Literal["long", "short"] = "long",
    truss: Literal["planar", "box"] = "planar",
    a: Optional[float] = None,
    ri: Optional[float] = None,
    connectors: Literal["snug_tight", "welded", "pretensioned"] = "welded",
) -> CompressionResult:
    """AISC 360-22 Chapter E: Design compressive strength, phi_c*Pn (N), of a US_Metric section; phi_c = 0.90.

    Pn is the lowest of the limit states of Table User Note E1.1, with E7 (Pn = Fn*Ae) for slender-element sections:
        W, S, M, HP: FB (E3) about x and y, TB (E4-2)
        C, MC: FB about x and y, FTB (E4-3, x-axis of symmetry)
        WT, ST, MT, 2L: FB about x and y, FTB (E4-3, y-axis of symmetry); E6 for 2L when a and ri are given
        L: FB with the E5 effective slenderness (or E3 about the principal axes), FTB (E4) when b/t > 0.71*sqrt(E/Fy)
        HSS, Pipe: FB about x and y

    Args:
        section: US_Metric section
        Fy: Specified minimum yield stress (MPa); default 345 MPa
        L, K: Unbraced length (mm) and effective length factor, used for every axis unless overridden
        Lx, Ly, Lz, Kx, Ky, Kz: Per-axis unbraced lengths (mm) and effective length factors; z is torsional
        E, G: Moduli (MPa); 200 000 MPa and 77 200 MPa
        section_type, properties: Section as a plain dictionary, or overrides, in section-table units e.g {"J": ...} in 10³ mm⁴
        single_angle_method: "E5" (loaded through one leg) or "E3" (concentric, principal axes)
        connected_leg, truss: E5 options
        a, ri, connectors: E6 options for double angles; connector spacing and component minimum radius of gyration (mm)
    """
    section_type_, data = metric_properties(section, section_type, properties)
    return us_compression.compression(
        Fy=Fy, L=L, K=K, Lx=Lx, Ly=Ly, Lz=Lz, Kx=Kx, Ky=Ky, Kz=Kz, E=E, G=G, section_type=section_type_, properties=data,
        single_angle_method=single_angle_method, connected_leg=connected_leg, truss=truss, a=a, ri=ri, connectors=connectors,
    )


# --- F. Design of Members for Flexure ---
def angle_beta_w(bl: float, bs: float, tolerance: float = 1.0) -> float:
    """AISC 360-22 Commentary Table C-F10.1: magnitude of beta_w (mm) for single angles; zero for equal-leg angles.

    Args:
        bl, bs: Leg lengths (mm), matched to the table within `tolerance`
        tolerance: Absolute tolerance on the leg lengths (mm)
    """
    bl, bs = max(bl, bs), min(bl, bs)
    if math.isclose(bl, bs, abs_tol=tolerance):
        return 0.0
    for (long_leg, short_leg), beta_w in BETA_W_ANGLES_MM.items():
        if math.isclose(long_leg, bl, abs_tol=tolerance) and math.isclose(short_leg, bs, abs_tol=tolerance):
            return beta_w
    raise ValueError(f"No tabulated beta_w for an L{bl:g}X{bs:g}; pass beta_w (mm) explicitly.")


def flexure(
    section: Optional[BaseSection] = None,
    Fy: float = FY_A992,
    Lb: float = 0.0,
    Cb: float = 1.0,
    axis: BendingAxis | str = BendingAxis.MAJOR,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    Fu: float = FU_A992,
    Afn: Optional[float] = None,
    stem_in_compression: bool = False,
    geometric_axis: bool = False,
    toe_in_compression: bool = True,
    restrained_at_max_moment: bool = False,
    beta_w: Optional[float] = None,
    moments: Optional[tuple[float, float, float, float]] = None,
) -> FlexureResult:
    """AISC 360-22 Chapter F: Design flexural strength, phi_b*Mn (N-mm), of a US_Metric section; phi_b = 0.90.

    Selected per Table User Note F1.1:
        W, S, M, HP major axis: F2 (compact), F3 (noncompact or slender flanges), F4 (noncompact web), F5 (slender web)
        W, S, M, HP, C, MC minor axis: F6; C, MC major axis: F2
        HSS rectangular and square: F7; HSS round, Pipe: F8
        WT, ST, MT, 2L: F9 (plane of symmetry only); L: F10 (principal axes, or a geometric axis of equal-leg angles)

    Args:
        section: US_Metric section
        Fy: Specified minimum yield stress (MPa); default 345 MPa
        Lb: Unbraced length (mm); 0 for continuous bracing
        Cb: LTB modification factor, per F1-1
        axis: "major" or "minor"; the principal axes for single angles
        E: Modulus of elasticity (MPa)
        section_type, properties: Section as a plain dictionary, or overrides, in section-table units
        Fu, Afn: Tensile strength (MPa) and net tension flange area (mm²) for F13.1 at bolt holes (I-shapes)
        stem_in_compression: Tees and double angles; stem or web legs in compression
        geometric_axis: Single equal-leg angles bent about a geometric axis (F10.2(2))
        toe_in_compression: Single angles; leg toe in compression (F10.3)
        restrained_at_max_moment: Single angles, geometric axis; lateral-torsional restraint at the maximum moment only
        beta_w: Single unequal-leg angles about the major principal axis (mm); defaults to -beta_w from Table C-F10.1, i.e
            the long leg in compression, which is conservative
        moments: (Mmax, MA, MB, MC) in the unbraced segment (N-mm); when given, Cb is calculated per F1-1
    """
    section_type_, data = metric_properties(section, section_type, properties)
    if beta_w is None and section_type_ in SINGLE_ANGLE_SECTION_TYPES and not geometric_axis and _normalize_axis(axis) == BendingAxis.MAJOR:
        legs: tuple[float, float] = (float(data.get("d", 0.0) or 0.0), float(data.get("b", 0.0) or 0.0))
        beta_w = -angle_beta_w(max(legs), min(legs)) # F10.2(1): negative w with the long leg in compression
    return us_flexure.flexure(
        Fy=Fy, Lb=Lb, Cb=Cb, axis=axis, E=E, section_type=section_type_, properties=data, Fu=Fu, Afn=Afn,
        stem_in_compression=stem_in_compression, geometric_axis=geometric_axis, toe_in_compression=toe_in_compression,
        restrained_at_max_moment=restrained_at_max_moment, beta_w=beta_w, moments=moments,
    )


# --- G. Design of Members for Shear ---
def shear(
    section: Optional[BaseSection] = None,
    Fy: float = FY_A992,
    axis: BendingAxis | str = BendingAxis.MAJOR,
    a: Optional[float] = None,
    Lv: Optional[float] = None,
    tension_field: bool = False,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ShearResult:
    """AISC 360-22 Chapter G: Design shear strength, phi_v*Vn (N), of a US_Metric section.

        W, S, M, HP: G2.1(a) (phi_v = 1.00 for h/tw <= 2.24*sqrt(E/Fy)) or G2.1(b); G2.2 with tension_field; G6 minor axis
        C, MC: G2.1(b); G6 minor axis. WT, ST, MT: G3 stem; G6 flange. L and 2L: G3. HSS: G4 (Aw = 2ht). Round HSS, Pipe: G5

    Args:
        section: US_Metric section
        Fy: Specified minimum yield stress (MPa); default 345 MPa
        axis: "major" (shear in the plane of the web) or "minor"
        a: Clear distance between transverse stiffeners (mm); I-shapes and channels
        Lv: Distance from maximum to zero shear force (mm); round HSS
        tension_field: Consider G2.2 tension field action (interior panels, a/h <= 3); the larger of G2.1 and G2.2 is taken
        E: Modulus of elasticity (MPa)
        section_type, properties: Section as a plain dictionary, or overrides, in section-table units
    """
    section_type_, data = metric_properties(section, section_type, properties)
    return us_shear.shear(Fy=Fy, axis=axis, a=a, Lv=Lv, tension_field=tension_field, E=E, section_type=section_type_, properties=data)


# --- H. Design of Members for Combined Forces and Torsion ---
def hss_torsion(
    section: Optional[BaseSection] = None,
    Fy: float = FY_A992,
    L: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TorsionResult:
    """AISC 360-22 Section H3.1: Design torsional strength, phi_T*Tn (N-mm), of round and rectangular HSS and pipe; phi_T = 0.90.

    Args:
        section: US_Metric HSS or pipe section; C is read in 10³ mm³
        Fy: Specified minimum yield stress (MPa); default 345 MPa
        L: Length of member (mm); round HSS (H3-2a)
        E: Modulus of elasticity (MPa)
        section_type, properties: Section as a plain dictionary, or overrides, in section-table units
    """
    section_type_, data = metric_properties(section, section_type, properties)
    return us_combined.hss_torsion(Fy=Fy, L=L, E=E, section_type=section_type_, properties=data)


def calculate_Pey(Iy: float, Lb: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation H1-2: Pey = pi^2*E*Iy/Lb^2 (N), for the H1.2 Cb multiplier sqrt(1 + alpha*Pr/Pey).

    Args:
        Iy: Moment of inertia about the minor axis (mm⁴)
        Lb: Unbraced length (mm)
        E: Modulus of elasticity (MPa)
    """
    return us_combined.calculate_Pey(Iy, Lb, E)


# --- C. Design for Stability; Appendices 7 and 8 ---
def calculate_Pe1(I: float, Lc1: float, E: float = E_STEEL, tau_b: float = 1.0, direct_analysis: bool = True) -> float:
    """AISC 360-22 Equation A-8-5: Pe1 = pi^2*EI*/Lc1^2 (N); EI* = 0.8*tau_b*EI for the direct analysis method.

    Args:
        I: Moment of inertia in the plane of bending (mm⁴)
        Lc1: Effective length in the plane of bending, no lateral translation (mm)
        E: Modulus of elasticity (MPa)
        tau_b: Stiffness reduction parameter, C2.3
        direct_analysis: False for the effective length and first-order analysis methods (EI* = EI)
    """
    return us_stability.calculate_Pe1(I, Lc1, E, tau_b, direct_analysis)


def check_first_order_method(
    drift_ratio: float,
    column_Pr: float,
    column_Pns: float,
    beam_Pr: float = 0.0,
    beam_I: Optional[float] = None,
    L: Optional[float] = None,
    alpha: float = ALPHA_LRFD,
    E: float = E_STEEL,
) -> UtilisationCheck:
    """AISC 360-22 Appendix 7.3.1: Limitations of the first-order analysis method; forces in N, beam_I in mm⁴, L in mm."""
    return us_stability.check_first_order_method(drift_ratio, column_Pr, column_Pns, beam_Pr, beam_I, L, alpha, E)


def moment_redistribution_Lm(M1: float, M2: float, ry: float, Fy: float, shape: Literal["i-shape", "box"] = "i-shape", E: float = E_STEEL) -> float:
    """AISC 360-22 Equations A-8-9 and A-8-10: Limiting unbraced length Lm (mm) for moment redistribution; Fy <= 450 MPa.

    Args:
        M1, M2: Smaller and larger end moments; M1/M2 positive in reverse curvature
        ry: Radius of gyration about the minor axis (mm)
        Fy: Specified minimum yield stress (MPa)
        shape: "i-shape" (A-8-9) or "box" for rectangular bars, rectangular HSS and symmetric boxes (A-8-10)
        E: Modulus of elasticity (MPa)
    """
    return us_stability.moment_redistribution_Lm(M1, M2, ry, Fy, shape, E, Fy_limit=REDISTRIBUTION_FY_LIMIT)


if __name__ == "__main__":
    from steelsnakes.US_Metric.sections.beams import W
    from steelsnakes.US_Metric.sections.hollow import HSS_RCT

    # 🌟 - W360X134 (W14X90), AISC Design Example E.1D in SI: Lcx = 9.14 m, Lcy = Lcz = 4.57 m; phi_c*Pn = 927 kips = 4 120 kN
    column = W("W360X134")
    print(compression(column, Lx=9144.0, Ly=4572.0, Lz=4572.0).model_dump(exclude={"checks"}))
    # W460X74 (W18X50), AISC Design Example F.1-2B: Lb = 3.57 m, Cb = 1.01; Mn = 4 060 kip-in. = 459 kN-m
    print(flexure(W("W460X74"), Lb=11.7 * 304.8, Cb=1.01).model_dump())
    print(shear(W("W610X92")).model_dump())
    print(hss_torsion(HSS_RCT("HSS152.4X101.6X6.4")).model_dump())
    print("🐬")
