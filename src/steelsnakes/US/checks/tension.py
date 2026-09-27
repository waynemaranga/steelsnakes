# D: DESIGN OF MEMBERS FOR TENSION
# D1. Slenderness Limitations
# D2. Tensile Strength
# D3. Effective Net Area
# D4. Built-Up Members
# D5. Pin-Connected Members
# D6. Eyebars
# User Note: For cases not included in this chapter, the following sections apply:
# • B3.11 Members subjected to fatigue
# • Chapter H Members subjected to combined axial tension and flexure
# • J3 Threaded rods
# • J4.1 Connecting elements in tension
# • J4.3 Block shear rupture strength at end connections of tension members
from __future__ import annotations

import math
from enum import Enum
from fractions import Fraction
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import _positive_value, _require_positive, _section_properties

# Resistance factors (LRFD only)
PHI_T_YIELDING = 0.90 # D2(a); tensile yielding in the gross section
PHI_T_RUPTURE = 0.75 # D2(b); tensile rupture in the net section
PHI_SF = 0.75 # D5.1(b); shear rupture of pin-connected members
PHI_BEARING = 0.75 # J7; bearing on the projected area of the pin (D5.1(c))

HOLE_ALLOWANCE = 1 / 16 # in. [is 2 mm in US_Metric module]; B4.3b, added to nominal hole dimension
PIN_BE_OFFSET = 0.63 # in. [is 16 mm in US_Metric module]; D5.1, be = 2t + 0.63
PIN_CLEARANCES = (1 / 32, 1 / 16) # in. [is (1, 2) mm in US_Metric module]; D5.1(b), dh - d limits for Cr = 1.0 and Cr = 0.95
EYEBAR_T_MIN = 0.5 # in. [is 13 mm in US_Metric module]; D6.2(e), thinner eyebars need external nuts
EYEBAR_HOLE_CLEARANCE = 1 / 32 # in. [is 1 mm in US_Metric module]; D6.2(c), dh <= d + 1/32
EYEBAR_FY_LIMIT = 70.0 # ksi [is 485 MPa in US_Metric module]; D6.2(d), dh <= 5t above this Fy
TENSION_SLENDERNESS_LIMIT = 300 # User Note D1; preferably not exceeded, does not apply to rods


def _dimension(value: float, unit: str) -> str:
    # 1/32 in., 1/2 in., 13 mm; for messages and requirement labels
    return f"{Fraction(value).limit_denominator(64)} {unit}"


class TensionResult(BaseModel):
    # D1. Slenderness Limitations
    # No slenderness limitations for tension members,
    L: Optional[float] = None # fabricated length of the member, in [mm]
    r: Optional[float] = None # least radius of gyration, in [mm]
    L_r: Optional[float] = None # slenderness ratio; preferably <= 300 per User Note D1 (not for rods)
    # D2. Tensile Strength; lower value for either tensile yielding of gross section [D2-1] or tensile rupture of net section [D2-2]
    phi_t: float # Resistance factor for tension, of governing limit state
    Pn: float # Nominal tensile strength, of governing limit state, kips [N]
    phi_t_Pn: float # Design tensile strength, kips [N]
    limit_state: LimitState # governing limit state; TENSILE_YIELDING or TENSILE_RUPTURE
    Pn_yielding: float # D2-1, kips [N]
    Pn_rupture: float # D2-2, kips [N]
    Fy: float # Specified minimum yield strength of the material, ksi [MPa]
    Fu: float # Specified minimum tensile strength of the material, ksi [MPa]
    Ag: float # Gross area, in^2 [mm^2]
    Ae: float # Effective net area, in^2 [mm^2]
    # D3. Effective Net Area; per B4.3
    An: float # Net area, in^2 [mm^2]
    U: float # Shear lag factor, per Table D3.1, cases 1-8
    # D4. Built-Up Members;
    # ...
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- B4.3 Gross and Net Area Determination ---
def calculate_net_area(
    Ag: float,
    t: float,
    hole_diameters: Sequence[float] = (),
    staggers: Sequence[tuple[float, float]] = (),
    hole_allowance: float = HOLE_ALLOWANCE,
) -> float:
    """AISC 360-22 Section B4.3b: Net area, An, across one chain of bolt holes in an element of thickness t.

    An = Ag - Σ(dh + 1/16)*t + Σ(s^2/4g)*t

    Args:
        Ag: Gross area (in²)
        t: Thickness of the element containing the holes (in)
        hole_diameters: Nominal dimensions of every hole in the chain (in); 1/16 in. is added to each
        staggers: (s, g) for every gage space in a diagonal or zigzag chain; s is pitch (in), g is gage (in)
        hole_allowance: Added to each nominal hole dimension; 1/16 in. [2 mm]

    Returns:
        An: Net area (in²)
    """
    # NOTE: For angles, the gage for holes in opposite adjacent legs is the sum of the gages from the back of the angles less the thickness.
    # NOTE: For slotted HSS welded to a gusset plate, An is Ag less t times the total width of material removed to form the slot.
    # NOTE: For members without holes, An = Ag.
    An = Ag - sum((dh + hole_allowance) * t for dh in hole_diameters) + sum((s**2 / (4.0 * g)) * t for s, g in staggers)
    if An <= 0.0:
        raise ValueError("Net area must be positive; check hole diameters and thickness.")
    return An


# --- D3. Effective Net Area ---
class ShearLagCase(str, Enum):
    """AISC 360-22 Table D3.1 shear lag case identifiers.

    The enum value is the string form used in the codebase, e.g. `"case2"`.
    `description` is a short viewing guide for users; the case id remains the
    authoritative selector for calculations.
    """

    CASE_1 = "case1"
    CASE_2 = "case2"
    CASE_3 = "case3"
    CASE_4 = "case4"
    CASE_5 = "case5"
    CASE_6 = "case6"
    CASE_7 = "case7"
    CASE_8 = "case8"

    @property
    def label(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        descriptions: dict[ShearLagCase, str] = {
            ShearLagCase.CASE_1: "Tension load transmitted directly to each cross-sectional element by fasteners or welds",
            ShearLagCase.CASE_2: "All tension members except HSS; load transmitted to some but not all elements by fasteners or longitudinal (+ transverse) welds",
            ShearLagCase.CASE_3: "Load transmitted only by transverse welds to some but not all elements; An = area of directly connected elements",
            ShearLagCase.CASE_4: "Plates, angles, channels with welds at heels, tees and W-shapes with connected elements; longitudinal welds only",
            ShearLagCase.CASE_5: "Round and rectangular HSS with single concentric gusset through slots in the HSS",
            ShearLagCase.CASE_6: "Rectangular HSS with two side gusset plates",
            ShearLagCase.CASE_7: "W-, M-, S-, HP-shapes or tees cut from them; flange (>= 3 fasteners per line) or web (>= 4 fasteners per line) connected",
            ShearLagCase.CASE_8: "Single and double angles with 3 or more fasteners per line in the direction of loading",
        }
        return descriptions[self]


def shear_lag_factor(case: ShearLagCase | str, **kwargs) -> float:
    """AISC 360-22 Section D3, Table D3.1: Shear lag factor, U, for connections to tension members.

    Keyword arguments by case:
        case1: none; U = 1.0
        case2: x_bar, l; U = 1 - x_bar/l
        case3: none; U = 1.0 and An = area of the directly connected elements
        case4: x_bar, l, w; U = 3l^2/(3l^2 + w^2) * (1 - x_bar/l); l = (l1 + l2)/2
        case5: round HSS: R, theta (rad), tp, l; rectangular HSS: b, H, t, l
        case6: B, H, l
        case7: bf, d, n and connected="flange" (n >= 3) or connected="web" (n >= 4)
        case8: n >= 3
        For cases 7 and 8, x_bar and l may also be passed to use the larger Case 2 value.
        For open cross sections, Ag and A_connected may be passed to apply the D3 lower bound, U >= A_connected/Ag.

    where x_bar is the connection eccentricity (in), l the connection length (in), n the number of fasteners
    per line in the direction of loading, and all other symbols per Table D3.1.
    """
    try:
        case_key = case if isinstance(case, ShearLagCase) else ShearLagCase(case.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ShearLagCase)
        raise ValueError(f"Invalid case '{case}'. Expected one of: {allowed}.") from exc

    def _case_2() -> float:
        x_bar = _require_positive(kwargs.get("x_bar"), "x_bar")
        l = _require_positive(kwargs.get("l"), "l")
        return 1.0 - x_bar / l

    match case_key:
        case ShearLagCase.CASE_1 | ShearLagCase.CASE_3:
            U = 1.0
        case ShearLagCase.CASE_2:
            U = _case_2()
        case ShearLagCase.CASE_4:
            l = _require_positive(kwargs.get("l"), "l")
            w = _require_positive(kwargs.get("w"), "w")
            U = (3.0 * l**2 / (3.0 * l**2 + w**2)) * _case_2()
        case ShearLagCase.CASE_5:
            l = _require_positive(kwargs.get("l"), "l")
            if kwargs.get("R") is not None:
                # round HSS; x_bar = R*sin(θ)/θ - tp/2
                R = _require_positive(kwargs.get("R"), "R")
                theta = _require_positive(kwargs.get("theta"), "theta")
                tp = _require_positive(kwargs.get("tp"), "tp")
                x_bar = R * math.sin(theta) / theta - tp / 2.0
                U = (1.0 + (x_bar / l) ** 3.2) ** -10
            else:
                # rectangular HSS; b = (B - tp)/2, from the gusset face to the outer face of the HSS wall (Design Example D.4)
                b = _require_positive(kwargs.get("b"), "b")
                H = _require_positive(kwargs.get("H"), "H")
                t = _require_positive(kwargs.get("t"), "t")
                x_bar = b - (2.0 * b**2 + t * H - 2.0 * t**2) / (2.0 * H + 4.0 * b - 4.0 * t)
                U = 1.0 - x_bar / l
        case ShearLagCase.CASE_6:
            l = _require_positive(kwargs.get("l"), "l")
            B = _require_positive(kwargs.get("B"), "B")
            H = _require_positive(kwargs.get("H"), "H")
            U_B = 3.0 * l**2 / (3.0 * l**2 + B**2)
            U_H = 3.0 * l**2 / (3.0 * l**2 + H**2)
            U = (B * U_B + H * U_H) / (H + B)
        case ShearLagCase.CASE_7:
            n = int(_require_positive(kwargs.get("n"), "n"))
            connected = str(kwargs.get("connected", "flange")).strip().lower()
            match connected:
                case "flange":
                    if n < 3:
                        raise ValueError("Case 7 (flange connected) requires three or more fasteners per line; use case2.")
                    bf = _require_positive(kwargs.get("bf"), "bf")
                    d = _require_positive(kwargs.get("d"), "d") # for tees, d of the section from which the tee was cut
                    U = 0.90 if bf >= 2.0 / 3.0 * d else 0.85
                case "web":
                    if n < 4:
                        raise ValueError("Case 7 (web connected) requires four or more fasteners per line; use case2.")
                    U = 0.70
                case _:
                    raise ValueError("Case 7 requires connected='flange' or connected='web'.")
            if kwargs.get("x_bar") is not None and kwargs.get("l") is not None:
                U = max(U, _case_2()) # If U is calculated per Case 2, the larger value is permitted
        case ShearLagCase.CASE_8:
            n = int(_require_positive(kwargs.get("n"), "n"))
            if n >= 4:
                U = 0.80
            elif n == 3:
                U = 0.60
            else:
                raise ValueError("Case 8 requires three or more fasteners per line; with fewer, use case2.")
            if kwargs.get("x_bar") is not None and kwargs.get("l") is not None:
                U = max(U, _case_2()) # If U is calculated per Case 2, the larger value is permitted
        case _:
            raise ValueError(f"No shear lag definition is implemented for '{case_key.value}'.")

    # D3: For open cross sections (W, M, S, C, HP, WT, ST, single & double angles), U need not be less than
    # the ratio of the gross area of the connected element(s) to the member gross area. Not for HSS or plates.
    A_connected = kwargs.get("A_connected")
    Ag = kwargs.get("Ag")
    if A_connected is not None and Ag is not None and case_key not in {ShearLagCase.CASE_5, ShearLagCase.CASE_6}:
        U = max(U, _require_positive(A_connected, "A_connected") / _require_positive(Ag, "Ag"))

    if U <= 0.0:
        raise ValueError(f"Shear lag factor U = {U:.4f} is not positive; check connection length and eccentricity.")
    return min(U, 1.0)


# SHEAR_LAG_FACTORS = {}
def calculate_effective_net_area(An: float, U: float) -> float:
    """AISC 360-22 Equation D3-1: Effective net area of tension members, Ae = An*U.

    Args:
        An: Net area (in²), per B4.3
        U: Shear lag factor, per Table D3.1

    Returns:
        Ae: Effective net area (in²)
    """
    # TODO: consider, in future, implementing individual checks to build larger check
    Ae = U * An
    return round(Ae, ndigits=4) # TODO: note likelyhood of this as a good implementation, but need to be concise :)


# --- D2. Tensile Strength ---
def tensile_yielding_strength(Fy: float, Ag: float) -> float:
    """AISC 360-22 Equation D2-1: Nominal tensile strength for tensile yielding in the gross section, Pn = Fy*Ag.

    Args:
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area (in²)

    Returns:
        Pn: Nominal tensile strength (kips); phi_t = 0.90
    """
    return Fy * Ag


def tensile_rupture_strength(Fu: float, Ae: float) -> float:
    """AISC 360-22 Equation D2-2: Nominal tensile strength for tensile rupture in the net section, Pn = Fu*Ae.

    Args:
        Fu: Specified minimum tensile strength (ksi)
        Ae: Effective net area (in²)

    Returns:
        Pn: Nominal tensile strength (kips); phi_t = 0.75
    """
    # NOTE: Where connections use plug, slot or fillet welds in holes or slots, the effective net area through the holes shall be used.
    return Fu * Ae


def check_tension_slenderness(L: float, r: float) -> UtilisationCheck:
    """AISC 360-22 Section D1 (User Note): Slenderness ratio L/r of tension members preferably should not exceed 300.

    Args:
        L: Fabricated length of the member (in)
        r: Least radius of gyration (in)
    """
    L_r = _require_positive(L, "L") / _require_positive(r, "r")
    utilisation = L_r / TENSION_SLENDERNESS_LIMIT
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"L_r": L_r, "limit": TENSION_SLENDERNESS_LIMIT, "note": "Recommendation only; does not apply to rods."},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="D1", title="Slenderness limitations (User Note)"),
    )


def _least_radius_of_gyration(data: dict[str, Any]) -> float:
    radii = [value for value in (_positive_value(data, "rx"), _positive_value(data, "ry"), _positive_value(data, "rz")) if value > 0.0]
    return min(radii) if radii else 0.0


def tension(
    section: Optional[BaseSection] = None,
    Fy: float = 50.0,
    Fu: float = 65.0,
    Ag: Optional[float] = None,
    An: Optional[float] = None,
    U: float = 1.0,
    L: Optional[float] = None,
    r: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TensionResult:
    """AISC 360-22 Section D2: Design tensile strength, phi_t*Pn, as the lower of tensile yielding and tensile rupture.

    Provide a section (Ag and least r are read from it), a section_type with properties, or Ag directly.

    Args:
        section: US section; A is taken as Ag and the least of rx, ry, rz as r
        Fy: Specified minimum yield stress (ksi); default 50 ksi (ASTM A992)
        Fu: Specified minimum tensile strength (ksi); default 65 ksi (ASTM A992)
        Ag: Gross area (in²); overrides the section value
        An: Net area (in²) per B4.3b; defaults to Ag for members without holes
        U: Shear lag factor per Table D3.1; see shear_lag_factor()
        L: Fabricated length (in); optional, for the D1 slenderness recommendation
        r: Least radius of gyration (in); overrides the section value
        section_type: Section type when passing plain properties
        properties: Plain section properties, or overrides for the section's properties
    """
    data: dict[str, Any] = {}
    if section is not None or section_type is not None:
        _, data = _section_properties(section, section_type, properties)
    elif properties is not None:
        data = dict(properties)

    Ag_value = _require_positive(Ag if Ag is not None else _positive_value(data, "A", "Ag"), "Ag")
    An_value = _require_positive(An if An is not None else Ag_value, "An")
    if An_value > Ag_value:
        raise ValueError("Net area An cannot exceed gross area Ag.")
    U_value = _require_positive(U, "U")
    if U_value > 1.0:
        raise ValueError("Shear lag factor U cannot exceed 1.0.")

    Ae = calculate_effective_net_area(An_value, U_value)
    Pn_yielding = tensile_yielding_strength(Fy, Ag_value) # D2-1
    Pn_rupture = tensile_rupture_strength(Fu, Ae) # D2-2

    if PHI_T_YIELDING * Pn_yielding <= PHI_T_RUPTURE * Pn_rupture:
        phi_t, Pn, limit_state, equation = PHI_T_YIELDING, Pn_yielding, LimitState.TENSILE_YIELDING, "D2-1"
    else:
        phi_t, Pn, limit_state, equation = PHI_T_RUPTURE, Pn_rupture, LimitState.TENSILE_RUPTURE, "D2-2"

    r_value = r if r is not None else (_least_radius_of_gyration(data) or None)
    L_r = (L / r_value) if (L is not None and r_value) else None

    return TensionResult(
        L=L,
        r=r_value,
        L_r=L_r,
        phi_t=phi_t,
        Pn=Pn,
        phi_t_Pn=phi_t * Pn,
        limit_state=limit_state,
        Pn_yielding=Pn_yielding,
        Pn_rupture=Pn_rupture,
        Fy=Fy,
        Fu=Fu,
        Ag=Ag_value,
        Ae=Ae,
        An=An_value,
        U=U_value,
        reference=Reference(code=DesignCode.AISC_360, clause="D2", equation=equation, title="Tensile strength"),
        metadata={
            "phi_t_Pn_yielding": PHI_T_YIELDING * Pn_yielding,
            "phi_t_Pn_rupture": PHI_T_RUPTURE * Pn_rupture,
            "slenderness_ok": (L_r <= TENSION_SLENDERNESS_LIMIT) if L_r is not None else None,
        },
    )


def tension_utilisation(Pu: float, phi_t_Pn: float) -> UtilisationCheck:
    """AISC 360-22 Section D2: Tension utilisation, Pu / phi_t*Pn (LRFD).

    Args:
        Pu: Required tensile strength (kips)
        phi_t_Pn: Design tensile strength (kips)
    """
    utilisation = compute_utilisation(abs(Pu), phi_t_Pn)
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pu": Pu, "phi_t_Pn": phi_t_Pn},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="D2", title="Tensile strength"),
    )


# --- D4. Built-Up Members ---
# [NO PLAN TO IMPLEMENT BUILT-UP MEMBERS IN ANY CODE] # NOTE: see J3.6 for spacing of connectors; tie plates >= 2/3 distance between lines, thickness >= 1/50 of it, spacing <= 6 in.


# --- D5. Pin-Connected Members ---
class PinConnectedMemberResult(BaseModel):
    # D5. Pin-Connected Members; lowest of tensile rupture, shear rupture, bearing and yielding
    phi_Pn: float # design tensile strength, kips [N]
    limit_state: LimitState # governing limit state
    Fy: float # specified minimum yield stress, ksi [MPa]
    Fu: float # specified minimum tensile strength, ksi [MPa]
    # - for tensile rupture (D5-1)
    Pn_tensile_rupture: float # Fu*(2*t*be), kips [N]
    # - for shear rupture (D5-2)
    Pn_shear_rupture: float # 0.6*Cr*Fu*Asf, kips [N]
    Asf: float # area on shear failure path, in^2 [mm^2]
    t: float # thickness of the plate, in [mm]
    d: float # diameter of the pin, in [mm]
    dh: float # hole diameter, in [mm]
    be: float # 2t + 0.63 in. [2t + 16 mm], but not more than the actual distance from the edge of the hole to the edge of the part, normal to the force
    a: float # shortest distance from edge of the pin hole to the edge of the member, parallel to the force, in [mm]
    Cr: float # reduction factor for shear rupture on pin-connected members; dependent on ratio of d and dh;

    # - for bearing on pin's projected area (J7)
    Rn_bearing: float # 1.8*Fy*Apb, kips [N]
    Apb: float # projected bearing area of the pin, d*t, in^2 [mm^2]
    # - for yielding on gross section (D2(a))
    Pn_yielding: float # Fy*Ag, kips [N]
    Ag: float # gross area, in^2 [mm^2]

    # D5.2 Dimensional requirements
    w: Optional[float] = None # width of the plate at the pin hole, in [mm]
    w_min: float # 2*be + d, in [mm]
    a_min: float # 1.33*be, in [mm]
    dimensional_requirements_met: Optional[bool] = None
    reference: Optional[Reference] = None


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
    be_offset: float = PIN_BE_OFFSET,
    clearances: tuple[float, float] = PIN_CLEARANCES,
) -> PinConnectedMemberResult:
    """AISC 360-22 Section D5: Pin-connected members.

    Design tensile strength is the lower of tensile rupture (D5-1), shear rupture (D5-2), bearing on the projected area of
    the pin (J7-1) and yielding on the gross section (D2-1).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Fu: Specified minimum tensile strength (ksi)
        t: Thickness of plate (in)
        d: Diameter of pin (in)
        dh: Diameter of hole (in)
        a: Shortest distance from edge of pin hole to edge of member, parallel to the force (in)
        w: Width of plate at the pin hole (in); hole assumed midway between the edges (D5.2(a))
        Ag: Gross area of the member (in²); defaults to w*t
        be_actual: Actual distance from edge of hole to edge of part normal to the force (in); defaults to (w - dh)/2
        be_offset: 0.63 in. [16 mm] in be = 2t + 0.63
        clearances: dh - d limits (in) for Cr = 1.0 and Cr = 0.95; (1/32, 1/16) in. [(1, 2) mm]
    """
    t = _require_positive(t, "t")
    d = _require_positive(d, "d")
    dh = _require_positive(dh, "dh")
    a = _require_positive(a, "a")
    if dh < d:
        raise ValueError("Hole diameter dh cannot be smaller than the pin diameter d.")

    be = 2.0 * t + be_offset # D5.1
    if be_actual is None and w is not None:
        be_actual = (w - dh) / 2.0
    if be_actual is not None:
        be = min(be, _require_positive(be_actual, "be_actual"))

    # Cr = 1.0 when dh - d <= 1/32 in. [1 mm]; 0.95 when 1/32 in. < dh - d <= 1/16 in. [1 mm < dh - d <= 2 mm]
    clearance: float = dh - d
    tight, loose = clearances
    if clearance <= tight + 1e-9:
        Cr = 1.0
    elif clearance <= loose + 1e-9:
        Cr = 0.95
    else:
        raise ValueError(f"Cr is only defined for dh - d <= {Fraction(loose).limit_denominator(64)} per D5.1(b); see also D5.2(b).")

    Asf = 2.0 * t * (a + d / 2.0)
    Pn_tensile_rupture = Fu * (2.0 * t * be) # D5-1
    Pn_shear_rupture = 0.6 * Cr * Fu * Asf # D5-2
    Apb = d * t
    Rn_bearing = 1.8 * Fy * Apb # J7-1
    Ag_value = Ag if Ag is not None else (w * t if w is not None else None)
    Ag_value = _require_positive(Ag_value, "Ag (or w)")
    Pn_yielding = tensile_yielding_strength(Fy, Ag_value) # D2-1

    candidates = [
        (PHI_T_RUPTURE * Pn_tensile_rupture, LimitState.TENSILE_RUPTURE, "D5-1"),
        (PHI_SF * Pn_shear_rupture, LimitState.SHEAR_RUPTURE, "D5-2"),
        (PHI_BEARING * Rn_bearing, LimitState.BEARING, "J7-1"),
        (PHI_T_YIELDING * Pn_yielding, LimitState.TENSILE_YIELDING, "D2-1"),
    ]
    phi_Pn, limit_state, equation = min(candidates, key=lambda item: item[0])

    w_min = 2.0 * be + d # D5.2(c)
    a_min = 1.33 * be # D5.2(c)
    dimensional_requirements_met = (w >= w_min and a >= a_min) if w is not None else None

    return PinConnectedMemberResult(
        phi_Pn=phi_Pn,
        limit_state=limit_state,
        Fy=Fy,
        Fu=Fu,
        Pn_tensile_rupture=Pn_tensile_rupture,
        Pn_shear_rupture=Pn_shear_rupture,
        Asf=Asf,
        t=t,
        d=d,
        dh=dh,
        be=be,
        a=a,
        Cr=Cr,
        Rn_bearing=Rn_bearing,
        Apb=Apb,
        Pn_yielding=Pn_yielding,
        Ag=Ag_value,
        w=w,
        w_min=w_min,
        a_min=a_min,
        dimensional_requirements_met=dimensional_requirements_met,
        reference=Reference(code=DesignCode.AISC_360, clause="D5", equation=equation, title="Pin-connected members"),
    )


# --- D6. Eyebars ---
def check_eyebar(
    Fy: float,
    Fu: float,
    t: float,
    w: float,
    d: Optional[float] = None,
    dh: Optional[float] = None,
    t_min: float = EYEBAR_T_MIN,
    hole_clearance: float = EYEBAR_HOLE_CLEARANCE,
    Fy_limit: float = EYEBAR_FY_LIMIT,
    units: tuple[str, str] = ("in.", "ksi"),
) -> TensionResult:
    """AISC 360-22 Section D6: Eyebars; tensile strength per D2 with Ag taken as the gross area of the eyebar body.

    For calculation purposes, the width of the body of the eyebar shall not exceed eight times its thickness.

    Args:
        Fy: Specified minimum yield stress (ksi)
        Fu: Specified minimum tensile strength (ksi)
        t: Thickness of eyebar (in)
        w: Width of eyebar body (in)
        d: Pin diameter (in); optional, for D6.2(c)
        dh: Pin-hole diameter (in); optional, for D6.2(c) and D6.2(d)
        t_min: 1/2 in. [13 mm]; D6.2(e)
        hole_clearance: 1/32 in. [1 mm]; D6.2(c)
        Fy_limit: 70 ksi [485 MPa]; D6.2(d)
        units: (length, stress) units for the requirement labels; ("mm", "MPa") in the US_Metric module
    """
    t = _require_positive(t, "t")
    w_calc = min(_require_positive(w, "w"), 8.0 * t) # D6.1, body width not more than 8t for calculation
    result = tension(Fy=Fy, Fu=Fu, Ag=w_calc * t)

    length_unit, stress_unit = units
    requirements: dict[str, Optional[bool]] = {f"t >= {_dimension(t_min, length_unit)} (else external nuts required), D6.2(e)": t >= t_min}
    if d is not None:
        requirements["d >= 7/8 w, D6.2(c)"] = d >= 7.0 / 8.0 * w
    if d is not None and dh is not None:
        requirements[f"dh <= d + {_dimension(hole_clearance, length_unit)}, D6.2(c)"] = dh <= d + hole_clearance + 1e-9
    if dh is not None and Fy > Fy_limit:
        requirements[f"dh <= 5t for Fy > {Fy_limit:g} {stress_unit}, D6.2(d)"] = dh <= 5.0 * t

    return result.model_copy(
        update={
            "reference": Reference(code=DesignCode.AISC_360, clause="D6", equation=result.reference.equation if result.reference else None, title="Eyebars"),
            "metadata": {**result.metadata, "w_calc": w_calc, "dimensional_requirements": requirements},
        }
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.beams import W_beam

    # AISC Design Example D.1: W8x21, 4 holes of 13/16 in. through the flanges, U = 0.908 (Case 2)
    beam = W_beam("W8X21")
    An = calculate_net_area(beam.A, beam.tf, hole_diameters=[13 / 16] * 4)
    U = shear_lag_factor("case7", bf=beam.bf, d=beam.d, n=3, x_bar=0.831, l=9.0)
    print(tension(section=beam, An=An, U=U, L=25 * 12).model_dump())
    print(check_pin_connected_member(Fy=50.0, Fu=65.0, t=1.0, d=4.0, dh=4.03125, a=3.5, w=8.25).model_dump())
    print("🐬")
