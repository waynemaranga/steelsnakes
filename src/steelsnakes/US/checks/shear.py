# G1. General Provisions
# G2. I-Shaped Members and Channels
# G3. Single Angles and Tees
# G4. Rectangular HSS, Box Sections, and Other Singly and Doubly Symmetric Members
# G5. Round HSS
# G6. Doubly Symmetric and Singly Symmetric Members Subjected to Minor-Axis Shear
# G7. Beams and Girders with Web Openings

# User Note: For cases not included in this chapter, the following sections apply:
# • H3.3 Unsymmetric sections
# • J4.2 Shear strength of connecting elements
# • J10.6 Web panel-zone shear

from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import (
    CHANNEL_SECTION_TYPES,
    I_SECTION_TYPES,
    RECT_HSS_SECTION_TYPES,
    ROUND_HSS_SECTION_TYPES,
    TEE_SECTION_TYPES,
    _positive_value,
    _require_positive,
    _section_properties,
)
from steelsnakes.US.checks.compression import DOUBLE_ANGLE_SECTION_TYPES, E_STEEL, SINGLE_ANGLE_SECTION_TYPES
from steelsnakes.US.checks.flexure import BendingAxis, _normalize_axis

PHI_V = 0.90 # G1(a); all provisions except G2.1(a)
PHI_V_ROLLED_I = 1.00 # G2.1(a); webs of rolled I-shaped members with h/tw <= 2.24*sqrt(E/Fy)


class ShearResult(BaseModel):
    # G1. General Provisions
    phi_v: float # shear resistance factor
    Vn: float # nominal shear strength, kips [N]; per G2 through G7
    phi_v_Vn: float # design shear strength, kips [N]
    limit_state: LimitState # SHEAR_YIELDING or SHEAR_BUCKLING
    Fy: float # specified minimum yield stress of the material, ksi [MPa]
    E: float = E_STEEL # modulus of elasticity, ksi [MPa]
    Aw: float # area resisting shear, in^2 [mm^2]; d*tw for webs, 2ht for HSS, bf*tf per flange for minor-axis shear
    Cv1: Optional[float] = None # web shear strength coefficient; per G2.1 for rolled shapes;
    # G2. I-Shaped Members and Channels
    Cv2: Optional[float] = None # web shear buckling strength coefficient; per G2.2 (G2-9, G2-10, G2-11)
    kv: Optional[float] = None # web plate shear buckling coefficient
    h_tw: Optional[float] = None # slenderness used for Cv; h/tw, b/t, h/t, bf/2tf or bf/tf
    a: Optional[float] = None # clear distance between transverse stiffeners, in. [mm]
    h: Optional[float] = None # clear distance between flanges less fillets (or width resisting shear), in. [mm]
    tension_field: bool = False # G2.2 or G2.3 tension field action
    # G3. Single Angles and Tees
    # G4. Rectangular HSS, Box Sections, and Other Singly and Doubly Symmetric Members
    # G5. Round HSS
    Fcr: Optional[float] = None # critical stress, ksi [MPa]; G5-2a, G5-2b
    Lv: Optional[float] = None # distance from maximum to zero shear force, in. [mm]
    # G6. Doubly Symmetric and Singly Symmetric Members Subjected to Minor-Axis Shear
    axis: BendingAxis = BendingAxis.MAJOR # MAJOR: shear in the plane of the web; MINOR: minor-axis shear
    # G7. Beams and Girders with Web Openings
    # [NO IMPLEMENTATION PLANNED] # NOTE: the effect of all web openings shall be determined; see AISC Design Guide 2
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _shear_limit_state(Cv: float) -> LimitState:
    return LimitState.SHEAR_YIELDING if Cv >= 1.0 else LimitState.SHEAR_BUCKLING


# --- G2. I-Shaped Members and Channels ---
def calculate_kv(a: Optional[float] = None, h: Optional[float] = None) -> float:
    """AISC 360-22 Section G2.1(b)(2): Web plate shear buckling coefficient, kv.

    (i) webs without transverse stiffeners: kv = 5.34
    (ii) webs with transverse stiffeners: kv = 5 + 5/(a/h)^2 (G2-5); kv = 5.34 when a/h > 3.0
    """
    if a is None:
        return 5.34
    a_h = _require_positive(a, "a") / _require_positive(h, "h")
    return 5.34 if a_h > 3.0 else 5.0 + 5.0 / a_h**2


def calculate_Cv1(h_tw: float, kv: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equations G2-3 and G2-4: Web shear strength coefficient, Cv1.

    (i) h/tw <= 1.10*sqrt(kv*E/Fy): Cv1 = 1.0 (G2-3)
    (ii) h/tw > 1.10*sqrt(kv*E/Fy): Cv1 = 1.10*sqrt(kv*E/Fy)/(h/tw) (G2-4)
    """
    limit = 1.10 * math.sqrt(kv * E / Fy)
    return 1.0 if h_tw <= limit else limit / h_tw


def calculate_Cv2(h_tw: float, kv: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equations G2-9, G2-10 and G2-11: Web shear buckling coefficient, Cv2.

    (i) h/tw <= 1.10*sqrt(kv*E/Fy): Cv2 = 1.0 (G2-9)
    (ii) 1.10*sqrt(kv*E/Fy) < h/tw <= 1.37*sqrt(kv*E/Fy): Cv2 = 1.10*sqrt(kv*E/Fy)/(h/tw) (G2-10)
    (iii) h/tw > 1.37*sqrt(kv*E/Fy): Cv2 = 1.51*kv*E/((h/tw)^2*Fy) (G2-11)
    """
    root = math.sqrt(kv * E / Fy)
    if h_tw <= 1.10 * root:
        return 1.0
    if h_tw <= 1.37 * root:
        return 1.10 * root / h_tw
    return 1.51 * kv * E / (h_tw**2 * Fy)


def check_web_shear(
    Fy: float,
    d: float,
    tw: float,
    h_tw: float,
    rolled: bool = True,
    a: Optional[float] = None,
    E: float = E_STEEL,
) -> ShearResult:
    """AISC 360-22 Section G2.1: Shear strength of webs of I-shaped members and channels, Vn = 0.6*Fy*Aw*Cv1 (G2-1).

    (a) webs of rolled I-shaped members with h/tw <= 2.24*sqrt(E/Fy): phi_v = 1.00 and Cv1 = 1.0 (G2-2)
    (b) all other I-shaped members and channels: phi_v = 0.90 and Cv1 per G2-3 or G2-4

    Args:
        Fy: Specified minimum yield stress (ksi)
        d: Overall depth (in)
        tw: Web thickness (in)
        h_tw: h/tw; h is the clear distance between flanges less the fillets (rolled) or per G2.1(b)(1)(i) (built-up)
        rolled: True for rolled I-shaped members; False for channels and built-up members
        a: Clear distance between transverse stiffeners (in); None for unstiffened webs
        E: Modulus of elasticity (ksi)
    """
    Aw = _require_positive(d, "d") * _require_positive(tw, "tw")
    h_tw = _require_positive(h_tw, "h_tw")
    h = h_tw * tw
    kv = calculate_kv(a, h)
    if rolled and h_tw <= 2.24 * math.sqrt(E / Fy):
        phi_v, Cv1, equation = PHI_V_ROLLED_I, 1.0, "G2-2"
    else:
        phi_v, Cv1 = PHI_V, calculate_Cv1(h_tw, kv, Fy, E)
        equation = "G2-3" if Cv1 >= 1.0 else "G2-4"
    Vn = 0.6 * Fy * Aw * Cv1 # G2-1
    return ShearResult(
        phi_v=phi_v, Vn=Vn, phi_v_Vn=phi_v * Vn, limit_state=_shear_limit_state(Cv1), Fy=Fy, E=E, Aw=Aw, Cv1=Cv1,
        kv=kv, h_tw=h_tw, a=a, h=h,
        reference=Reference(code=DesignCode.AISC_360, clause="G2.1", equation=equation, title="Shear strength of webs"),
    )


def check_tension_field_shear(
    Fy: float,
    d: float,
    tw: float,
    h: float,
    a: float,
    Afc: float,
    Aft: float,
    bfc: float,
    bft: float,
    E: float = E_STEEL,
) -> ShearResult:
    """AISC 360-22 Section G2.2: Shear strength of interior web panels with a/h <= 3 considering tension field action.

    (a) h/tw <= 1.10*sqrt(kv*E/Fy): Vn = 0.6*Fy*Aw (G2-6)
    (b) h/tw > 1.10*sqrt(kv*E/Fy):
        (1) 2Aw/(Afc + Aft) <= 2.5, h/bfc <= 6.0 and h/bft <= 6.0: Vn = 0.6*Fy*Aw*[Cv2 + (1 - Cv2)/(1.15*sqrt(1 + (a/h)^2))] (G2-7)
        (2) otherwise: Vn = 0.6*Fy*Aw*[Cv2 + (1 - Cv2)/(1.15*(a/h + sqrt(1 + (a/h)^2)))] (G2-8)
    The nominal shear strength is permitted to be taken as the larger of G2.1 and G2.2.
    """
    Aw = _require_positive(d, "d") * _require_positive(tw, "tw")
    a_h = _require_positive(a, "a") / _require_positive(h, "h")
    if a_h > 3.0:
        raise ValueError("G2.2 tension field action requires a/h <= 3.")
    h_tw = h / tw
    kv = calculate_kv(a, h)
    Cv2 = calculate_Cv2(h_tw, kv, Fy, E)
    if h_tw <= 1.10 * math.sqrt(kv * E / Fy):
        Vn, equation = 0.6 * Fy * Aw, "G2-6"
    elif 2.0 * Aw / (Afc + Aft) <= 2.5 and h / bfc <= 6.0 and h / bft <= 6.0:
        Vn, equation = 0.6 * Fy * Aw * (Cv2 + (1.0 - Cv2) / (1.15 * math.sqrt(1.0 + a_h**2))), "G2-7"
    else:
        Vn, equation = 0.6 * Fy * Aw * (Cv2 + (1.0 - Cv2) / (1.15 * (a_h + math.sqrt(1.0 + a_h**2)))), "G2-8"
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fy, E=E, Aw=Aw, Cv2=Cv2, kv=kv,
        h_tw=h_tw, a=a, h=h, tension_field=equation != "G2-6",
        reference=Reference(code=DesignCode.AISC_360, clause="G2.2", equation=equation, title="Interior web panels considering tension field action"),
        metadata={"a_h": a_h, "2Aw/(Afc+Aft)": 2.0 * Aw / (Afc + Aft), "h/bfc": h / bfc, "h/bft": h / bft},
    )


def calculate_de(tw: float, Cv2: float) -> float:
    """AISC 360-22 Equations G2-14 and G2-15: de = 35*tw*(0.8 - Cv2)^2 when Cv2 <= 0.8, else 0."""
    return 35.0 * tw * (0.8 - Cv2) ** 2 if Cv2 <= 0.8 else 0.0


def calculate_beta_v(Mpf: float, Mpm: float, Mpst: float, h: float, Fyw: float, tw: float, Cv2: float) -> float:
    """AISC 360-22 Equation G2-13: beta_v = 2.8*(sqrt(Mpf + Mpm) + sqrt(Mpst + Mpm)) / (h*sqrt(Fyw*tw*(1 - Cv2))) <= 1.0.

    Args:
        Mpf: Plastic moment of the flange and a segment of web of depth de (kip-in.)
        Mpm: Smaller of Mpf and Mpst (kip-in.)
        Mpst: Plastic moment of the end stiffener plus web; see G2.3 (kip-in.)
        h: Clear distance between flanges (in)
        Fyw: Specified minimum yield stress of the web (ksi)
        tw: Web thickness (in)
        Cv2: Web shear buckling coefficient
    """
    if Cv2 >= 1.0:
        return 1.0
    return min(2.8 * (math.sqrt(Mpf + Mpm) + math.sqrt(Mpst + Mpm)) / (h * math.sqrt(Fyw * tw * (1.0 - Cv2))), 1.0)


def check_end_panel_shear(Fyw: float, d: float, tw: float, h: float, a: float, beta_v: float, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G2.3: End web panels with a/h <= 3 and equal flange areas considering tension field action.

    Vn = 0.6*Fyw*Aw*[Cv2 + beta_v*(1 - Cv2)/(1.15*sqrt(1 + (a/h)^2))] (G2-12)
    NOTE: the flexural stress in the tension flange in the end panel, alpha*Mr/Sxt, shall not exceed 0.35Fy (alpha = 1.0 for LRFD).
    NOTE: I-shaped members with unequal flange areas shall be determined by analysis.
    """
    Aw = _require_positive(d, "d") * _require_positive(tw, "tw")
    a_h = _require_positive(a, "a") / _require_positive(h, "h")
    if a_h > 3.0:
        raise ValueError("G2.3 tension field action requires a/h <= 3.")
    kv = calculate_kv(a, h)
    Cv2 = calculate_Cv2(h / tw, kv, Fyw, E)
    Vn = 0.6 * Fyw * Aw * (Cv2 + min(beta_v, 1.0) * (1.0 - Cv2) / (1.15 * math.sqrt(1.0 + a_h**2)))
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fyw, E=E, Aw=Aw, Cv2=Cv2, kv=kv,
        h_tw=h / tw, a=a, h=h, tension_field=True,
        reference=Reference(code=DesignCode.AISC_360, clause="G2.3", equation="G2-12", title="End web panels considering tension field action"),
        metadata={"beta_v": beta_v, "de": calculate_de(tw, Cv2)},
    )


def transverse_stiffeners_required(h_tw: float, Fy: float, Vu: Optional[float] = None, d: Optional[float] = None, tw: Optional[float] = None, rolled: bool = True, E: float = E_STEEL) -> bool:
    """AISC 360-22 Section G2.4(a): Transverse stiffeners are not required where h/tw <= 2.54*sqrt(E/Fy), or where the
    available shear strength per G2.1 with kv = 5.34 is greater than the required shear strength, Vu.
    """
    if h_tw <= 2.54 * math.sqrt(E / Fy):
        return False
    if Vu is not None and d is not None and tw is not None:
        return check_web_shear(Fy, d, tw, h_tw, rolled=rolled, E=E).phi_v_Vn < Vu
    return True


class TransverseStiffenerResult(BaseModel):
    # G2.4 Transverse Stiffeners
    b_t_st: float # width-to-thickness ratio of the stiffener
    b_t_limit: float # 0.56*sqrt(E/Fyst); G2-16
    Ist: float # moment of inertia of the transverse stiffeners, in^4 [mm^4]
    Ist1: float # for the full shear post-buckling resistance, in^4 [mm^4]; G2-18
    Ist2: float # for the web shear buckling resistance, in^4 [mm^4]; G2-19
    Ist_required: float # Ist2 + (Ist1 - Ist2)*rho_w; G2-17
    rho_st: float # larger of Fyw/Fyst and 1.0
    rho_w: float # maximum shear ratio, (Vr - Vc2)/(Vc1 - Vc2) >= 0
    bp: float # smaller of a and h, in. [mm]
    adequacy: Literal["OK", "FAILS"] = "OK"
    reference: Optional[Reference] = None


def check_transverse_stiffener(
    Fyw: float,
    Fyst: float,
    b_t_st: float,
    Ist: float,
    h: float,
    a: float,
    tw: float,
    Vr: Optional[float] = None,
    Vc1: Optional[float] = None,
    Vc2: Optional[float] = None,
    E: float = E_STEEL,
) -> TransverseStiffenerResult:
    """AISC 360-22 Section G2.4(d) and (e): Transverse stiffener slenderness (G2-16) and moment of inertia (G2-17 to G2-19).

    Where Vr, Vc1 and Vc2 are not given, rho_w = 1.0 i.e Ist is conservatively taken as Ist1 (User Note).

    Args:
        Fyw, Fyst: Specified minimum yield stresses of the web and stiffener (ksi)
        b_t_st: Width-to-thickness ratio of the stiffener
        Ist: Moment of inertia of the stiffener(s) about the web center (pairs) or the face in contact with the web (single) (in⁴)
        h: Clear distance between flanges (in)
        a: Clear distance between transverse stiffeners (in)
        tw: Web thickness (in)
        Vr: Required shear strength in the panel (kips)
        Vc1: Available shear strength per G2.1 or G2.2 (kips)
        Vc2: Available shear strength with Vn = 0.6*Fy*Aw*Cv2 (kips)
    """
    b_t_limit = 0.56 * math.sqrt(E / Fyst) # G2-16
    rho_st = max(Fyw / Fyst, 1.0)
    bp = min(a, h)
    Ist1 = h**4 * rho_st**1.3 / 40.0 * (Fyw / E) ** 1.5 # G2-18
    Ist2 = max((2.5 / (a / h) ** 2 - 2.0) * bp * tw**3, 0.5 * bp * tw**3) # G2-19
    if Vr is not None and Vc1 is not None and Vc2 is not None and Vc1 > Vc2:
        rho_w = max((Vr - Vc2) / (Vc1 - Vc2), 0.0)
    else:
        rho_w = 1.0
    Ist_required = Ist2 + (Ist1 - Ist2) * rho_w # G2-17
    return TransverseStiffenerResult(
        b_t_st=b_t_st, b_t_limit=b_t_limit, Ist=Ist, Ist1=Ist1, Ist2=Ist2, Ist_required=Ist_required, rho_st=rho_st, rho_w=rho_w, bp=bp,
        adequacy="OK" if (b_t_st <= b_t_limit and Ist >= Ist_required) else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="G2.4", equation="G2-17", title="Transverse stiffeners"),
    )


# --- G3. Single Angles and Tees ---
def check_single_angle_or_tee_shear(Fy: float, b: float, t: float, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G3: Single-angle leg or tee stem, Vn = 0.6*Fy*b*t*Cv2 (G3-1); Cv2 with h/tw = b/t and kv = 1.2.

    Args:
        Fy: Specified minimum yield stress (ksi)
        b: Width of the leg resisting the shear force, or depth of the tee stem (in)
        t: Thickness of the angle leg or tee stem (in)
        E: Modulus of elasticity (ksi)
    """
    Aw = _require_positive(b, "b") * _require_positive(t, "t")
    Cv2 = calculate_Cv2(b / t, 1.2, Fy, E)
    Vn = 0.6 * Fy * Aw * Cv2
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fy, E=E, Aw=Aw, Cv2=Cv2, kv=1.2, h_tw=b / t,
        reference=Reference(code=DesignCode.AISC_360, clause="G3", equation="G3-1", title="Single angles and tees"),
    )


# --- G4. Rectangular HSS, Box Sections, and Other Singly and Doubly Symmetric Members ---
def check_rectangular_hss_shear(Fy: float, h: float, t: float, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G4: Rectangular HSS and box sections, Vn = 0.6*Fy*Aw*Cv2 (G4-1); Aw = 2ht, kv = 5.

    Args:
        Fy: Specified minimum yield stress (ksi)
        h: Width resisting the shear force; clear distance between flanges less the inside corner radius on each side for HSS,
            or the clear distance between flanges for box sections. If the corner radius is unknown, the outside dimension minus 3t (in)
        t: Design wall thickness (in)
        E: Modulus of elasticity (ksi)
    """
    Aw = 2.0 * _require_positive(h, "h") * _require_positive(t, "t")
    Cv2 = calculate_Cv2(h / t, 5.0, Fy, E)
    Vn = 0.6 * Fy * Aw * Cv2
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fy, E=E, Aw=Aw, Cv2=Cv2, kv=5.0, h_tw=h / t, h=h,
        reference=Reference(code=DesignCode.AISC_360, clause="G4", equation="G4-1", title="Rectangular HSS and box sections"),
    )


def check_symmetric_member_shear(Fy: float, d: float, tw: float, h: float, n_webs: int = 1, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G4: Other singly or doubly symmetric shapes, Vn = 0.6*Fy*Aw*Cv2 (G4-1); Aw = sum of d*tw, kv = 5.

    Args:
        Fy: Specified minimum yield stress (ksi)
        d: Overall depth (in)
        tw: Web thickness (in)
        h: Width resisting the shear force; clear distance between flanges (welded) or between fastener lines (bolted) (in)
        n_webs: Number of webs
        E: Modulus of elasticity (ksi)
    """
    Aw = n_webs * _require_positive(d, "d") * _require_positive(tw, "tw")
    Cv2 = calculate_Cv2(_require_positive(h, "h") / tw, 5.0, Fy, E)
    Vn = 0.6 * Fy * Aw * Cv2
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fy, E=E, Aw=Aw, Cv2=Cv2, kv=5.0, h_tw=h / tw, h=h,
        reference=Reference(code=DesignCode.AISC_360, clause="G4", equation="G4-1", title="Other singly and doubly symmetric members"),
    )


# --- G5. Round HSS ---
def check_round_hss_shear(Fy: float, Ag: float, D: float, t: float, Lv: Optional[float] = None, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G5: Round HSS, Vn = Fcr*Ag/2 (G5-1) for shear yielding and shear buckling.

    Fcr is the larger of 1.60E/(sqrt(Lv/D)*(D/t)^(5/4)) (G5-2a) and 0.78E/(D/t)^(3/2) (G5-2b), but not exceeding 0.6Fy.
    Where Lv is not given, G5-2a is omitted, which is conservative.

    Args:
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area (in²)
        D: Outside diameter (in)
        t: Design wall thickness (in)
        Lv: Distance from maximum to zero shear force (in)
        E: Modulus of elasticity (ksi)
    """
    # NOTE: The shear buckling equations, G5-2a and G5-2b, will control for D/t over 100, high-strength steels, and long lengths.
    # NOTE: For standard sections, shear yielding will usually control and Fcr = 0.6Fy.
    D_t = _require_positive(D, "D") / _require_positive(t, "t")
    Fcr_b = 0.78 * E / D_t**1.5 # G5-2b
    Fcr_a = 1.60 * E / (math.sqrt(_require_positive(Lv, "Lv") / D) * D_t**1.25) if Lv is not None else 0.0 # G5-2a
    Fcr_buckling = max(Fcr_a, Fcr_b)
    Fcr = min(Fcr_buckling, 0.6 * Fy)
    Vn = Fcr * _require_positive(Ag, "Ag") / 2.0
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=LimitState.SHEAR_YIELDING if Fcr >= 0.6 * Fy else LimitState.SHEAR_BUCKLING,
        Fy=Fy, E=E, Aw=Ag / 2.0, Fcr=Fcr, Lv=Lv, h_tw=D_t,
        reference=Reference(code=DesignCode.AISC_360, clause="G5", equation="G5-1", title="Round HSS"),
        metadata={"Fcr_G5-2a": Fcr_a if Lv is not None else None, "Fcr_G5-2b": Fcr_b},
    )


# --- G6. Doubly Symmetric and Singly Symmetric Members Subjected to Minor-Axis Shear ---
def check_minor_axis_shear(Fy: float, bf: float, tf: float, channel: bool = False, n_elements: int = 2, E: float = E_STEEL) -> ShearResult:
    """AISC 360-22 Section G6: Minor-axis shear without torsion, Vn = 0.6*Fy*bf*tf*Cv2 (G6-1) for each shear resisting element.

    Cv2 with h/tw = bf/2tf for I-shaped members and tees, or bf/tf for channels, and kv = 1.2.
    User Note: Cv2 = 1.0 for all ASTM A6 W, S, M and HP shapes when Fy <= 70 ksi.

    Args:
        Fy: Specified minimum yield stress (ksi)
        bf: Flange width (in)
        tf: Flange thickness (in)
        channel: True for channels
        n_elements: Number of shear resisting elements (flanges); 2 for I-shapes and channels, 1 for tees
        E: Modulus of elasticity (ksi)
    """
    h_tw = _require_positive(bf, "bf") / (_require_positive(tf, "tf") * (1.0 if channel else 2.0))
    Cv2 = calculate_Cv2(h_tw, 1.2, Fy, E)
    Aw = n_elements * bf * tf
    Vn = 0.6 * Fy * Aw * Cv2
    return ShearResult(
        phi_v=PHI_V, Vn=Vn, phi_v_Vn=PHI_V * Vn, limit_state=_shear_limit_state(Cv2), Fy=Fy, E=E, Aw=Aw, Cv2=Cv2, kv=1.2, h_tw=h_tw,
        axis=BendingAxis.MINOR,
        reference=Reference(code=DesignCode.AISC_360, clause="G6", equation="G6-1", title="Minor-axis shear"),
        metadata={"n_elements": n_elements},
    )


# --- G7. Beams and Girders with Web Openings ---
# [NO IMPLEMENTATION PLANNED]


def shear(
    section: Optional[BaseSection] = None,
    Fy: float = 50.0,
    axis: BendingAxis | str = BendingAxis.MAJOR,
    a: Optional[float] = None,
    Lv: Optional[float] = None,
    tension_field: bool = False,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ShearResult:
    """AISC 360-22 Chapter G: Design shear strength, phi_v*Vn, of a US section.

        W, S, M, HP: G2.1(a) or (b) (major axis); G2.2 with tension_field and stiffener spacing a; G6 (minor axis)
        C, MC: G2.1(b) (major axis); G6 (minor axis)
        WT, ST, MT: G3 stem (major axis); G6 flange (minor axis)
        L: G3 long leg (major axis) or short leg (minor axis); 2L: G3 for both angles, web legs (major) or flange legs (minor)
        HSS rectangular/square: G4, Aw = 2ht; HSS round, Pipe: G5

    Args:
        section: US section object
        Fy: Specified minimum yield stress (ksi); default 50 ksi
        axis: "major" (shear in the plane of the web) or "minor"
        a: Clear distance between transverse stiffeners (in); I-shapes and channels
        Lv: Distance from maximum to zero shear force (in); round HSS
        tension_field: Consider G2.2 tension field action (interior panels, a/h <= 3); the larger of G2.1 and G2.2 is taken
        E: Modulus of elasticity (ksi)
        section_type, properties: Section as a plain dictionary, or property overrides
    """
    section_type_, data = _section_properties(section, section_type, properties)
    axis_ = _normalize_axis(axis)

    def value(*keys: str) -> float:
        return _positive_value(data, *keys)

    def _require(*keys: str) -> float:
        return _require_positive(value(*keys), keys[0])

    result: ShearResult
    if section_type_ in I_SECTION_TYPES or section_type_ in CHANNEL_SECTION_TYPES:
        channel = section_type_ in CHANNEL_SECTION_TYPES
        if axis_ == BendingAxis.MINOR:
            result = check_minor_axis_shear(Fy, _require("bf"), _require("tf"), channel=channel, n_elements=2, E=E)
        else:
            d, tw, h_tw = _require("d"), _require("tw"), _require("h_tw")
            result = check_web_shear(Fy, d, tw, h_tw, rolled=not channel, a=a, E=E)
            if tension_field and a is not None and not channel:
                bf, tf = _require("bf"), _require("tf")
                field = check_tension_field_shear(Fy, d, tw, h_tw * tw, a, bf * tf, bf * tf, bf, bf, E)
                if field.phi_v_Vn > result.phi_v_Vn:
                    result = field
    elif section_type_ in TEE_SECTION_TYPES:
        if axis_ == BendingAxis.MINOR:
            result = check_minor_axis_shear(Fy, _require("bf"), _require("tf"), channel=False, n_elements=1, E=E)
        else:
            result = check_single_angle_or_tee_shear(Fy, _require("d"), _require("tw"), E)
    elif section_type_ in SINGLE_ANGLE_SECTION_TYPES:
        legs = (value("d"), value("b"))
        b = max(legs) if axis_ == BendingAxis.MAJOR else min(legs)
        result = check_single_angle_or_tee_shear(Fy, _require_positive(b, "leg"), _require("t"), E)
    elif section_type_ in DOUBLE_ANGLE_SECTION_TYPES:
        b = _require("d") if axis_ == BendingAxis.MAJOR else _require("b") # d: web (vertical) legs, b: flange legs
        single = check_single_angle_or_tee_shear(Fy, b, _require("t"), E)
        result = single.model_copy(update={"Vn": 2.0 * single.Vn, "phi_v_Vn": 2.0 * single.phi_v_Vn, "Aw": 2.0 * single.Aw, "metadata": {"n_angles": 2}})
    elif section_type_ in RECT_HSS_SECTION_TYPES:
        t = _require("tdes", "tnom")
        if axis_ == BendingAxis.MAJOR:
            h = value("h_tdes") * t or value("h") or (_require("Ht") - 3.0 * t)
        else:
            h = value("b_tdes") * t or value("b") or (_require("B") - 3.0 * t)
        result = check_rectangular_hss_shear(Fy, h, t, E)
    elif section_type_ in ROUND_HSS_SECTION_TYPES:
        result = check_round_hss_shear(Fy, _require("A"), _require("OD", "D"), _require("tdes", "tnom"), Lv, E)
    else:
        raise NotImplementedError(f"Shear is not implemented for section type '{section_type_.value}'.")

    return result.model_copy(update={"axis": axis_, "metadata": {**result.metadata, "section_type": section_type_.value}})


def shear_utilisation(Vu: float, phi_v_Vn: float) -> UtilisationCheck:
    """AISC 360-22 Section G1: Shear utilisation, Vu / phi_v*Vn (LRFD).

    Args:
        Vu: Required shear strength (kips)
        phi_v_Vn: Design shear strength (kips)
    """
    utilisation = compute_utilisation(abs(Vu), phi_v_Vn)
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Vu": Vu, "phi_v_Vn": phi_v_Vn},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="G1", title="Shear strength"),
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.beams import W_beam
    from steelsnakes.US.sections.hollow import HSS_RND

    # AISC Design Example G.1B: W24x62; phi_v*Vn = 306 kips
    print(shear(section=W_beam("W24X62")).model_dump())
    # AISC Design Example G.5: HSS16.000x0.375, Lv = 16 ft; phi_v*Vn = 232 kips
    print(shear(section=HSS_RND("HSS16.000X0.375"), Lv=192.0).model_dump())
    print("🐬")
