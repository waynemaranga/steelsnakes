# F1. General Provisions
# F2. Doubly Symmetric Compact I-Shaped Members and Channels Bent About Their Major Axis
# F3. Doubly Symmetric I-Shaped Members with Compact Webs and Noncompact or Slender Flanges Bent About Their Major Axis
# F4. Other I-Shaped Members with Compact or Noncompact Webs Bent About Their Major Axis
# F5. Doubly Symmetric and Singly Symmetric I-Shaped Members with Slender Webs Bent About Their Major Axis
# F6. I-Shaped Members and Channels Bent About Their Minor Axis
# F7. Square and Rectangular HSS and Box Sections
# F8. Round HSS
# F9. Tees and Double Angles Loaded in the Plane of Symmetry
# F10. Single Angles
# F11. Rectangular Bars and Rounds
# F12. Unsymmetrical Shapes
# F13. Proportions of Beams and Girders

# NOTE: For cases not included in this chapter, the following sections apply:
# • Chapter G Design provisions for shear
# • H1–H3 Members subjected to biaxial flexure or to combined flexure and axial force
# • H3 Members subjected to flexure and torsion
# • Appendix 3 Members subjected to fatigue
# For guidance in determining the appropriate sections of this chapter to apply, Table User Note F1.1 may be used.
# Table User Note F1.1 (C = compact, NC = noncompact, S = slender):
# | Section | Flange    | Web       | Limit states          |
# | F2      | C         | C         | Y, LTB                |
# | F3      | NC, S     | C         | LTB, FLB              |
# | F4      | C, NC, S  | C, NC     | CFY, LTB, FLB, TFY    |
# | F5      | C, NC, S  | S         | CFY, LTB, FLB, TFY    |
# | F6      | C, NC, S  | NA        | Y, FLB                |
# | F7      | C, NC, S  | C, NC, S  | Y, FLB, WLB, LTB      |
# | F8      | NA        | NA        | Y, LB                 |
# | F9      | C, NC, S  | NA        | Y, LTB, FLB, WLB      |
# | F10     | NA        | NA        | Y, LTB, LLB           |
# | F11     | NA        | NA        | Y, LTB                |
# | F12     | NA        | NA        | All limit states      |

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import (
    CHANNEL_SECTION_TYPES,
    I_SECTION_TYPES,
    RECT_HSS_SECTION_TYPES,
    ROUND_HSS_SECTION_TYPES,
    TEE_SECTION_TYPES,
    FlexureCase,
    _positive_value,
    _require_positive,
    _section_properties,
    classify_flexure,
)
from steelsnakes.US.checks.compression import DOUBLE_ANGLE_SECTION_TYPES, E_STEEL, SINGLE_ANGLE_SECTION_TYPES, _double_angle_J

PHI_B = 0.90 # F1(a); LRFD


class BendingAxis(str, Enum):
    """Axis of bending. For single angles, MAJOR and MINOR are the principal axes w-w and z-z."""

    MAJOR = "major" # x-x
    MINOR = "minor" # y-y


def _normalize_axis(value: BendingAxis | str) -> BendingAxis:
    if isinstance(value, BendingAxis):
        return value
    aliases = {
        "major": BendingAxis.MAJOR, "x": BendingAxis.MAJOR, "x-x": BendingAxis.MAJOR, "strong": BendingAxis.MAJOR, "w": BendingAxis.MAJOR,
        "minor": BendingAxis.MINOR, "y": BendingAxis.MINOR, "y-y": BendingAxis.MINOR, "weak": BendingAxis.MINOR, "z": BendingAxis.MINOR,
    }
    axis = aliases.get(value.strip().lower().replace("_", "-"))
    if axis is None:
        raise ValueError("Unsupported axis. Use a BendingAxis value or one of: 'major', 'minor', 'x', 'y'.")
    return axis


class FlexureResult(BaseModel):
    # F1. General Provisions
    phi_b: float = PHI_B # flexural resistance factor
    Mn: float # nominal flexural strength, kip-in. [N-mm]; per F2-F13; assumes supports are restrained against rotation about longitudinal axis;
    phi_b_Mn: float # design flexural strength, kip-in. [N-mm]
    limit_state: LimitState # governing limit state
    limit_states: dict[str, float] = Field(default_factory=dict) # Mn of every limit state evaluated, kip-in. [N-mm]
    # NOTE: for singly-symmetric members in single curvature, and for all doubly symmetric members
    Cb: float = 1.0 # lateral-torsional buckling modification factor, for nonuniform BMDs when both segment ends are braced; per F1-1;
    # ... ↪ Cb = 12.5Mmax / (2.5Mmax + 3MA + 4MB + 3MC) i.e F1-1; Cb = 1.0 for cantilevers
    Mmax: Optional[float] = None # absolute value maximum moment in the unbraced segment, kip-in. [N-mm]
    MA: Optional[float] = None # absolute value moment at 1/4 unbraced segment, kip-in. [N-mm]
    MB: Optional[float] = None # absolute value moment at mid unbraced segment, kip-in. [N-mm]
    MC: Optional[float] = None # absolute value moment at 3/4 unbraced segment, kip-in. [N-mm]
    # NOTE: for doubly symmetric sections with no transverse loading between brace points, F1-1 reduces to 1.0 (uniform moment), 2.27 (equal end moments of same sign, reverse curvature) and 1.67 (one end moment zero)
    # NOTE: for singly-symmetric members subjected to reverse curvature, LTB strength shall be checked for both flanges (F1(d))
    Fy: float # specified minimum yield strength of the material, ksi [MPa]
    E: float = E_STEEL # modulus of elasticity, ksi [MPa]
    Lb: float = 0.0 # length between points braced against lateral displacement of the compression flange or against twist, in. [mm]
    axis: BendingAxis = BendingAxis.MAJOR
    section_class: Optional[SectionClass] = None # COMPACT, NONCOMPACT or SLENDER_ELEMENT per B4.1b
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _governing(states: dict[LimitState, tuple[float, str]]) -> tuple[LimitState, float, str, dict[str, float]]:
    limit_state, (Mn, equation) = min(states.items(), key=lambda item: item[1][0])
    return limit_state, Mn, equation, {state.value: value for state, (value, _) in states.items()}


def _worst(*classes: Optional[SectionClass]) -> Optional[SectionClass]:
    rank = {SectionClass.COMPACT: 1, SectionClass.NONCOMPACT: 2, SectionClass.SLENDER_ELEMENT: 3}
    present = [value for value in classes if value is not None]
    return max(present, key=lambda value: rank[value]) if present else None


def _limits(case: FlexureCase, wttr: float, Fy: float, E: float, **kwargs: float) -> tuple[float, float, SectionClass]:
    # kwargs carry the extra case inputs, e.g kc and Fl for Table B4.1b case 11
    result = classify_flexure(case, E=E, Fy=Fy, wttr=wttr, **kwargs)
    return float(result.metadata["lambda_p"]), float(result.metadata["lambda_r"]), result.section_class


def _interpolate(M_high: float, M_low: float, x: float, x_low: float, x_high: float) -> float:
    # linear transition used throughout Chapter F: M_high - (M_high - M_low)*(x - x_low)/(x_high - x_low)
    return M_high - (M_high - M_low) * (x - x_low) / (x_high - x_low)


# --- F1. General Provisions ---
def calculate_Cb(Mmax: float, MA: float, MB: float, MC: float) -> float:
    """AISC 360-22 Equation F1-1: Lateral-torsional buckling modification factor, Cb.

    Cb = 12.5*Mmax / (2.5*Mmax + 3*MA + 4*MB + 3*MC); absolute values of moments in the unbraced segment.
    Cb = 1.0 for cantilevers where warping is prevented at the support and the free end is unbraced.
    """
    Mmax, MA, MB, MC = abs(Mmax), abs(MA), abs(MB), abs(MC)
    Mmax = _require_positive(Mmax, "Mmax")
    return 12.5 * Mmax / (2.5 * Mmax + 3.0 * MA + 4.0 * MB + 3.0 * MC)


# --- F2. Doubly Symmetric Compact I-Shaped Members and Channels Bent About Their Major Axis ---
def calculate_rts(Iy: float, Cw: float, Sx: float) -> float:
    """AISC 360-22 Equation F2-7: rts^2 = sqrt(Iy*Cw)/Sx."""
    return math.sqrt(math.sqrt(_require_positive(Iy, "Iy") * _require_positive(Cw, "Cw")) / _require_positive(Sx, "Sx"))


def calculate_c(ho: Optional[float] = None, Iy: Optional[float] = None, Cw: Optional[float] = None, channel: bool = False) -> float:
    """AISC 360-22 Equation F2-8: c = 1 for doubly symmetric I-shapes (F2-8a); c = ho/2*sqrt(Iy/Cw) for channels (F2-8b)."""
    if not channel:
        return 1.0
    return _require_positive(ho, "ho") / 2.0 * math.sqrt(_require_positive(Iy, "Iy") / _require_positive(Cw, "Cw"))


def calculate_Lp(ry: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation F2-5: Limiting laterally unbraced length for yielding, Lp = 1.76*ry*sqrt(E/Fy)."""
    return 1.76 * _require_positive(ry, "ry") * math.sqrt(E / Fy)


def calculate_Lr(rts: float, J: float, c: float, Sx: float, ho: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation F2-6: Limiting unbraced length for inelastic LTB.

    Lr = 1.95*rts*E/(0.7*Fy) * sqrt(Jc/(Sx*ho) + sqrt((Jc/(Sx*ho))^2 + 6.76*(0.7*Fy/E)^2))
    """
    term = J * c / (_require_positive(Sx, "Sx") * _require_positive(ho, "ho"))
    return 1.95 * _require_positive(rts, "rts") * E / (0.7 * Fy) * math.sqrt(term + math.sqrt(term**2 + 6.76 * (0.7 * Fy / E) ** 2))


def calculate_Fcr_ltb(Lb: float, rts: float, J: float, c: float, Sx: float, ho: float, Cb: float = 1.0, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation F2-4: Critical stress for elastic LTB.

    Fcr = Cb*pi^2*E/(Lb/rts)^2 * sqrt(1 + 0.078*Jc/(Sx*ho)*(Lb/rts)^2)
    """
    # NOTE: The square root term may be conservatively taken as equal to 1.0.
    Lb_rts = _require_positive(Lb, "Lb") / _require_positive(rts, "rts")
    return Cb * math.pi**2 * E / Lb_rts**2 * math.sqrt(1.0 + 0.078 * J * c / (Sx * ho) * Lb_rts**2)


class CompactIShapeFlexureResult(FlexureResult):
    # F2. Doubly Symmetric Compact I-Shaped Members and Channels Bent About Their Major Axis
    # User NOTE: For Fy = 50 ksi, all current ASTM A6 W, S, M, C, and MC shapes except W21x48, W14x99, W14x90, W12x65, W10x12, W8x31, W8x10, W6x15, W6x9, W6x8.5, and M4x6 have compact flanges
    # User NOTE: For Fy <= 70 ksi, all current ASTM A6 W, S, M, HP, C, and MC shapes have compact webs
    # Mn: nominal flexural strength per F2-1 or F2-2 or F2-3; minimum per yielding (plastic moment) and LTB;
    Mp: float # plastic moment, kip-in. [N-mm] per F2-1; Mp = Zx*Fy
    Zx: float # plastic section modulus about the major axis, in^3 [mm^3]
    Sx: float # elastic section modulus about the major axis, in^3 [mm^3]
    Lp: float # limiting laterally unbraced length for yielding, in. (mm) per F2-5 i.e Lp = 1.76*ry*sqrt(E/Fy)
    Lr: float # limiting laterally unbraced length for inelastic LTB, in. (mm) per F2-6
    Fcr: Optional[float] = None # critical stress for lateral-torsional buckling, ksi [MPa], per F2-4
    ho: float # distance between the centroids of the flanges, in. (mm)
    ry: float # radius of gyration about the y-axis, in. (mm)
    rts: float # effective radius of gyration, in. (mm); rts^2 = (Iy*Cw)^0.5 / Sx, per F2-7;
    J: float # torsional constant, in^4 [mm^4]
    c_coeff: float # per F2-8


def _ltb_F2(Fy: float, Mp: float, Sx: float, ry: float, rts: float, J: float, ho: float, Lb: float, Cb: float, c: float, E: float) -> tuple[Optional[tuple[float, str]], float, float, Optional[float]]:
    Lp = calculate_Lp(ry, Fy, E)
    Lr = calculate_Lr(rts, J, c, Sx, ho, Fy, E)
    if Lb <= Lp:
        return None, Lp, Lr, None # (a) LTB does not apply
    if Lb <= Lr:
        return (min(Cb * _interpolate(Mp, 0.7 * Fy * Sx, Lb, Lp, Lr), Mp), "F2-2"), Lp, Lr, None
    Fcr = calculate_Fcr_ltb(Lb, rts, J, c, Sx, ho, Cb, E)
    return (min(Fcr * Sx, Mp), "F2-3"), Lp, Lr, Fcr


def check_compact_i_shape_flexure(
    Fy: float,
    Zx: float,
    Sx: float,
    ry: float,
    rts: float,
    J: float,
    ho: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    c: float = 1.0,
    E: float = E_STEEL,
) -> CompactIShapeFlexureResult:
    """AISC 360-22 Section F2: Doubly symmetric compact I-shaped members and channels bent about their major axis.

    Mn is the lower of yielding, Mp = Fy*Zx (F2-1), and lateral-torsional buckling (F2-2, F2-3).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Zx, Sx: Plastic and elastic section moduli about the x-axis (in³)
        ry: Radius of gyration about the y-axis (in)
        rts: Effective radius of gyration (in), per F2-7
        J: Torsional constant (in⁴)
        ho: Distance between flange centroids (in)
        Lb: Unbraced length (in); 0 for continuous bracing
        Cb: LTB modification factor, per F1-1
        c: 1.0 for doubly symmetric I-shapes, per F2-8b for channels
        E: Modulus of elasticity (ksi)
    """
    Mp = Fy * _require_positive(Zx, "Zx")
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F2-1")}
    ltb, Lp, Lr, Fcr = _ltb_F2(Fy, Mp, _require_positive(Sx, "Sx"), ry, rts, J, ho, Lb, Cb, c, E)
    if ltb is not None:
        states[LimitState.LATERAL_TORSIONAL_BUCKLING] = ltb
    limit_state, Mn, equation, limit_states = _governing(states)
    return CompactIShapeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=SectionClass.COMPACT, Mp=Mp, Zx=Zx, Sx=Sx, Lp=Lp, Lr=Lr, Fcr=Fcr, ho=ho, ry=ry, rts=rts, J=J, c_coeff=c,
        reference=Reference(code=DesignCode.AISC_360, clause="F2", equation=equation, title="Doubly symmetric compact I-shaped members and channels bent about their major axis"),
    )


# --- F3. Doubly Symmetric I-Shaped Members with Compact Webs and Noncompact or Slender Flanges Bent About Their Major Axis ---
def calculate_kc(h_tw: float) -> float:
    """kc = 4/sqrt(h/tw), not less than 0.35 nor greater than 0.76 for calculation purposes (F3, F4, F5)."""
    return max(0.35, min(4.0 / math.sqrt(_require_positive(h_tw, "h/tw")), 0.76))


class NoncompactFlangeIShapeFlexureResult(CompactIShapeFlexureResult):
    # F3. Doubly Symmetric I-Shaped Members with Compact Webs and Noncompact or Slender Flanges Bent About Their Major Axis
    # User Note: W21x48, W14x99, W14x90, W12x65, W10x12, W8x31, W8x10, W6x15, W6x9, W6x8.5, and M4x6 have noncompact flanges for Fy = 50 ksi
    lambda_f: float # bf/2tf
    lambda_pf: float # per Table B4.1b case 10
    lambda_rf: float # per Table B4.1b case 10
    kc: float # 4/sqrt(h/tw), 0.35 <= kc <= 0.76


def check_noncompact_flange_i_shape_flexure(
    Fy: float,
    Zx: float,
    Sx: float,
    ry: float,
    rts: float,
    J: float,
    ho: float,
    bf_2tf: float,
    h_tw: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    E: float = E_STEEL,
) -> NoncompactFlangeIShapeFlexureResult:
    """AISC 360-22 Section F3: Doubly symmetric I-shaped members with compact webs and noncompact or slender flanges.

    Mn is the lower of lateral-torsional buckling (F2.2) and compression flange local buckling:
        noncompact flanges: Mn = Mp - (Mp - 0.7*Fy*Sx)*(lambda - lambda_pf)/(lambda_rf - lambda_pf) (F3-1)
        slender flanges: Mn = 0.9*E*kc*Sx/lambda^2 (F3-2)
    """
    Mp = Fy * _require_positive(Zx, "Zx")
    Sx = _require_positive(Sx, "Sx")
    lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_10, bf_2tf, Fy, E)
    kc = calculate_kc(h_tw)
    states: dict[LimitState, tuple[float, str]] = {}
    ltb, Lp, Lr, Fcr = _ltb_F2(Fy, Mp, Sx, ry, rts, J, ho, Lb, Cb, 1.0, E) # F3.1: LTB per F2.2
    if ltb is not None:
        states[LimitState.LATERAL_TORSIONAL_BUCKLING] = ltb
    match flange_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (_interpolate(Mp, 0.7 * Fy * Sx, bf_2tf, lambda_pf, lambda_rf), "F3-1")
        case SectionClass.SLENDER_ELEMENT:
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (0.9 * E * kc * Sx / bf_2tf**2, "F3-2")
        case _:
            states[LimitState.PLASTIC_MOMENT_YIELDING] = (Mp, "F2-1") # compact flange; F2 governs
    limit_state, Mn, equation, limit_states = _governing(states)
    return NoncompactFlangeIShapeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=flange_class, Mp=Mp, Zx=Zx, Sx=Sx, Lp=Lp, Lr=Lr, Fcr=Fcr, ho=ho, ry=ry, rts=rts, J=J, c_coeff=1.0,
        lambda_f=bf_2tf, lambda_pf=lambda_pf, lambda_rf=lambda_rf, kc=kc,
        reference=Reference(code=DesignCode.AISC_360, clause="F3", equation=equation, title="I-shaped members with compact webs and noncompact or slender flanges"),
    )


# --- F4. Other I-Shaped Members with Compact or Noncompact Webs Bent About Their Major Axis ---
# NOTE: preferrably designed conservatively to F5.
def calculate_rt(bfc: float, tfc: float, hc: float, tw: float) -> tuple[float, float]:
    """AISC 360-22 Equations F4-11 and F4-12: rt = bfc/sqrt(12*(1 + aw/6)), aw = hc*tw/(bfc*tfc).

    Returns:
        (rt, aw)
    """
    aw = _require_positive(hc, "hc") * _require_positive(tw, "tw") / (_require_positive(bfc, "bfc") * _require_positive(tfc, "tfc"))
    return bfc / math.sqrt(12.0 * (1.0 + aw / 6.0)), aw


def calculate_singly_symmetric_web_lambda_p(hc: float, hp: float, Mp: float, My: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Table B4.1b case 16: lambda_p = (hc/hp)*sqrt(E/Fy) / (0.54*Mp/My - 0.09)^2 <= lambda_r = 5.70*sqrt(E/Fy)."""
    lambda_p = (hc / _require_positive(hp, "hp")) * math.sqrt(E / Fy) / (0.54 * Mp / My - 0.09) ** 2
    return min(lambda_p, 5.70 * math.sqrt(E / Fy))


def _web_plastification_factor(Mp: float, My: float, lambda_w: float, lambda_pw: float, lambda_rw: float, Iyc_Iy: float) -> float:
    # F4-9a, F4-9b, F4-10 (Rpc with Myc) and F4-16a, F4-16b, F4-17 (Rpt with Myt)
    if Iyc_Iy <= 0.23:
        return 1.0
    if lambda_w <= lambda_pw:
        return Mp / My
    return min(Mp / My - (Mp / My - 1.0) * (lambda_w - lambda_pw) / (lambda_rw - lambda_pw), Mp / My)


class NoncompactWebIShapeFlexureResult(FlexureResult):
    # F4. Other I-Shaped Members with Compact or Noncompact Webs Bent About Their Major Axis
    Mp: float # FyZx <= 1.6FySx, kip-in. [N-mm]
    Myc: float # yield moment in the compression flange, FySxc, kip-in. [N-mm]; F4-4
    Myt: float # yield moment in the tension flange, FySxt, kip-in. [N-mm]
    Sxc: float # elastic section modulus referred to compression flange, in^3 [mm^3]
    Sxt: float # elastic section modulus referred to tension flange, in^3 [mm^3]
    Rpc: float # web plastification factor; F4-9a, F4-9b, F4-10
    Rpt: float # web plastification factor for tension flange yielding; F4-16a, F4-16b, F4-17
    FL: float # nominal compression flange stress above which inelastic buckling limit states apply, ksi [MPa]; F4-6a, F4-6b
    rt: float # effective radius of gyration for LTB, in. [mm]; F4-11
    aw: float # hc*tw/(bfc*tfc); F4-12
    hc: float # twice the distance from centroid to inside face of compression flange less fillet, in. [mm]
    Lp: float # F4-7
    Lr: float # F4-8
    Fcr: Optional[float] = None # F4-5, ksi [MPa]
    lambda_w: float # hc/tw
    lambda_pw: float
    lambda_rw: float
    lambda_f: float # bfc/2tfc
    lambda_pf: float
    lambda_rf: float


def check_noncompact_web_i_shape_flexure(
    Fy: float,
    Zx: float,
    Sxc: float,
    Sxt: float,
    Iy: float,
    Iyc: float,
    J: float,
    ho: float,
    hc: float,
    tw: float,
    bfc: float,
    tfc: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    h_tw: Optional[float] = None,
    Sx: Optional[float] = None,
    lambda_pw: Optional[float] = None,
    lambda_rw: Optional[float] = None,
    built_up: bool = False,
    E: float = E_STEEL,
) -> NoncompactWebIShapeFlexureResult:
    """AISC 360-22 Section F4: Other I-shaped members with compact or noncompact webs bent about their major axis.

    Mn is the lowest of compression flange yielding (F4-1), LTB (F4-2, F4-3), compression flange local buckling
    (F4-13, F4-14) and tension flange yielding (F4-15).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Zx: Plastic section modulus (in³)
        Sxc, Sxt: Elastic section moduli referred to the compression and tension flanges (in³)
        Iy, Iyc: Moments of inertia of the section and of the compression flange about the y-axis (in⁴)
        J: Torsional constant (in⁴); taken as zero when Iyc/Iy <= 0.23
        ho: Distance between flange centroids (in)
        hc: Twice the distance from the centroid to the inside face of the compression flange less the fillet (in)
        tw: Web thickness (in)
        bfc, tfc: Compression flange width and thickness (in)
        Lb, Cb: Unbraced length (in) and LTB modification factor
        h_tw: h/tw for kc; defaults to hc/tw
        Sx: Elastic section modulus for the Mp limit; defaults to min(Sxc, Sxt)
        lambda_pw, lambda_rw: Web limits; default to Table B4.1b case 15 (doubly symmetric). Use case 16 for singly symmetric.
        built_up: True for built-up I-shapes; the flange limits are then Table B4.1b case 11 (kc, FL), else case 10 (rolled)
        E: Modulus of elasticity (ksi)
    """
    Sxc = _require_positive(Sxc, "Sxc")
    Sxt = _require_positive(Sxt, "Sxt")
    Sx = Sx if Sx is not None else min(Sxc, Sxt)
    Mp = min(Fy * _require_positive(Zx, "Zx"), 1.6 * Fy * Sx)
    Myc = Fy * Sxc # F4-4
    Myt = Fy * Sxt
    Iyc_Iy = _require_positive(Iyc, "Iyc") / _require_positive(Iy, "Iy")
    lambda_w = hc / _require_positive(tw, "tw")
    lambda_pw = lambda_pw if lambda_pw is not None else 3.76 * math.sqrt(E / Fy)
    lambda_rw = lambda_rw if lambda_rw is not None else 5.70 * math.sqrt(E / Fy)
    Rpc = _web_plastification_factor(Mp, Myc, lambda_w, lambda_pw, lambda_rw, Iyc_Iy)
    Rpt = _web_plastification_factor(Mp, Myt, lambda_w, lambda_pw, lambda_rw, Iyc_Iy)
    FL = 0.7 * Fy if Sxt / Sxc >= 0.7 else max(Fy * Sxt / Sxc, 0.5 * Fy) # F4-6a, F4-6b
    rt, aw = calculate_rt(bfc, tfc, hc, tw)
    J_ltb = 0.0 if Iyc_Iy <= 0.23 else J # For Iyc/Iy <= 0.23, J shall be taken as zero

    states: dict[LimitState, tuple[float, str]] = {LimitState.COMPRESSION_FLANGE_YIELDING: (Rpc * Myc, "F4-1")}
    # F4.2 Lateral-torsional buckling
    Lp = 1.1 * rt * math.sqrt(E / Fy) # F4-7
    term = J_ltb / (Sxc * _require_positive(ho, "ho"))
    Lr = 1.95 * rt * E / FL * math.sqrt(term + math.sqrt(term**2 + 6.76 * (FL / E) ** 2)) # F4-8
    Fcr: Optional[float] = None
    if Lb > Lp:
        if Lb <= Lr:
            states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Cb * _interpolate(Rpc * Myc, FL * Sxc, Lb, Lp, Lr), Rpc * Myc), "F4-2")
        else:
            Fcr = Cb * math.pi**2 * E / (Lb / rt) ** 2 * math.sqrt(1.0 + 0.078 * term * (Lb / rt) ** 2) # F4-5
            states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Fcr * Sxc, Rpc * Myc), "F4-3")
    # F4.3 Compression flange local buckling; lambda_pf, lambda_rf per Table B4.1b, case 10 (rolled) or 11 (built-up)
    lambda_f = bfc / (2.0 * tfc)
    kc = calculate_kc(h_tw if h_tw is not None else lambda_w)
    if built_up:
        lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_11, lambda_f, Fy, E, kc=kc, Fl=FL)
    else:
        lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_10, lambda_f, Fy, E)
    match flange_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (_interpolate(Rpc * Myc, FL * Sxc, lambda_f, lambda_pf, lambda_rf), "F4-13")
        case SectionClass.SLENDER_ELEMENT:
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (0.9 * E * kc * Sxc / lambda_f**2, "F4-14")
    # F4.4 Tension flange yielding
    if Sxt < Sxc:
        states[LimitState.TENSION_FLANGE_YIELDING] = (Rpt * Myt, "F4-15")

    web_class = SectionClass.COMPACT if lambda_w <= lambda_pw else (SectionClass.NONCOMPACT if lambda_w <= lambda_rw else SectionClass.SLENDER_ELEMENT)
    limit_state, Mn, equation, limit_states = _governing(states)
    return NoncompactWebIShapeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=_worst(web_class, flange_class), Mp=Mp, Myc=Myc, Myt=Myt, Sxc=Sxc, Sxt=Sxt, Rpc=Rpc, Rpt=Rpt, FL=FL,
        rt=rt, aw=aw, hc=hc, Lp=Lp, Lr=Lr, Fcr=Fcr, lambda_w=lambda_w, lambda_pw=lambda_pw, lambda_rw=lambda_rw,
        lambda_f=lambda_f, lambda_pf=lambda_pf, lambda_rf=lambda_rf,
        reference=Reference(code=DesignCode.AISC_360, clause="F4", equation=equation, title="Other I-shaped members with compact or noncompact webs"),
        metadata={"Iyc_Iy": Iyc_Iy, "kc": kc, "built_up": built_up},
    )


# --- F5. Doubly Symmetric and Singly Symmetric I-Shaped Members with Slender Webs Bent About Their Major Axis ---
def calculate_Rpg(aw: float, hc_tw: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation F5-6: Bending strength reduction factor.

    Rpg = 1 - aw/(1200 + 300*aw) * (hc/tw - 5.7*sqrt(E/Fy)) <= 1.0; aw per F4-12 but not exceeding 10
    """
    aw = min(aw, 10.0)
    return min(1.0 - aw / (1200.0 + 300.0 * aw) * (hc_tw - 5.7 * math.sqrt(E / Fy)), 1.0)


class SlenderWebIShapeFlexureResult(FlexureResult):
    # F5. Doubly Symmetric and Singly Symmetric I-Shaped Members with Slender Webs Bent About Their Major Axis
    Rpg: float # bending strength reduction factor; F5-6
    aw: float # F4-12, not exceeding 10 for Rpg
    rt: float # F4-11
    Sxc: float
    Sxt: float
    Lp: float # F4-7
    Lr: float # F5-5
    Fcr_ltb: Optional[float] = None # F5-3, F5-4
    Fcr_flb: Optional[float] = None # F5-8, F5-9
    lambda_f: float # bfc/2tfc
    lambda_pf: float
    lambda_rf: float


def check_slender_web_i_shape_flexure(
    Fy: float,
    Sxc: float,
    Sxt: float,
    hc: float,
    tw: float,
    bfc: float,
    tfc: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    h_tw: Optional[float] = None,
    built_up: bool = False,
    E: float = E_STEEL,
) -> SlenderWebIShapeFlexureResult:
    """AISC 360-22 Section F5: I-shaped members with slender webs bent about their major axis.

    Mn is the lowest of compression flange yielding (F5-1), LTB (F5-2), compression flange local buckling (F5-7) and
    tension flange yielding (F5-10).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Sxc, Sxt: Elastic section moduli referred to the compression and tension flanges (in³)
        hc: Twice the distance from the centroid to the inside face of the compression flange (in)
        tw: Web thickness (in)
        bfc, tfc: Compression flange width and thickness (in)
        Lb, Cb: Unbraced length (in) and LTB modification factor
        h_tw: h/tw for kc; defaults to hc/tw
        built_up: True for built-up I-shapes (plate girders); the flange limits are then Table B4.1b case 11 with
            FL = 0.7Fy (slender web, footnote [b]), else case 10 (rolled)
        E: Modulus of elasticity (ksi)
    """
    Sxc = _require_positive(Sxc, "Sxc")
    Sxt = _require_positive(Sxt, "Sxt")
    hc_tw = _require_positive(hc, "hc") / _require_positive(tw, "tw")
    rt, aw = calculate_rt(bfc, tfc, hc, tw)
    Rpg = calculate_Rpg(aw, hc_tw, Fy, E)
    states: dict[LimitState, tuple[float, str]] = {LimitState.COMPRESSION_FLANGE_YIELDING: (Rpg * Fy * Sxc, "F5-1")}

    # F5.2 Lateral-torsional buckling
    Lp = 1.1 * rt * math.sqrt(E / Fy) # F4-7
    Lr = math.pi * rt * math.sqrt(E / (0.7 * Fy)) # F5-5
    Fcr_ltb: Optional[float] = None
    if Lb > Lp:
        if Lb <= Lr:
            Fcr_ltb, equation = min(Cb * (Fy - 0.3 * Fy * (Lb - Lp) / (Lr - Lp)), Fy), "F5-3"
        else:
            Fcr_ltb, equation = min(Cb * math.pi**2 * E / (Lb / rt) ** 2, Fy), "F5-4"
        states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (Rpg * Fcr_ltb * Sxc, equation)

    # F5.3 Compression flange local buckling; lambda_pf, lambda_rf per Table B4.1b, case 10 (rolled) or 11 (built-up)
    lambda_f = bfc / (2.0 * tfc)
    kc = calculate_kc(h_tw if h_tw is not None else hc_tw)
    if built_up:
        lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_11, lambda_f, Fy, E, kc=kc, Fl=0.7 * Fy)
    else:
        lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_10, lambda_f, Fy, E)
    Fcr_flb: Optional[float] = None
    match flange_class:
        case SectionClass.NONCOMPACT:
            Fcr_flb = Fy - 0.3 * Fy * (lambda_f - lambda_pf) / (lambda_rf - lambda_pf) # F5-8
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (Rpg * Fcr_flb * Sxc, "F5-8")
        case SectionClass.SLENDER_ELEMENT:
            Fcr_flb = 0.9 * E * kc / lambda_f**2 # F5-9
            states[LimitState.COMPRESSION_FLANGE_LOCAL_BUCKLING] = (Rpg * Fcr_flb * Sxc, "F5-9")
    # F5.4 Tension flange yielding
    if Sxt < Sxc:
        states[LimitState.TENSION_FLANGE_YIELDING] = (Fy * Sxt, "F5-10")

    limit_state, Mn, equation, limit_states = _governing(states)
    return SlenderWebIShapeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=SectionClass.SLENDER_ELEMENT, Rpg=Rpg, aw=aw, rt=rt, Sxc=Sxc, Sxt=Sxt, Lp=Lp, Lr=Lr,
        Fcr_ltb=Fcr_ltb, Fcr_flb=Fcr_flb, lambda_f=lambda_f, lambda_pf=lambda_pf, lambda_rf=lambda_rf,
        reference=Reference(code=DesignCode.AISC_360, clause="F5", equation=equation, title="I-shaped members with slender webs"),
        metadata={"hc_tw": hc_tw, "flange_class": flange_class.value, "kc": kc, "built_up": built_up},
    )


# --- F6. I-Shaped Members and Channels Bent About Their Minor Axis ---
class MinorAxisFlexureResult(FlexureResult):
    # F6. I-Shaped Members and Channels Bent About Their Minor Axis
    Mp: float # FyZy <= 1.6FySy, kip-in. [N-mm]; F6-1
    Zy: float # plastic section modulus about the y-axis, in^3 [mm^3]
    Sy: float # elastic section modulus about the y-axis, in^3 [mm^3]
    lambda_f: float # b/tf; b = bf/2 for I-shapes, bf for channels
    lambda_pf: float # Table B4.1b case 13
    lambda_rf: float
    Fcr: Optional[float] = None # 0.7E/(b/tf)^2, F6-4


def check_minor_axis_flexure(Fy: float, Zy: float, Sy: float, b: float, tf: float, E: float = E_STEEL) -> MinorAxisFlexureResult:
    """AISC 360-22 Section F6: I-shaped members and channels bent about their minor axis.

    Mn is the lower of yielding, Mp = Fy*Zy <= 1.6*Fy*Sy (F6-1), and flange local buckling (F6-2, F6-3).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Zy, Sy: Plastic and elastic section moduli about the y-axis (in³)
        b: Half the full flange width, bf/2, for I-shapes; the full nominal flange dimension for channels (in)
        tf: Flange thickness (in)
        E: Modulus of elasticity (ksi)
    """
    Sy = _require_positive(Sy, "Sy")
    Mp = min(Fy * _require_positive(Zy, "Zy"), 1.6 * Fy * Sy)
    lambda_f = _require_positive(b, "b") / _require_positive(tf, "tf")
    lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_13, lambda_f, Fy, E)
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F6-1")}
    Fcr: Optional[float] = None
    match flange_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.FLANGE_LOCAL_BUCKLING] = (_interpolate(Mp, 0.7 * Fy * Sy, lambda_f, lambda_pf, lambda_rf), "F6-2")
        case SectionClass.SLENDER_ELEMENT:
            Fcr = 0.7 * E / lambda_f**2 # F6-4
            states[LimitState.FLANGE_LOCAL_BUCKLING] = (Fcr * Sy, "F6-3")
    limit_state, Mn, equation, limit_states = _governing(states)
    return MinorAxisFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Fy=Fy, E=E, axis=BendingAxis.MINOR,
        section_class=flange_class, Mp=Mp, Zy=Zy, Sy=Sy, lambda_f=lambda_f, lambda_pf=lambda_pf, lambda_rf=lambda_rf, Fcr=Fcr,
        reference=Reference(code=DesignCode.AISC_360, clause="F6", equation=equation, title="I-shaped members and channels bent about their minor axis"),
    )


# --- F7. Square and Rectangular HSS and Box Sections ---
def calculate_hss_effective_width(b: float, tf: float, Fy: float, E: float = E_STEEL, box: bool = False) -> float:
    """AISC 360-22 Equations F7-4 (HSS) and F7-5 (box): Effective width of a slender compression flange.

    be = 1.92*tf*sqrt(E/Fy)*(1 - k/(b/tf)*sqrt(E/Fy)) <= b; k = 0.38 for HSS and 0.34 for box sections
    """
    k = 0.34 if box else 0.38
    b_tf = _require_positive(b, "b") / _require_positive(tf, "tf")
    return min(1.92 * tf * math.sqrt(E / Fy) * (1.0 - k / b_tf * math.sqrt(E / Fy)), b)


def calculate_effective_section_modulus(I: float, A: float, depth: float, t: float, b: float, be: float) -> float:
    """Effective section modulus, Se, to the compression fibre with the ineffective width (b - be) of the compression flange removed.

    The neutral axis shift is accounted for; the ineffective strip of thickness t is centred t/2 inside the compression face.

    Args:
        I: Moment of inertia about the axis of bending (in⁴)
        A: Gross area (in²)
        depth: Overall depth perpendicular to the axis of bending (in)
        t: Compression flange thickness (in)
        b: Flange width (in)
        be: Effective flange width (in)
    """
    removed = (b - be) * t
    if removed <= 0.0:
        return I / (depth / 2.0)
    y_removed = depth / 2.0 - t / 2.0
    I_0 = I - removed * y_removed**2 - (b - be) * t**3 / 12.0 # about the original centroid
    A_eff = A - removed
    shift = removed * y_removed / A_eff # neutral axis moves away from the compression flange
    I_eff = I_0 - A_eff * shift**2
    return I_eff / (depth / 2.0 + shift)


class RectangularHSSFlexureResult(FlexureResult):
    # F7. Square and Rectangular HSS and Box Sections
    Mp: float # FyZ, kip-in. [N-mm]; F7-1
    Z: float # plastic section modulus about the axis of bending, in^3 [mm^3]
    S: float # elastic section modulus about the axis of bending, in^3 [mm^3]
    Se: Optional[float] = None # effective section modulus, slender flanges, in^3 [mm^3]; F7-3
    be: Optional[float] = None # effective width of compression flange, in. [mm]; F7-4, F7-5
    lambda_f: float # b/tf
    lambda_pf: float
    lambda_rf: float
    lambda_w: float # h/tw
    lambda_pw: float
    lambda_rw: float
    Rpg: Optional[float] = None # F5-6 with aw = 2htw/(btf); F7-7
    Lp: Optional[float] = None # F7-10
    Lr: Optional[float] = None # F7-11


def check_rectangular_hss_flexure(
    Fy: float,
    Z: float,
    S: float,
    b: float,
    h: float,
    t: float,
    I: Optional[float] = None,
    A: Optional[float] = None,
    depth: Optional[float] = None,
    tw: Optional[float] = None,
    Lb: float = 0.0,
    Cb: float = 1.0,
    ry: Optional[float] = None,
    J: Optional[float] = None,
    box: bool = False,
    ltb: bool = True,
    axis: BendingAxis | str = BendingAxis.MAJOR,
    E: float = E_STEEL,
) -> RectangularHSSFlexureResult:
    """AISC 360-22 Section F7: Square and rectangular HSS and box sections bent about either axis.

    Mn is the lowest of yielding (F7-1), flange local buckling (F7-2, F7-3), web local buckling (F7-6, F7-7) and
    lateral-torsional buckling (F7-8, F7-9).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Z, S: Plastic and elastic section moduli about the axis of bending (in³)
        b: Width of the compression flange per B4.1b; for HSS, the flat width (in)
        h: Depth of web per B4.1b; for HSS, the flat depth (in)
        t: Design wall thickness (flange thickness for box sections) (in)
        I, A, depth: Moment of inertia (in⁴), gross area (in²) and overall depth (in) for Se of slender flanges
        tw: Web thickness for box sections (in); defaults to t
        Lb, Cb: Unbraced length (in) and LTB modification factor
        ry, J: Radius of gyration about the minor axis (in) and torsional constant (in⁴) for LTB
        box: True for box sections (F7-5, Table B4.1b case 21)
        ltb: False where LTB does not apply i.e square sections and minor-axis bending
        axis: Axis of bending, for reporting
        E: Modulus of elasticity (ksi)
    """
    tf = _require_positive(t, "t")
    tw = tw if tw is not None else tf
    S = _require_positive(S, "S")
    Mp = Fy * _require_positive(Z, "Z") # F7-1
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F7-1")}

    # F7.2 Flange local buckling
    lambda_f = _require_positive(b, "b") / tf
    lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_21 if box else FlexureCase.CASE_17, lambda_f, Fy, E)
    Se: Optional[float] = None
    be: Optional[float] = None
    match flange_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.FLANGE_LOCAL_BUCKLING] = (min(_interpolate(Mp, Fy * S, lambda_f, lambda_pf, lambda_rf), Mp), "F7-2")
        case SectionClass.SLENDER_ELEMENT:
            be = calculate_hss_effective_width(b, tf, Fy, E, box)
            Se = calculate_effective_section_modulus(_require_positive(I, "I"), _require_positive(A, "A"), _require_positive(depth, "depth"), tf, b, be)
            states[LimitState.FLANGE_LOCAL_BUCKLING] = (Fy * Se, "F7-3")

    # F7.3 Web local buckling
    lambda_w = _require_positive(h, "h") / tw
    lambda_pw, lambda_rw, web_class = _limits(FlexureCase.CASE_19, lambda_w, Fy, E)
    Rpg: Optional[float] = None
    match web_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.WEB_LOCAL_BUCKLING] = (min(_interpolate(Mp, Fy * S, lambda_w, lambda_pw, lambda_rw), Mp), "F7-6")
        case SectionClass.SLENDER_ELEMENT:
            # User Note: There are no HSS with slender webs; box sections with slender webs and slender flanges are not addressed
            if flange_class == SectionClass.SLENDER_ELEMENT:
                raise NotImplementedError("Box sections with slender webs and slender flanges are not addressed in AISC 360-22 F7.")
            Rpg = calculate_Rpg(2.0 * h * tw / (b * tf), lambda_w, Fy, E)
            states[LimitState.WEB_LOCAL_BUCKLING] = (Rpg * Fy * S, "F7-7")

    # F7.4 Lateral-torsional buckling; will not occur in square sections or sections bending about their minor axis
    Lp: Optional[float] = None
    Lr: Optional[float] = None
    if ltb and ry and J and A:
        root_JA = math.sqrt(J * A)
        Lp = 0.13 * E * ry * root_JA / Mp # F7-10
        Lr = 2.0 * E * ry * root_JA / (0.7 * Fy * S) # F7-11
        if Lb > Lp:
            if Lb <= Lr:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Cb * _interpolate(Mp, 0.7 * Fy * S, Lb, Lp, Lr), Mp), "F7-8")
            else:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(2.0 * E * Cb * root_JA / (Lb / ry), Mp), "F7-9")

    limit_state, Mn, equation, limit_states = _governing(states)
    return RectangularHSSFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb, axis=_normalize_axis(axis),
        section_class=_worst(flange_class, web_class), Mp=Mp, Z=Z, S=S, Se=Se, be=be, lambda_f=lambda_f, lambda_pf=lambda_pf,
        lambda_rf=lambda_rf, lambda_w=lambda_w, lambda_pw=lambda_pw, lambda_rw=lambda_rw, Rpg=Rpg, Lp=Lp, Lr=Lr,
        reference=Reference(code=DesignCode.AISC_360, clause="F7", equation=equation, title="Square and rectangular HSS and box sections"),
    )


# --- F8. Round HSS ---
class RoundHSSFlexureResult(FlexureResult):
    # F8. Round HSS; applies to D/t < 0.45E/Fy
    Mp: float # FyZ, kip-in. [N-mm]; F8-1
    Z: float
    S: float
    D_t: float # D/t
    lambda_p: float # 0.07E/Fy, Table B4.1b case 20
    lambda_r: float # 0.31E/Fy
    Fcr: Optional[float] = None # 0.33E/(D/t), F8-4


def check_round_hss_flexure(Fy: float, Z: float, S: float, D: float, t: float, E: float = E_STEEL) -> RoundHSSFlexureResult:
    """AISC 360-22 Section F8: Round HSS, lower of yielding (F8-1) and local buckling (F8-2, F8-3).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Z, S: Plastic and elastic section moduli (in³)
        D: Outside diameter (in)
        t: Design wall thickness (in)
        E: Modulus of elasticity (ksi)
    """
    D_t = _require_positive(D, "D") / _require_positive(t, "t")
    if D_t >= 0.45 * E / Fy:
        raise ValueError(f"F8 applies to round HSS with D/t < 0.45E/Fy (D/t = {D_t:.1f}).")
    S = _require_positive(S, "S")
    Mp = Fy * _require_positive(Z, "Z")
    lambda_p, lambda_r, wall_class = _limits(FlexureCase.CASE_20, D_t, Fy, E)
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F8-1")}
    Fcr: Optional[float] = None
    match wall_class:
        case SectionClass.NONCOMPACT:
            states[LimitState.LOCAL_BUCKLING] = ((0.021 * E / D_t + Fy) * S, "F8-2")
        case SectionClass.SLENDER_ELEMENT:
            Fcr = 0.33 * E / D_t # F8-4
            states[LimitState.LOCAL_BUCKLING] = (Fcr * S, "F8-3")
    limit_state, Mn, equation, limit_states = _governing(states)
    return RoundHSSFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Fy=Fy, E=E,
        section_class=wall_class, Mp=Mp, Z=Z, S=S, D_t=D_t, lambda_p=lambda_p, lambda_r=lambda_r, Fcr=Fcr,
        reference=Reference(code=DesignCode.AISC_360, clause="F8", equation=equation, title="Round HSS"),
    )


# --- F9. Tees and Double Angles Loaded in the Plane of Symmetry ---
def _tee_ltb_Mcr(E: float, Lb: float, Iy: float, J: float, d: float, stem_in_compression: bool) -> tuple[float, float]:
    # F9-10 with B per F9-11 (stem/web legs in tension) or F9-12 (in compression)
    B = (-1.0 if stem_in_compression else 1.0) * 2.3 * (d / Lb) * math.sqrt(Iy / J)
    return 1.95 * E / Lb * math.sqrt(Iy * J) * (B + math.sqrt(1.0 + B**2)), B


def _single_angle_ltb(My: float, Mcr: float) -> tuple[float, str]:
    # F10-2 and F10-3
    if My / Mcr <= 1.0:
        return min((1.92 - 1.17 * math.sqrt(My / Mcr)) * My, 1.5 * My), "F10-2"
    return (0.92 - 0.17 * Mcr / My) * Mcr, "F10-3"


def _leg_local_buckling(Fy: float, Sc: float, b_t: float, E: float) -> tuple[Optional[tuple[float, str]], SectionClass]:
    # F10.3 Leg local buckling; Table B4.1b case 12
    _, _, leg_class = _limits(FlexureCase.CASE_12, b_t, Fy, E)
    match leg_class:
        case SectionClass.NONCOMPACT:
            return (Fy * Sc * (2.43 - 1.72 * b_t * math.sqrt(Fy / E)), "F10-6"), leg_class
        case SectionClass.SLENDER_ELEMENT:
            return (0.71 * E / b_t**2 * Sc, "F10-7"), leg_class # Fcr per F10-8
    return None, leg_class


class TeeFlexureResult(FlexureResult):
    # F9. Tees and Double Angles Loaded in the Plane of Symmetry
    shape: Literal["tee", "double_angle"] = "tee"
    stem_in_compression: bool = False # stem (web legs) in compression anywhere along the unbraced length
    Mp: float # F9-2, F9-4 or F9-5, kip-in. [N-mm]
    My: float # FySx, kip-in. [N-mm]; F9-3
    Sxc: Optional[float] = None # elastic section modulus referred to the compression flange, in^3 [mm^3]
    Lp: Optional[float] = None # F9-8
    Lr: Optional[float] = None # F9-9
    Mcr: Optional[float] = None # F9-10
    B: Optional[float] = None # F9-11 or F9-12
    Fcr_stem: Optional[float] = None # F9-17, F9-18 or F9-19


def check_tee_flexure(
    Fy: float,
    Zx: float,
    Sx: float,
    Ix: float,
    y: float,
    Iy: float,
    J: float,
    d: float,
    tw: float,
    bf: float,
    tf: float,
    ry: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    stem_in_compression: bool = False,
    E: float = E_STEEL,
) -> TeeFlexureResult:
    """AISC 360-22 Section F9: Tees loaded in the plane of symmetry.

    Mn is the lowest of yielding (F9-1), LTB (F9.2), flange local buckling (F9.3, stem in tension) and local buckling
    of the tee stem (F9.4, stem in compression).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Zx, Sx: Plastic and elastic (to the stem tip) section moduli (in³)
        Ix: Moment of inertia about the x-axis (in⁴); for Sxc = Ix/y
        y: Distance from the outside of the flange to the centroid (in)
        Iy: Moment of inertia about the y-axis (in⁴)
        J: Torsional constant (in⁴)
        d: Depth of the tee (in)
        tw, bf, tf: Stem thickness, flange width and flange thickness (in)
        ry: Radius of gyration about the y-axis (in)
        Lb: Unbraced length (in); 0 for continuous bracing
        Cb: Not used by F9; retained for reporting
        stem_in_compression: True if the stem is in compression anywhere along the unbraced length
        E: Modulus of elasticity (ksi)
    """
    Sx = _require_positive(Sx, "Sx")
    My = Fy * Sx # F9-3
    if stem_in_compression:
        Mp, yield_equation = My, "F9-4"
    else:
        Mp, yield_equation = min(Fy * _require_positive(Zx, "Zx"), 1.6 * My), "F9-2"
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, yield_equation)}

    # F9.2 Lateral-torsional buckling
    Lp: Optional[float] = None
    Lr: Optional[float] = None
    Mcr: Optional[float] = None
    B: Optional[float] = None
    if Lb > 0.0:
        J = _require_positive(J, "J")
        Iy = _require_positive(Iy, "Iy")
        Mcr, B = _tee_ltb_Mcr(E, Lb, Iy, J, d, stem_in_compression)
        if stem_in_compression:
            states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Mcr, My), "F9-13")
        else:
            Lp = 1.76 * _require_positive(ry, "ry") * math.sqrt(E / Fy) # F9-8
            Lr = 1.95 * (E / Fy) * math.sqrt(Iy * J) / Sx * math.sqrt(2.36 * (Fy / E) * d * Sx / J + 1.0) # F9-9
            if Lp < Lb <= Lr:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (_interpolate(Mp, My, Lb, Lp, Lr), "F9-6")
            elif Lb > Lr:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (Mcr, "F9-7")

    Sxc = _require_positive(Ix, "Ix") / _require_positive(y, "y")
    lambda_f = _require_positive(bf, "bf") / (2.0 * _require_positive(tf, "tf"))
    lambda_pf, lambda_rf, flange_class = _limits(FlexureCase.CASE_10, lambda_f, Fy, E)
    d_tw = _require_positive(d, "d") / _require_positive(tw, "tw")
    _, _, stem_class = _limits(FlexureCase.CASE_14, d_tw, Fy, E)
    Fcr_stem: Optional[float] = None
    if not stem_in_compression:
        # F9.3(a) Flange local buckling of tees; flange in flexural compression
        match flange_class:
            case SectionClass.NONCOMPACT:
                states[LimitState.FLANGE_LOCAL_BUCKLING] = (min(_interpolate(Mp, 0.7 * Fy * Sxc, lambda_f, lambda_pf, lambda_rf), 1.6 * My), "F9-14")
            case SectionClass.SLENDER_ELEMENT:
                states[LimitState.FLANGE_LOCAL_BUCKLING] = (0.7 * E * Sxc / lambda_f**2, "F9-15")
        section_class = flange_class
    else:
        # F9.4(a) Local buckling of tee stems in flexural compression
        if d_tw <= 0.84 * math.sqrt(E / Fy):
            Fcr_stem, equation = Fy, "F9-17"
        elif d_tw <= 1.52 * math.sqrt(E / Fy):
            Fcr_stem, equation = (1.43 - 0.515 * d_tw * math.sqrt(Fy / E)) * Fy, "F9-18"
        else:
            Fcr_stem, equation = 1.52 * E / d_tw**2, "F9-19"
        states[LimitState.LOCAL_BUCKLING] = (Fcr_stem * Sx, equation) # F9-16
        section_class = stem_class

    limit_state, Mn, equation, limit_states = _governing(states)
    return TeeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=section_class, shape="tee", stem_in_compression=stem_in_compression, Mp=Mp, My=My, Sxc=Sxc,
        Lp=Lp, Lr=Lr, Mcr=Mcr, B=B, Fcr_stem=Fcr_stem,
        reference=Reference(code=DesignCode.AISC_360, clause="F9", equation=equation, title="Tees loaded in the plane of symmetry"),
        metadata={"lambda_f": lambda_f, "d_tw": d_tw},
    )


def check_double_angle_flexure(
    Fy: float,
    Zx: float,
    Sx: float,
    Ix: float,
    y: float,
    Iy: float,
    J: float,
    d: float,
    b: float,
    t: float,
    ry: float,
    Lb: float = 0.0,
    Cb: float = 1.0,
    web_legs_in_compression: bool = False,
    E: float = E_STEEL,
) -> TeeFlexureResult:
    """AISC 360-22 Section F9: Double angles loaded in the plane of symmetry.

    Mn is the lowest of yielding (F9-2 or F9-5), LTB (F9.2; F10-2/F10-3 for web legs in compression) and leg local
    buckling per F10.3 (flange legs in compression, Sc = Ix/y; or web legs in compression, Sc = Sx).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Zx, Sx: Plastic and elastic (to the web leg tips) section moduli (in³)
        Ix: Moment of inertia about the x-axis (in⁴)
        y: Distance from the back of the flange legs to the centroid (in)
        Iy: Moment of inertia about the y-axis (in⁴)
        J: Torsional constant of both angles (in⁴)
        d: Width of the web (vertical) legs (in)
        b: Width of the flange (horizontal) legs (in)
        t: Leg thickness (in)
        ry: Radius of gyration about the y-axis (in)
        Lb: Unbraced length (in); 0 for continuous bracing
        Cb: Not used by F9; retained for reporting
        web_legs_in_compression: True if the web legs are in compression anywhere along the unbraced length
        E: Modulus of elasticity (ksi)
    """
    Sx = _require_positive(Sx, "Sx")
    t = _require_positive(t, "t")
    My = Fy * Sx # F9-3
    if web_legs_in_compression:
        Mp, yield_equation = 1.5 * My, "F9-5"
    else:
        Mp, yield_equation = min(Fy * _require_positive(Zx, "Zx"), 1.6 * My), "F9-2"
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, yield_equation)}

    Lp: Optional[float] = None
    Lr: Optional[float] = None
    Mcr: Optional[float] = None
    B: Optional[float] = None
    if Lb > 0.0:
        J = _require_positive(J, "J")
        Iy = _require_positive(Iy, "Iy")
        Mcr, B = _tee_ltb_Mcr(E, Lb, Iy, J, d, web_legs_in_compression)
        if web_legs_in_compression:
            states[LimitState.LATERAL_TORSIONAL_BUCKLING] = _single_angle_ltb(My, Mcr) # F9.2(b)(2)
        else:
            Lp = 1.76 * _require_positive(ry, "ry") * math.sqrt(E / Fy) # F9-8
            Lr = 1.95 * (E / Fy) * math.sqrt(Iy * J) / Sx * math.sqrt(2.36 * (Fy / E) * d * Sx / J + 1.0) # F9-9
            if Lp < Lb <= Lr:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (_interpolate(Mp, My, Lb, Lp, Lr), "F9-6")
            elif Lb > Lr:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (Mcr, "F9-7")

    if web_legs_in_compression:
        Sc, b_t = Sx, d / t # F9.4(b): Sc taken as the elastic section modulus
    else:
        Sc, b_t = _require_positive(Ix, "Ix") / _require_positive(y, "y"), b / t # F9.3(b): Sc referred to the compression flange
    llb, leg_class = _leg_local_buckling(Fy, Sc, b_t, E)
    if llb is not None:
        states[LimitState.LEG_LOCAL_BUCKLING] = llb

    limit_state, Mn, equation, limit_states = _governing(states)
    return TeeFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        section_class=leg_class, shape="double_angle", stem_in_compression=web_legs_in_compression, Mp=Mp, My=My, Sxc=Sc,
        Lp=Lp, Lr=Lr, Mcr=Mcr, B=B,
        reference=Reference(code=DesignCode.AISC_360, clause="F9", equation=equation, title="Double angles loaded in the plane of symmetry"),
        metadata={"b_t": b_t},
    )


# --- F10. Single Angles ---
# Table C-F10.1: beta_w values for angles (Commentary), keyed by (long leg, short leg) in inches; zero for equal legs.
# beta_w is positive with short legs in compression and negative with long legs in compression.
BETA_W_ANGLES: dict[tuple[float, float], float] = {
    (8.0, 6.0): 3.31,
    (8.0, 4.0): 5.48,
    (7.0, 4.0): 4.37,
    (6.0, 4.0): 3.14,
    (6.0, 3.5): 3.69,
    (5.0, 3.5): 2.40,
    (5.0, 3.0): 2.99,
    (4.0, 3.5): 0.87,
    (4.0, 3.0): 1.65,
    (3.5, 3.0): 0.87,
    (3.5, 2.5): 1.62,
    (3.0, 2.5): 0.86,
    (3.0, 2.0): 1.56,
    (2.5, 2.0): 0.85,
    (2.5, 1.5): 1.49,
}


def angle_beta_w(bl: float, bs: float, tolerance: float = 0.05) -> float:
    """AISC 360-22 Commentary Table C-F10.1: magnitude of beta_w (in.) for single angles; zero for equal-leg angles.

    Args:
        bl, bs: Leg lengths (in); matched to the table within `tolerance`, so soft-converted metric legs e.g 203 mm = 7.99 in. find L8
        tolerance: Absolute tolerance on the leg lengths (in)
    """
    bl, bs = max(bl, bs), min(bl, bs)
    if math.isclose(bl, bs, abs_tol=tolerance):
        return 0.0
    for (long_leg, short_leg), beta_w in BETA_W_ANGLES.items():
        if math.isclose(long_leg, bl, abs_tol=tolerance) and math.isclose(short_leg, bs, abs_tol=tolerance):
            return beta_w
    raise ValueError(f"No tabulated beta_w for an L{bl}x{bs}; pass beta_w explicitly.")


class SingleAngleFlexureResult(FlexureResult):
    # F10. Single Angles
    angle_axis: Literal["major", "minor", "geometric"] = "major" # principal w-w, principal z-z, or geometric x-x (equal-leg)
    My: float # yield moment, kip-in. [N-mm]
    My_ltb: Optional[float] = None # yield moment used for LTB; 0.8My for geometric-axis bending without LTB restraint
    Mcr: Optional[float] = None # elastic LTB moment, kip-in. [N-mm]; F10-4, F10-5a, F10-5b
    Sc: Optional[float] = None # elastic section modulus to the toe in compression, in^3 [mm^3]
    b_t: float # leg width-to-thickness ratio
    beta_w: float = 0.0 # section property for single angles about major principal axis, in. [mm]


def check_single_angle_flexure(
    Fy: float,
    S: float,
    b: float,
    t: float,
    angle_axis: Literal["major", "minor", "geometric"] = "major",
    Sc: Optional[float] = None,
    Lb: float = 0.0,
    Cb: float = 1.0,
    Ag: Optional[float] = None,
    rz: Optional[float] = None,
    beta_w: float = 0.0,
    toe_in_compression: bool = True,
    restrained_at_max_moment: bool = False,
    E: float = E_STEEL,
) -> SingleAngleFlexureResult:
    """AISC 360-22 Section F10: Single angles; lowest of yielding (F10-1), LTB (F10-2, F10-3) and leg local buckling (F10.3).

    Args:
        Fy: Specified minimum yield stress (ksi)
        S: Elastic section modulus for the yield moment about the axis of bending (in³); the geometric section modulus for geometric-axis bending
        b: Full width of the leg in compression (in)
        t: Leg thickness (in)
        angle_axis: "major" (principal w), "minor" (principal z; no LTB) or "geometric" (equal-leg angle, no axial compression)
        Sc: Elastic section modulus to the toe in compression (in³); defaults to S, or 0.8S for geometric-axis bending without LTB restraint
        Lb: Laterally unbraced length (in); 0 for continuous lateral-torsional restraint
        Cb: LTB modification factor; not more than 1.5 for principal-axis bending
        Ag, rz: Gross area (in²) and minor principal radius of gyration (in); F10-4
        beta_w: Section property about major principal axis (in); + short legs in compression, - long legs in compression, 0 equal legs
        toe_in_compression: False where the leg toe is in tension, so leg local buckling does not apply
        restrained_at_max_moment: Geometric-axis bending with lateral-torsional restraint at the point of maximum moment only
        E: Modulus of elasticity (ksi)
    """
    S = _require_positive(S, "S")
    b_t = _require_positive(b, "b") / _require_positive(t, "t")
    My = Fy * S
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (1.5 * My, "F10-1")}

    # F10.2 Lateral-torsional buckling; for bending about the minor principal axis, only yielding and LLB apply
    Mcr: Optional[float] = None
    My_ltb: Optional[float] = None
    if angle_axis != "minor" and Lb > 0.0:
        match angle_axis:
            case "major":
                Cb = min(Cb, 1.5)
                term = 4.4 * beta_w * _require_positive(rz, "rz") / (Lb * t)
                Mcr = 9.0 * E * _require_positive(Ag, "Ag") * rz * t * Cb / (8.0 * Lb) * (math.sqrt(1.0 + term**2) + term) # F10-4
                My_ltb = My
            case "geometric":
                sign = -1.0 if toe_in_compression else 1.0 # F10-5a with maximum compression at the toe, F10-5b with maximum tension at the toe
                Mcr = 0.58 * E * b**4 * t * Cb / Lb**2 * (math.sqrt(1.0 + 0.88 * (Lb * t / b**2) ** 2) + sign)
                if restrained_at_max_moment:
                    Mcr, My_ltb = 1.25 * Mcr, My # (ii) restraint at the point of maximum moment only
                else:
                    My_ltb = 0.80 * My # (i) no lateral-torsional restraint
            case _:
                raise ValueError("angle_axis must be 'major', 'minor' or 'geometric'.")
        states[LimitState.LATERAL_TORSIONAL_BUCKLING] = _single_angle_ltb(My_ltb, Mcr)

    # F10.3 Leg local buckling; applies when the toe of the leg is in compression
    if Sc is None:
        Sc = 0.80 * S if (angle_axis == "geometric" and not restrained_at_max_moment) else S
    llb, leg_class = _leg_local_buckling(Fy, Sc, b_t, E)
    if toe_in_compression and llb is not None:
        states[LimitState.LEG_LOCAL_BUCKLING] = llb

    limit_state, Mn, equation, limit_states = _governing(states)
    return SingleAngleFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb,
        axis=BendingAxis.MINOR if angle_axis == "minor" else BendingAxis.MAJOR, section_class=leg_class,
        angle_axis=angle_axis, My=My, My_ltb=My_ltb, Mcr=Mcr, Sc=Sc if toe_in_compression else None, b_t=b_t, beta_w=beta_w,
        reference=Reference(code=DesignCode.AISC_360, clause="F10", equation=equation, title="Single angles"),
    )


# --- F11. Rectangular Bars and Rounds ---
class BarFlexureResult(FlexureResult):
    # F11. Rectangular Bars and Rounds
    shape: Literal["rectangular", "round"] = "rectangular"
    Mp: float # FyZ <= 1.5FySx (bars) or 1.6FySx (rounds), kip-in. [N-mm]; F11-1, F11-2
    Z: float
    S: float
    Lb_d_t2: Optional[float] = None # Lb*d/t^2
    Fcr: Optional[float] = None # F11-5


def check_bar_flexure(
    Fy: float,
    d: float,
    t: Optional[float] = None,
    Lb: float = 0.0,
    Cb: float = 1.0,
    shape: Literal["rectangular", "round"] = "rectangular",
    E: float = E_STEEL,
) -> BarFlexureResult:
    """AISC 360-22 Section F11: Rectangular bars bent about either geometric axis, and rounds.

    Args:
        Fy: Specified minimum yield stress (ksi)
        d: Depth of the rectangular bar in the plane of bending, or diameter of the round (in)
        t: Width of the rectangular bar parallel to the axis of bending (in)
        Lb: Unbraced length of the compression region (in)
        Cb: LTB modification factor
        shape: "rectangular" or "round"
        E: Modulus of elasticity (ksi)
    """
    d = _require_positive(d, "d")
    Lb_d_t2: Optional[float] = None
    Fcr: Optional[float] = None
    if shape == "round":
        Z, S = d**3 / 6.0, math.pi * d**3 / 32.0
        Mp = min(Fy * Z, 1.6 * Fy * S) # F11-2
        states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F11-2")}
        axis = BendingAxis.MAJOR
    else:
        t = _require_positive(t, "t")
        Z, S = t * d**2 / 4.0, t * d**2 / 6.0
        Mp = min(Fy * Z, 1.5 * Fy * S) # F11-1
        states = {LimitState.PLASTIC_MOMENT_YIELDING: (Mp, "F11-1")}
        axis = BendingAxis.MAJOR if d > t else BendingAxis.MINOR
        # F11.2 LTB; not for rectangular bars bent about their minor axis, nor Lb*d/t^2 <= 0.08E/Fy
        if d > t and Lb > 0.0:
            Lb_d_t2 = Lb * d / t**2
            if 0.08 * E / Fy < Lb_d_t2 <= 1.9 * E / Fy:
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Cb * (1.52 - 0.274 * Lb_d_t2 * Fy / E) * Fy * S, Mp), "F11-3")
            elif Lb_d_t2 > 1.9 * E / Fy:
                Fcr = 1.9 * E * Cb / Lb_d_t2 # F11-5
                states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Fcr * S, Mp), "F11-4")
    limit_state, Mn, equation, limit_states = _governing(states)
    return BarFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Cb=Cb, Fy=Fy, E=E, Lb=Lb, axis=axis,
        shape=shape, Mp=Mp, Z=Z, S=S, Lb_d_t2=Lb_d_t2, Fcr=Fcr,
        reference=Reference(code=DesignCode.AISC_360, clause="F11", equation=equation, title="Rectangular bars and rounds"),
    )


# --- F12. Unsymmetrical Shapes ---
# [NO SECTION DATABASE] # NOTE: applies to all unsymmetrical shapes except single angles; Appendix 1.3 recommended for economy
class UnsymmetricFlexureResult(FlexureResult):
    # F12. Unsymmetrical Shapes; Mn = Fn*Smin (F12-1)
    Fn: float # nominal stress, ksi [MPa]
    Smin: float # minimum elastic section modulus relative to the axis of bending, in^3 [mm^3]


def check_unsymmetric_flexure(Fy: float, Smin: float, Fcr_ltb: Optional[float] = None, Fcr_lb: Optional[float] = None, E: float = E_STEEL) -> UnsymmetricFlexureResult:
    """AISC 360-22 Section F12: Unsymmetrical shapes; Mn = Fn*Smin with Fn the lowest of Fy (F12-2), and the LTB (F12-3)
    and local buckling (F12-4) stresses determined by analysis, each not exceeding Fy.

    User Note: for Z-shaped members, Fcr for LTB is recommended as 0.5Fcr of a channel with the same flange and web properties.
    """
    Smin = _require_positive(Smin, "Smin")
    states: dict[LimitState, tuple[float, str]] = {LimitState.PLASTIC_MOMENT_YIELDING: (Fy * Smin, "F12-2")}
    if Fcr_ltb is not None:
        states[LimitState.LATERAL_TORSIONAL_BUCKLING] = (min(Fcr_ltb, Fy) * Smin, "F12-3")
    if Fcr_lb is not None:
        states[LimitState.LOCAL_BUCKLING] = (min(Fcr_lb, Fy) * Smin, "F12-4")
    limit_state, Mn, equation, limit_states = _governing(states)
    return UnsymmetricFlexureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=limit_state, limit_states=limit_states, Fy=Fy, E=E, Fn=Mn / Smin, Smin=Smin,
        reference=Reference(code=DesignCode.AISC_360, clause="F12", equation=equation, title="Unsymmetrical shapes"),
    )


# --- F13. Proportions of Beams and Girders ---
class TensionFlangeRuptureResult(FlexureResult):
    # F13.1 Strength reductions for members with bolt holes in the tension flange
    Afg: float # gross area of tension flange, in^2 [mm^2]
    Afn: float # net area of tension flange, in^2 [mm^2]
    Yt: float # 1.0 for Fy/Fu <= 0.8, 1.1 otherwise
    Fu: float


def check_tension_flange_rupture(Fy: float, Fu: float, Afg: float, Afn: float, Sx: float, E: float = E_STEEL) -> Optional[TensionFlangeRuptureResult]:
    """AISC 360-22 Section F13.1: Tensile rupture of the tension flange at bolt holes.

    (a) Fu*Afn >= Yt*Fy*Afg: the limit state does not apply; returns None
    (b) Fu*Afn < Yt*Fy*Afg: Mn <= Fu*Afn/Afg * Sx (F13-1)

    Args:
        Fy, Fu: Specified minimum yield and tensile stresses (ksi)
        Afg, Afn: Gross and net areas of the tension flange (in²), per B4.3
        Sx: Minimum elastic section modulus about the x-axis (in³)
    """
    Yt = 1.0 if Fy / Fu <= 0.8 else 1.1
    if Fu * Afn >= Yt * Fy * Afg:
        return None
    Mn = Fu * Afn / _require_positive(Afg, "Afg") * _require_positive(Sx, "Sx")
    return TensionFlangeRuptureResult(
        Mn=Mn, phi_b_Mn=PHI_B * Mn, limit_state=LimitState.TENSILE_RUPTURE, limit_states={LimitState.TENSILE_RUPTURE.value: Mn},
        Fy=Fy, E=E, Afg=Afg, Afn=Afn, Yt=Yt, Fu=Fu,
        reference=Reference(code=DesignCode.AISC_360, clause="F13.1", equation="F13-1", title="Members with bolt holes in the tension flange"),
    )


def check_i_shape_proportions(
    Fy: float,
    h_tw: float,
    Iyc: Optional[float] = None,
    Iy: Optional[float] = None,
    a_h: Optional[float] = None,
    aw: Optional[float] = None,
    slender_web: bool = False,
    E: float = E_STEEL,
) -> UtilisationCheck:
    """AISC 360-22 Section F13.2: Proportioning limits for I-shaped members.

    - singly symmetric: 0.1 <= Iyc/Iy <= 0.9 (F13-2)
    - slender webs: (h/tw)max = 12.0*sqrt(E/Fy) for a/h <= 1.5 (F13-3), 0.40E/Fy for a/h > 1.5 (F13-4)
    - unstiffened girders: h/tw <= 260; aw <= 10
    Utilisation is the largest ratio of value to limit.
    """
    ratios: dict[str, float] = {}
    if Iyc is not None and Iy is not None:
        Iyc_Iy = Iyc / _require_positive(Iy, "Iy")
        ratios["Iyc/Iy <= 0.9 (F13-2)"] = Iyc_Iy / 0.9
        ratios["Iyc/Iy >= 0.1 (F13-2)"] = 0.1 / Iyc_Iy if Iyc_Iy > 0.0 else math.inf
    if slender_web:
        if a_h is None:
            ratios["h/tw <= 260 (unstiffened)"] = h_tw / 260.0
        elif a_h <= 1.5:
            ratios["h/tw <= 12.0sqrt(E/Fy) (F13-3)"] = h_tw / (12.0 * math.sqrt(E / Fy))
        else:
            ratios["h/tw <= 0.40E/Fy (F13-4)"] = h_tw / (0.40 * E / Fy)
    elif a_h is None:
        ratios["h/tw <= 260 (unstiffened)"] = h_tw / 260.0
    if aw is not None:
        ratios["aw <= 10"] = aw / 10.0
    utilisation = max(ratios.values()) if ratios else 0.0
    return UtilisationCheck(
        utilisation=utilisation,
        metadata=ratios,
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="F13.2", title="Proportioning limits for I-shaped members"),
    )


# --- Section dispatch per Table User Note F1.1 ---
def flexure(
    section: Optional[BaseSection] = None,
    Fy: float = 50.0,
    Lb: float = 0.0,
    Cb: float = 1.0,
    axis: BendingAxis | str = BendingAxis.MAJOR,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    Fu: float = 65.0,
    Afn: Optional[float] = None,
    stem_in_compression: bool = False,
    geometric_axis: bool = False,
    toe_in_compression: bool = True,
    restrained_at_max_moment: bool = False,
    beta_w: Optional[float] = None,
    moments: Optional[tuple[float, float, float, float]] = None,
) -> FlexureResult:
    """AISC 360-22 Chapter F: Design flexural strength, phi_b*Mn, of a US section, selected per Table User Note F1.1.

        W, S, M, HP major axis: F2 (compact), F3 (noncompact/slender flanges), F4 (noncompact web), F5 (slender web)
        W, S, M, HP, C, MC minor axis: F6
        C, MC major axis: F2
        HSS rectangular/square: F7; HSS round, Pipe: F8
        WT, ST, MT, 2L: F9 (plane of symmetry only)
        L: F10 (principal axes, or geometric axis for equal-leg angles)

    Args:
        section: US section object
        Fy: Specified minimum yield stress (ksi); default 50 ksi
        Lb: Unbraced length (in); 0 for continuous bracing
        Cb: LTB modification factor, per F1-1
        axis: "major" or "minor"; principal axes for single angles
        E: Modulus of elasticity (ksi)
        section_type, properties: Section as a plain dictionary, or property overrides
        Fu, Afn: Tensile strength (ksi) and net tension flange area (in²) for F13.1 at bolt holes (I-shapes)
        stem_in_compression: Tees and double angles; stem or web legs in compression
        geometric_axis: Single equal-leg angles bent about a geometric axis (F10.2(2))
        toe_in_compression: Single angles; leg toe in compression (F10.3)
        restrained_at_max_moment: Single angles, geometric axis; lateral-torsional restraint at max moment only
        beta_w: Single unequal-leg angles about the major principal axis; defaults to -beta_w per Table C-F10.1 (long leg in compression, conservative)
        moments: (Mmax, MA, MB, MC) in the unbraced segment (kip-in.); when given, Cb is calculated per F1-1
    """
    section_type_, data = _section_properties(section, section_type, properties)
    axis_ = _normalize_axis(axis)
    if moments is not None:
        Cb = calculate_Cb(*moments)
    def value(*keys: str) -> float:
        return _positive_value(data, *keys)

    def _require(*keys: str) -> float:
        return _require_positive(value(*keys), keys[0])

    result: FlexureResult
    if section_type_ in I_SECTION_TYPES or section_type_ in CHANNEL_SECTION_TYPES:
        channel = section_type_ in CHANNEL_SECTION_TYPES
        tw, tf, bf = _require("tw"), _require("tf"), _require("bf")
        if axis_ == BendingAxis.MINOR:
            result = check_minor_axis_flexure(Fy, _require("Zy"), _require("Sy"), bf if channel else bf / 2.0, tf, E)
        else:
            h_tw = _require("h_tw")
            lambda_f = bf / tf if channel else bf / (2.0 * tf)
            _, _, web_class = _limits(FlexureCase.CASE_15, h_tw, Fy, E)
            _, _, flange_class = _limits(FlexureCase.CASE_10, lambda_f, Fy, E)
            Zx, Sx, ry, J, ho = _require("Zx"), _require("Sx"), _require("ry"), _require("J"), _require("ho")
            rts = value("rts") or calculate_rts(_require("Iy"), _require("Cw"), Sx)
            if channel:
                if web_class != SectionClass.COMPACT or flange_class != SectionClass.COMPACT:
                    raise NotImplementedError("AISC 360-22 F2 covers channels with compact webs and flanges only.")
                c = calculate_c(ho, _require("Iy"), _require("Cw"), channel=True)
                result = check_compact_i_shape_flexure(Fy, Zx, Sx, ry, rts, J, ho, Lb, Cb, c, E)
            elif web_class == SectionClass.COMPACT and flange_class == SectionClass.COMPACT:
                result = check_compact_i_shape_flexure(Fy, Zx, Sx, ry, rts, J, ho, Lb, Cb, 1.0, E)
            elif web_class == SectionClass.COMPACT:
                result = check_noncompact_flange_i_shape_flexure(Fy, Zx, Sx, ry, rts, J, ho, lambda_f, h_tw, Lb, Cb, E)
            elif web_class == SectionClass.NONCOMPACT:
                result = check_noncompact_web_i_shape_flexure(
                    Fy, Zx, Sx, Sx, _require("Iy"), _require("Iy") / 2.0, J, ho, h_tw * tw, tw, bf, tf, Lb, Cb, h_tw=h_tw, Sx=Sx, E=E
                ) # doubly symmetric: Sxc = Sxt = Sx, Iyc = Iy/2, hc = h
            else:
                result = check_slender_web_i_shape_flexure(Fy, Sx, Sx, h_tw * tw, tw, bf, tf, Lb, Cb, h_tw=h_tw, E=E)
            if Afn is not None and not channel:
                rupture = check_tension_flange_rupture(Fy, Fu, bf * tf, Afn, Sx, E)
                if rupture is not None:
                    limit_states = {**result.limit_states, LimitState.TENSILE_RUPTURE.value: rupture.Mn}
                    if rupture.Mn < result.Mn:
                        result = result.model_copy(update={"Mn": rupture.Mn, "phi_b_Mn": rupture.phi_b_Mn, "limit_state": LimitState.TENSILE_RUPTURE, "reference": rupture.reference})
                    result = result.model_copy(update={"limit_states": limit_states})

    elif section_type_ in RECT_HSS_SECTION_TYPES:
        t = _require("tdes", "tnom")
        b_flat = value("b_tdes") * t or _require("b")
        h_flat = value("h_tdes") * t or _require("h")
        if axis_ == BendingAxis.MAJOR:
            ltb = section_type_ == SectionType.HSS_RCT and value("Ht") > value("B")
            result = check_rectangular_hss_flexure(
                Fy, _require("Zx"), _require("Sx"), b_flat, h_flat, t, I=_require("Ix"), A=_require("A"), depth=_require("Ht"),
                Lb=Lb, Cb=Cb, ry=value("ry"), J=value("J"), ltb=ltb, axis=axis_, E=E,
            )
        else:
            result = check_rectangular_hss_flexure(
                Fy, _require("Zy"), _require("Sy"), h_flat, b_flat, t, I=_require("Iy"), A=_require("A"), depth=_require("B"),
                Lb=Lb, Cb=Cb, ltb=False, axis=axis_, E=E,
            ) # minor axis: the Ht walls are the flanges

    elif section_type_ in ROUND_HSS_SECTION_TYPES:
        result = check_round_hss_flexure(Fy, _require("Zx"), _require("Sx"), _require("OD", "D"), _require("tdes", "tnom"), E)

    elif section_type_ in TEE_SECTION_TYPES or section_type_ in DOUBLE_ANGLE_SECTION_TYPES:
        if axis_ != BendingAxis.MAJOR:
            raise NotImplementedError("F9 covers tees and double angles loaded in the plane of symmetry (x-axis bending) only.")
        if section_type_ in TEE_SECTION_TYPES:
            result = check_tee_flexure(
                Fy, _require("Zx"), _require("Sx"), _require("Ix"), _require("y"), _require("Iy"), value("J"), _require("d"),
                _require("tw"), _require("bf"), _require("tf"), _require("ry"), Lb, Cb, stem_in_compression, E,
            )
        else:
            J = value("J") or _double_angle_J(data)
            result = check_double_angle_flexure(
                Fy, _require("Zx"), _require("Sx"), _require("Ix"), _require("y"), _require("Iy"), J, _require("d"),
                _require("b"), _require("t"), _require("ry"), Lb, Cb, stem_in_compression, E,
            )

    elif section_type_ in SINGLE_ANGLE_SECTION_TYPES:
        t = _require("t")
        bl, bs = max(value("d"), value("b")), min(value("d"), value("b"))
        if geometric_axis:
            if not math.isclose(bl, bs):
                raise NotImplementedError("F10.2(2) geometric-axis bending is for equal-leg angles only; use principal axes.")
            S = _require("Sx") if axis_ == BendingAxis.MAJOR else _require("Sy")
            result = check_single_angle_flexure(
                Fy, S, bl, t, "geometric", Lb=Lb, Cb=Cb, toe_in_compression=toe_in_compression, restrained_at_max_moment=restrained_at_max_moment, E=E
            )
        elif axis_ == BendingAxis.MAJOR:
            S_min = min(v for v in (value("SwA"), value("SwB"), value("SwC")) if v > 0.0)
            Sc = min(v for v in (value("SwA"), value("SwC")) if v > 0.0) # toes
            beta = beta_w if beta_w is not None else -angle_beta_w(bl, bs)
            result = check_single_angle_flexure(
                Fy, S_min, bl, t, "major", Sc=Sc, Lb=Lb, Cb=Cb, Ag=_require("A"), rz=_require("rz"), beta_w=beta, toe_in_compression=True, E=E
            )
        else:
            S_min = min(v for v in (value("SzA"), value("SzB"), value("SzC")) if v > 0.0)
            Sc = min(v for v in (value("SzA"), value("SzC")) if v > 0.0) if toe_in_compression else None # toes
            result = check_single_angle_flexure(Fy, S_min, bl, t, "minor", Sc=Sc, Lb=Lb, Cb=Cb, toe_in_compression=toe_in_compression, E=E)

    else:
        raise NotImplementedError(f"Flexure is not implemented for section type '{section_type_.value}'.")

    update: dict[str, Any] = {"metadata": {**result.metadata, "section_type": section_type_.value}}
    if moments is not None:
        update.update(dict(zip(("Mmax", "MA", "MB", "MC"), (abs(moment) for moment in moments))))
    return result.model_copy(update=update)


def flexure_utilisation(Mu: float, phi_b_Mn: float) -> UtilisationCheck:
    """AISC 360-22 Section F1: Flexure utilisation, Mu / phi_b*Mn (LRFD).

    Args:
        Mu: Required flexural strength (kip-in.)
        phi_b_Mn: Design flexural strength (kip-in.)
    """
    utilisation = compute_utilisation(abs(Mu), phi_b_Mn)
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Mu": Mu, "phi_b_Mn": phi_b_Mn},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="F1", title="Flexural strength"),
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.beams import W_beam
    from steelsnakes.US.sections.hollow import HSS_RCT

    # AISC Design Example F.1-2B: W18x50, Lb = 11.7 ft, Cb = 1.01; Mn = 4,060 kip-in.
    print(flexure(section=W_beam("W18X50"), Fy=50.0, Lb=11.7 * 12, Cb=1.01).model_dump())
    # AISC Design Example F.7B: HSS10x6x3/16, Lb = 21 ft, Cb = 1.14; Mn = 796 kip-in. (FLB)
    print(flexure(section=HSS_RCT("HSS10X6X3/16"), Fy=50.0, Lb=252.0, Cb=1.14).model_dump())
    print("🐬")
