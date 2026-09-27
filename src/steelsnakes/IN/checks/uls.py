# IS 800:2025 (DRAFT): ULTIMATE LIMIT STATES
# Draft Indian Standard General Construction in Steel, the fourth revision of IS 800: CED 07 (27869) WC, April 2025
# 9.2.4 material properties; 10.9 Table 3 maximum slenderness; 12.3.3 and 12.4.1 Tables 4 and 5 partial safety factors
# 13 Tension members: 13.2 yielding, 13.3 rupture (plates, threaded rods, angles and other sections), 13.4 block shear
# 14 Compression members: 14.1 Tables 7 to 10, flexural, torsional and torsional flexural buckling; 14.2 Table 11
# ... effective lengths; 14.3.2 effective sectional area; 14.5.1 single angle struts (Table 12)
# 15 Bending: 15.2.1 laterally supported beams, 15.2.2 lateral torsional buckling (Tables 13 and 14), 15.3 Tables 15 and
# ... 16 effective lengths, 15.4 shear with the simple post-critical and tension field methods
# 16 Combined forces: 16.2 shear and bending, 16.3.1 section strength (Table 17), 16.3.2 member strength (Table 18)
# Annex D: effective length factor of columns in frames; Annex E: elastic critical moment (Table 42)
# NOTE: units follow IS 800 and the IS 808 tables: forces kN, moments kNm, stresses N/mm² [MPa], lengths mm; section
# ... properties as tabulated: area cm², I and I_t cm⁴, Z cm³, I_w cm⁶ (10⁶ mm⁶), r mm. Values passed through
# ... `properties` use the same units, with the IN keys (D, B, t, T, R1, area, I_zz, Z_zz, Z_pz, I_t, I_w, ...) or the
# ... common aliases (h, b, tw, tf, A, Iz, Zez, Zpz, It, Iw).
# NOTE: IS 800 axes (8): z-z is the major axis, parallel to the flanges, and y-y the minor axis; angles also have the
# ... principal axes u-u and v-v. For I-sections and channels the larger of I_zz and I_yy is taken as z-z.
# NOTE: fy defaults to Table 1 (IS 2062) for `steel_grade` and the thickest element, as in the classification.
# NOTE: where the draft misprints, the checks follow the draft's own tables or the text it restates, and say so where it
# ... happens, e.g. 14.1.2.1 prints χ = 1/(φ + (φ² + λ²)^0.5) but Table 8 follows φ² - λ².
from __future__ import annotations

import math
import re
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.IN.checks.classification import (
    _CLASS_RANK,
    ANGLE_SECTION_TYPES,
    CHANNEL_SECTION_TYPES,
    CHS_SECTION_TYPES,
    COLD_FORMED_SECTION_TYPES,
    EDITION,
    RHS_SECTION_TYPES,
    ROLLED_I_SECTION_TYPES,
    ClassificationResult,
    ElementKind,
    StressPattern,
    classify_section_from_dict,
    effective_width,
    epsilon,
    ultimate_stress,
    yield_stress,
)

IS_800 = DesignCode.IS_800

# 9.2.4.1 Physical properties of structural steel
E_STEEL = 2.0e5 # N/mm² [MPa]; modulus of elasticity
G_STEEL = 0.769e5 # N/mm² [MPa]; modulus of rigidity
POISSON_RATIO = 0.3
UNIT_MASS = 7_850.0 # kg/m³
THERMAL_EXPANSION = 12e-6 # per °C

# Table 5: Partial safety factors for materials γm
GAMMA_M0 = 1.10 # i) resistance governed by yielding, and ii) resistance of member to buckling
GAMMA_M1 = 1.25 # iii) resistance governed by ultimate stress
CONNECTION_SAFETY_FACTORS: dict[str, tuple[float, float]] = { # iv) resistance of connections, (shop, field)
    "friction_bolts": (1.25, 1.25), # γmf
    "bearing_bolts": (1.25, 1.25), # γmb
    "rivets": (1.25, 1.25), # γmr
    "welds": (1.25, 1.50), # γmw
}

# Table 4: Partial safety factors for loads γf, by combination and limit state; "IL_leading" is the imposed load causing
# ... the higher load effects (note 1); CL, crane loads, are imposed loads (10.6.3)
LOAD_FACTORS: dict[str, dict[str, dict[str, float]]] = {
    "DL+IL+CL": { # i)
        "strength": {"DL": 1.5, "IL_leading": 1.5, "IL_accompanying": 1.05},
        "serviceability": {"DL": 1.0, "IL_leading": 1.0, "IL_accompanying": 1.0},
    },
    "DL+IL+CL+WL/EL": { # ii) first line
        "strength": {"DL": 1.2, "IL_leading": 1.2, "IL_accompanying": 1.05, "WL/EL": 0.6},
        "serviceability": {"DL": 1.0, "IL_leading": 0.8, "IL_accompanying": 0.8, "WL/EL": 0.8},
    },
    "DL+IL+CL+WL/EL (WL/EL leading)": { # ii) second line
        "strength": {"DL": 1.2, "IL_leading": 1.2, "IL_accompanying": 0.53, "WL/EL": 1.2},
        "serviceability": {"DL": 1.0, "IL_leading": 0.8, "IL_accompanying": 0.8, "WL/EL": 0.8},
    },
    "DL+WL/EL": { # iii)
        "strength": {"DL": 1.5, "WL/EL": 1.5},
        "serviceability": {"DL": 1.0, "WL/EL": 1.0},
    },
    "DL+ER": {"strength": {"DL": 1.2, "ER": 1.2}}, # iv)
    "DL+IL+FL": {"strength": {"DL": 1.0, "IL_leading": 1.0, "FL": 1.0}}, # V) IL 1.0 for storage, else 0.5 (note 3)
    "DL+IL+AL": {"strength": {"DL": 1.0, "IL_leading": 0.35, "IL_accompanying": 0.35, "AL": 1.0}}, # v)
}
DEAD_LOAD_STABILISING = 0.9 # Table 4 note 2; 12.5.1.1 c): dead load contributing to stability or reducing stresses
IMPOSED_LOAD_FIRE_OTHER = 0.5 # Table 4 note 3: imposed load in fire, other than storage

# Table 3: Maximum values of effective slenderness ratios KL/r
MAXIMUM_SLENDERNESS: dict[str, float] = {
    "compression": 180.0, # i) compressive loads from dead and imposed loads
    "tension_reversal": 180.0, # ii) tension member with reversal of stress from loads other than wind or seismic
    "compression_wind_earthquake": 250.0, # iii) compression only from combinations with wind/earthquake effects
    "compression_flange": 300.0, # iv) compression flange of a beam against lateral torsional buckling
    "tie_reversal_wind_earthquake": 350.0, # v) tie in a roof truss or bracing, reversal from wind or earthquake
    "tension": 400.0, # vi) members always under tension (other than pre-tensioned); note 1): no limit if sag is avoided
}

# Table 7: Imperfection factor α
IMPERFECTION_FACTORS: dict[str, float] = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}

# Table 10: Buckling class of cross sections, as ((z-z, y-y) for fy <= 420 MPa, (z-z, y-y) for fy > 420 MPa)
BUCKLING_CLASSES: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "rolled_I_tf_40": (("a", "b"), ("a0", "a")), # rolled I, h/bf > 1.2, tf <= 40 mm
    "rolled_I_tf_100": (("b", "c"), ("a", "b")), # rolled I, h/bf > 1.2, 40 < tf <= 100 mm
    "rolled_H_tf_100": (("b", "c"), ("a", "b")), # rolled I, h/bf <= 1.2, tf <= 100 mm
    "rolled_H_thick": (("d", "d"), ("c", "c")), # rolled I, h/bf <= 1.2, tf > 100 mm
    "welded_I_tf_40": (("b", "c"), ("b", "c")), # welded I, tf <= 40 mm
    "welded_I_thick": (("c", "d"), ("c", "d")), # welded I, tf > 40 mm
    "hot_rolled_hollow": (("a", "a"), ("a0", "a0")),
    "cold_formed_hollow": (("b", "b"), ("c", "c")),
    "welded_box": (("b", "b"), ("b", "b")), # generally
    "welded_box_thick_welds": (("c", "c"), ("c", "c")), # thick welds, b/tf < 30 and h/tw < 30
    "channel_tee_solid": (("c", "c"), ("c", "c")), # channel, T and solid sections
    "built_up": (("c", "c"), ("c", "c")), # built-up members
    "rolled_angle": (("b", "b"), ("a", "a")),
    "welded_angle": (("c", "c"), ("c", "c")), # t <= 40 mm
}

# Table 11: Effective length KL of prismatic compression members, as a multiple of L; (translation, rotation) at one end,
# ... then the other
COMPRESSION_EFFECTIVE_LENGTHS: dict[str, float] = {
    "fixed_free": 2.0, # restrained, restrained; free, free
    "pinned_sway_fixed": 2.0, # restrained, free; free, restrained
    "pinned_pinned": 1.0, # restrained, free; restrained, free
    "fixed_sway_fixed": 1.2, # restrained, restrained; free, restrained
    "fixed_pinned": 0.8, # restrained, restrained; restrained, free
    "fixed_fixed": 0.65, # restrained, restrained; restrained, restrained
}

# Table 12: Constants k1, k2 and k3 of single angle struts loaded through one leg, by end connection and gusset fixity
ANGLE_STRUT_CONSTANTS: dict[tuple[str, str], tuple[float, float, float]] = {
    ("welded", "fixed"): (0.798, 0.563, -2.072), # i) fully welded or connected with two or more bolts
    ("welded", "hinged"): (0.401, 0.420, -1.040),
    ("single_bolt", "fixed"): (0.418, 0.547, -1.400), # ii) single bolt
    ("single_bolt", "hinged"): (0.374, 0.415, -2.072),
}

# Table 15: Effective length LLT for simply supported beams, as (normal, destabilizing) multiples of L, plus 2D where
# ... flagged; the ends are torsionally restrained, fully in rows i) to v)
BEAM_EFFECTIVE_LENGTHS: dict[str, tuple[float, float, bool]] = {
    "both_flanges_fully_restrained": (0.70, 0.85, False), # i) warping restraint of both flanges fully
    "compression_flange_fully_restrained": (0.75, 0.90, False), # ii) only compression flange fully
    "both_flanges_partially_restrained": (0.80, 0.95, False), # iii) both flanges partially
    "compression_flange_partially_restrained": (0.85, 1.00, False), # iv) only compression flange partially
    "no_warping_restraint": (1.00, 1.20, False), # v) no restraint in both flanges
    "bottom_flange_connected": (1.0, 1.2, True), # vi) torsion partially restrained by bottom flange support connection
    "bottom_flange_bearing": (1.2, 1.4, True), # vii) torsion partially restrained by bottom flange bearing support
}
# Table 16: Effective length LLT for cantilevers of length L, (normal, destabilizing) multiples of L, by support a) to d)
# ... and top restraint i) free, ii) lateral restraint to top flange, iii) torsional, iv) lateral and torsional
CANTILEVER_EFFECTIVE_LENGTHS: dict[str, dict[str, tuple[float, float]]] = {
    "continuous_lateral": {"free": (3.0, 7.5), "lateral": (2.7, 7.5), "torsional": (2.4, 4.5), "lateral_torsional": (2.1, 3.6)}, # a)
    "continuous_partial_torsional": {"free": (2.0, 5.0), "lateral": (1.8, 5.0), "torsional": (1.6, 3.0), "lateral_torsional": (1.4, 2.4)}, # b)
    "continuous_lateral_torsional": {"free": (1.0, 2.5), "lateral": (0.9, 2.5), "torsional": (0.8, 1.5), "lateral_torsional": (0.7, 1.2)}, # c)
    "built_in": {"free": (0.8, 1.4), "lateral": (0.7, 1.4), "torsional": (0.6, 0.6), "lateral_torsional": (0.5, 0.5)}, # d) restrained laterally, torsionally and against rotation on plan
}

# Table 42: Constants c1, c2 and c3 of Annex E, by effective length factor K
# ... end moments M and ψM, ψ: {K: (c1, c3)}; c2 is not applicable. NOTE: ψ = -3/4 repeats the ψ = -1/2 values of c1 for
# ... K = 0.7 and 0.5, as printed (and as in IS 800:2007)
ANNEX_E_END_MOMENT_CONSTANTS: dict[float, dict[float, tuple[float, float]]] = {
    1.0: {1.0: (1.000, 1.000), 0.7: (1.000, 1.113), 0.5: (1.000, 1.144)},
    0.75: {1.0: (1.141, 0.998), 0.7: (1.270, 1.565), 0.5: (1.305, 2.283)},
    0.5: {1.0: (1.323, 0.992), 0.7: (1.473, 1.556), 0.5: (1.514, 2.271)},
    0.25: {1.0: (1.563, 0.977), 0.7: (1.739, 1.531), 0.5: (1.788, 2.235)},
    0.0: {1.0: (1.879, 0.939), 0.7: (2.092, 1.473), 0.5: (2.150, 2.150)},
    -0.25: {1.0: (2.281, 0.855), 0.7: (2.538, 1.340), 0.5: (2.609, 1.957)},
    -0.5: {1.0: (2.704, 0.676), 0.7: (3.009, 1.059), 0.5: (3.093, 1.546)},
    -0.75: {1.0: (2.927, 0.366), 0.7: (3.009, 0.575), 0.5: (3.093, 0.837)},
    -1.0: {1.0: (2.752, 0.000), 0.7: (3.063, 0.000), 0.5: (3.149, 0.000)},
}
# ... transverse loading: {K: (c1, c2, c3)}
ANNEX_E_TRANSVERSE_LOAD_CONSTANTS: dict[str, dict[float, tuple[float, float, float]]] = {
    "udl_simply_supported": {1.0: (1.132, 0.459, 0.525), 0.5: (0.972, 0.304, 0.980)},
    "udl_fixed_ends": {1.0: (1.285, 1.562, 0.753), 0.5: (0.712, 0.652, 1.070)},
    "point_load_simply_supported": {1.0: (1.365, 0.553, 1.730), 0.5: (1.070, 0.432, 3.050)}, # at mid-span
    "point_load_fixed_ends": {1.0: (1.565, 1.267, 2.640), 0.5: (0.938, 0.715, 4.800)}, # at mid-span
    "two_point_loads": {1.0: (1.046, 0.430, 1.120), 0.5: (1.010, 0.410, 1.890)}, # at the quarter points
}

# Section-table keys, in the order tried, for each IS 800 symbol; values stay in the table units
_PROPERTY_MAP: dict[str, tuple[str, ...]] = {
    "D": ("D", "h"), # overall depth, mm
    "B": ("B", "b"), # overall width, mm
    "tw": ("tw", "t"), # web or wall thickness, mm
    "tf": ("tf", "T", "t"), # flange thickness, mm; the average thickness of tapered flanges (10.8.3 c))
    "R1": ("R1", "r1", "r"), # root radius, mm
    "d": ("d",), # depth of the web, mm
    "A": ("area", "A", "Ag"), # cm²
    "Iz": ("I_zz", "Iz", "I"), # cm⁴
    "Iy": ("I_yy", "Iy", "I"), # cm⁴
    "Iu": ("I_uu", "Iu"), # cm⁴
    "Iv": ("I_vv", "I_vy", "Iv"), # cm⁴
    "Zez": ("Z_zz", "Zez", "Ze"), # cm³
    "Zey": ("Z_yy", "Zey", "Ze"), # cm³
    "Zpz": ("Z_pz", "Zpz", "Zp"), # cm³
    "Zpy": ("Z_py", "Zpy", "Zp"), # cm³
    "rz": ("r_z", "rz"), # mm
    "ry": ("r_y", "ry"), # mm
    "ru": ("r_u", "ru"), # mm
    "rv": ("r_v", "rv"), # mm
    "It": ("I_t", "It"), # cm⁴
    "Iw": ("I_w", "Iw"), # cm⁶
}

BendingAxis = Literal["z", "y"] # z-z major, y-y minor
Loading = Literal["normal", "destabilizing"] # 15.3
Connection = Literal["bolted", "welded"]
AngleConnection = Literal["welded", "two_bolts", "single_bolt"] # Table 12: i) fully welded or two or more bolts; ii)
Fixity = Literal["fixed", "hinged"]
SectionClassInput = SectionClass | int | str


# --- Helpers ---
def _require_positive(value: Optional[float], name: str) -> float:
    if value is None or value <= 0.0:
        raise ValueError(f"{name} must be positive.")
    return float(value)


def _reference(clause: str, equation: Optional[str] = None, title: Optional[str] = None, notes: Optional[str] = EDITION) -> Reference:
    return Reference(code=IS_800, clause=clause, equation=equation, title=title, notes=notes)


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
    """Accept SectionClass.CLASS_2, 2, "2", "class 2", "CLASS_2" or the IS 800 names, e.g "compact"."""
    if isinstance(value, SectionClass):
        if value not in _CLASS_RANK:
            raise ValueError(f"IS 800 uses classes 1 to 4 (10.8.2), not {value.value}.")
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
    if section_type in ANGLE_SECTION_TYPES:
        return "angle"
    if section_type in RHS_SECTION_TYPES:
        return "RHS"
    if section_type in CHS_SECTION_TYPES:
        return "CHS"
    return "other"


def _section_data(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> tuple[Optional[SectionType], dict[str, float], dict[str, Any]]:
    """Resolve a section and/or plain properties into (section_type, IS 800 symbols in table units, raw data).

    `properties` overrides or supplements the section's own values, e.g "I_t" and "I_w" where the tables have none.
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

    family: str = _family(section_type)
    if family in ("I", "channel") and data.get("Iy", 0.0) > data.get("Iz", 0.0):
        for major, minor in (("Iz", "Iy"), ("Zez", "Zey"), ("Zpz", "Zpy"), ("rz", "ry")): # z-z is the major axis (8)
            major_value, minor_value = data.pop(major, None), data.pop(minor, None)
            if minor_value is not None:
                data[major] = minor_value
            if major_value is not None:
                data[minor] = major_value
    if family == "CHS":
        diameter: Optional[float] = data.pop("d", None) # outside diameter, where given as d
        if diameter is not None:
            data.setdefault("D", diameter)
    size = raw.get("hxb") or raw.get("hxh") or raw.get("designation") # "h x b" text of hollow sections and angles
    numbers: list[float] = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", size)] if isinstance(size, str) else []
    if family == "angle":
        leg_a, leg_b = raw.get("a"), raw.get("b")
        legs: list[float] = [float(value) for value in (leg_a, leg_b) if isinstance(value, (int, float)) and value > 0.0]
        if not legs and len(numbers) >= 2:
            legs = numbers[:2]
        if legs:
            data["leg_long"], data["leg_short"] = max(legs), min(legs)
        data.pop("B", None)
    elif family == "RHS" and len(numbers) >= 2:
        data.setdefault("D", numbers[0])
        data.setdefault("B", numbers[1])
    return section_type, data, raw


def _get(data: dict[str, float], key: str) -> float:
    value: Optional[float] = data.get(key)
    if value is None or value <= 0.0:
        raise ValueError(f"Section property '{key}' is not available; pass it through `properties` (section-table units) or as an argument.")
    return value


def _radius(data: dict[str, float], axis: str) -> float:
    """Radius of gyration about `axis` (mm), from I and A (cm⁴, cm²) where tabulated, else the tabulated r (mm)."""
    I: Optional[float] = data.get(f"I{axis}")
    A: Optional[float] = data.get("A")
    if I and A:
        return math.sqrt(I / A) * 10.0 # cm -> mm
    return _get(data, f"r{axis}")


def _design_strength(fy_mpa: Optional[float], steel_grade: str, data: dict[str, float]) -> float:
    """fy as given, else Table 1 for the thickest element (the flange of rolled sections)."""
    if fy_mpa is not None:
        return _require_positive(fy_mpa, "fy_mpa")
    thickness: float = max(data.get("tf", 0.0), data.get("tw", 0.0))
    if thickness <= 0.0:
        raise ValueError("Pass fy_mpa, or a section with its thicknesses, for Table 1.")
    return yield_stress(thickness, steel_grade)


def _ultimate_strength(fu_mpa: Optional[float], steel_grade: str) -> float:
    return _require_positive(fu_mpa, "fu_mpa") if fu_mpa is not None else ultimate_stress(steel_grade)


def _classify(
    section_type: Optional[SectionType],
    raw: dict[str, Any],
    fy: float,
    pattern: StressPattern,
    P_kN: Optional[float] = None,
) -> ClassificationResult:
    """10.8: classification of the section by the IN classification engine; P_kN gives the stress ratios r1 and r2."""
    if section_type is None:
        raise ValueError("Pass `section_class`, or a section (or section_type with properties) to classify.")
    return classify_section_from_dict(section_type, raw, fy_mpa=fy, stress_pattern=pattern, P_kN=P_kN if P_kN else None)


# --- 12.3.3 and 12.4.1 Partial safety factors ---
class FactoredLoadResult(BaseModel):
    # 12.3.3 Design action Qd = Σ γfk Qck, with the partial safety factors of Table 4
    combination: str
    limit_state: Literal["strength", "serviceability"]
    factored: float # in the units of the loads, e.g kN or kN/m
    factors: dict[str, float] # γf applied to each load
    reference: Optional[Reference] = None


def load_factors(combination: str, limit_state: Literal["strength", "serviceability"] = "strength") -> dict[str, float]:
    """IS 800:2025 Table 4: Partial safety factors γf of a load combination, e.g "DL+IL+CL" -> {"DL": 1.5, ...}.

    Args:
        combination: LOAD_FACTORS key
        limit_state: "strength" or "serviceability"
    """
    if combination not in LOAD_FACTORS:
        raise ValueError(f"Unknown combination '{combination}'; expected one of {', '.join(LOAD_FACTORS)}.")
    factors: Optional[dict[str, float]] = LOAD_FACTORS[combination].get(limit_state)
    if factors is None:
        raise ValueError(f"Table 4 gives no {limit_state} factors for {combination}.")
    return dict(factors)


def factored_load(
    combination: str = "DL+IL+CL",
    dead: float = 0.0,
    imposed: float = 0.0,
    imposed_accompanying: float = 0.0,
    wind: float = 0.0,
    erection: float = 0.0,
    fire: float = 0.0,
    accidental: float = 0.0,
    limit_state: Literal["strength", "serviceability"] = "strength",
    dead_stabilising: bool = False,
    storage: bool = True,
) -> FactoredLoadResult:
    """IS 800:2025 12.3.3 and Table 4: Design action Qd = Σ γf Qk of one load combination.

    e.g "DL+IL+CL" at the limit state of strength: 1.5DL + 1.5IL (leading) + 1.05IL (accompanying).

    Args:
        combination: LOAD_FACTORS key, "DL+IL+CL", "DL+IL+CL+WL/EL", "DL+IL+CL+WL/EL (WL/EL leading)", "DL+WL/EL",
            "DL+ER", "DL+IL+FL" or "DL+IL+AL"
        dead: Dead load DL
        imposed: Leading imposed load IL (including crane loads), the one causing the higher load effects (note 1)
        imposed_accompanying: Accompanying imposed loads
        wind: Wind load or earthquake effects WL/EL
        erection: Erection load ER
        fire: Forces due to restraints during fire FL
        accidental: Accidental load AL
        limit_state: "strength" or "serviceability"
        dead_stabilising: Note 2: γf = 0.9 on dead load contributing to stability or reducing stresses (12.5.1.1 c))
        storage: Note 3, "DL+IL+FL": the imposed load is a storage load (γf = 1.0), else γf = 0.5
    """
    factors: dict[str, float] = load_factors(combination, limit_state)
    if dead_stabilising and limit_state == "strength":
        factors["DL"] = DEAD_LOAD_STABILISING
    if combination == "DL+IL+FL" and not storage:
        factors["IL_leading"] = IMPOSED_LOAD_FIRE_OTHER
    loads: dict[str, float] = {
        "DL": dead,
        "IL_leading": imposed,
        "IL_accompanying": imposed_accompanying,
        "WL/EL": wind,
        "ER": erection,
        "FL": fire,
        "AL": accidental,
    }
    return FactoredLoadResult(
        combination=combination,
        limit_state=limit_state,
        factored=sum(factor * loads[name] for name, factor in factors.items()),
        factors=factors,
        reference=_reference("12.3.3", title="Table 4: Partial safety factors for loads"),
    )


def connection_safety_factor(connector: str = "bearing_bolts", fabrication: Literal["shop", "field"] = "shop") -> float:
    """IS 800:2025 Table 5 iv): Partial safety factor γm of a connection.

    Args:
        connector: "friction_bolts" (γmf), "bearing_bolts" (γmb), "rivets" (γmr) or "welds" (γmw)
        fabrication: "shop" or "field"
    """
    if connector not in CONNECTION_SAFETY_FACTORS:
        raise ValueError(f"Unknown connector '{connector}'; expected one of {', '.join(CONNECTION_SAFETY_FACTORS)}.")
    shop, field = CONNECTION_SAFETY_FACTORS[connector]
    return shop if fabrication == "shop" else field


# --- 10.9 Maximum effective slenderness ratio ---
def check_slenderness(KL_r: float, member: str = "compression") -> UtilisationCheck:
    """IS 800:2025 10.9.1 and Table 3: KL/r against its maximum, e.g 180 for members carrying dead and imposed loads.

    Args:
        KL_r: Effective slenderness ratio KL/r, r of the effective section (10.7.1)
        member: MAXIMUM_SLENDERNESS key
    """
    if member not in MAXIMUM_SLENDERNESS:
        raise ValueError(f"Unknown member '{member}'; expected one of {', '.join(MAXIMUM_SLENDERNESS)}.")
    limit: float = MAXIMUM_SLENDERNESS[member]
    return _ratio_check(compute_utilisation(_require_positive(KL_r, "KL_r"), limit), "10.9.1", "Maximum effective slenderness ratio", KL_r=KL_r, limit=limit)


# --- 13 Design of tension members ---
def net_area(b_mm: float, t_mm: float, n_holes: int = 0, d_h_mm: float = 0.0, staggers: Sequence[tuple[float, float]] = (), punched: bool = False) -> float:
    """IS 800:2025 13.3.1: Net area An = [b - n dh + Σ ps²/(4g)] t of a plate along a critical section (cm²).

    Args:
        b_mm: Width of the plate (mm)
        t_mm: Thickness (mm)
        n_holes: Number of bolt holes in the critical section
        d_h_mm: Diameter of the bolt hole (mm)
        staggers: (ps, g) of every inclined leg of the section: staggered pitch and gauge (mm), Fig. 5
        punched: Directly punched holes, taken 2 mm larger
    """
    b_mm, t_mm = _require_positive(b_mm, "b_mm"), _require_positive(t_mm, "t_mm")
    d_h: float = d_h_mm + (2.0 if punched and n_holes else 0.0)
    width: float = b_mm - n_holes * d_h + sum(p_s**2 / (4.0 * _require_positive(g, "g")) for p_s, g in staggers)
    if width <= 0.0:
        raise ValueError("The holes leave no net width.")
    return width * t_mm / 100.0


def shear_lag_factor(w_mm: float, t_mm: float, fy: float, fu: float, bs_mm: float, Lc_mm: float) -> float:
    """IS 800:2025 13.3.3: β = 1.4 - 0.076(w/t)(fy/fu)(bs/Lc), but <= 0.9 fu γm0/(fy γm1) and >= 0.7.

    Args:
        w_mm: Outstand leg width w (mm)
        t_mm: Thickness of the leg (mm)
        fy, fu: Yield and ultimate stress (MPa)
        bs_mm: Shear lag width bs (mm), Fig. 6
        Lc_mm: Length of the end connection (mm): between the outermost bolts, or of the weld, along the load
    """
    beta: float = 1.4 - 0.076 * (w_mm / _require_positive(t_mm, "t_mm")) * (fy / fu) * (bs_mm / _require_positive(Lc_mm, "Lc_mm"))
    return max(min(beta, 0.9 * fu * GAMMA_M0 / (fy * GAMMA_M1)), 0.7)


def block_shear_strength(Avg_mm2: float, Avn_mm2: float, Atg_mm2: float, Atn_mm2: float, fy: float, fu: float) -> float:
    """IS 800:2025 13.4.1: Block shear strength Tdb of a bolted end connection, the smaller of (kN)

    Tdb1 = Avg fy/(√3 γm0) + 0.9 Atn fu/γm1
    Tdb2 = 0.9 Avn fu/(√3 γm1) + Atg fy/γm0

    Args:
        Avg_mm2, Avn_mm2: Minimum gross and net area in shear along the bolt line(s) parallel to the force (mm²)
        Atg_mm2, Atn_mm2: Minimum gross and net area in tension, perpendicular to the force (mm²)
        fy, fu: Yield and ultimate stress (MPa)
    """
    root3: float = math.sqrt(3.0)
    T_db1: float = Avg_mm2 * fy / (root3 * GAMMA_M0) + 0.9 * Atn_mm2 * fu / GAMMA_M1
    T_db2: float = 0.9 * Avn_mm2 * fu / (root3 * GAMMA_M1) + Atg_mm2 * fy / GAMMA_M0
    return min(T_db1, T_db2) / 1e3


class TensionResult(BaseModel):
    # 13 Tension members: Td, the least of yielding (13.2), rupture (13.3) and block shear (13.4)
    Td: float # kN
    Tdg: float # kN; 13.2, Ag fy/γm0
    Tdn: float # kN; 13.3
    Tdb: Optional[float] = None # kN; 13.4
    governing: str # "yielding", "rupture" or "block shear"
    Ag: float # cm²
    An: float # cm²
    fy: float # MPa
    fu: float # MPa
    method: str # rupture: "13.3.1", "13.3.2", "13.3.3" or "13.3.4"
    beta: Optional[float] = None # 13.3.3
    Anc: Optional[float] = None # cm²; net area of the connected leg
    Ago: Optional[float] = None # cm²; gross area of the outstanding leg
    T: Optional[float] = None # kN
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.TENSILE_YIELDING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_tension(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    fu_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    T_kN: Optional[float] = None,
    An_cm2: Optional[float] = None,
    threaded_rod: bool = False,
    Lc_mm: Optional[float] = None,
    bs_mm: Optional[float] = None,
    connection: Connection = "bolted",
    connected_leg: Literal["long", "short"] = "long",
    g_mm: Optional[float] = None,
    Ago_cm2: Optional[float] = None,
    w_mm: Optional[float] = None,
    t_mm: Optional[float] = None,
    Avg_mm2: Optional[float] = None,
    Avn_mm2: Optional[float] = None,
    Atg_mm2: Optional[float] = None,
    Atn_mm2: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TensionResult:
    """IS 800:2025 13: Design strength Td of a tension member, the least of Tdg, Tdn and Tdb.

    - 13.2 yielding of the gross section: Tdg = Ag fy/γm0
    - 13.3.1 rupture of plates, and 13.3.2 threaded rods (An the net root area): Tdn = 0.9 An fu/γm1
    - 13.3.3 angles connected through one leg, and 13.3.4 other sections connected by one or more elements, with shear lag:
      Tdn = 0.9 Anc fu/γm1 + β Ago fy/γm0, β from shear_lag_factor(); used where Lc_mm is given
    - 13.4.1 block shear of bolted connections, where the four areas are given; see block_shear_strength()

    For angles Ago = (w - t/2)t of the outstanding leg w, Anc = An - Ago, and bs = w (welded) or w + g - t (bolted, g the
    gauge of the bolts from the heel of the connected leg), Fig. 6.

    Args:
        section: IN section
        fy_mpa, fu_mpa: Yield and ultimate stress (MPa); default to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade, "E250" to "E450"
        T_kN: Factored tension (kN)
        An_cm2: Net area of the whole section (cm²), see net_area(); Ag by default
        threaded_rod: 13.3.2, An the net root area at the threads
        Lc_mm: Length of the end connection (mm), for shear lag (13.3.3, 13.3.4)
        bs_mm: Shear lag width (mm); overrides the angle defaults
        connection: "bolted" or "welded", for bs of angles
        connected_leg: "long" or "short" leg of an angle connected
        g_mm: Gauge of the bolt line from the heel of the connected leg (mm), for bs of bolted angles
        Ago_cm2, w_mm, t_mm: Gross area (cm²), width and thickness (mm) of the outstanding element; required for 13.3.4
        Avg_mm2, Avn_mm2, Atg_mm2, Atn_mm2: Block shear areas (mm²), 13.4.1
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    fu: float = _ultimate_strength(fu_mpa, steel_grade)
    A_g: float = _get(data, "A")
    A_n: float = _require_positive(An_cm2, "An_cm2") if An_cm2 is not None else A_g
    if A_n > A_g + 1e-9:
        raise ValueError("Net area An cannot exceed the gross area Ag.")
    notes: list[str] = []
    T_dg: float = A_g * 100.0 * fy / GAMMA_M0 / 1e3 # 13.2

    beta, A_nc, A_go = None, None, None
    if Lc_mm is not None:
        if family == "angle" and Ago_cm2 is None:
            t: float = _get(data, "tw")
            connected: float = _get(data, "leg_long" if connected_leg == "long" else "leg_short")
            w: float = _get(data, "leg_short" if connected_leg == "long" else "leg_long")
            A_go = (w - t / 2.0) * t / 100.0
            if bs_mm is None:
                if connection == "welded":
                    bs_mm = w
                elif g_mm is not None:
                    bs_mm = w + g_mm - t # Fig. 6
                else:
                    raise ValueError("Bolted angles need g_mm, the gauge from the heel of the connected leg, or bs_mm (Fig. 6).")
            method: str = "13.3.3"
            notes.append(f"Angle connected through the {connected_leg} leg ({connected:.0f} mm); outstand w = {w:.0f} mm.")
        else:
            A_go = _require_positive(Ago_cm2, "Ago_cm2")
            w = _require_positive(w_mm, "w_mm")
            t = _require_positive(t_mm, "t_mm")
            method = "13.3.3" if family == "angle" else "13.3.4"
            if bs_mm is None:
                raise ValueError("Pass bs_mm, the shear lag width (13.3.4).")
        A_nc = A_n - A_go
        if A_nc <= 0.0:
            raise ValueError("The net area of the connected element Anc = An - Ago must be positive.")
        beta = shear_lag_factor(w, t, fy, fu, bs_mm, Lc_mm)
        T_dn: float = (0.9 * A_nc * 100.0 * fu / GAMMA_M1 + beta * A_go * 100.0 * fy / GAMMA_M0) / 1e3
    else:
        method = "13.3.2" if threaded_rod else "13.3.1"
        T_dn = 0.9 * A_n * 100.0 * fu / GAMMA_M1 / 1e3
        if family in ("angle", "channel", "I"):
            notes.append("Rupture without shear lag (13.3.1); pass Lc_mm for members connected by one element (13.3.3, 13.3.4).")

    T_db: Optional[float] = None
    block_areas: tuple[Optional[float], ...] = (Avg_mm2, Avn_mm2, Atg_mm2, Atn_mm2)
    if any(area is not None for area in block_areas):
        if any(area is None for area in block_areas):
            raise ValueError("Block shear needs Avg_mm2, Avn_mm2, Atg_mm2 and Atn_mm2 (13.4.1).")
        T_db = block_shear_strength(Avg_mm2, Avn_mm2, Atg_mm2, Atn_mm2, fy, fu) # type: ignore[arg-type]

    strengths: dict[str, float] = {"yielding": T_dg, "rupture": T_dn}
    if T_db is not None:
        strengths["block shear"] = T_db
    governing: str = min(strengths, key=lambda key: strengths[key])
    T_d: float = strengths[governing]
    limit_state: LimitState = LimitState.TENSILE_YIELDING if governing == "yielding" else LimitState.TENSILE_RUPTURE
    return TensionResult(
        Td=T_d,
        Tdg=T_dg,
        Tdn=T_dn,
        Tdb=T_db,
        governing=governing,
        Ag=A_g,
        An=A_n,
        fy=fy,
        fu=fu,
        method=method,
        beta=beta,
        Anc=A_nc,
        Ago=A_go,
        T=T_kN,
        utilisation=_utilisation_check(T_kN, T_d, "13.1", f"Tension, {governing}") if T_kN is not None else None,
        limit_state=limit_state,
        reference=_reference("13.1", title="Design of tension members"),
        metadata={"notes": notes} if notes else {},
    )


# --- 14 Design of compression members ---
def effective_length(L: float, restraint: str = "pinned_pinned") -> float:
    """IS 800:2025 14.2.2 and Table 11: Effective length KL of a prismatic compression member (mm).

    Args:
        L: Unsupported length, centre to centre of the intersections with the supporting members (14.2.1) (mm)
        restraint: COMPRESSION_EFFECTIVE_LENGTHS key, "fixed_free" (2.0L), "pinned_sway_fixed" (2.0L), "pinned_pinned"
            (1.0L), "fixed_sway_fixed" (1.2L), "fixed_pinned" (0.8L) or "fixed_fixed" (0.65L)
    """
    if restraint not in COMPRESSION_EFFECTIVE_LENGTHS:
        raise ValueError(f"Unknown restraint '{restraint}'; expected one of {', '.join(COMPRESSION_EFFECTIVE_LENGTHS)}.")
    return COMPRESSION_EFFECTIVE_LENGTHS[restraint] * _require_positive(L, "L")


def stiffness_ratio(Kc_sum: float, Kb_sum: float) -> float:
    """IS 800:2025 D-1: β = ΣKc/(ΣKc + ΣKb) at one end of a column, K = C(I/L) of the columns and beams at the joint."""
    total: float = _require_positive(Kc_sum, "Kc_sum") + max(Kb_sum, 0.0)
    return Kc_sum / total


def frame_effective_length_factor(beta_1: float, beta_2: float, sway: bool = False) -> float:
    """IS 800:2025 D-1: Effective length factor K of a column in a frame with rigid beam to column connections.

    a) non-sway (braced) frames: K = [1 + 0.145(β1 + β2) - 0.265β1β2]/[2 - 0.364(β1 + β2) - 0.247β1β2]
    b) sway (moment resisting) frames: K = {[1 - 0.2(β1 + β2) - 0.12β1β2]/[1 - 0.8(β1 + β2) + 0.6β1β2]}^0.5

    Args:
        beta_1, beta_2: β at the two ends, see stiffness_ratio(); 0 for fixed and 1 for pinned
        sway: Sway frame
    """
    for beta in (beta_1, beta_2):
        if not 0.0 <= beta <= 1.0:
            raise ValueError("β1 and β2 must lie between 0 (fixed) and 1 (pinned).")
    total, product = beta_1 + beta_2, beta_1 * beta_2
    if sway:
        denominator: float = 1.0 - 0.8 * total + 0.6 * product
        if denominator <= 0.0:
            raise ValueError("Both ends pinned in a sway frame: the column is a mechanism (K is infinite).")
        return math.sqrt((1.0 - 0.2 * total - 0.12 * product) / denominator)
    return (1.0 + 0.145 * total - 0.265 * product) / (2.0 - 0.364 * total - 0.247 * product)


def buckling_class(shape: str, axis: str = "z", fy_mpa: float = 250.0) -> str:
    """IS 800:2025 14.1.2.3 and Table 10: Buckling class a0, a, b, c or d.

    Args:
        shape: BUCKLING_CLASSES key, e.g "rolled_I_tf_40"; see buckling_shape()
        axis: "z" (major) or "y" (minor); any other axis, e.g "v" of angles, takes the y-y class
        fy_mpa: Yield stress (MPa); columns (4) and (5) of Table 10 split at 420 MPa
    """
    if shape not in BUCKLING_CLASSES:
        raise ValueError(f"Unknown shape '{shape}'; expected one of {', '.join(BUCKLING_CLASSES)}.")
    classes: tuple[str, str] = BUCKLING_CLASSES[shape][1 if fy_mpa > 420.0 else 0]
    return classes[0] if axis == "z" else classes[1]


def buckling_shape(
    section_type: Optional[SectionType],
    D_mm: Optional[float] = None,
    B_mm: Optional[float] = None,
    tf_mm: Optional[float] = None,
    welded: bool = False,
    thick_welds: bool = False,
) -> str:
    """IS 800:2025 Table 10: the row (BUCKLING_CLASSES key) of an IN section, or of a hollow section type.

    Rolled I-sections are told apart by h/bf and tf; welded ones by tf; hollow sections by hot rolled or cold formed.
    Table 10 has no rolled I row for h/bf > 1.2 with tf > 100 mm; the h/bf <= 1.2 row for tf > 100 mm is used.
    """
    family: str = _family(section_type)
    if family == "I":
        tf: float = _require_positive(tf_mm, "tf_mm")
        if welded:
            return "welded_I_tf_40" if tf <= 40.0 else "welded_I_thick"
        if tf > 100.0:
            return "rolled_H_thick"
        if _require_positive(D_mm, "D_mm") / _require_positive(B_mm, "B_mm") > 1.2:
            return "rolled_I_tf_40" if tf <= 40.0 else "rolled_I_tf_100"
        return "rolled_H_tf_100"
    if family in ("RHS", "CHS"):
        if welded:
            return "welded_box_thick_welds" if thick_welds else "welded_box"
        return "cold_formed_hollow" if section_type in COLD_FORMED_SECTION_TYPES else "hot_rolled_hollow"
    if family == "channel":
        return "channel_tee_solid"
    if family == "angle":
        return "welded_angle" if welded else "rolled_angle"
    raise NotImplementedError(f"Table 10 has no row for {family} sections; pass `buckling_classes`.")


def non_dimensional_slenderness(KL_r: float, fy: float, E: float = E_STEEL) -> float:
    """IS 800:2025 14.1.2.1: λ = (fy/fcr)^0.5, fcr = π²E/(KL/r)² the Euler buckling stress."""
    if KL_r < 0.0:
        raise ValueError("KL_r cannot be negative.")
    return KL_r * math.sqrt(_require_positive(fy, "fy") / E) / math.pi


def euler_buckling_stress(KL_r: float, E: float = E_STEEL) -> float:
    """IS 800:2025 14.1.2.1: Euler buckling stress fcr = π²E/(KL/r)² (MPa)."""
    return math.pi**2 * E / _require_positive(KL_r, "KL_r") ** 2


def stress_reduction_factor(lambda_bar: float, alpha: float) -> float:
    """IS 800:2025 14.1.2.1: χ = 1/[φ + (φ² - λ²)^0.5] <= 1.0, φ = 0.5[1 + α(λ - 0.2) + λ²].

    NOTE: the draft prints φ² + λ² under the root; Table 8 is computed with φ² - λ², e.g 0.579 for class a, fy = 250 MPa,
    KL/r = 100, as used here (and in IS 800:2007).

    Args:
        lambda_bar: Non-dimensional effective slenderness ratio λ
        alpha: Imperfection factor α, Table 7
    """
    if lambda_bar < 0.0:
        raise ValueError("lambda_bar cannot be negative.")
    phi: float = 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar**2)
    return min(1.0 / (phi + math.sqrt(max(phi**2 - lambda_bar**2, 0.0))), 1.0)


def design_compressive_stress(KL_r: float, fy: float, buckling_class: str = "b", E: float = E_STEEL) -> float:
    """IS 800:2025 14.1.2: Design compressive stress fcd = χ fy/γm0 <= fy/γm0 (MPa); Table 9.

    Args:
        KL_r: Effective slenderness ratio KL/r
        fy: Yield stress (MPa)
        buckling_class: "a0", "a", "b", "c" or "d" (Table 10)
        E: Modulus of elasticity (MPa)
    """
    if buckling_class not in IMPERFECTION_FACTORS:
        raise ValueError(f"Unknown buckling class '{buckling_class}'; expected one of {', '.join(IMPERFECTION_FACTORS)}.")
    chi: float = stress_reduction_factor(non_dimensional_slenderness(KL_r, fy, E), IMPERFECTION_FACTORS[buckling_class])
    return chi * fy / GAMMA_M0


def torsional_flexural_reduction_factor(
    lambda_TF: float,
    lambda_y: float,
    alpha: float,
    A_mm2: float,
    fy: float,
    i_p_mm: float,
    I_T_mm4: float,
    d_y_mm: float = 0.0,
    G: float = G_STEEL,
) -> float:
    """IS 800:2025 14.1.2.2: Reduction factor χ for torsional and torsional flexural buckling.

    χ = 1/[φ + (φ² - λTF²)^0.5] <= 1.0
    φ = 0.5[1 + (λTF/λy)² αTF(λy - 0.2) + λTF²]
    αTF = α[A fy (ip² + dy²)/(6.25 G IT)]^0.5

    NOTE: as in 14.1.2.1, the draft prints φ² + λTF² under the root; φ² - λTF² is used. The draft defines λy as "the
    distance between intermediate lateral support and shear centre", which is dy; λy here is the non-dimensional
    slenderness for flexural buckling about y-y (as in 15.2.2).

    Args:
        lambda_TF: (fy/fcrTF)^0.5, fcrTF the torsional (flexural) buckling stress
        lambda_y: Non-dimensional slenderness for flexural buckling about y-y
        alpha: Imperfection factor α of Table 7 (the class for y-y)
        A_mm2: Area (mm²)
        fy: Yield stress (MPa)
        i_p_mm: Polar radius of gyration, ip² = (Iy + Iz)/A (mm)
        I_T_mm4: Torsion constant (mm⁴)
        d_y_mm: Distance between an intermediate lateral support and the shear centre (mm)
        G: Modulus of rigidity (MPa)
    """
    lambda_y = _require_positive(lambda_y, "lambda_y")
    alpha_TF: float = alpha * math.sqrt(A_mm2 * fy * (i_p_mm**2 + d_y_mm**2) / (6.25 * G * _require_positive(I_T_mm4, "I_T_mm4")))
    phi: float = 0.5 * (1.0 + (lambda_TF / lambda_y) ** 2 * alpha_TF * (lambda_y - 0.2) + lambda_TF**2)
    return min(1.0 / (phi + math.sqrt(max(phi**2 - lambda_TF**2, 0.0))), 1.0)


def elastic_torsional_buckling_stress(
    A_cm2: float,
    Iy_cm4: float,
    Iz_cm4: float,
    It_cm4: float,
    Iw_cm6: float,
    L_T_mm: float,
    y0_mm: float = 0.0,
    E: float = E_STEEL,
    G: float = G_STEEL,
) -> float:
    """Elastic torsional buckling stress fcr,T = (G IT + π²E Iw/LT²)/(A i0²), i0² = (Iy + Iz)/A + y0² (MPa).

    The draft names fcrTF (14.1.2.2) without a formula; this is the classical elastic value, as in EN 1993-1-3 6.2.3.

    Args:
        A_cm2: Area (cm²)
        Iy_cm4, Iz_cm4: Second moments of area (cm⁴)
        It_cm4: Torsion constant (cm⁴)
        Iw_cm6: Warping constant (cm⁶)
        L_T_mm: Effective length for torsional buckling (mm)
        y0_mm: Distance of the shear centre from the centroid (mm)
        E, G: Moduli (MPa)
    """
    A: float = _require_positive(A_cm2, "A_cm2") * 100.0
    i0_sq: float = (Iy_cm4 + Iz_cm4) * 1e4 / A + y0_mm**2
    L_T: float = _require_positive(L_T_mm, "L_T_mm")
    return (G * It_cm4 * 1e4 + math.pi**2 * E * Iw_cm6 * 1e6 / L_T**2) / (A * i0_sq)


def elastic_torsional_flexural_buckling_stress(f_cr_y: float, f_cr_T: float, y0_mm: float, i0_mm: float) -> float:
    """Elastic torsional flexural buckling stress of a section symmetric about y-y (MPa), classical elastic theory as in
    EN 1993-1-3 6.2.3(7): fcr,TF = [(fcr,y + fcr,T) - ((fcr,y + fcr,T)² - 4β fcr,y fcr,T)^0.5]/(2β), β = 1 - (y0/i0)².

    Args:
        f_cr_y: Euler buckling stress about the axis of symmetry (MPa)
        f_cr_T: Elastic torsional buckling stress (MPa), elastic_torsional_buckling_stress()
        y0_mm: Distance of the shear centre from the centroid, along the axis of symmetry (mm)
        i0_mm: Polar radius of gyration about the shear centre (mm)
    """
    beta: float = 1.0 - (y0_mm / _require_positive(i0_mm, "i0_mm")) ** 2
    if beta <= 0.0:
        raise ValueError("y0 must be smaller than i0.")
    total: float = f_cr_y + f_cr_T
    return (total - math.sqrt(max(total**2 - 4.0 * beta * f_cr_y * f_cr_T, 0.0))) / (2.0 * beta)


_ELEMENT_COUNTS: dict[str, dict[str, int]] = {
    "I": {"flange": 4, "web": 1}, # four flange outstands
    "channel": {"flange": 2, "web": 1},
    "RHS": {"flange_wall": 2, "web_wall": 2},
}


class EffectiveArea(BaseModel):
    # 10.7.1 b) 1), 10.8.2 d) and 14.3.2: effective sectional area Ae in compression
    Ae: float # cm²
    Ag: float # cm²
    section_class: SectionClass
    deductions: dict[str, float] = Field(default_factory=dict) # cm², per element (all of its kind)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _effective_area(family: str, data: dict[str, float], classification: ClassificationResult) -> tuple[float, dict[str, float]]:
    """Ag less the width of every slender element in excess of its semi-compact limit (10.8.2 d)), cm²."""
    A_g: float = _get(data, "A")
    eps: float = classification.epsilon
    deductions: dict[str, float] = {}
    for element in classification.elements:
        if element.section_class != SectionClass.CLASS_4:
            continue
        t: float = element.t_mm
        if element.kind == ElementKind.ANGLE:
            leg: float = element.metadata.get("d/t", 0.0) * t
            b_eff: float = min(element.b_mm, 14.5 * eps * t)
            d_eff: float = min(leg, 14.5 * eps * t)
            b_eff -= max(b_eff + d_eff - 22.3 * eps * t, 0.0) # (b + d)/t <= 22.3ε, taken off the longer leg
            deductions[element.name] = (element.b_mm - b_eff + leg - d_eff) * t / 100.0
            continue
        count: Optional[int] = _ELEMENT_COUNTS.get(family, {}).get(element.name)
        if count is None or element.class_3_limit is None:
            raise NotImplementedError(f"No effective width rule for the {element.name} of {family} sections; pass A_eff_cm2.")
        excess: float = element.b_mm - effective_width(element.b_mm, t, element.class_3_limit)
        deductions[element.name] = count * excess * t / 100.0
    return A_g - sum(deductions.values()), deductions


def effective_sectional_area(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> EffectiveArea:
    """IS 800:2025 14.3.2 and 10.8.2 d): Effective sectional area Ae of a member in axial compression.

    Ae = Ag for plastic, compact and semi-compact sections; for slender (class 4) sections, the width of every slender
    element in excess of its semi-compact limit is deducted (the conservative alternative to IS 801). Holes not fitted
    with rivets, bolts or pins are deducted separately in check_compression().
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    classification: ClassificationResult = _classify(section_type, raw, fy, StressPattern.COMPRESSION)
    A_e, deductions = (_get(data, "A"), {}) if classification.section_class != SectionClass.CLASS_4 else _effective_area(_family(section_type), data, classification)
    return EffectiveArea(
        Ae=A_e,
        Ag=_get(data, "A"),
        section_class=classification.section_class,
        deductions=deductions,
        reference=_reference("14.3.2", title="Effective sectional area"),
    )


class BucklingMode(BaseModel):
    axis: str # "z", "y", "v" or "TF"
    KL: Optional[float] = None # mm
    r: Optional[float] = None # mm
    KL_r: Optional[float] = None # effective slenderness ratio
    lambda_bar: float # non-dimensional slenderness
    buckling_class: str # Table 10
    alpha: float # Table 7
    chi: float # 14.1.2.1 or 14.1.2.2
    fcd: float # MPa
    Pd: float # kN


class CompressionResult(BaseModel):
    # 14.1.2 Design compressive strength Pd = Ae fcd, the least over the buckling modes
    Pd: float # kN
    Pdz: Optional[float] = None # kN; flexural buckling about z-z (major)
    Pdy: Optional[float] = None # kN; flexural buckling about y-y (minor)
    Pd_TF: Optional[float] = None # kN; torsional or torsional flexural buckling, 14.1.2.2
    governing_axis: str
    section_class: SectionClass # 10.8, in axial compression
    fy: float # MPa
    Ae: float # cm²
    Ag: float # cm²
    modes: list[BucklingMode]
    P: Optional[float] = None # kN
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.FLEXURAL_BUCKLING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_compression(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    P_kN: Optional[float] = None,
    KLz_mm: Optional[float] = None,
    KLy_mm: Optional[float] = None,
    KLv_mm: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    buckling_classes: Optional[dict[str, str]] = None,
    A_eff_cm2: Optional[float] = None,
    A_holes_cm2: float = 0.0,
    f_cr_TF_mpa: Optional[float] = None,
    d_y_mm: float = 0.0,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CompressionResult:
    """IS 800:2025 14.1.2: Design compressive strength Pd = Ae fcd, for every axis with an effective length.

    fcd = χ fy/γm0 with χ from 14.1.2.1 and the buckling class of Table 10 (Table 9 tabulates fcd). Ae is the gross area,
    less holes not fitted with fasteners, for semi-compact and better sections; the slender elements lose their width in
    excess of the semi-compact limit (14.3.2, 10.8.2 d)). With f_cr_TF_mpa, torsional or torsional flexural buckling is
    also checked (14.1.2.2); it needs the y-y mode (KLy_mm) and I_t.

    Args:
        section: IN section; classified in axial compression unless `section_class` is given
        fy_mpa: Yield stress (MPa); defaults to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade, "E250" to "E450"
        P_kN: Factored compression (kN)
        KLz_mm, KLy_mm: Effective lengths for buckling about z-z and y-y (mm), 14.2; see effective_length()
        KLv_mm: Effective length about v-v of angles (mm)
        section_class: Class to use instead of classifying
        welded: Welded (built-up) section, for Table 10
        buckling_classes: Buckling class per axis, e.g {"z": "b", "y": "c"}; overrides Table 10
        A_eff_cm2: Effective area of a slender section (cm²); overrides 10.8.2 d)
        A_holes_cm2: Area of holes not fitted with rivets, bolts or pins (cm²), 14.3.2
        f_cr_TF_mpa: Torsional (flexural) buckling stress fcrTF (MPa), see elastic_torsional_buckling_stress()
        d_y_mm: Distance between an intermediate lateral support and the shear centre (mm), 14.1.2.2
        E, G: Moduli (MPa)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    A_g: float = _get(data, "A")
    classification: Optional[ClassificationResult] = None
    if section_class is not None:
        cls: SectionClass = _as_section_class(section_class)
    else:
        classification = _classify(section_type, raw, fy, StressPattern.COMPRESSION)
        cls = classification.section_class
    notes: list[str] = []
    A_e: float = A_g
    if cls == SectionClass.CLASS_4:
        if A_eff_cm2 is not None:
            A_e = _require_positive(A_eff_cm2, "A_eff_cm2")
        else:
            classification = classification or _classify(section_type, raw, fy, StressPattern.COMPRESSION)
            A_e, deductions = _effective_area(family, data, classification)
            notes.append("10.8.2 d): slender elements reduced to their semi-compact width: " + ", ".join(f"{name} -{value:.2f} cm²" for name, value in deductions.items()))
    A_e -= max(A_holes_cm2, 0.0) # 14.3.2
    A_e = _require_positive(A_e, "Ae")
    buckling_classes = buckling_classes or {}

    modes: list[BucklingMode] = []
    for axis, K_L in (("z", KLz_mm), ("y", KLy_mm), ("v", KLv_mm)):
        if K_L is None:
            continue
        r: float = _radius(data, axis)
        KL_r: float = _require_positive(K_L, f"KL{axis}_mm") / r
        if axis in buckling_classes:
            class_: str = buckling_classes[axis]
        else:
            class_ = buckling_class(buckling_shape(section_type, data.get("D"), data.get("B"), data.get("tf"), welded), axis, fy)
        alpha: float = IMPERFECTION_FACTORS[class_]
        lambda_bar: float = non_dimensional_slenderness(KL_r, fy, E)
        chi: float = stress_reduction_factor(lambda_bar, alpha)
        f_cd: float = chi * fy / GAMMA_M0
        modes.append(BucklingMode(axis=axis, KL=K_L, r=r, KL_r=KL_r, lambda_bar=lambda_bar, buckling_class=class_, alpha=alpha, chi=chi, fcd=f_cd, Pd=A_e * 100.0 * f_cd / 1e3))
        if KL_r > MAXIMUM_SLENDERNESS["compression"]:
            notes.append(f"Table 3: KL/r = {KL_r:.0f} about {axis}-{axis} exceeds 180 for members carrying dead and imposed loads.")

    if f_cr_TF_mpa is not None:
        y_mode: Optional[BucklingMode] = next((mode for mode in modes if mode.axis == "y"), None)
        if y_mode is None:
            raise ValueError("Torsional flexural buckling (14.1.2.2) needs the y-y mode; pass KLy_mm.")
        lambda_TF: float = math.sqrt(fy / _require_positive(f_cr_TF_mpa, "f_cr_TF_mpa"))
        i_p: float = math.sqrt((_get(data, "Iy") + _get(data, "Iz")) / A_g) * 10.0 # mm
        chi_TF: float = torsional_flexural_reduction_factor(lambda_TF, y_mode.lambda_bar, y_mode.alpha, A_g * 100.0, fy, i_p, _get(data, "It") * 1e4, d_y_mm, G)
        f_cd_TF: float = chi_TF * fy / GAMMA_M0
        modes.append(BucklingMode(axis="TF", lambda_bar=lambda_TF, buckling_class=y_mode.buckling_class, alpha=y_mode.alpha, chi=chi_TF, fcd=f_cd_TF, Pd=A_e * 100.0 * f_cd_TF / 1e3))

    if not modes:
        raise ValueError("Pass at least one effective length: KLz_mm, KLy_mm or KLv_mm.")
    governing: BucklingMode = min(modes, key=lambda mode: mode.Pd)
    by_axis: dict[str, float] = {mode.axis: mode.Pd for mode in modes}
    limit_state: LimitState = LimitState.TORSIONAL_FLEXURAL_BUCKLING if governing.axis == "TF" else LimitState.FLEXURAL_BUCKLING
    return CompressionResult(
        Pd=governing.Pd,
        Pdz=by_axis.get("z"),
        Pdy=by_axis.get("y"),
        Pd_TF=by_axis.get("TF"),
        governing_axis=governing.axis,
        section_class=cls,
        fy=fy,
        Ae=A_e,
        Ag=A_g,
        modes=modes,
        P=P_kN,
        utilisation=_utilisation_check(P_kN, governing.Pd, "14.1.2", "Design compressive strength") if P_kN is not None else None,
        limit_state=limit_state,
        reference=_reference("14.1.2", title="Design compressive strength"),
        metadata={"notes": notes} if notes else {},
    )


# --- 14.5 Angle struts ---
def _angle_slenderness(L_r: float, fy: float, E: float) -> float:
    """14.5.1: (L/r)/(ε(π²E/250)^0.5), i.e. the λ of 14.1.2.1."""
    return L_r / (epsilon(fy) * math.sqrt(math.pi**2 * E / 250.0))


def angle_strut_modification_factor(
    lambda_aa: float,
    lambda_phi: float,
    connection: AngleConnection = "two_bolts",
    fixity: Fixity | float = "hinged",
) -> float:
    """IS 800:2025 14.5.1.2 and Table 12: Kf = k1 + k2 λaa + k3 λφ of a single angle loaded through one leg.

    Args:
        lambda_aa: Non-dimensional slenderness about the a-a axis, parallel to the connected leg
        lambda_phi: λφ = ((b1 + b2)/2t)/(ε(π²E/250)^0.5)
        connection: "welded" or "two_bolts" (Table 12 i)), or "single_bolt" (ii))
        fixity: "fixed" or "hinged" in-plane rotational restraint of the gusset by the supporting member, or the fraction
            of full fixity (0 hinged to 1 fixed) for partial restraint, Kf interpolated between the two (note 1)
    """
    row: str = "single_bolt" if connection == "single_bolt" else "welded"
    fixed: float = sum(k * value for k, value in zip(ANGLE_STRUT_CONSTANTS[(row, "fixed")], (1.0, lambda_aa, lambda_phi)))
    hinged: float = sum(k * value for k, value in zip(ANGLE_STRUT_CONSTANTS[(row, "hinged")], (1.0, lambda_aa, lambda_phi)))
    if isinstance(fixity, str):
        if fixity not in ("fixed", "hinged"):
            raise ValueError("fixity must be 'fixed', 'hinged' or a fraction between 0 and 1.")
        return fixed if fixity == "fixed" else hinged
    if not 0.0 <= fixity <= 1.0:
        raise ValueError("fixity must lie between 0 (hinged) and 1 (fixed).")
    return hinged + fixity * (fixed - hinged)


class AngleStrutResult(BaseModel):
    # 14.5.1 Single angle struts: concentric loading (14.5.1.1) or loaded through one leg (14.5.1.2)
    Pd: float # kN
    fcd: float # MPa; fcde for 14.5.1.2
    chi: float # χvv or χaa
    lambda_bar: float # λvv or λaa
    lambda_phi: Optional[float] = None
    Kf: Optional[float] = None
    buckling_class: str
    loading: Literal["concentric", "one_leg"]
    r: float # rvv or raa, mm
    L: float # mm
    section_class: Optional[SectionClass] = None
    fy: float # MPa
    A: float # cm²
    P: Optional[float] = None # kN
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.FLEXURAL_BUCKLING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_angle_strut(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    P_kN: Optional[float] = None,
    L_mm: Optional[float] = None,
    loading: Literal["concentric", "one_leg"] = "one_leg",
    connection: AngleConnection = "two_bolts",
    fixity: Fixity | float = "hinged",
    connected_leg: Literal["long", "short"] = "long",
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> AngleStrutResult:
    """IS 800:2025 14.5.1: Design strength of a single angle strut.

    14.5.1.1 concentric loading: 14.1.2 with λvv = (lvv/rvv)/(ε(π²E/250)^0.5) about the minor axis v-v and the Table 10
    class of rolled angles (b, or a above 420 MPa).
    14.5.1.2 loaded through one leg by a gusset: fcde = Kf χaa fy/γm0, χaa for buckling class b at λaa about the a-a axis
    parallel to the connected leg, Kf = k1 + k2 λaa + k3 λφ (Table 12) and λφ = ((b1 + b2)/2t)/(ε(π²E/250)^0.5). fcde
    is kept to fy/γm0 at most. The a-a axis parallel to the long leg has the smaller of the two rectangular I.

    Args:
        section: IN angle (EqualAngle or UnequalAngle)
        fy_mpa: Yield stress (MPa); defaults to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade
        P_kN: Factored compression (kN)
        L_mm: lvv (concentric) or laa (one leg), the length between lateral supports (mm)
        loading: "concentric" or "one_leg"
        connection: Table 12: "welded" or "two_bolts" (two or more bolts), or "single_bolt"
        fixity: "fixed", "hinged" or a fraction of full fixity, see angle_strut_modification_factor()
        connected_leg: "long" or "short" leg on the gusset
        E: Modulus of elasticity (MPa)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    if _family(section_type) != "angle":
        raise ValueError("14.5.1 applies to single angles (EA, UA).")
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    A: float = _get(data, "A")
    L: float = _require_positive(L_mm, "L_mm")
    classification: ClassificationResult = _classify(section_type, raw, fy, StressPattern.COMPRESSION)
    notes: list[str] = []
    if classification.is_slender:
        notes.append("Slender angle (Table 2 iv)): the effective area should replace A (10.8.2 d)).")

    if loading == "concentric":
        r: float = _radius(data, "v")
        lambda_bar: float = _angle_slenderness(L / r, fy, E)
        class_: str = buckling_class("rolled_angle", "v", fy)
        chi: float = stress_reduction_factor(lambda_bar, IMPERFECTION_FACTORS[class_])
        f_cd: float = chi * fy / GAMMA_M0
        lambda_phi, K_f, clause = None, None, "14.5.1.1"
    else:
        I_values: list[float] = [data[key] for key in ("Iz", "Iy") if key in data]
        if not I_values:
            raise ValueError("Loading through one leg needs I_zz and I_yy of the angle.")
        I_aa: float = min(I_values) if connected_leg == "long" else max(I_values)
        r = math.sqrt(I_aa / A) * 10.0
        lambda_bar = _angle_slenderness(L / r, fy, E)
        class_ = "b" # 14.5.1.2: buckling class b
        chi = stress_reduction_factor(lambda_bar, IMPERFECTION_FACTORS[class_])
        t: float = _get(data, "tw")
        lambda_phi = _angle_slenderness((_get(data, "leg_long") + _get(data, "leg_short")) / (2.0 * t), fy, E)
        K_f = angle_strut_modification_factor(lambda_bar, lambda_phi, connection, fixity)
        f_cd = min(K_f * chi, 1.0) * fy / GAMMA_M0
        clause = "14.5.1.2"
        if K_f * chi > 1.0:
            notes.append(f"Kf χaa = {K_f * chi:.3f} > 1; fcde is kept to fy/γm0.")
    P_d: float = A * 100.0 * f_cd / 1e3
    return AngleStrutResult(
        Pd=P_d,
        fcd=f_cd,
        chi=chi,
        lambda_bar=lambda_bar,
        lambda_phi=lambda_phi,
        Kf=K_f,
        buckling_class=class_,
        loading=loading,
        r=r,
        L=L,
        section_class=classification.section_class,
        fy=fy,
        A=A,
        P=P_kN,
        utilisation=_utilisation_check(P_kN, P_d, clause, "Single angle strut") if P_kN is not None else None,
        reference=_reference(clause, title="Single angle struts"),
        metadata={"notes": notes} if notes else {},
    )


# --- 15.4 Shear ---
def shear_area(
    section: Optional[BaseSection] = None,
    axis: BendingAxis = "z",
    welded: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> float:
    """IS 800:2025 15.4.1.1: Shear area Av (cm²).

    a) I and channel sections: major axis bending (load parallel to the web), hot rolled h tw, welded d tw; minor axis
       bending, 2b tf
    b) RHS of uniform thickness: load parallel to the depth h, A h/(b + h); parallel to the width b, A b/(b + h)
    c) CHS of uniform thickness: 2A/π
    d) plates and solid bars: A

    Args:
        section: IN section
        axis: Axis of bending, "z" (major, shear parallel to the web) or "y" (minor)
        welded: Welded I or channel section
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    return _shear_area(_family(section_type), data, axis, welded)


def _shear_area(family: str, data: dict[str, float], axis: BendingAxis, welded: bool) -> float:
    if family in ("I", "channel"):
        if axis == "z":
            depth: float = _get(data, "D") - 2.0 * _get(data, "tf") if welded else _get(data, "D") # d, clear between the flanges
            return depth * _get(data, "tw") / 100.0
        return 2.0 * _get(data, "B") * _get(data, "tf") / 100.0
    if family == "RHS":
        D, B = _get(data, "D"), _get(data, "B")
        return _get(data, "A") * (D if axis == "z" else B) / (B + D)
    if family == "CHS":
        return 2.0 * _get(data, "A") / math.pi
    raise NotImplementedError(f"15.4.1.1 gives no shear area for {family} sections; pass Av_cm2.")


def shear_holes_negligible(Avn_cm2: float, Av_cm2: float, fy: float, fu: float) -> bool:
    """IS 800:2025 15.4.1.1 NOTE: fastener holes need not be accounted for in the plastic shear strength where
    Avn >= (fy/fu)(γm1/γm0)Av/0.9; otherwise the effective shear area is the one satisfying the limit."""
    return Avn_cm2 >= (fy / fu) * (GAMMA_M1 / GAMMA_M0) * Av_cm2 / 0.9


def shear_buckling_coefficient(c_d: Optional[float] = None) -> float:
    """IS 800:2025 15.4.2.2 a): Shear buckling coefficient Kv; 5.35 with transverse stiffeners only at the supports
    (c_d None), 4.0 + 5.35/(c/d)² for c/d < 1.0 and 5.35 + 4.0/(c/d)² for c/d >= 1.0."""
    if c_d is None:
        return 5.35
    c_d = _require_positive(c_d, "c_d")
    return 4.0 + 5.35 / c_d**2 if c_d < 1.0 else 5.35 + 4.0 / c_d**2


def shear_buckling_required(d_tw: float, fyw: float, Kv: Optional[float] = None) -> bool:
    """IS 800:2025 15.4.2.1: shear buckling is verified where d/tw > 67εw (no stiffeners) or 67εw(Kv/5.35)^0.5
    (with stiffeners), εw = (250/fyw)^0.5."""
    limit: float = 67.0 * epsilon(fyw) * (math.sqrt(Kv / 5.35) if Kv is not None else 1.0)
    return d_tw > limit


def elastic_critical_shear_stress(d_tw: float, Kv: float = 5.35, E: float = E_STEEL, mu: float = POISSON_RATIO) -> float:
    """IS 800:2025 15.4.2.2 a): τcr,e = Kv π²E/[12(1 - μ²)(d/tw)²] (MPa)."""
    return Kv * math.pi**2 * E / (12.0 * (1.0 - mu**2) * _require_positive(d_tw, "d_tw") ** 2)


def web_shear_slenderness(d_tw: float, fyw: float, Kv: float = 5.35, E: float = E_STEEL) -> float:
    """IS 800:2025 15.4.2.2 a): λw = [fyw/(√3 τcr,e)]^0.5."""
    return math.sqrt(fyw / (math.sqrt(3.0) * elastic_critical_shear_stress(d_tw, Kv, E)))


def shear_buckling_stress(lambda_w: float, fyw: float) -> float:
    """IS 800:2025 15.4.2.2 a): τb (MPa); fyw/√3 for λw <= 0.8, [1 - 0.8(λw - 0.8)]fyw/√3 for 0.8 < λw < 1.2 and
    fyw/(√3 λw²) for λw >= 1.2."""
    tau_y: float = fyw / math.sqrt(3.0)
    if lambda_w <= 0.8:
        return tau_y
    if lambda_w < 1.2:
        return (1.0 - 0.8 * (lambda_w - 0.8)) * tau_y
    return tau_y / lambda_w**2


def flange_reduced_plastic_moment(bf_mm: float, tf_mm: float, fyf: float, Nf_kN: float = 0.0) -> float:
    """IS 800:2025 15.4.2.2 b): Mfr = 0.25 bf tf² fyf [1 - (Nf/(bf tf fyf/γm0))²] of a flange carrying Nf (kNm)."""
    squash: float = bf_mm * tf_mm * fyf / GAMMA_M0 # N
    ratio: float = min(abs(Nf_kN) * 1e3 / squash, 1.0)
    return 0.25 * bf_mm * tf_mm**2 * fyf * (1.0 - ratio**2) / 1e6


def tension_field_shear_resistance(
    d_mm: float,
    tw_mm: float,
    c_mm: float,
    fyw: float,
    Av_cm2: float,
    Mfr_c_kNm: float,
    Mfr_t_kNm: float,
    E: float = E_STEEL,
) -> float:
    """IS 800:2025 15.4.2.2 b): Nominal shear resistance by the tension field method (kN).

    Vtf = [Av τb + 0.9 wtf tw fv sin φ] <= Vp
    fv = [fyw² - 3τb² + ψ²]^0.5 - ψ,  ψ = 1.5 τb sin 2φ,  φ = tan⁻¹(d/c)/1.5
    wtf = d cos φ - (c - sc - st) sin φ,  s = (2/sin φ)[Mfr/(fyw tw)]^0.5 <= c for the compression and tension flanges

    Valid for webs with intermediate transverse stiffeners and c/d >= 1.0, the adjacent panels or end posts anchoring
    the tension field.

    Args:
        d_mm: Depth of the web (mm)
        tw_mm: Thickness of the web (mm)
        c_mm: Spacing of the transverse stiffeners (mm)
        fyw: Yield stress of the web (MPa)
        Av_cm2: Shear area (cm²)
        Mfr_c_kNm, Mfr_t_kNm: Reduced plastic moments of the compression and tension flanges (kNm), see
            flange_reduced_plastic_moment()
        E: Modulus of elasticity (MPa)
    """
    d, t, c = _require_positive(d_mm, "d_mm"), _require_positive(tw_mm, "tw_mm"), _require_positive(c_mm, "c_mm")
    if c / d < 1.0:
        raise ValueError("The tension field method needs c/d >= 1.0 (15.4.2.2 b)).")
    Kv: float = shear_buckling_coefficient(c / d)
    tau_b: float = shear_buckling_stress(web_shear_slenderness(d / t, fyw, Kv, E), fyw)
    phi: float = math.atan(d / c) / 1.5
    psi: float = 1.5 * tau_b * math.sin(2.0 * phi)
    f_v: float = math.sqrt(max(fyw**2 - 3.0 * tau_b**2 + psi**2, 0.0)) - psi
    s_c: float = min(2.0 / math.sin(phi) * math.sqrt(max(Mfr_c_kNm, 0.0) * 1e6 / (fyw * t)), c)
    s_t: float = min(2.0 / math.sin(phi) * math.sqrt(max(Mfr_t_kNm, 0.0) * 1e6 / (fyw * t)), c)
    w_tf: float = d * math.cos(phi) - (c - s_c - s_t) * math.sin(phi)
    A_v: float = Av_cm2 * 100.0
    V_p: float = A_v * fyw / math.sqrt(3.0)
    return min(A_v * tau_b + 0.9 * max(w_tf, 0.0) * t * f_v * math.sin(phi), V_p) / 1e3


class ShearResult(BaseModel):
    # 15.4 Shear: Vd = Vn/γm0, Vn = Vp (15.4.1) or the shear buckling resistance (15.4.2)
    Vd: float # kN
    Vn: float # kN
    Vp: float # kN; Av fyw/√3
    Av: float # cm²
    axis: BendingAxis
    fyw: float # MPa
    d_tw: Optional[float] = None # web slenderness, where a web carries the shear
    shear_buckling: bool = False # 15.4.2.1
    Kv: Optional[float] = None
    lambda_w: Optional[float] = None
    tau_b: Optional[float] = None # MPa
    Vcr: Optional[float] = None # kN; simple post-critical method, Av τb
    Vtf: Optional[float] = None # kN; tension field method
    method: str # "15.4.1", "15.4.2.2 a)" or "15.4.2.2 b)"
    V: Optional[float] = None # kN
    high_shear: Optional[bool] = None # 16.2: V > 0.6 Vd
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.SHEAR_YIELDING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_shear(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    V_kN: Optional[float] = None,
    axis: BendingAxis = "z",
    welded: bool = False,
    c_mm: Optional[float] = None,
    method: Literal["post_critical", "tension_field"] = "post_critical",
    Nf_kN: float = 0.0,
    Av_cm2: Optional[float] = None,
    Avn_cm2: Optional[float] = None,
    fu_mpa: Optional[float] = None,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ShearResult:
    """IS 800:2025 15.4: Design shear strength Vd = Vn/γm0.

    15.4.1: Vn = Vp = Av fyw/√3, with the shear areas of shear_area(). Webs of I and channel sections loaded parallel to
    the web, and the webs of RHS, are checked for shear buckling where d/tw > 67εw (15.4.2.1), d the depth of the web
    clear between the flanges; then Vn is the lesser of Vp and
        a) the simple post-critical method, Vcr = Av τb (the web stiffened at the supports), or
        b) the tension field method, Vtf (intermediate stiffeners at c_mm, c/d >= 1.0).
    fyw defaults to Table 1 for the web thickness. With Avn_cm2, fastener holes reduce Av to the area that satisfies
    Avn >= (fy/fu)(γm1/γm0)Av/0.9 where they are not negligible (15.4.1.1 NOTE).

    Args:
        section: IN section
        fy_mpa: Yield stress of the web (MPa); defaults to Table 1 for `steel_grade` and the web thickness
        steel_grade: IS 2062 grade
        V_kN: Factored shear (kN)
        axis: Axis of bending, "z" (shear parallel to the web) or "y" (parallel to the flanges)
        welded: Welded section, for the shear area
        c_mm: Spacing of intermediate transverse stiffeners (mm); none by default
        method: "post_critical" or "tension_field"
        Nf_kN: Axial force in the flanges, for Mfr of the tension field method (kN)
        Av_cm2: Shear area (cm²); overrides shear_area()
        Avn_cm2: Net shear area at fastener holes (cm²), 15.4.1.1 NOTE
        fu_mpa: Ultimate stress (MPa), for Avn; defaults to Table 1 for `steel_grade`
        E: Modulus of elasticity (MPa)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    t_web: float = data.get("tw", 0.0)
    fyw: float = _require_positive(fy_mpa, "fy_mpa") if fy_mpa is not None else (yield_stress(t_web, steel_grade) if t_web > 0.0 else _design_strength(None, steel_grade, data))
    A_v: float = _require_positive(Av_cm2, "Av_cm2") if Av_cm2 is not None else _shear_area(family, data, axis, welded)
    notes: list[str] = []
    if Avn_cm2 is not None:
        fu: float = _ultimate_strength(fu_mpa, steel_grade)
        if not shear_holes_negligible(Avn_cm2, A_v, fyw, fu):
            A_v = 0.9 * _require_positive(Avn_cm2, "Avn_cm2") * (fu / fyw) * (GAMMA_M0 / GAMMA_M1)
            notes.append(f"15.4.1.1 NOTE: fastener holes reduce the shear area to {A_v:.2f} cm².")
    V_p: float = A_v * 100.0 * fyw / math.sqrt(3.0) / 1e3 # 15.4.1

    d: Optional[float] = None
    if family in ("I", "channel") and axis == "z":
        d = _get(data, "D") - 2.0 * _get(data, "tf")
    elif family == "RHS":
        d = (_get(data, "D") if axis == "z" else _get(data, "B")) - 3.0 * _get(data, "tw")
    d_tw: Optional[float] = d / t_web if (d is not None and t_web > 0.0) else None
    Kv: Optional[float] = shear_buckling_coefficient(c_mm / d) if (c_mm is not None and d is not None) else None
    buckling: bool = d_tw is not None and shear_buckling_required(d_tw, fyw, Kv)
    V_n: float = V_p
    lambda_w, tau_b, V_cr, V_tf = None, None, None, None
    clause: str = "15.4.1"
    if buckling and d is not None and d_tw is not None:
        Kv_used: float = Kv if Kv is not None else 5.35
        lambda_w = web_shear_slenderness(d_tw, fyw, Kv_used, E)
        tau_b = shear_buckling_stress(lambda_w, fyw)
        V_cr = A_v * 100.0 * tau_b / 1e3 # 15.4.2.2 a): Av τb
        V_n, clause = min(V_cr, V_p), "15.4.2.2 a)"
        notes.append("The simple post-critical method needs transverse stiffeners at the supports.")
        if method == "tension_field":
            if c_mm is None or family not in ("I", "channel"):
                raise ValueError("The tension field method needs an I or channel web with intermediate stiffeners (c_mm).")
            M_fr: float = flange_reduced_plastic_moment(_get(data, "B"), _get(data, "tf"), fyw, Nf_kN)
            V_tf = tension_field_shear_resistance(d, t_web, c_mm, fyw, A_v, M_fr, M_fr, E)
            V_n, clause = V_tf, "15.4.2.2 b)"
    V_d: float = V_n / GAMMA_M0

    return ShearResult(
        Vd=V_d,
        Vn=V_n,
        Vp=V_p,
        Av=A_v,
        axis=axis,
        fyw=fyw,
        d_tw=d_tw,
        shear_buckling=buckling,
        Kv=Kv if Kv is not None else (5.35 if buckling else None),
        lambda_w=lambda_w,
        tau_b=tau_b,
        Vcr=V_cr,
        Vtf=V_tf,
        method=clause,
        V=V_kN,
        high_shear=abs(V_kN) > 0.6 * V_d if V_kN is not None else None,
        utilisation=_utilisation_check(V_kN, V_d, clause, "Design shear strength") if V_kN is not None else None,
        limit_state=LimitState.SHEAR_BUCKLING if buckling else LimitState.SHEAR_YIELDING,
        reference=_reference("15.4", title="Shear"),
        metadata={"notes": notes} if notes else {},
    )


# --- 15.2.1 Laterally supported beams; 16.2 combined shear and bending ---
def tension_flange_holes_negligible(Anf_Agf: float, fy: float, fu: float) -> bool:
    """IS 800:2025 15.2.1.4 a): holes in the tension flange need not be considered where
    Anf/Agf >= (fy/fu)(γm1/γm0)/0.9; otherwise the effective flange area Aef satisfying it replaces Agf."""
    return Anf_Agf >= (fy / fu) * (GAMMA_M1 / GAMMA_M0) / 0.9


def shear_lag_negligible(b_mm: float, L0_mm: float, element: Literal["outstand", "internal"] = "outstand") -> bool:
    """IS 800:2025 15.2.1.5: shear lag in flanges may be disregarded where bo <= L0/20 (outstands) or bi <= L0/10
    (internal elements), L0 the length between points of zero moment."""
    return b_mm <= L0_mm / (20.0 if element == "outstand" else 10.0)


def high_shear_design_moment(Md: float, Mfd: float, V: float, Vd: float, Ze_cm3: float, fy: float, section_class: SectionClassInput = 1) -> float:
    """IS 800:2025 16.2.2: Design bending strength under high shear, V > 0.6 Vd (kNm).

    a) plastic or compact sections: Mdv = Md - β(Md - Mfd) <= 1.2 Ze fy/γm0, β = (2V/Vd - 1)²
    b) semi-compact sections: Mdv = Ze fy/γm0

    Args:
        Md: Plastic design moment of the whole section disregarding the high shear (kNm)
        Mfd: Plastic design strength of the section excluding the shear area (kNm)
        V, Vd: Factored shear and design shear strength (kN)
        Ze_cm3: Elastic section modulus of the whole section (cm³)
        fy: Yield stress (MPa)
        section_class: Class of the section
    """
    elastic: float = Ze_cm3 * fy / GAMMA_M0 / 1e3
    if not _is_plastic(_as_section_class(section_class)):
        return elastic
    beta: float = (2.0 * abs(V) / _require_positive(Vd, "Vd") - 1.0) ** 2
    return min(Md - beta * (Md - Mfd), 1.2 * elastic)


def _shear_area_modulus(family: str, data: dict[str, float], axis: BendingAxis, A_v: float, welded: bool) -> float:
    """Plastic modulus of the shear area about the axis of bending (cm³), for Mfd (16.2.2)."""
    if family in ("I", "channel"):
        if axis == "z":
            depth: float = _get(data, "D") - 2.0 * _get(data, "tf") if welded else _get(data, "D")
            return A_v * 100.0 * depth / 4.0 / 1e3
        return _get(data, "Zpy") - (_get(data, "D") - 2.0 * _get(data, "tf")) * _get(data, "tw") ** 2 / 4.0 / 1e3 # all but the web
    if family == "RHS":
        return A_v * 100.0 * (_get(data, "D") if axis == "z" else _get(data, "B")) / 4.0 / 1e3
    raise NotImplementedError(f"No Mfd rule for {family} sections; pass Mfd_kNm.")


class MomentCapacityResult(BaseModel):
    # 15.2.1 Design bending strength of a laterally supported beam, with high shear (15.2.1.3, 16.2.2)
    Md: float # kNm; Mdv under high shear
    axis: BendingAxis
    section_class: SectionClass # 10.8, in bending about `axis` (with P where given)
    fy: float # MPa
    beta_b: float # 15.2.1.2
    modulus: str # "Zp", "Ze" or "Zeff"
    W: float # cm³; βb Zp
    Zp: Optional[float] = None # cm³
    Ze: float # cm³
    Md_limit: float # kNm; 1.2 Ze fy/γm0 (1.5 for cantilevers)
    high_shear: bool = False # V > 0.6 Vd
    beta: Optional[float] = None # 16.2.2 a): (2V/Vd - 1)²
    Mfd: Optional[float] = None # kNm
    V: Optional[float] = None # kN
    Vd: Optional[float] = None # kN
    M: Optional[float] = None # kNm
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.PLASTIC_MOMENT_YIELDING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_bending(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    axis: BendingAxis = "z",
    M_kNm: Optional[float] = None,
    V_kN: float = 0.0,
    P_kN: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    cantilever: bool = False,
    welded: bool = False,
    Z_eff_cm3: Optional[float] = None,
    Mfd_kNm: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> MomentCapacityResult:
    """IS 800:2025 15.2.1: Design bending strength Md of a laterally supported beam about one axis.

    15.2.1.2, V <= 0.6Vd: Md = βb Zp fy/γm0 <= 1.2 Ze fy/γm0 (1.5 Ze fy/γm0 for cantilevers), βb = 1.0 (plastic, compact),
    Ze/Zp (semi-compact) or Zeff/Zp (slender, 15.2.2).
    15.2.1.3, V > 0.6Vd: Md = Mdv of 16.2.2, with Mfd from the plastic modulus less that of the shear area.

    Angles have no tabulated Zp, so plastic and compact angles take Ze, which is conservative. Webs with d/tw > 67ε need
    15.2.1.1 (flanges only, or combined shear and normal stresses in the web); the result then carries a note.

    Args:
        section: IN section; classified in bending about `axis` unless `section_class` is given
        fy_mpa: Yield stress (MPa); defaults to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade
        axis: "z" (major) or "y" (minor)
        M_kNm: Factored moment (kNm)
        V_kN: Co-existing shear (kN), parallel to the web for "z" and to the flanges for "y"
        P_kN: Co-existing axial compression (kN), for the classification of webs (Table 2 note 5)
        section_class: Class to use instead of classifying, e.g 2 or "semi-compact"
        cantilever: 15.2.1.2: 1.5 Ze fy/γm0 for cantilevers, else 1.2 Ze fy/γm0
        welded: Welded section, for the shear area
        Z_eff_cm3: Effective section modulus of a slender section (cm³); required for class 4
        Mfd_kNm: Plastic design strength excluding the shear area (kNm); overrides the section rule
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("z", "y"):
        raise ValueError("axis must be 'z' (major) or 'y' (minor).")
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    pattern: StressPattern = StressPattern.MAJOR_AXIS_BENDING if axis == "z" else StressPattern.MINOR_AXIS_BENDING
    axial: Optional[float] = P_kN if (P_kN and family != "CHS") else None
    if section_class is not None:
        cls: SectionClass = _as_section_class(section_class)
    else:
        cls = _classify(section_type, raw, fy, pattern, axial).section_class
    Z_p: Optional[float] = data.get(f"Zp{axis}")
    Z_e: float = _get(data, f"Ze{axis}")
    notes: list[str] = []

    if _is_plastic(cls):
        if Z_p is None:
            W, modulus, beta_b = Z_e, "Ze", 1.0
            notes.append("No plastic modulus is tabulated; Ze is used for a plastic or compact section, which is conservative.")
        else:
            W, modulus, beta_b = Z_p, "Zp", 1.0
    elif cls == SectionClass.CLASS_3:
        W, modulus = Z_e, "Ze"
        beta_b = Z_e / Z_p if Z_p else 1.0
    else:
        if Z_eff_cm3 is None:
            raise ValueError("Slender (class 4) section: pass Z_eff_cm3, the effective section modulus (15.2.2, 10.8.2 d)).")
        W, modulus = _require_positive(Z_eff_cm3, "Z_eff_cm3"), "Zeff"
        beta_b = W / Z_p if Z_p else 1.0
    M_d_limit: float = (1.5 if cantilever else 1.2) * Z_e * fy / GAMMA_M0 / 1e3 # 15.2.1.2
    M_d: float = min(W * fy / GAMMA_M0 / 1e3, M_d_limit)

    # 15.2.1.3 and 16.2.2 High shear
    high: bool = False
    beta, M_fd, V_d = None, None, None
    if V_kN:
        shear: ShearResult = check_shear(section, fy_mpa, steel_grade, V_kN, axis, welded, section_type=section_type, properties=properties)
        V_d = shear.Vd
        if abs(V_kN) > 0.6 * V_d:
            high = True
            if Mfd_kNm is not None:
                M_fd = Mfd_kNm
            elif _is_plastic(cls):
                Z_pv: float = _shear_area_modulus(family, data, axis, shear.Av, welded)
                M_fd = max((W - Z_pv) * fy / GAMMA_M0 / 1e3, 0.0)
            beta = (2.0 * abs(V_kN) / V_d - 1.0) ** 2
            if cls == SectionClass.CLASS_4:
                notes.append("16.2.2 covers plastic, compact and semi-compact sections; a slender section under high shear needs 15.2.1.1.")
            else:
                M_d = high_shear_design_moment(M_d, M_fd or 0.0, V_kN, V_d, Z_e, fy, cls)
    if axis == "z" and family in ("I", "channel") and "tw" in data and "D" in data and "tf" in data:
        d_tw: float = (data["D"] - 2.0 * data["tf"]) / data["tw"]
        if d_tw > 67.0 * epsilon(fy):
            notes.append(f"d/tw = {d_tw:.1f} > 67ε: the web is susceptible to shear buckling; see 15.2.1.1.")

    return MomentCapacityResult(
        Md=M_d,
        axis=axis,
        section_class=cls,
        fy=fy,
        beta_b=beta_b,
        modulus=modulus,
        W=W,
        Zp=Z_p,
        Ze=Z_e,
        Md_limit=M_d_limit,
        high_shear=high,
        beta=beta,
        Mfd=M_fd,
        V=V_kN or None,
        Vd=V_d,
        M=M_kNm,
        utilisation=_utilisation_check(M_kNm, M_d, "16.2.2" if high else "15.2.1.2", "Design bending strength") if M_kNm is not None else None,
        reference=_reference("16.2.2" if high else "15.2.1.2", title="Design bending strength, laterally supported"),
        metadata={"notes": notes} if notes else {},
    )


# --- 15.3 Effective length for lateral torsional buckling ---
def beam_effective_length(L: float, restraint: str = "no_warping_restraint", loading: Loading = "normal", D: Optional[float] = None) -> float:
    """IS 800:2025 15.3.1 and Table 15: Effective length LLT of a simply supported beam (mm).

    Args:
        L: Span (mm); between points of inflection for continuous beams (note 4)
        restraint: BEAM_EFFECTIVE_LENGTHS key, rows i) to vii)
        loading: "normal" or "destabilizing"
        D: Overall depth of the beam (mm), for rows vi) and vii)
    """
    if restraint not in BEAM_EFFECTIVE_LENGTHS:
        raise ValueError(f"Unknown restraint '{restraint}'; expected one of {', '.join(BEAM_EFFECTIVE_LENGTHS)}.")
    normal, destabilizing, plus_2D = BEAM_EFFECTIVE_LENGTHS[restraint]
    length: float = (destabilizing if loading == "destabilizing" else normal) * _require_positive(L, "L")
    return length + 2.0 * _require_positive(D, "D") if plus_2D else length


def segment_effective_length(L: float, loading: Loading = "normal", partial: bool = False) -> float:
    """IS 800:2025 15.3.1 and 15.3.2: Effective length LLT of a segment between intermediate lateral restraints (mm).

    L, the distance between the restraints (15.3.2), times 1.2 for destabilizing loading (15.3.2) and 1.2 for partial
    lateral restraints (15.3.1); both factors apply together.
    """
    factor: float = (1.2 if loading == "destabilizing" else 1.0) * (1.2 if partial else 1.0)
    return factor * _require_positive(L, "L")


def cantilever_effective_length(L: float, support: str = "continuous_lateral", tip: str = "free", loading: Loading = "normal") -> float:
    """IS 800:2025 15.3.3 and Table 16: Effective length LLT of a cantilever of projecting length L (mm).

    Args:
        L: Projecting length (mm)
        support: a) "continuous_lateral", b) "continuous_partial_torsional", c) "continuous_lateral_torsional" or
            d) "built_in" (restrained laterally, torsionally and against rotation on plan)
        tip: i) "free", ii) "lateral", iii) "torsional" or iv) "lateral_torsional" restraint at the top
        loading: "normal" or "destabilizing"
    """
    if support not in CANTILEVER_EFFECTIVE_LENGTHS or tip not in CANTILEVER_EFFECTIVE_LENGTHS[support]:
        raise ValueError(f"Unknown support '{support}' or tip '{tip}'; see CANTILEVER_EFFECTIVE_LENGTHS.")
    normal, destabilizing = CANTILEVER_EFFECTIVE_LENGTHS[support][tip]
    return (destabilizing if loading == "destabilizing" else normal) * _require_positive(L, "L")


# --- 15.2.2 Laterally unsupported beams ---
def elastic_critical_moment(Iy_cm4: float, It_cm4: float, Iw_cm6: float, LLT_mm: float, E: float = E_STEEL, G: float = G_STEEL) -> float:
    """IS 800:2025 15.2.2.1: Mcr = {(π²E Iy/LLT²)[G It + π²E Iw/LLT²]}^0.5 of a simply supported, prismatic, symmetric
    member (kNm), Iy about the minor axis."""
    L: float = _require_positive(LLT_mm, "LLT_mm")
    Iy: float = _require_positive(Iy_cm4, "Iy_cm4") * 1e4
    return math.sqrt(math.pi**2 * E * Iy / L**2 * (G * It_cm4 * 1e4 + math.pi**2 * E * Iw_cm6 * 1e6 / L**2)) / 1e6


def critical_bending_stress(LLT_mm: float, ry_mm: float, hf_mm: float, tf_mm: float, E: float = E_STEEL) -> float:
    """IS 800:2025 15.2.2.1: fcr,b = [1.1π²E/(LLT/ry)²][1 + (1/20)((LLT/ry)/(hf/tf))²]^0.5 of non-slender rolled sections
    (MPa); Mcr = βb Zp fcr,b.

    Args:
        LLT_mm: Effective length for lateral torsional buckling (mm)
        ry_mm: Radius of gyration about the minor axis (mm)
        hf_mm: Centre to centre distance between the flanges (mm)
        tf_mm: Thickness of the flange (mm)
        E: Modulus of elasticity (MPa)
    """
    slenderness: float = _require_positive(LLT_mm, "LLT_mm") / _require_positive(ry_mm, "ry_mm")
    return 1.1 * math.pi**2 * E / slenderness**2 * math.sqrt(1.0 + (slenderness / (_require_positive(hf_mm, "hf_mm") / _require_positive(tf_mm, "tf_mm"))) ** 2 / 20.0)


def annex_e_constants(case: float | str = 1.0, K: float = 1.0) -> tuple[float, float, float]:
    """IS 800:2025 Annex E and Table 42: (c1, c2, c3) for the loading and the effective length factor K.

    Args:
        case: ψ of end moments M and ψM (-1 <= ψ <= 1, interpolated linearly between the tabulated values), or a
            transverse load: "udl_simply_supported", "udl_fixed_ends", "point_load_simply_supported",
            "point_load_fixed_ends" or "two_point_loads"
        K: Effective length factor, 1.0, 0.7 or 0.5 (end moments) or 1.0 or 0.5 (transverse loads)
    """
    if isinstance(case, str):
        if case not in ANNEX_E_TRANSVERSE_LOAD_CONSTANTS:
            raise ValueError(f"Unknown case '{case}'; expected a ψ or one of {', '.join(ANNEX_E_TRANSVERSE_LOAD_CONSTANTS)}.")
        by_K: dict[float, tuple[float, float, float]] = ANNEX_E_TRANSVERSE_LOAD_CONSTANTS[case]
        if K not in by_K:
            raise ValueError(f"Table 42 gives K = {', '.join(str(k) for k in by_K)} for {case}.")
        return by_K[K]
    psi: float = float(case)
    if not -1.0 <= psi <= 1.0:
        raise ValueError("ψ must lie between -1 and 1.")
    if K not in (1.0, 0.7, 0.5):
        raise ValueError("Table 42 gives K = 1.0, 0.7 or 0.5 for end moments.")
    points: list[float] = sorted(ANNEX_E_END_MOMENT_CONSTANTS)
    for low, high in zip(points, points[1:]):
        if low <= psi <= high:
            c1_low, c3_low = ANNEX_E_END_MOMENT_CONSTANTS[low][K]
            c1_high, c3_high = ANNEX_E_END_MOMENT_CONSTANTS[high][K]
            share: float = (psi - low) / (high - low)
            return c1_low + share * (c1_high - c1_low), 0.0, c3_low + share * (c3_high - c3_low)
    raise ValueError("ψ out of range.") # pragma: no cover


def monosymmetry_constant(beta_f: float, hy_mm: float, lipped: bool = False, hL_mm: float = 0.0, h_mm: Optional[float] = None) -> float:
    """IS 800:2025 E-1.2: approximation of yj (mm).

    a) plain flanges: yj = 0.8(2βf - 1)hy/2 (βf > 0.5) or 1.0(2βf - 1)hy/2 (βf <= 0.5)
    b) lipped flanges: yj = 0.8(2βf - 1)(1 + hL/h)hy/2 (βf > 0.5) or (2βf - 1)(1 + hL/h)hy/2 (βf <= 0.5)

    βf = Ifc/(Ifc + Ift), Ifc and Ift about the minor axis of the compression and tension flanges; hy the distance
    between the shear centres of the two flanges; hL the height of the lip and h the overall height.
    """
    factor: float = 0.8 if beta_f > 0.5 else 1.0
    lip: float = 1.0 + (hL_mm / _require_positive(h_mm, "h_mm") if lipped else 0.0)
    return factor * (2.0 * beta_f - 1.0) * lip * hy_mm / 2.0


def warping_constant_mono_i(beta_f: float, Iy_cm4: float, hy_mm: float) -> float:
    """IS 800:2025 E-1.2: Iw = (1 - βf)βf Iy hy² of an I-section monosymmetric about the minor axis (cm⁶)."""
    return (1.0 - beta_f) * beta_f * Iy_cm4 * 1e4 * hy_mm**2 / 1e6


def elastic_critical_moment_general(
    Iy_cm4: float,
    It_cm4: float,
    Iw_cm6: float,
    L_mm: float,
    c1: float = 1.0,
    c2: float = 0.0,
    c3: float = 0.0,
    K: float = 1.0,
    Kw: float = 1.0,
    yg_mm: float = 0.0,
    yj_mm: float = 0.0,
    E: float = E_STEEL,
    G: float = G_STEEL,
) -> float:
    """IS 800:2025 E-1.2: Elastic critical moment of a section symmetric about the minor axis (kNm).

    Mcr = c1 (π²E Iy/LLT²){[(K/Kw)² Iw/Iy + G It LLT²/(π²E Iy) + (c2 yg - c3 yj)²]^0.5 - (c2 yg - c3 yj)}

    with LLT = K L. For a doubly symmetric section with K = Kw = 1.0, c1 = 1 and the load at the shear centre, this is
    the Mcr of 15.2.2.1.

    Args:
        Iy_cm4: Second moment of area about the minor axis (cm⁴)
        It_cm4: St. Venant's torsion constant (cm⁴)
        Iw_cm6: Warping constant (cm⁶)
        L_mm: Unsupported length (mm)
        c1, c2, c3: Table 42, see annex_e_constants()
        K: Effective length factor about the weak axis, 0.5 (complete restraint) to 1.0 (free)
        Kw: Warping restraint factor, 1.0 unless warping is restrained at the lateral supports
        yg_mm: Distance of the point of application of the load from the shear centre (mm), positive when the load acts
            towards the shear centre from its point of application (e.g gravity load on the top flange)
        yj_mm: Monosymmetry constant (mm), see monosymmetry_constant(); 0 for doubly symmetric sections
        E, G: Moduli (MPa)
    """
    L_LT: float = K * _require_positive(L_mm, "L_mm")
    Iy: float = _require_positive(Iy_cm4, "Iy_cm4") * 1e4
    Iw: float = Iw_cm6 * 1e6
    It: float = It_cm4 * 1e4
    offset: float = c2 * yg_mm - c3 * yj_mm
    root: float = math.sqrt((K / Kw) ** 2 * Iw / Iy + G * It * L_LT**2 / (math.pi**2 * E * Iy) + offset**2)
    return c1 * math.pi**2 * E * Iy / L_LT**2 * (root - offset) / 1e6


def lateral_torsional_imperfection_factor(
    shape: str = "rolled_I",
    h_mm: Optional[float] = None,
    b_mm: Optional[float] = None,
    tf_mm: Optional[float] = None,
    Zez_cm3: Optional[float] = None,
    Zey_cm3: Optional[float] = None,
) -> float:
    """IS 800:2025 15.2.2 and Table 13: Imperfection parameter αLT.

    - "rolled_I": h/b > 1.2: 0.12(Zez/Zey)^0.5 <= 0.34 (tf <= 40 mm) or 0.16(Zez/Zey)^0.5 <= 0.49 (tf > 40 mm);
      h/b <= 1.2: 0.12(Zez/Zey)^0.5 <= 0.34
    - "welded_I": 0.12(Zez/Zey)^0.5 <= 0.34 for either thickness, as printed (EN 1993-1-1:2022 Table 8.5 has
      0.21/0.64 and 0.25/0.76)
    - "rolled_unequal_I": 0.21 (h/bmin <= 2.0) or 0.34; "welded_unequal_I": 0.49 or 0.76; b the smaller flange (note)
    - "other_rolled" (channels, tees): 0.76

    Args:
        shape: "rolled_I", "welded_I", "rolled_unequal_I", "welded_unequal_I" or "other_rolled"
        h_mm: Overall depth (mm)
        b_mm: Flange width, the smaller of the two for unequal flanges (mm)
        tf_mm: Flange thickness (mm)
        Zez_cm3, Zey_cm3: Elastic section moduli about z-z and y-y (cm³)
    """
    match shape:
        case "rolled_I" | "welded_I":
            ratio: float = math.sqrt(_require_positive(Zez_cm3, "Zez_cm3") / _require_positive(Zey_cm3, "Zey_cm3"))
            if shape == "rolled_I" and _require_positive(h_mm, "h_mm") / _require_positive(b_mm, "b_mm") > 1.2 and _require_positive(tf_mm, "tf_mm") > 40.0:
                return min(0.16 * ratio, 0.49)
            return min(0.12 * ratio, 0.34)
        case "rolled_unequal_I":
            return 0.21 if _require_positive(h_mm, "h_mm") / _require_positive(b_mm, "b_mm") <= 2.0 else 0.34
        case "welded_unequal_I":
            return 0.49 if _require_positive(h_mm, "h_mm") / _require_positive(b_mm, "b_mm") <= 2.0 else 0.76
        case "other_rolled":
            return 0.76
    raise ValueError(f"Unknown shape '{shape}'; expected rolled_I, welded_I, rolled_unequal_I, welded_unequal_I or other_rolled.")


def moment_gradient_factor(case: str = "uniform", psi: float = 1.0, M0_Mh: Optional[float] = None) -> float:
    """IS 800:2025 15.2.2 and Table 14: Moment gradient effect parameter fm.

    - "uniform": 1.0
    - "end_moments", M and ψM with -1 <= ψ <= 1: 1.25 - 0.1ψ - 0.15ψ²
    - "udl": 1.05; "point_load" (at mid-span): 1.10
    - "udl_with_end_moments" (both ends): 1.0 + 1.35r - 0.33r³ for 0 <= r < 2.0, else 1.05
    - "udl_with_end_moment" (one end): 1.25 + 0.5r² - 0.275r⁴ for 0 <= r < 1.47, else 1.05
    - "point_load_with_end_moments": 1.0 + 1.25r - 0.30r³ for 0 <= r < 2.0, else 1.10
    - "point_load_with_end_moment": 1.25 + 0.325r² - 0.175r⁴ for 0 <= r < 1.5, else 1.10

    with r = M0/Mh, M0 the free moment at mid-span of the simply supported member and Mh the end (hogging) moment. The
    draft covers r >= 0 only; for r < 0, fm = 1.0 (conservative, EN 1993-1-1:2022 8.3.2.3).
    """
    match case:
        case "uniform":
            return 1.0
        case "end_moments":
            if not -1.0 <= psi <= 1.0:
                raise ValueError("ψ must lie between -1 and 1.")
            return 1.25 - 0.1 * psi - 0.15 * psi**2
        case "udl":
            return 1.05
        case "point_load":
            return 1.10
    if case not in ("udl_with_end_moments", "udl_with_end_moment", "point_load_with_end_moments", "point_load_with_end_moment"):
        raise ValueError(f"Unknown case '{case}'; see moment_gradient_factor() for the Table 14 cases.")
    if M0_Mh is None:
        raise ValueError(f"'{case}' needs M0_Mh, the ratio of the free moment to the end moment.")
    r: float = M0_Mh
    if r < 0.0:
        return 1.0
    match case:
        case "udl_with_end_moments":
            return 1.0 + 1.35 * r - 0.33 * r**3 if r < 2.0 else 1.05
        case "udl_with_end_moment":
            return 1.25 + 0.5 * r**2 - 0.275 * r**4 if r < 1.47 else 1.05
        case "point_load_with_end_moments":
            return 1.0 + 1.25 * r - 0.30 * r**3 if r < 2.0 else 1.10
    return 1.25 + 0.325 * r**2 - 0.175 * r**4 if r < 1.5 else 1.10


def lateral_torsional_reduction_factor(lambda_LT: float, alpha_LT: float, fm: float = 1.0, lambda_y: Optional[float] = None) -> float:
    """IS 800:2025 15.2.2: Bending stress reduction factor χLT for lateral torsional buckling.

    Doubly symmetric sections with lateral support at the ends (lambda_y given):
        χLT = fm/{φLT + [φLT² - fm λLT²]^0.5} <= 1.0
        φLT = 0.5[1 + fm((λLT/λy)² αLT(λy - 0.2) + λLT²)]
    Other sections (lambda_y None), which the draft does not cover: the IS 800:2007 form, as EN 1993-1-1:2022 8.3.2.3(2)
        χLT = 1/{φLT + [φLT² - λLT²]^0.5} <= 1.0,  φLT = 0.5[1 + αLT(λLT - 0.2) + λLT²]

    NOTE: the draft prints αLT(λLT - 0.2) in φLT; EN 1993-1-1:2022 Formula (8.82), which the draft adopts with Tables 13
    and 14 (and the same form in 14.1.2.2), has αLT(λy - 0.2), used here. As λLT < λy for rolled I-sections, this is
    also the conservative reading.

    Args:
        lambda_LT: Non-dimensional slenderness for lateral torsional buckling
        alpha_LT: Imperfection parameter, Table 13
        fm: Moment gradient effect parameter, Table 14
        lambda_y: Non-dimensional weak axis slenderness, (fy/fcry)^0.5, for the length between lateral supports
    """
    if lambda_LT < 0.0:
        raise ValueError("lambda_LT cannot be negative.")
    if lambda_y is None:
        phi: float = 0.5 * (1.0 + alpha_LT * (lambda_LT - 0.2) + lambda_LT**2)
        return min(1.0 / (phi + math.sqrt(max(phi**2 - lambda_LT**2, 0.0))), 1.0)
    lambda_y = _require_positive(lambda_y, "lambda_y")
    phi = 0.5 * (1.0 + fm * ((lambda_LT / lambda_y) ** 2 * alpha_LT * (lambda_y - 0.2) + lambda_LT**2))
    return min(fm / (phi + math.sqrt(max(phi**2 - fm * lambda_LT**2, 0.0))), 1.0)


class LateralTorsionalBucklingResult(BaseModel):
    # 15.2.2 Design bending strength of a laterally unsupported beam, Md = βb Zp fbd, fbd = χLT fy/γm0
    Md: float # kNm
    Md_supported: float # kNm; 15.2.1, which Md does not exceed
    fbd: Optional[float] = None # MPa
    chi_LT: Optional[float] = None
    lambda_LT: Optional[float] = None
    lambda_y: Optional[float] = None
    alpha_LT: Optional[float] = None # Table 13
    fm: float = 1.0 # Table 14
    Mcr: Optional[float] = None # kNm; 15.2.2.1
    fcrb: Optional[float] = None # MPa; approximate 15.2.2.1
    LLT: Optional[float] = None # mm
    beta_b: float
    section_class: SectionClass # 10.8, in major axis bending
    fy: float # MPa
    modulus: str # "Zp", "Ze" or "Zeff"
    W: float # cm³; βb Zp
    susceptible: bool = True # 15.2.2: False where the beam may be treated as laterally supported
    method: str # "15.2.2", or "15.2.2 b)" and "15.2.2 c)" where not susceptible
    Mz: Optional[float] = None # kNm
    utilisation: Optional[UtilisationCheck] = None
    limit_state: LimitState = LimitState.LATERAL_TORSIONAL_BUCKLING
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_lateral_torsional_buckling(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    LLT_mm: Optional[float] = None,
    Mz_kNm: Optional[float] = None,
    fm: float = 1.0,
    Ly_mm: Optional[float] = None,
    Mcr_kNm: Optional[float] = None,
    approximate: bool = False,
    alpha_LT: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    P_kN: Optional[float] = None,
    cantilever: bool = False,
    welded: bool = False,
    Z_eff_cm3: Optional[float] = None,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> LateralTorsionalBucklingResult:
    """IS 800:2025 15.2.2: Design bending strength of a laterally unsupported beam bent about its major axis.

    Md = βb Zp fbd, fbd = χLT fy/γm0, λLT = (βb Zp fy/Mcr)^0.5 <= (1.2 Ze fy/Mcr)^0.5, and Md <= the laterally supported
    Md of 15.2.1. Mcr is from 15.2.2.1 with It and Iw, or from the approximate fcr,b of non-slender rolled sections
    (`approximate`, or where It and Iw are missing); or pass Mcr_kNm, e.g from elastic_critical_moment_general().

    - I-sections: χLT from the doubly symmetric formula with fm (Table 14) and λy = (fy/fcry)^0.5, fcry for the distance
      between the lateral supports of the compression flange (Ly_mm, LLT_mm by default); αLT from Table 13
    - Channels: the general formula with αLT = 0.76 (Table 13, other rolled sections); fm is not applied. The 15.2.2.1
      Mcr may be used for channels, conservatively
    - Hollow sections are treated as laterally supported (15.2.2 b)), as is any beam with λLT < 0.4 (15.2.2 c))

    Args:
        section: IN section; classified in major axis bending unless `section_class` is given
        fy_mpa: Yield stress (MPa); defaults to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade
        LLT_mm: Effective length for lateral torsional buckling (mm), 15.3; see beam_effective_length()
        Mz_kNm: Maximum factored major axis moment in the segment (kNm)
        fm: Moment gradient effect parameter, Table 14; see moment_gradient_factor()
        Ly_mm: Distance between the lateral supports of the compression flange (mm), for λy; LLT_mm by default
        Mcr_kNm: Elastic lateral torsional buckling moment (kNm); overrides 15.2.2.1
        approximate: Use fcr,b of 15.2.2.1 for Mcr
        alpha_LT: Imperfection parameter; overrides Table 13
        section_class: Class to use instead of classifying
        P_kN: Co-existing axial compression (kN), for the classification
        cantilever: 1.5 Ze fy/γm0 limit of 15.2.1.2 (1.2 otherwise)
        welded: Welded I-section, for Table 13
        Z_eff_cm3: Effective modulus of a slender section (cm³)
        E, G: Moduli (MPa)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    capacity: MomentCapacityResult = check_bending(
        section, fy_mpa, steel_grade, "z", None, 0.0, P_kN, section_class, cantilever, welded, Z_eff_cm3, None, section_type, properties,
    )
    fy: float = capacity.fy
    W: float = capacity.W # βb Zp, cm³
    notes: list[str] = list(capacity.metadata.get("notes", []))
    common: dict[str, Any] = {
        "Md_supported": capacity.Md,
        "fm": fm,
        "LLT": LLT_mm,
        "beta_b": capacity.beta_b,
        "section_class": capacity.section_class,
        "fy": fy,
        "modulus": capacity.modulus,
        "W": W,
        "Mz": Mz_kNm,
    }
    M_d: float = capacity.Md
    f_bd, chi_LT, lambda_LT, lambda_y, alpha, M_cr, f_crb = None, None, None, None, None, None, None
    susceptible: bool = True
    method: str = "15.2.2"

    if family in ("RHS", "CHS"):
        susceptible, method = False, "15.2.2 b)"
    else:
        if family not in ("I", "channel") and Mcr_kNm is None:
            raise NotImplementedError(f"15.2.2.1 gives no Mcr for {family} sections; pass Mcr_kNm (and alpha_LT).")
        L_LT: float = _require_positive(LLT_mm, "LLT_mm")
        r_y: float = _radius(data, "y")
        if Mcr_kNm is not None:
            M_cr = _require_positive(Mcr_kNm, "Mcr_kNm")
        elif approximate or "It" not in data or "Iw" not in data:
            if not approximate:
                notes.append("It or Iw not available: Mcr = βb Zp fcr,b with the approximate fcr,b of 15.2.2.1.")
            T: float = _get(data, "tf")
            f_crb = critical_bending_stress(L_LT, r_y, _get(data, "D") - T, T, E)
            M_cr = W * f_crb / 1e3
        else:
            M_cr = elastic_critical_moment(_get(data, "Iy"), data["It"], data["Iw"], L_LT, E, G)
        lambda_LT = min(math.sqrt(W * fy / 1e3 / M_cr), math.sqrt(1.2 * capacity.Ze * fy / 1e3 / M_cr))
        if L_LT / r_y > MAXIMUM_SLENDERNESS["compression_flange"]:
            notes.append(f"Table 3: LLT/ry = {L_LT / r_y:.0f} exceeds 300 for the compression flange of a beam.")
        if lambda_LT < 0.4:
            susceptible, method = False, "15.2.2 c)"
        else:
            if alpha_LT is not None:
                alpha = alpha_LT
            elif family == "I":
                alpha = lateral_torsional_imperfection_factor("welded_I" if welded else "rolled_I", data.get("D"), data.get("B"), data.get("tf"), _get(data, "Zez"), _get(data, "Zey"))
            else:
                alpha = lateral_torsional_imperfection_factor("other_rolled")
            if family == "I":
                lambda_y = non_dimensional_slenderness((Ly_mm if Ly_mm is not None else L_LT) / r_y, fy, E)
                chi_LT = lateral_torsional_reduction_factor(lambda_LT, alpha, fm, lambda_y)
            else:
                chi_LT = lateral_torsional_reduction_factor(lambda_LT, alpha)
                if fm != 1.0:
                    notes.append("fm (Table 14) applies to doubly symmetric sections only; not applied.")
            f_bd = chi_LT * fy / GAMMA_M0
            M_d = min(W * f_bd / 1e3, capacity.Md)

    return LateralTorsionalBucklingResult(
        Md=M_d,
        fbd=f_bd,
        chi_LT=chi_LT,
        lambda_LT=lambda_LT,
        lambda_y=lambda_y,
        alpha_LT=alpha,
        Mcr=M_cr,
        fcrb=f_crb,
        susceptible=susceptible,
        method=method,
        utilisation=_utilisation_check(Mz_kNm, M_d, method, "Lateral torsional buckling") if Mz_kNm is not None else None,
        reference=_reference("15.2.2", title="Laterally unsupported beams"),
        metadata={"notes": notes} if notes else {},
        **common,
    )


# --- 16 Members subjected to combined forces ---
def reduced_flexural_strength(
    shape: str,
    n: float,
    Mdy: float,
    Mdz: float,
    A_cm2: Optional[float] = None,
    b_mm: Optional[float] = None,
    tf_mm: Optional[float] = None,
    h_mm: Optional[float] = None,
    tw_mm: Optional[float] = None,
) -> tuple[float, float]:
    """IS 800:2025 16.3.1.2: Reduced flexural strengths (Mndy, Mndz) of plastic and compact sections without bolt holes
    under the axial force ratio n = N/Nd (kNm).

    a) "plate": Mnd = Md(1 - n²)
    b) "welded_I": Mndy = Mdy[1 - ((n - a)/(1 - a))²] <= Mdy for n >= a; Mndz = Mdz(1 - n)/(1 - 0.5a) <= Mdz;
       a = (A - 2b tf)/A <= 0.5
    c) "rolled_I" (standard I or H): Mndz = 1.11 Mdz(1 - n) <= Mdz; Mndy = Mdy for n <= 0.2, else 1.56 Mdy(1 - n)(n + 0.6)
    d) "RHS" (and welded box sections, symmetric about both axes): Mndy = Mdy(1 - n)/(1 - 0.5af) <= Mdy,
       Mndz = Mdz(1 - n)/(1 - 0.5aw) <= Mdz; aw = (A - 2b tf)/A <= 0.5, af = (A - 2h tw)/A <= 0.5
    e) "CHS": Mnd = 1.04 Md(1 - n^1.7) <= Md

    Args:
        shape: "plate", "welded_I", "rolled_I", "RHS" or "CHS"
        n: N/Nd
        Mdy, Mdz: Design bending strengths about y-y and z-z (kNm)
        A_cm2: Area (cm²); b), d)
        b_mm, tf_mm: Width and thickness of the flanges (mm); b), d)
        h_mm, tw_mm: Depth and web thickness (mm); d)
    """
    n = min(abs(n), 1.0)
    match shape:
        case "plate":
            return Mdy * (1.0 - n**2), Mdz * (1.0 - n**2)
        case "rolled_I":
            M_ndy: float = Mdy if n <= 0.2 else min(1.56 * Mdy * (1.0 - n) * (n + 0.6), Mdy)
            return M_ndy, min(1.11 * Mdz * (1.0 - n), Mdz)
        case "welded_I":
            A: float = _require_positive(A_cm2, "A_cm2") * 100.0
            a: float = min((A - 2.0 * _require_positive(b_mm, "b_mm") * _require_positive(tf_mm, "tf_mm")) / A, 0.5)
            M_ndy = Mdy * (1.0 - ((n - a) / (1.0 - a)) ** 2) if n >= a else Mdy
            return min(M_ndy, Mdy), min(Mdz * (1.0 - n) / (1.0 - 0.5 * a), Mdz)
        case "RHS":
            A = _require_positive(A_cm2, "A_cm2") * 100.0
            a_w: float = min((A - 2.0 * _require_positive(b_mm, "b_mm") * _require_positive(tf_mm, "tf_mm")) / A, 0.5)
            a_f: float = min((A - 2.0 * _require_positive(h_mm, "h_mm") * _require_positive(tw_mm, "tw_mm")) / A, 0.5)
            return min(Mdy * (1.0 - n) / (1.0 - 0.5 * a_f), Mdy), min(Mdz * (1.0 - n) / (1.0 - 0.5 * a_w), Mdz)
        case "CHS":
            factor: float = 1.04 * (1.0 - n**1.7)
            return min(factor * Mdy, Mdy), min(factor * Mdz, Mdz)
    raise ValueError(f"Unknown shape '{shape}'; expected plate, welded_I, rolled_I, RHS or CHS.")


def interaction_exponents(shape: str, n: float) -> tuple[float, float]:
    """IS 800:2025 16.3.1.1 and Table 17: Constants (α1, α2) on My and Mz, n = N/Nd.

    "I" and "channel": 5n >= 1 and 2; "CHS": 2 and 2; "RHS": 1.66/(1 - 1.13n²) <= 6 for both; "solid_rectangle":
    1.73 + 1.8n³ for both.
    """
    n = abs(n)
    match shape:
        case "I" | "channel":
            return max(5.0 * n, 1.0), 2.0
        case "CHS":
            return 2.0, 2.0
        case "RHS":
            denominator: float = 1.0 - 1.13 * n**2
            value: float = min(1.66 / denominator, 6.0) if denominator > 0.0 else 6.0
            return value, value
        case "solid_rectangle":
            return 1.73 + 1.8 * n**3, 1.73 + 1.8 * n**3
    raise ValueError(f"Unknown shape '{shape}'; expected I, channel, CHS, RHS or solid_rectangle.")


def equivalent_uniform_moment_factor(
    psi: float = 1.0,
    alpha_s: Optional[float] = None,
    alpha_h: Optional[float] = None,
    loading: Literal["uniform", "concentrated"] = "uniform",
    sway: bool = False,
) -> float:
    """IS 800:2025 Table 18: Equivalent uniform moment factor Cmy, Cmz or CmLT, between the relevant braced points.

    - linear moment M to ψM: 0.6 + 0.4ψ >= 0.4
    - end moments Mh and ψMh with a span moment Ms, αs = Ms/Mh (|Mh| > |Ms|):
        0 <= αs <= 1: 0.2 + 0.8αs >= 0.4
        -1 <= αs < 0: ψ >= 0: 0.1 - 0.8αs (uniform), -0.8αs (concentrated); ψ < 0: 0.1(1 - ψ) - 0.8αs (uniform),
        0.2(1 - ψ) - 0.8αs (concentrated); all >= 0.4
    - span moment Ms with end moments Mh and ψMh, αh = Mh/Ms (|Ms| > |Mh|):
        0 <= αh <= 1: 0.95 - 0.05αh (uniform), 0.90 + 0.10αh (concentrated)
        -1 <= αh < 0: ψ >= 0: 0.95 + 0.05αh, 0.90 + 0.10αh; ψ < 0: 0.95 + 0.05αh(1 + 2ψ), 0.90 + 0.1αh(1 + 2ψ)
    - members with a sway buckling mode: Cmy = Cmz = 0.9

    NOTE: printed as in the draft; EN 1993-1-1 Table B.3, the source, has 0.2(-ψ) - 0.8αs and 0.95 + 0.05αh in the
    corresponding cells.

    Args:
        psi: End moment ratio ψ, -1 <= ψ <= 1
        alpha_s: αs = Ms/Mh, for the second diagram
        alpha_h: αh = Mh/Ms, for the third diagram
        loading: "uniform" or "concentrated" transverse loading
        sway: Member with a sway buckling mode (Cmy and Cmz)
    """
    if sway:
        return 0.9
    if not -1.0 <= psi <= 1.0:
        raise ValueError("ψ must lie between -1 and 1.")
    uniform: bool = loading == "uniform"
    if alpha_s is not None:
        if not -1.0 <= alpha_s <= 1.0:
            raise ValueError("αs must lie between -1 and 1.")
        if alpha_s >= 0.0:
            value: float = 0.2 + 0.8 * alpha_s
        elif psi >= 0.0:
            value = (0.1 if uniform else 0.0) - 0.8 * alpha_s
        else:
            value = (0.1 if uniform else 0.2) * (1.0 - psi) - 0.8 * alpha_s
        return max(value, 0.4)
    if alpha_h is not None:
        if not -1.0 <= alpha_h <= 1.0:
            raise ValueError("αh must lie between -1 and 1.")
        if alpha_h >= 0.0:
            return 0.95 - 0.05 * alpha_h if uniform else 0.90 + 0.10 * alpha_h
        spread: float = 1.0 if psi >= 0.0 else 1.0 + 2.0 * psi
        return 0.95 + 0.05 * alpha_h * spread if uniform else 0.90 + 0.10 * alpha_h * spread
    return max(0.6 + 0.4 * psi, 0.4)


class CombinedResult(BaseModel):
    # 16.3 Combined axial force and bending moment: section strength (16.3.1) and overall member strength (16.3.2)
    method: str # the cross-section check used: "16.3.1.1" or "16.3.1.3" (and the conservative linear form)
    section_class: Optional[SectionClass] = None # 10.8, under the moments (and the axial force)
    fy: float # MPa
    N: float = 0.0 # kN; P (compression) or T (tension)
    My: float = 0.0 # kNm; minor axis
    Mz: float = 0.0 # kNm; major axis
    Nd: Optional[float] = None # kN; Td, or Ag fy/γm0 in compression
    Mdy: Optional[float] = None # kNm; 15.2.1, with the co-existing shear
    Mdz: Optional[float] = None # kNm
    Mndy: Optional[float] = None # kNm; 16.3.1.2
    Mndz: Optional[float] = None # kNm
    alpha_1: Optional[float] = None # Table 17
    alpha_2: Optional[float] = None # Table 17
    Pdy: Optional[float] = None # kN; 14.1.2
    Pdz: Optional[float] = None # kN
    Md_LT: Optional[float] = None # kNm; 15.2.2
    Meff: Optional[float] = None # kNm; 16.3.2.1
    Ky: Optional[float] = None
    Kz: Optional[float] = None
    KLT: Optional[float] = None
    Cmy: float = 1.0 # Table 18
    Cmz: float = 1.0
    CmLT: float = 1.0
    ny: Optional[float] = None
    nz: Optional[float] = None
    utilisations: dict[str, float] # every check made
    governing: str
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _reduced_shape(family: str, welded: bool) -> Optional[str]:
    if family == "I":
        return "welded_I" if welded else "rolled_I"
    if family in ("RHS", "CHS"):
        return family
    return None # channels and angles: no 16.3.1.2 approximation


def _section_strength(
    family: str,
    cls: SectionClass,
    data: dict[str, float],
    welded: bool,
    N: float,
    N_d: float,
    My: float,
    Mz: float,
    M_dy: Optional[float],
    M_dz: Optional[float],
) -> tuple[dict[str, float], str, Optional[float], Optional[float], Optional[float], Optional[float]]:
    """16.3.1: cross-section checks; returns (checks, method, Mndy, Mndz, α1, α2)."""
    linear: float = compute_utilisation(N, N_d) + (compute_utilisation(My, M_dy) if My else 0.0) + (compute_utilisation(Mz, M_dz) if Mz else 0.0)
    if not _is_plastic(cls):
        return {"section (16.3.1.3)": linear}, "16.3.1.3", None, None, None, None
    checks: dict[str, float] = {"section, conservative (16.3.1.1)": linear}
    shape: Optional[str] = _reduced_shape(family, welded)
    if shape is None:
        return checks, "16.3.1.1 (conservative)", None, None, None, None
    n: float = compute_utilisation(N, N_d)
    M_ndy, M_ndz = reduced_flexural_strength(
        shape, n, M_dy or 0.0, M_dz or 0.0, data.get("A"), data.get("B"), data.get("tf"), data.get("D"), data.get("tw"),
    )
    alpha_1, alpha_2 = interaction_exponents("I" if family == "I" else family, n)
    exact: float = (compute_utilisation(My, M_ndy) ** alpha_1 if My else 0.0) + (compute_utilisation(Mz, M_ndz) ** alpha_2 if Mz else 0.0)
    if not My and not Mz:
        exact = n
    checks["section (16.3.1.1)"] = exact
    return checks, "16.3.1.1", M_ndy, M_ndz, alpha_1, alpha_2


def check_tension_and_bending(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    fu_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    T_kN: float = 0.0,
    My_kNm: float = 0.0,
    Mz_kNm: float = 0.0,
    Vy_kN: float = 0.0,
    Vz_kN: float = 0.0,
    An_cm2: Optional[float] = None,
    LLT_mm: Optional[float] = None,
    fm: float = 1.0,
    Ly_mm: Optional[float] = None,
    independent: bool = False,
    section_class: Optional[SectionClassInput] = None,
    cantilever: bool = False,
    welded: bool = False,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CombinedResult:
    """IS 800:2025 16.3.1 and 16.3.2.1: Members under axial tension and bending.

    16.3.1.1, plastic and compact: (My/Mndy)^α1 + (Mz/Mndz)^α2 <= 1.0 with 16.3.1.2 and Table 17, or conservatively
    N/Nd + My/Mdy + Mz/Mdz <= 1.0 (the smaller is the section result); 16.3.1.3, semi-compact: the linear form. Nd = Td
    (Section 13). 16.3.2.1, with LLT_mm: Meff = Mz - ψ T Zec/A <= Md of 15.2.2, ψ = 0.8 where T and M can vary
    independently, else 1.0.

    Args:
        section: IN section; classified in bending
        fy_mpa, fu_mpa: Yield and ultimate stress (MPa); default to Table 1
        steel_grade: IS 2062 grade
        T_kN: Factored tension (kN)
        My_kNm, Mz_kNm: Factored moments about the minor and major axes (kNm)
        Vy_kN, Vz_kN: Co-existing shear with My (parallel to the flanges) and with Mz (parallel to the web) (kN)
        An_cm2: Net area (cm²), see check_tension()
        LLT_mm: Effective length for lateral torsional buckling (mm)
        fm, Ly_mm: See check_lateral_torsional_buckling()
        independent: T and M can vary independently (ψ = 0.8)
        section_class, cantilever, welded: See check_bending()
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    T, My, Mz = abs(T_kN), abs(My_kNm), abs(Mz_kNm)
    tension: TensionResult = check_tension(section, fy, fu_mpa, steel_grade, T or None, An_cm2, section_type=section_type, properties=properties)
    bend_z: Optional[MomentCapacityResult] = check_bending(section, fy, steel_grade, "z", Mz, Vz_kN, None, section_class, cantilever, welded, section_type=section_type, properties=properties) if Mz else None
    bend_y: Optional[MomentCapacityResult] = check_bending(section, fy, steel_grade, "y", My, Vy_kN, None, section_class, cantilever, welded, section_type=section_type, properties=properties) if My else None
    cls: Optional[SectionClass] = _worst(bend_z.section_class if bend_z else None, bend_y.section_class if bend_y else None)
    M_dy: Optional[float] = bend_y.Md if bend_y else None
    M_dz: Optional[float] = bend_z.Md if bend_z else None
    checks, method, M_ndy, M_ndz, alpha_1, alpha_2 = _section_strength(family, cls or SectionClass.CLASS_3, data, welded, T, tension.Td, My, Mz, M_dy, M_dz)
    section_check: float = min(checks.values())
    governing_checks: dict[str, float] = {f"section ({method})": section_check}

    M_d_LT, M_eff = None, None
    notes: list[str] = []
    if LLT_mm is not None and Mz:
        ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(
            section, fy, steel_grade, LLT_mm, None, fm, Ly_mm, section_class=section_class, cantilever=cantilever, welded=welded, section_type=section_type, properties=properties,
        )
        M_d_LT = ltb.Md
        psi: float = 0.8 if independent else 1.0
        M_eff = max(Mz - psi * T * _get(data, "Zez") / _get(data, "A") / 100.0, 0.0) # kN·cm -> kNm
        checks["member, Meff/Md (16.3.2.1)"] = governing_checks["member, Meff/Md (16.3.2.1)"] = compute_utilisation(M_eff, M_d_LT)
        notes.extend(ltb.metadata.get("notes", []))
    governing: str = _governing(governing_checks)
    return CombinedResult(
        method=method,
        section_class=cls,
        fy=fy,
        N=T,
        My=My,
        Mz=Mz,
        Nd=tension.Td,
        Mdy=M_dy,
        Mdz=M_dz,
        Mndy=M_ndy,
        Mndz=M_ndz,
        alpha_1=alpha_1,
        alpha_2=alpha_2,
        Md_LT=M_d_LT,
        Meff=M_eff,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(governing_checks[governing], "16.3", f"Axial tension and bending: {governing}"),
        reference=_reference("16.3", title="Combined axial force and bending moment"),
        metadata={"notes": notes} if notes else {},
    )


def check_compression_and_bending(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    P_kN: float = 0.0,
    My_kNm: float = 0.0,
    Mz_kNm: float = 0.0,
    Vy_kN: float = 0.0,
    Vz_kN: float = 0.0,
    KLy_mm: Optional[float] = None,
    KLz_mm: Optional[float] = None,
    LLT_mm: Optional[float] = None,
    Cmy: float = 1.0,
    Cmz: float = 1.0,
    CmLT: float = 1.0,
    fm: float = 1.0,
    Ly_mm: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    cantilever: bool = False,
    welded: bool = False,
    buckling_classes: Optional[dict[str, str]] = None,
    A_eff_cm2: Optional[float] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CombinedResult:
    """IS 800:2025 16.3.1 and 16.3.2.2: Members under axial compression and biaxial bending.

    Section strength (16.3.1), Nd = Ag fy/γm0 and Md of 15.2.1 with the co-existing shear, the section classified under
    P and the moment: as in check_tension_and_bending().

    Member strength (16.3.2.2), with KLy_mm and KLz_mm:
        P/Pdy + Ky Cmy My/Mdy + KLT Mz/Mdz <= 1.0
        P/Pdz + 0.6 Ky Cmy My/Mdy + Kz Cmz Mz/Mdz <= 1.0
    Ky = 1 + (λy - 0.2)ny <= 1 + 0.8ny, Kz = 1 + (λz - 0.2)nz <= 1 + 0.8nz,
    KLT = 1 - 0.1 λLT ny/(CmLT - 0.25) >= 1 - 0.1ny/(CmLT - 0.25), ny = P/Pdy and nz = P/Pdz; Pdy and Pdz from 14.1.2, Mdz
    from 15.2.2 where LLT_mm is given (else 15.2.1) and Mdy from 15.2.1. λLT is that of 15.2.2 (0 where it is not
    computed); EN 1993-1-1 Annex B has λz here.

    Args:
        section: IN section
        fy_mpa: Yield stress (MPa); defaults to Table 1 for `steel_grade`
        steel_grade: IS 2062 grade
        P_kN: Factored axial compression (kN)
        My_kNm, Mz_kNm: Maximum factored moments about the minor and major axes (kNm)
        Vy_kN, Vz_kN: Co-existing shear with My and with Mz (kN), for the section strength
        KLy_mm, KLz_mm: Effective lengths for flexural buckling about y-y and z-z (mm)
        LLT_mm: Effective length for lateral torsional buckling (mm)
        Cmy, Cmz, CmLT: Equivalent uniform moment factors, Table 18; see equivalent_uniform_moment_factor()
        fm, Ly_mm: See check_lateral_torsional_buckling()
        section_class: Class to use instead of classifying
        cantilever, welded: See check_bending()
        buckling_classes, A_eff_cm2: See check_compression()
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy: float = _design_strength(fy_mpa, steel_grade, data)
    P, My, Mz = abs(P_kN), abs(My_kNm), abs(Mz_kNm)
    notes: list[str] = []
    bend_z: Optional[MomentCapacityResult] = check_bending(section, fy, steel_grade, "z", Mz, Vz_kN, P or None, section_class, cantilever, welded, section_type=section_type, properties=properties) if Mz else None
    bend_y: Optional[MomentCapacityResult] = check_bending(section, fy, steel_grade, "y", My, Vy_kN, P or None, section_class, cantilever, welded, section_type=section_type, properties=properties) if My else None
    cls: Optional[SectionClass] = _worst(bend_z.section_class if bend_z else None, bend_y.section_class if bend_y else None)
    if cls is None:
        cls = _as_section_class(section_class) if section_class is not None else _classify(section_type, raw, fy, StressPattern.COMPRESSION).section_class
    A_n: float = _require_positive(A_eff_cm2, "A_eff_cm2") if (A_eff_cm2 is not None and cls == SectionClass.CLASS_4) else _get(data, "A")
    N_d: float = A_n * 100.0 * fy / GAMMA_M0 / 1e3 # 16.3.1.1: Ag fy/γm0
    M_dy: Optional[float] = bend_y.Md if bend_y else None
    M_dz: Optional[float] = bend_z.Md if bend_z else None
    checks, method, M_ndy, M_ndz, alpha_1, alpha_2 = _section_strength(family, cls, data, welded, P, N_d, My, Mz, M_dy, M_dz)
    governing_checks: dict[str, float] = {f"section ({method})": min(checks.values())}

    P_dy, P_dz, M_d_LT, K_y, K_z, K_LT, n_y, n_z = None, None, None, None, None, None, None, None
    if KLy_mm is not None and KLz_mm is not None:
        compression: CompressionResult = check_compression(
            section, fy, steel_grade, P, KLz_mm, KLy_mm, None, section_class, welded, buckling_classes, A_eff_cm2, section_type=section_type, properties=properties,
        )
        modes: dict[str, BucklingMode] = {mode.axis: mode for mode in compression.modes}
        P_dy, P_dz = modes["y"].Pd, modes["z"].Pd
        M_dz_member: float = check_bending(section, fy, steel_grade, "z", None, 0.0, P or None, section_class, cantilever, welded, section_type=section_type, properties=properties).Md if Mz else 0.0
        M_dy_member: float = check_bending(section, fy, steel_grade, "y", None, 0.0, P or None, section_class, cantilever, welded, section_type=section_type, properties=properties).Md if My else 0.0
        lambda_LT: float = 0.0
        if LLT_mm is not None and Mz:
            ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(
                section, fy, steel_grade, LLT_mm, None, fm, Ly_mm, P_kN=P or None, section_class=section_class, cantilever=cantilever, welded=welded, section_type=section_type, properties=properties,
            )
            M_d_LT, M_dz_member = ltb.Md, ltb.Md
            lambda_LT = ltb.lambda_LT or 0.0
            notes.extend(ltb.metadata.get("notes", []))
        n_y, n_z = P / P_dy, P / P_dz
        K_y = min(1.0 + (modes["y"].lambda_bar - 0.2) * n_y, 1.0 + 0.8 * n_y)
        K_z = min(1.0 + (modes["z"].lambda_bar - 0.2) * n_z, 1.0 + 0.8 * n_z)
        K_LT = max(1.0 - 0.1 * lambda_LT * n_y / (CmLT - 0.25), 1.0 - 0.1 * n_y / (CmLT - 0.25))
        term_y: float = compute_utilisation(My, M_dy_member) if My else 0.0
        term_z: float = compute_utilisation(Mz, M_dz_member) if Mz else 0.0
        checks["member, y-y (16.3.2.2)"] = governing_checks["member, y-y (16.3.2.2)"] = n_y + K_y * Cmy * term_y + K_LT * term_z
        checks["member, z-z (16.3.2.2)"] = governing_checks["member, z-z (16.3.2.2)"] = n_z + 0.6 * K_y * Cmy * term_y + K_z * Cmz * term_z
        notes.extend(compression.metadata.get("notes", []))
    else:
        notes.append("Member strength (16.3.2.2) not checked: pass KLy_mm and KLz_mm.")
    governing: str = _governing(governing_checks)
    return CombinedResult(
        method=method,
        section_class=cls,
        fy=fy,
        N=P,
        My=My,
        Mz=Mz,
        Nd=N_d,
        Mdy=M_dy,
        Mdz=M_dz,
        Mndy=M_ndy,
        Mndz=M_ndz,
        alpha_1=alpha_1,
        alpha_2=alpha_2,
        Pdy=P_dy,
        Pdz=P_dz,
        Md_LT=M_d_LT,
        Ky=K_y,
        Kz=K_z,
        KLT=K_LT,
        Cmy=Cmy,
        Cmz=Cmz,
        CmLT=CmLT,
        ny=n_y,
        nz=n_z,
        utilisations=checks,
        governing=governing,
        utilisation=_ratio_check(governing_checks[governing], "16.3", f"Axial compression and bending: {governing}"),
        reference=_reference("16.3", title="Combined axial force and bending moment"),
        metadata={"notes": notes} if notes else {},
    )


if __name__ == "__main__":
    from steelsnakes.IN.sections import MediumWeightBeam

    # ISMB 300 (IS 808): I_t and I_w from the thin-walled formulas Σbt³/3 and Iy hf²/4
    beam = MediumWeightBeam(
        designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26,
        I_zz=8603.6, I_yy=453.9, Z_zz=573.6, Z_yy=64.8, Z_pz=651.7, Z_py=111.0, I_t=21.7, I_w=93_870.0,
    )
    print(check_tension(beam, T_kN=900.0).Td)
    print(check_compression(beam, P_kN=500.0, KLz_mm=4000.0, KLy_mm=4000.0).Pd)
    print(check_shear(beam, V_kN=200.0).Vd, check_bending(beam, M_kNm=120.0).Md)
    ltb = check_lateral_torsional_buckling(beam, LLT_mm=4000.0, Mz_kNm=80.0, fm=moment_gradient_factor("udl"))
    print(ltb.lambda_LT, ltb.chi_LT, ltb.Md)
    print(check_compression_and_bending(beam, P_kN=300.0, Mz_kNm=60.0, KLy_mm=4000.0, KLz_mm=4000.0, LLT_mm=4000.0).utilisations)
    print("🐬")
