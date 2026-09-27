# IS 800:2025 (DRAFT): SERVICEABILITY LIMIT STATES
# 12.6 Limit state of serviceability: γf = 1.0 for all loads unless Table 4 says otherwise
# 12.6.1 Deflection: Table 6 deflection limits; 12.6.1.1 camber
# 12.6.2 Vibration: Annex C design against floor vibration; C-2 annoyance criteria, C-3 floor frequency, C-4 damping,
# ... C-5 acceleration from heel impact
# NOTE: Table 6 gives recommended limits; greater or lesser values may be more appropriate (12.6.1), so every check takes
# ... a span ratio to override them. Imposed load includes all post construction loads, superimposed dead loads too.
# NOTE: units: line loads kN/m (1 kN/m = 1 N/mm), point loads kN, lengths mm, I cm⁴ as tabulated, E N/mm² [MPa];
# ... deflections in mm and frequencies in Hz.
from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from steelsnakes.base.checks import LimitState, Reference, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.IN.checks.uls import E_STEEL, BendingAxis, _get, _ratio_check, _reference, _require_positive, _section_data, factored_load

Support = Literal["simply_supported", "both_ends_fixed", "one_end_fixed", "cantilever"] # one_end_fixed: the other end pinned
Loading = Literal["uniform", "concentrated"] # concentrated: at mid-span, or at the tip of a cantilever

# Table 6: Deflection limits, as n in span/n (height/n), under the design load of the row
VERTICAL_DEFLECTION_LIMITS: dict[str, float] = {
    # Industrial buildings
    "purlin_elastic": 150.0, # purlins and girts, imposed and wind load, elastic cladding
    "purlin_brittle": 180.0, # purlins and girts, brittle cladding
    "industrial_beam_elastic": 240.0, # simple span, imposed load, elastic cladding
    "industrial_beam_brittle": 300.0, # simple span, brittle cladding
    "industrial_cantilever_elastic": 120.0, # cantilever span, imposed load, elastic cladding
    "industrial_cantilever_brittle": 150.0, # cantilever span, brittle cladding
    "rafter_profiled_sheeting": 180.0, # rafter supporting profiled metal sheeting, imposed load
    "rafter_plastered_sheeting": 240.0, # rafter supporting plastered sheeting
    "gantry_manual": 500.0, # gantry, crane load (manual operation), wheels of crane
    "gantry_electric_up_to_50t": 750.0, # gantry, crane load (electric operation up to 50 t)
    "gantry_electric_over_50t": 1_000.0, # gantry, crane load (electric operation over 50 t)
    # Other buildings, imposed load
    "floor_not_susceptible": 300.0, # floor and roof, elements not susceptible to cracking
    "floor_susceptible": 360.0, # floor and roof, elements susceptible to cracking
    "cantilever_not_susceptible": 150.0, # cantilever, elements not susceptible to cracking
    "cantilever_susceptible": 180.0, # cantilever, elements susceptible to cracking
}
HORIZONTAL_DEFLECTION_LIMITS: dict[str, float] = {
    # Industrial buildings
    "column_elastic": 150.0, # column, no cranes (due to wind), elastic cladding: height/150
    "column_brittle": 240.0, # column, no cranes, masonry/brittle cladding: height/240
    "gantry_lateral": 400.0, # gantry (lateral), crane load and wind load, absolute: span/400
    "column_gantry_elastic": 200.0, # column/frame, crane load and wind load, gantry, elastic cladding: height/200
    "column_gantry_brittle": 400.0, # column/frame, gantry, brittle cladding; cab operated: height/400
    # Other buildings, wind load
    "building_elastic": 300.0, # building, elastic cladding: height/300
    "building_brittle": 500.0, # building, brittle cladding: height/500
    "inter_storey_drift": 300.0, # storey height/300
}
CRANE_RAIL_RELATIVE_DISPLACEMENT = 25.0 # mm; Table 6: relative displacement between rails supporting the crane (note 1)
CAMBER_SPAN = 25_000.0 # mm; 12.6.1.1: spans greater than 25 m

# Annex C: design against floor vibration
FLOOR_FREQUENCY_LIMITS: dict[str, float] = {"normal": 5.0, "rhythmic": 8.0} # Hz; C-2
ANNOYANCE_ACCELERATION = 0.005 # g; C-2: threshold level in the 2 Hz to 8 Hz range, 0.5 percent g
FLOOR_DAMPING: dict[str, tuple[Optional[float], float]] = { # C-4: percent of critical damping, (from, to)
    "fully_composite": (2.0, 2.0),
    "bare_steel_beam_concrete_deck": (3.0, 4.0),
    "finishes_ceiling_ducts_furniture": (6.0, 6.0), # floor with finishes, false ceiling, fire proofing, ducts, furniture
    "partitions": (None, 12.0), # up to 12: partitions not along a support, or within 6 m, orthogonal
}

# Maximum elastic deflection of a uniform beam, δ = k*W*L³/(E*I), W the total load (w*L for uniform loading)
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


def _limit(limits: dict[str, float], key: Optional[str], name: str) -> Optional[float]:
    if key is None:
        return None
    if key not in limits:
        raise ValueError(f"Unknown {name} '{key}'; expected one of {', '.join(limits)}.")
    return limits[key]


# --- 12.6 Serviceability loads ---
def serviceability_load(
    combination: str = "DL+IL+CL",
    imposed: float = 0.0,
    imposed_accompanying: float = 0.0,
    wind: float = 0.0,
    dead: float = 0.0,
) -> float:
    """IS 800:2025 12.6 and Table 4: Load for the limit state of serviceability.

    γf = 1.0, except with wind or earthquake effects, where imposed and wind loads take 0.8 ("DL+IL+CL+WL/EL"). Table 6
    limits the deflections under imposed load (and wind for columns), so `dead` is 0 by default.

    Args:
        combination: "DL+IL+CL", "DL+IL+CL+WL/EL" or "DL+WL/EL"
        imposed: Leading imposed load, including crane loads
        imposed_accompanying: Accompanying imposed loads
        wind: Wind load or earthquake effects
        dead: Dead load, where the deflection under it is also wanted
    """
    return factored_load(combination, dead, imposed, imposed_accompanying, wind, limit_state="serviceability").factored


# --- 12.6.1 Deflection ---
def beam_deflection(load: float, L: float, I: float, support: Support = "simply_supported", loading: Loading = "uniform", E: float = E_STEEL) -> float:
    """Maximum elastic deflection of a uniform beam, δ = k*W*L³/(E*I) (mm); shear deformation is ignored.

    simply supported: 5wL⁴/(384EI) uniform, PL³/(48EI) concentrated at mid-span
    both ends fixed: wL⁴/(384EI), PL³/(192EI)
    one end fixed, the other pinned: wL⁴/(184.6EI), PL³/(48√5EI)
    cantilever: wL⁴/(8EI), PL³/(3EI) concentrated at the tip

    Args:
        load: Line load w (kN/m) for "uniform", or point load P (kN) for "concentrated"
        L: Span, or length of the cantilever (mm)
        I: Second moment of area about the axis of bending (cm⁴)
        support: "simply_supported", "both_ends_fixed", "one_end_fixed" or "cantilever"
        loading: "uniform", or "concentrated" at mid-span (at the tip of a cantilever)
        E: Modulus of elasticity (N/mm²), 2.0 x 10⁵ (9.2.4.1)
    """
    if (support, loading) not in DEFLECTION_COEFFICIENTS:
        raise ValueError(f"No deflection coefficient for support '{support}' with loading '{loading}'.")
    L = _require_positive(L, "L")
    W: float = load * L if loading == "uniform" else load * 1e3 # N
    return DEFLECTION_COEFFICIENTS[(support, loading)] * W * L**3 / (E * _require_positive(I, "I") * 1e4)


def recommended_camber(delta_dead: float, delta_imposed: float) -> float:
    """IS 800:2025 12.6.1.1: camber approximately equal to the deflection due to dead load plus half the imposed load (mm),
    generally for spans greater than 25 m (CAMBER_SPAN); deflections without impact or dynamic effects."""
    return delta_dead + 0.5 * delta_imposed


class DeflectionResult(BaseModel):
    # 12.6.1 Deflection under serviceability loads, against the limits of Table 6
    delta: float # calculated deflection, mm
    length: Optional[float] = None # span, length of a cantilever, height or storey height, mm
    case: Optional[str] = None # VERTICAL_DEFLECTION_LIMITS or HORIZONTAL_DEFLECTION_LIMITS key
    span_ratio: Optional[float] = None # n in span/n (height/n); None for an absolute limit
    limit: float # mm
    limit_state: LimitState
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _check_deflection(delta: float, length: float, limits: dict[str, float], case: Optional[str], span_ratio: Optional[float], limit_state: LimitState, title: str) -> DeflectionResult:
    length = _require_positive(length, "length")
    n: Optional[float] = span_ratio if span_ratio is not None else _limit(limits, case, "case")
    if n is None:
        raise ValueError("Pass a Table 6 case or span_ratio.")
    limit: float = length / _require_positive(n, "span_ratio")
    return DeflectionResult(
        delta=delta,
        length=length,
        case=case,
        span_ratio=n,
        limit=limit,
        limit_state=limit_state,
        utilisation=_ratio_check(compute_utilisation(abs(delta), limit), "12.6.1", title, span_ratio=n),
        reference=_reference("12.6.1", title="Table 6: Deflection limits"),
    )


def check_vertical_deflection(delta: float, L: float, member: Optional[str] = "floor_not_susceptible", span_ratio: Optional[float] = None) -> DeflectionResult:
    """IS 800:2025 12.6.1 and Table 6: Vertical deflection of a purlin, beam, cantilever, rafter or gantry.

    Args:
        delta: Calculated deflection under the serviceability loads (mm)
        L: Span, or length of a cantilever (mm)
        member: VERTICAL_DEFLECTION_LIMITS key, e.g "floor_not_susceptible" (span/300), "floor_susceptible" (span/360),
            "cantilever_susceptible" (span/180), "purlin_elastic" (span/150) or "gantry_electric_up_to_50t" (span/750)
        span_ratio: n in the limit span/n; overrides `member`
    """
    return _check_deflection(delta, L, VERTICAL_DEFLECTION_LIMITS, member, span_ratio, LimitState.VERTICAL_DEFLECTION, "Vertical deflection")


def check_beam_deflection(
    section: Optional[BaseSection] = None,
    L: float = 0.0,
    imposed: float = 0.0,
    support: Support = "simply_supported",
    loading: Loading = "uniform",
    member: Optional[str] = None,
    span_ratio: Optional[float] = None,
    axis: BendingAxis = "z",
    I: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> DeflectionResult:
    """IS 800:2025 12.6.1: Vertical deflection of a single-span beam or a cantilever under its imposed load (Table 6).

    Args:
        section: IN section; I is read from the section tables
        L: Span, or length of the cantilever (mm)
        imposed: Unfactored imposed load (kN/m for "uniform", kN for "concentrated"); see serviceability_load()
        support, loading: See beam_deflection()
        member: VERTICAL_DEFLECTION_LIMITS key; by default "cantilever_not_susceptible" for cantilevers and
            "floor_not_susceptible" otherwise (other buildings, elements not susceptible to cracking)
        span_ratio: n in the limit span/n; overrides `member`
        axis: Axis of bending, "z" (major) or "y" (minor)
        I: Second moment of area (cm⁴); overrides the section value
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("z", "y"):
        raise ValueError("axis must be 'z' (major) or 'y' (minor).")
    _, data, _ = _section_data(section, section_type, properties)
    I_value: float = _require_positive(I, "I") if I is not None else _get(data, f"I{axis}")
    delta: float = beam_deflection(imposed, L, I_value, support, loading, E)
    member_value: Optional[str] = member if member is not None else ("cantilever_not_susceptible" if support == "cantilever" else "floor_not_susceptible")
    result: DeflectionResult = check_vertical_deflection(delta, L, member_value, span_ratio)
    result.metadata.update({"I": I_value, "support": support, "loading": loading, "axis": axis})
    return result


def check_horizontal_deflection(delta: float, h: float, case: Optional[str] = "building_elastic", span_ratio: Optional[float] = None) -> DeflectionResult:
    """IS 800:2025 12.6.1 and Table 6: Lateral deflection of columns, frames and buildings, or of gantries under crane
    and wind loads.

    Args:
        delta: Calculated deflection (mm): at the top of a column or building, within one storey (drift), or of a gantry
        h: Height of the column or building, storey height, or span of the gantry (mm)
        case: HORIZONTAL_DEFLECTION_LIMITS key, e.g "building_elastic" (height/300), "building_brittle" (height/500),
            "inter_storey_drift" (storey height/300), "column_elastic" (height/150) or "gantry_lateral" (span/400)
        span_ratio: n in the limit h/n; overrides `case`
    """
    return _check_deflection(delta, h, HORIZONTAL_DEFLECTION_LIMITS, case, span_ratio, LimitState.HORIZONTAL_DEFLECTION, "Lateral deflection")


def check_crane_rail_displacement(delta: float, limit: float = CRANE_RAIL_RELATIVE_DISPLACEMENT) -> DeflectionResult:
    """IS 800:2025 Table 6: Relative displacement between the rails supporting a crane, 25 mm under crane and wind loads;
    the crane supplier may be consulted for higher values (note 1).

    Args:
        delta: Relative lateral displacement between the rails (mm)
        limit: Limit (mm)
    """
    limit = _require_positive(limit, "limit")
    return DeflectionResult(
        delta=delta,
        limit=limit,
        case="crane_rails",
        limit_state=LimitState.HORIZONTAL_DEFLECTION,
        utilisation=_ratio_check(compute_utilisation(abs(delta), limit), "12.6.1", "Relative displacement of crane rails"),
        reference=_reference("12.6.1", title="Table 6: Deflection limits"),
    )


# --- 12.6.2 Vibration: Annex C ---
def floor_frequency(I_T_cm4: float, W_kN_m: float, L_mm: float, E: float = E_STEEL) -> float:
    """IS 800:2025 C-3: Fundamental natural frequency of a simply supported one way floor system, f1 = 156(E IT/(W L⁴))^0.5
    (Hz), assuming full composite action even in non-composite construction.

    Args:
        I_T_cm4: Transformed moment of inertia of the one way system in equivalent steel, the concrete flange as wide as
            the beam spacing (cm⁴)
        W_kN_m: Dead load of the one way joist (kN/m, i.e N/mm)
        L_mm: Span (mm)
        E: Modulus of elasticity of steel (MPa)
    """
    I_T: float = _require_positive(I_T_cm4, "I_T_cm4") * 1e4
    return 156.0 * math.sqrt(E * I_T / (_require_positive(W_kN_m, "W_kN_m") * _require_positive(L_mm, "L_mm") ** 4))


def combined_floor_frequency(f1: float, f2: float) -> float:
    """IS 800:2025 C-3: Floor frequency fr of a one way system (f1) on a flexible perpendicular beam (f2),
    1/fr² = 1/f1² + 1/f2² (Hz)."""
    return 1.0 / math.sqrt(1.0 / _require_positive(f1, "f1") ** 2 + 1.0 / _require_positive(f2, "f2") ** 2)


def effective_floor_width(t_s_mm: float, one_side: bool = False) -> float:
    """IS 800:2025 C-5: Equivalent floor width b = 40ts, or 20ts with an overhang on one side of the beam only (mm);
    ts the equivalent slab thickness, averaging the concrete in slab and ribs."""
    return (20.0 if one_side else 40.0) * _require_positive(t_s_mm, "t_s_mm")


def heel_impact_acceleration(f_r: float, W_kN: float) -> float:
    """IS 800:2025 C-5: Peak acceleration from heel impact, a0/g = 600 fr/W, W the total weight of the floor plus
    contents over the span and the equivalent floor width in N; for spans over 7 m and f1 below 10 Hz.

    Args:
        f_r: Floor frequency (Hz)
        W_kN: Total weight (kN)

    Returns:
        a0/g
    """
    return 600.0 * _require_positive(f_r, "f_r") / (_require_positive(W_kN, "W_kN") * 1e3)


class VibrationResult(BaseModel):
    # 12.6.2 and Annex C: floor frequency against C-2, with the heel impact acceleration of C-5
    f: float # floor frequency fr (f1 without a flexible supporting beam), Hz
    f1: Optional[float] = None # Hz; C-3
    f2: Optional[float] = None # Hz; the supporting beam
    f_min: float # Hz; C-2
    activity: str # "normal" or "rhythmic"
    a0_g: Optional[float] = None # C-5, a0/g
    limit_state: LimitState = LimitState.VIBRATION
    utilisation: UtilisationCheck # f_min/f
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_vibration(
    f: Optional[float] = None,
    I_T_cm4: Optional[float] = None,
    W_kN_m: Optional[float] = None,
    L_mm: Optional[float] = None,
    f2: Optional[float] = None,
    activity: Literal["normal", "rhythmic"] = "normal",
    W_total_kN: Optional[float] = None,
    E: float = E_STEEL,
) -> VibrationResult:
    """IS 800:2025 12.6.2 and Annex C: Floor frequency against C-2, f >= 5 Hz (normal human activity) or 8 Hz (rhythmic).

    The frequency is f, or f1 of C-3 from I_T_cm4, W_kN_m and L_mm, reduced to fr with a flexible supporting beam of
    frequency f2. With W_total_kN, the heel impact acceleration a0/g of C-5 is added and compared, as information, with
    the 0.5 % g threshold of C-2 (C-5 applies to spans over 7 m with f1 below 10 Hz).

    Args:
        f: Floor frequency (Hz); overrides C-3
        I_T_cm4, W_kN_m, L_mm: See floor_frequency()
        f2: Natural frequency of the flexible supporting beam (Hz)
        activity: "normal" or "rhythmic"
        W_total_kN: Total weight of the floor and contents over the span and the equivalent floor width (kN), C-5
        E: Modulus of elasticity (MPa)
    """
    if activity not in FLOOR_FREQUENCY_LIMITS:
        raise ValueError(f"activity must be one of {', '.join(FLOOR_FREQUENCY_LIMITS)}.")
    f1: Optional[float] = None
    if f is None:
        if I_T_cm4 is None or W_kN_m is None or L_mm is None:
            raise ValueError("Pass f, or I_T_cm4, W_kN_m and L_mm for C-3.")
        f1 = floor_frequency(I_T_cm4, W_kN_m, L_mm, E)
        f = combined_floor_frequency(f1, f2) if f2 is not None else f1
    f = _require_positive(f, "f")
    f_min: float = FLOOR_FREQUENCY_LIMITS[activity]
    notes: list[str] = []
    a0_g: Optional[float] = None
    if W_total_kN is not None:
        a0_g = heel_impact_acceleration(f, W_total_kN)
        if a0_g > ANNOYANCE_ACCELERATION:
            notes.append(f"C-2: a0/g = {a0_g:.4f} exceeds the 0.5 % g threshold of perception.")
        if (L_mm is not None and L_mm <= 7_000.0) or (f1 or f) >= 10.0:
            notes.append("C-5 applies to spans over 7 m with f1 below 10 Hz.")
    return VibrationResult(
        f=f,
        f1=f1,
        f2=f2,
        f_min=f_min,
        activity=activity,
        a0_g=a0_g,
        utilisation=_ratio_check(f_min / f, "C-2", "Floor vibration", f=f),
        reference=_reference("12.6.2", title="Vibration; Annex C design against floor vibration"),
        metadata={"notes": notes} if notes else {},
    )


if __name__ == "__main__":
    from steelsnakes.IN.sections import MediumWeightBeam

    beam = MediumWeightBeam(designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26, I_zz=8603.6, I_yy=453.9)
    print(check_beam_deflection(beam, L=6000.0, imposed=serviceability_load(imposed=10.0), member="floor_susceptible").model_dump())
    print(check_horizontal_deflection(9.0, 3500.0, "inter_storey_drift").model_dump())
    print(check_vibration(I_T_cm4=40_000.0, W_kN_m=8.0, L_mm=9000.0).model_dump())
    print("🐬")
