# BS 5950-1:2000: ULTIMATE LIMIT STATES
# 2.4 Ultimate limit states: 2.4.1 strength (Table 2), 2.4.2 stability, 2.4.4 brittle fracture, 2.4.5 structural integrity
# 3.4 Section properties: net and effective net areas
# 3.6 Slender cross-sections: effective properties, or the reduced design strength
# 4 Design of structural members: 4.2 bending, 4.3 lateral-torsional buckling, 4.4.5 shear buckling, 4.5 web bearing
# ... and buckling, 4.6 tension, 4.7 compression, 4.8 combined moment and axial force, 4.9 biaxial moments
# Annex B: lateral-torsional buckling; Annex C: compressive strength; Annex H: shear buckling strength (H.1, H.2);
# ... Annex I: combined axial compression and bending (I.1 stocky members, I.2 reduced plastic moment capacity)
# NOTE: units follow BS 5950 practice and the UK section tables: forces kN, moments kNm, stresses N/mm² [MPa], lengths
# ... mm; section properties as tabulated: A cm², Z and S cm³, I and J cm⁴, r cm and H dm⁶. Values passed through
# ... `properties` use the same units, with the UK table keys (h, b, tw, tf, d, r, A, I_yy, W_pl_yy, U, X, I_w, I_t, ...)
# ... or the BS notation (D, B, t, T, d, A, Ix, Sx, u, x, H, J).
# NOTE: BS 5950 axes: x-x is the major axis and y-y the minor axis, i.e. y-y and z-z of the UK tables; angles use u-u and
# ... v-v for their principal axes. Design forces and moments are magnitudes; Fc is compression and Ft tension.
# NOTE: py defaults to Table 9 for `steel_grade` and the thickest element of the section, as in the classification.
from __future__ import annotations

import math
import re
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.BS.checks.classification import (
    _CLASS_RANK,
    CF_RHS_SECTION_TYPES,
    CHANNEL_SECTION_TYPES,
    CHS_SECTION_TYPES,
    DOUBLE_ANGLE_SECTION_TYPES,
    HF_RHS_SECTION_TYPES,
    ROLLED_I_SECTION_TYPES,
    SINGLE_ANGLE_SECTION_TYPES,
    ClassificationResult,
    ElementClassification,
    StressPattern,
    _normalize_stress_pattern,
    classify_section_from_dict,
    design_strength,
    effective_plastic_modulus,
    epsilon,
)

BS_5950 = DesignCode.BS_5950_1

# 3.1.3 Other properties
E_STEEL = 205_000.0 # N/mm² [MPa]; modulus of elasticity
POISSON_RATIO = 0.30
G_STEEL = E_STEEL / (2.0 * (1.0 + POISSON_RATIO)) # N/mm² [MPa]; shear modulus G = E/[2(1 + ν)]
THERMAL_EXPANSION = 12e-6 # per °C; coefficient of linear thermal expansion
# B.2.2 and C.2: Robertson constants of the Perry formula
ROBERTSON_LTB = 7.0 # aLT, lateral-torsional buckling
ROBERTSON_CONSTANTS: dict[str, float] = {"a": 2.0, "b": 3.5, "c": 5.5, "d": 8.0} # a, strut curves (a) to (d)
# 3.4.3: effective net area coefficient Ke
EFFECTIVE_NET_AREA_COEFFICIENTS: dict[str, float] = {"S275": 1.2, "S355": 1.1, "S460": 1.0}
# 2.4.2 and 4.3.2: notional and restraint forces
NOTIONAL_FORCE_RATIO = 0.005 # 2.4.2.4: 0.5 % of the factored vertical dead and imposed loads
MINIMUM_WIND_RATIO = 0.01 # 2.4.2.3: 1.0 % of the factored dead load
RESTRAINT_FORCE_RATIO = 0.025 # 4.3.2.2.1: 2.5 % of the maximum factored force in the compression flange
RESTRAINT_FORCE_MINIMUM = 0.01 # 4.3.2.2.2, 4.3.3 and 4.7.1.2: 1 %
TIE_MINIMUM = 75.0 # kN; 2.4.5.2 and 2.4.5.3 a)

BendingAxis = Literal["x", "y"] # x-x major, y-y minor
ShearDirection = Literal["web", "flanges"] # load parallel to the web(s), with Mx; or to the flanges, with My
Loading = Literal["normal", "destabilizing"] # 4.3.4
Connection = Literal["bolted", "welded"]
Class4Method = Literal["effective", "reduced_strength"] # 3.6.2 to 3.6.4 and 3.6.6, or the 3.6.5 alternative
InteractionMethod = Literal["simplified", "exact", "stocky"] # 4.8.3.3.1, 4.8.3.3.2 or 4.8.3.3.3, I.1
SectionClassInput = SectionClass | int | str

# Table 2: Partial factors for loads γf
LOAD_FACTORS: dict[str, float] = {
    "dead": 1.4, # dead load, except as follows
    "dead_with_wind_and_imposed": 1.2, # dead load acting together with wind load and imposed load combined
    "dead_with_crane_and_imposed": 1.2, # dead load acting together with crane loads and imposed load combined
    "dead_with_crane_and_wind": 1.2, # dead load acting together with crane loads and wind load combined
    "dead_counteracting": 1.0, # dead load whenever it counteracts the effects of other loads
    "dead_restraining": 1.0, # dead load when restraining sliding, overturning or uplift
    "imposed": 1.6,
    "imposed_with_wind": 1.2,
    "wind": 1.4,
    "wind_with_imposed": 1.2,
    "storage_tanks": 1.4, # storage tanks, including contents
    "storage_tanks_empty_restraining": 1.0, # storage tanks, empty, when restraining sliding, overturning or uplift
    "earth_worst_credible": 1.2, # earth and ground-water load, worst credible values, 2.2.4
    "earth_nominal": 1.4, # earth and ground-water load, nominal values, 2.2.4
    "exceptional_snow": 1.05, # due to local drifting on roofs, 7.4 in BS 6399-3
    "temperature": 1.2, # forces due to temperature change
    "crane_vertical": 1.6, # note a: 1.0 for vertical crane loads that counteract the effects of other loads
    "crane_vertical_with_horizontal": 1.4,
    "crane_horizontal": 1.6, # surge (2.2.3) or crabbing (4.11.2)
    "crane_horizontal_with_vertical": 1.4,
    "crane_vertical_with_imposed": 1.4,
    "crane_horizontal_with_imposed": 1.2,
    "imposed_with_vertical_crane": 1.4,
    "imposed_with_horizontal_crane": 1.2,
    "crane_with_wind": 1.2,
    "wind_with_crane": 1.2,
}

# Table 3: Factor K for type of detail, stress level and strain conditions, as (components in tension due to factored
# ... loads with stress >= 0.3Ynom, with stress < 0.3Ynom, components not subject to applied tension)
BRITTLE_FRACTURE_K: dict[str, tuple[float, float, float]] = {
    "plain": (2.0, 3.0, 4.0), # plain steel; NOTE 2: baseplates attached to columns by nominal welds only
    "drilled": (1.5, 2.0, 3.0), # drilled holes or reamed holes
    "flame_cut": (1.0, 1.5, 2.0), # flame cut edges
    "punched": (1.0, 1.5, 2.0), # punched holes, un-reamed
    "welded": (1.0, 1.5, 2.0), # welded, generally
    "cover_plate_ends": (0.5, 0.75, 1.0), # welded across ends of cover plates; NOTE 3: attachments <= 150 mm long are not
    "unstiffened_flange": (0.5, 0.75, 1.0), # welded connections to unstiffened flanges, 6.7.5
}
# Table 7: Charpy test temperature, or equivalent test temperature, T27J (°C) by steel quality; W (weather resistant),
# ... P and H (hollow section) suffixes share the rows, e.g J2H, J2W, K2W, NLH
CHARPY_TEMPERATURES: dict[str, float] = {"JR": 20.0, "J0": 0.0, "J2": -20.0, "K2": -30.0, "M": -30.0, "N": -30.0, "ML": -50.0, "NL": -50.0, "Q": -20.0, "QL": -40.0, "QL1": -60.0, "G": -15.0}

# Table 13: Effective length LE for beams without intermediate restraint, as (normal, destabilizing) multiples of LLT,
# ... plus 2D where flagged; the first five rows have the compression flange laterally restrained and nominal torsional
# ... restraint (4.2.2), the last two the compression flange laterally unrestrained with both flanges free to rotate on plan
BEAM_EFFECTIVE_LENGTHS: dict[str, tuple[float, float, bool]] = {
    "both_flanges_fully_restrained": (0.7, 0.85, False), # both flanges fully restrained against rotation on plan
    "compression_flange_fully_restrained": (0.75, 0.9, False), # compression flange fully restrained against rotation on plan
    "both_flanges_partially_restrained": (0.8, 0.95, False), # both flanges partially restrained against rotation on plan
    "compression_flange_partially_restrained": (0.85, 1.0, False), # compression flange partially restrained against rotation on plan
    "both_flanges_free": (1.0, 1.2, False), # both flanges free to rotate on plan
    "bottom_flange_connected": (1.0, 1.2, True), # partial torsional restraint by connection of the bottom flange to supports
    "bottom_flange_bearing": (1.2, 1.4, True), # partial torsional restraint only by pressure of the bottom flange onto supports
}
# Table 14: Effective length LE for cantilevers without intermediate restraint, (normal, destabilizing) multiples of L,
# ... by support a) to d) and tip 1) free, 2) lateral restraint to top flange, 3) torsional restraint, 4) lateral and torsional
CANTILEVER_EFFECTIVE_LENGTHS: dict[str, dict[str, tuple[float, float]]] = {
    "continuous_lateral": {"free": (3.0, 7.5), "lateral": (2.7, 7.5), "torsional": (2.4, 4.5), "lateral_torsional": (2.1, 3.6)}, # a)
    "continuous_partial_torsional": {"free": (2.0, 5.0), "lateral": (1.8, 5.0), "torsional": (1.6, 3.0), "lateral_torsional": (1.4, 2.4)}, # b)
    "continuous_lateral_torsional": {"free": (1.0, 2.5), "lateral": (0.9, 2.5), "torsional": (0.8, 1.5), "lateral_torsional": (0.7, 1.2)}, # c)
    "built_in": {"free": (0.8, 1.4), "lateral": (0.7, 1.4), "torsional": (0.6, 0.6), "lateral_torsional": (0.5, 0.5)}, # d) restrained laterally, torsionally and against rotation on plan
}
# Table 15: Limiting value of LE/ry for RHS, (D/B, value x 275/py); beyond it, lateral-torsional buckling is checked (B.2.6)
RHS_LIMITING_SLENDERNESS: tuple[tuple[float, float], ...] = (
    (1.25, 770.0), (1.33, 670.0), (1.4, 580.0), (1.44, 550.0), (1.5, 515.0), (1.67, 435.0),
    (1.75, 410.0), (1.8, 395.0), (2.0, 340.0), (2.5, 275.0), (3.0, 225.0), (4.0, 170.0),
)
# Table 22: Nominal effective length LE for a compression member, as a multiple of L
COMPRESSION_EFFECTIVE_LENGTHS: dict[str, float] = {
    # a) non-sway mode: effectively held in position at both ends
    "fixed_fixed": 0.7, # effectively restrained in direction at both ends
    "partial_partial": 0.85, # partially restrained in direction at both ends
    "fixed_pinned": 0.85, # restrained in direction at one end
    "pinned_pinned": 1.0, # not restrained in direction at either end
    # b) sway mode: one end effectively held in position and restrained in direction, the other not held in position
    "sway_fixed": 1.2, # other end effectively restrained in direction
    "sway_partial": 1.5, # other end partially restrained in direction
    "sway_free": 2.0, # other end not restrained in direction
}
# Table 23: Allocation of strut curve, as ((x-x, y-y) for thickness <= 40 mm, (x-x, y-y) for > 40 mm)
STRUT_CURVES: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "hot_finished_hollow": (("a", "a"), ("a", "a")),
    "cold_formed_hollow": (("c", "c"), ("c", "c")),
    "rolled_I": (("a", "b"), ("b", "c")),
    "rolled_H": (("b", "c"), ("c", "d")),
    "welded_I": (("b", "c"), ("b", "d")), # welded I- or H-section; NOTE 2: y-y b) or c) if the flanges are machine cut
    "welded_box": (("b", "b"), ("c", "c")), # NOTE 3: longitudinal welds near the corners
    "bar": (("b", "b"), ("c", "c")), # round, square or flat bar
    "angle_channel_tee": (("c", "c"), ("c", "c")), # rolled angle, channel or T; laced, battened, back-to-back or compound
}

# Section-table keys, in the order tried, for each BS 5950 symbol; values stay in the table units
_PROPERTY_MAP: dict[str, tuple[str, ...]] = {
    "D": ("D", "h"), # overall depth, mm
    "B": ("B", "b"), # overall breadth, mm
    "t": ("tw", "t"), # web or wall thickness, mm
    "T": ("tf", "T", "t"), # flange thickness, mm
    "d": ("d",), # depth of web between fillets, mm
    "r": ("r", "r_1"), # root radius, mm
    "A": ("A", "Ag", "total_area"), # cm²
    "Ix": ("Ix", "I_yy", "I"), # cm⁴
    "Iy": ("Iy", "I_zz", "I"), # cm⁴
    "Iu": ("Iu", "I_uu"), # cm⁴
    "Iv": ("Iv", "I_vv"), # cm⁴
    "rx": ("rx", "i_yy", "i"), # cm
    "ry": ("ry", "i_zz", "i"), # cm
    "ru": ("ru", "i_uu"), # cm
    "rv": ("rv", "i_vv"), # cm
    "Zx": ("Zx", "W_el_yy", "W_el"), # cm³
    "Zy": ("Zy", "W_el_zz", "W_el"), # cm³
    "Sx": ("Sx", "W_pl_yy", "W_pl"), # cm³
    "Sy": ("Sy", "W_pl_zz", "W_pl"), # cm³
    "u": ("u", "U"), # buckling parameter
    "x": ("x", "X"), # torsional index
    "H": ("H", "I_w"), # warping constant, dm⁶
    "J": ("J", "I_t"), # torsion constant, cm⁴
}


# --- Helpers ---
def _require_positive(value: Optional[float], name: str) -> float:
    if value is None or value <= 0.0:
        raise ValueError(f"{name} must be positive.")
    return float(value)


def _reference(clause: str, equation: Optional[str] = None, title: Optional[str] = None, notes: Optional[str] = None) -> Reference:
    return Reference(code=BS_5950, clause=clause, equation=equation, title=title, notes=notes)


def _ratio_check(utilisation: float, clause: str, title: str, **metadata: Any) -> UtilisationCheck:
    return UtilisationCheck(
        utilisation=utilisation,
        metadata=metadata,
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=_reference(clause, title=title),
    )


def _utilisation_check(demand: float, capacity: float, clause: str, title: str) -> UtilisationCheck:
    """Demand/capacity <= 1.0, on the magnitude of the demand."""
    utilisation: float = compute_utilisation(abs(demand), capacity)
    return _ratio_check(utilisation, clause, title, demand=demand, capacity=capacity)


def _governing(checks: dict[str, float]) -> str:
    return max(checks, key=lambda key: checks[key])


_CLASS_WORDS: dict[str, SectionClass] = {
    "plastic": SectionClass.CLASS_1,
    "compact": SectionClass.CLASS_2,
    "semi-compact": SectionClass.CLASS_3,
    "semicompact": SectionClass.CLASS_3,
    "slender": SectionClass.CLASS_4,
}


def _as_section_class(value: SectionClassInput) -> SectionClass:
    """Accept SectionClass.CLASS_2, 2, "2", "class 2", "CLASS_2" or the BS 5950 names, e.g "compact"."""
    if isinstance(value, SectionClass):
        if value not in _CLASS_RANK:
            raise ValueError(f"BS 5950 uses classes 1 to 4 (3.5.2), not {value.value}.")
        return value
    text: str = str(value).strip().lower()
    if text in _CLASS_WORDS:
        return _CLASS_WORDS[text]
    digits: str = re.sub(r"\D", "", text)
    if digits not in {"1", "2", "3", "4"}:
        raise ValueError(f"Unrecognised section class '{value}'; use 1 to 4, or plastic, compact, semi-compact or slender.")
    return SectionClass[f"CLASS_{digits}"]


def _worst(*classes: Optional[SectionClass]) -> Optional[SectionClass]:
    given: list[SectionClass] = [item for item in classes if item is not None]
    return max(given, key=lambda item: _CLASS_RANK[item]) if given else None


def _is_plastic(section_class: SectionClass) -> bool:
    return section_class in (SectionClass.CLASS_1, SectionClass.CLASS_2)


def _family(section_type: Optional[SectionType]) -> str:
    if section_type in ROLLED_I_SECTION_TYPES:
        return "I"
    if section_type in CHANNEL_SECTION_TYPES:
        return "channel"
    if section_type in SINGLE_ANGLE_SECTION_TYPES:
        return "angle"
    if section_type in DOUBLE_ANGLE_SECTION_TYPES:
        return "double_angle"
    if section_type in HF_RHS_SECTION_TYPES or section_type in CF_RHS_SECTION_TYPES:
        return "RHS"
    if section_type in CHS_SECTION_TYPES:
        return "CHS"
    if section_type == SectionType.HFEHS:
        return "EHS"
    return "other"


def _section_data(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> tuple[Optional[SectionType], dict[str, float], dict[str, Any]]:
    """Resolve a section and/or plain properties into (section_type, BS 5950 symbols in table units, raw data).

    `properties` overrides or supplements the section's own values, e.g "d" and "B" of a welded section.
    """
    raw: dict[str, Any] = {}
    if section is not None:
        raw.update(section.get_properties())
        raw.setdefault("designation", section.designation)
        section_type = section.get_section_type()
    raw.update(properties or {})

    data: dict[str, float] = {}
    for key, aliases in _PROPERTY_MAP.items():
        for alias in aliases:
            value = raw.get(alias)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0:
                data[key] = float(value)
                break

    if section_type in CHS_SECTION_TYPES:
        diameter: Optional[float] = data.pop("d", None) # the UK tables give the outside diameter as d
        if diameter is not None:
            data.setdefault("D", diameter)
    size = raw.get("hxb") or raw.get("hxh") # hollow sections and angles store "h x b" as text
    if isinstance(size, str):
        numbers: list[float] = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", size)]
        if len(numbers) >= 2:
            if section_type in SINGLE_ANGLE_SECTION_TYPES or section_type in DOUBLE_ANGLE_SECTION_TYPES:
                data.setdefault("leg_long", max(numbers[:2]))
                data.setdefault("leg_short", min(numbers[:2]))
            else:
                data.setdefault("D", numbers[0])
                data.setdefault("B", numbers[1])
    return section_type, data, raw


def _get(data: dict[str, float], key: str) -> float:
    value = data.get(key)
    if value is None or value <= 0.0:
        raise ValueError(f"Section property '{key}' is not available; pass it through `properties` (section-table units) or as an argument.")
    return value


def _design_strength(py_mpa: Optional[float], steel_grade: str, data: dict[str, float]) -> float:
    """3.1.1: py as given, else Table 9 for the thickest element (the flange of rolled sections)."""
    if py_mpa is not None:
        return _require_positive(py_mpa, "py_mpa")
    thickness: float = max(data.get("T", 0.0), data.get("t", 0.0))
    if thickness <= 0.0:
        raise ValueError("Pass py_mpa, or a section with its thicknesses, for Table 9.")
    return design_strength(thickness, steel_grade)


def _classify(
    section_type: Optional[SectionType],
    raw: dict[str, Any],
    py: float,
    pattern: StressPattern,
    Fc_kN: Optional[float] = None,
) -> ClassificationResult:
    """3.5: classification of the section by the BS classification engine; Fc_kN gives the stress ratios r1 and r2 (3.5.5)."""
    if section_type is None:
        raise ValueError("Pass `section_class`, or a section (or section_type with properties) to classify.")
    return classify_section_from_dict(section_type, raw, py_mpa=py, stress_pattern=pattern, Fc_kN=Fc_kN if Fc_kN else None)


# --- 2.4.1 Limit state of strength ---
def load_factor(load: str) -> float:
    """BS 5950-1:2000 Table 2: Partial factor γf for a type of load and load combination, e.g "imposed_with_wind" -> 1.2.

    Table 2 note a: use γf = 1.0 for vertical crane loads that counteract the effects of other loads.

    Args:
        load: LOAD_FACTORS key
    """
    if load not in LOAD_FACTORS:
        raise ValueError(f"Unknown load '{load}'; expected one of {', '.join(LOAD_FACTORS)}.")
    return LOAD_FACTORS[load]


class FactoredLoadResult(BaseModel):
    # 2.4.1.2 Buildings without cranes: principal load combinations, with the partial factors γf of Table 2
    combination: int # 1: dead and imposed; 2: dead and wind; 3: dead, imposed and wind
    factored: float # in the units of the loads, e.g kN or kN/m
    factors: dict[str, float] # γf applied to each load
    reference: Optional[Reference] = None


def factored_load(
    combination: Literal[1, 2, 3] = 1,
    dead: float = 0.0,
    imposed: float = 0.0,
    wind: float = 0.0,
    dead_counteracts: bool = False,
) -> FactoredLoadResult:
    """BS 5950-1:2000 2.4.1.2 and Table 2: Factored load of load combination 1, 2 or 3 for buildings without cranes.

    - Load combination 1, dead and imposed (gravity) loads: 1.4Gk + 1.6Qk
    - Load combination 2, dead and wind loads: 1.4Gk + 1.4Wk
    - Load combination 3, dead, imposed and wind loads: 1.2Gk + 1.2Qk + 1.2Wk

    with γf = 1.0 on dead load that counteracts the other loads, e.g restraining uplift or overturning (2.4.1.1).
    Notional horizontal forces (2.4.2.4) go with combination 1; see notional_horizontal_force().

    Args:
        combination: 1, 2 or 3
        dead: Dead load Gk
        imposed: Imposed load Qk; ignored in combination 2
        wind: Wind load Wk; ignored in combination 1
        dead_counteracts: The dead load counteracts the effects of the other loads
    """
    match combination:
        case 1:
            factors: dict[str, float] = {"dead": LOAD_FACTORS["dead"], "imposed": LOAD_FACTORS["imposed"]}
        case 2:
            factors = {"dead": LOAD_FACTORS["dead"], "wind": LOAD_FACTORS["wind"]}
        case 3:
            factors = {"dead": LOAD_FACTORS["dead_with_wind_and_imposed"], "imposed": LOAD_FACTORS["imposed_with_wind"], "wind": LOAD_FACTORS["wind_with_imposed"]}
        case _:
            raise ValueError("combination must be 1, 2 or 3 (2.4.1.2).")
    if dead_counteracts:
        factors["dead"] = LOAD_FACTORS["dead_counteracting"]
    loads: dict[str, float] = {"dead": dead, "imposed": imposed, "wind": wind}
    return FactoredLoadResult(
        combination=combination,
        factored=sum(factor * loads[name] for name, factor in factors.items()),
        factors=factors,
        reference=_reference("2.4.1.2", title="Table 2: Partial factors for loads"),
    )


# --- 2.4.2 Stability limit states ---
def notional_horizontal_force(factored_vertical_load: float) -> float:
    """BS 5950-1:2000 2.4.2.4: Notional horizontal force, 0.5 % of the factored vertical dead and imposed loads at a level.

    It acts with load combination 1 only, in any one direction at a time, and not for overturning, pattern loads, with
    applied horizontal loads or temperature effects, nor in the foundation reactions.
    """
    return NOTIONAL_FORCE_RATIO * abs(factored_vertical_load)


def minimum_horizontal_wind_load(factored_dead_load: float) -> float:
    """BS 5950-1:2000 2.4.2.3: In load combinations 2 and 3 the horizontal factored wind load is at least 1.0 % of the
    factored dead load applied horizontally."""
    return MINIMUM_WIND_RATIO * abs(factored_dead_load)


def elastic_critical_load_factor(h: float, delta: float) -> float:
    """BS 5950-1:2000 2.4.2.6: Sway mode elastic critical load factor of a storey, λcr = h/(200δ).

    Args:
        h: Storey height (mm)
        delta: Notional horizontal deflection of the top of the storey relative to its bottom, under the notional
            horizontal forces of 2.4.2.4 (mm)
    """
    return _require_positive(h, "h") / (200.0 * _require_positive(delta, "delta"))


def amplification_factor(lambda_cr: float, clad: bool = True) -> float:
    """BS 5950-1:2000 2.4.2.7 b): Amplification factor kamp on the sway effects of a sway-sensitive frame, λcr >= 4.0.

    1) clad structures, the stiffening of infill panels or sheeting not taken into account: λcr/(1.15λcr - 1.5) >= 1.0
    2) unclad frames, or with that stiffening explicitly taken into account: λcr/(λcr - 1)

    Args:
        lambda_cr: Elastic critical load factor, see elastic_critical_load_factor()
        clad: Case 1); False for case 2)
    """
    if lambda_cr < 4.0:
        raise ValueError("λcr < 4.0: use second-order elastic analysis (2.4.2.7).")
    if clad:
        return max(lambda_cr / (1.15 * lambda_cr - 1.5), 1.0)
    return lambda_cr / (lambda_cr - 1.0)


class SwayStabilityResult(BaseModel):
    # 2.4.2.6 "Non-sway" and 2.4.2.7 "sway-sensitive" frames; single-storey frames with moment-resisting joints are in 5.5
    lambda_cr: float # smallest over the storeys
    lambda_cr_storeys: list[float]
    governing_storey: int # index into the storeys given
    non_sway: bool # 2.4.2.6: clad, the stiffening not taken into account, and λcr >= 10
    k_amp: Optional[float] = None # 2.4.2.7 b); 1.0 for non-sway frames, None where λcr < 4.0
    second_order_required: bool # 2.4.2.7: λcr < 4.0
    clad: bool
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_sway_stability(
    storey_heights: Sequence[float],
    deflections: Sequence[float],
    clad: bool = True,
    stiffening_taken_into_account: bool = False,
) -> SwayStabilityResult:
    """BS 5950-1:2000 2.4.2.6 and 2.4.2.7: Non-sway or sway-sensitive classification from the notional sway deflections.

    λcr is the smallest h/(200δ) over the storeys. A clad frame whose infill or sheeting stiffening is not explicitly taken
    into account is non-sway where λcr >= 10; every other frame is sway-sensitive, with its sway effects amplified by kamp
    for λcr >= 4.0, or second-order elastic analysis needed below that.

    Args:
        storey_heights: Height of each storey (mm)
        deflections: Notional horizontal deflection of the top of each storey relative to its bottom (mm)
        clad: Clad structure
        stiffening_taken_into_account: The stiffening of masonry infill panels or profiled sheeting diaphragms is
            explicitly taken into account, e.g by partial sway bracing (Annex E)
    """
    if len(storey_heights) != len(deflections) or not storey_heights:
        raise ValueError("Pass one deflection per storey height.")
    factors: list[float] = [elastic_critical_load_factor(h, delta) for h, delta in zip(storey_heights, deflections)]
    lambda_cr: float = min(factors)
    case_1: bool = clad and not stiffening_taken_into_account
    non_sway: bool = case_1 and lambda_cr >= 10.0
    k_amp: Optional[float] = 1.0 if non_sway else (amplification_factor(lambda_cr, case_1) if lambda_cr >= 4.0 else None)
    return SwayStabilityResult(
        lambda_cr=lambda_cr,
        lambda_cr_storeys=factors,
        governing_storey=factors.index(lambda_cr),
        non_sway=non_sway,
        k_amp=k_amp,
        second_order_required=lambda_cr < 4.0,
        clad=clad,
        reference=_reference("2.4.2.6", title="Non-sway and sway-sensitive frames"),
    )


def restraint_reduction_factor(N_r: int) -> float:
    """BS 5950-1:2000 4.3.2.2.3 and 4.7.1.2: kr = (0.2 + 1/Nr)^0.5 on the restraint forces of bracing that restrains Nr
    parallel members; 1.0 for a single member."""
    if N_r < 1:
        raise ValueError("N_r must be at least 1.")
    return min(math.sqrt(0.2 + 1.0 / N_r), 1.0)


def lateral_restraint_forces(F_flange: float, spacings: Sequence[float], torsional: bool = False) -> list[float]:
    """BS 5950-1:2000 4.3.2.2 and 4.3.3: Forces on intermediate lateral or torsional restraints to a compression flange (kN).

    The restraints together resist 2.5 % of the maximum factored force in the compression flange, divided between them in
    proportion to their spacing (4.3.2.2.1); with three or more, each resists at least 1 % (4.3.2.2.2). Each force of the
    couple on a torsional restraint is the larger of the two (4.3.3).

    Args:
        F_flange: Maximum factored force in the compression flange within the span (kN)
        spacings: Spacing attributed to each restraint, e.g half the sum of the adjacent segment lengths (mm)
        torsional: Torsional restraints (4.3.3); the 1 % minimum then applies whatever their number
    """
    if not spacings:
        raise ValueError("Pass the spacing of at least one restraint.")
    total: float = sum(_require_positive(spacing, "spacing") for spacing in spacings)
    shares: list[float] = [RESTRAINT_FORCE_RATIO * abs(F_flange) * spacing / total for spacing in spacings]
    if torsional or len(spacings) >= 3:
        return [max(share, RESTRAINT_FORCE_MINIMUM * abs(F_flange)) for share in shares]
    return shares


# --- 2.4.4 Brittle fracture ---
def charpy_temperature(steel_grade: str) -> float:
    """BS 5950-1:2000 Table 7: T27J (°C) for the quality of a steel name, e.g "S355J2" -> -20, "S355NLH" -> -50."""
    text: str = re.sub(r"\s+", "", steel_grade.upper())
    match = re.fullmatch(r"S\d{3}(JR|J0|J2|K2|QL1|QL|Q|ML|NL|M|N|G)[A-Z0-9]*", text)
    if match is None:
        raise ValueError(f"No Table 7 quality in '{steel_grade}'; pass T27J directly.")
    return CHARPY_TEMPERATURES[match.group(1)]


def limiting_thickness(T_min: float, T27J: float, Y_nom: float) -> float:
    """BS 5950-1:2000 2.4.4: Limiting thickness t1 (mm) at K = 1, the alternative to Tables 4 and 5.

    t1 = 50(1.2)^N (355/Ynom)^1.4 if T27J <= Tmin + 20 °C, else 50(1.2)^N ((35 + Tmin - T27J)/15)(355/Ynom)^1.4,
    with N = (Tmin - T27J)/10.

    Args:
        T_min: Minimum service temperature in the steel (°C); in the UK -5 °C internal and -15 °C external
        T27J: Test temperature for a 27 J Charpy value, or the Table 7 equivalent (°C)
        Y_nom: Nominal yield strength for t <= 16 mm, as in the grade designation (N/mm²)
    """
    N: float = (T_min - T27J) / 10.0
    t1: float = 50.0 * 1.2**N * (355.0 / _require_positive(Y_nom, "Y_nom")) ** 1.4
    if T27J > T_min + 20.0:
        t1 *= (35.0 + T_min - T27J) / 15.0
    return max(t1, 0.0)


class BrittleFractureResult(BaseModel):
    # 2.4.4 Brittle fracture: t <= K t1, and t <= t2 of the product standard (Table 6)
    t: float # element thickness, mm
    K: float # Table 3
    t1: float # limiting thickness at K = 1, mm
    t_max: float # K*t1, or t2 where smaller, mm
    t2: Optional[float] = None # Table 6, mm
    T_min: float # °C
    T27J: float # °C
    Y_nom: float # N/mm²
    utilisation: UtilisationCheck # t/t_max
    reference: Optional[Reference] = None


def check_brittle_fracture(
    t: float,
    steel_grade: Optional[str] = "S355J2",
    T_min: float = -5.0,
    detail: str = "welded",
    stress: Literal["high_tension", "low_tension", "no_tension"] = "high_tension",
    plastic_deformation: bool = False,
    K: Optional[float] = None,
    T27J: Optional[float] = None,
    Y_nom: Optional[float] = None,
    t2: Optional[float] = None,
) -> BrittleFractureResult:
    """BS 5950-1:2000 2.4.4: Brittle fracture, t <= K t1 with t1 from limiting_thickness().

    Args:
        t: Thickness of the element (mm); for rolled sections, relate K to the element and t2 to the thickest element
        steel_grade: Grade and quality, e.g "S275J0", "S355J2H" or "S460NL"; gives T27J (Table 7) and Ynom
        T_min: Minimum service temperature (°C); -5 °C internal or -15 °C external steelwork in the UK
        detail: BRITTLE_FRACTURE_K key (Table 3)
        stress: "high_tension" (stress >= 0.3Ynom), "low_tension" or "no_tension" (not subject to applied tension)
        plastic_deformation: Table 3 NOTE 1, e.g crash barriers or crane stops; K is halved
        K: Overrides Table 3
        T27J: Overrides Table 7 (°C)
        Y_nom: Overrides the strength of the grade name (N/mm²)
        t2: Maximum thickness at which the full Charpy value applies, Table 6 (mm)
    """
    t = _require_positive(t, "t")
    if K is None:
        if detail not in BRITTLE_FRACTURE_K:
            raise ValueError(f"Unknown detail '{detail}'; expected one of {', '.join(BRITTLE_FRACTURE_K)}.")
        K = BRITTLE_FRACTURE_K[detail][("high_tension", "low_tension", "no_tension").index(stress)]
        if plastic_deformation:
            K *= 0.5
    if T27J is None:
        if steel_grade is None:
            raise ValueError("Pass steel_grade or T27J.")
        T27J = charpy_temperature(steel_grade)
    if Y_nom is None:
        match = re.search(r"\d{3}", steel_grade or "")
        if match is None:
            raise ValueError("Pass steel_grade or Y_nom.")
        Y_nom = float(match.group())
    t1: float = limiting_thickness(T_min, T27J, Y_nom)
    t_max: float = K * t1 if t2 is None else min(K * t1, t2)
    return BrittleFractureResult(
        t=t,
        K=K,
        t1=t1,
        t_max=t_max,
        t2=t2,
        T_min=T_min,
        T27J=T27J,
        Y_nom=Y_nom,
        utilisation=_ratio_check(compute_utilisation(t, t_max), "2.4.4", "Brittle fracture", K=K, t1=t1),
        reference=_reference("2.4.4", title="Brittle fracture"),
    )


# --- 2.4.5 Structural integrity ---
def tie_force(g_k: float = 0.0, q_k: float = 0.0, s_t: float = 0.0, L: float = 0.0, edge: bool = False, column_load: float = 0.0) -> float:
    """BS 5950-1:2000 2.4.5.2 and 2.4.5.3: Factored tensile force for a horizontal tie and its end connections (kN).

    - 2.4.5.2: at least 75 kN in all buildings, not additive to other loads
    - 2.4.5.3 a): internal ties 0.5(1.4gk + 1.6qk)st L, edge ties 0.25(1.4gk + 1.6qk)st L, but not less than 75 kN
    - 2.4.5.3 b): ties anchoring edge columns also resist 1 % of the maximum factored dead and imposed load in the column

    Args:
        g_k: Specified dead load per unit area of the floor or roof (kN/m²)
        q_k: Specified imposed load per unit area (kN/m²)
        s_t: Mean transverse spacing of the ties adjacent to that checked (mm)
        L: Span (mm)
        edge: Edge tie
        column_load: Maximum factored vertical dead and imposed load in the adjacent edge column (kN)
    """
    coefficient: float = 0.25 if edge else 0.5
    force: float = coefficient * (1.4 * g_k + 1.6 * q_k) * s_t * L / 1e6 # kN/m² x mm x mm
    return max(force, TIE_MINIMUM, 0.01 * column_load)


# --- 3.4 Section properties ---
def net_area(A: float, t: float, D: float, n_holes: int = 0, staggers: Sequence[tuple[float, float]] = ()) -> float:
    """BS 5950-1:2000 3.4.2 and 3.4.4: Net area An of a cross-section or element with bolt holes (cm²).

    The deduction is the greater of 3.4.4.2, the holes in a cross-section perpendicular to the member axis, n_holes*D*t,
    and 3.4.4.3 b), a chain of len(staggers) + 1 holes on a diagonal or zig-zag line less 0.25s²t/g for each gauge
    space it crosses (Figure 3). For angles with holes in both legs, g is the sum of the back marks less the thickness.

    Args:
        A: Gross area (cm²)
        t: Thickness of the holed material (mm)
        D: Hole diameter (mm)
        n_holes: Holes in the critical cross-section perpendicular to the member axis
        staggers: (s, g) for every gauge space of the chain: staggered pitch s and gauge g (mm); s = 0 where the chain
            crosses a gauge space square to the member axis, e.g line B of Figure 3 is [(s2, g1), (0, g1)]
    """
    A = _require_positive(A, "A")
    t = _require_positive(t, "t")
    D = _require_positive(D, "D")
    if n_holes < 0:
        raise ValueError("n_holes cannot be negative.")
    deduction: float = n_holes * D * t # mm²; 3.4.4.2
    if staggers:
        holes: int = len(staggers) + 1
        chain: float = t * (holes * D - sum(0.25 * s**2 / _require_positive(g, "g") for s, g in staggers)) # 3.4.4.3 b)
        deduction = max(deduction, chain)
    A_net: float = A - deduction / 100.0
    if A_net <= 0.0:
        raise ValueError("Net area must be positive; check the hole diameter, thickness and count.")
    return A_net


def effective_net_area_coefficient(steel_grade: Optional[str] = "S275", py: Optional[float] = None, Us: Optional[float] = None) -> float:
    """BS 5950-1:2000 3.4.3: Effective net area coefficient Ke = 1.2 (S275), 1.1 (S355), 1.0 (S460), else (Us/1.2)/py.

    Args:
        steel_grade: e.g "S275" or "S355J2"
        py: Design strength (N/mm²); other grades
        Us: Specified minimum tensile strength (N/mm²); other grades
    """
    grade: str = re.sub(r"\s+", "", (steel_grade or "").upper())[:4]
    if grade in EFFECTIVE_NET_AREA_COEFFICIENTS:
        return EFFECTIVE_NET_AREA_COEFFICIENTS[grade]
    if py is not None and Us is not None:
        return (_require_positive(Us, "Us") / 1.2) / _require_positive(py, "py")
    raise ValueError(f"Ke is tabulated for {', '.join(EFFECTIVE_NET_AREA_COEFFICIENTS)}; pass py and Us for other grades.")


def effective_net_area(a_n: float, a_g: float, K_e: float) -> float:
    """BS 5950-1:2000 3.4.3: Effective net area of an element, ae = Ke*an but ae <= ag (cm²)."""
    return min(K_e * _require_positive(a_n, "a_n"), _require_positive(a_g, "a_g"))


# --- 3.6 Slender cross-sections ---
def slender_web_effective_width(f_cw: float, f_tw: float, p_yw: float, t: float) -> float:
    """BS 5950-1:2000 3.6.2.4: Effective width of the compression zone of a class 4 slender web in bending (mm).

    beff = 120εt/[(1 + (fcw - ftw)/pyw)(1 + ftw/fcw)], arranged as 0.4beff next to the compression flange and 0.6beff
    next to the elastic neutral axis of the effective section (Figure 9), with fcw and ftw from the section with the
    web fully effective.

    Args:
        f_cw: Maximum compressive stress in the web (N/mm²)
        f_tw: Maximum tensile stress in the web (N/mm²)
        p_yw: Design strength of the web (N/mm²)
        t: Web thickness (mm)
    """
    f_cw = _require_positive(f_cw, "f_cw")
    return 120.0 * epsilon(p_yw) * _require_positive(t, "t") / ((1.0 + (f_cw - f_tw) / p_yw) * (1.0 + f_tw / f_cw))


def reduced_design_strength(py: float, beta_3: float, beta: float) -> float:
    """BS 5950-1:2000 3.6.5: Reduced design strength pyr = (β3/β)²py at which the section is class 3 semi-compact.

    Args:
        py: Design strength (N/mm²)
        beta_3: Class 3 limit of the element, epsilon included (Table 11 or 12)
        beta: Its b/T, b/t, D/t or d/t, exceeding beta_3
    """
    return min((_require_positive(beta_3, "beta_3") / _require_positive(beta, "beta")) ** 2, 1.0) * py


def chs_effective_ratios(D_t: float, py: float) -> tuple[float, float]:
    """BS 5950-1:2000 3.6.6: (Aeff/A, Zeff/Z) of a class 4 slender CHS with D <= 240tε².

    Aeff/A = [(80/(D/t))(275/py)]^0.5 and Zeff/Z = [(140/(D/t))(275/py)]^0.25, each capped at 1.
    """
    eps2: float = 275.0 / _require_positive(py, "py")
    if _require_positive(D_t, "D_t") > 240.0 * eps2:
        raise ValueError(f"3.6.6 applies to D/t <= 240ε² = {240.0 * eps2:.1f}; D/t = {D_t:.1f}.")
    return min(math.sqrt(80.0 / D_t * eps2), 1.0), min((140.0 / D_t * eps2) ** 0.25, 1.0)


def angle_effective_ratios(b_t: float, py: float) -> tuple[float, float]:
    """BS 5950-1:2000 3.6.4: (Aeff/A, Zeff/Z) of a class 4 slender hot rolled equal-leg angle, 12ε/(b/t) and 15ε/(b/t),
    each capped at 1, with b the leg length."""
    eps: float = epsilon(py)
    return min(12.0 * eps / _require_positive(b_t, "b_t"), 1.0), min(15.0 * eps / b_t, 1.0)


class EffectiveSection(BaseModel):
    # 3.6 Slender cross-sections: effective properties of a class 4 slender cross-section under one stress pattern
    stress_pattern: StressPattern
    method: str # "3.6.2.2", "3.6.2.3", "3.6.4", "3.6.6", "3.6.5" or "not slender"
    py: float # N/mm²; design strength
    A: Optional[float] = None # gross area, cm²
    A_eff: Optional[float] = None # cm²; under axial compression
    Z: Optional[float] = None # section modulus about the axis of bending, cm³
    Z_eff: Optional[float] = None # cm³; the smaller value for the axis (3.6.2.3)
    py_r: Optional[float] = None # N/mm²; 3.6.5 reduced design strength, the section then being class 3 semi-compact
    slender_elements: list[str] = Field(default_factory=list)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _modulus_without_strips(I: float, A: float, strips: Sequence[tuple[float, float, float]], c: float) -> float:
    """Elastic modulus (cm³) after removing strips (area cm², distance y cm towards the compression side, own I cm⁴) from a
    section of I (cm⁴) and A (cm²) with extreme fibres at c (cm); the smaller of the two moduli (3.6.2.3)."""
    removed: float = sum(area for area, _, _ in strips)
    A_eff: float = A - removed
    if A_eff <= 0.0:
        raise ValueError("The removed strips exceed the section area.")
    e: float = sum(area * y for area, y, _ in strips) / A_eff # centroid shift away from the compression side
    I_eff: float = I - sum(area * y**2 + own for area, y, own in strips) - A_eff * e**2
    return min(I_eff / (c + e), I_eff / (c - e))


def _reduced_strength(py: float, slender: Sequence[ElementClassification]) -> float:
    """3.6.5 over every slender element and, for single angles in compression, every criterion that fails."""
    factor: float = 1.0
    for element in slender:
        if "governing_check" in element.metadata:
            for label in ("b/t", "d/t", "(b+d)/t"):
                value, limit = element.metadata[label], element.metadata[f"{label}_limit"]
                if value > limit:
                    factor = min(factor, (limit / value) ** 2)
        elif element.class_3_limit is not None and element.ratio > element.class_3_limit:
            factor = min(factor, (element.class_3_limit / element.ratio) ** 2)
    return py * factor


def _effective_area(family: str, section_type: Optional[SectionType], data: dict[str, float], slender: Sequence[ElementClassification], py: float) -> tuple[float, str]:
    """3.6.2.2 (I, H and RHS), 3.6.4 (equal angles) or 3.6.6 (CHS): Aeff under axial compression (cm²)."""
    A: float = _get(data, "A")
    eps: float = epsilon(py)
    match family:
        case "I":
            deduction: float = 0.0 # mm²
            for element in slender:
                if element.name == "flange": # four outstands at the class 3 width (Figure 8a)
                    deduction += 4.0 * max(element.b_mm - (element.class_3_limit or 0.0) * element.t_mm, 0.0) * element.t_mm
                elif element.name == "web": # 20εt next to each flange, with a central non-effective zone
                    deduction += max(element.b_mm - 40.0 * eps * element.t_mm, 0.0) * element.t_mm
            return A - deduction / 100.0, "3.6.2.2"
        case "RHS":
            width: float = 40.0 if section_type in HF_RHS_SECTION_TYPES else 35.0 # 40εt hot finished, 35εt cold formed
            deduction = sum(2.0 * max(element.b_mm - width * eps * element.t_mm, 0.0) * element.t_mm for element in slender)
            return A - deduction / 100.0, "3.6.2.2"
        case "CHS":
            area_ratio, _ = chs_effective_ratios(_get(data, "D") / _get(data, "t"), py)
            return A * area_ratio, "3.6.6"
        case "angle" if data.get("leg_long") == data.get("leg_short"):
            area_ratio, _ = angle_effective_ratios(_get(data, "leg_long") / _get(data, "t"), py)
            return A * area_ratio, "3.6.4"
    raise NotImplementedError(f"Effective areas are not implemented for {family} sections.")


def _effective_modulus(
    family: str,
    section_type: Optional[SectionType],
    data: dict[str, float],
    slender: Sequence[ElementClassification],
    py: float,
    axis: BendingAxis,
) -> tuple[float, str]:
    """3.6.2.3 (I, H and RHS with fully effective webs), 3.6.4 (equal angles) or 3.6.6 (CHS): Zeff about `axis` (cm³)."""
    Z: float = _get(data, f"Z{axis}")
    eps: float = epsilon(py)
    match family:
        case "CHS":
            _, modulus_ratio = chs_effective_ratios(_get(data, "D") / _get(data, "t"), py)
            return Z * modulus_ratio, "3.6.6"
        case "angle" if data.get("leg_long") == data.get("leg_short"):
            _, modulus_ratio = angle_effective_ratios(_get(data, "leg_long") / _get(data, "t"), py)
            return Z * modulus_ratio, "3.6.4"
        case "I":
            if any(element.name == "web" for element in slender):
                raise NotImplementedError("3.6.2.4 (class 4 slender web in bending) is not implemented.")
            flange: ElementClassification = next(element for element in slender if element.name == "flange")
            w: float = flange.b_mm - (flange.class_3_limit or 0.0) * flange.t_mm # removed from each outstand tip, mm
            T: float = flange.t_mm
            if axis == "x": # the two outstands of the compression flange
                D: float = _get(data, "D")
                strips: list[tuple[float, float, float]] = [(2.0 * w * T / 100.0, (D - T) / 20.0, 2.0 * w * T**3 / 12.0 / 1e4)]
                c: float = D / 20.0
            else: # the compression tips of both flanges
                B: float = _get(data, "B")
                strips = [(2.0 * w * T / 100.0, (B - w) / 20.0, 2.0 * T * w**3 / 12.0 / 1e4)]
                c = B / 20.0
            return _modulus_without_strips(_get(data, f"I{axis}"), _get(data, "A"), strips, c), "3.6.2.3"
        case "RHS":
            if any(element.name == "web_wall" for element in slender):
                raise NotImplementedError("3.6.2.4 (class 4 slender web in bending) is not implemented.")
            flange = next(element for element in slender if element.name == "flange_wall")
            width: float = 40.0 if section_type in HF_RHS_SECTION_TYPES else 35.0
            w = flange.b_mm - width * eps * flange.t_mm
            t: float = flange.t_mm
            depth: float = _get(data, "D") if axis == "x" else _get(data, "B")
            strips = [(w * t / 100.0, (depth - t) / 20.0, w * t**3 / 12.0 / 1e4)]
            return _modulus_without_strips(_get(data, f"I{axis}"), _get(data, "A"), strips, depth / 20.0), "3.6.2.3"
    raise NotImplementedError(f"Effective moduli are not implemented for {family} sections.")


def _effective_section(
    section_type: Optional[SectionType],
    data: dict[str, float],
    classification: ClassificationResult,
    pattern: StressPattern,
    method: Class4Method = "effective",
) -> EffectiveSection:
    py: float = classification.py_mpa
    compression: bool = pattern == StressPattern.COMPRESSION
    axis: BendingAxis = "y" if pattern == StressPattern.MINOR_AXIS_BENDING else "x"
    slender: list[ElementClassification] = [element for element in classification.elements if element.section_class == SectionClass.CLASS_4]
    base: dict[str, Any] = {
        "stress_pattern": pattern,
        "py": py,
        "A": data.get("A"),
        "Z": None if compression else data.get(f"Z{axis}"),
        "slender_elements": [element.name for element in slender],
        "reference": _reference("3.6", title="Slender cross-sections"),
    }
    if not slender:
        return EffectiveSection(method="not slender", A_eff=data.get("A") if compression else None, Z_eff=None if compression else data.get(f"Z{axis}"), **base)
    notes: list[str] = []
    if method == "effective":
        family: str = _family(section_type)
        try:
            if compression:
                A_eff, clause = _effective_area(family, section_type, data, slender, py)
                return EffectiveSection(method=clause, A_eff=A_eff, **base)
            Z_eff, clause = _effective_modulus(family, section_type, data, slender, py, axis)
            return EffectiveSection(method=clause, Z_eff=Z_eff, **base)
        except NotImplementedError as error:
            notes.append(f"{error} The 3.6.5 reduced design strength is used.")
    return EffectiveSection(method="3.6.5", py_r=_reduced_strength(py, slender), metadata={"notes": notes} if notes else {}, **base)


def effective_section(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
    Fc_kN: Optional[float] = None,
    method: Class4Method = "effective",
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> EffectiveSection:
    """BS 5950-1:2000 3.6: Effective properties of a class 4 slender cross-section.

    - 3.6.2.2 doubly symmetric I, H, RHS and SHS in compression: slender webs and internal flanges effective over 40εt
      (35εt cold formed RHS) in two equal portions; slender outstands at the class 3 width of Table 11 (Figure 8a)
    - 3.6.2.3 the same sections in bending, with webs that are not slender: Zeff of the section without the non-effective
      zone of the compression flange (Figure 8b), the smaller modulus about the axis
    - 3.6.4 hot rolled equal angles: Aeff/A = 12ε/(b/t), Zeff/Z = 15ε/(b/t)
    - 3.6.6 CHS with D <= 240tε²: Aeff/A = [(80/(D/t))(275/py)]^0.5, Zeff/Z = [(140/(D/t))(275/py)]^0.25
    - 3.6.5 otherwise, or with method="reduced_strength": pyr = (β3/β)²py, the section then being class 3 semi-compact

    Singly symmetric sections, such as channels, need the moments of the centroid shift (3.6.3), so they take 3.6.5; as do
    slender webs in bending (3.6.2.4, see slender_web_effective_width()).

    Args:
        section: UK section object
        py_mpa: Design strength py (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        stress_pattern: "compression", "bending-major-axis" or "bending-minor-axis"
        Fc_kN: Axial compression (kN), for the stress ratio r2 of webs in compression (3.5.5); defaults to r2 = 1
        method: "effective" or "reduced_strength" (3.6.5)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    pattern: StressPattern = _normalize_stress_pattern(stress_pattern)
    if pattern == StressPattern.COMBINED:
        raise ValueError("Effective properties are for axial compression (Aeff) or bending about one axis (Zeff).")
    section_type, data, raw = _section_data(section, section_type, properties)
    py: float = _design_strength(py_mpa, steel_grade, data)
    classification: ClassificationResult = _classify(section_type, raw, py, pattern, Fc_kN)
    return _effective_section(section_type, data, classification, pattern, method)


# --- 4.2 Members subject to bending ---
def shear_area(
    section: Optional[BaseSection] = None,
    direction: ShearDirection = "web",
    welded: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> float:
    """BS 5950-1:2000 4.2.3: Shear area Av (cm²).

    a) rolled I, H and channel sections, load parallel to web: tD
    b) welded I-sections, load parallel to web: td
    c) RHS, load parallel to webs: AD/(D + B); parallel to the flanges, AB/(D + B) as the webs are then the B walls
    g) CHS: 0.6A
    i) any other case: 0.9A0, A0 the rectilinear element with the largest dimension parallel to the shear; taken here as
       both flanges of I, H and channel sections (0.9 x 2BT) and the longer leg of angles

    Args:
        section: UK section
        direction: "web", load parallel to the web(s), with Mx; "flanges", parallel to the flanges, with My
        welded: Welded I-section (b)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    return _shear_area(_family(section_type), data, direction, welded)


def _shear_area(family: str, data: dict[str, float], direction: ShearDirection, welded: bool) -> float:
    match family, direction:
        case ("I" | "channel" | "other"), "web":
            depth: float = _get(data, "d") if welded else _get(data, "D")
            return _get(data, "t") * depth / 100.0 # a) tD, b) td
        case ("I" | "channel" | "other"), "flanges":
            return 0.9 * 2.0 * _get(data, "B") * _get(data, "T") / 100.0 # i) 0.9A0
        case "RHS", _:
            D, B = _get(data, "D"), _get(data, "B")
            return _get(data, "A") * (D if direction == "web" else B) / (D + B) # c)
        case "CHS", _:
            return 0.6 * _get(data, "A") # g)
        case ("angle" | "double_angle"), _:
            legs: float = 2.0 if family == "double_angle" else 1.0
            return 0.9 * legs * _get(data, "leg_long") * _get(data, "t") / 100.0 # i) 0.9A0
    raise NotImplementedError(f"4.2.3 shear area is not implemented for {family} sections; pass Av_cm2.")


def _shear_area_modulus(family: str, data: dict[str, float], direction: ShearDirection, A_v: float, welded: bool) -> float:
    """4.2.5.3: plastic modulus Sv of the shear area Av (cm³), located next to the neutral axis in CHS and RHS (4.2.3)."""
    match family, direction:
        case ("I" | "channel" | "other"), "web":
            depth: float = _get(data, "d") if welded else _get(data, "D")
            return _get(data, "t") * depth**2 / 4.0 / 1e3
        case ("I" | "channel" | "other"), "flanges":
            return 0.9 * 2.0 * _get(data, "T") * _get(data, "B") ** 2 / 4.0 / 1e3
        case "RHS", _:
            return A_v * (_get(data, "D") if direction == "web" else _get(data, "B")) / 10.0 / 4.0
        case "CHS", _: # the arcs within 0.3π of the neutral axis
            R: float = (_get(data, "D") - _get(data, "t")) / 2.0
            return 4.0 * R**2 * _get(data, "t") * (1.0 - math.cos(0.3 * math.pi)) / 1e3
    return A_v * _get(data, "leg_long") / 10.0 / 4.0


def shear_capacity(A_v: float, py: float) -> float:
    """BS 5950-1:2000 4.2.3: Shear capacity Pv = 0.6pyAv (kN), from Av (cm²) and py (N/mm²)."""
    return 0.6 * _require_positive(py, "py") * _require_positive(A_v, "A_v") / 10.0


def shear_buckling_required(d_t: float, py: float, welded: bool = False) -> bool:
    """BS 5950-1:2000 4.2.3 and 4.4.5.1: webs need a shear buckling check where d/t > 70ε (rolled) or 62ε (welded)."""
    return d_t > (62.0 if welded else 70.0) * epsilon(py)


def _web_slenderness(d_t: float, py: float, a_d: float) -> float:
    """H.1: λw = (pv/qe)^0.5, with qe = [0.75 + 1/(a/d)²](1000/(d/t))² for a/d <= 1, else [1 + 0.75/(a/d)²](1000/(d/t))²."""
    base: float = (1000.0 / _require_positive(d_t, "d_t")) ** 2
    q_e: float = (0.75 + 1.0 / a_d**2) * base if a_d <= 1.0 else (1.0 + 0.75 / a_d**2) * base
    return math.sqrt(0.6 * py / q_e)


def shear_buckling_strength(d_t: float, py: float, a_d: float = math.inf, welded: bool = False) -> float:
    """BS 5950-1:2000 H.1: Shear buckling strength qw of the web of an I-section (N/mm²), the basis of Table 21.

    welded: qw = pv (λw <= 0.8); [(13.48 - 5.6λw)/9]pv (0.8 < λw < 1.25); 0.9pv/λw (λw >= 1.25)
    rolled: qw = pv (λw <= 0.9); 0.9pv/λw (λw > 0.9)

    Args:
        d_t: Web depth to thickness ratio d/t
        py: Design strength of the web pyw (N/mm²)
        a_d: Stiffener spacing ratio a/d; infinity for webs without intermediate stiffeners
        welded: Welded I-section
    """
    p_v: float = 0.6 * _require_positive(py, "py")
    lambda_w: float = _web_slenderness(d_t, py, a_d)
    if welded:
        if lambda_w <= 0.8:
            return p_v
        return (13.48 - 5.6 * lambda_w) / 9.0 * p_v if lambda_w < 1.25 else 0.9 * p_v / lambda_w
    return p_v if lambda_w <= 0.9 else 0.9 * p_v / lambda_w


def critical_shear_strength(d_t: float, py: float, a_d: float = math.inf, welded: bool = False) -> float:
    """BS 5950-1:2000 H.2: Critical shear strength qcr of the web of an I-section (N/mm²), for Vcr = d*t*qcr.

    welded: qcr = pv (λw <= 0.8); (1.64 - 0.8λw)pv (0.8 < λw < 1.25); pv/λw² (λw >= 1.25)
    rolled: qcr = pv (λw <= 0.9); [(8.1/λw - 2)/7]pv (0.9 < λw < 1.25); pv/λw² (λw >= 1.25)
    """
    p_v: float = 0.6 * _require_positive(py, "py")
    lambda_w: float = _web_slenderness(d_t, py, a_d)
    if lambda_w >= 1.25:
        return p_v / lambda_w**2
    if welded:
        return p_v if lambda_w <= 0.8 else (1.64 - 0.8 * lambda_w) * p_v
    return p_v if lambda_w <= 0.9 else (8.1 / lambda_w - 2.0) / 7.0 * p_v


def critical_shear_buckling_resistance(V_w: float, P_v: float) -> float:
    """BS 5950-1:2000 4.4.5.4: Vcr from the simple shear buckling resistance Vw (kN).

    Vcr = Pv if Vw = Pv; (9Vw - 2Pv)/7 if Pv > Vw > 0.72Pv; (Vw/0.9)²/Pv if Vw <= 0.72Pv
    """
    if V_w >= P_v:
        return P_v
    if V_w > 0.72 * P_v:
        return (9.0 * V_w - 2.0 * P_v) / 7.0
    return (V_w / 0.9) ** 2 / P_v


def shear_reduction_factor(F_v: float, P_v: float) -> float:
    """BS 5950-1:2000 4.2.5.3 and H.3.2: ρ = [2(Fv/Pv) - 1]² where Fv > 0.6Pv, else 0 (low shear, 4.2.5.2)."""
    ratio: float = abs(F_v) / _require_positive(P_v, "P_v")
    return 0.0 if ratio <= 0.6 else min((2.0 * ratio - 1.0) ** 2, 1.0)


class ShearResult(BaseModel):
    # 4.2.3 Shear capacity, with the shear buckling resistance of 4.4.5.2 for webs with d/t > 70ε (62ε welded)
    Pv: float # kN; 0.6pyAv
    Av: float # cm²
    direction: ShearDirection
    py: float # N/mm²
    d_t: Optional[float] = None # web slenderness, where a web carries the shear
    shear_buckling: bool = False # 4.2.3: d/t > 70ε rolled or 62ε welded
    qw: Optional[float] = None # N/mm², H.1
    Vw: Optional[float] = None # kN; 4.4.5.2, d*t*qw for each web
    Vcr: Optional[float] = None # kN; 4.4.5.4, no end anchorage needed where Fv <= Vcr
    capacity: float # kN; Pv, or Vw where the web buckles in shear
    Fv: Optional[float] = None # kN
    high_shear: Optional[bool] = None # 4.2.5.3: Fv > 0.6Pv
    rho: Optional[float] = None # 4.2.5.3
    utilisation: Optional[UtilisationCheck] = None
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_shear(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fv_kN: Optional[float] = None,
    direction: ShearDirection = "web",
    welded: bool = False,
    a_mm: Optional[float] = None,
    Av_cm2: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ShearResult:
    """BS 5950-1:2000 4.2.3: Shear capacity Pv, and the shear buckling resistance Vw = d*t*qw (4.4.5.2) where needed.

    Webs of I, H and channel sections loaded parallel to the web, and the webs of RHS, are checked for shear buckling
    where d/t > 70ε (rolled) or 62ε (welded); qw is from H.1, whose I-section rules are also applied to the flat webs of
    RHS. Webs carrying moment or axial force as well as shear need 4.4.4 and H.3 (not implemented).

    Args:
        section: UK section
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fv_kN: Shear force (kN)
        direction: "web" or "flanges", see shear_area()
        welded: Welded section
        a_mm: Spacing of intermediate transverse stiffeners (mm); none by default
        Av_cm2: Shear area (cm²); overrides shear_area()
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    A_v: float = _require_positive(Av_cm2, "Av_cm2") if Av_cm2 is not None else _shear_area(family, data, direction, welded)
    P_v: float = shear_capacity(A_v, py)

    webs: int = 0
    d: Optional[float] = None
    if family in ("I", "channel", "other") and direction == "web" and "d" in data and "t" in data:
        webs, d = 1, data["d"]
    elif family == "RHS" and "t" in data:
        k: float = 3.0 if section_type in HF_RHS_SECTION_TYPES else 5.0 # Table 12 note a
        webs, d = 2, (_get(data, "D") if direction == "web" else _get(data, "B")) - k * data["t"]
    d_t: Optional[float] = d / data["t"] if d is not None else None
    buckling: bool = d_t is not None and shear_buckling_required(d_t, py, welded)
    q_w, V_w, V_cr = None, None, None
    if buckling and d is not None and d_t is not None:
        a_d: float = a_mm / d if a_mm is not None else math.inf
        q_w = shear_buckling_strength(d_t, py, a_d, welded)
        V_w = min(webs * d * data["t"] * q_w / 1e3, P_v) # 4.4.5.2
        V_cr = critical_shear_buckling_resistance(V_w, P_v)
    capacity: float = V_w if V_w is not None else P_v

    return ShearResult(
        Pv=P_v,
        Av=A_v,
        direction=direction,
        py=py,
        d_t=d_t,
        shear_buckling=buckling,
        qw=q_w,
        Vw=V_w,
        Vcr=V_cr,
        capacity=capacity,
        Fv=Fv_kN,
        high_shear=abs(Fv_kN) > 0.6 * P_v if Fv_kN is not None else None,
        rho=shear_reduction_factor(Fv_kN, P_v) if Fv_kN is not None else None,
        utilisation=_utilisation_check(Fv_kN, capacity, "4.4.5.2" if buckling else "4.2.3", "Shear") if Fv_kN is not None else None,
        reference=_reference("4.2.3", title="Shear capacity"),
    )


def elastic_shear_stress_limit(py: float) -> float:
    """BS 5950-1:2000 4.2.4: peak elastic shear stress in webs that vary in thickness, 0.7py (N/mm²)."""
    return 0.7 * _require_positive(py, "py")


def notched_end_moment_capacity(
    py: float,
    notch: Literal["single", "double"] = "single",
    Z: Optional[float] = None,
    t: Optional[float] = None,
    d: Optional[float] = None,
    F_v: float = 0.0,
    P_v: Optional[float] = None,
) -> float:
    """BS 5950-1:2000 4.2.5.4: Moment capacity Mc of a notched end of an I, H or channel section (kNm).

    Low shear (Fv <= 0.75Pv): pyZ singly notched; py*t*d²/6 doubly notched.
    High shear: 1.5pyZ[1 - (Fv/Pv)²] singly; (py*t*d²/4)[1 - (Fv/Pv)²] doubly.

    Args:
        py: Design strength (N/mm²)
        notch: "single" or "double"
        Z: Section modulus of the residual tee at a singly notched end (cm³)
        t: Web thickness (mm), doubly notched
        d: Residual depth of a doubly notched end (mm)
        F_v: Shear force (kN)
        P_v: Shear capacity of the notched end (kN), for high shear
    """
    high: bool = P_v is not None and abs(F_v) > 0.75 * P_v
    reduction: float = 1.0 - (abs(F_v) / P_v) ** 2 if high and P_v else 1.0
    if notch == "single":
        modulus: float = _require_positive(Z, "Z") * 1e3 # mm³
        return (1.5 * reduction if high else 1.0) * py * modulus / 1e6
    plate: float = _require_positive(t, "t") * _require_positive(d, "d") ** 2
    return (py * plate / 4.0 * reduction if high else py * plate / 6.0) / 1e6


def tension_flange_holes_negligible(a_t: float, a_t_net: float, K_e: float) -> bool:
    """BS 5950-1:2000 4.2.5.5: bolt holes in a tension flange (or the whole tension zone) need no allowance in Mc where
    at,net >= at/Ke; otherwise an effective net area of Ke*at,net may be used."""
    return _require_positive(a_t_net, "a_t_net") >= _require_positive(a_t, "a_t") / _require_positive(K_e, "K_e")


class MomentCapacityResult(BaseModel):
    # 4.2.5 Moment capacity about one axis, with co-existing shear (4.2.5.2, 4.2.5.3) and the limit of 4.2.5.1
    Mc: float # kNm
    axis: BendingAxis
    section_class: SectionClass # 3.5, in bending about `axis` (with Fc where given, 4.8.1)
    py: float # N/mm²; pyr for the 3.6.5 method
    modulus: str # "S", "Seff", "Z" or "Zeff"
    W: float # cm³; the modulus used
    S: Optional[float] = None # plastic modulus, cm³
    Z: float # section modulus, cm³
    Mc_limit: float # kNm; 4.2.5.1: 1.2pyZ for simple spans and cantilevers, 1.5pyZ generally
    high_shear: bool = False # 4.2.5.3: Fv > 0.6Pv
    rho: float = 0.0 # 4.2.5.3
    Sv: Optional[float] = None # cm³
    Fv: Optional[float] = None # kN
    Pv: Optional[float] = None # kN
    M: Optional[float] = None # design moment, kNm
    utilisation: Optional[UtilisationCheck] = None
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_bending(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    axis: BendingAxis = "x",
    M_kNm: Optional[float] = None,
    Fv_kN: float = 0.0,
    Fc_kN: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    use_Seff: bool = True,
    simple_span: bool = True,
    welded: bool = False,
    class_4_method: Class4Method = "effective",
    Z_eff_cm3: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> MomentCapacityResult:
    """BS 5950-1:2000 4.2.5: Moment capacity Mc about one axis.

    Low shear, Fv <= 0.6Pv (4.2.5.2): pyS (class 1, 2); pyZ or pySeff (class 3, 3.5.6); pyZeff (class 4, 3.6).
    High shear, Fv > 0.6Pv (4.2.5.3): py(S - ρSv); py(Z - ρSv/1.5) or py(Seff - ρSv); py(Zeff - ρSv/1.5).
    4.2.5.1: Mc <= 1.2pyZ for simply supported beams and cantilevers, or 1.5pyZ generally.

    Angles have no tabulated S, so class 1 and 2 angles take Z, which is conservative. Where d/t > 70ε (62ε welded) the
    web needs the shear buckling rules of 4.4.4, which are not implemented; the result then carries a note.

    Args:
        section: UK section; classified in bending about `axis` unless `section_class` is given
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        axis: "x" (major) or "y" (minor)
        M_kNm: Design moment (kNm)
        Fv_kN: Co-existing shear (kN), parallel to the web for "x" and to the flanges for "y"
        Fc_kN: Co-existing axial compression (kN), for the classification of webs (3.5.5, 4.8.1); Seff is then not used
        section_class: Class to use instead of classifying, e.g 2 or "semi-compact"
        use_Seff: Class 3: use Seff (3.5.6) rather than Z
        simple_span: 4.2.5.1: a simply supported beam or cantilever (1.2pyZ); False for 1.5pyZ
        welded: Welded section, for the shear area
        class_4_method: "effective" (3.6.2 to 3.6.6) or "reduced_strength" (3.6.5)
        Z_eff_cm3: Effective section modulus for class 4 (cm³); overrides 3.6
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("x", "y"):
        raise ValueError("axis must be 'x' (major) or 'y' (minor).")
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    pattern: StressPattern = StressPattern.MAJOR_AXIS_BENDING if axis == "x" else StressPattern.MINOR_AXIS_BENDING
    axial: Optional[float] = Fc_kN if (Fc_kN and family != "CHS") else None # 3.5.1: CHS are classified for bending alone
    classification: Optional[ClassificationResult] = None
    if section_class is not None:
        cls: SectionClass = _as_section_class(section_class)
    else:
        classification = _classify(section_type, raw, py, pattern, axial)
        cls = classification.section_class
    S: Optional[float] = data.get(f"S{axis}")
    Z: float = _get(data, f"Z{axis}")
    notes: list[str] = []
    py_used: float = py

    if _is_plastic(cls):
        if S is None:
            W, modulus = Z, "Z"
            notes.append("No plastic modulus is tabulated; Z is used for a class 1 or 2 section, which is conservative.")
        else:
            W, modulus = S, "S"
    elif cls == SectionClass.CLASS_3:
        W, modulus = Z, "Z"
        if use_Seff and S is not None and axial is None and section_type is not None:
            try:
                W = effective_plastic_modulus(section_type=section_type, properties=raw, py_mpa=py, axis="major" if axis == "x" else "minor").S_eff
            except ValueError: # e.g a section_class of 3 given for a section that classifies as 4
                W = Z
            modulus = "Seff" if W > Z else "Z"
    elif Z_eff_cm3 is not None:
        W, modulus = _require_positive(Z_eff_cm3, "Z_eff_cm3"), "Zeff"
    else:
        classification = classification or _classify(section_type, raw, py, pattern, axial)
        effective: EffectiveSection = _effective_section(section_type, data, classification, pattern, class_4_method)
        if effective.py_r is not None:
            W, modulus, py_used = Z, "Z", effective.py_r
            notes.append(f"3.6.5: reduced design strength pyr = {effective.py_r:.1f} N/mm².")
        else:
            W, modulus = _require_positive(effective.Z_eff, "Z_eff"), "Zeff"
        notes.extend(effective.metadata.get("notes", []))

    # 4.2.5.3 High shear
    direction: ShearDirection = "web" if axis == "x" else "flanges"
    P_v: Optional[float] = None
    rho: float = 0.0
    S_v: Optional[float] = None
    W_reduced: float = W
    if Fv_kN:
        A_v: float = _shear_area(family, data, direction, welded)
        P_v = shear_capacity(A_v, py)
        rho = shear_reduction_factor(Fv_kN, P_v)
        if rho > 0.0:
            S_v = _shear_area_modulus(family, data, direction, A_v, welded)
            W_reduced = W - (rho * S_v / 1.5 if modulus in ("Z", "Zeff") else rho * S_v)
    M_c_limit: float = (1.2 if simple_span else 1.5) * py_used * Z / 1e3 # 4.2.5.1
    M_c: float = max(min(py_used * W_reduced / 1e3, M_c_limit), 0.0)
    if axis == "x" and family in ("I", "channel") and "d" in data and "t" in data and shear_buckling_required(data["d"] / data["t"], py, welded):
        notes.append("d/t exceeds 70ε (62ε welded): the moment capacity should allow for shear buckling (4.4.4), not implemented.")

    return MomentCapacityResult(
        Mc=M_c,
        axis=axis,
        section_class=cls,
        py=py_used,
        modulus=modulus,
        W=W,
        S=S,
        Z=Z,
        Mc_limit=M_c_limit,
        high_shear=rho > 0.0,
        rho=rho,
        Sv=S_v,
        Fv=Fv_kN or None,
        Pv=P_v,
        M=M_kNm,
        utilisation=_utilisation_check(M_kNm, M_c, "4.2.5", "Moment capacity") if M_kNm is not None else None,
        reference=_reference("4.2.5.3" if rho > 0.0 else "4.2.5.2", title="Moment capacity"),
        metadata={"notes": notes} if notes else {},
    )


# --- 4.3 Lateral-torsional buckling ---
def beam_effective_length(L_LT: float, restraint: str = "both_flanges_free", loading: Loading = "normal", D: Optional[float] = None) -> float:
    """BS 5950-1:2000 4.3.5.1 and Table 13: Effective length LE of a beam without intermediate lateral restraint (mm).

    Args:
        L_LT: Length of the beam between restraints (mm)
        restraint: BEAM_EFFECTIVE_LENGTHS key, the conditions of restraint at the supports
        loading: "normal" or "destabilizing" (4.3.4)
        D: Overall depth of the beam (mm), for the rows with + 2D
    """
    if restraint not in BEAM_EFFECTIVE_LENGTHS:
        raise ValueError(f"Unknown restraint '{restraint}'; expected one of {', '.join(BEAM_EFFECTIVE_LENGTHS)}.")
    normal, destabilizing, plus_2D = BEAM_EFFECTIVE_LENGTHS[restraint]
    L_E: float = (destabilizing if loading == "destabilizing" else normal) * _require_positive(L_LT, "L_LT")
    return L_E + 2.0 * _require_positive(D, "D") if plus_2D else L_E


def segment_effective_length(L_LT: float, loading: Loading = "normal", support_restraint: Optional[str] = None, D: Optional[float] = None) -> float:
    """BS 5950-1:2000 4.3.5.2: Effective length LE of a segment between intermediate lateral restraints (mm).

    1.0LLT for normal loading or 1.2LLT for destabilizing loading; for the segment next to a support, the mean of that and
    the Table 13 value for the restraint at the support, both with LLT the segment length.

    Args:
        L_LT: Segment length between lateral restraints (mm)
        loading: "normal" or "destabilizing"
        support_restraint: BEAM_EFFECTIVE_LENGTHS key, for a segment between a support and the first restraint
        D: Overall depth (mm), for the Table 13 rows with + 2D
    """
    L_E: float = (1.2 if loading == "destabilizing" else 1.0) * _require_positive(L_LT, "L_LT")
    if support_restraint is None:
        return L_E
    return 0.5 * (L_E + beam_effective_length(L_LT, support_restraint, loading, D))


def cantilever_effective_length(
    L: float,
    support: str = "continuous_lateral_torsional",
    tip: str = "free",
    loading: Loading = "normal",
    tip_moment: bool = False,
) -> float:
    """BS 5950-1:2000 4.3.5.4 and Table 14: Effective length LE of a cantilever without intermediate restraint (mm).

    With a moment applied at the tip, LE is increased by the greater of 30 % or 0.3L.

    Args:
        L: Length of the cantilever (mm)
        support: CANTILEVER_EFFECTIVE_LENGTHS key: "continuous_lateral" a), "continuous_partial_torsional" b),
            "continuous_lateral_torsional" c) or "built_in" d)
        tip: "free", "lateral" (restraint to the top flange), "torsional" or "lateral_torsional"
        loading: "normal" or "destabilizing"
        tip_moment: A bending moment is applied at the tip
    """
    if support not in CANTILEVER_EFFECTIVE_LENGTHS or tip not in CANTILEVER_EFFECTIVE_LENGTHS[support]:
        raise ValueError(f"Unknown support '{support}' or tip '{tip}'; see CANTILEVER_EFFECTIVE_LENGTHS.")
    normal, destabilizing = CANTILEVER_EFFECTIVE_LENGTHS[support][tip]
    L = _require_positive(L, "L")
    L_E: float = (destabilizing if loading == "destabilizing" else normal) * L
    return max(1.3 * L_E, L_E + 0.3 * L) if tip_moment else L_E


def _end_moment_points(beta: float) -> tuple[float, float, float]:
    """Quarter-point, mid-length and three-quarter-point moments of a linear diagram from M = 1 to βM."""
    if not -1.0 <= beta <= 1.0:
        raise ValueError("beta must be between -1 and 1.")
    return (3.0 + beta) / 4.0, (1.0 + beta) / 2.0, (1.0 + 3.0 * beta) / 4.0


def equivalent_uniform_moment_factor_mLT(
    beta: Optional[float] = None,
    M2: Optional[float] = None,
    M3: Optional[float] = None,
    M4: Optional[float] = None,
    M_max: Optional[float] = None,
    cantilever: bool = False,
    loading: Loading = "normal",
) -> float:
    """BS 5950-1:2000 4.3.6.6 and Table 18: Equivalent uniform moment factor mLT for lateral-torsional buckling.

    General case: mLT = 0.2 + (0.15M2 + 0.5M3 + 0.15M4)/Mmax but mLT >= 0.44, all moments positive, with M2 and M4 at the
    quarter points and M3 at mid-length. End moments M and βM use the same formula, which gives the tabulated values
    (0.6 + 0.4β for β >= -1/3, 0.44 below -0.5). mLT = 1.0 for cantilevers and the destabilizing loading condition.

    Args:
        beta: End moment ratio, -1 <= β <= 1 (negative in double curvature)
        M2, M3, M4, M_max: Moments of the general case (kNm)
        cantilever: Cantilever without intermediate lateral restraint
        loading: "normal" or "destabilizing"
    """
    if cantilever or loading == "destabilizing":
        return 1.0
    if beta is not None:
        M2, M3, M4 = _end_moment_points(beta)
        M_max = 1.0
    if M2 is None or M3 is None or M4 is None or M_max is None:
        raise ValueError("Pass beta, or M2, M3, M4 and M_max.")
    return max(0.2 + (0.15 * abs(M2) + 0.5 * abs(M3) + 0.15 * abs(M4)) / _require_positive(abs(M_max), "M_max"), 0.44)


def equivalent_uniform_moment_factor_m(
    beta: Optional[float] = None,
    M2: Optional[float] = None,
    M3: Optional[float] = None,
    M4: Optional[float] = None,
    M_max: Optional[float] = None,
    M24: Optional[float] = None,
) -> float:
    """BS 5950-1:2000 4.8.3.3.4 and Table 26: Equivalent uniform moment factor m (mx, my, myx) for flexural buckling.

    m = 0.2 + (0.1M2 + 0.6M3 + 0.1M4)/Mmax but m >= 0.8M24/Mmax, with M2, M3 and M4 signed: positive on one side of the
    axis, and where they lie on both sides the side giving the larger m is positive. Mmax and M24 (the maximum in the
    central half) are positive. End moments M and βM give 0.6 + 0.4β >= 0.4 through the same formula. Sway members and
    cantilever columns take m >= 0.85 (4.8.3.3.4).

    Args:
        beta: End moment ratio, -1 <= β <= 1
        M2, M3, M4: Signed moments at the quarter points and mid-length (kNm)
        M_max: Maximum moment in the segment (kNm)
        M24: Maximum moment in the central half (kNm); defaults to max(|M2|, |M3|, |M4|)
    """
    if beta is not None:
        M2, M3, M4 = _end_moment_points(beta)
        M_max = 1.0
        M24 = max(abs(M2), abs(M3), abs(M4))
    if M2 is None or M3 is None or M4 is None or M_max is None:
        raise ValueError("Pass beta, or M2, M3, M4 and M_max.")
    M_max = _require_positive(abs(M_max), "M_max")
    central: float = abs(M24) if M24 is not None else max(abs(M2), abs(M3), abs(M4))
    terms: float = 0.1 * M2 + 0.6 * M3 + 0.1 * M4
    return max(0.2 + max(terms, -terms) / M_max, 0.8 * central / M_max)


def limiting_equivalent_slenderness(py: float, E: float = E_STEEL) -> float:
    """BS 5950-1:2000 B.2.2: λL0 = 0.4(π²E/py)^0.5; pb = py for λLT <= λL0 (4.3.6.5)."""
    return 0.4 * math.sqrt(math.pi**2 * E / _require_positive(py, "py"))


def _perry_strength(slenderness: float, py: float, eta: float, E: float) -> float:
    """B.2.1 and C.1: the smaller root of (pE - p)(py - p) = η pE p, p = pE py/(φ + (φ² - pE py)^0.5)."""
    if slenderness <= 0.0:
        return py
    p_E: float = math.pi**2 * E / slenderness**2
    phi: float = (py + (eta + 1.0) * p_E) / 2.0
    return p_E * py / (phi + math.sqrt(max(phi**2 - p_E * py, 0.0)))


def bending_strength(lambda_LT: float, py: float, welded: bool = False, E: float = E_STEEL) -> float:
    """BS 5950-1:2000 4.3.6.5 and B.2.1: Bending strength pb for lateral-torsional buckling (N/mm²), Tables 16 and 17.

    pb = pE py/(φLT + (φLT² - pE py)^0.5), pE = π²E/λLT², φLT = (py + (ηLT + 1)pE)/2, and pb = py for λLT <= λL0.
    Perry factor (B.2.2), aLT = 7.0:
        rolled: ηLT = aLT(λLT - λL0)/1000 >= 0
        welded: 0 (λLT <= λL0); 2aLT(λLT - λL0)/1000 (λL0 < λLT < 2λL0); 2aLT λL0/1000 (2λL0 <= λLT <= 3λL0);
            aLT(λLT - λL0)/1000 (λLT > 3λL0)

    Args:
        lambda_LT: Equivalent slenderness λLT
        py: Design strength (N/mm²)
        welded: Welded section (Table 17)
        E: Modulus of elasticity (N/mm²)
    """
    if lambda_LT < 0.0:
        raise ValueError("lambda_LT cannot be negative.")
    lambda_L0: float = limiting_equivalent_slenderness(py, E)
    if lambda_LT <= lambda_L0:
        return py
    if not welded:
        eta: float = ROBERTSON_LTB * (lambda_LT - lambda_L0) / 1e3
    elif lambda_LT < 2.0 * lambda_L0:
        eta = 2.0 * ROBERTSON_LTB * (lambda_LT - lambda_L0) / 1e3
    elif lambda_LT <= 3.0 * lambda_L0:
        eta = 2.0 * ROBERTSON_LTB * lambda_L0 / 1e3
    else:
        eta = ROBERTSON_LTB * (lambda_LT - lambda_L0) / 1e3
    return _perry_strength(lambda_LT, py, eta, E)


def monosymmetry_index(eta: float, D_L_over_D: float = 0.0) -> float:
    """BS 5950-1:2000 4.3.6.7: Approximate monosymmetry index ψ = kη(2η - 1)(1 + 0.5DL/D) for 0.1 <= η <= 0.9, with
    kη = 0.8 for η > 0.5 and 1.0 for η < 0.5; DL is the depth of compression flange lips (0 for plain flanges)."""
    if not 0.1 <= eta <= 0.9:
        raise ValueError("The approximation holds for 0.1 <= η <= 0.9; evaluate ψ with B.2.4.1.")
    k_eta: float = 0.8 if eta > 0.5 else 1.0
    return k_eta * (2.0 * eta - 1.0) * (1.0 + 0.5 * D_L_over_D)


def slenderness_factor(lambda_over_x: float, eta: float = 0.5, psi: float = 0.0) -> float:
    """BS 5950-1:2000 4.3.6.7 and B.2.4.1: Slenderness factor v, Table 19.

    v = 1/{[4η(1 - η) + 0.05(λ/x)² + ψ²]^0.5 + ψ}^0.5, which for equal flanges (η = 0.5, ψ = 0) is [1 + 0.05(λ/x)²]^-0.25.

    Args:
        lambda_over_x: λ/x, slenderness over torsional index
        eta: Flange ratio η = Iyc/(Iyc + Iyt); 0.5 for equal flanges
        psi: Monosymmetry index ψ; see monosymmetry_index()
    """
    root: float = math.sqrt(4.0 * eta * (1.0 - eta) + 0.05 * lambda_over_x**2 + psi**2) + psi
    return 1.0 / math.sqrt(root)


def buckling_parameter(Sx: float, A: float, Ix: float, Iy: float, h_s: Optional[float] = None, H: Optional[float] = None) -> float:
    """BS 5950-1:2000 B.2.3: Buckling parameter u of an I- or H-section, (4Sx²γ/(A²hs²))^0.25, or of a channel with equal
    flanges, (Iy Sx²γ/(A²H))^0.25, with γ = 1 - Iy/Ix.

    Args:
        Sx: Plastic modulus about the major axis (cm³)
        A: Area (cm²)
        Ix, Iy: Second moments of area (cm⁴)
        h_s: Distance between the shear centres of the flanges (mm), D - T for equal flanges; I- and H-sections
        H: Warping constant (dm⁶); channels
    """
    gamma: float = 1.0 - Iy / _require_positive(Ix, "Ix")
    if H is not None:
        return (Iy * Sx**2 * gamma / (A**2 * _require_positive(H, "H") * 1e6)) ** 0.25
    h_s_cm: float = _require_positive(h_s, "h_s") / 10.0
    return (4.0 * Sx**2 * gamma / (_require_positive(A, "A") ** 2 * h_s_cm**2)) ** 0.25


def torsional_index(A: float, J: float, h_s: Optional[float] = None, H: Optional[float] = None, Iy: Optional[float] = None) -> float:
    """BS 5950-1:2000 B.2.3: Torsional index x of an I- or H-section, 0.566hs(A/J)^0.5, or of a channel with equal flanges,
    1.132(AH/(Iy J))^0.5.

    Args:
        A: Area (cm²)
        J: Torsion constant (cm⁴)
        h_s: Distance between the shear centres of the flanges (mm); I- and H-sections
        H: Warping constant (dm⁶), with Iy (cm⁴); channels
    """
    if H is not None:
        return 1.132 * math.sqrt(A * _require_positive(H, "H") * 1e6 / (_require_positive(Iy, "Iy") * _require_positive(J, "J")))
    return 0.566 * _require_positive(h_s, "h_s") / 10.0 * math.sqrt(_require_positive(A, "A") / _require_positive(J, "J"))


def equivalent_slenderness(u: float, v: float, slenderness: float, beta_W: float = 1.0) -> float:
    """BS 5950-1:2000 4.3.6.7 and B.2.3: λLT = u v λ (βW)^0.5, with λ = LE/ry."""
    return u * v * slenderness * math.sqrt(beta_W)


def rhs_limiting_slenderness(D_over_B: float, py: float) -> Optional[float]:
    """BS 5950-1:2000 4.3.6.1 and Table 15: Limiting LE/ry below which an RHS needs no lateral-torsional buckling check.

    Square sections (D/B <= 1) are never susceptible (math.inf). Between the tabulated D/B the next higher row is used,
    which is conservative; below 1.25, the 1.25 row. None beyond D/B = 4, where B.2.6 is always used.
    """
    if D_over_B <= 1.0:
        return math.inf
    for ratio, value in RHS_LIMITING_SLENDERNESS:
        if D_over_B <= ratio + 1e-9:
            return value * 275.0 / _require_positive(py, "py")
    return None


def rhs_torsion_constant(D: float, B: float, t: float) -> float:
    """BS 5950-1:2000 B.2.6.3: Torsion constant of an RHS, J = 4Ah²t/h + ht³/3 (cm⁴), h the mean perimeter and Ah the
    area it encloses (dimensions in mm)."""
    h: float = 2.0 * ((D - t) + (B - t))
    A_h: float = (D - t) * (B - t)
    return (4.0 * A_h**2 * t / h + h * t**3 / 3.0) / 1e4


def box_equivalent_slenderness(Sx: float, A: float, J: float, Ix: float, Iy: float, slenderness: float, beta_W: float = 1.0) -> float:
    """BS 5950-1:2000 B.2.6.1: λLT = 2.25(φb λ βW)^0.5 of a box section or RHS, φb = (Sx²γb/(AJ))^0.5 and
    γb = (1 - Iy/Ix)(1 - J/(2.6Ix)); Sx cm³, A cm², J, Ix and Iy cm⁴, λ = LE/ry."""
    gamma_b: float = (1.0 - Iy / Ix) * (1.0 - J / (2.6 * Ix))
    phi_b: float = math.sqrt(Sx**2 * max(gamma_b, 0.0) / (A * _require_positive(J, "J")))
    return 2.25 * math.sqrt(phi_b * slenderness * beta_W)


def plate_equivalent_slenderness(L_E: float, d: float, t: float, beta_W: float = 1.0) -> float:
    """BS 5950-1:2000 B.2.7: λLT = 2.8(βW LE d/t²)^0.5 of a plate, flat or solid rectangular bar bent about its major axis
    (mLT = 1.0); LE, depth d and thickness t in mm."""
    return 2.8 * math.sqrt(beta_W * _require_positive(L_E, "L_E") * _require_positive(d, "d") / _require_positive(t, "t") ** 2)


def angle_equivalent_slenderness(phi_a: float, L_v: float, r_v: float, psi_a: float = 0.0) -> float:
    """BS 5950-1:2000 B.2.9: λLT of a single angle bent about its major axis u-u, 2.25νa(φa λv)^0.5 with λv = Lv/rv.

    Equal angles (B.2.9.2): νa = 1. Unequal angles (B.2.9.3): νa = {[1 + (4.5ψa/λv)²]^0.5 + 4.5ψa/λv}^0.5, with ψa
    positive when the short leg is in compression and negative when the long leg is (anywhere in the segment).

    Args:
        phi_a: φa = [Zu²γa/(AJ)]^0.5, as tabulated (phi_a, phi_a_min, phi_a_max in the UK tables)
        L_v: Length between points restrained in both the x-x and y-y directions (mm)
        r_v: Radius of gyration about v-v (cm)
        psi_a: Monosymmetry index ψa (psi_a in the UK tables); 0 for equal angles
    """
    lambda_v: float = _require_positive(L_v, "L_v") / (_require_positive(r_v, "r_v") * 10.0)
    shift: float = 4.5 * psi_a / lambda_v
    nu_a: float = math.sqrt(math.sqrt(1.0 + shift**2) + shift)
    return 2.25 * nu_a * math.sqrt(_require_positive(phi_a, "phi_a") * lambda_v)


def angle_buckling_resistance_moment(py: float, Zx: float, L_E: float, r_v: float, heel_in_compression: bool = True) -> float:
    """BS 5950-1:2000 4.3.8.3: Simplified Mb of a single equal angle with b/t <= 15ε bent about x-x (kNm).

    Heel in compression: 0.8pyZx. Heel in tension: pyZx(1350ε - LE/rv)/(1625ε) but <= 0.8pyZx; it applies throughout the
    length Lv if the heel is in tension anywhere within it.

    Args:
        py: Design strength (N/mm²)
        Zx: Smaller section modulus about x-x (cm³)
        L_E: Effective length based on the length Lv between restraints against buckling about v-v (mm)
        r_v: Radius of gyration about v-v (cm)
        heel_in_compression: Heel of the angle in compression
    """
    M_limit: float = 0.8 * py * _require_positive(Zx, "Zx") / 1e3
    if heel_in_compression:
        return M_limit
    eps: float = epsilon(py)
    factor: float = (1350.0 * eps - _require_positive(L_E, "L_E") / (_require_positive(r_v, "r_v") * 10.0)) / (1625.0 * eps)
    return max(min(py * Zx * factor / 1e3, M_limit), 0.0)


class LateralTorsionalBucklingResult(BaseModel):
    # 4.3 Lateral-torsional buckling of a segment in major axis bending; 4.3.6.2: Mx <= Mb/mLT and Mx <= Mcx
    Mb: float # kNm; buckling resistance moment
    Mcx: float # kNm; major axis moment capacity, 4.2.5.2
    pb: Optional[float] = None # N/mm²; 4.3.6.5
    lambda_LT: Optional[float] = None # 4.3.6.7, B.2.6, B.2.7 or B.2.9
    lambda_L0: Optional[float] = None # B.2.2
    slenderness: Optional[float] = None # λ = LE/ry
    u: Optional[float] = None # buckling parameter
    x: Optional[float] = None # torsional index
    v: Optional[float] = None # slenderness factor, Table 19
    beta_W: float = 1.0 # 4.3.6.9
    mLT: float = 1.0 # Table 18
    LE: Optional[float] = None # mm
    section_class: SectionClass # 3.5, in major axis bending
    py: float # N/mm²; pyr for 3.6.5
    modulus: str # "S", "Seff", "Z" or "Zeff"
    W: float # cm³
    susceptible: bool = True # 4.3.6.1: False where Mb = Mcx without a check
    method: str # "4.3.6.4", "4.3.7", "B.2.6", "4.3.8.3" or "4.3.6.1"
    Mx: Optional[float] = None # maximum major axis moment in the segment, kNm
    utilisations: dict[str, float] = Field(default_factory=dict)
    governing: Optional[str] = None
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.LATERAL_TORSIONAL_BUCKLING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_lateral_torsional_buckling(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    LE_mm: Optional[float] = None,
    Mx_kNm: Optional[float] = None,
    mLT: float = 1.0,
    loading: Loading = "normal",
    section_class: Optional[SectionClassInput] = None,
    Fc_kN: Optional[float] = None,
    use_Seff: bool = True,
    simple_span: bool = True,
    welded: bool = False,
    approximate: bool = False,
    u: Optional[float] = None,
    x: Optional[float] = None,
    eta: float = 0.5,
    psi: float = 0.0,
    heel_in_compression: bool = True,
    class_4_method: Class4Method = "effective",
    Z_eff_cm3: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> LateralTorsionalBucklingResult:
    """BS 5950-1:2000 4.3.6: Buckling resistance moment Mb of a segment bent about its major axis, and Mx <= Mb/mLT.

    - I-, H- and channel sections (4.3.6.4 c)): Mb = pb Sx, pb Zx or pb Sx,eff, pb Zx,eff by class, pb from B.2.1 with
      λLT = u v λ βW^0.5; u and x from the tables, else from B.2.3, else the 4.3.6.8 approximations (u = 0.9, x = D/T
      rolled; u = 1.0 welded). `approximate=True` uses those approximations, which is the 4.3.7 simple method (Table 20).
      Channels use the I-section method, valid where loads and reactions act through the shear centre (4.3.6.7 b)).
    - RHS (B.2.6): only where LE/ry exceeds Table 15; λLT = 2.25(φb λ βW)^0.5.
    - CHS and square hollow sections are not susceptible (4.3.6.1), nor any section with λLT <= λL0 (pb = py).
    - Single equal angles (4.3.8.3): the simplified method, bending about x-x.

    Args:
        section: UK section; classified in major axis bending unless `section_class` is given
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        LE_mm: Effective length for lateral-torsional buckling (mm), 4.3.5; see beam_effective_length()
        Mx_kNm: Maximum major axis moment in the segment (kNm)
        mLT: Equivalent uniform moment factor, Table 18; see equivalent_uniform_moment_factor_mLT()
        loading: "destabilizing" sets mLT = 1.0 (4.3.6.6); LE should also be for destabilizing loading
        section_class: Class to use instead of classifying
        Fc_kN: Co-existing axial compression (kN), for the classification (4.8.1)
        use_Seff: Class 3: Mb = pb Sx,eff (βW = Sx,eff/Sx) rather than pb Zx
        simple_span: 4.2.5.1 limit on Mcx: 1.2pyZ, or 1.5pyZ with False
        welded: Welded section (Table 17, B.2.2)
        approximate: 4.3.6.8 conservative u and x
        u, x: Buckling parameter and torsional index; override the tables
        eta, psi: Flange ratio and monosymmetry index for unequal flanges (4.3.6.7); 0.5 and 0 for equal flanges
        heel_in_compression: Single angles (4.3.8.3)
        class_4_method: "effective" or "reduced_strength" (3.6.5)
        Z_eff_cm3: Effective modulus for class 4 (cm³)
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    capacity: MomentCapacityResult = check_bending(
        section, py_mpa, steel_grade, "x", None, 0.0, Fc_kN, section_class, use_Seff, simple_span, welded, class_4_method, Z_eff_cm3, section_type, properties,
    )
    py: float = capacity.py
    M_cx: float = capacity.Mc
    m_LT: float = 1.0 if loading == "destabilizing" else mLT
    notes: list[str] = list(capacity.metadata.get("notes", []))
    S_x: Optional[float] = data.get("Sx")
    beta_W: float = 1.0 if capacity.modulus == "S" or S_x is None else capacity.W / S_x # 4.3.6.9
    common: dict[str, Any] = {
        "Mcx": M_cx,
        "beta_W": beta_W,
        "mLT": m_LT,
        "LE": LE_mm,
        "section_class": capacity.section_class,
        "py": py,
        "modulus": capacity.modulus,
        "W": capacity.W,
        "Mx": Mx_kNm,
    }
    M_b: float = M_cx
    pb, lambda_LT, lambda_L0, slenderness, u_value, x_value, v_value = None, None, None, None, None, None, None
    susceptible: bool = True
    method: str = "4.3.6.4"

    if family == "CHS" or (family == "RHS" and data.get("D") == data.get("B")):
        susceptible, method = False, "4.3.6.1"
    elif family == "RHS":
        slenderness = _require_positive(LE_mm, "LE_mm") / (_get(data, "ry") * 10.0)
        limit: Optional[float] = rhs_limiting_slenderness(_get(data, "D") / _get(data, "B"), py)
        if limit is not None and slenderness <= limit:
            susceptible, method = False, "4.3.6.1"
            notes.append(f"Table 15: LE/ry = {slenderness:.0f} <= {limit:.0f}; no lateral-torsional buckling check.")
        else:
            J: float = data.get("J") or rhs_torsion_constant(_get(data, "D"), _get(data, "B"), _get(data, "t"))
            lambda_LT = box_equivalent_slenderness(_require_positive(S_x, "Sx"), _get(data, "A"), J, _get(data, "Ix"), _get(data, "Iy"), slenderness, beta_W)
            method = "B.2.6"
    elif family in ("I", "channel", "other"):
        slenderness = _require_positive(LE_mm, "LE_mm") / (_get(data, "ry") * 10.0)
        D, T = data.get("D"), data.get("T")
        if approximate:
            u_value, x_value = 1.0 if welded else 0.9, _require_positive(D, "D") / _require_positive(T, "T") # 4.3.6.8
            method = "4.3.6.4" if welded else "4.3.7"
        else:
            u_value, x_value = u or data.get("u"), x or data.get("x")
            try:
                if u_value is None or x_value is None:
                    A, J_value = _get(data, "A"), _get(data, "J")
                    if family == "channel":
                        H: float = _get(data, "H")
                        u_value = u_value or buckling_parameter(_require_positive(S_x, "Sx"), A, _get(data, "Ix"), _get(data, "Iy"), H=H)
                        x_value = x_value or torsional_index(A, J_value, H=H, Iy=_get(data, "Iy"))
                    else:
                        h_s: float = _require_positive(D, "D") - _require_positive(T, "T")
                        u_value = u_value or buckling_parameter(_require_positive(S_x, "Sx"), A, _get(data, "Ix"), _get(data, "Iy"), h_s=h_s)
                        x_value = x_value or torsional_index(A, J_value, h_s=h_s)
            except ValueError:
                u_value, x_value = 1.0 if welded else 0.9, _require_positive(D, "D") / _require_positive(T, "T")
                notes.append("u and x are not tabulated nor computable (B.2.3); the 4.3.6.8 approximations are used.")
        v_value = slenderness_factor(slenderness / x_value, eta, psi)
        lambda_LT = equivalent_slenderness(u_value, v_value, slenderness, beta_W)
    elif family == "angle":
        if data.get("leg_long") != data.get("leg_short"):
            raise NotImplementedError("Unequal angles need the basic method (4.3.8.2): see angle_equivalent_slenderness() and bending_strength().")
        if data["leg_long"] / _get(data, "t") > 15.0 * epsilon(py):
            raise ValueError("4.3.8.3 applies to equal angles with b/t <= 15ε.")
        M_b = angle_buckling_resistance_moment(py, _get(data, "Zx"), _require_positive(LE_mm, "LE_mm"), _get(data, "rv"), heel_in_compression)
        method = "4.3.8.3"
    else:
        raise NotImplementedError(f"Lateral-torsional buckling of {family} sections is not implemented.")

    if lambda_LT is not None:
        lambda_L0 = limiting_equivalent_slenderness(py, E)
        pb = bending_strength(lambda_LT, py, welded, E)
        M_b = pb * capacity.W / 1e3 # 4.3.6.4 c)

    checks: dict[str, float] = {}
    if Mx_kNm is not None:
        checks = {"Mx/Mcx (4.3.6.2)": compute_utilisation(abs(Mx_kNm), M_cx), "mLT Mx/Mb (4.3.6.2)": compute_utilisation(m_LT * abs(Mx_kNm), M_b)}
    governing: Optional[str] = _governing(checks) if checks else None
    return LateralTorsionalBucklingResult(
        Mb=M_b,
        pb=pb,
        lambda_LT=lambda_LT,
        lambda_L0=lambda_L0,
        slenderness=slenderness,
        u=u_value,
        x=x_value,
        v=v_value,
        susceptible=susceptible,
        method=method,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(checks[governing], "4.3.6.2", "Lateral-torsional buckling") if governing else None,
        reference=_reference("4.3.6", title="Resistance to lateral-torsional buckling"),
        metadata={"notes": notes} if notes else {},
        **common,
    )


# --- 4.5 Web bearing capacity and buckling resistance ---
class WebBearingResult(BaseModel):
    # 4.5.2.1 Bearing capacity and 4.5.3.1 buckling resistance of an unstiffened web under a force applied through a flange
    Pbw: float # kN; (b1 + nk)t pyw
    Px: float # kN; buckling resistance, Pxr where the loaded flange is not restrained (4.5.3.1)
    b1: float # stiff bearing length, mm (4.5.1.3)
    n: float
    k: float # mm; T + r rolled, T welded
    py: float # N/mm²; pyw
    Fx: Optional[float] = None # kN
    utilisations: dict[str, float] = Field(default_factory=dict)
    governing: Optional[str] = None
    utilisation: Optional[UtilisationCheck] = None
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_web_bearing(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fx_kN: Optional[float] = None,
    b1_mm: float = 0.0,
    be_mm: Optional[float] = None,
    ae_mm: Optional[float] = None,
    flange_restrained: bool = True,
    LE_mm: Optional[float] = None,
    welded: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> WebBearingResult:
    """BS 5950-1:2000 4.5.2.1 and 4.5.3.1: Bearing capacity and buckling resistance of an unstiffened web.

    Pbw = (b1 + nk)t pyw, with n = 5, or 2 + 0.6be/k <= 5 at the end of a member; k = T + r (rolled) or T (welded).
    Px = 25εt/((b1 + nk)d)^0.5 x Pbw, times (ae + 0.7d)/(1.4d) where the load is less than 0.7d from the end, and times
    0.7d/LE where the loaded flange is not restrained against rotation relative to the web and lateral movement relative
    to the other flange (Pxr). Stiffeners are needed where Fx exceeds either (4.5.2.2, 4.5.3.2, not implemented).

    Args:
        section: UK I, H or channel section
        py_mpa: Design strength of the web (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fx_kN: Local compressive force applied through the flange (kN)
        b1_mm: Stiff bearing length (mm), 4.5.1.3 and Figure 13
        be_mm: Distance from the end of the stiff bearing to the nearer end of the member (mm); None away from an end
        ae_mm: Distance from the load or reaction to the nearer end of the member (mm), where less than 0.7d
        flange_restrained: The loaded flange is restrained against rotation and lateral movement (4.5.3.1 a) and b))
        LE_mm: Effective length of the web as a strut (mm, 4.7.2), where the flange is not restrained
        welded: Welded section
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    py: float = _design_strength(py_mpa, steel_grade, data)
    t, T, d = _get(data, "t"), _get(data, "T"), _get(data, "d")
    k: float = T if welded else T + data.get("r", 0.0)
    n: float = 5.0 if be_mm is None else min(2.0 + 0.6 * be_mm / k, 5.0)
    b1: float = max(b1_mm, 0.0)
    P_bw: float = (b1 + n * k) * t * py / 1e3
    P_x: float = 25.0 * epsilon(py) * t / math.sqrt((b1 + n * k) * d) * P_bw
    notes: list[str] = []
    if ae_mm is not None and ae_mm < 0.7 * d:
        P_x *= (ae_mm + 0.7 * d) / (1.4 * d)
    if not flange_restrained:
        P_x *= 0.7 * d / _require_positive(LE_mm, "LE_mm") # Pxr
        notes.append("Pxr: the loaded flange is not restrained, so Px is reduced by 0.7d/LE.")
    checks: dict[str, float] = {}
    if Fx_kN is not None:
        checks = {"bearing (4.5.2.1)": compute_utilisation(abs(Fx_kN), P_bw), "buckling (4.5.3.1)": compute_utilisation(abs(Fx_kN), P_x)}
    governing: Optional[str] = _governing(checks) if checks else None
    return WebBearingResult(
        Pbw=P_bw,
        Px=P_x,
        b1=b1,
        n=n,
        k=k,
        py=py,
        Fx=Fx_kN,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(checks[governing], "4.5", "Web bearing and buckling") if governing else None,
        reference=_reference("4.5", title="Web bearing capacity and buckling resistance"),
        metadata={"notes": notes} if notes else {},
    )


# --- 4.6 Tension members ---
class TensionResult(BaseModel):
    # 4.6 Tension members: Pt = pyAe (4.6.1), or the reduced capacity of simple ties with eccentric end connections (4.6.3)
    Pt: float # kN
    Ae: float # cm²; effective net area, 3.4.3
    An: float # cm²; net area
    Ag: float # cm²; gross area
    Ke: float # 3.4.3
    py: float # N/mm²
    method: str # "4.6.1", "4.6.3.1" or "4.6.3.2"
    a1: Optional[float] = None # gross area of the connected element, cm²
    a2: Optional[float] = None # Ag - a1, cm²
    Ft: Optional[float] = None # kN
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.TENSILE_YIELDING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_tension(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Ft_kN: Optional[float] = None,
    An_cm2: Optional[float] = None,
    elements: Optional[Sequence[tuple[float, float]]] = None,
    Ke: Optional[float] = None,
    Us_mpa: Optional[float] = None,
    connection: Optional[Connection] = None,
    connected_leg: Literal["long", "short"] = "long",
    a1_cm2: Optional[float] = None,
    both_sides: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TensionResult:
    """BS 5950-1:2000 4.6: Tension capacity Pt.

    4.6.1: Pt = pyAe, Ae the sum of the effective net areas ae = Ke*an <= ag of the elements (3.4.3), but <= 1.2An.
    The elements are given as (ag, an) pairs; with An alone, Ke is not applied (Ae = An), which is conservative since
    the holes may all lie in one element. Without holes, Ae = Ag.

    4.6.3 simple ties connected eccentrically, through one leg of an angle, the web of a channel or the flange of a T,
    with a2 = Ag - a1 and a1 the gross area of the connected element; the holes are taken in the connected element:
        4.6.3.1 single, or double on the same side of a gusset: bolted py(Ae - 0.5a2), welded py(Ag - 0.3a2)
        4.6.3.2 a) double, both sides of a gusset and interconnected: bolted py(Ae - 0.25a2), welded py(Ag - 0.15a2),
            per component

    Args:
        section: UK section; back-to-back angles give the capacity of the pair
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"; also gives Ke
        Ft_kN: Axial tension (kN)
        An_cm2: Net area of the whole section (cm²), see net_area()
        elements: (ag, an) of every element (cm²), for 3.4.3; overrides An_cm2
        Ke: Effective net area coefficient; overrides 3.4.3
        Us_mpa: Specified minimum tensile strength (N/mm²), for Ke of other grades
        connection: "bolted" or "welded", for the simple tie rules of 4.6.3
        connected_leg: "long" or "short" leg of an angle connected
        a1_cm2: Gross area of the connected element of one component (cm²); defaults to t x the connected leg of angles,
            t x D of channels. With `connection`, any holes are taken in the connected element
        both_sides: 4.6.3.2 a), double components on both sides of a gusset, interconnected at least twice
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    A_g: float = _get(data, "A")
    K_e: float = Ke if Ke is not None else effective_net_area_coefficient(steel_grade, py, Us_mpa)
    notes: list[str] = []
    if elements:
        A_n: float = sum(a_n for _, a_n in elements)
        A_e: float = sum(effective_net_area(a_n, a_g, K_e) for a_g, a_n in elements)
    else:
        A_n = _require_positive(An_cm2, "An_cm2") if An_cm2 is not None else A_g
        A_e = A_n
        if A_n < A_g and connection is None:
            notes.append("Ke not applied: pass `elements` [(ag, an), ...] for the effective net area of 3.4.3.")
    if A_n > A_g + 1e-9:
        raise ValueError("Net area An cannot exceed the gross area Ag.")
    A_e = min(A_e, 1.2 * A_n) # 4.6.1

    components: float = 2.0 if family == "double_angle" else 1.0
    a_1, a_2 = None, None
    method: str = "4.6.1"
    if connection is None:
        P_t: float = py * A_e / 10.0
    else:
        if a1_cm2 is not None:
            a_1 = a1_cm2 * components
        elif family in ("angle", "double_angle"):
            leg: float = _get(data, "leg_long" if connected_leg == "long" else "leg_short")
            a_1 = components * leg * _get(data, "t") / 100.0
        elif family == "channel":
            a_1 = _get(data, "D") * _get(data, "t") / 100.0
        else:
            raise ValueError("Pass a1_cm2, the gross area of the connected element (4.6.3).")
        a_2 = A_g - a_1
        if not 0.0 < a_1 < A_g:
            raise ValueError("a1 must be positive and less than the gross area.")
        holes: float = A_g - A_n # all in the connected element
        A_e = min(effective_net_area(a_1 - holes, a_1, K_e) + a_2, 1.2 * A_n)
        double_rule: bool = both_sides and components == 2.0
        method = "4.6.3.2" if double_rule else "4.6.3.1"
        if connection == "bolted":
            P_t = py * (A_e - (0.25 if double_rule else 0.5) * a_2) / 10.0
        else:
            P_t = py * (A_g - (0.15 if double_rule else 0.3) * a_2) / 10.0

    return TensionResult(
        Pt=P_t,
        Ae=A_e,
        An=A_n,
        Ag=A_g,
        Ke=K_e,
        py=py,
        method=method,
        a1=a_1,
        a2=a_2,
        Ft=Ft_kN,
        utilisation=_utilisation_check(Ft_kN, P_t, method, "Tension capacity") if Ft_kN is not None else None,
        reference=_reference(method, title="Tension members"),
        metadata={"notes": notes} if notes else {},
    )


# --- 4.7 Compression members ---
def effective_length(L: float, restraint: str = "pinned_pinned") -> float:
    """BS 5950-1:2000 4.7.3 and Table 22: Nominal effective length LE of a compression member (mm).

    Args:
        L: Segment length between restraints in the plane considered (mm)
        restraint: COMPRESSION_EFFECTIVE_LENGTHS key; non-sway "fixed_fixed", "partial_partial", "fixed_pinned",
            "pinned_pinned", or sway "sway_fixed", "sway_partial", "sway_free"
    """
    if restraint not in COMPRESSION_EFFECTIVE_LENGTHS:
        raise ValueError(f"Unknown restraint '{restraint}'; expected one of {', '.join(COMPRESSION_EFFECTIVE_LENGTHS)}.")
    return COMPRESSION_EFFECTIVE_LENGTHS[restraint] * _require_positive(L, "L")


def _strut_shape(section_type: Optional[SectionType], data: dict[str, float], welded: bool) -> str:
    family: str = _family(section_type)
    if family == "I":
        if welded:
            return "welded_I"
        return "rolled_I" if _get(data, "D") / _get(data, "B") > 1.2 else "rolled_H" # UB are I-sections, UC and UBP H
    if family in ("RHS", "CHS", "EHS"):
        if welded:
            return "welded_box"
        return "cold_formed_hollow" if section_type in (SectionType.CFRHS, SectionType.CFSHS, SectionType.CFCHS) else "hot_finished_hollow"
    if family in ("channel", "angle", "double_angle"):
        return "angle_channel_tee"
    raise NotImplementedError(f"Table 23 has no strut curve for {family} sections; pass `curves` or `shape`.")


def strut_curve(
    section_type: Optional[SectionType] = None,
    axis: str = "x",
    T: Optional[float] = None,
    welded: bool = False,
    shape: Optional[str] = None,
    D: Optional[float] = None,
    B: Optional[float] = None,
) -> str:
    """BS 5950-1:2000 4.7.5 and Table 23: Strut curve a) to d) for buckling about `axis`.

    Rolled I-sections (D/B > 1.2, i.e UB) and H-sections (UC, UBP) are told apart by D/B. For thicknesses between 40 mm
    and 50 mm Table 23 NOTE 1 averages the pc of both rows; check_compression() does that.

    Args:
        section_type: Section type
        axis: "x", "y", or any other axis (e.g "v" of angles), which takes the y-y curve
        T: Maximum thickness of the section (mm)
        welded: Welded I, H or box section
        shape: STRUT_CURVES key; overrides the section type
        D, B: Depth and breadth (mm), for rolled I or H
    """
    shape_value: str = shape or _strut_shape(section_type, {"D": D or 0.0, "B": B or 0.0}, welded)
    if shape_value not in STRUT_CURVES:
        raise ValueError(f"Unknown shape '{shape_value}'; expected one of {', '.join(STRUT_CURVES)}.")
    curves: tuple[str, str] = STRUT_CURVES[shape_value][1 if (T is not None and T > 40.0) else 0]
    return curves[0] if axis == "x" else curves[1]


def limiting_slenderness(py: float, E: float = E_STEEL) -> float:
    """BS 5950-1:2000 C.2: λ0 = 0.2(π²E/py)^0.5, below which pc = py."""
    return 0.2 * math.sqrt(math.pi**2 * E / _require_positive(py, "py"))


def compressive_strength(slenderness: float, py: float, curve: str = "b", E: float = E_STEEL) -> float:
    """BS 5950-1:2000 4.7.5 and C.1: Compressive strength pc (N/mm²), Table 24.

    pc = pE py/(φ + (φ² - pE py)^0.5), pE = π²E/λ², φ = (py + (η + 1)pE)/2, η = a(λ - λ0)/1000 >= 0 with λ0 from
    limiting_slenderness() and the Robertson constant a = 2.0, 3.5, 5.5 or 8.0 for strut curves a) to d).

    Args:
        slenderness: λ = LE/r (4.7.2)
        py: Design strength (N/mm²); 20 N/mm² less for welded I, H and box sections (4.7.5)
        curve: Strut curve "a", "b", "c" or "d" (Table 23)
        E: Modulus of elasticity (N/mm²)
    """
    if curve not in ROBERTSON_CONSTANTS:
        raise ValueError(f"Unknown strut curve '{curve}'; expected one of {', '.join(ROBERTSON_CONSTANTS)}.")
    if slenderness < 0.0:
        raise ValueError("slenderness cannot be negative.")
    py = _require_positive(py, "py")
    eta: float = max(ROBERTSON_CONSTANTS[curve] * (slenderness - limiting_slenderness(py, E)) / 1e3, 0.0)
    return _perry_strength(slenderness, py, eta, E)


def single_angle_slenderness(
    L_v: float,
    r_v: float,
    L_a: float,
    r_a: float,
    L_b: float,
    r_b: float,
    connection: Literal["two_bolts", "slotted", "single_bolt"] = "two_bolts",
    alternate_restraint: bool = False,
) -> float:
    """BS 5950-1:2000 4.7.10.2 and Table 25: Slenderness λ of a single angle strut connected by one leg at each end.

    a) "two_bolts", two or more bolts in standard holes in line, or welded: the greatest of 0.85Lv/rv >= 0.7Lv/rv + 15,
       1.0La/ra >= 0.7La/ra + 30 and 0.85Lb/rb >= 0.7Lb/rb + 30
    b) "slotted", one bolt in a standard hole and one in a kidney-shaped slot, and c) "single_bolt": the same with factors
       1.0; c) also takes 80 % of the compression resistance (see check_angle_strut())
    Alternate restraints to the two legs increase λ by 20 % (4.7.10.1). a-a is the axis parallel to the connected leg and
    b-b the axis perpendicular to it.

    Args:
        L_v, L_a, L_b: Lengths between restraints for buckling about v-v, a-a and b-b (mm), between the intersections of the
            centroidal axes or of the setting out lines of the bolts
        r_v, r_a, r_b: Radii of gyration (cm)
        connection: "two_bolts", "slotted" or "single_bolt"
        alternate_restraint: Lateral restraints to the two legs alternately
    """
    factor: float = 0.85 if connection == "two_bolts" else 1.0
    lam_v: float = _require_positive(L_v, "L_v") / (_require_positive(r_v, "r_v") * 10.0)
    lam_a: float = _require_positive(L_a, "L_a") / (_require_positive(r_a, "r_a") * 10.0)
    lam_b: float = _require_positive(L_b, "L_b") / (_require_positive(r_b, "r_b") * 10.0)
    slenderness: float = max(max(factor * lam_v, 0.7 * lam_v + 15.0), max(lam_a, 0.7 * lam_a + 30.0), max(factor * lam_b, 0.7 * lam_b + 30.0))
    return 1.2 * slenderness if alternate_restraint else slenderness


def double_angle_slenderness(
    L_x: float,
    r_x: float,
    L_y: float,
    r_y: float,
    lambda_c: float,
    connection: Literal["one_side_bolts", "one_side_single_bolt", "both_sides_bolts", "both_sides_slotted", "both_sides_single_bolt"] = "one_side_bolts",
) -> float:
    """BS 5950-1:2000 4.7.10.3 and Table 25: Slenderness λ of double angles, back-to-back (4.7.13) or battened (4.7.12),
    connected by one leg of each angle at each end.

    x-x: 1.0Lx/rx >= 0.7Lx/rx + 30 (0.85Lx/rx for c) "both_sides_bolts"); y-y, parallel to the connected surfaces:
    [(kLy/ry)² + λc²]^0.5 >= 1.4λc, with k = 0.85 for a) "one_side_bolts" and 1.0 otherwise. e) "both_sides_single_bolt"
    also takes 80 % of the compression resistance.

    Args:
        L_x, L_y: Lengths between restraints for buckling about x-x and y-y (mm)
        r_x, r_y: Radii of gyration of the pair (cm)
        lambda_c: λc = Lv/rv of one angle, Lv between interconnecting bolts or end welds of adjacent battens
        connection: a) "one_side_bolts", b) "one_side_single_bolt", c) "both_sides_bolts", d) "both_sides_slotted" or
            e) "both_sides_single_bolt"
    """
    lam_x: float = _require_positive(L_x, "L_x") / (_require_positive(r_x, "r_x") * 10.0)
    lam_y: float = _require_positive(L_y, "L_y") / (_require_positive(r_y, "r_y") * 10.0)
    x_factor: float = 0.85 if connection == "both_sides_bolts" else 1.0
    y_factor: float = 0.85 if connection == "one_side_bolts" else 1.0
    return max(max(x_factor * lam_x, 0.7 * lam_x + 30.0), max(math.sqrt((y_factor * lam_y) ** 2 + lambda_c**2), 1.4 * lambda_c))


def channel_slenderness(L_x: float, r_x: float, L_y: float, r_y: float, rows: Literal["two_rows", "single_row"] = "two_rows") -> float:
    """BS 5950-1:2000 4.7.10.4: Slenderness of a single channel connected only by its web at each end, the greater of
    0.85Lx/rx (two or more rows of bolts, or welded; 1.0Lx/rx for a single row) and 1.0Ly/ry >= 0.7Ly/ry + 30."""
    lam_x: float = _require_positive(L_x, "L_x") / (_require_positive(r_x, "r_x") * 10.0)
    lam_y: float = _require_positive(L_y, "L_y") / (_require_positive(r_y, "r_y") * 10.0)
    return max((0.85 if rows == "two_rows" else 1.0) * lam_x, max(lam_y, 0.7 * lam_y + 30.0))


def tee_slenderness(L_x: float, r_x: float, L_y: float, r_y: float, rows: Literal["two_rows", "single_row"] = "two_rows") -> float:
    """BS 5950-1:2000 4.7.10.5: Slenderness of a single T-section connected only by its flange at each end, the greater of
    1.0Lx/rx >= 0.7Lx/rx + 30 and 0.85Ly/ry (two or more rows of bolts, or welded; 1.0Ly/ry for a single row)."""
    lam_x: float = _require_positive(L_x, "L_x") / (_require_positive(r_x, "r_x") * 10.0)
    lam_y: float = _require_positive(L_y, "L_y") / (_require_positive(r_y, "r_y") * 10.0)
    return max(max(lam_x, 0.7 * lam_x + 30.0), (0.85 if rows == "two_rows" else 1.0) * lam_y)


def _radius_of_gyration(axis: str, data: dict[str, float], raw: dict[str, Any], back_to_back_gap_mm: Optional[float]) -> float:
    """r about `axis` (cm); back-to-back angles tabulate ry (i_zz) per gap, interpolated here."""
    if f"r{axis}" in data:
        return data[f"r{axis}"]
    gaps = raw.get("i_zz")
    if axis == "y" and isinstance(gaps, dict) and gaps:
        points: list[tuple[float, float]] = sorted((float(gap), float(value)) for gap, value in gaps.items())
        if back_to_back_gap_mm is None:
            return points[0][1] # the smallest gap, conservative
        gap: float = min(max(back_to_back_gap_mm, points[0][0]), points[-1][0])
        for (g0, r0), (g1, r1) in zip(points, points[1:]):
            if g0 <= gap <= g1:
                return r0 + (r1 - r0) * (gap - g0) / (g1 - g0) if g1 > g0 else r0
        return points[-1][1]
    return _get(data, f"r{axis}")


class StrutResult(BaseModel):
    axis: str # "x", "y" or "v"
    LE: Optional[float] = None # mm
    r: Optional[float] = None # cm
    slenderness: float # λ, 4.7.2; reduced by (Aeff/Ag)^0.5 for class 4 (pcs)
    curve: str # Table 23
    pc: float # N/mm²; pcs for class 4
    Pc: float # kN


class CompressionResult(BaseModel):
    # 4.7.4 Compression resistance, Agpc (class 1 to 3) or Aeff pcs (class 4), the least over the buckling axes
    Pc: float # kN
    Pcx: Optional[float] = None # kN; buckling about the major axis only
    Pcy: Optional[float] = None # kN; buckling about the minor axis only
    governing_axis: str
    section_class: SectionClass # 3.5, in axial compression (r2 from Fc where given)
    py: float # N/mm²; pyr for the 3.6.5 method
    py_strut: float # N/mm²; for pc, 20 N/mm² less for welded I, H and box sections (4.7.5)
    A: float # cm²; Ag, or Aeff for class 4
    Ag: float # cm²
    modes: list[StrutResult]
    Fc: Optional[float] = None # kN
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.FLEXURAL_BUCKLING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_compression(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fc_kN: Optional[float] = None,
    LEx_mm: Optional[float] = None,
    LEy_mm: Optional[float] = None,
    LEv_mm: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    curves: Optional[dict[str, str]] = None,
    slenderness: Optional[dict[str, float]] = None,
    A_eff_cm2: Optional[float] = None,
    class_4_method: Class4Method = "effective",
    reduction: float = 1.0,
    back_to_back_gap_mm: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CompressionResult:
    """BS 5950-1:2000 4.7.4: Compression resistance Pc of a member, for every axis with an effective length.

    Pc = Ag pc (class 1 to 3) or Aeff pcs (class 4, 3.6), pcs being pc at λ(Aeff/Ag)^0.5. pc is from Annex C with the strut
    curve of Table 23, and py - 20 N/mm² for welded I, H and box sections; between 40 mm and 50 mm thick the pc of both
    rows is averaged (Table 23 NOTE 1). The class is for axial compression, with r2 = Fc/(Ag py) where Fc is given
    (3.5.5), else r2 = 1.

    Args:
        section: UK section; classified in axial compression unless `section_class` is given
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fc_kN: Axial compression (kN)
        LEx_mm, LEy_mm: Effective lengths for buckling about x-x and y-y (mm), 4.7.3; see effective_length()
        LEv_mm: Effective length about v-v of single angles (mm)
        section_class: Class to use instead of classifying
        welded: Welded I, H or box section
        curves: Strut curves per axis, e.g {"x": "b", "y": "c"}; override Table 23
        slenderness: λ per axis, e.g from single_angle_slenderness(); overrides LE/r
        A_eff_cm2: Effective area for class 4 (cm²); overrides 3.6
        class_4_method: "effective" or "reduced_strength" (3.6.5)
        reduction: Factor on Pc, e.g 0.8 for angles connected by a single bolt (4.7.10.2 c), 4.7.10.3 e))
        back_to_back_gap_mm: Gap between back-to-back angles, for ry from the tables; the smallest gap by default
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    py: float = _design_strength(py_mpa, steel_grade, data)
    A_g: float = _get(data, "A")
    classification: Optional[ClassificationResult] = None
    if section_class is not None:
        cls: SectionClass = _as_section_class(section_class)
    else:
        classification = _classify(section_type, raw, py, StressPattern.COMPRESSION, Fc_kN)
        cls = classification.section_class
    notes: list[str] = []
    A: float = A_g
    py_used: float = py
    if cls == SectionClass.CLASS_4:
        if A_eff_cm2 is not None:
            A = _require_positive(A_eff_cm2, "A_eff_cm2")
        else:
            classification = classification or _classify(section_type, raw, py, StressPattern.COMPRESSION, Fc_kN)
            effective: EffectiveSection = _effective_section(section_type, data, classification, StressPattern.COMPRESSION, class_4_method)
            notes.extend(effective.metadata.get("notes", []))
            if effective.py_r is not None:
                py_used = effective.py_r
                notes.append(f"3.6.5: reduced design strength pyr = {effective.py_r:.1f} N/mm².")
            else:
                A = _require_positive(effective.A_eff, "A_eff")
    effective_ratio: float = math.sqrt(A / A_g) # 4.7.4 b): pcs at λ(Aeff/Ag)^0.5
    py_strut: float = py_used - 20.0 if welded and _family(section_type) in ("I", "RHS", "CHS", "other") else py_used # 4.7.5
    curves = curves or {}
    slenderness = slenderness or {}
    T_max: float = max(data.get("T", 0.0), data.get("t", 0.0))

    modes: list[StrutResult] = []
    for axis, L_E in (("x", LEx_mm), ("y", LEy_mm), ("v", LEv_mm)):
        if L_E is None and axis not in slenderness:
            continue
        r: Optional[float] = None
        if axis in slenderness:
            lam: float = slenderness[axis]
        else:
            r = _radius_of_gyration(axis, data, raw, back_to_back_gap_mm)
            lam = _require_positive(L_E, f"LE{axis}_mm") / (r * 10.0)
        lam_used: float = lam * effective_ratio
        if axis in curves:
            curve: str = curves[axis]
            p_c: float = compressive_strength(lam_used, py_strut, curve, E)
        else:
            shape: str = _strut_shape(section_type, data, welded)
            curve = strut_curve(axis=axis, T=T_max, shape=shape)
            p_c = compressive_strength(lam_used, py_strut, curve, E)
            if 40.0 < T_max <= 50.0: # Table 23 NOTE 1
                thin: str = strut_curve(axis=axis, T=40.0, shape=shape)
                if thin != curve:
                    p_c = 0.5 * (p_c + compressive_strength(lam_used, py_strut, thin, E))
                    curve = f"{thin}/{curve}"
        modes.append(StrutResult(axis=axis, LE=L_E, r=r, slenderness=lam_used, curve=curve, pc=p_c, Pc=reduction * A * p_c / 10.0))

    if not modes:
        raise ValueError("Pass at least one effective length: LEx_mm, LEy_mm or LEv_mm (or `slenderness`).")
    governing: StrutResult = min(modes, key=lambda mode: mode.Pc)
    by_axis: dict[str, float] = {mode.axis: mode.Pc for mode in modes}
    return CompressionResult(
        Pc=governing.Pc,
        Pcx=by_axis.get("x"),
        Pcy=by_axis.get("y"),
        governing_axis=governing.axis,
        section_class=cls,
        py=py_used,
        py_strut=py_strut,
        A=A,
        Ag=A_g,
        modes=modes,
        Fc=Fc_kN,
        utilisation=_utilisation_check(Fc_kN, governing.Pc, "4.7.4", "Compression resistance") if Fc_kN is not None else None,
        reference=_reference("4.7.4", title="Compression resistance"),
        metadata={"notes": notes} if notes else {},
    )


def _component_angle_rv(section_type: Optional[SectionType], designation: str) -> float:
    """rv of one angle of a back-to-back pair (cm), from the single angle tables; e.g "90x90x12" is "90x90x12.0" there."""
    from steelsnakes.base.exceptions import SectionNotFoundError
    from steelsnakes.UK.sections.angles import L_EQUAL, L_UNEQUAL

    constructor = L_EQUAL if section_type == SectionType.L_EQUAL_B2B else L_UNEQUAL
    parts: list[str] = designation.split("x")
    candidates: list[str] = [designation]
    if len(parts) == 3:
        candidates.append(f"{parts[0]}x{parts[1]}x{float(parts[2]):.1f}")
    for candidate in candidates:
        try:
            return float(constructor(candidate).get_properties()["i_vv"])
        except (SectionNotFoundError, KeyError, ValueError):
            continue
    raise ValueError(f"No single angle '{designation}' in the tables; pass r_v_cm, rv of one angle.")


def check_angle_strut(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fc_kN: Optional[float] = None,
    L_mm: float = 0.0,
    connection: str = "two_bolts",
    connected_leg: Literal["long", "short"] = "long",
    L_v_mm: Optional[float] = None,
    L_a_mm: Optional[float] = None,
    L_b_mm: Optional[float] = None,
    L_c_mm: Optional[float] = None,
    r_v_cm: Optional[float] = None,
    back_to_back_gap_mm: Optional[float] = None,
    alternate_restraint: bool = False,
    section_class: Optional[SectionClassInput] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CompressionResult:
    """BS 5950-1:2000 4.7.10: Angle strut, single or double, designed as axially loaded (end eccentricity neglected).

    The slenderness is from single_angle_slenderness() (4.7.10.2) or double_angle_slenderness() (4.7.10.3), strut curve c,
    and connections by a single bolt take 80 % of the compression resistance.

    Args:
        section: L_EQUAL, L_UNEQUAL, L_EQUAL_B2B or L_UNEQUAL_B2B
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fc_kN: Axial compression (kN)
        L_mm: Length between the intersections of the centroidal axes or bolt setting out lines (mm); default for L_v,
            L_a and L_b (single) or L_x and L_y (double)
        connection: single angles "two_bolts", "slotted" or "single_bolt"; double angles "one_side_bolts",
            "one_side_single_bolt", "both_sides_bolts", "both_sides_slotted" or "both_sides_single_bolt"
        connected_leg: "long" or "short"; a-a is parallel to the connected leg
        L_v_mm, L_a_mm, L_b_mm: Lengths about v-v, a-a and b-b (single); L_a_mm and L_b_mm are L_x and L_y (double)
        L_c_mm: Spacing of the interconnections of double angles (mm), for λc
        r_v_cm: rv of one angle of a pair (cm); by default from the single angle tables
        back_to_back_gap_mm: Gap between back-to-back angles, for ry
        alternate_restraint: Single angles restrained on the two legs alternately (+20 %)
        section_class: Class to use instead of classifying
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    if family == "angle":
        # UK tables: y-y is perpendicular to the long leg, z-z parallel to it
        r_a: float = _get(data, "ry" if connected_leg == "long" else "rx")
        r_b: float = _get(data, "rx" if connected_leg == "long" else "ry")
        lam: float = single_angle_slenderness(
            L_v_mm or L_mm, _get(data, "rv"), L_a_mm or L_mm, r_a, L_b_mm or L_mm, r_b, connection, alternate_restraint, # type: ignore[arg-type]
        )
        reduction: float = 0.8 if connection == "single_bolt" else 1.0
    elif family == "double_angle":
        r_v: Optional[float] = r_v_cm if r_v_cm is not None else _component_angle_rv(section_type, str(raw.get("designation")))
        lambda_c: float = _require_positive(L_c_mm, "L_c_mm") / (r_v * 10.0)
        lam = double_angle_slenderness(
            L_a_mm or L_mm, _get(data, "rx"), L_b_mm or L_mm, _radius_of_gyration("y", data, raw, back_to_back_gap_mm), lambda_c, connection, # type: ignore[arg-type]
        )
        reduction = 0.8 if connection == "both_sides_single_bolt" else 1.0
    else:
        raise ValueError("check_angle_strut() is for single and double angles; see channel_slenderness() and tee_slenderness().")
    result: CompressionResult = check_compression(
        section, py_mpa, steel_grade, Fc_kN, section_class=section_class, slenderness={"y": lam}, curves={"y": "c"},
        reduction=reduction, section_type=section_type, properties=properties,
    )
    result.reference = _reference("4.7.10", title="Angle, channel or T-section struts")
    result.metadata.update({"connection": connection, "slenderness": lam})
    return result


# --- 4.7.7 Columns in simple structures ---
def simple_column_eccentricity(section: Optional[BaseSection] = None, axis: BendingAxis = "x", bearing: float = 0.0, section_type: Optional[SectionType] = None, properties: Optional[dict[str, Any]] = None) -> float:
    """BS 5950-1:2000 4.7.7 3): Eccentricity of a simple beam reaction on a column, 100 mm from the face of the steel column
    or at the centre of the stiff bearing, whichever is greater (mm).

    Args:
        section: Column section
        axis: "x" for a beam on the flange (face at D/2), "y" for a beam on the web (face at t/2)
        bearing: Length of stiff bearing from the face (mm)
    """
    _, data, _ = _section_data(section, section_type, properties)
    face: float = _get(data, "D") / 2.0 if axis == "x" else _get(data, "t") / 2.0
    return face + max(100.0, bearing / 2.0)


class SimpleColumnResult(BaseModel):
    # 4.7.7 Columns in simple structures, nominal moments only: Fc/Pc + Mx/Mbs + My/(pyZy) <= 1
    Pc: float # kN; 4.7.4
    Mbs: float # kNm; buckling resistance moment for simple columns
    Mcy: float # kNm; py Zy
    lambda_LT: Optional[float] = None # 0.5L/ry
    section_class: SectionClass
    Fc: float # kN
    Mx: float # kNm
    My: float # kNm
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_simple_column(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fc_kN: float = 0.0,
    Mx_kNm: float = 0.0,
    My_kNm: float = 0.0,
    LEx_mm: Optional[float] = None,
    LEy_mm: Optional[float] = None,
    L_mm: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> SimpleColumnResult:
    """BS 5950-1:2000 4.7.7: Column in a simple structure under the nominal moments from beam reactions.

    Fc/Pc + Mx/Mbs + My/(pyZy) <= 1, all m = 1.0. Mbs is Mb from 4.3.6.4 with λLT = 0.5L/ry for doubly symmetric I and H
    sections; for CHS, SHS and RHS within Table 15, Mbs = Mc. Other sections take Mb of 4.3 with LE = L.

    Args:
        section: UK section
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fc_kN: Axial compression (kN)
        Mx_kNm, My_kNm: Nominal moments (kNm), see simple_column_eccentricity()
        LEx_mm, LEy_mm: Effective lengths for flexural buckling (mm)
        L_mm: Distance between levels at which the column is laterally restrained in both directions (mm)
        section_class: Class to use instead of classifying
        welded: Welded section
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    compression: CompressionResult = check_compression(section, py, steel_grade, Fc_kN or None, LEx_mm, LEy_mm, section_class=section_class, welded=welded, E=E, section_type=section_type, properties=properties)
    L: float = _require_positive(L_mm if L_mm is not None else LEy_mm, "L_mm")
    lambda_LT: Optional[float] = None
    if family == "I":
        capacity: MomentCapacityResult = check_bending(section, py, steel_grade, "x", section_class=section_class, section_type=section_type, properties=properties)
        lambda_LT = 0.5 * L / (_get(data, "ry") * 10.0)
        M_bs: float = bending_strength(lambda_LT, capacity.py, welded, E) * capacity.W / 1e3 # 4.3.6.4 with λLT = 0.5L/ry
        cls: SectionClass = capacity.section_class
    else:
        ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(section, py, steel_grade, LE_mm=L, section_class=section_class, welded=welded, E=E, section_type=section_type, properties=properties)
        M_bs = ltb.Mb
        cls = ltb.section_class
    if compression.section_class == SectionClass.CLASS_4: # 4.8.1; axial compression alone is never class 1 or 2
        cls = SectionClass.CLASS_4
    M_cy: float = py * _get(data, "Zy") / 1e3
    utilisation: float = compute_utilisation(Fc_kN, compression.Pc) + compute_utilisation(abs(Mx_kNm), M_bs) + compute_utilisation(abs(My_kNm), M_cy)
    return SimpleColumnResult(
        Pc=compression.Pc,
        Mbs=M_bs,
        Mcy=M_cy,
        lambda_LT=lambda_LT,
        section_class=cls,
        Fc=Fc_kN,
        Mx=Mx_kNm,
        My=My_kNm,
        utilisation=_ratio_check(utilisation, "4.7.7", "Columns in simple structures"),
        reference=_reference("4.7.7", title="Columns in simple structures"),
        metadata={"Pcx": compression.Pcx, "Pcy": compression.Pcy},
    )


# --- 4.8 Members with combined moment and axial force ---
def reduced_plastic_moduli(n: float, A: float, D: float, B: float, T: float, t: float, Sx: float, Sy: float) -> tuple[float, float]:
    """BS 5950-1:2000 I.2.1: Reduced plastic moduli (Srx, Sry) of an I- or H-section with equal flanges (cm³).

    Srx = Sx - (A²/4t)n² for n <= t(D - 2T)/A, else (A²/4B)(2BD/A - 1 + n)(1 - n)
    Sry = Sy - (A²/4D)n² for n <= tD/A, else (A²/8T)(4BT/A - 1 + n)(1 - n)

    Args:
        n: Axial force ratio F/(A py)
        A: Area (cm²)
        D, B, T, t: Depth, flange width, flange and web thickness (mm)
        Sx, Sy: Plastic moduli (cm³)
    """
    n = min(abs(n), 1.0)
    D, B, T, t = D / 10.0, B / 10.0, T / 10.0, t / 10.0 # cm
    S_rx: float = Sx - A**2 / (4.0 * t) * n**2 if n <= t * (D - 2.0 * T) / A else A**2 / (4.0 * B) * (2.0 * B * D / A - 1.0 + n) * (1.0 - n)
    S_ry: float = Sy - A**2 / (4.0 * D) * n**2 if n <= t * D / A else A**2 / (8.0 * T) * (4.0 * B * T / A - 1.0 + n) * (1.0 - n)
    return max(min(S_rx, Sx), 0.0), max(min(S_ry, Sy), 0.0)


def _reduced_plastic_moduli(family: str, data: dict[str, float], n: float) -> Optional[tuple[float, float]]:
    """I.2: Srx and Sry of I and H (I.2.1), RHS as an I-section with webs 2t by statics (I.2.2), and CHS, S cos(πn/2)."""
    if family == "I":
        return reduced_plastic_moduli(n, _get(data, "A"), _get(data, "D"), _get(data, "B"), _get(data, "T"), _get(data, "t"), _get(data, "Sx"), _get(data, "Sy"))
    if family == "RHS":
        A, D, B, t = _get(data, "A"), _get(data, "D"), _get(data, "B"), _get(data, "t")
        S_rx, _ = reduced_plastic_moduli(n, A, D, B, t, 2.0 * t, _get(data, "Sx"), _get(data, "Sy"))
        S_ry, _ = reduced_plastic_moduli(n, A, B, D, t, 2.0 * t, _get(data, "Sy"), _get(data, "Sx"))
        return S_rx, S_ry
    if family == "CHS":
        factor: float = math.cos(math.pi * min(abs(n), 1.0) / 2.0)
        return _get(data, "Sx") * factor, _get(data, "Sy") * factor
    return None


def _biaxial_exponents(family: str) -> tuple[float, float]:
    """4.8.2.3: (z1, z2): I and H 2.0, 1.0; CHS 2.0, 2.0; RHS 5/3, 5/3; other 1.0, 1.0."""
    return {"I": (2.0, 1.0), "CHS": (2.0, 2.0), "RHS": (5.0 / 3.0, 5.0 / 3.0)}.get(family, (1.0, 1.0))


def _exact_cross_section(family: str, cls: SectionClass, data: dict[str, float], py: float, F: float, Mx: float, My: float, M_cx: float, M_cy: float) -> Optional[tuple[float, float, float]]:
    """4.8.2.3 for class 1 and 2: (utilisation, Mrx, Mry), with Mr <= Mc; None where the shape has no reduced moduli."""
    if not _is_plastic(cls):
        return None
    try:
        moduli: Optional[tuple[float, float]] = _reduced_plastic_moduli(family, data, F / (_get(data, "A") * py / 10.0))
    except ValueError:
        return None
    if moduli is None:
        return None
    M_rx: float = min(py * moduli[0] / 1e3, M_cx)
    M_ry: float = min(py * moduli[1] / 1e3, M_cy)
    z1, z2 = _biaxial_exponents(family)
    if Mx and My:
        utilisation: float = compute_utilisation(Mx, M_rx) ** z1 + compute_utilisation(My, M_ry) ** z2
    else:
        utilisation = max(compute_utilisation(Mx, M_rx), compute_utilisation(My, M_ry))
    return utilisation, M_rx, M_ry


class CombinedResult(BaseModel):
    # 4.8 Members with combined moment and axial force (4.9 with no axial force)
    method: str # "4.8.2.2", "4.8.2.3", "simplified", "exact" or "stocky"
    section_class: Optional[SectionClass] = None # 4.8.1: under the moment and axial force together
    py: float # N/mm²
    Fc: float = 0.0 # kN
    Ft: float = 0.0 # kN
    Mx: float = 0.0 # kNm
    My: float = 0.0 # kNm
    MLT: Optional[float] = None # kNm; maximum major axis moment in the segment governing Mb
    Pt: Optional[float] = None # kN; 4.6.1
    Pc: Optional[float] = None # kN; 4.7.4
    Pcx: Optional[float] = None # kN
    Pcy: Optional[float] = None # kN
    Mcx: Optional[float] = None # kNm; 4.2.5 with the co-existing shear, for the cross-section check
    Mcy: Optional[float] = None # kNm
    Mb: Optional[float] = None # kNm; 4.3
    Mrx: Optional[float] = None # kNm; I.2
    Mry: Optional[float] = None # kNm; I.2
    Max: Optional[float] = None # kNm; I.1
    May: Optional[float] = None # kNm; I.1
    Mab: Optional[float] = None # kNm; I.1
    mx: float = 1.0 # Table 26
    my: float = 1.0 # Table 26
    myx: float = 1.0 # Table 26
    mLT: float = 1.0 # Table 18
    utilisations: dict[str, float] # every check made
    governing: str
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_tension_and_bending(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Ft_kN: float = 0.0,
    Mx_kNm: float = 0.0,
    My_kNm: float = 0.0,
    Fv_x_kN: float = 0.0,
    Fv_y_kN: float = 0.0,
    An_cm2: Optional[float] = None,
    elements: Optional[Sequence[tuple[float, float]]] = None,
    LE_LT_mm: Optional[float] = None,
    mLT: float = 1.0,
    section_class: Optional[SectionClassInput] = None,
    use_Seff: bool = True,
    simple_span: bool = True,
    welded: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CombinedResult:
    """BS 5950-1:2000 4.8.2: Tension members with moments.

    4.8.2.2: Ft/Pt + Mx/Mcx + My/Mcy <= 1. 4.8.2.3, for class 1 and 2 with reduced moduli (I.2): Mx <= Mrx and My <= Mry,
    or (Mx/Mrx)^z1 + (My/Mry)^z2 <= 1 with both moments; the smaller of the two is the cross-section result, as 4.8.2.3
    is an alternative. Lateral-torsional buckling is checked under the moment alone (4.8.2.1) where LE_LT_mm is given.

    Args:
        section: UK section; classified in bending, as tension relieves the compression zone
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Ft_kN: Axial tension at the critical location (kN)
        Mx_kNm, My_kNm: Moments at the critical location (kNm)
        Fv_x_kN, Fv_y_kN: Co-existing shear parallel to the web (with Mx) and to the flanges (with My) (kN)
        An_cm2, elements: Net area, see check_tension()
        LE_LT_mm: Effective length for lateral-torsional buckling (mm)
        mLT: Equivalent uniform moment factor, Table 18
        section_class: Class to use instead of classifying
        use_Seff, simple_span, welded: See check_bending()
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    Ft, Mx, My = abs(Ft_kN), abs(Mx_kNm), abs(My_kNm)
    tension: TensionResult = check_tension(section, py, steel_grade, Ft or None, An_cm2, elements, section_type=section_type, properties=properties)
    bend_x: Optional[MomentCapacityResult] = check_bending(section, py, steel_grade, "x", Mx, Fv_x_kN, None, section_class, use_Seff, simple_span, welded, section_type=section_type, properties=properties) if Mx else None
    bend_y: Optional[MomentCapacityResult] = check_bending(section, py, steel_grade, "y", My, Fv_y_kN, None, section_class, use_Seff, simple_span, welded, section_type=section_type, properties=properties) if My else None
    M_cx: Optional[float] = bend_x.Mc if bend_x else None
    M_cy: Optional[float] = bend_y.Mc if bend_y else None
    cls: Optional[SectionClass] = _worst(bend_x.section_class if bend_x else None, bend_y.section_class if bend_y else None)
    simplified: float = compute_utilisation(Ft, tension.Pt) + (compute_utilisation(Mx, M_cx) if M_cx else 0.0) + (compute_utilisation(My, M_cy) if M_cy else 0.0)
    checks: dict[str, float] = {"cross-section (4.8.2.2)": simplified}
    method: str = "4.8.2.2"
    M_rx, M_ry = None, None
    if cls is not None:
        exact = _exact_cross_section(family, cls, data, py, Ft, Mx, My, M_cx or math.inf, M_cy or math.inf)
        if exact is not None:
            checks["cross-section (4.8.2.3)"] = exact[0]
            M_rx, M_ry = exact[1] if Mx else None, exact[2] if My else None
            if exact[0] < simplified:
                method = "4.8.2.3"
    cross: float = min(value for key, value in checks.items() if key.startswith("cross-section"))
    governing_checks: dict[str, float] = {f"cross-section ({method})": cross}
    M_b: Optional[float] = None
    if LE_LT_mm is not None and Mx:
        ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(
            section, py, steel_grade, LE_LT_mm, Mx, mLT, section_class=section_class, use_Seff=use_Seff, simple_span=simple_span, welded=welded, section_type=section_type, properties=properties,
        )
        M_b = ltb.Mb
        checks["lateral-torsional (4.8.2.1)"] = governing_checks["lateral-torsional (4.8.2.1)"] = compute_utilisation(mLT * Mx, M_b)
    governing: str = _governing(governing_checks)
    return CombinedResult(
        method=method,
        section_class=cls,
        py=py,
        Ft=Ft,
        Mx=Mx,
        My=My,
        Pt=tension.Pt,
        Mcx=M_cx,
        Mcy=M_cy,
        Mb=M_b,
        Mrx=M_rx,
        Mry=M_ry,
        mLT=mLT,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(governing_checks[governing], "4.8.2", f"Tension members with moments: {governing}"),
        reference=_reference("4.8.2", title="Tension members with moments"),
    )


def _stocky_capacity(slenderness: float, eps: float, M_r: float, M_o: float) -> float:
    """I.1: Max or May, Mr for λ <= 17.15ε, Mo for λ >= 85.8ε, linear in λ between."""
    if slenderness <= 17.15 * eps:
        return M_r
    if slenderness >= 85.8 * eps:
        return M_o
    return M_o + (85.8 * eps - slenderness) / (68.65 * eps) * (M_r - M_o)


def check_compression_and_bending(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fc_kN: float = 0.0,
    Mx_kNm: float = 0.0,
    My_kNm: float = 0.0,
    Fv_x_kN: float = 0.0,
    Fv_y_kN: float = 0.0,
    LEx_mm: Optional[float] = None,
    LEy_mm: Optional[float] = None,
    LE_LT_mm: Optional[float] = None,
    MLT_kNm: Optional[float] = None,
    mx: float = 1.0,
    my: float = 1.0,
    myx: float = 1.0,
    mLT: float = 1.0,
    method: InteractionMethod = "exact",
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    use_Seff: bool = True,
    simple_span: bool = True,
    class_4_method: Class4Method = "effective",
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CombinedResult:
    """BS 5950-1:2000 4.8.3: Compression members with moments, and 4.9 biaxial moments (Fc = 0).

    Cross-section capacity (4.8.3.2): Fc/(Ag py) + Mx/Mcx + My/Mcy <= 1, with Aeff for class 4; for class 1 and 2 the
    4.8.2.3 alternative with the reduced moments of I.2 is used where it is more favourable.

    Member buckling resistance (4.8.3.3), by `method`:
        - "simplified" (4.8.3.3.1): Fc/Pc + mxMx/(pyZx) + myMy/(pyZy) <= 1 and Fc/Pcy + mLT MLT/Mb + myMy/(pyZy) <= 1
        - "exact": 4.8.3.3.2 for I- and H-sections with equal flanges, 4.8.3.3.3 for CHS and RHS, with in-plane,
          out-of-plane, lateral-torsional and interactive buckling; other shapes fall back to the simplified method
        - "stocky": I.1, for doubly symmetric class 1 and 2 cross-sections, with Max, May and Mab

    The classification follows the moment and axial force together (4.8.1): webs use r1 and r2 from Fc (3.5.5); CHS are
    classified for compression and for bending separately. The moment capacities of the member checks ignore shear
    (4.8.1), those of the cross-section check include it. Without LE_LT_mm the segment is taken as fully restrained
    (4.2.2), Mb = Mcx.

    Args:
        section: UK section
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fc_kN: Axial compression (kN), >= 0
        Mx_kNm, My_kNm: Maximum moments about the major and minor axes (kNm)
        Fv_x_kN, Fv_y_kN: Co-existing shear parallel to the web and to the flanges (kN), for the cross-section check
        LEx_mm, LEy_mm: Effective lengths for flexural buckling (mm); needed with axial force
        LE_LT_mm: Effective length for lateral-torsional buckling (mm)
        MLT_kNm: Maximum major axis moment in the segment governing Mb (kNm); defaults to Mx
        mx, my, myx: Equivalent uniform moment factors, Table 26; see equivalent_uniform_moment_factor_m()
        mLT: Equivalent uniform moment factor, Table 18
        method: "simplified", "exact" or "stocky"
        section_class: Class to use instead of classifying
        welded: Welded section
        use_Seff, simple_span: See check_bending()
        class_4_method: "effective" or "reduced_strength" (3.6.5)
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if Fc_kN < 0.0:
        raise ValueError("Fc_kN is compression (>= 0); use check_tension_and_bending() for tension.")
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    py: float = _design_strength(py_mpa, steel_grade, data)
    eps: float = epsilon(py)
    Fc, Mx, My = Fc_kN, abs(Mx_kNm), abs(My_kNm)
    M_LT: float = abs(MLT_kNm) if MLT_kNm is not None else Mx
    axial: Optional[float] = Fc if Fc > 0.0 else None
    notes: list[str] = []
    common: dict[str, Any] = {"section": section, "py_mpa": py, "steel_grade": steel_grade, "section_type": section_type, "properties": properties}
    bending: dict[str, Any] = {"use_Seff": use_Seff, "simple_span": simple_span, "welded": welded, "class_4_method": class_4_method}

    # 4.7 Compression resistance
    compression: Optional[CompressionResult] = None
    P_cx, P_cy = math.inf, math.inf
    if Fc > 0.0:
        if LEx_mm is None or LEy_mm is None:
            raise ValueError("LEx_mm and LEy_mm are needed for the member buckling checks under axial force.")
        compression = check_compression(Fc_kN=Fc, LEx_mm=LEx_mm, LEy_mm=LEy_mm, section_class=section_class, welded=welded, class_4_method=class_4_method, E=E, **common)
        P_cx, P_cy = compression.Pcx or math.inf, compression.Pcy or math.inf
    P_c: float = min(P_cx, P_cy)

    # 4.2.5 Moment capacities: with shear for the cross-section, without for the member (4.8.1)
    moment_x: Optional[MomentCapacityResult] = check_bending(axis="x", Fv_kN=Fv_x_kN, Fc_kN=axial, section_class=section_class, **bending, **common) if (Mx or M_LT) else None
    moment_y: Optional[MomentCapacityResult] = check_bending(axis="y", Fv_kN=Fv_y_kN, Fc_kN=axial, section_class=section_class, **bending, **common) if My else None
    member_x: Optional[MomentCapacityResult] = check_bending(axis="x", Fc_kN=axial, section_class=section_class, **bending, **common) if (Mx or M_LT) else None
    member_y: Optional[MomentCapacityResult] = check_bending(axis="y", Fc_kN=axial, section_class=section_class, **bending, **common) if My else None
    # 4.8.1: the class under the moments with the axial force; the axial compression class matters only when slender, since
    # ... Table 11 gives webs in axial compression no class 1 or 2 limit
    cls: SectionClass = _worst(moment_x.section_class if moment_x else None, moment_y.section_class if moment_y else None) or (
        compression.section_class if compression else SectionClass.CLASS_1
    )
    if compression is not None and compression.section_class == SectionClass.CLASS_4:
        cls = SectionClass.CLASS_4

    # 4.3 Buckling resistance moment
    M_b: Optional[float] = None
    lambda_LT: float = 0.0
    ltb_needed: bool = False
    if member_x is not None:
        M_b = member_x.Mc
        if LE_LT_mm is not None and family != "CHS":
            ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(
                LE_mm=LE_LT_mm, Mx_kNm=M_LT, mLT=mLT, section_class=section_class, Fc_kN=axial, E=E, **bending, **common,
            )
            M_b, ltb_needed, lambda_LT = ltb.Mb, ltb.susceptible, ltb.lambda_LT or 0.0
        elif family not in ("CHS", "RHS"):
            notes.append("No LE_LT_mm: the segment is taken as fully restrained against lateral-torsional buckling (4.2.2), Mb = Mcx.")

    # 4.8.3.2 Cross-section capacity
    M_cx: Optional[float] = moment_x.Mc if moment_x else None
    M_cy: Optional[float] = moment_y.Mc if moment_y else None
    checks: dict[str, float] = {}
    A_axial: float = compression.A if (compression and cls == SectionClass.CLASS_4) else _get(data, "A")
    py_axial: float = compression.py if compression else py
    cross: float = Fc / (A_axial * py_axial / 10.0) + (compute_utilisation(Mx, M_cx) if Mx and M_cx else 0.0) + (compute_utilisation(My, M_cy) if My and M_cy else 0.0)
    cross_clause: str = "4.8.3.2c" if cls == SectionClass.CLASS_4 else "4.8.3.2a"
    M_rx, M_ry = None, None
    exact_cross = _exact_cross_section(family, cls, data, py, Fc, Mx, My, M_cx or math.inf, M_cy or math.inf)
    if exact_cross is not None:
        M_rx, M_ry = exact_cross[1], exact_cross[2]
        if exact_cross[0] < cross:
            cross, cross_clause = exact_cross[0], "4.8.3.2b"
    checks[f"cross-section ({cross_clause})"] = cross

    # 4.8.3.3 Member buckling resistance
    r_x: float = Fc / P_cx
    r_y: float = Fc / P_cy
    M_cx_m: float = member_x.Mc if member_x else math.inf
    M_cy_m: float = member_y.Mc if member_y else math.inf
    Mb_value: float = M_b if M_b else math.inf
    method_used: str = method
    if method == "exact" and family not in ("I", "RHS", "CHS"):
        method_used = "simplified"
        notes.append("4.8.3.3.2 and 4.8.3.3.3 are for I, H, CHS and RHS; the simplified method (4.8.3.3.1) is used.")
    if method == "stocky" and (family not in ("I", "RHS", "CHS") or not _is_plastic(cls)):
        raise ValueError("I.1 is for doubly symmetric class 1 plastic or class 2 compact cross-sections (I, H, CHS, RHS).")

    member: dict[str, float] = {}
    M_ax, M_ay, M_ab = None, None, None
    if Fc > 0.0:
        member["axial (4.7.4)"] = Fc / P_c
    if method_used == "simplified":
        # 4.8.3.3.1; pyZ with Zeff for class 4, or pyr Z for 3.6.5
        pyZx: float = (member_x.py * (member_x.W if member_x.modulus == "Zeff" else member_x.Z) / 1e3) if member_x else math.inf
        pyZy: float = (member_y.py * (member_y.W if member_y.modulus == "Zeff" else member_y.Z) / 1e3) if member_y else math.inf
        member["flexural (4.8.3.3.1)"] = Fc / P_c + mx * Mx / pyZx + my * My / pyZy
        member["lateral-torsional (4.8.3.3.1)"] = r_y + mLT * M_LT / Mb_value + my * My / pyZy
    elif method_used == "exact":
        k_y: float = 1.0 if family == "I" else 0.5 # (1 + Fc/Pcy) for I and H, (1 + 0.5Fc/Pcy) for hollow sections
        clause: str = "4.8.3.3.2" if family == "I" else "4.8.3.3.3"
        out_of_plane: float = mLT * M_LT / Mb_value if (family == "I" or ltb_needed) else 0.5 * mLT * M_LT / M_cx_m
        interactive_x: float = mx * Mx * (1.0 + 0.5 * r_x) / (M_cx_m * (1.0 - r_x)) if r_x < 1.0 else math.inf
        interactive_y: float = my * My * (1.0 + k_y * r_y) / (M_cy_m * (1.0 - r_y)) if r_y < 1.0 else math.inf
        if (Mx or M_LT) and not My:
            member[f"major axis in-plane ({clause}a)"] = r_x + mx * Mx / M_cx_m * (1.0 + 0.5 * r_x)
            member[f"out-of-plane ({clause}a)"] = r_y + out_of_plane
        elif My and not (Mx or M_LT):
            member[f"minor axis in-plane ({clause}b)"] = r_y + my * My / M_cy_m * (1.0 + k_y * r_y)
            member[f"out-of-plane ({clause}b)"] = r_x + 0.5 * myx * My / M_cy_m
        elif My:
            member[f"major axis ({clause}c)"] = r_x + mx * Mx / M_cx_m * (1.0 + 0.5 * r_x) + 0.5 * myx * My / M_cy_m
            member[f"lateral-torsional ({clause}c)"] = r_y + out_of_plane + my * My / M_cy_m * (1.0 + k_y * r_y)
            member[f"interactive ({clause}c)"] = interactive_x + interactive_y
    else:
        # I.1 Stocky members
        moduli: Optional[tuple[float, float]] = _reduced_plastic_moduli(family, data, Fc / (_get(data, "A") * py / 10.0))
        assert moduli is not None
        M_rx = min(py * moduli[0] / 1e3, M_cx_m)
        M_ry = min(py * moduli[1] / 1e3, M_cy_m)
        k_y = 1.0 if family == "I" else 0.5
        lambda_x: float = next((mode.slenderness for mode in compression.modes if mode.axis == "x"), 0.0) if compression else 0.0
        lambda_y: float = next((mode.slenderness for mode in compression.modes if mode.axis == "y"), 0.0) if compression else 0.0
        if Mx or M_LT:
            M_ox: float = M_cx_m * (1.0 - r_x) / (1.0 + 0.5 * r_x)
            M_ax = _stocky_capacity(lambda_x, eps, M_rx, M_ox)
            r_b: float = mLT * M_LT / Mb_value
            r_c: float = r_y
            M_xy: float = M_cx_m * math.sqrt(max(1.0 - r_c, 0.0)) if family == "I" else 2.0 * M_cx_m * (1.0 - r_c)
            M_ob: float = Mb_value * (1.0 - r_c) if M_b else M_rx
            if r_b + r_c > 0.0:
                lambda_r: float = (r_b * lambda_LT + r_c * lambda_y) / (r_b + r_c)
                lambda_r0: float = 17.15 * eps * (2.0 * r_b + r_c) / (r_b + r_c)
                if lambda_r <= lambda_r0:
                    M_ab = min(M_rx, M_xy)
                elif lambda_r < 85.8 * eps:
                    M_ab = min(M_ob + (85.8 * eps - lambda_r) / (85.8 * eps - lambda_r0) * (M_rx - M_ob), M_xy)
                else:
                    M_ab = M_ob
            else:
                M_ab = min(M_rx, M_xy)
        if My:
            M_oy: float = M_cy_m * (1.0 - r_y) / (1.0 + k_y * r_y)
            M_ay = _stocky_capacity(lambda_y, eps, M_ry, M_oy)
        lateral_y: float = M_cy_m * (1.0 - r_x) # Mcy(1 - Fc/Pcx)
        if (Mx or M_LT) and not My:
            member["major axis in-plane (I.1a)"] = compute_utilisation(mx * Mx, M_ax or 0.0)
            member["out-of-plane (I.1a)"] = compute_utilisation(mLT * M_LT, M_ab or 0.0)
        elif My and not (Mx or M_LT):
            member["minor axis in-plane (I.1b)"] = compute_utilisation(my * My, M_ay or 0.0)
            member["out-of-plane (I.1b)"] = compute_utilisation(myx * My, 2.0 * lateral_y)
        elif My:
            member["major axis (I.1c)"] = compute_utilisation(mx * Mx, M_ax or 0.0) + compute_utilisation(0.5 * myx * My, lateral_y)
            member["lateral-torsional (I.1c)"] = compute_utilisation(mLT * M_LT, M_ab or 0.0) + compute_utilisation(my * My, M_ay or 0.0)
            member["interactive (I.1c)"] = compute_utilisation(mx * Mx, M_ax or 0.0) + compute_utilisation(my * My, M_ay or 0.0)
    checks.update(member)
    governing: str = _governing(checks)
    return CombinedResult(
        method=method_used,
        section_class=cls,
        py=py,
        Fc=Fc,
        Mx=Mx,
        My=My,
        MLT=M_LT if (Mx or M_LT) else None,
        Pc=P_c if Fc > 0.0 else None,
        Pcx=P_cx if Fc > 0.0 else None,
        Pcy=P_cy if Fc > 0.0 else None,
        Mcx=M_cx,
        Mcy=M_cy,
        Mb=M_b,
        Mrx=M_rx,
        Mry=M_ry,
        Max=M_ax,
        May=M_ay,
        Mab=M_ab,
        mx=mx,
        my=my,
        myx=myx,
        mLT=mLT,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(checks[governing], "4.8.3", f"Compression members with moments: {governing}"),
        reference=_reference("4.8.3" if Fc > 0.0 else "4.9", title="Members with combined moment and axial force"),
        metadata={"notes": notes} if notes else {},
    )


def check_single_angle_compression_and_bending(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    Fc_kN: float = 0.0,
    Mx_kNm: float = 0.0,
    My_kNm: float = 0.0,
    LEx_mm: float = 0.0,
    LEy_mm: float = 0.0,
    LEv_mm: Optional[float] = None,
    mLTx: float = 1.0,
    mLTy: float = 1.0,
    heel_in_compression_x: bool = True,
    heel_in_compression_y: bool = True,
    section_class: Optional[SectionClassInput] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CombinedResult:
    """BS 5950-1:2000 I.4.3: Simplified method for an equal angle under axial compression and moments about x-x and y-y.

    Fc/Pc + mLTx Mx/Mbx + mLTy My/Mby <= 1, with mLTx, mLTy >= 0.6, Pc for buckling about any axis including v-v, and Mbx
    and Mby from 4.3.8.3 using LEy with Zx and LEx with Zy.

    Args:
        section: L_EQUAL
        py_mpa: Design strength (N/mm²); defaults to Table 9 for `steel_grade`
        steel_grade: "S275", "S355" or "S460"
        Fc_kN: Axial compression (kN)
        Mx_kNm, My_kNm: Maximum moments about x-x and y-y (kNm)
        LEx_mm, LEy_mm: Lengths between points restrained against buckling about x-x and y-y (mm)
        LEv_mm: Effective length about v-v (mm); defaults to the smaller of LEx and LEy
        mLTx, mLTy: Table 18 factors for the moments about x-x over LEy and about y-y over LEx
        heel_in_compression_x, heel_in_compression_y: For Mbx and Mby (4.3.8.3)
        section_class: Class to use instead of classifying
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    if _family(section_type) != "angle" or data.get("leg_long") != data.get("leg_short"):
        raise ValueError("I.4.3 is for single equal angles; use the basic method (I.4.2) for unequal angles.")
    py: float = _design_strength(py_mpa, steel_grade, data)
    L_v: float = LEv_mm if LEv_mm is not None else min(_require_positive(LEx_mm, "LEx_mm"), _require_positive(LEy_mm, "LEy_mm"))
    compression: CompressionResult = check_compression(section, py, steel_grade, Fc_kN or None, LEx_mm, LEy_mm, L_v, section_class=section_class, section_type=section_type, properties=properties)
    r_v: float = _get(data, "rv")
    M_bx: float = angle_buckling_resistance_moment(compression.py, _get(data, "Zx"), LEy_mm, r_v, heel_in_compression_x)
    M_by: float = angle_buckling_resistance_moment(compression.py, _get(data, "Zy"), LEx_mm, r_v, heel_in_compression_y)
    m_x, m_y = max(mLTx, 0.6), max(mLTy, 0.6)
    utilisation: float = compute_utilisation(Fc_kN, compression.Pc) + compute_utilisation(m_x * abs(Mx_kNm), M_bx) + compute_utilisation(m_y * abs(My_kNm), M_by)
    checks: dict[str, float] = {"simplified (I.4.3)": utilisation}
    return CombinedResult(
        method="I.4.3",
        section_class=compression.section_class,
        py=compression.py,
        Fc=Fc_kN,
        Mx=abs(Mx_kNm),
        My=abs(My_kNm),
        Pc=compression.Pc,
        mLT=m_x,
        utilisations=checks,
        governing="simplified (I.4.3)",
        utilisation=_ratio_check(utilisation, "I.4.3", "Single angle members"),
        reference=_reference("I.4.3", title="Single angle members, simplified method"),
        metadata={"Mbx": M_bx, "Mby": M_by, "mLTy": m_y},
    )


# --- Annexes B.3, C.3 and I.5: internal moments ---
def strut_action_moment(f_c: float, p_c: float, py: float, S: float) -> float:
    """BS 5950-1:2000 C.3: Maximum strut action moment Mmax = (py/pc - 1)fc S (kNm), midway between the points of
    inflexion; at Lz from one, Ms = Mmax sin(πLz/LE). fc and pc in N/mm², S (plastic modulus about the buckling axis) cm³."""
    return (py / _require_positive(p_c, "p_c") - 1.0) * f_c * S / 1e3


def lateral_torsional_internal_moment(py: float, p_b: float, M_cx: float, M_cy: float, M_x: float, m_LT: float = 1.0) -> float:
    """BS 5950-1:2000 B.3.1: Additional minor axis moment from lateral-torsional buckling, My,max = (py/pb - 1)(Mcy/Mcx)mLT Mx
    (kNm), in the units of the moments."""
    return (py / _require_positive(p_b, "p_b") - 1.0) * (M_cy / _require_positive(M_cx, "M_cx")) * m_LT * M_x


def amplified_moment(M: float, f_c: float, slenderness: float, m: float = 1.0, E: float = E_STEEL) -> float:
    """BS 5950-1:2000 I.5.1: Additional moment from the amplification of an applied moment, Madd,max = mM/(pE/fc - 1) with
    pE = π²E/λ², in the units of M."""
    if f_c <= 0.0:
        return 0.0
    p_E: float = math.pi**2 * E / _require_positive(slenderness, "slenderness") ** 2
    if p_E <= f_c:
        raise ValueError("fc reaches the Euler stress pE; the member is unstable.")
    return m * M / (p_E / f_c - 1.0)


def internal_moment_at(M_max: float, L_z: float, L_E: float) -> float:
    """BS 5950-1:2000 B.3.1, C.3 and I.5.1: M = Mmax sin(180 Lz/LE), at Lz from a point of inflexion (Lz, LE in mm)."""
    return M_max * math.sin(math.pi * L_z / _require_positive(L_E, "L_E"))


if __name__ == "__main__":
    from steelsnakes.UK import UB, UC

    beam = UB("457x191x67")
    print(check_bending(beam, steel_grade="S275", M_kNm=300.0, Fv_kN=250.0).model_dump())
    print(check_lateral_torsional_buckling(beam, steel_grade="S275", LE_mm=4000.0, Mx_kNm=200.0, mLT=0.925).model_dump())
    column = UC("254x254x73")
    print(check_compression(column, steel_grade="S275", Fc_kN=1200.0, LEx_mm=5000.0, LEy_mm=5000.0).model_dump())
    print(check_compression_and_bending(column, steel_grade="S275", Fc_kN=1000.0, Mx_kNm=60.0, My_kNm=10.0, LEx_mm=5000.0, LEy_mm=5000.0, LE_LT_mm=5000.0).model_dump())
    print("🐬")
