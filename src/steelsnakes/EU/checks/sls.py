# 7: SERVICEABILITY LIMIT STATES
# 7.1 General
# 7.2 Serviceability limit states for buildings
# 7.2.1 Vertical deflections
# 7.2.2 Horizontal deflections
# 7.2.3 Dynamic effects
# NOTE: EN 1993-1-1:2005+A1:2014 gives no limits of its own; 7.2 refers to EN 1990 Annex A1.4, and the limits are to be
# ... specified for each project and agreed with the client (7.1(3), 7.2), or given by the National Annex (NOTE B). The
# ... default deflection limits here are the suggested values of the UK NA to BS EN 1993-1-1.
# NOTE: units are N, mm and N/mm² [MPa]; line loads are in N/mm (1 kN/m = 1 N/mm), deflections in mm, masses per unit
# ... length in kg/m and frequencies in Hz. Section tables are converted on read, as in steelsnakes.EU.checks.uls.
from __future__ import annotations

import math
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import LimitState, Reference, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.checks.uls import (
    E_STEEL,
    ETA,
    BendingAxis,
    ShearDirection,
    _family,
    _get,
    _ratio_check,
    _reference,
    _require_positive,
    _section_data,
    _shear_area,
    _shear_area_shape,
    _web_depth,
    longitudinal_stress,
)

GAMMA_M_SER = 1.00 # EN 1993-2 7.3(1) NOTE: recommended partial factor for the serviceability limit states
GRAVITY = 9.81 # m/s²; weight to mass
F_MIN = 3.0 # Hz; 7.2.3: floors on which people walk, as in the former ENV 1993-1-1 (5 Hz for rhythmic activity, e.g gymnasia)

Support = Literal["simply_supported", "both_ends_fixed", "one_end_fixed", "cantilever"] # one_end_fixed: the other end pinned
Loading = Literal["uniform", "concentrated"] # concentrated: at mid-span, or at the tip of a cantilever
SLSCombination = Literal["characteristic", "frequent", "quasi-permanent"] # EN 1990 6.5.3(2) a) to c)

# EN 1990 Table A1.1: Recommended values of (ψ0, ψ1, ψ2) for buildings
PSI_FACTORS: dict[str, tuple[float, float, float]] = {
    "A": (0.7, 0.5, 0.3), # imposed loads, category A: domestic, residential areas
    "B": (0.7, 0.5, 0.3), # category B: office areas
    "C": (0.7, 0.7, 0.6), # category C: congregation areas
    "D": (0.7, 0.7, 0.6), # category D: shopping areas
    "E": (1.0, 0.9, 0.8), # category E: storage areas
    "F": (0.7, 0.7, 0.6), # category F: traffic area, vehicle weight <= 30 kN
    "G": (0.7, 0.5, 0.3), # category G: traffic area, 30 kN < vehicle weight <= 160 kN
    "H": (0.0, 0.0, 0.0), # category H: roofs
    "snow_nordic": (0.7, 0.5, 0.2), # snow: Finland, Iceland, Norway, Sweden
    "snow_high": (0.7, 0.5, 0.2), # snow: other CEN member states, sites at altitude H > 1000 m a.s.l.
    "snow": (0.5, 0.2, 0.0), # snow: other CEN member states, sites at altitude H <= 1000 m a.s.l.
    "wind": (0.6, 0.2, 0.0), # wind loads on buildings; the UK NA to BS EN 1990 takes ψ0 = 0.5
    "temperature": (0.6, 0.5, 0.0), # temperature (non-fire) in buildings
}

# 7.2.1(1)B and 7.2.2(1)B NOTE B, UK NA to BS EN 1993-1-1: suggested limits as n in L/n (H/n), for deflections under the
# ... characteristic combination of the variable actions; None where the limit is to suit the cladding
VERTICAL_DEFLECTION_LIMITS: dict[str, Optional[float]] = {
    "cantilever": 180.0, # cantilevers: length/180
    "brittle_finish": 360.0, # beams carrying plaster or other brittle finish: span/360
    "beam": 200.0, # other beams, except purlins and sheeting rails: span/200
    "purlin": None, # purlins and sheeting rails: to suit the characteristics of the cladding
}
HORIZONTAL_DEFLECTION_LIMITS: dict[str, Optional[float]] = {
    "single_storey": 300.0, # tops of columns in single storey buildings, except portal frames: height/300
    "portal_frame": None, # columns in portal frame buildings, not supporting crane runways: to suit the cladding
    "multi_storey": 300.0, # in each storey of a building with more than one storey: height of that storey/300
}

# Maximum elastic deflection of a uniform beam, w = k*W*L³/(E*I), W the total load (w*L for uniform loading)
DEFLECTION_COEFFICIENTS: dict[tuple[str, str], float] = {
    ("simply_supported", "uniform"): 5.0 / 384.0,
    ("simply_supported", "concentrated"): 1.0 / 48.0,
    ("both_ends_fixed", "uniform"): 1.0 / 384.0,
    ("both_ends_fixed", "concentrated"): 1.0 / 192.0,
    ("one_end_fixed", "uniform"): 0.0054161, # 1/184.6, at 0.4215L from the pinned end
    ("one_end_fixed", "concentrated"): 1.0 / (48.0 * math.sqrt(5.0)), # 1/107.3, at L/√5 from the pinned end
    ("cantilever", "uniform"): 1.0 / 8.0,
    ("cantilever", "concentrated"): 1.0 / 3.0,
}
# First natural frequency of a uniform beam under uniform mass, f = K/(2π)*sqrt(E*I/(m*L⁴)); K = (β₁L)², Euler-Bernoulli
FREQUENCY_COEFFICIENTS: dict[str, float] = {
    "simply_supported": math.pi**2, # 9.870
    "both_ends_fixed": 22.373,
    "one_end_fixed": 15.418,
    "cantilever": 3.516,
}


# --- Helpers ---
def _limit(limits: dict[str, Optional[float]], key: Optional[str], name: str) -> Optional[float]:
    if key is None:
        return None
    if key not in limits:
        raise ValueError(f"Unknown {name} '{key}'; expected one of {', '.join(limits)}.")
    return limits[key]


def _mass_per_metre(raw: dict[str, Any]) -> float:
    """Mass per metre from the section tables (kg/m); back-to-back angles store the total of the pair."""
    value = raw.get("mass_per_metre") or raw.get("total_mass_per_metre")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0.0:
        raise ValueError("Section mass per metre is not available; pass self_weight=False and include it in the loads.")
    return float(value)


def line_load_from_mass(m: float) -> float:
    """Weight of a mass per unit length as a line load, w = m*g (N/mm = kN/m), from m (kg/m)."""
    return m * GRAVITY / 1e3


def mass_from_line_load(w: float) -> float:
    """Mass per unit length of a line load, m = w/g (kg/m), from w (N/mm = kN/m)."""
    return w * 1e3 / GRAVITY


# --- EN 1990 6.5.3 Combinations of actions for the serviceability limit states ---
def psi_factors(category: str) -> tuple[float, float, float]:
    """EN 1990 Table A1.1: (ψ0, ψ1, ψ2) for a variable action on a building, e.g "B" (offices), "snow" or "wind"."""
    if category not in PSI_FACTORS:
        raise ValueError(f"Unknown category '{category}'; Table A1.1 lists {', '.join(PSI_FACTORS)}.")
    return PSI_FACTORS[category]


def sls_combination(
    permanent: float | Sequence[float] = 0.0,
    variable: Sequence[tuple[float, str]] = (),
    combination: SLSCombination = "characteristic",
    P: float = 0.0,
    leading: Optional[int] = None,
) -> float:
    """EN 1990 6.5.3(2), Equations 6.14b to 6.16b: Combination of actions for the serviceability limit states.

    characteristic (6.14b): ΣG_k,j + P + Q_k,1 + Σψ0,i*Q_k,i; normally for irreversible limit states
    frequent (6.15b): ΣG_k,j + P + ψ1,1*Q_k,1 + Σψ2,i*Q_k,i; normally for reversible limit states
    quasi-permanent (6.16b): ΣG_k,j + P + Σψ2,i*Q_k,i; normally for long-term effects and the appearance of the structure

    With a linear analysis the effects of the actions, e.g deflections from each load case, combine the same way.

    Args:
        permanent: Characteristic permanent actions G_k,j, or their effects
        variable: (Q_k,i, category) for each variable action, with a PSI_FACTORS category, e.g [(7.5, "B"), (1.2, "snow")]
        combination: "characteristic", "frequent" or "quasi-permanent"
        P: Relevant representative value of a prestressing action
        leading: Index in `variable` of the leading action Q_k,1; by default, the one giving the largest value

    Returns:
        The combined value, in the units of the inputs
    """
    G: float = float(permanent) if isinstance(permanent, (int, float)) else float(sum(permanent))
    psis: list[tuple[float, float, float]] = [psi_factors(category) for _, category in variable]
    if combination not in ("characteristic", "frequent", "quasi-permanent"):
        raise ValueError("combination must be 'characteristic', 'frequent' or 'quasi-permanent'.")
    if combination == "quasi-permanent" or not variable:
        return G + P + sum(psi[2] * Q for (Q, _), psi in zip(variable, psis)) # (6.16b)

    def _value(j: int) -> float:
        total: float = G + P
        for i, ((Q, _), (psi_0, psi_1, psi_2)) in enumerate(zip(variable, psis)):
            if combination == "characteristic":
                total += Q if i == j else psi_0 * Q # (6.14b)
            else:
                total += psi_1 * Q if i == j else psi_2 * Q # (6.15b)
        return total

    if leading is not None:
        if not 0 <= leading < len(variable):
            raise ValueError(f"leading must index one of the {len(variable)} variable actions.")
        return _value(leading)
    return max(_value(j) for j in range(len(variable)))


# --- 7.1(4) Plastic redistribution at the serviceability limit state ---
def serviceability_stress_utilisations(sigma_Ed_ser: float, tau_Ed_ser: float, fy: float, gamma_M_ser: float = GAMMA_M_SER) -> dict[str, float]:
    """EN 1993-2 7.3(1), Equations 7.1 to 7.3: Stress limits under the SLS combination, as utilisations.

    σ_Ed,ser <= fy/γM,ser (7.1); τ_Ed,ser <= fy/(√3γM,ser) (7.2); sqrt(σ_Ed,ser² + 3τ_Ed,ser²) <= fy/γM,ser (7.3)
    """
    f: float = _require_positive(fy, "fy") / gamma_M_ser
    return {
        "sigma (7.1)": abs(sigma_Ed_ser) / f,
        "tau (7.2)": abs(tau_Ed_ser) * math.sqrt(3.0) / f,
        "sigma + tau (7.3)": math.sqrt(sigma_Ed_ser**2 + 3.0 * tau_Ed_ser**2) / f,
    }


class ServiceabilityStressResult(BaseModel):
    # 7.1(4): elastic stresses under the SLS combination, to EN 1993-2 7.3, so that no plastic redistribution occurs
    sigma_Ed_ser: float # N/mm²; |N|/A + |M_y|/W_el,y + |M_z|/W_el,z at the most stressed fibre
    tau_Ed_ser: float # N/mm²; V/A_w on the web of I-sections and channels loaded parallel to the web, else V/A_v
    fy: float # N/mm²
    gamma_M_ser: float
    limit_state: LimitState = LimitState.SERVICEABILITY_STRESS
    utilisations: dict[str, float] # {"sigma (7.1)": ..., "tau (7.2)": ..., "sigma + tau (7.3)": ...}
    governing: str # key of the largest utilisation
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_serviceability_stresses(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    N_Ed_ser: float = 0.0,
    M_y_Ed_ser: float = 0.0,
    M_z_Ed_ser: float = 0.0,
    V_z_Ed_ser: float = 0.0,
    V_y_Ed_ser: float = 0.0,
    sigma_Ed_ser: Optional[float] = None,
    tau_Ed_ser: Optional[float] = None,
    gamma_M_ser: float = GAMMA_M_SER,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ServiceabilityStressResult:
    """EN 1993-1-1 7.1(4): where plastic global analysis is used for the ULS, check that the stresses stay elastic under
    the SLS combination, so that no plastic redistribution occurs, with the limits of EN 1993-2 7.3 (Equations 7.1 to 7.3).

    σ_Ed,ser adds the elastic stresses at the most stressed fibre (6.2.9.2). τ_Ed,ser is the mean shear stress V/A_w on the
    web of I-sections and channels loaded parallel to the web (6.2.6(5)), otherwise V/A_v (6.2.6(3)), taking the larger
    of the two directions. (7.3) combines them as if at the same point, which is conservative.

    Args:
        section: EU/UK section
        fy: Yield strength (N/mm²)
        N_Ed_ser: Axial force under the SLS combination (N)
        M_y_Ed_ser, M_z_Ed_ser: Moments under the SLS combination (Nmm)
        V_z_Ed_ser, V_y_Ed_ser: Shear forces parallel to the web or depth (z) and to the flanges or width (y) (N)
        sigma_Ed_ser, tau_Ed_ser: Stresses from a separate analysis (N/mm²); override the calculation
        gamma_M_ser: Partial factor for the serviceability limit states
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy = _require_positive(fy, "fy")
    if sigma_Ed_ser is None:
        sigma_Ed_ser = longitudinal_stress(N_Ed_ser, _get(data, "A"), M_y_Ed_ser, data.get("W_el_y"), M_z_Ed_ser, data.get("W_el_z"))
    if tau_Ed_ser is None:
        tau_Ed_ser = 0.0
        shear_actions: tuple[tuple[ShearDirection, float], ...] = (("z", V_z_Ed_ser), ("y", V_y_Ed_ser))
        for direction, V_Ed in shear_actions:
            if V_Ed == 0.0:
                continue
            if direction == "z" and family in ("I", "channel"):
                A_shear: float = _web_depth(data) * _get(data, "t_w") # A_w = h_w*t_w, (6.21)
            else:
                A_shear = _shear_area(data, _shear_area_shape(section_type, False), direction, ETA) # 6.2.6(3)
            tau_Ed_ser = max(tau_Ed_ser, abs(V_Ed) / A_shear)

    utilisations: dict[str, float] = serviceability_stress_utilisations(sigma_Ed_ser, tau_Ed_ser, fy, gamma_M_ser)
    governing: str = max(utilisations, key=lambda key: utilisations[key])
    equation: str = governing[governing.index("(") + 1 : -1] # EN 1993-2 equation, e.g "7.3"
    return ServiceabilityStressResult(
        sigma_Ed_ser=sigma_Ed_ser,
        tau_Ed_ser=tau_Ed_ser,
        fy=fy,
        gamma_M_ser=gamma_M_ser,
        utilisations=utilisations,
        governing=governing,
        utilisation=UtilisationCheck(
            utilisation=utilisations[governing],
            metadata={"sigma_Ed_ser": sigma_Ed_ser, "tau_Ed_ser": tau_Ed_ser},
            adequacy="OK" if utilisations[governing] <= 1.0 else "FAILS",
            reference=_reference("7.1(4)", equation, f"Serviceability stresses: {governing}", notes="EN 1993-2 7.3"),
        ),
        reference=_reference("7.1(4)", title="Plastic redistribution at the serviceability limit state", notes="EN 1993-2 7.3"),
    )


# --- 7.2.1 Vertical deflections ---
def beam_deflection(load: float, L: float, I: float, support: Support = "simply_supported", loading: Loading = "uniform", E: float = E_STEEL) -> float:
    """Maximum elastic deflection of a uniform beam, w = k*W*L³/(E*I) (mm); shear deformation is ignored.

    simply supported: 5wL⁴/(384EI) uniform, PL³/(48EI) concentrated at mid-span
    both ends fixed: wL⁴/(384EI), PL³/(192EI)
    one end fixed, the other pinned: wL⁴/(184.6EI), PL³/(48√5EI)
    cantilever: wL⁴/(8EI), PL³/(3EI) concentrated at the tip

    Args:
        load: Line load w (N/mm = kN/m) for "uniform", or point load P (N) for "concentrated"
        L: Span, or length of the cantilever (mm)
        I: Second moment of area about the axis of bending (mm⁴)
        support: "simply_supported", "both_ends_fixed", "one_end_fixed" or "cantilever"
        loading: "uniform", or "concentrated" at mid-span (at the tip of a cantilever)
        E: Modulus of elasticity (N/mm²)
    """
    if (support, loading) not in DEFLECTION_COEFFICIENTS:
        raise ValueError(f"No deflection coefficient for support '{support}' with loading '{loading}'.")
    L = _require_positive(L, "L")
    W: float = load * L if loading == "uniform" else load
    return DEFLECTION_COEFFICIENTS[(support, loading)] * W * L**3 / (E * _require_positive(I, "I"))


class VerticalDeflectionResult(BaseModel):
    # 7.2.1 Vertical deflections, with the definitions of EN 1990 A1.4.3 and Figure A1.1
    w_c: float = 0.0 # precamber in the unloaded member, mm
    w_1: float = 0.0 # initial part of the deflection under the permanent loads, mm
    w_2: float = 0.0 # long-term part of the deflection under the permanent loads, mm
    w_3: float # additional part of the deflection due to the variable actions, mm
    w_tot: float # w_1 + w_2 + w_3, mm
    w_max: float # w_tot - w_c, remaining total deflection, mm
    L: float # span, or length of a cantilever, mm
    member: Optional[str] = None # VERTICAL_DEFLECTION_LIMITS key
    span_ratio_w_3: Optional[float] = None # n in L/n
    span_ratio_w_max: Optional[float] = None # n in L/n
    w_3_limit: Optional[float] = None # L/n, mm
    w_max_limit: Optional[float] = None # L/n, mm
    limit_state: LimitState = LimitState.VERTICAL_DEFLECTION
    utilisations: dict[str, float] # e.g {"w_3": 0.72, "w_max": 0.54}
    governing: str # key of the largest utilisation
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_vertical_deflection(
    L: float,
    w_3: float,
    w_1: float = 0.0,
    w_2: float = 0.0,
    w_c: float = 0.0,
    member: Optional[str] = "beam",
    span_ratio_w_3: Optional[float] = None,
    span_ratio_w_max: Optional[float] = None,
) -> VerticalDeflectionResult:
    """EN 1993-1-1 7.2.1: Vertical deflections to EN 1990 A1.4.3 and Figure A1.1, w_tot = w_1 + w_2 + w_3 and w_max = w_tot - w_c.

    The limits are to be agreed with the client (7.2.1(1)B). The UK NA limits w_3, the deflection under the characteristic
    combination of the variable actions, without the permanent actions; see VERTICAL_DEFLECTION_LIMITS. Some National
    Annexes also limit w_max, which `span_ratio_w_max` checks.

    Args:
        L: Span, or length of a cantilever (mm)
        w_3: Additional deflection due to the variable actions of the relevant combination (mm)
        w_1: Initial deflection under the permanent loads (mm)
        w_2: Long-term deflection under the permanent loads (mm), e.g from creep in composite members
        w_c: Precamber in the unloaded member (mm)
        member: VERTICAL_DEFLECTION_LIMITS key for the limit on w_3, "cantilever", "brittle_finish", "beam" or "purlin";
            None to check only the span ratios given
        span_ratio_w_3: n in the limit L/n on w_3, e.g 360; overrides `member`
        span_ratio_w_max: n in the limit L/n on w_max, e.g 250
    """
    L = _require_positive(L, "L")
    n_w_3: Optional[float] = span_ratio_w_3 if span_ratio_w_3 is not None else _limit(VERTICAL_DEFLECTION_LIMITS, member, "member")
    w_tot: float = w_1 + w_2 + w_3
    w_max: float = w_tot - w_c
    checks: dict[str, float] = {}
    w_3_limit: Optional[float] = None
    w_max_limit: Optional[float] = None
    if n_w_3 is not None:
        w_3_limit = L / _require_positive(n_w_3, "span_ratio_w_3")
        checks["w_3"] = compute_utilisation(abs(w_3), w_3_limit)
    if span_ratio_w_max is not None:
        w_max_limit = L / _require_positive(span_ratio_w_max, "span_ratio_w_max")
        checks["w_max"] = compute_utilisation(abs(w_max), w_max_limit)
    if not checks:
        raise ValueError(f"No deflection limit for member '{member}'; pass span_ratio_w_3 (e.g to suit the cladding) or span_ratio_w_max.")

    governing: str = max(checks, key=lambda key: checks[key])
    return VerticalDeflectionResult(
        w_c=w_c,
        w_1=w_1,
        w_2=w_2,
        w_3=w_3,
        w_tot=w_tot,
        w_max=w_max,
        L=L,
        member=member,
        span_ratio_w_3=n_w_3,
        span_ratio_w_max=span_ratio_w_max,
        w_3_limit=w_3_limit,
        w_max_limit=w_max_limit,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(checks[governing], "7.2.1", None, f"Vertical deflection: {governing}", w_3=w_3, w_max=w_max),
        reference=_reference("7.2.1", title="Vertical deflections", notes="EN 1990 A1.4.3, Figure A1.1"),
    )


def check_beam_deflection(
    section: Optional[BaseSection] = None,
    L: float = 0.0,
    G_k: float = 0.0,
    Q_k: float = 0.0,
    support: Support = "simply_supported",
    loading: Loading = "uniform",
    member: Optional[str] = None,
    self_weight: bool = False,
    w_c: float = 0.0,
    w_2: float = 0.0,
    span_ratio_w_3: Optional[float] = None,
    span_ratio_w_max: Optional[float] = None,
    axis: BendingAxis = "y",
    I: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> VerticalDeflectionResult:
    """EN 1993-1-1 7.2.1: Vertical deflection of a single-span beam or a cantilever from its loads; w_1 from G_k and w_3 from Q_k.

    Args:
        section: EU/UK section; I is read from the section tables
        L: Span, or length of the cantilever (mm)
        G_k: Permanent load (N/mm = kN/m for "uniform", N for "concentrated")
        Q_k: Variable load of the SLS combination, in the units of G_k; combine several variable actions with sls_combination()
        support, loading: See beam_deflection()
        member: VERTICAL_DEFLECTION_LIMITS key; by default "cantilever" for cantilevers and "beam" otherwise
        self_weight: Add the member's self weight, from the mass per metre in the tables, to the permanent loads
        w_c: Precamber (mm)
        w_2: Long-term deflection under the permanent loads (mm)
        span_ratio_w_3, span_ratio_w_max: n in the limits L/n; see check_vertical_deflection()
        axis: Axis of bending, "y" (major) or "z" (minor)
        I: Second moment of area (mm⁴); overrides the section value
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("y", "z"):
        raise ValueError("axis must be 'y' or 'z'.")
    _, data, raw = _section_data(section, section_type, properties)
    I_value: float = _require_positive(I if I is not None else data.get(f"I_{axis}"), f"I_{axis}")
    L = _require_positive(L, "L")
    g_self: float = line_load_from_mass(_mass_per_metre(raw)) if self_weight else 0.0 # N/mm
    w_1: float = beam_deflection(G_k, L, I_value, support, loading, E) + beam_deflection(g_self, L, I_value, support, "uniform", E)
    w_3: float = beam_deflection(Q_k, L, I_value, support, loading, E)
    member_value: Optional[str] = member if member is not None else ("cantilever" if support == "cantilever" else "beam")
    result: VerticalDeflectionResult = check_vertical_deflection(L, w_3, w_1, w_2, w_c, member_value, span_ratio_w_3, span_ratio_w_max)
    result.metadata.update({"I": I_value, "support": support, "loading": loading, "g_self": g_self, "axis": axis})
    return result


# --- 7.2.2 Horizontal deflections ---
class HorizontalDeflectionResult(BaseModel):
    # 7.2.2 Horizontal deflections, with the definitions of EN 1990 A1.4.3 and Figure A1.2
    u: float # overall horizontal displacement over the building height H, Σu_i, mm
    H: float # building height, ΣH_i, mm
    u_i: list[float] # horizontal displacement over each storey height, mm
    H_i: list[float] # storey heights, mm
    structure: Optional[str] = None # HORIZONTAL_DEFLECTION_LIMITS key
    height_ratio_u_i: Optional[float] = None # n in H_i/n
    height_ratio_u: Optional[float] = None # n in H/n
    u_i_limits: list[float] = Field(default_factory=list) # H_i/n, mm
    u_limit: Optional[float] = None # H/n, mm
    limit_state: LimitState = LimitState.HORIZONTAL_DEFLECTION
    utilisations: dict[str, float] # e.g {"u_1": 0.69, "u_2": 0.81, "u": 1.17}
    governing: str # key of the largest utilisation
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_horizontal_deflection(
    u_i: float | Sequence[float],
    H_i: float | Sequence[float],
    structure: Optional[str] = "multi_storey",
    height_ratio_u_i: Optional[float] = None,
    height_ratio_u: Optional[float] = None,
) -> HorizontalDeflectionResult:
    """EN 1993-1-1 7.2.2: Horizontal deflections to EN 1990 A1.4.3 and Figure A1.2, storey by storey (u_i over H_i) and
    over the building height (u over H).

    Args:
        u_i: Horizontal displacement over each storey height, the drift relative to the floor below (mm), from the
            ground up; a single value for a single storey
        H_i: Height of each storey (mm)
        structure: HORIZONTAL_DEFLECTION_LIMITS key for the storey limit, "single_storey", "portal_frame" or
            "multi_storey"; None to check only the height ratios given
        height_ratio_u_i: n in the limit H_i/n on each u_i, e.g 300; overrides `structure`
        height_ratio_u: n in the limit H/n on the overall u, e.g 500
    """
    drifts: list[float] = [float(u_i)] if isinstance(u_i, (int, float)) else [float(value) for value in u_i]
    heights: list[float] = [float(H_i)] if isinstance(H_i, (int, float)) else [float(value) for value in H_i]
    if not drifts or len(drifts) != len(heights):
        raise ValueError("Pass one storey height H_i for each horizontal displacement u_i.")
    heights = [_require_positive(value, "H_i") for value in heights]
    u: float = sum(drifts)
    H: float = sum(heights)
    n_u_i: Optional[float] = height_ratio_u_i if height_ratio_u_i is not None else _limit(HORIZONTAL_DEFLECTION_LIMITS, structure, "structure")
    checks: dict[str, float] = {}
    u_i_limits: list[float] = []
    u_limit: Optional[float] = None
    if n_u_i is not None:
        n_u_i = _require_positive(n_u_i, "height_ratio_u_i")
        u_i_limits = [value / n_u_i for value in heights]
        for index, (drift, limit) in enumerate(zip(drifts, u_i_limits), start=1):
            checks[f"u_{index}"] = compute_utilisation(abs(drift), limit)
    if height_ratio_u is not None:
        u_limit = H / _require_positive(height_ratio_u, "height_ratio_u")
        checks["u"] = compute_utilisation(abs(u), u_limit)
    if not checks:
        raise ValueError(f"No deflection limit for structure '{structure}'; pass height_ratio_u_i (e.g to suit the cladding) or height_ratio_u.")

    governing: str = max(checks, key=lambda key: checks[key])
    return HorizontalDeflectionResult(
        u=u,
        H=H,
        u_i=drifts,
        H_i=heights,
        structure=structure,
        height_ratio_u_i=n_u_i,
        height_ratio_u=height_ratio_u,
        u_i_limits=u_i_limits,
        u_limit=u_limit,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(checks[governing], "7.2.2", None, f"Horizontal deflection: {governing}", u=u),
        reference=_reference("7.2.2", title="Horizontal deflections", notes="EN 1990 A1.4.3, Figure A1.2"),
    )


# --- 7.2.3 Dynamic effects ---
def natural_frequency(I: float, m: float, L: float, support: Support = "simply_supported", E: float = E_STEEL) -> float:
    """First natural frequency of a uniform beam under uniform mass, f = K/(2π)*sqrt(E*I/(m*L⁴)) (Hz); Euler-Bernoulli.

    K = π² simply supported, 22.37 both ends fixed, 15.42 one end fixed and the other pinned, 3.516 cantilever.

    Args:
        I: Second moment of area about the axis of bending (mm⁴)
        m: Vibrating mass per unit length (kg/m), e.g the member and the floor it carries
        L: Span, or length of the cantilever (mm)
        support: "simply_supported", "both_ends_fixed", "one_end_fixed" or "cantilever"
        E: Modulus of elasticity (N/mm²)
    """
    if support not in FREQUENCY_COEFFICIENTS:
        raise ValueError(f"Unknown support '{support}'; expected one of {', '.join(FREQUENCY_COEFFICIENTS)}.")
    EI: float = E * _require_positive(I, "I") * 1e-6 # Nmm² -> Nm²
    L_m: float = _require_positive(L, "L") / 1e3 # mm -> m
    return FREQUENCY_COEFFICIENTS[support] / (2.0 * math.pi) * math.sqrt(EI / (_require_positive(m, "m") * L_m**4))


def natural_frequency_from_deflection(delta: float, coefficient: float = 18.0) -> float:
    """First natural frequency of a simply supported member from its deflection under the vibrating mass, f = 18/sqrt(δ) (Hz).

    The coefficient for a uniform beam under uniform mass is (π/2)sqrt(5g/384) = 17.75, with δ in mm; 18 is the usual
    rounding.

    Args:
        delta: Instantaneous deflection under the weight of the vibrating mass (mm)
        coefficient: 18 by default
    """
    return coefficient / math.sqrt(_require_positive(delta, "delta"))


class VibrationResult(BaseModel):
    # 7.2.3 Dynamic effects: EN 1990 A1.4.4(4), the natural frequency is kept above a value agreed with the client
    f: float # first natural frequency, Hz
    f_min: float # minimum natural frequency, Hz
    m: Optional[float] = None # vibrating mass per unit length, kg/m
    delta: Optional[float] = None # instantaneous deflection under the weight of the vibrating mass, mm
    L: Optional[float] = None # span, mm
    support: Optional[Support] = None
    limit_state: LimitState = LimitState.VIBRATION
    utilisation: UtilisationCheck # f_min/f
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_vibration(
    section: Optional[BaseSection] = None,
    L: Optional[float] = None,
    w: float = 0.0,
    f: Optional[float] = None,
    f_min: float = F_MIN,
    support: Support = "simply_supported",
    self_weight: bool = True,
    I: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> VibrationResult:
    """EN 1993-1-1 7.2.3: Vertical vibration of a floor beam, f >= f_min, to EN 1990 A1.4.4(4).

    f is the frequency of the beam under its uniform mass, from natural_frequency(), unless given. Where f < f_min,
    EN 1990 A1.4.4(5) calls for a refined analysis of the dynamic response, including damping, e.g SCI P354 in the UK.

    Args:
        section: EU/UK section; I_y and the mass per metre are read from the section tables
        L: Span (mm)
        w: Weight of the vibrating mass other than the member, as a line load (N/mm = kN/m), e.g the slab, finishes and a
            proportion of the imposed load it carries
        f: Natural frequency from a separate analysis (Hz); skips the calculation
        f_min: Minimum natural frequency (Hz), agreed with the client; 3 Hz by default, see F_MIN
        support: "simply_supported", "both_ends_fixed", "one_end_fixed" or "cantilever"
        self_weight: Add the member's mass per metre to the vibrating mass
        I: Second moment of area (mm⁴); overrides the section's I_y
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    f_min = _require_positive(f_min, "f_min")
    m: Optional[float] = None
    delta: Optional[float] = None
    if f is None:
        _, data, raw = _section_data(section, section_type, properties)
        L = _require_positive(L, "L")
        I_value: float = _require_positive(I if I is not None else data.get("I_y"), "I_y")
        m = mass_from_line_load(w) + (_mass_per_metre(raw) if self_weight else 0.0)
        f = natural_frequency(I_value, m, L, support, E)
        delta = beam_deflection(line_load_from_mass(m), L, I_value, support, "uniform", E)
    f = _require_positive(f, "f")
    notes: list[str] = []
    if f < f_min:
        notes.append("EN 1990 A1.4.4(5): f < f_min; carry out a refined analysis of the dynamic response, including damping.")
    return VibrationResult(
        f=f,
        f_min=f_min,
        m=m,
        delta=delta,
        L=L,
        support=support if m is not None else None,
        utilisation=_ratio_check(f_min / f, "7.2.3", None, "Natural frequency", f=f, f_min=f_min),
        reference=_reference("7.2.3", title="Dynamic effects", notes="EN 1990 A1.4.4"),
        metadata={"notes": notes} if notes else {},
    )


if __name__ == "__main__":
    from steelsnakes.EU.sections.beams import IPE

    beam = IPE("IPE-300")
    Q_k = sls_combination(variable=[(7.5, "B"), (1.2, "snow")]) # kN/m, characteristic combination
    print(check_beam_deflection(beam, L=6000.0, G_k=5.0, Q_k=Q_k, member="brittle_finish", self_weight=True).model_dump())
    print(check_horizontal_deflection([8.0, 9.5, 7.0], [3500.0, 3500.0, 3500.0], height_ratio_u=500.0).model_dump())
    print(check_vibration(beam, L=6000.0, w=5.0 + 0.1 * 7.5).model_dump())
    print(check_serviceability_stresses(beam, 355.0, M_y_Ed_ser=100e6, V_z_Ed_ser=60e3).model_dump())
    print("🐬")
