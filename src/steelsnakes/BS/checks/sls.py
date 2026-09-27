# BS 5950-1:2000: SERVICEABILITY LIMIT STATES
# 2.5.1 Serviceability loads
# 2.5.2 Deflection: Table 8, suggested limits for calculated deflections
# 2.5.3 Vibration and oscillation
# NOTE: Table 8 gives suggested limits; greater or lesser values may be more appropriate (2.5.2), so every check takes a
# ... span ratio to override them. On low pitched and flat roofs ponding should also be investigated (2.5.2).
# NOTE: units: line loads kN/m (1 kN/m = 1 N/mm), point loads kN, lengths mm, I cm⁴ as tabulated, E N/mm² [MPa];
# ... deflections in mm and frequencies in Hz.
from __future__ import annotations

import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from steelsnakes.base.checks import LimitState, Reference, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.BS.checks.uls import E_STEEL, BendingAxis, _get, _ratio_check, _reference, _require_positive, _section_data

IMPOSED_WITH_WIND_FACTOR = 0.8 # 2.5.1: combined imposed and wind loads, 80 % of the specified values
F_MIN = 3.0 # Hz; 2.5.3 refers to specialist literature: SCI P076 (reference [3]) for floors on which people walk

Support = Literal["simply_supported", "both_ends_fixed", "one_end_fixed", "cantilever"] # one_end_fixed: the other end pinned
Loading = Literal["uniform", "concentrated"] # concentrated: at mid-span, or at the tip of a cantilever

# Table 8: Suggested limits for calculated deflections, as n in L/n (H/n); None where the limit is to suit the cladding
# ... or the crane runway
VERTICAL_DEFLECTION_LIMITS: dict[str, Optional[float]] = {
    "cantilever": 180.0, # a) cantilevers, due to imposed load: length/180
    "brittle_finish": 360.0, # a) beams carrying plaster or other brittle finish: span/360
    "beam": 200.0, # a) other beams, except purlins and sheeting rails: span/200
    "purlin": None, # a) purlins and sheeting rails: to suit the cladding, 4.12.2
    "crane_girder": 600.0, # c) crane girders, static vertical wheel loads from overhead travelling cranes: span/600
}
HORIZONTAL_DEFLECTION_LIMITS: dict[str, Optional[float]] = {
    "single_storey": 300.0, # b) tops of columns in single-storey buildings, except portal frames: height/300
    "portal_frame": None, # b) columns in portal frame buildings, not supporting crane runways: to suit cladding
    "crane_column": None, # b) columns supporting crane runways: to suit crane runway
    "multi_storey": 300.0, # b) in each storey of a building with more than one storey: height of that storey/300
    "crane_girder": 500.0, # c) crane girders, horizontal crane loads, on the top flange properties alone: span/500
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


def _limit(limits: dict[str, Optional[float]], key: Optional[str], name: str) -> Optional[float]:
    if key is None:
        return None
    if key not in limits:
        raise ValueError(f"Unknown {name} '{key}'; expected one of {', '.join(limits)}.")
    return limits[key]


# --- 2.5.1 Serviceability loads ---
def serviceability_load(imposed: float = 0.0, wind: float = 0.0, dead: float = 0.0) -> float:
    """BS 5950-1:2000 2.5.1: Serviceability load, the unfactored specified values.

    Imposed and wind loads acting together need only be taken at 80 % of their specified values. Exceptional snow load
    (local drifting, 7.4 of BS 6399-3) is not part of the imposed load at serviceability; nor, with horizontal crane loads
    and wind together, need more than the greater effect be considered. Table 8 limits the deflections under imposed load
    (and wind for columns), so `dead` is 0 by default.

    Args:
        imposed: Imposed load, excluding exceptional snow
        wind: Wind load
        dead: Dead load, where the deflection under it is also wanted
    """
    factor: float = IMPOSED_WITH_WIND_FACTOR if (imposed and wind) else 1.0
    return dead + factor * (imposed + wind)


# --- 2.5.2 Deflection ---
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
        E: Modulus of elasticity (N/mm²)
    """
    if (support, loading) not in DEFLECTION_COEFFICIENTS:
        raise ValueError(f"No deflection coefficient for support '{support}' with loading '{loading}'.")
    L = _require_positive(L, "L")
    W: float = load * L if loading == "uniform" else load * 1e3 # N
    return DEFLECTION_COEFFICIENTS[(support, loading)] * W * L**3 / (E * _require_positive(I, "I") * 1e4)


class DeflectionResult(BaseModel):
    # 2.5.2 Deflection under serviceability loads, against the suggested limits of Table 8
    delta: float # calculated deflection, mm
    length: float # span, length of a cantilever or storey height, mm
    case: Optional[str] = None # VERTICAL_DEFLECTION_LIMITS or HORIZONTAL_DEFLECTION_LIMITS key
    span_ratio: float # n in L/n (H/n)
    limit: float # L/n, mm
    limit_state: LimitState
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _check_deflection(delta: float, length: float, limits: dict[str, Optional[float]], case: Optional[str], span_ratio: Optional[float], limit_state: LimitState, title: str) -> DeflectionResult:
    length = _require_positive(length, "length")
    n: Optional[float] = span_ratio if span_ratio is not None else _limit(limits, case, "case")
    if n is None:
        raise ValueError(f"Table 8 sets no numerical limit for '{case}' (to suit the cladding or crane runway); pass span_ratio.")
    limit: float = length / _require_positive(n, "span_ratio")
    return DeflectionResult(
        delta=delta,
        length=length,
        case=case,
        span_ratio=n,
        limit=limit,
        limit_state=limit_state,
        utilisation=_ratio_check(compute_utilisation(abs(delta), limit), "2.5.2", title, span_ratio=n),
        reference=_reference("2.5.2", title="Table 8: Suggested limits for calculated deflections"),
    )


def check_vertical_deflection(delta: float, L: float, member: Optional[str] = "beam", span_ratio: Optional[float] = None) -> DeflectionResult:
    """BS 5950-1:2000 2.5.2 and Table 8 a), c): Vertical deflection of a beam, cantilever or crane girder.

    Args:
        delta: Calculated deflection under the serviceability loads, e.g due to imposed load (mm)
        L: Span, or length of a cantilever (mm)
        member: VERTICAL_DEFLECTION_LIMITS key, "cantilever" (L/180), "brittle_finish" (L/360), "beam" (L/200), "purlin"
            (to suit the cladding) or "crane_girder" (L/600, static vertical wheel loads)
        span_ratio: n in the limit L/n; overrides `member`
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
    axis: BendingAxis = "x",
    I: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> DeflectionResult:
    """BS 5950-1:2000 2.5.2: Vertical deflection of a single-span beam or a cantilever under its imposed load (Table 8 a)).

    Args:
        section: UK section; I is read from the section tables
        L: Span, or length of the cantilever (mm)
        imposed: Unfactored imposed load (kN/m for "uniform", kN for "concentrated"); see serviceability_load()
        support, loading: See beam_deflection()
        member: VERTICAL_DEFLECTION_LIMITS key; by default "cantilever" for cantilevers and "beam" otherwise
        span_ratio: n in the limit L/n; overrides `member`
        axis: Axis of bending, "x" (major) or "y" (minor)
        I: Second moment of area (cm⁴); overrides the section value
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("x", "y"):
        raise ValueError("axis must be 'x' (major) or 'y' (minor).")
    _, data, _ = _section_data(section, section_type, properties)
    I_value: float = _require_positive(I, "I") if I is not None else _get(data, f"I{axis}")
    delta: float = beam_deflection(imposed, L, I_value, support, loading, E)
    member_value: Optional[str] = member if member is not None else ("cantilever" if support == "cantilever" else "beam")
    result: DeflectionResult = check_vertical_deflection(delta, L, member_value, span_ratio)
    result.metadata.update({"I": I_value, "support": support, "loading": loading, "axis": axis})
    return result


def check_horizontal_deflection(delta: float, h: float, case: Optional[str] = "multi_storey", span_ratio: Optional[float] = None) -> DeflectionResult:
    """BS 5950-1:2000 2.5.2 and Table 8 b), c): Horizontal deflection of columns under imposed and wind load, or of crane
    girders under horizontal crane loads.

    Args:
        delta: Calculated deflection (mm): of the top of a single-storey column, within one storey (relative to the floor
            below), or of a crane girder on its top flange properties alone
        h: Height of the column or storey, or span of the crane girder (mm)
        case: HORIZONTAL_DEFLECTION_LIMITS key, "single_storey" (H/300), "multi_storey" (storey height/300),
            "portal_frame" and "crane_column" (to suit), or "crane_girder" (span/500)
        span_ratio: n in the limit H/n; overrides `case`
    """
    return _check_deflection(delta, h, HORIZONTAL_DEFLECTION_LIMITS, case, span_ratio, LimitState.HORIZONTAL_DEFLECTION, "Horizontal deflection")


# --- 2.5.3 Vibration and oscillation ---
def natural_frequency_from_deflection(delta: float) -> float:
    """Approximate natural frequency of a floor beam, f = 18/√δ (Hz), δ the instantaneous deflection under the
    self weight and the other permanent loads (mm); the approximation of SCI P076, reference [3] of BS 5950-1."""
    return 18.0 / math.sqrt(_require_positive(delta, "delta"))


class VibrationResult(BaseModel):
    # 2.5.3 Vibration and oscillation: BS 5950-1 refers to specialist literature, here SCI P076
    f: float # natural frequency, Hz
    f_min: float # Hz
    delta: Optional[float] = None # mm
    limit_state: LimitState = LimitState.VIBRATION
    utilisation: UtilisationCheck # f_min/f
    reference: Optional[Reference] = None


def check_vibration(delta: Optional[float] = None, f: Optional[float] = None, f_min: float = F_MIN) -> VibrationResult:
    """BS 5950-1:2000 2.5.3: Natural frequency of a floor against a minimum, f >= f_min.

    2.5.3 sets no limit; the 3 Hz default is the usual minimum for floors on which people walk (SCI P076); rhythmic
    activity, e.g gymnasia, calls for more.

    Args:
        delta: Instantaneous deflection under the permanent loads (mm), for natural_frequency_from_deflection()
        f: Natural frequency (Hz); overrides `delta`
        f_min: Minimum natural frequency (Hz)
    """
    if f is None:
        if delta is None:
            raise ValueError("Pass delta or f.")
        f = natural_frequency_from_deflection(delta)
    f = _require_positive(f, "f")
    return VibrationResult(
        f=f,
        f_min=f_min,
        delta=delta,
        utilisation=_ratio_check(f_min / f, "2.5.3", "Vibration", f=f),
        reference=_reference("2.5.3", title="Vibration and oscillation", notes="SCI P076, reference [3]"),
    )


if __name__ == "__main__":
    from steelsnakes.UK import UB

    beam = UB("457x191x67")
    print(check_beam_deflection(beam, L=6000.0, imposed=serviceability_load(imposed=20.0), member="brittle_finish").model_dump())
    print(check_horizontal_deflection(9.0, 3500.0).model_dump())
    print(check_vibration(delta=12.0).model_dump())
    print("🐬")
