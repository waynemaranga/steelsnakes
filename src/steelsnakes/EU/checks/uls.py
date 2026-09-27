# 6: ULTIMATE LIMIT STATES
# 6.1 General
# 6.2 Resistance of cross-sections
# 6.3 Buckling resistance of members
# 6.4 Uniform built-up compression members
# Annex A: Method 1, interaction factors kij for the interaction formula in 6.3.3(4)
# Annex B: Method 2, interaction factors kij for the interaction formula in 6.3.3(4)
# NOTE: EN 1993-1-1:2005+A1:2014 with the recommended values of the Nationally Determined Parameters; see the National
# ... Annex for others, e.g the UK NA takes gamma_M2 = 1.10.
# NOTE: units are N, mm and N/mm² [MPa]; moments are in Nmm (1 kNm = 1e6 Nmm). Section tables are in mm, cm², cm³, cm⁴,
# ... cm and dm⁶ (I_w) and are converted on read; values passed as `properties` use the section-table units.
# NOTE: design action effects are magnitudes, except N_Ed in combined checks, where compression is positive.
from __future__ import annotations

import math
import re
from enum import Enum
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
from steelsnakes.base.exceptions import SectionClass4Error
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.EU.checks.classification import (
    ANGLE_SECTION_TYPES,
    CHANNEL_SECTION_TYPES,
    ELLIPTICAL_HOLLOW_SECTION_TYPES,
    GAMMA_M0,
    RECTANGULAR_HOLLOW_SECTION_TYPES,
    ROLLED_I_SECTION_TYPES,
    ROUND_HOLLOW_SECTION_TYPES,
    SQUARE_HOLLOW_SECTION_TYPES,
    ElementInput,
    ElementStressDistribution,
    StressPattern,
    _class_rank,
    _epsilon,
    _rectangular_hollow_elements_from_dict,
    _square_hollow_elements_from_dict,
    channel_section_elements,
    classify_elements,
    classify_section,
    classify_section_from_dict,
    i_section_elements,
)

# 6.1(1) NOTE 2B: recommended partial factors for buildings; GAMMA_M0 = 1.00 is shared with the classification module
GAMMA_M1 = 1.00 # resistance of members to instability assessed by member checks
GAMMA_M2 = 1.25 # resistance of cross-sections in tension to fracture; is 1.10 in the UK NA
# 3.2.6(1): design values of material coefficients
E_STEEL = 210_000.0 # N/mm² [MPa]; modulus of elasticity
G_STEEL = 81_000.0 # N/mm² [MPa]; shear modulus
ETA = 1.0 # 6.2.6(3) NOTE: eta of EN 1993-1-5, conservatively 1.0; EN 1993-1-5 5.1(2) NOTE recommends 1.2 up to S460
LAMBDA_LT_0 = 0.4 # 6.3.2.3(1) NOTE: plateau length, recommended maximum value for rolled or equivalent welded sections
BETA_LT = 0.75 # 6.3.2.3(1) NOTE: recommended minimum value
LAMBDA_C0 = LAMBDA_LT_0 + 0.1 # 6.3.2.4(1)B NOTE 2B: slenderness limit of the equivalent compression flange
K_FL = 1.10 # 6.3.2.4(2)B NOTE B: modification factor of the equivalent compression flange method

BucklingAxis = Literal["y", "z", "v"] # v: minor principal axis of angles
BendingAxis = Literal["y", "z"]
ShearDirection = Literal["z", "y"] # z: load parallel to the web or depth (V_z,Ed); y: parallel to the flanges or width (V_y,Ed)
ShearAreaShape = Literal["rolled_I", "welded_I", "rolled_channel", "welded_channel", "rolled_T", "welded_T", "welded_box", "RHS", "CHS"]
BucklingShape = Literal["rolled_I", "welded_I", "hot_finished_hollow", "cold_formed_hollow", "welded_box", "U", "T", "solid", "L"]
TorsionShape = Literal["I", "channel", "hollow"]
LTBMethod = Literal["general", "rolled"] # 6.3.2.2 (6.56) or 6.3.2.3 (6.57)
InteractionMethod = Literal["A", "B"] # 6.3.3(5): Annex A (method 1) or Annex B (method 2)
SectionClassInput = SectionClass | int | str

# Table 6.1: Imperfection factors for buckling curves
IMPERFECTION_FACTORS: dict[str, float] = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}
# Table 6.3: Recommended imperfection factors for lateral torsional buckling curves
LTB_IMPERFECTION_FACTORS: dict[str, float] = {"a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}

# Table 3.1: nominal (fy, fu) in N/mm² for t <= 40 mm, then for 40 mm < t <= 80 mm; EN 10219-1 is tabulated to t <= 40 mm
STEEL_GRADES: dict[str, dict[str, tuple[tuple[float, float], Optional[tuple[float, float]]]]] = {
    "EN 10025-2": {
        "S235": ((235.0, 360.0), (215.0, 360.0)),
        "S275": ((275.0, 430.0), (255.0, 410.0)),
        "S355": ((355.0, 490.0), (335.0, 470.0)),
        "S450": ((440.0, 550.0), (410.0, 550.0)),
    },
    "EN 10025-3": {
        "S275N": ((275.0, 390.0), (255.0, 370.0)),
        "S355N": ((355.0, 490.0), (335.0, 470.0)),
        "S420N": ((420.0, 520.0), (390.0, 520.0)),
        "S460N": ((460.0, 540.0), (430.0, 540.0)),
    },
    "EN 10025-4": {
        "S275M": ((275.0, 370.0), (255.0, 360.0)),
        "S355M": ((355.0, 470.0), (335.0, 450.0)),
        "S420M": ((420.0, 520.0), (390.0, 500.0)),
        "S460M": ((460.0, 540.0), (430.0, 530.0)),
    },
    "EN 10025-5": {
        "S235W": ((235.0, 360.0), (215.0, 340.0)),
        "S355W": ((355.0, 490.0), (335.0, 490.0)),
    },
    "EN 10025-6": {
        "S460Q": ((460.0, 570.0), (440.0, 550.0)),
    },
    "EN 10210-1": { # hot finished structural hollow sections
        "S235H": ((235.0, 360.0), (215.0, 340.0)),
        "S275H": ((275.0, 430.0), (255.0, 410.0)),
        "S355H": ((355.0, 510.0), (335.0, 490.0)),
        "S275NH": ((275.0, 390.0), (255.0, 370.0)),
        "S355NH": ((355.0, 490.0), (335.0, 470.0)),
        "S420NH": ((420.0, 540.0), (390.0, 520.0)),
        "S460NH": ((460.0, 560.0), (430.0, 550.0)),
    },
    "EN 10219-1": { # cold formed structural hollow sections
        "S235H": ((235.0, 360.0), None),
        "S275H": ((275.0, 430.0), None),
        "S355H": ((355.0, 510.0), None),
        "S275NH": ((275.0, 370.0), None),
        "S355NH": ((355.0, 470.0), None),
        "S460NH": ((460.0, 550.0), None),
        "S275MH": ((275.0, 360.0), None),
        "S355MH": ((355.0, 470.0), None),
        "S420MH": ((420.0, 500.0), None),
        "S460MH": ((460.0, 530.0), None),
    },
}

# Section-table keys -> (check keys, factor to N-mm units): A cm², W cm³, I and I_t cm⁴, i cm, I_w dm⁶; dimensions are in mm
_PROPERTY_MAP: dict[str, tuple[tuple[str, ...], float]] = {
    "A": (("A", "total_area"), 1e2),
    "I_y": (("I_yy", "I"), 1e4),
    "I_z": (("I_zz", "I"), 1e4),
    "I_v": (("I_vv",), 1e4),
    "i_y": (("i_yy", "i"), 1e1),
    "i_z": (("i_zz", "i"), 1e1),
    "i_v": (("i_vv",), 1e1),
    "W_el_y": (("W_el_yy", "W_el"), 1e3),
    "W_el_z": (("W_el_zz", "W_el"), 1e3),
    "W_pl_y": (("W_pl_yy", "W_pl"), 1e3),
    "W_pl_z": (("W_pl_zz", "W_pl"), 1e3),
    "I_t": (("I_t",), 1e4),
    "W_t": (("W_t",), 1e3),
    "I_w": (("I_w",), 1e12),
    "h": (("h",), 1.0),
    "b": (("b",), 1.0),
    "t_w": (("tw", "t"), 1.0),
    "t_f": (("tf", "t"), 1.0),
    "t": (("t",), 1.0),
    "r": (("r", "r_1"), 1.0),
    "d": (("d",), 1.0),
}


# --- Helpers ---
def _require_positive(value: Optional[float], name: str) -> float:
    if value is None or value <= 0.0:
        raise ValueError(f"{name} must be positive.")
    return float(value)


def _reference(clause: str, equation: Optional[str] = None, title: Optional[str] = None, notes: Optional[str] = None) -> Reference:
    return Reference(code=DesignCode.EN_1993, clause=clause, equation=equation, title=title, notes=notes)


def _ratio_check(utilisation: float, clause: str, equation: Optional[str], title: str, **metadata: Any) -> UtilisationCheck:
    return UtilisationCheck(
        utilisation=utilisation,
        metadata=metadata,
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=_reference(clause, equation, title),
    )


def _utilisation_check(demand: float, resistance: float, clause: str, equation: Optional[str], title: str) -> UtilisationCheck:
    """E_d/R_d <= 1.0, on the magnitude of the action effect."""
    utilisation: float = compute_utilisation(abs(demand), resistance)
    return _ratio_check(utilisation, clause, equation, title, E_d=demand, R_d=resistance)


def _as_section_class(value: SectionClassInput) -> SectionClass:
    """Accept SectionClass.CLASS_2, 2, "2", "class 2" or "CLASS_2"."""
    if isinstance(value, SectionClass):
        if value.name not in {"CLASS_1", "CLASS_2", "CLASS_3", "CLASS_4"}:
            raise ValueError(f"EN 1993 uses Classes 1 to 4, not {value.value}.")
        return value
    digits: str = re.sub(r"\D", "", str(value))
    if digits not in {"1", "2", "3", "4"}:
        raise ValueError(f"Unrecognised section class '{value}'; use 1, 2, 3 or 4.")
    return SectionClass[f"CLASS_{digits}"]


def _is_plastic(section_class: SectionClass) -> bool:
    return section_class in (SectionClass.CLASS_1, SectionClass.CLASS_2)


def _family(section_type: Optional[SectionType]) -> str:
    if section_type in ROLLED_I_SECTION_TYPES:
        return "I"
    if section_type in CHANNEL_SECTION_TYPES:
        return "channel"
    if section_type in ANGLE_SECTION_TYPES:
        return "angle"
    if section_type in RECTANGULAR_HOLLOW_SECTION_TYPES or section_type in SQUARE_HOLLOW_SECTION_TYPES:
        return "RHS"
    if section_type in ROUND_HOLLOW_SECTION_TYPES:
        return "CHS"
    if section_type in ELLIPTICAL_HOLLOW_SECTION_TYPES:
        return "EHS"
    return "other"


def _section_data(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> tuple[Optional[SectionType], dict[str, float], dict[str, Any]]:
    """Resolve a section and/or plain properties (section-table units) into (section_type, N-mm data, raw data).

    `properties` overrides or supplements the section's own values, e.g I_w for a custom section.
    """
    raw: dict[str, Any] = {}
    if section is not None:
        raw.update(section.get_properties())
        section_type = section.get_section_type()
    raw.update(properties or {})

    data: dict[str, float] = {}
    for key, (aliases, factor) in _PROPERTY_MAP.items():
        for alias in aliases:
            value = raw.get(alias)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0:
                data[key] = float(value) * factor
                break

    size = raw.get("hxb") or raw.get("hxh") # hollow sections store "h x b" as text
    if isinstance(size, str) and ("h" not in data or "b" not in data):
        numbers: list[str] = re.findall(r"\d+(?:\.\d+)?", size)
        if len(numbers) >= 2:
            data.setdefault("h", float(numbers[0]))
            data.setdefault("b", float(numbers[1]))
    if section_type in ROUND_HOLLOW_SECTION_TYPES and "d" in data:
        data["D"] = data.pop("d") # outside diameter, not a depth between fillets
    return section_type, data, raw


def _get(data: dict[str, float], key: str) -> float:
    value = data.get(key)
    if value is None or value <= 0.0:
        raise ValueError(f"Section property '{key}' is not available; pass it through `properties` (section-table units) or as an argument.")
    return value


def _web_depth(data: dict[str, float]) -> float:
    """h_w = h - 2t_f, the depth of the web between the flanges."""
    return _get(data, "h") - 2.0 * _get(data, "t_f")


def _classify(
    section: Optional[BaseSection],
    section_type: Optional[SectionType],
    raw: dict[str, Any],
    fy: float,
    pattern: StressPattern,
    custom_elements: Optional[list[ElementInput]] = None,
) -> SectionClass:
    """5.5: class from the EU classification engine; Class 4 hollow sections report CLASS_4 instead of raising."""
    try:
        if custom_elements is not None:
            return classify_elements(custom_elements, fy).section_class
        if section is not None:
            return classify_section(section=section, fy_mpa=fy, stress_pattern=pattern).section_class
        if section_type is not None and raw:
            return classify_section_from_dict(section_type, raw, fy_mpa=fy, stress_pattern=pattern).section_class
    except SectionClass4Error:
        return SectionClass.CLASS_4
    raise ValueError("Pass `section_class`, or a section (or section_type with properties) to classify.")


def _class_for_actions(
    section: Optional[BaseSection],
    section_type: Optional[SectionType],
    data: dict[str, float],
    raw: dict[str, Any],
    fy: float,
    N_Ed: float,
    M_y_Ed: float,
    M_z_Ed: float,
    section_class: Optional[SectionClassInput],
) -> Optional[SectionClass]:
    """5.5: class of the cross-section under the given actions (compression positive); None under tension and/or shear only.

    Compression with major-axis bending on I-sections and channels treats the web as a part in bending and compression,
    with the plastic alpha = (1 + N_Ed/(c*t_w*fy))/2 and the elastic psi = 2N_Ed/(A*fy) - 1. Compression with bending
    about one axis of an RHS or SHS does the same for the two walls in bending, alpha = (1 + N_Ed/(2c*t*fy))/2, with the
    other two walls in compression. Other combinations with compression use the uniform-compression limits, which is
    conservative.
    """
    if section_class is not None:
        return _as_section_class(section_class)
    has_moment: bool = M_y_Ed != 0.0 or M_z_Ed != 0.0
    if N_Ed <= 0.0 and not has_moment:
        return None
    if N_Ed > 0.0 and not has_moment:
        return _classify(section, section_type, raw, fy, StressPattern.COMPRESSION)
    if N_Ed <= 0.0:
        classes: list[SectionClass] = []
        if M_y_Ed != 0.0:
            classes.append(_classify(section, section_type, raw, fy, StressPattern.MAJOR_AXIS_BENDING))
        if M_z_Ed != 0.0:
            classes.append(_classify(section, section_type, raw, fy, StressPattern.MINOR_AXIS_BENDING))
        return max(classes, key=_class_rank)

    family: str = _family(section_type)
    psi: float = max(min(2.0 * N_Ed / (data["A"] * fy) - 1.0, 1.0), -1.0) if "A" in data else -1.0 # elastic, extreme fibre at fy
    if M_z_Ed == 0.0 and family in ("I", "channel") and all(key in data for key in ("d", "t_w", "b", "t_f", "A")):
        # Table 5.2 Sheet 1/3: web in bending and compression; Sheet 2/3: flanges in compression
        c, t_w = data["d"], data["t_w"]
        alpha: float = min(0.5 * (1.0 + N_Ed / (c * t_w * fy)), 1.0) # plastic neutral axis in the web
        r: float = 0.0 if section_type == SectionType.UPN else data.get("r", 0.0) # flange c = (b - tw - 2r)/2 or b - tw - r
        if family == "I":
            elements: list[ElementInput] = i_section_elements(d_mm=c, tw_mm=t_w, b_mm=data["b"], tf_mm=data["t_f"], r_mm=r)
        else:
            elements = channel_section_elements(d_mm=c, tw_mm=t_w, b_mm=data["b"], tf_mm=data["t_f"], r_mm=r)
        elements = [
            element.model_copy(update={"stress": ElementStressDistribution.COMBINED, "alpha": alpha, "psi": psi}) if element.name == "web" else element
            for element in elements
        ]
        return _classify(section, section_type, raw, fy, StressPattern.COMBINED, custom_elements=elements)
    if family == "RHS" and (M_y_Ed == 0.0) != (M_z_Ed == 0.0) and all(key in data for key in ("t", "A")):
        # Table 5.2 Sheet 1/3: the two walls parallel to the plane of bending in bending and compression, the others in compression
        walls: list[ElementInput] = _hollow_walls(section, section_type, raw)
        bending_wall: str = "web_wall" if M_y_Ed != 0.0 else "flange_wall" # h walls for M_y, b walls for M_z
        c_wall: float = next(wall.c_mm for wall in walls if wall.name == bending_wall)
        alpha = min(0.5 * (1.0 + N_Ed / (2.0 * c_wall * data["t"] * fy)), 1.0) # plastic neutral axis in the two walls
        elements = [
            wall.model_copy(update={"stress": ElementStressDistribution.COMBINED, "alpha": alpha, "psi": psi}) if wall.name == bending_wall else wall
            for wall in walls
        ]
        return _classify(section, section_type, raw, fy, StressPattern.COMBINED, custom_elements=elements)
    return _classify(section, section_type, raw, fy, StressPattern.COMPRESSION)


def _hollow_walls(section: Optional[BaseSection], section_type: Optional[SectionType], raw: dict[str, Any]) -> list[ElementInput]:
    """web_wall (h walls) and flange_wall (b walls) of an RHS or SHS, Table 5.2 Sheet 1/3, with c = h - 3t and b - 3t as tabulated."""
    if section is not None:
        return list(section.classification_elements())
    if section_type in SQUARE_HOLLOW_SECTION_TYPES:
        return _square_hollow_elements_from_dict(raw)
    return _rectangular_hollow_elements_from_dict(raw)


def _class_4_value(value: Optional[float], name: str, clause: str) -> float:
    if value is None:
        raise SectionClass4Error(
            f"Class 4 cross-section: pass {name} from EN 1993-1-5 effective widths ({clause}); effective properties are not implemented."
        )
    return _require_positive(value, name)


def _phi(lambda_bar: float, alpha: float, lambda_0: float = 0.2, beta: float = 1.0) -> float:
    """6.3.1.2(1) and 6.3.2.2(1): Phi = 0.5[1 + alpha(lambda_bar - 0.2) + lambda_bar²]; 6.3.2.3(1) with lambda_0 and beta."""
    return 0.5 * (1.0 + alpha * (lambda_bar - lambda_0) + beta * lambda_bar**2)


def _alpha(curve_or_alpha: float | str, table: dict[str, float], name: str) -> float:
    if isinstance(curve_or_alpha, str):
        if curve_or_alpha not in table:
            raise ValueError(f"Unknown buckling curve '{curve_or_alpha}' for {name}; expected one of {', '.join(table)}.")
        return table[curve_or_alpha]
    return _require_positive(curve_or_alpha, "alpha")


# --- 3.2 Structural steel ---
class SteelMaterial(BaseModel):
    # 3.2.1 Material properties; Table 3.1 simplification of the product standards
    grade: str # Table 3.1 row, e.g "S355" or "S355NH"
    standard: str # product standard, e.g "EN 10025-2"
    t: float # nominal thickness of the element, mm
    fy: float # nominal yield strength, N/mm² [MPa]
    fu: float # nominal ultimate tensile strength, N/mm² [MPa]
    E: float = E_STEEL # 3.2.6(1), N/mm²
    G: float = G_STEEL # 3.2.6(1), N/mm²
    epsilon: float # sqrt(235/fy), Table 5.2
    reference: Optional[Reference] = None


def _grade_key(grade: str) -> str:
    """Table 3.1 row for a steel name: impact qualities are dropped and NL/ML/QL share the N/M/Q rows, e.g S355J2H -> S355H."""
    text: str = grade.upper().replace(" ", "").split("+")[0]
    match = re.fullmatch(r"S(\d{3})([A-Z0-9]*)", text)
    if match is None:
        raise ValueError(f"Unrecognised steel grade '{grade}'; expected e.g 'S355', 'S355J2' or 'S355NH'.")
    strength, suffix = match.groups()
    suffix = re.sub(r"^(JR|J0|J2|K2)", "", suffix)
    suffix = {"NL": "N", "ML": "M", "QL": "Q", "QL1": "Q", "NLH": "NH", "MLH": "MH"}.get(suffix, suffix)
    return f"S{strength}{suffix}"


def steel_material(grade: str = "S355", t: float = 16.0, standard: Optional[str] = None) -> SteelMaterial:
    """EN 1993-1-1 3.2.1, Table 3.1: Nominal yield strength fy and ultimate tensile strength fu of structural steel.

    3.2.1(1) lets the National Annex choose between Table 3.1 and the product standard (fy = ReH, fu = Rm); the UK NA
    uses the product standard, which steps fy down at 16 mm, 40 mm, 63 mm and 80 mm.

    Args:
        grade: Steel grade, e.g "S355", "S355J2", "S355NL" or "S355J2H"; impact qualities (JR, J0, J2, K2) are ignored
        t: Nominal thickness of the element (mm), e.g the flange of a rolled section; Table 3.1 covers t <= 80 mm
        standard: Product standard, e.g "EN 10025-2" or "EN 10219-1"; by default, the first standard listing the grade

    Returns:
        SteelMaterial with fy and fu (N/mm²)
    """
    key: str = _grade_key(grade)
    t = _require_positive(t, "t")
    if standard is not None and standard not in STEEL_GRADES:
        raise ValueError(f"Unknown product standard '{standard}'; Table 3.1 lists {', '.join(STEEL_GRADES)}.")
    standards: list[str] = [standard] if standard is not None else list(STEEL_GRADES)
    for name in standards:
        rows = STEEL_GRADES[name]
        if key not in rows:
            continue
        thin, thick = rows[key]
        if t <= 40.0:
            fy, fu = thin
        elif t <= 80.0 and thick is not None:
            fy, fu = thick
        else:
            raise ValueError(f"Table 3.1 gives no strengths for {key} ({name}) at t = {t} mm; use the product standard.")
        return SteelMaterial(
            grade=key,
            standard=name,
            t=t,
            fy=fy,
            fu=fu,
            epsilon=_epsilon(fy),
            reference=_reference("3.2.1", title="Table 3.1: Nominal values of yield strength fy and ultimate tensile strength fu"),
        )
    raise ValueError(f"Steel grade '{grade}' ({key}) is not in Table 3.1{' for ' + standard if standard else ''}.")


# --- 6.2.1 General ---
def yield_criterion_utilisation(sigma_x_Ed: float, sigma_z_Ed: float, tau_Ed: float, fy: float, gamma_M0: float = GAMMA_M0) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.1: Elastic verification at a critical point of the cross-section.

    (σx/(fy/γM0))² + (σz/(fy/γM0))² - (σx/(fy/γM0))(σz/(fy/γM0)) + 3(τ/(fy/γM0))² <= 1

    Args:
        sigma_x_Ed: Design longitudinal stress at the point (N/mm²); tension positive
        sigma_z_Ed: Design transverse stress at the point (N/mm²); tension positive
        tau_Ed: Design shear stress at the point (N/mm²)
        fy: Yield strength (N/mm²)
        gamma_M0: Partial factor for resistance of cross-sections
    """
    f: float = _require_positive(fy, "fy") / gamma_M0
    utilisation: float = (sigma_x_Ed / f) ** 2 + (sigma_z_Ed / f) ** 2 - (sigma_x_Ed / f) * (sigma_z_Ed / f) + 3.0 * (tau_Ed / f) ** 2
    return _ratio_check(utilisation, "6.2.1(5)", "6.1", "Yield criterion", sigma_x_Ed=sigma_x_Ed, sigma_z_Ed=sigma_z_Ed, tau_Ed=tau_Ed)


def linear_interaction_utilisation(
    N_Ed: float,
    N_Rd: float,
    M_y_Ed: float = 0.0,
    M_y_Rd: Optional[float] = None,
    M_z_Ed: float = 0.0,
    M_z_Rd: Optional[float] = None,
) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.2: Conservative linear summation for Class 1, 2 or 3, N_Ed/N_Rd + My,Ed/My,Rd + Mz,Ed/Mz,Rd <= 1.

    Args:
        N_Ed: Design axial force (N)
        N_Rd: Design axial resistance (N)
        M_y_Ed, M_z_Ed: Design moments (Nmm)
        M_y_Rd, M_z_Rd: Design moment resistances, including any reduction for shear (6.2.8) (Nmm)
    """
    utilisation: float = compute_utilisation(abs(N_Ed), N_Rd)
    for M_Ed, M_Rd, name in ((M_y_Ed, M_y_Rd, "M_y_Rd"), (M_z_Ed, M_z_Rd, "M_z_Rd")):
        if M_Ed != 0.0:
            if M_Rd is None:
                raise ValueError(f"{name} is required when the matching moment is not zero.")
            utilisation += compute_utilisation(abs(M_Ed), M_Rd)
    return _ratio_check(utilisation, "6.2.1(7)", "6.2", "Linear interaction", N_Ed=N_Ed, M_y_Ed=M_y_Ed, M_z_Ed=M_z_Ed)


# --- 6.2.2 Section properties ---
def net_area(A: float, t: float, d0: float, n_holes: int = 0, staggers: Sequence[tuple[float, float]] = ()) -> float:
    """EN 1993-1-1 6.2.2.2 and Equation 6.3: Net area of a cross-section with fastener holes.

    The deduction is the greater of 6.2.2.2(3), the holes in any cross-section perpendicular to the member axis,
    n_holes*d0*t, and 6.2.2.2(4)b), a staggered chain of n holes, t*(n*d0 - Σ s²/(4p)).

    Args:
        A: Gross area (mm²)
        t: Thickness of the holed element (mm)
        d0: Hole diameter (mm)
        n_holes: Holes in the critical cross-section perpendicular to the member axis (failure plane 2, Figure 6.1)
        staggers: (s, p) for every gap along a diagonal or zig-zag chain of len(staggers) + 1 holes; s is the staggered
            pitch parallel to the member axis, p the spacing perpendicular to it (mm). For angles with holes in both legs,
            p is measured along the centre of thickness (6.2.2.2(5)).

    Returns:
        A_net: Net area (mm²)
    """
    A = _require_positive(A, "A")
    t = _require_positive(t, "t")
    d0 = _require_positive(d0, "d0")
    if n_holes < 0:
        raise ValueError("n_holes cannot be negative.")
    deduction: float = n_holes * d0 * t # 6.2.2.2(3)
    if staggers:
        n: int = len(staggers) + 1
        chain: float = t * (n * d0 - sum(s**2 / (4.0 * _require_positive(p, "p")) for s, p in staggers)) # (6.3)
        deduction = max(deduction, chain)
    A_net: float = A - deduction
    if A_net <= 0.0:
        raise ValueError("Net area must be positive; check the hole diameter, thickness and count.")
    return A_net


# --- 6.2.3 Tension ---
def plastic_tension_resistance(A: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 Equation 6.6: Design plastic resistance of the gross cross-section, N_pl,Rd = A*fy/γM0 (N)."""
    return _require_positive(A, "A") * _require_positive(fy, "fy") / gamma_M0


def ultimate_net_tension_resistance(A_net: float, fu: float, gamma_M2: float = GAMMA_M2) -> float:
    """EN 1993-1-1 Equation 6.7: Design ultimate resistance of the net cross-section at holes, N_u,Rd = 0.9*A_net*fu/γM2 (N)."""
    return 0.9 * _require_positive(A_net, "A_net") * _require_positive(fu, "fu") / gamma_M2


def net_section_yield_resistance(A_net: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 Equation 6.8: Net section resistance for Category C connections, N_net,Rd = A_net*fy/γM0 (N)."""
    return _require_positive(A_net, "A_net") * _require_positive(fy, "fy") / gamma_M0


def tension_utilisation(N_Ed: float, N_t_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.5: N_Ed/N_t,Rd <= 1.0."""
    return _utilisation_check(N_Ed, N_t_Rd, "6.2.3", "6.5", "Tension")


class TensionResult(BaseModel):
    # 6.2.3 Tension; N_t,Rd is the smaller of (6.6) and (6.7), or of (6.6) and (6.8) in Category C connections
    N_t_Rd: float # design tension resistance, N
    limit_state: LimitState # TENSILE_YIELDING (6.6, 6.8) or TENSILE_RUPTURE (6.7)
    N_pl_Rd: float # (6.6), N; plastic resistance of the gross cross-section
    N_u_Rd: float # (6.7), N; ultimate resistance of the net cross-section at holes for fasteners
    N_net_Rd: Optional[float] = None # (6.8), N; Category C connections only
    A: float # gross area, mm²
    A_net: float # net area, mm²; 6.2.2.2
    fy: float # N/mm²
    fu: float # N/mm²
    ductile: bool # 6.2.3(3): N_pl,Rd < N_u,Rd, as needed where capacity design is requested (EN 1998)
    N_Ed: Optional[float] = None # design tension force, N
    utilisation: Optional[UtilisationCheck] = None # (6.5)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_tension(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    fu: float = 490.0,
    N_Ed: Optional[float] = None,
    A: Optional[float] = None,
    A_net: Optional[float] = None,
    category_C: bool = False,
    gamma_M0: float = GAMMA_M0,
    gamma_M2: float = GAMMA_M2,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> TensionResult:
    """EN 1993-1-1 6.2.3: Design tension resistance N_t,Rd and, with N_Ed, the utilisation to Equation 6.5.

    For angles connected through one leg, EN 1993-1-8 3.10.3 applies (6.2.3(5)); that reduction is not made here.

    Args:
        section: EU/UK section; A is read from the section tables
        fy: Yield strength (N/mm²); see steel_material()
        fu: Ultimate tensile strength (N/mm²)
        N_Ed: Design tension force (N)
        A: Gross area (mm²); overrides the section value
        A_net: Net area at holes (mm²), see net_area(); defaults to A for members without holes
        category_C: Category C (slip-resistant at ULS) connection, EN 1993-1-8 3.4.1(1); the net section is then (6.8)
        gamma_M0: Partial factor for resistance of cross-sections
        gamma_M2: Partial factor for resistance of cross-sections in tension to fracture
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    _, data, _ = _section_data(section, section_type, properties)
    A_value: float = _require_positive(A if A is not None else data.get("A"), "A")
    A_net_value: float = _require_positive(A_net if A_net is not None else A_value, "A_net")
    if A_net_value > A_value:
        raise ValueError("Net area A_net cannot exceed the gross area A.")

    N_pl_Rd: float = plastic_tension_resistance(A_value, fy, gamma_M0) # (6.6)
    N_u_Rd: float = ultimate_net_tension_resistance(A_net_value, fu, gamma_M2) # (6.7)
    N_net_Rd: Optional[float] = net_section_yield_resistance(A_net_value, fy, gamma_M0) if category_C else None # (6.8)
    if N_net_Rd is not None:
        net_Rd, net_state, net_equation = N_net_Rd, LimitState.TENSILE_YIELDING, "6.8"
    else:
        net_Rd, net_state, net_equation = N_u_Rd, LimitState.TENSILE_RUPTURE, "6.7"
    if N_pl_Rd <= net_Rd:
        N_t_Rd, limit_state, equation = N_pl_Rd, LimitState.TENSILE_YIELDING, "6.6"
    else:
        N_t_Rd, limit_state, equation = net_Rd, net_state, net_equation

    return TensionResult(
        N_t_Rd=N_t_Rd,
        limit_state=limit_state,
        N_pl_Rd=N_pl_Rd,
        N_u_Rd=N_u_Rd,
        N_net_Rd=N_net_Rd,
        A=A_value,
        A_net=A_net_value,
        fy=fy,
        fu=fu,
        ductile=N_pl_Rd < N_u_Rd,
        N_Ed=N_Ed,
        utilisation=tension_utilisation(N_Ed, N_t_Rd) if N_Ed is not None else None,
        reference=_reference("6.2.3", equation, "Tension"),
    )


# --- 6.2.4 Compression ---
def compression_resistance(A: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 Equations 6.10 and 6.11: N_c,Rd = A*fy/γM0 for Class 1, 2 or 3; pass A_eff as A for Class 4 (N)."""
    return _require_positive(A, "A") * _require_positive(fy, "fy") / gamma_M0


def compression_utilisation(N_Ed: float, N_c_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.9: N_Ed/N_c,Rd <= 1.0."""
    return _utilisation_check(N_Ed, N_c_Rd, "6.2.4", "6.9", "Compression")


class CompressionResult(BaseModel):
    # 6.2.4 Compression; holes filled by fasteners need not be allowed for, except oversize and slotted holes (6.2.4(3))
    N_c_Rd: float # (6.10) or (6.11), N
    section_class: SectionClass # 5.5, under uniform compression
    A: float # mm²; A for Class 1, 2 or 3, A_eff for Class 4
    fy: float # N/mm²
    N_Ed: Optional[float] = None # design compression force, N
    utilisation: Optional[UtilisationCheck] = None # (6.9)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_compression(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    N_Ed: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    A: Optional[float] = None,
    A_eff: Optional[float] = None,
    gamma_M0: float = GAMMA_M0,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CompressionResult:
    """EN 1993-1-1 6.2.4: Design resistance of the cross-section for uniform compression, N_c,Rd.

    Args:
        section: EU/UK section; classified under uniform compression unless `section_class` is given
        fy: Yield strength (N/mm²)
        N_Ed: Design compression force (N)
        section_class: Class to use instead of classifying, e.g 1 or SectionClass.CLASS_3
        A: Gross area (mm²); overrides the section value
        A_eff: Effective area for Class 4 (mm²), from EN 1993-1-5; unsymmetric Class 4 sections also need 6.2.9.3
        gamma_M0: Partial factor for resistance of cross-sections
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    cls: SectionClass = _as_section_class(section_class) if section_class is not None else _classify(section, section_type, raw, fy, StressPattern.COMPRESSION)
    if cls == SectionClass.CLASS_4:
        A_used, equation = _class_4_value(A_eff, "A_eff", "6.2.2.5"), "6.11"
    else:
        A_used, equation = _require_positive(A if A is not None else data.get("A"), "A"), "6.10"
    N_c_Rd: float = compression_resistance(A_used, fy, gamma_M0)
    return CompressionResult(
        N_c_Rd=N_c_Rd,
        section_class=cls,
        A=A_used,
        fy=fy,
        N_Ed=N_Ed,
        utilisation=compression_utilisation(N_Ed, N_c_Rd) if N_Ed is not None else None,
        reference=_reference("6.2.4", equation, "Compression"),
    )


# --- 6.2.5 Bending moment ---
def section_modulus_for_class(
    section_class: SectionClassInput,
    W_pl: Optional[float] = None,
    W_el: Optional[float] = None,
    W_eff: Optional[float] = None,
) -> tuple[float, str]:
    """EN 1993-1-1 6.2.5(2): (W, equation); W_pl for Class 1 or 2 (6.13), W_el,min for Class 3 (6.14), W_eff,min for Class 4 (6.15).

    Class 1 or 2 without a plastic modulus, e.g angles, whose tables give W_el only, take W_el,min (6.14): the elastic
    verification of 6.2.1(4) is permitted for all classes, and is conservative.
    """
    match _as_section_class(section_class):
        case SectionClass.CLASS_1 | SectionClass.CLASS_2:
            if W_pl is None and W_el is not None:
                return _require_positive(W_el, "W_el,min"), "6.14" # 6.2.1(4)
            return _require_positive(W_pl, "W_pl (Class 1 or 2)"), "6.13"
        case SectionClass.CLASS_3:
            return _require_positive(W_el, "W_el,min (Class 3)"), "6.14"
        case _:
            return _class_4_value(W_eff, "W_eff,min", "6.2.2.5"), "6.15"


def bending_resistance(W: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 Equations 6.13 to 6.15: M_c,Rd = W*fy/γM0 (Nmm), with W from section_modulus_for_class()."""
    return _require_positive(W, "W") * _require_positive(fy, "fy") / gamma_M0


def tension_flange_holes_negligible(A_f: float, A_f_net: float, fy: float, fu: float, gamma_M0: float = GAMMA_M0, gamma_M2: float = GAMMA_M2) -> bool:
    """EN 1993-1-1 Equation 6.16: fastener holes in the tension flange may be ignored if 0.9*A_f,net*fu/γM2 >= A_f*fy/γM0.

    Per 6.2.5(5), the same limit applied to the whole tension zone (flange plus tension zone of the web) covers web holes.
    """
    return 0.9 * _require_positive(A_f_net, "A_f_net") * fu / gamma_M2 >= _require_positive(A_f, "A_f") * fy / gamma_M0


def bending_utilisation(M_Ed: float, M_c_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.12: M_Ed/M_c,Rd <= 1.0."""
    return _utilisation_check(M_Ed, M_c_Rd, "6.2.5", "6.12", "Bending moment")


class BendingResult(BaseModel):
    # 6.2.5 Bending moment about one principal axis; for bending about both axes, see 6.2.9 and check_cross_section()
    M_c_Rd: float # (6.13) to (6.15), Nmm
    axis: BendingAxis
    section_class: SectionClass # 5.5, under bending about `axis`
    W: float # mm³; W_pl, W_el,min or W_eff,min
    fy: float # N/mm²
    M_Ed: Optional[float] = None # design bending moment, Nmm
    utilisation: Optional[UtilisationCheck] = None # (6.12)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_bending(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    axis: BendingAxis = "y",
    M_Ed: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    W_pl: Optional[float] = None,
    W_el: Optional[float] = None,
    W_eff: Optional[float] = None,
    gamma_M0: float = GAMMA_M0,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> BendingResult:
    """EN 1993-1-1 6.2.5: Design resistance for bending about one principal axis, M_c,Rd.

    Args:
        section: EU/UK section; classified under bending about `axis` unless `section_class` is given
        fy: Yield strength (N/mm²)
        axis: "y" (major) or "z" (minor)
        M_Ed: Design bending moment (Nmm)
        section_class: Class to use instead of classifying
        W_pl, W_el: Plastic and minimum elastic moduli about `axis` (mm³); override the section values
        W_eff: Minimum effective modulus for Class 4 (mm³), from EN 1993-1-5
        gamma_M0: Partial factor for resistance of cross-sections
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if axis not in ("y", "z"):
        raise ValueError("axis must be 'y' or 'z'.")
    section_type, data, raw = _section_data(section, section_type, properties)
    pattern: StressPattern = StressPattern.MAJOR_AXIS_BENDING if axis == "y" else StressPattern.MINOR_AXIS_BENDING
    cls: SectionClass = _as_section_class(section_class) if section_class is not None else _classify(section, section_type, raw, fy, pattern)
    W, equation = section_modulus_for_class(
        cls,
        W_pl=W_pl if W_pl is not None else data.get(f"W_pl_{axis}"),
        W_el=W_el if W_el is not None else data.get(f"W_el_{axis}"),
        W_eff=W_eff,
    )
    M_c_Rd: float = bending_resistance(W, fy, gamma_M0)
    return BendingResult(
        M_c_Rd=M_c_Rd,
        axis=axis,
        section_class=cls,
        W=W,
        fy=fy,
        M_Ed=M_Ed,
        utilisation=bending_utilisation(M_Ed, M_c_Rd) if M_Ed is not None else None,
        reference=_reference("6.2.5", equation, "Bending moment"),
    )


# --- 6.2.6 Shear ---
def _shear_area_shape(section_type: Optional[SectionType], welded: bool) -> ShearAreaShape:
    family: str = _family(section_type)
    if family == "I":
        return "welded_I" if welded else "rolled_I"
    if family == "channel":
        return "welded_channel" if welded else "rolled_channel"
    if family == "RHS":
        return "RHS"
    if family == "CHS":
        return "CHS"
    raise NotImplementedError(
        f"6.2.6(3) gives no shear area for section type '{section_type.value if section_type else None}'; pass A_v directly or a `shape`."
    )


def _shear_area(data: dict[str, float], shape: ShearAreaShape, direction: ShearDirection, eta: float) -> float:
    A: float = _get(data, "A")
    match shape, direction:
        case "rolled_I", "z":
            # a) rolled I and H sections, load parallel to web; not less than eta*h_w*t_w
            b, t_f, t_w, r = _get(data, "b"), _get(data, "t_f"), _get(data, "t_w"), data.get("r", 0.0)
            return max(A - 2.0 * b * t_f + (t_w + 2.0 * r) * t_f, eta * _web_depth(data) * t_w)
        case "rolled_channel", "z":
            # b) rolled channel sections, load parallel to web
            b, t_f, t_w, r = _get(data, "b"), _get(data, "t_f"), _get(data, "t_w"), data.get("r", 0.0)
            return A - 2.0 * b * t_f + (t_w + r) * t_f
        case "rolled_T", "z":
            # c) rolled T-sections, load parallel to web
            b, t_f, t_w, r = _get(data, "b"), _get(data, "t_f"), _get(data, "t_w"), data.get("r", 0.0)
            return A - b * t_f + (t_w + 2.0 * r) * t_f / 2.0
        case "welded_T", "z":
            # c) welded T-sections, load parallel to web
            return _get(data, "t_w") * (_get(data, "h") - _get(data, "t_f") / 2.0)
        case "welded_I", "z":
            # d) welded I and H sections, load parallel to web
            return eta * _web_depth(data) * _get(data, "t_w")
        case "welded_box", "z":
            # d) welded box sections, load parallel to the two webs
            return eta * 2.0 * _web_depth(data) * _get(data, "t_w")
        case "welded_I" | "welded_channel" | "rolled_I" | "rolled_channel", "y":
            # e) welded I, H and channel sections, load parallel to flanges; also used for rolled sections
            return A - _web_depth(data) * _get(data, "t_w")
        case "welded_box", "y":
            # e) welded box sections, load parallel to flanges
            return A - 2.0 * _web_depth(data) * _get(data, "t_w")
        case "RHS", "z":
            # f) rolled rectangular hollow sections of uniform thickness, load parallel to depth
            h, b = _get(data, "h"), _get(data, "b")
            return A * h / (b + h)
        case "RHS", "y":
            # f) load parallel to width
            h, b = _get(data, "h"), _get(data, "b")
            return A * b / (b + h)
        case "CHS", _:
            # g) circular hollow sections and tubes of uniform thickness
            return 2.0 * A / math.pi
        case _:
            raise NotImplementedError(f"6.2.6(3) gives no shear area for shape '{shape}' with the load parallel to '{direction}'.")


def shear_area(
    section: Optional[BaseSection] = None,
    direction: ShearDirection = "z",
    shape: Optional[ShearAreaShape] = None,
    welded: bool = False,
    eta: float = ETA,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> float:
    """EN 1993-1-1 6.2.6(3): Shear area A_v (mm²).

    a) rolled I and H, load parallel to web: A - 2b*tf + (tw + 2r)tf, but not less than eta*hw*tw
    b) rolled channels, load parallel to web: A - 2b*tf + (tw + r)tf
    c) rolled T: A - b*tf + (tw + 2r)tf/2; welded T: tw(h - tf/2)
    d) welded I, H and box, load parallel to web: eta*Σ(hw*tw)
    e) welded I, H, channel and box, load parallel to flanges: A - Σ(hw*tw); also used here for rolled I and channels
    f) rolled RHS of uniform thickness: A*h/(b + h) parallel to depth, A*b/(b + h) parallel to width
    g) CHS and tubes of uniform thickness: 2A/π

    with hw = h - 2tf.

    Args:
        section: EU/UK section
        direction: "z", load parallel to the web or depth (V_z,Ed); "y", parallel to the flanges or width (V_y,Ed)
        shape: Override the shape inferred from the section type, e.g "welded_box" or "rolled_T"
        welded: Treat I, H and channel sections as welded
        eta: η of EN 1993-1-5; 6.2.6(3) NOTE: may conservatively be taken as 1.0
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    return _shear_area(data, shape or _shear_area_shape(section_type, welded), direction, eta)


def plastic_shear_resistance(A_v: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 Equation 6.18: Design plastic shear resistance without torsion, V_pl,Rd = A_v*(fy/√3)/γM0 (N)."""
    return _require_positive(A_v, "A_v") * _require_positive(fy, "fy") / math.sqrt(3.0) / gamma_M0


def shear_utilisation(V_Ed: float, V_c_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.17: V_Ed/V_c,Rd <= 1.0; V_c,Rd is V_pl,Rd for plastic design, or V_pl,T,Rd with torsion (6.25)."""
    return _utilisation_check(V_Ed, V_c_Rd, "6.2.6", "6.17", "Shear")


def elastic_shear_stress(V_Ed: float, S: float, I: float, t: float) -> float:
    """EN 1993-1-1 Equation 6.20: Shear stress at a point, tau_Ed = V_Ed*S/(I*t) (N/mm²).

    Args:
        V_Ed: Design shear force (N)
        S: First moment of area about the centroidal axis of the part between the point and the boundary (mm³)
        I: Second moment of area of the whole cross-section (mm⁴)
        t: Thickness at the point (mm)
    """
    return V_Ed * S / (_require_positive(I, "I") * _require_positive(t, "t"))


def elastic_shear_utilisation(tau_Ed: float, fy: float, gamma_M0: float = GAMMA_M0) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.19: tau_Ed/(fy/(√3*γM0)) <= 1.0, for elastic design where 6.17 cannot be used."""
    return _utilisation_check(tau_Ed, _require_positive(fy, "fy") / (math.sqrt(3.0) * gamma_M0), "6.2.6(4)", "6.19", "Elastic shear")


def web_shear_stress(V_Ed: float, A_f: float, A_w: float) -> float:
    """EN 1993-1-1 Equation 6.21: Shear stress in the web of I- or H-sections, tau_Ed = V_Ed/A_w, valid for A_f/A_w >= 0.6.

    Args:
        V_Ed: Design shear force (N)
        A_f: Area of one flange (mm²)
        A_w: Area of the web, h_w*t_w (mm²)
    """
    if _require_positive(A_f, "A_f") / _require_positive(A_w, "A_w") < 0.6:
        raise ValueError("Equation 6.21 needs A_f/A_w >= 0.6; use elastic_shear_stress() (6.20).")
    return V_Ed / A_w


def shear_buckling_check_required(h_w: float, t_w: float, fy: float, eta: float = ETA) -> bool:
    """EN 1993-1-1 Equation 6.22: webs without intermediate stiffeners need a shear buckling check to EN 1993-1-5 section 5
    when h_w/t_w > 72ε/η."""
    return _require_positive(h_w, "h_w") / _require_positive(t_w, "t_w") > 72.0 * _epsilon(fy) / eta


# --- 6.2.7 Torsion ---
def torsion_utilisation(T_Ed: float, T_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.23: T_Ed/T_Rd <= 1.0, with T_Ed = T_t,Ed + T_w,Ed (6.24)."""
    return _utilisation_check(T_Ed, T_Rd, "6.2.7", "6.23", "Torsion")


def st_venant_shear_stress(T_t_Ed: float, W_t: Optional[float] = None, I_t: Optional[float] = None, t: Optional[float] = None) -> float:
    """EN 1993-1-1 6.2.7(4): Shear stress tau_t,Ed due to St. Venant torsion (N/mm²).

    Closed hollow sections: T_t,Ed/W_t, with the torsional modulus W_t of the section tables.
    Open sections: T_t,Ed*t/I_t, at the thickest part t.

    Args:
        T_t_Ed: St. Venant torsional moment (Nmm)
        W_t: Torsional section modulus of a hollow section (mm³)
        I_t: St. Venant torsional constant (mm⁴)
        t: Thickness of the part (mm), with I_t
    """
    if W_t is not None:
        return T_t_Ed / _require_positive(W_t, "W_t")
    if I_t is not None and t is not None:
        return T_t_Ed * _require_positive(t, "t") / _require_positive(I_t, "I_t")
    raise ValueError("Pass W_t (closed sections), or I_t and t (open sections).")


def hollow_section_torsional_resistance(W_t: float, fy: float, gamma_M0: float = GAMMA_M0) -> float:
    """EN 1993-1-1 6.2.7(7) and (8): Elastic St. Venant torsional resistance of a closed hollow section, warping neglected,
    T_Rd = W_t*fy/(√3*γM0) (Nmm)."""
    return _require_positive(W_t, "W_t") * _require_positive(fy, "fy") / (math.sqrt(3.0) * gamma_M0)


def shear_resistance_with_torsion(
    V_pl_Rd: float,
    fy: float,
    tau_t_Ed: float,
    tau_w_Ed: float = 0.0,
    shape: TorsionShape = "I",
    gamma_M0: float = GAMMA_M0,
) -> float:
    """EN 1993-1-1 Equations 6.26 to 6.28: Plastic shear resistance reduced for torsion, V_pl,T,Rd (N).

    I or H section (6.26): sqrt(1 - τt/(1.25*fy/(√3γM0)))*V_pl,Rd
    Channel (6.27): (sqrt(1 - τt/(1.25*fy/(√3γM0))) - τw/(fy/(√3γM0)))*V_pl,Rd
    Structural hollow section (6.28): (1 - τt/(fy/(√3γM0)))*V_pl,Rd

    Args:
        V_pl_Rd: Plastic shear resistance, 6.2.6 (N)
        fy: Yield strength (N/mm²)
        tau_t_Ed: Shear stress due to St. Venant torsion (N/mm²)
        tau_w_Ed: Shear stress due to warping torsion (N/mm²); channels only
        shape: "I", "channel" or "hollow"
        gamma_M0: Partial factor for resistance of cross-sections
    """
    f_v: float = _require_positive(fy, "fy") / (math.sqrt(3.0) * gamma_M0)
    tau_t, tau_w = abs(tau_t_Ed), abs(tau_w_Ed)
    match shape:
        case "I":
            factor = math.sqrt(max(1.0 - tau_t / (1.25 * f_v), 0.0)) # (6.26)
        case "channel":
            factor = math.sqrt(max(1.0 - tau_t / (1.25 * f_v), 0.0)) - tau_w / f_v # (6.27)
        case "hollow":
            factor = 1.0 - tau_t / f_v # (6.28)
        case _:
            raise ValueError("shape must be 'I', 'channel' or 'hollow'.")
    return max(factor, 0.0) * V_pl_Rd


class ShearResult(BaseModel):
    # 6.2.6 Shear; 6.2.7(9) with torsion; rho per 6.2.8 for the bending resistance
    V_c_Rd: float # N; V_pl,Rd (6.18), or V_pl,T,Rd (6.26 to 6.28) with torsion
    V_pl_Rd: float # (6.18), N
    V_pl_T_Rd: Optional[float] = None # (6.26) to (6.28), N
    A_v: float # shear area, mm²; 6.2.6(3)
    direction: ShearDirection
    fy: float # N/mm²
    h_w_over_t_w: Optional[float] = None # (6.22), web slenderness of I, H and channel sections loaded parallel to the web
    shear_buckling_check_required: Optional[bool] = None # (6.22): verify to EN 1993-1-5 section 5 (not implemented)
    V_Ed: Optional[float] = None # design shear force, N
    high_shear: Optional[bool] = None # 6.2.8(2): V_Ed > 0.5*V_c,Rd, so the moment resistance is reduced
    rho: Optional[float] = None # (6.29)
    utilisation: Optional[UtilisationCheck] = None # (6.17) or (6.25)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_shear(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    direction: ShearDirection = "z",
    V_Ed: Optional[float] = None,
    A_v: Optional[float] = None,
    shape: Optional[ShearAreaShape] = None,
    welded: bool = False,
    eta: float = ETA,
    tau_t_Ed: Optional[float] = None,
    tau_w_Ed: float = 0.0,
    gamma_M0: float = GAMMA_M0,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ShearResult:
    """EN 1993-1-1 6.2.6: Design plastic shear resistance V_pl,Rd, reduced for torsion to 6.2.7(9) when tau_t_Ed is given.

    Args:
        section: EU/UK section
        fy: Yield strength (N/mm²)
        direction: "z", load parallel to the web or depth; "y", parallel to the flanges or width
        V_Ed: Design shear force (N)
        A_v: Shear area (mm²); overrides shear_area()
        shape: Override the shape used for the shear area, see shear_area()
        welded: Treat I, H and channel sections as welded
        eta: η of EN 1993-1-5; 1.0 per the 6.2.6(3) NOTE
        tau_t_Ed: Shear stress due to St. Venant torsion (N/mm²), see st_venant_shear_stress()
        tau_w_Ed: Shear stress due to warping torsion (N/mm²); channels only
        gamma_M0: Partial factor for resistance of cross-sections
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, _ = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    shape_value: Optional[ShearAreaShape] = shape
    if A_v is None:
        shape_value = shape or _shear_area_shape(section_type, welded)
        A_v = _shear_area(data, shape_value, direction, eta)
    V_pl_Rd: float = plastic_shear_resistance(A_v, fy, gamma_M0)

    V_pl_T_Rd: Optional[float] = None
    if tau_t_Ed is not None:
        torsion_shape: TorsionShape = "hollow" if family in ("RHS", "CHS", "EHS") else ("channel" if family == "channel" else "I")
        V_pl_T_Rd = shear_resistance_with_torsion(V_pl_Rd, fy, tau_t_Ed, tau_w_Ed, torsion_shape, gamma_M0)
    V_c_Rd: float = V_pl_T_Rd if V_pl_T_Rd is not None else V_pl_Rd

    h_w_over_t_w: Optional[float] = None
    buckling: Optional[bool] = None
    if direction == "z" and family in ("I", "channel") and all(key in data for key in ("h", "t_f", "t_w")):
        h_w_over_t_w = _web_depth(data) / data["t_w"]
        buckling = shear_buckling_check_required(_web_depth(data), data["t_w"], fy, eta)

    utilisation: Optional[UtilisationCheck] = None
    rho: Optional[float] = None
    if V_Ed is not None:
        utilisation = (
            _utilisation_check(V_Ed, V_c_Rd, "6.2.7(9)", "6.25", "Shear and torsion")
            if V_pl_T_Rd is not None
            else shear_utilisation(V_Ed, V_c_Rd)
        )
        rho = shear_reduction_factor(V_Ed, V_c_Rd)

    return ShearResult(
        V_c_Rd=V_c_Rd,
        V_pl_Rd=V_pl_Rd,
        V_pl_T_Rd=V_pl_T_Rd,
        A_v=A_v,
        direction=direction,
        fy=fy,
        h_w_over_t_w=h_w_over_t_w,
        shear_buckling_check_required=buckling,
        V_Ed=V_Ed,
        high_shear=(abs(V_Ed) > 0.5 * V_c_Rd) if V_Ed is not None else None,
        rho=rho,
        utilisation=utilisation,
        reference=_reference("6.2.6", "6.18", "Shear"),
        metadata={"shape": shape_value} if shape_value else {},
    )


# --- 6.2.8 Bending and shear ---
def shear_reduction_factor(V_Ed: float, V_pl_Rd: float) -> float:
    """EN 1993-1-1 6.2.8(2) to (4) and Equation 6.29: rho = (2V_Ed/V_pl,Rd - 1)², or 0 when V_Ed <= 0.5*V_pl,Rd.

    With torsion, pass V_pl,T,Rd as V_pl_Rd (6.2.8(4)).
    """
    ratio: float = abs(V_Ed) / _require_positive(V_pl_Rd, "V_pl_Rd")
    if ratio <= 0.5:
        return 0.0
    return min((2.0 * ratio - 1.0) ** 2, 1.0)


def reduced_yield_strength(fy: float, rho: float) -> float:
    """EN 1993-1-1 Equation 6.29: Reduced yield strength (1 - rho)*fy for the shear area (N/mm²)."""
    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho must be between 0 and 1.")
    return (1.0 - rho) * fy


def i_section_shear_reduced_moment_resistance(
    W_pl_y: float,
    A_w: float,
    t_w: float,
    fy: float,
    rho: float,
    M_y_c_Rd: Optional[float] = None,
    gamma_M0: float = GAMMA_M0,
) -> float:
    """EN 1993-1-1 Equation 6.30: I-sections with equal flanges, major axis, M_y,V,Rd = (W_pl,y - rho*A_w²/(4t_w))*fy/γM0 <= M_y,c,Rd.

    Args:
        W_pl_y: Plastic section modulus, major axis (mm³)
        A_w: Web area, h_w*t_w (mm²)
        t_w: Web thickness (mm)
        fy: Yield strength (N/mm²)
        rho: Reduction factor, see shear_reduction_factor()
        M_y_c_Rd: Moment resistance from 6.2.5(2) (Nmm); defaults to W_pl,y*fy/γM0
        gamma_M0: Partial factor for resistance of cross-sections
    """
    M_y_V_Rd: float = (_require_positive(W_pl_y, "W_pl_y") - rho * A_w**2 / (4.0 * _require_positive(t_w, "t_w"))) * fy / gamma_M0
    cap: float = M_y_c_Rd if M_y_c_Rd is not None else W_pl_y * fy / gamma_M0
    return max(min(M_y_V_Rd, cap), 0.0)


# --- 6.2.9 Bending and axial force ---
def rectangular_reduced_moment_resistance(M_pl_Rd: float, N_Ed: float, N_pl_Rd: float) -> float:
    """EN 1993-1-1 Equation 6.32: Rectangular solid section without fastener holes, M_N,Rd = M_pl,Rd*[1 - (N_Ed/N_pl,Rd)²] (Nmm)."""
    n: float = abs(N_Ed) / _require_positive(N_pl_Rd, "N_pl_Rd")
    return max(M_pl_Rd * (1.0 - n**2), 0.0)


def axial_force_negligible(
    N_Ed: float,
    N_pl_Rd: float,
    h_w: float,
    t_w: float,
    fy: float,
    axis: BendingAxis = "y",
    gamma_M0: float = GAMMA_M0,
) -> bool:
    """EN 1993-1-1 6.2.9.1(4): doubly symmetrical I- and H-sections need no allowance for axial force on M_pl,Rd when

    y-y: N_Ed <= 0.25*N_pl,Rd (6.33) and N_Ed <= 0.5*h_w*t_w*fy/γM0 (6.34)
    z-z: N_Ed <= h_w*t_w*fy/γM0 (6.35)
    """
    N: float = abs(N_Ed)
    web: float = _require_positive(h_w, "h_w") * _require_positive(t_w, "t_w") * fy / gamma_M0
    if axis == "y":
        return N <= 0.25 * N_pl_Rd and N <= 0.5 * web
    return N <= web


def i_section_reduced_moment_resistances(
    M_pl_y_Rd: float,
    M_pl_z_Rd: float,
    N_Ed: float,
    N_pl_Rd: float,
    A: float,
    b: float,
    t_f: float,
) -> tuple[float, float]:
    """EN 1993-1-1 6.2.9.1(5), Equations 6.36 to 6.38: (M_N,y,Rd, M_N,z,Rd) of rolled, or welded equal-flange, I and H sections.

    M_N,y,Rd = M_pl,y,Rd(1 - n)/(1 - 0.5a) <= M_pl,y,Rd (6.36)
    M_N,z,Rd = M_pl,z,Rd for n <= a (6.37), else M_pl,z,Rd[1 - ((n - a)/(1 - a))²] (6.38)

    where n = N_Ed/N_pl,Rd and a = (A - 2b*t_f)/A <= 0.5; fastener holes are not accounted for.
    """
    n: float = min(abs(N_Ed) / _require_positive(N_pl_Rd, "N_pl_Rd"), 1.0)
    A = _require_positive(A, "A")
    a: float = min((A - 2.0 * b * t_f) / A, 0.5)
    M_N_y_Rd: float = min(M_pl_y_Rd * (1.0 - n) / (1.0 - 0.5 * a), M_pl_y_Rd) # (6.36)
    M_N_z_Rd: float = M_pl_z_Rd if n <= a else M_pl_z_Rd * (1.0 - ((n - a) / (1.0 - a)) ** 2) # (6.37), (6.38)
    return M_N_y_Rd, max(M_N_z_Rd, 0.0)


def box_reduced_moment_resistances(
    M_pl_y_Rd: float,
    M_pl_z_Rd: float,
    N_Ed: float,
    N_pl_Rd: float,
    A: float,
    b: float,
    h: float,
    t_f: float,
    t_w: Optional[float] = None,
) -> tuple[float, float]:
    """EN 1993-1-1 6.2.9.1(5), Equations 6.39 and 6.40: (M_N,y,Rd, M_N,z,Rd) of RHS of uniform thickness and welded boxes.

    M_N,y,Rd = M_pl,y,Rd(1 - n)/(1 - 0.5a_w) <= M_pl,y,Rd (6.39)
    M_N,z,Rd = M_pl,z,Rd(1 - n)/(1 - 0.5a_f) <= M_pl,z,Rd (6.40)

    where a_w = (A - 2b*t_f)/A <= 0.5 and a_f = (A - 2h*t_w)/A <= 0.5; for hollow sections t_f = t_w = t.
    """
    n: float = min(abs(N_Ed) / _require_positive(N_pl_Rd, "N_pl_Rd"), 1.0)
    A = _require_positive(A, "A")
    t_w_value: float = t_w if t_w is not None else t_f
    a_w: float = min((A - 2.0 * b * t_f) / A, 0.5)
    a_f: float = min((A - 2.0 * h * t_w_value) / A, 0.5)
    return (
        min(M_pl_y_Rd * (1.0 - n) / (1.0 - 0.5 * a_w), M_pl_y_Rd), # (6.39)
        min(M_pl_z_Rd * (1.0 - n) / (1.0 - 0.5 * a_f), M_pl_z_Rd), # (6.40)
    )


def chs_reduced_moment_resistance(M_pl_Rd: float, N_Ed: float, N_pl_Rd: float) -> float:
    """EN 1993-1-1 6.2.9.1(6): Circular hollow sections, M_N,Rd = M_pl,Rd(1 - n^1.7) (Nmm)."""
    n: float = min(abs(N_Ed) / _require_positive(N_pl_Rd, "N_pl_Rd"), 1.0)
    return M_pl_Rd * (1.0 - n**1.7)


def biaxial_bending_exponents(shape: str, n: float) -> tuple[float, float]:
    """EN 1993-1-1 6.2.9.1(6): (alpha, beta) for Equation 6.41; unity (conservative) for other shapes.

    I and H sections: alpha = 2, beta = 5n >= 1
    Circular hollow sections: alpha = beta = 2
    Rectangular hollow sections: alpha = beta = 1.66/(1 - 1.13n²) <= 6

    Args:
        shape: "I", "CHS" or "RHS"; anything else returns (1, 1)
        n: N_Ed/N_pl,Rd
    """
    n = abs(n)
    match shape:
        case "I":
            return 2.0, max(5.0 * n, 1.0)
        case "CHS":
            return 2.0, 2.0
        case "RHS":
            denominator: float = 1.0 - 1.13 * n**2
            exponent: float = 6.0 if denominator <= 0.0 else min(1.66 / denominator, 6.0)
            return exponent, exponent
        case _:
            return 1.0, 1.0


def biaxial_bending_utilisation(
    M_y_Ed: float,
    M_z_Ed: float,
    M_N_y_Rd: float,
    M_N_z_Rd: float,
    alpha: float = 1.0,
    beta: float = 1.0,
) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.41: [My,Ed/M_N,y,Rd]^alpha + [Mz,Ed/M_N,z,Rd]^beta <= 1, for Class 1 and 2 cross-sections.

    alpha and beta may conservatively be taken as unity; see biaxial_bending_exponents().
    """
    utilisation: float = compute_utilisation(abs(M_y_Ed), M_N_y_Rd) ** alpha + compute_utilisation(abs(M_z_Ed), M_N_z_Rd) ** beta
    return _ratio_check(utilisation, "6.2.9.1(6)", "6.41", "Bi-axial bending", alpha=alpha, beta=beta)


def longitudinal_stress(
    N_Ed: float,
    A: float,
    M_y_Ed: float = 0.0,
    W_y: Optional[float] = None,
    M_z_Ed: float = 0.0,
    W_z: Optional[float] = None,
) -> float:
    """EN 1993-1-1 6.2.9.2: Maximum longitudinal stress sigma_x,Ed = |N_Ed|/A + |My,Ed|/W_y + |Mz,Ed|/W_z (N/mm²).

    The terms are added at the most stressed fibre; use W_el,min (Class 3) or the net/effective values where relevant.
    """
    sigma: float = abs(N_Ed) / _require_positive(A, "A")
    if M_y_Ed != 0.0:
        sigma += abs(M_y_Ed) / _require_positive(W_y, "W_y")
    if M_z_Ed != 0.0:
        sigma += abs(M_z_Ed) / _require_positive(W_z, "W_z")
    return sigma


def longitudinal_stress_utilisation(sigma_x_Ed: float, fy: float, gamma_M0: float = GAMMA_M0) -> UtilisationCheck:
    """EN 1993-1-1 Equations 6.42 and 6.43: sigma_x,Ed <= fy/γM0, in the absence of shear force."""
    return _utilisation_check(sigma_x_Ed, _require_positive(fy, "fy") / gamma_M0, "6.2.9.2", "6.42", "Longitudinal stress")


def class_4_interaction_utilisation(
    N_Ed: float,
    A_eff: float,
    fy: float,
    M_y_Ed: float = 0.0,
    W_eff_y_min: Optional[float] = None,
    M_z_Ed: float = 0.0,
    W_eff_z_min: Optional[float] = None,
    e_N_y: float = 0.0,
    e_N_z: float = 0.0,
    gamma_M0: float = GAMMA_M0,
) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.44: Class 4 cross-sections, with all terms taken as additive (conservative on signs).

    N_Ed/(A_eff*fy/γM0) + (My,Ed + N_Ed*e_Ny)/(W_eff,y,min*fy/γM0) + (Mz,Ed + N_Ed*e_Nz)/(W_eff,z,min*fy/γM0) <= 1

    Args:
        N_Ed: Design axial force (N)
        A_eff: Effective area under uniform compression (mm²)
        fy: Yield strength (N/mm²)
        M_y_Ed, M_z_Ed: Design moments (Nmm)
        W_eff_y_min, W_eff_z_min: Effective moduli under the moment alone, at the fibre of maximum elastic stress (mm³)
        e_N_y, e_N_z: Shifts of the centroidal axes under compression only, 6.2.2.5(4) (mm)
        gamma_M0: Partial factor for resistance of cross-sections
    """
    f: float = _require_positive(fy, "fy") / gamma_M0
    utilisation: float = abs(N_Ed) / (_require_positive(A_eff, "A_eff") * f)
    M_y: float = abs(M_y_Ed) + abs(N_Ed * e_N_y)
    M_z: float = abs(M_z_Ed) + abs(N_Ed * e_N_z)
    if M_y != 0.0:
        utilisation += M_y / (_require_positive(W_eff_y_min, "W_eff_y_min") * f)
    if M_z != 0.0:
        utilisation += M_z / (_require_positive(W_eff_z_min, "W_eff_z_min") * f)
    return _ratio_check(utilisation, "6.2.9.3(2)", "6.44", "Class 4 bending and axial force")


# --- 6.2.10 Bending, shear and axial force ---
class CrossSectionResult(BaseModel):
    # 6.2 Resistance of cross-sections under N, V and M together, 6.2.1 to 6.2.10; fastener holes are not accounted for
    section_class: Optional[SectionClass] = None # 5.5 under the given actions; None under tension and/or shear only
    method: str # "plastic" (6.31, 6.41), "linear" (6.2), "elastic" (6.42) or "effective" (6.44)
    fy: float # N/mm²
    N_Ed: float # N; compression positive
    M_y_Ed: float # Nmm
    M_z_Ed: float # Nmm
    V_y_Ed: float # N
    V_z_Ed: float # N
    N_Rd: float # N; A*fy/γM0 (6.6, 6.10) or A_eff*fy/γM0 (6.11), with the shear area at (1 - rho)fy (6.2.10(3))
    V_pl_y_Rd: Optional[float] = None # (6.18), N
    V_pl_z_Rd: Optional[float] = None # (6.18), N
    rho_y: float = 0.0 # (6.29)
    rho_z: float = 0.0 # (6.29)
    M_y_Rd: Optional[float] = None # Nmm; M_c,y,Rd reduced for shear (6.2.8) and axial force (6.2.9), e.g M_N,y,Rd
    M_z_Rd: Optional[float] = None # Nmm
    alpha: float = 1.0 # (6.41)
    beta: float = 1.0 # (6.41)
    utilisations: dict[str, float] # every check made, e.g {"N (6.9)": 0.41, "M_y (6.31)": 0.83}
    governing: str # key of the largest utilisation
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_cross_section(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    N_Ed: float = 0.0,
    M_y_Ed: float = 0.0,
    M_z_Ed: float = 0.0,
    V_y_Ed: float = 0.0,
    V_z_Ed: float = 0.0,
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    eta: float = ETA,
    A_eff: Optional[float] = None,
    W_eff_y: Optional[float] = None,
    W_eff_z: Optional[float] = None,
    e_N_y: float = 0.0,
    e_N_z: float = 0.0,
    gamma_M0: float = GAMMA_M0,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> CrossSectionResult:
    """EN 1993-1-1 6.2: Resistance of a cross-section to axial force, shear and bending about both axes.

    - Shear (6.2.6) and, where V_Ed > 0.5*V_pl,Rd, the reduced yield strength (1 - rho)fy on the shear area (6.2.8, 6.2.10);
      for I-sections under V_z by Equation 6.30, otherwise conservatively as (1 - rho) on the whole moment resistance.
    - Class 1 and 2 (6.2.9.1): M_N,Rd for I and H (6.36 to 6.38), RHS (6.39, 6.40) and CHS, with Equation 6.41 for
      bi-axial bending; other shapes use the linear summation of Equation 6.2.
    - Class 3 (6.2.9.2): elastic stresses, Equation 6.42. Class 4 (6.2.9.3): Equation 6.44 with effective properties.

    The class follows the actions unless `section_class` is given; see _class_for_actions(). Fastener holes are not
    accounted for, as 6.2.9.1(5) requires; check net sections with check_tension() and tension_flange_holes_negligible().

    Args:
        section: EU/UK section
        fy: Yield strength (N/mm²)
        N_Ed: Design axial force (N); compression positive, tension negative
        M_y_Ed, M_z_Ed: Design moments about the major and minor axes (Nmm)
        V_y_Ed, V_z_Ed: Design shear forces parallel to the flanges (y) and to the web (z) (N)
        section_class: Class to use instead of classifying
        welded: Treat I, H and channel sections as welded for the shear area
        eta: η of EN 1993-1-5 for the shear area
        A_eff, W_eff_y, W_eff_z: Class 4 effective properties from EN 1993-1-5 (mm², mm³)
        e_N_y, e_N_z: Class 4 shifts of the centroidal axes under compression (mm)
        gamma_M0: Partial factor for resistance of cross-sections
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy = _require_positive(fy, "fy")
    A: float = _get(data, "A")
    cls: Optional[SectionClass] = _class_for_actions(section, section_type, data, raw, fy, N_Ed, M_y_Ed, M_z_Ed, section_class)
    checks: dict[str, tuple[float, str, str]] = {} # name -> (utilisation, clause, equation)
    notes: list[str] = []

    # --- 6.2.6 Shear, and rho for the shear area (6.2.8, 6.2.10)
    V_pl_Rd: dict[str, Optional[float]] = {"y": None, "z": None}
    rho: dict[str, float] = {"y": 0.0, "z": 0.0}
    A_v: dict[str, float] = {"y": 0.0, "z": 0.0}
    shear_actions: tuple[tuple[ShearDirection, float], ...] = (("z", V_z_Ed), ("y", V_y_Ed))
    for direction, V_Ed in shear_actions:
        if V_Ed == 0.0:
            continue
        A_v[direction] = _shear_area(data, _shear_area_shape(section_type, welded), direction, eta)
        V_pl = plastic_shear_resistance(A_v[direction], fy, gamma_M0)
        V_pl_Rd[direction] = V_pl
        rho[direction] = shear_reduction_factor(V_Ed, V_pl)
        checks[f"V_{direction} (6.17)"] = (compute_utilisation(abs(V_Ed), V_pl), "6.2.6", "6.17")
    rho_max: float = max(rho.values())
    if rho_max > 0.0:
        notes.append("6.2.8(3)/6.2.10(3): V_Ed > 0.5*V_pl,Rd; reduced yield strength (1 - rho)fy used on the shear area.")
    A_N: float = max(A - rho["z"] * A_v["z"] - rho["y"] * A_v["y"], 0.0) # 6.2.10(3): the shear area at (1 - rho)fy

    compression: bool = N_Ed > 0.0
    axial_name: str = "N (6.9)" if compression else "N (6.5)"
    method: str = "plastic"
    M_y_Rd: Optional[float] = None
    M_z_Rd: Optional[float] = None
    alpha, beta = 1.0, 1.0

    if cls is None or _is_plastic(cls):
        N_Rd: float = A_N * fy / gamma_M0 # (6.6), (6.10)
        if N_Ed != 0.0:
            checks[axial_name] = (compute_utilisation(abs(N_Ed), N_Rd), "6.2.4" if compression else "6.2.3", "6.9" if compression else "6.5")
        if M_y_Ed != 0.0 or M_z_Ed != 0.0:
            if family == "angle":
                # 6.2.1(4): angle tables give W_el only; the elastic resistance is used, which is conservative
                data = {**data, "W_pl_y": data.get("W_pl_y") or data.get("W_el_y", 0.0), "W_pl_z": data.get("W_pl_z") or data.get("W_el_z", 0.0)}
                notes.append("6.2.1(4): W_pl is not tabulated for angles; W_el used for Class 1 and 2.")
            M_pl_y: float = _get(data, "W_pl_y") * fy / gamma_M0 if M_y_Ed != 0.0 else data.get("W_pl_y", 0.0) * fy / gamma_M0 # (6.13)
            M_pl_z: float = _get(data, "W_pl_z") * fy / gamma_M0 if M_z_Ed != 0.0 else data.get("W_pl_z", 0.0) * fy / gamma_M0 # (6.13)
            # 6.2.8 Bending and shear
            if family == "I" and rho["z"] > 0.0 and M_pl_y > 0.0:
                M_pl_y = i_section_shear_reduced_moment_resistance(data["W_pl_y"], _web_depth(data) * _get(data, "t_w"), data["t_w"], fy, rho["z"], M_pl_y, gamma_M0) # (6.30)
                M_pl_y *= 1.0 - rho["y"] # flanges carry V_y and most of M_y
                M_pl_z *= 1.0 - rho_max
            else:
                M_pl_y *= 1.0 - rho_max
                M_pl_z *= 1.0 - rho_max
            # 6.2.9.1 Bending and axial force
            n: float = abs(N_Ed) / N_Rd if N_Rd > 0.0 else math.inf
            if N_Ed == 0.0:
                M_y_Rd, M_z_Rd = M_pl_y, M_pl_z
            elif family == "I":
                M_y_Rd, M_z_Rd = i_section_reduced_moment_resistances(M_pl_y, M_pl_z, N_Ed, N_Rd, A, _get(data, "b"), _get(data, "t_f"))
                h_w, t_w = _web_depth(data), _get(data, "t_w")
                if axial_force_negligible(N_Ed, N_Rd, h_w, t_w, fy, "y", gamma_M0):
                    M_y_Rd = M_pl_y # (6.33), (6.34)
                if axial_force_negligible(N_Ed, N_Rd, h_w, t_w, fy, "z", gamma_M0):
                    M_z_Rd = M_pl_z # (6.35)
            elif family == "RHS":
                t: float = _get(data, "t")
                M_y_Rd, M_z_Rd = box_reduced_moment_resistances(M_pl_y, M_pl_z, N_Ed, N_Rd, A, _get(data, "b"), _get(data, "h"), t, t)
            elif family == "CHS":
                M_y_Rd = chs_reduced_moment_resistance(M_pl_y, N_Ed, N_Rd)
                M_z_Rd = chs_reduced_moment_resistance(M_pl_z, N_Ed, N_Rd)
            else:
                method = "linear"
                M_y_Rd, M_z_Rd = M_pl_y, M_pl_z

            if method == "linear":
                linear: float = compute_utilisation(abs(N_Ed), N_Rd)
                if M_y_Ed != 0.0:
                    linear += compute_utilisation(abs(M_y_Ed), M_y_Rd)
                if M_z_Ed != 0.0:
                    linear += compute_utilisation(abs(M_z_Ed), M_z_Rd)
                checks["N + M (6.2)"] = (linear, "6.2.1(7)", "6.2")
                notes.append("6.2.9.1: no M_N,Rd approximation for this shape; linear summation (6.2) used.")
            elif M_y_Ed != 0.0 and M_z_Ed != 0.0:
                alpha, beta = biaxial_bending_exponents(family, n)
                biaxial: float = compute_utilisation(abs(M_y_Ed), M_y_Rd) ** alpha + compute_utilisation(abs(M_z_Ed), M_z_Rd) ** beta
                checks["M_y + M_z (6.41)"] = (biaxial, "6.2.9.1(6)", "6.41")
            elif M_y_Ed != 0.0:
                checks["M_y (6.31)"] = (compute_utilisation(abs(M_y_Ed), M_y_Rd), "6.2.9.1", "6.31" if N_Ed != 0.0 else "6.12")
            else:
                checks["M_z (6.31)"] = (compute_utilisation(abs(M_z_Ed), M_z_Rd), "6.2.9.1", "6.31" if N_Ed != 0.0 else "6.12")

    elif cls == SectionClass.CLASS_3:
        method = "elastic"
        fy_V: float = reduced_yield_strength(fy, rho_max) # conservative: (1 - rho)fy on the whole section
        N_Rd = A * fy_V / gamma_M0
        W_y: Optional[float] = _get(data, "W_el_y") if M_y_Ed != 0.0 else data.get("W_el_y")
        W_z: Optional[float] = _get(data, "W_el_z") if M_z_Ed != 0.0 else data.get("W_el_z")
        M_y_Rd = W_y * fy_V / gamma_M0 if W_y else None # (6.14)
        M_z_Rd = W_z * fy_V / gamma_M0 if W_z else None
        if N_Ed != 0.0:
            checks[axial_name] = (compute_utilisation(abs(N_Ed), N_Rd), "6.2.4" if compression else "6.2.3", "6.9" if compression else "6.5")
        if M_y_Ed != 0.0 or M_z_Ed != 0.0:
            sigma: float = longitudinal_stress(N_Ed, A, M_y_Ed, W_y, M_z_Ed, W_z)
            checks["N + M (6.42)"] = (compute_utilisation(sigma, fy_V / gamma_M0), "6.2.9.2", "6.42")

    else:
        method = "effective"
        fy_V = reduced_yield_strength(fy, rho_max)
        A_c: float = _class_4_value(A_eff, "A_eff", "6.2.2.5") if compression else A
        N_Rd = A_c * fy_V / gamma_M0 # (6.11)
        if N_Ed != 0.0:
            checks["N (6.11)" if compression else axial_name] = (compute_utilisation(abs(N_Ed), N_Rd), "6.2.4" if compression else "6.2.3", "6.9" if compression else "6.5")
        e_y, e_z = (e_N_y, e_N_z) if compression else (0.0, 0.0)
        if M_y_Ed != 0.0 or M_z_Ed != 0.0 or e_y != 0.0 or e_z != 0.0:
            W_eff_y_value: Optional[float] = _class_4_value(W_eff_y, "W_eff_y", "6.2.2.5") if (M_y_Ed != 0.0 or e_y != 0.0) else None
            W_eff_z_value: Optional[float] = _class_4_value(W_eff_z, "W_eff_z", "6.2.2.5") if (M_z_Ed != 0.0 or e_z != 0.0) else None
            M_y_Rd = W_eff_y_value * fy_V / gamma_M0 if W_eff_y_value else None # (6.15)
            M_z_Rd = W_eff_z_value * fy_V / gamma_M0 if W_eff_z_value else None
            check = class_4_interaction_utilisation(N_Ed, A_c, fy_V, M_y_Ed, W_eff_y_value, M_z_Ed, W_eff_z_value, e_y, e_z, gamma_M0)
            checks["N + M (6.44)"] = (check.utilisation, "6.2.9.3(2)", "6.44")

    if not checks:
        checks["none"] = (0.0, "6.2", "")
    governing: str = max(checks, key=lambda key: checks[key][0])
    value, clause, equation = checks[governing]
    return CrossSectionResult(
        section_class=cls,
        method=method,
        fy=fy,
        N_Ed=N_Ed,
        M_y_Ed=M_y_Ed,
        M_z_Ed=M_z_Ed,
        V_y_Ed=V_y_Ed,
        V_z_Ed=V_z_Ed,
        N_Rd=N_Rd,
        V_pl_y_Rd=V_pl_Rd["y"],
        V_pl_z_Rd=V_pl_Rd["z"],
        rho_y=rho["y"],
        rho_z=rho["z"],
        M_y_Rd=M_y_Rd,
        M_z_Rd=M_z_Rd,
        alpha=alpha,
        beta=beta,
        utilisations={key: item[0] for key, item in checks.items()},
        governing=governing,
        utilisation=_ratio_check(value, clause, equation or None, f"Cross-section resistance: {governing}"),
        reference=_reference("6.2", title="Resistance of cross-sections"),
        metadata={"notes": notes} if notes else {},
    )


# --- 6.3.1 Uniform members in compression ---
def imperfection_factor(curve: str) -> float:
    """EN 1993-1-1 Table 6.1: Imperfection factor alpha for buckling curve a0, a, b, c or d."""
    return _alpha(curve, IMPERFECTION_FACTORS, "Table 6.1")


def _grade_strength(steel_grade: str) -> float:
    match = re.search(r"\d{3}", steel_grade)
    if match is None:
        raise ValueError(f"Unrecognised steel grade '{steel_grade}'.")
    return float(match.group())


def _buckling_shape(section_type: Optional[SectionType], welded: bool) -> BucklingShape:
    family: str = _family(section_type)
    if family == "I":
        return "welded_I" if welded else "rolled_I"
    if family in ("RHS", "CHS", "EHS"):
        return "cold_formed_hollow" if section_type in (SectionType.CFRHS, SectionType.CFSHS, SectionType.CFCHS) else "hot_finished_hollow"
    if family == "channel":
        return "U"
    if family == "angle":
        return "L"
    raise NotImplementedError(
        f"Table 6.2 has no buckling curve for section type '{section_type.value if section_type else None}'; pass `shape` or the curve."
    )


def buckling_curve(
    section_type: Optional[SectionType] = None,
    axis: str = "z",
    h: Optional[float] = None,
    b: Optional[float] = None,
    t_f: Optional[float] = None,
    fy: float = 355.0,
    steel_grade: Optional[str] = None,
    welded: bool = False,
    thick_welds: bool = False,
    shape: Optional[BucklingShape] = None,
) -> str:
    """EN 1993-1-1 Table 6.2: Selection of the flexural buckling curve for a cross-section.

    The S460 column applies to grades of 460 N/mm² (from `steel_grade`, else fy >= 460); S235 to S420 use the other.
    Torsional and torsional-flexural buckling use the z-axis curve (6.3.1.4(3)).

    Args:
        section_type: Section type; rolled I/H, hollow (hot finished or cold formed), channels (U) and angles (L)
        axis: "y", "z", "v" (angles) or "T"/"TF" (torsional modes, read as "z")
        h, b, t_f: Depth, width and flange thickness (mm); rolled and welded I-sections only
        fy: Yield strength (N/mm²)
        steel_grade: e.g "S460"; selects the S460 column
        welded: Welded I-section
        thick_welds: Welded box with a > 0.5t_f, b/t_f < 30 and h/t_w < 30 (curve c)
        shape: Override the shape inferred from the section type, e.g "welded_box", "T" or "solid"
    """
    shape_value: BucklingShape = shape or _buckling_shape(section_type, welded)
    s460: bool = (_grade_strength(steel_grade) if steel_grade else fy) >= 460.0
    major: bool = axis == "y"
    match shape_value:
        case "rolled_I":
            if h is None or b is None or t_f is None:
                raise ValueError("h, b and t_f are required for rolled I- and H-sections (Table 6.2).")
            if h / b > 1.2:
                if t_f <= 40.0:
                    return ("a0" if s460 else "a") if major else ("a0" if s460 else "b")
                if t_f <= 100.0:
                    return ("a" if s460 else "b") if major else ("a" if s460 else "c")
                raise ValueError("Table 6.2 gives no curve for rolled sections with h/b > 1.2 and t_f > 100 mm.")
            if t_f <= 100.0:
                return ("a" if s460 else "b") if major else ("a" if s460 else "c")
            return "c" if s460 else "d"
        case "welded_I":
            if t_f is None:
                raise ValueError("t_f is required for welded I-sections (Table 6.2).")
            if t_f <= 40.0:
                return "b" if major else "c"
            return "c" if major else "d"
        case "hot_finished_hollow":
            return "a0" if s460 else "a"
        case "cold_formed_hollow":
            return "c"
        case "welded_box":
            return "c" if thick_welds else "b"
        case "U" | "T" | "solid":
            return "c"
        case "L":
            return "b"
        case _:
            raise ValueError(f"Unknown buckling shape '{shape_value}'.")


def lambda_1(fy: float, E: float = E_STEEL) -> float:
    """EN 1993-1-1 6.3.1.3(1): lambda_1 = π*sqrt(E/fy) = 93.9ε."""
    return math.pi * math.sqrt(E / _require_positive(fy, "fy"))


def elastic_critical_force(I: float, L_cr: float, E: float = E_STEEL) -> float:
    """Elastic critical force for flexural buckling, N_cr = π²EI/L_cr² (N), on gross properties (6.3.1.2(1))."""
    return math.pi**2 * E * _require_positive(I, "I") / _require_positive(L_cr, "L_cr") ** 2


def non_dimensional_slenderness(A: float, fy: float, N_cr: float) -> float:
    """EN 1993-1-1 Equations 6.50 to 6.53: lambda_bar = sqrt(A*fy/N_cr); pass A_eff as A for Class 4."""
    return math.sqrt(_require_positive(A, "A") * _require_positive(fy, "fy") / _require_positive(N_cr, "N_cr"))


def flexural_slenderness(L_cr: float, i: float, fy: float, E: float = E_STEEL, A_eff_over_A: float = 1.0) -> float:
    """EN 1993-1-1 Equations 6.50 and 6.51: lambda_bar = (L_cr/i)/lambda_1, times sqrt(A_eff/A) for Class 4.

    Args:
        L_cr: Buckling length in the buckling plane (mm)
        i: Radius of gyration about the relevant axis, gross section (mm)
        fy: Yield strength (N/mm²)
        E: Modulus of elasticity (N/mm²)
        A_eff_over_A: A_eff/A for Class 4
    """
    return _require_positive(L_cr, "L_cr") / _require_positive(i, "i") / lambda_1(fy, E) * math.sqrt(A_eff_over_A)


def buckling_reduction_factor(lambda_bar: float, alpha: float | str) -> float:
    """EN 1993-1-1 Equation 6.49: chi = 1/(Phi + sqrt(Phi² - lambda_bar²)) <= 1.0, Phi = 0.5[1 + alpha(lambda_bar - 0.2) + lambda_bar²].

    Args:
        lambda_bar: Non-dimensional slenderness
        alpha: Imperfection factor, or the buckling curve ("a0" to "d", Table 6.1)
    """
    alpha_value: float = _alpha(alpha, IMPERFECTION_FACTORS, "Table 6.1")
    if lambda_bar < 0.0:
        raise ValueError("lambda_bar cannot be negative.")
    Phi: float = _phi(lambda_bar, alpha_value)
    return min(1.0 / (Phi + math.sqrt(Phi**2 - lambda_bar**2)), 1.0)


def buckling_resistance(chi: float, A: float, fy: float, gamma_M1: float = GAMMA_M1) -> float:
    """EN 1993-1-1 Equations 6.47 and 6.48: N_b,Rd = chi*A*fy/γM1 (N); pass A_eff as A for Class 4."""
    return chi * _require_positive(A, "A") * _require_positive(fy, "fy") / gamma_M1


def buckling_negligible(lambda_bar: float, N_Ed: Optional[float] = None, N_cr: Optional[float] = None) -> bool:
    """EN 1993-1-1 6.3.1.2(4): buckling effects may be ignored for lambda_bar <= 0.2 or N_Ed/N_cr <= 0.04."""
    if lambda_bar <= 0.2:
        return True
    return N_Ed is not None and N_cr is not None and abs(N_Ed) / N_cr <= 0.04


def buckling_utilisation(N_Ed: float, N_b_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.46: N_Ed/N_b,Rd <= 1.0."""
    return _utilisation_check(N_Ed, N_b_Rd, "6.3.1.1", "6.46", "Buckling resistance")


def polar_radius_of_gyration(i_y: float, i_z: float, y_0: float = 0.0, z_0: float = 0.0) -> float:
    """Polar radius of gyration about the shear centre, i_0 = sqrt(i_y² + i_z² + y_0² + z_0²) (mm); EN 1993-1-3 6.2.3(5)."""
    return math.sqrt(i_y**2 + i_z**2 + y_0**2 + z_0**2)


def elastic_torsional_buckling_force(I_t: float, I_w: float, L_cr_T: float, i_0: float, E: float = E_STEEL, G: float = G_STEEL) -> float:
    """Elastic torsional buckling force, N_cr,T = (G*I_t + π²E*I_w/L_T²)/i_0² (N); EN 1993-1-3 Equation 6.33a, for 6.3.1.4.

    Args:
        I_t: St. Venant torsional constant (mm⁴)
        I_w: Warping constant (mm⁶)
        L_cr_T: Buckling length for torsional buckling (mm)
        i_0: Polar radius of gyration about the shear centre (mm)
        E, G: Moduli (N/mm²)
    """
    return (G * _require_positive(I_t, "I_t") + math.pi**2 * E * I_w / _require_positive(L_cr_T, "L_cr_T") ** 2) / _require_positive(i_0, "i_0") ** 2


def elastic_torsional_flexural_buckling_force(N_cr_y: float, N_cr_T: float, y_0: float, i_0: float) -> float:
    """Elastic torsional-flexural buckling force of a section symmetric about the y-y axis (N); EN 1993-1-3 Equation 6.35.

    N_cr,TF = N_cr,y/(2β)[1 + N_cr,T/N_cr,y - sqrt((1 - N_cr,T/N_cr,y)² + 4(y_0/i_0)²N_cr,T/N_cr,y)], β = 1 - (y_0/i_0)²

    Args:
        N_cr_y: Flexural buckling force about the axis of symmetry y-y (N)
        N_cr_T: Torsional buckling force (N)
        y_0: Distance from the centroid to the shear centre along the axis of symmetry (mm)
        i_0: Polar radius of gyration about the shear centre (mm)
    """
    ratio: float = _require_positive(N_cr_T, "N_cr_T") / _require_positive(N_cr_y, "N_cr_y")
    offset: float = (y_0 / _require_positive(i_0, "i_0")) ** 2
    beta: float = 1.0 - offset
    return N_cr_y / (2.0 * beta) * (1.0 + ratio - math.sqrt((1.0 - ratio) ** 2 + 4.0 * offset * ratio))


class BucklingModeResult(BaseModel):
    axis: str # "y", "z" or "v" for flexural buckling; "T" torsional, "TF" torsional-flexural (6.3.1.4)
    L_cr: Optional[float] = None # buckling length, mm
    i: Optional[float] = None # radius of gyration, mm
    N_cr: float # elastic critical force, N
    lambda_bar: float # (6.50) to (6.53)
    curve: str # Table 6.2
    alpha: float # Table 6.1
    Phi: float # 6.3.1.2(1)
    chi: float # (6.49)
    N_b_Rd: float # (6.47) or (6.48), N


class BucklingResult(BaseModel):
    # 6.3.1 Uniform members in compression; N_b,Rd is the least over the buckling modes checked
    N_b_Rd: float # N
    limit_state: LimitState # FLEXURAL_BUCKLING, TORSIONAL_BUCKLING or TORSIONAL_FLEXURAL_BUCKLING
    governing_mode: str # axis of the governing mode
    chi: float # governing reduction factor
    section_class: SectionClass # 5.5, under uniform compression; 5.5.2(9) relaxation does not apply (5.5.2(10))
    A: float # mm²; A, or A_eff for Class 4
    fy: float # N/mm²
    modes: list[BucklingModeResult]
    buckling_negligible: Optional[bool] = None # 6.3.1.2(4), every mode, with N_Ed
    N_Ed: Optional[float] = None # design compression force, N
    utilisation: Optional[UtilisationCheck] = None # (6.46)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_buckling_resistance(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    L_cr_y: Optional[float] = None,
    L_cr_z: Optional[float] = None,
    L_cr_v: Optional[float] = None,
    L_cr_T: Optional[float] = None,
    N_Ed: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    A_eff: Optional[float] = None,
    welded: bool = False,
    steel_grade: Optional[str] = None,
    curves: Optional[dict[str, str]] = None,
    y_0: float = 0.0,
    gamma_M1: float = GAMMA_M1,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> BucklingResult:
    """EN 1993-1-1 6.3.1: Buckling resistance N_b,Rd of a uniform member in compression, for every buckling length given.

    Flexural buckling about y, z (and v for angles) uses Table 6.2; torsional buckling (L_cr_T) uses the z-axis curve,
    with N_cr = min(N_cr,TF, N_cr,T) when the shear centre is offset by y_0 (6.3.1.4). Non-symmetric Class 4 members also
    need 6.3.3 or 6.3.4 (6.3.1.1(2)).

    Args:
        section: EU/UK section; classified under uniform compression unless `section_class` is given
        fy: Yield strength (N/mm²)
        L_cr_y, L_cr_z, L_cr_v: Flexural buckling lengths (mm); v is the minor principal axis of angles
        L_cr_T: Torsional buckling length (mm); needs I_t and I_w (0 for hollow sections)
        N_Ed: Design compression force (N)
        section_class: Class to use instead of classifying
        A_eff: Effective area for Class 4 (mm²)
        welded: Welded I-section (Table 6.2)
        steel_grade: e.g "S460"; selects the S460 column of Table 6.2
        curves: Override curves per axis, e.g {"z": "c", "T": "c"}
        y_0: Shear centre offset along the y-y axis of symmetry (mm), for torsional-flexural buckling, e.g channels
        gamma_M1: Partial factor for member instability
        E, G: Moduli (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    fy = _require_positive(fy, "fy")
    cls: SectionClass = _as_section_class(section_class) if section_class is not None else _classify(section, section_type, raw, fy, StressPattern.COMPRESSION)
    A: float = _get(data, "A")
    A_used: float = _class_4_value(A_eff, "A_eff", "6.3.1.1(3)") if cls == SectionClass.CLASS_4 else A
    curves = curves or {}

    def _curve(axis: str) -> str:
        if axis in curves:
            return curves[axis]
        return buckling_curve(section_type, axis, data.get("h"), data.get("b"), data.get("t_f"), fy, steel_grade, welded)

    def _mode(axis: str, N_cr: float, curve: str, L_cr: Optional[float] = None, i: Optional[float] = None) -> BucklingModeResult:
        lambda_bar: float = non_dimensional_slenderness(A_used, fy, N_cr) # (6.50) to (6.53)
        alpha: float = imperfection_factor(curve)
        chi: float = buckling_reduction_factor(lambda_bar, alpha) # (6.49)
        return BucklingModeResult(
            axis=axis,
            L_cr=L_cr,
            i=i,
            N_cr=N_cr,
            lambda_bar=lambda_bar,
            curve=curve,
            alpha=alpha,
            Phi=_phi(lambda_bar, alpha),
            chi=chi,
            N_b_Rd=buckling_resistance(chi, A_used, fy, gamma_M1), # (6.47), (6.48)
        )

    modes: list[BucklingModeResult] = []
    N_cr_y: Optional[float] = None
    for axis, L_cr in (("y", L_cr_y), ("z", L_cr_z), ("v", L_cr_v)):
        if L_cr is None:
            continue
        i_value: Optional[float] = data.get(f"i_{axis}")
        I_value: float = data.get(f"I_{axis}") or A * _get(data, f"i_{axis}") ** 2
        N_cr: float = elastic_critical_force(I_value, L_cr, E)
        if axis == "y":
            N_cr_y = N_cr
        modes.append(_mode(axis, N_cr, _curve(axis), L_cr, i_value or math.sqrt(I_value / A)))

    if L_cr_T is not None:
        i_0: float = polar_radius_of_gyration(_get(data, "i_y"), _get(data, "i_z"), y_0)
        I_w: float = data.get("I_w", 0.0) if _family(section_type) in ("RHS", "CHS", "EHS", "angle") else _get(data, "I_w")
        N_cr_T: float = elastic_torsional_buckling_force(_get(data, "I_t"), I_w, L_cr_T, i_0, E, G)
        if y_0 != 0.0:
            N_cr_y_TF: float = N_cr_y if N_cr_y is not None else elastic_critical_force(_get(data, "I_y"), L_cr_T, E)
            N_cr_TF: float = min(elastic_torsional_flexural_buckling_force(N_cr_y_TF, N_cr_T, y_0, i_0), N_cr_T)
            modes.append(_mode("TF", N_cr_TF, curves.get("TF") or _curve("z"), L_cr_T, i_0))
        else:
            modes.append(_mode("T", N_cr_T, curves.get("T") or _curve("z"), L_cr_T, i_0))

    if not modes:
        raise ValueError("Pass at least one buckling length: L_cr_y, L_cr_z, L_cr_v or L_cr_T.")
    governing: BucklingModeResult = min(modes, key=lambda mode: mode.N_b_Rd)
    limit_state: LimitState = {
        "T": LimitState.TORSIONAL_BUCKLING,
        "TF": LimitState.TORSIONAL_FLEXURAL_BUCKLING,
    }.get(governing.axis, LimitState.FLEXURAL_BUCKLING)

    return BucklingResult(
        N_b_Rd=governing.N_b_Rd,
        limit_state=limit_state,
        governing_mode=governing.axis,
        chi=governing.chi,
        section_class=cls,
        A=A_used,
        fy=fy,
        modes=modes,
        buckling_negligible=all(buckling_negligible(mode.lambda_bar, N_Ed, mode.N_cr) for mode in modes) if N_Ed is not None else None,
        N_Ed=N_Ed,
        utilisation=buckling_utilisation(N_Ed, governing.N_b_Rd) if N_Ed is not None else None,
        reference=_reference("6.3.1", "6.47" if cls != SectionClass.CLASS_4 else "6.48", "Uniform members in compression"),
    )


# --- 6.3.2 Uniform members in bending ---
class MomentDiagram(str, Enum):
    """EN 1993-1-1 Table 6.6: moment distributions between lateral restraints, in the order of the table rows."""
    UNIFORM = "uniform" # psi = 1: k_c = 1.0
    LINEAR = "linear" # end moments M and psi*M, -1 <= psi <= 1: k_c = 1/(1.33 - 0.33psi)
    UDL_SIMPLY_SUPPORTED = "udl-simply-supported" # sagging parabola: 0.94
    UDL_BOTH_ENDS_FIXED = "udl-both-ends-fixed" # parabola with hogging at both ends: 0.90
    UDL_ONE_END_FIXED = "udl-one-end-fixed" # parabola with hogging at one end: 0.91
    POINT_LOAD_SIMPLY_SUPPORTED = "point-load-simply-supported" # central point load, triangle: 0.86
    POINT_LOAD_BOTH_ENDS_FIXED = "point-load-both-ends-fixed" # central point load with hogging at both ends: 0.77
    POINT_LOAD_ONE_END_FIXED = "point-load-one-end-fixed" # central point load with hogging at one end: 0.82


_KC_VALUES: dict[MomentDiagram, float] = {
    MomentDiagram.UDL_SIMPLY_SUPPORTED: 0.94,
    MomentDiagram.UDL_BOTH_ENDS_FIXED: 0.90,
    MomentDiagram.UDL_ONE_END_FIXED: 0.91,
    MomentDiagram.POINT_LOAD_SIMPLY_SUPPORTED: 0.86,
    MomentDiagram.POINT_LOAD_BOTH_ENDS_FIXED: 0.77,
    MomentDiagram.POINT_LOAD_ONE_END_FIXED: 0.82,
}


def correction_factor_kc(diagram: MomentDiagram | str = MomentDiagram.LINEAR, psi: float = 1.0) -> float:
    """EN 1993-1-1 Table 6.6: Correction factor k_c for the moment distribution between lateral restraints.

    Used for f in 6.3.2.3(2), the equivalent compression flange (6.59) and, as C_1 = k_c⁻², in Annex A.

    Args:
        diagram: MomentDiagram, or its value, e.g "udl-simply-supported"
        psi: Ratio of end moments for the linear diagram, -1 <= psi <= 1
    """
    diagram_value: MomentDiagram = MomentDiagram(diagram)
    if diagram_value == MomentDiagram.UNIFORM:
        return 1.0
    if diagram_value == MomentDiagram.LINEAR:
        if not -1.0 <= psi <= 1.0:
            raise ValueError("psi must be between -1 and 1.")
        return 1.0 / (1.33 - 0.33 * psi)
    return _KC_VALUES[diagram_value]


def ltb_curve(
    section_type: Optional[SectionType] = None,
    h: Optional[float] = None,
    b: Optional[float] = None,
    method: LTBMethod = "rolled",
    welded: bool = False,
) -> str:
    """EN 1993-1-1 Tables 6.4 (general case, 6.56) and 6.5 (rolled or equivalent welded sections, 6.57): LTB curve.

    Table 6.4: rolled I h/b <= 2 a, > 2 b; welded I h/b <= 2 c, > 2 d; other cross-sections d.
    Table 6.5: rolled I h/b <= 2 b, > 2 c; welded I h/b <= 2 c, > 2 d; I-sections only.
    """
    if _family(section_type) != "I":
        if method == "rolled":
            raise ValueError("Table 6.5 covers I-sections only; use method='general'.")
        return "d"
    h_over_b: float = _require_positive(h, "h") / _require_positive(b, "b")
    if method == "general":
        if welded:
            return "c" if h_over_b <= 2.0 else "d"
        return "a" if h_over_b <= 2.0 else "b"
    if welded:
        return "c" if h_over_b <= 2.0 else "d"
    return "b" if h_over_b <= 2.0 else "c"


def ltb_modification_factor(k_c: float, lambda_bar_LT: float) -> float:
    """EN 1993-1-1 6.3.2.3(2) NOTE: f = 1 - 0.5(1 - k_c)[1 - 2.0(lambda_bar_LT - 0.8)²] <= 1.0."""
    return min(1.0 - 0.5 * (1.0 - k_c) * (1.0 - 2.0 * (lambda_bar_LT - 0.8) ** 2), 1.0)


def ltb_reduction_factor(
    lambda_bar_LT: float,
    alpha_LT: float | str,
    method: LTBMethod = "rolled",
    lambda_LT_0: float = LAMBDA_LT_0,
    beta: float = BETA_LT,
    f: float = 1.0,
) -> float:
    """EN 1993-1-1 Equations 6.56 to 6.58: Reduction factor chi_LT for lateral-torsional buckling.

    general (6.56): Phi = 0.5[1 + alpha(lambda - 0.2) + lambda²]; chi = 1/(Phi + sqrt(Phi² - lambda²)) <= 1
    rolled (6.57): Phi = 0.5[1 + alpha(lambda - lambda_LT,0) + beta*lambda²]; chi = 1/(Phi + sqrt(Phi² - beta*lambda²)),
        chi <= 1 and <= 1/lambda²
    modified (6.58), rolled only: chi_LT,mod = chi_LT/f <= 1 and <= 1/lambda²

    Args:
        lambda_bar_LT: Non-dimensional slenderness for lateral-torsional buckling
        alpha_LT: Imperfection factor, or the curve ("a" to "d", Table 6.3)
        method: "general" (6.3.2.2) or "rolled" (6.3.2.3)
        lambda_LT_0, beta: 6.3.2.3(1) parameters; recommended 0.4 and 0.75
        f: Modification factor, see ltb_modification_factor(); 1.0 skips (6.58)
    """
    alpha: float = _alpha(alpha_LT, LTB_IMPERFECTION_FACTORS, "Table 6.3")
    if lambda_bar_LT < 0.0:
        raise ValueError("lambda_bar_LT cannot be negative.")
    if method == "general":
        Phi: float = _phi(lambda_bar_LT, alpha)
        return min(1.0 / (Phi + math.sqrt(Phi**2 - lambda_bar_LT**2)), 1.0)
    Phi = _phi(lambda_bar_LT, alpha, lambda_LT_0, beta)
    cap: float = 1.0 if lambda_bar_LT <= 1.0 else 1.0 / lambda_bar_LT**2
    chi_LT: float = min(1.0 / (Phi + math.sqrt(Phi**2 - beta * lambda_bar_LT**2)), cap) # (6.57)
    return min(chi_LT / _require_positive(f, "f"), cap) # (6.58)


def elastic_critical_moment(
    I_z: float,
    I_t: float,
    L: float,
    I_w: float = 0.0,
    C_1: float = 1.0,
    C_2: float = 0.0,
    z_g: float = 0.0,
    k: float = 1.0,
    k_w: float = 1.0,
    E: float = E_STEEL,
    G: float = G_STEEL,
) -> float:
    """Elastic critical moment for lateral-torsional buckling of doubly symmetric sections, M_cr (Nmm).

    EN 1993-1-1 does not give M_cr (6.3.2.2(2)); this is the formula of NCCI SN003 (Access Steel):

    M_cr = C_1 π²EI_z/(kL)² {sqrt[(k/k_w)² I_w/I_z + (kL)² G*I_t/(π²EI_z) + (C_2 z_g)²] - C_2 z_g}

    Args:
        I_z: Second moment of area about the minor axis (mm⁴)
        I_t: St. Venant torsional constant (mm⁴)
        L: Length between lateral restraints (mm)
        I_w: Warping constant (mm⁶); 0 for closed hollow sections
        C_1: Moment distribution factor; C_1 = k_c⁻² (Table 6.6, Annex A)
        C_2: Load position factor, with z_g
        z_g: Distance from the shear centre to the point of load application (mm); positive for destabilising loads
        k, k_w: Effective length factors for lateral bending and warping; 1.0 for fork supports
        E, G: Moduli (N/mm²)
    """
    I_z = _require_positive(I_z, "I_z")
    kL: float = k * _require_positive(L, "L")
    euler: float = math.pi**2 * E * I_z / kL**2
    root: float = math.sqrt((k / k_w) ** 2 * I_w / I_z + kL**2 * G * _require_positive(I_t, "I_t") / (math.pi**2 * E * I_z) + (C_2 * z_g) ** 2)
    return C_1 * euler * (root - C_2 * z_g)


def ltb_slenderness(W_y: float, fy: float, M_cr: float) -> float:
    """EN 1993-1-1 6.3.2.2(1): lambda_bar_LT = sqrt(W_y*fy/M_cr)."""
    return math.sqrt(_require_positive(W_y, "W_y") * _require_positive(fy, "fy") / _require_positive(M_cr, "M_cr"))


def ltb_buckling_resistance(chi_LT: float, W_y: float, fy: float, gamma_M1: float = GAMMA_M1) -> float:
    """EN 1993-1-1 Equation 6.55: M_b,Rd = chi_LT*W_y*fy/γM1 (Nmm); W_y = W_pl,y (Class 1, 2), W_el,y (3) or W_eff,y (4)."""
    return chi_LT * _require_positive(W_y, "W_y") * _require_positive(fy, "fy") / gamma_M1


def ltb_utilisation(M_Ed: float, M_b_Rd: float) -> UtilisationCheck:
    """EN 1993-1-1 Equation 6.54: M_Ed/M_b,Rd <= 1.0."""
    return _utilisation_check(M_Ed, M_b_Rd, "6.3.2.1", "6.54", "Lateral-torsional buckling")


class LateralTorsionalBucklingResult(BaseModel):
    # 6.3.2 Uniform members in bending: lateral-torsional buckling under major-axis bending
    M_b_Rd: float # (6.55), Nmm
    chi_LT: float # (6.56) or (6.57), modified by (6.58) where f < 1
    chi_LT_unmodified: float # before (6.58)
    f: float = 1.0 # 6.3.2.3(2); 1.0 in the general case
    lambda_bar_LT: float # 6.3.2.2(1)
    Phi_LT: float # 6.3.2.2(1) or 6.3.2.3(1)
    M_cr: Optional[float] = None # elastic critical moment, Nmm; None where the section is not susceptible
    W_y: float # mm³; W_pl,y, W_el,y or W_eff,y (6.3.2.1(3))
    curve: Optional[str] = None # Table 6.4 or Table 6.5
    alpha_LT: Optional[float] = None # Table 6.3
    method: LTBMethod
    section_class: SectionClass # 5.5, under major-axis bending
    k_c: Optional[float] = None # Table 6.6
    C_1: Optional[float] = None # M_cr moment distribution factor
    L: Optional[float] = None # length between lateral restraints, mm
    susceptible: bool = True # 6.3.2.1(2): False for circular and square hollow sections
    ltb_negligible: Optional[bool] = None # 6.3.2.2(4), with M_Ed
    M_Ed: Optional[float] = None # design moment, Nmm
    utilisation: Optional[UtilisationCheck] = None # (6.54)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_lateral_torsional_buckling(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    L: Optional[float] = None,
    M_Ed: Optional[float] = None,
    M_cr: Optional[float] = None,
    diagram: MomentDiagram | str = MomentDiagram.LINEAR,
    psi: float = 1.0,
    k_c: Optional[float] = None,
    C_1: Optional[float] = None,
    C_2: float = 0.0,
    z_g: float = 0.0,
    k: float = 1.0,
    k_w: float = 1.0,
    method: LTBMethod = "rolled",
    apply_f: bool = True,
    welded: bool = False,
    section_class: Optional[SectionClassInput] = None,
    W_eff_y: Optional[float] = None,
    lambda_LT_0: float = LAMBDA_LT_0,
    beta: float = BETA_LT,
    gamma_M1: float = GAMMA_M1,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> LateralTorsionalBucklingResult:
    """EN 1993-1-1 6.3.2: Buckling resistance moment M_b,Rd of a laterally unrestrained member in major-axis bending.

    M_cr is taken from elastic_critical_moment() (NCCI SN003) with C_1 = k_c⁻² unless M_cr or C_1 is given; that formula
    is for doubly symmetric sections, so channels are approximate and angles need M_cr. The rolled method (6.57) needs an
    I-section; other shapes fall back to the general case (6.56) with Table 6.4 "other cross-sections". Circular and
    square hollow sections are not susceptible (6.3.2.1(2)).

    Args:
        section: EU/UK section; classified under major-axis bending unless `section_class` is given
        fy: Yield strength (N/mm²)
        L: Length between lateral restraints (mm); needed unless M_cr is given
        M_Ed: Maximum design moment in the segment (Nmm)
        M_cr: Elastic critical moment (Nmm); overrides the calculation
        diagram: Table 6.6 moment distribution, for k_c
        psi: End moment ratio for the linear diagram
        k_c: Correction factor; overrides the Table 6.6 value
        C_1: M_cr moment factor; defaults to k_c⁻²
        C_2, z_g: Load height; z_g > 0 for destabilising loads above the shear centre (mm)
        k, k_w: Effective length factors for M_cr
        method: "rolled" (6.3.2.3) or "general" (6.3.2.2)
        apply_f: Apply the modification factor f of 6.3.2.3(2) (rolled method)
        welded: Welded I-section (Tables 6.4 and 6.5)
        section_class: Class to use instead of classifying
        W_eff_y: Effective modulus for Class 4 (mm³)
        lambda_LT_0, beta: 6.3.2.3(1) parameters
        gamma_M1: Partial factor for member instability
        E, G: Moduli (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy = _require_positive(fy, "fy")
    cls: SectionClass = _as_section_class(section_class) if section_class is not None else _classify(section, section_type, raw, fy, StressPattern.MAJOR_AXIS_BENDING)
    W_y, _ = section_modulus_for_class(cls, W_pl=data.get("W_pl_y"), W_el=data.get("W_el_y"), W_eff=W_eff_y)
    k_c_value: float = k_c if k_c is not None else correction_factor_kc(diagram, psi)
    C_1_value: float = C_1 if C_1 is not None else k_c_value**-2
    notes: list[str] = []

    if family == "CHS" or section_type in SQUARE_HOLLOW_SECTION_TYPES:
        M_b_Rd: float = ltb_buckling_resistance(1.0, W_y, fy, gamma_M1)
        return LateralTorsionalBucklingResult(
            M_b_Rd=M_b_Rd,
            chi_LT=1.0,
            chi_LT_unmodified=1.0,
            lambda_bar_LT=0.0,
            Phi_LT=0.0,
            W_y=W_y,
            method=method,
            section_class=cls,
            L=L,
            susceptible=False,
            ltb_negligible=True if M_Ed is not None else None,
            M_Ed=M_Ed,
            utilisation=ltb_utilisation(M_Ed, M_b_Rd) if M_Ed is not None else None,
            reference=_reference("6.3.2.1(2)", title="Not susceptible to lateral-torsional buckling"),
        )

    if M_cr is None:
        if family == "angle":
            raise ValueError("Pass M_cr for angles; the NCCI SN003 formula is for doubly symmetric sections.")
        if L is None:
            raise ValueError("Pass L (length between lateral restraints) or M_cr.")
        I_w: float = data.get("I_w", 0.0) if family in ("RHS", "EHS") else _get(data, "I_w")
        M_cr = elastic_critical_moment(_get(data, "I_z"), _get(data, "I_t"), L, I_w, C_1_value, C_2, z_g, k, k_w, E, G)
        if family == "channel":
            notes.append("M_cr for a channel uses the doubly symmetric formula (NCCI SN003); approximate.")

    method_used: LTBMethod = method
    if method == "rolled" and family != "I":
        method_used = "general"
        notes.append("Table 6.5 covers I-sections only; general case (6.56) with Table 6.4 used.")
    lambda_bar_LT: float = ltb_slenderness(W_y, fy, M_cr)
    curve: str = ltb_curve(section_type, data.get("h"), data.get("b"), method_used, welded)
    alpha_LT: float = LTB_IMPERFECTION_FACTORS[curve]
    f: float = ltb_modification_factor(k_c_value, lambda_bar_LT) if (method_used == "rolled" and apply_f) else 1.0
    chi_LT_unmodified: float = ltb_reduction_factor(lambda_bar_LT, alpha_LT, method_used, lambda_LT_0, beta)
    chi_LT: float = ltb_reduction_factor(lambda_bar_LT, alpha_LT, method_used, lambda_LT_0, beta, f)
    Phi_LT: float = _phi(lambda_bar_LT, alpha_LT) if method_used == "general" else _phi(lambda_bar_LT, alpha_LT, lambda_LT_0, beta)
    M_b_Rd = ltb_buckling_resistance(chi_LT, W_y, fy, gamma_M1)
    plateau: float = 0.2 if method_used == "general" else lambda_LT_0
    negligible: Optional[bool] = None
    if M_Ed is not None:
        negligible = lambda_bar_LT <= plateau or abs(M_Ed) / M_cr <= plateau**2 # 6.3.2.2(4)

    return LateralTorsionalBucklingResult(
        M_b_Rd=M_b_Rd,
        chi_LT=chi_LT,
        chi_LT_unmodified=chi_LT_unmodified,
        f=f,
        lambda_bar_LT=lambda_bar_LT,
        Phi_LT=Phi_LT,
        M_cr=M_cr,
        W_y=W_y,
        curve=curve,
        alpha_LT=alpha_LT,
        method=method_used,
        section_class=cls,
        k_c=k_c_value,
        C_1=C_1_value,
        L=L,
        ltb_negligible=negligible,
        M_Ed=M_Ed,
        utilisation=ltb_utilisation(M_Ed, M_b_Rd) if M_Ed is not None else None,
        reference=_reference("6.3.2", "6.55", "Uniform members in bending"),
        metadata={"notes": notes} if notes else {},
    )


# --- 6.3.2.4 Simplified assessment methods for beams with restraints in buildings ---
def equivalent_compression_flange_radius(b: float, t_f: float, h_w: float, t_w: float) -> float:
    """EN 1993-1-1 6.3.2.4(1)B: i_f,z of the compression flange plus 1/3 of the compressed web, about the minor axis (mm).

    For a doubly symmetric I-section in bending, half the web (h_w/2) is in compression.
    """
    A_f: float = _require_positive(b, "b") * _require_positive(t_f, "t_f")
    A_web: float = _require_positive(h_w, "h_w") / 2.0 * _require_positive(t_w, "t_w") / 3.0
    I_f: float = t_f * b**3 / 12.0 + A_web * t_w**2 / 12.0
    return math.sqrt(I_f / (A_f + A_web))


class RestrainedBeamResult(BaseModel):
    # 6.3.2.4 Simplified assessment of beams with discrete lateral restraints to the compression flange (buildings)
    lambda_bar_f: float # (6.59), slenderness of the equivalent compression flange
    lambda_bar_f_limit: float # lambda_bar_c0*M_c,Rd/M_y,Ed
    not_susceptible: bool # (6.59) satisfied: no lateral-torsional buckling between the restraints
    i_f_z: float # mm
    M_c_Rd: float # W_y*fy/γM1, Nmm
    curve: str # 6.3.2.4(3)B
    chi: float # (6.49) with lambda_bar_f
    M_b_Rd: float # (6.60), Nmm; M_c,Rd when not susceptible
    k_c: float # Table 6.6
    L_c: float # length between restraints, mm
    section_class: SectionClass
    M_Ed: float # maximum design moment between restraints, Nmm
    utilisation: Optional[UtilisationCheck] = None
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_restrained_beam(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    L_c: float = 0.0,
    M_Ed: float = 0.0,
    diagram: MomentDiagram | str = MomentDiagram.LINEAR,
    psi: float = 1.0,
    k_c: Optional[float] = None,
    welded: bool = False,
    section_class: Optional[SectionClassInput] = None,
    W_eff_y: Optional[float] = None,
    lambda_c0: float = LAMBDA_C0,
    k_fl: float = K_FL,
    gamma_M1: float = GAMMA_M1,
    E: float = E_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> RestrainedBeamResult:
    """EN 1993-1-1 6.3.2.4 (Equations 6.59 and 6.60): Equivalent compression flange method for I-sections in buildings.

    lambda_bar_f = k_c*L_c/(i_f,z*lambda_1) <= lambda_bar_c0*M_c,Rd/M_y,Ed (6.59), else M_b,Rd = k_fl*chi*M_c,Rd <= M_c,Rd (6.60),
    with chi from curve d (welded, h/t_f <= 44ε) or c (6.3.2.4(3)B).

    Args:
        section: EU/UK I- or H-section
        fy: Yield strength (N/mm²)
        L_c: Length between lateral restraints of the compression flange (mm)
        M_Ed: Maximum design moment between the restraints (Nmm)
        diagram, psi: Table 6.6 moment distribution, for k_c
        k_c: Correction factor; overrides the Table 6.6 value
        welded: Welded section
        section_class: Class to use instead of classifying
        W_eff_y: Effective modulus for Class 4 (mm³)
        lambda_c0: Slenderness limit; recommended lambda_bar_LT,0 + 0.1
        k_fl: Modification factor; recommended 1.10
        gamma_M1: Partial factor for member instability
        E: Modulus of elasticity (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    section_type, data, raw = _section_data(section, section_type, properties)
    if _family(section_type) != "I":
        raise NotImplementedError("The equivalent compression flange method (6.3.2.4) is implemented for I- and H-sections.")
    fy = _require_positive(fy, "fy")
    L_c = _require_positive(L_c, "L_c")
    cls: SectionClass = _as_section_class(section_class) if section_class is not None else _classify(section, section_type, raw, fy, StressPattern.MAJOR_AXIS_BENDING)
    W_y, _ = section_modulus_for_class(cls, W_pl=data.get("W_pl_y"), W_el=data.get("W_el_y"), W_eff=W_eff_y)
    k_c_value: float = k_c if k_c is not None else correction_factor_kc(diagram, psi)
    i_f_z: float = equivalent_compression_flange_radius(_get(data, "b"), _get(data, "t_f"), _web_depth(data), _get(data, "t_w"))
    lambda_bar_f: float = k_c_value * L_c / (i_f_z * lambda_1(fy, E)) # (6.59)
    M_c_Rd: float = W_y * fy / gamma_M1
    limit: float = lambda_c0 * M_c_Rd / _require_positive(abs(M_Ed), "M_Ed")
    not_susceptible: bool = lambda_bar_f <= limit
    curve: str = "d" if welded and _get(data, "h") / _get(data, "t_f") <= 44.0 * _epsilon(fy) else "c" # 6.3.2.4(3)B
    chi: float = buckling_reduction_factor(lambda_bar_f, curve)
    M_b_Rd: float = M_c_Rd if not_susceptible else min(k_fl * chi * M_c_Rd, M_c_Rd) # (6.60)
    return RestrainedBeamResult(
        lambda_bar_f=lambda_bar_f,
        lambda_bar_f_limit=limit,
        not_susceptible=not_susceptible,
        i_f_z=i_f_z,
        M_c_Rd=M_c_Rd,
        curve=curve,
        chi=chi,
        M_b_Rd=M_b_Rd,
        k_c=k_c_value,
        L_c=L_c,
        section_class=cls,
        M_Ed=M_Ed,
        utilisation=_utilisation_check(M_Ed, M_b_Rd, "6.3.2.4", "6.60" if not not_susceptible else "6.59", "Equivalent compression flange"),
        reference=_reference("6.3.2.4", "6.59", "Simplified assessment methods for beams with restraints in buildings"),
    )


# --- 6.3.3 Uniform members in bending and axial compression ---
def characteristic_resistances(
    section_class: SectionClassInput,
    fy: float,
    A: float,
    W_pl_y: Optional[float] = None,
    W_pl_z: Optional[float] = None,
    W_el_y: Optional[float] = None,
    W_el_z: Optional[float] = None,
    A_eff: Optional[float] = None,
    W_eff_y: Optional[float] = None,
    W_eff_z: Optional[float] = None,
) -> tuple[float, Optional[float], Optional[float]]:
    """EN 1993-1-1 Table 6.7: (N_Rk, M_y,Rk, M_z,Rk) = fy*(A_i, W_y, W_z), per class; moduli that are missing return None."""
    fy = _require_positive(fy, "fy")
    cls: SectionClass = _as_section_class(section_class)
    if _is_plastic(cls):
        A_i, W_y, W_z = A, W_pl_y, W_pl_z
    elif cls == SectionClass.CLASS_3:
        A_i, W_y, W_z = A, W_el_y, W_el_z
    else:
        A_i, W_y, W_z = _class_4_value(A_eff, "A_eff", "Table 6.7"), W_eff_y, W_eff_z
    return _require_positive(A_i, "A") * fy, W_y * fy if W_y else None, W_z * fy if W_z else None


def equivalent_moment_factor_B3(
    psi: float = 1.0,
    alpha_s: Optional[float] = None,
    alpha_h: Optional[float] = None,
    loading: Literal["uniform", "concentrated"] = "uniform",
    sway: bool = False,
) -> float:
    """EN 1993-1-1 Annex B, Table B.3: Equivalent uniform moment factor C_my, C_mz or C_mLT (method 2).

    M_h is the larger end moment, psi*M_h the other and M_s the span moment; pass alpha_s = M_s/M_h when |M_s| <= |M_h|,
    alpha_h = M_h/M_s when the span moment is larger, or neither for end moments only.

    - End moments only: 0.6 + 0.4psi >= 0.4
    - 0 <= alpha_s <= 1: 0.2 + 0.8alpha_s >= 0.4
    - -1 <= alpha_s < 0: uniform 0.1 - 0.8alpha_s (psi >= 0) or 0.1(1 - psi) - 0.8alpha_s (psi < 0), >= 0.4;
      concentrated -0.8alpha_s (psi >= 0) or 0.2(-psi) - 0.8alpha_s (psi < 0), >= 0.4
    - -1 <= alpha_h <= 1: uniform 0.95 + 0.05alpha_h, concentrated 0.90 + 0.10alpha_h; for alpha_h < 0 and psi < 0,
      alpha_h is multiplied by (1 + 2psi)
    - Sway buckling mode: 0.9

    Args:
        psi: End moment ratio, -1 <= psi <= 1
        alpha_s: M_s/M_h
        alpha_h: M_h/M_s
        loading: "uniform" or "concentrated" transverse load
        sway: Member with a sway buckling mode
    """
    if sway:
        return 0.9
    if not -1.0 <= psi <= 1.0:
        raise ValueError("psi must be between -1 and 1.")
    if alpha_s is not None and alpha_h is not None:
        raise ValueError("Pass alpha_s or alpha_h, not both.")
    uniform: bool = loading == "uniform"
    if alpha_s is not None:
        if not -1.0 <= alpha_s <= 1.0:
            raise ValueError("alpha_s must be between -1 and 1.")
        if alpha_s >= 0.0:
            C_m: float = 0.2 + 0.8 * alpha_s
        elif psi >= 0.0:
            C_m = (0.1 - 0.8 * alpha_s) if uniform else (-0.8 * alpha_s)
        else:
            C_m = (0.1 * (1.0 - psi) - 0.8 * alpha_s) if uniform else (0.2 * (-psi) - 0.8 * alpha_s)
        return max(C_m, 0.4)
    if alpha_h is not None:
        if not -1.0 <= alpha_h <= 1.0:
            raise ValueError("alpha_h must be between -1 and 1.")
        a_h: float = alpha_h * (1.0 + 2.0 * psi) if (alpha_h < 0.0 and psi < 0.0) else alpha_h
        return 0.95 + 0.05 * a_h if uniform else 0.90 + 0.10 * a_h
    return max(0.6 + 0.4 * psi, 0.4)


def equivalent_moment_factor_A2(
    N_Ed: float,
    N_cr_i: float,
    psi: float = 1.0,
    loading: Literal["linear", "uniform", "concentrated"] = "linear",
    delta_x: Optional[float] = None,
    M_i_Ed: Optional[float] = None,
    I_i: Optional[float] = None,
    L: Optional[float] = None,
    E: float = E_STEEL,
) -> float:
    """EN 1993-1-1 Annex A, Table A.2: Equivalent uniform moment factor C_mi,0 (method 1).

    - Linear end moments: 0.79 + 0.21psi + 0.36(psi - 0.33)N_Ed/N_cr,i
    - Uniform transverse load: 1 - 0.18N_Ed/N_cr,i
    - Concentrated transverse load: 1 + 0.03N_Ed/N_cr,i
    - General, from the first-order deflection: 1 + (π²EI_i|δ_x|/(L²|M_i,Ed(x)|) - 1)N_Ed/N_cr,i

    Args:
        N_Ed: Design compression force (N)
        N_cr_i: Elastic flexural buckling force about the axis (N)
        psi: End moment ratio, -1 <= psi <= 1
        loading: "linear", "uniform" or "concentrated"
        delta_x: Maximum first-order deflection (mm); selects the general formula, with M_i_Ed, I_i and L
        M_i_Ed: Maximum first-order moment (Nmm)
        I_i: Second moment of area about the axis (mm⁴)
        L: Member length (mm)
        E: Modulus of elasticity (N/mm²)
    """
    ratio: float = N_Ed / _require_positive(N_cr_i, "N_cr_i")
    if delta_x is not None:
        stiffness: float = math.pi**2 * E * _require_positive(I_i, "I_i") * abs(delta_x) / (_require_positive(L, "L") ** 2 * _require_positive(abs(M_i_Ed or 0.0), "M_i_Ed"))
        return 1.0 + (stiffness - 1.0) * ratio
    match loading:
        case "linear":
            if not -1.0 <= psi <= 1.0:
                raise ValueError("psi must be between -1 and 1.")
            return 0.79 + 0.21 * psi + 0.36 * (psi - 0.33) * ratio
        case "uniform":
            return 1.0 - 0.18 * ratio
        case "concentrated":
            return 1.0 + 0.03 * ratio
        case _:
            raise ValueError("loading must be 'linear', 'uniform' or 'concentrated'.")


class InteractionFactors(BaseModel):
    # 6.3.3(5): interaction factors for (6.61) and (6.62)
    k_yy: float
    k_yz: float
    k_zy: float
    k_zz: float
    method: InteractionMethod # "A" (Annex A) or "B" (Annex B)
    C_my: float
    C_mz: float
    C_mLT: float
    metadata: dict[str, Any] = Field(default_factory=dict)


def interaction_factors_method_2(
    *,
    N_Ed: float,
    N_Rk: float,
    chi_y: float,
    chi_z: float,
    lambda_bar_y: float,
    lambda_bar_z: float,
    C_my: float = 1.0,
    C_mz: float = 1.0,
    C_mLT: float = 1.0,
    section_class: SectionClassInput = SectionClass.CLASS_1,
    shape: Literal["I", "RHS"] = "I",
    susceptible_to_torsion: bool = True,
    gamma_M1: float = GAMMA_M1,
) -> InteractionFactors:
    """EN 1993-1-1 Annex B, Tables B.1 and B.2: Interaction factors k_ij (method 2).

    Elastic (Class 3, 4): k_yy = C_my(1 + 0.6λy*n_y) <= C_my(1 + 0.6n_y); k_zz likewise; k_yz = k_zz; k_zy = 0.8k_yy
    Plastic (Class 1, 2): k_yy = C_my(1 + (λy - 0.2)n_y) <= C_my(1 + 0.8n_y); k_yz = 0.6k_zz; k_zy = 0.6k_yy;
        I-sections k_zz = C_mz(1 + (2λz - 0.6)n_z) <= C_mz(1 + 1.4n_z); RHS k_zz = C_mz(1 + (λz - 0.2)n_z) <= C_mz(1 + 0.8n_z)
    Torsionally susceptible members (Table B.2): k_zy = 1 - c*λz*n_z/(C_mLT - 0.25) >= 1 - c*n_z/(C_mLT - 0.25), with c = 0.05
        (elastic) or 0.1 (plastic); for λz < 0.4 (plastic), k_zy = 0.6 + λz <= 1 - 0.1λz*n_z/(C_mLT - 0.25)

    where n_i = N_Ed/(chi_i*N_Rk/γM1). For I- and RHS under N and M_y only, Table B.1 allows k_zy = 0; not applied here.
    """
    n_y: float = N_Ed / (_require_positive(chi_y, "chi_y") * _require_positive(N_Rk, "N_Rk") / gamma_M1)
    n_z: float = N_Ed / (_require_positive(chi_z, "chi_z") * N_Rk / gamma_M1)
    plastic: bool = _is_plastic(_as_section_class(section_class))
    if plastic:
        k_yy: float = C_my * min(1.0 + (lambda_bar_y - 0.2) * n_y, 1.0 + 0.8 * n_y)
        if shape == "RHS":
            k_zz: float = C_mz * min(1.0 + (lambda_bar_z - 0.2) * n_z, 1.0 + 0.8 * n_z)
        else:
            k_zz = C_mz * min(1.0 + (2.0 * lambda_bar_z - 0.6) * n_z, 1.0 + 1.4 * n_z)
        k_yz: float = 0.6 * k_zz
        k_zy: float = 0.6 * k_yy
    else:
        k_yy = C_my * min(1.0 + 0.6 * lambda_bar_y * n_y, 1.0 + 0.6 * n_y)
        k_zz = C_mz * min(1.0 + 0.6 * lambda_bar_z * n_z, 1.0 + 0.6 * n_z)
        k_yz = k_zz
        k_zy = 0.8 * k_yy
    if susceptible_to_torsion:
        c: float = 0.1 if plastic else 0.05
        k_zy = max(1.0 - c * lambda_bar_z * n_z / (C_mLT - 0.25), 1.0 - c * n_z / (C_mLT - 0.25))
        if plastic and lambda_bar_z < 0.4:
            k_zy = min(0.6 + lambda_bar_z, 1.0 - 0.1 * lambda_bar_z * n_z / (C_mLT - 0.25))
    return InteractionFactors(
        k_yy=k_yy, k_yz=k_yz, k_zy=k_zy, k_zz=k_zz, method="B", C_my=C_my, C_mz=C_mz, C_mLT=C_mLT,
        metadata={"n_y": n_y, "n_z": n_z, "table": "B.2" if susceptible_to_torsion else "B.1"},
    )


def interaction_factors_method_1(
    *,
    N_Ed: float,
    M_y_Ed: float,
    M_z_Ed: float,
    N_cr_y: float,
    N_cr_z: float,
    N_cr_T: float = math.inf,
    N_cr_TF: Optional[float] = None,
    chi_y: float,
    chi_z: float,
    chi_LT: float = 1.0,
    lambda_bar_y: float,
    lambda_bar_z: float,
    lambda_bar_0: float = 0.0,
    C_my_0: float = 1.0,
    C_mz_0: float = 1.0,
    C_1: float = 1.0,
    A: float,
    fy: float,
    W_el_y: float,
    W_el_z: float,
    W_pl_y: Optional[float] = None,
    W_pl_z: Optional[float] = None,
    I_t: float = 0.0,
    I_y: float,
    section_class: SectionClassInput = SectionClass.CLASS_1,
    A_eff: Optional[float] = None,
    W_eff_y: Optional[float] = None,
    gamma_M0: float = GAMMA_M0,
) -> InteractionFactors:
    """EN 1993-1-1 Annex A, Tables A.1 and A.2: Interaction factors k_ij (method 1), with A1:2014.

    k_yy = C_my C_mLT μy/(1 - N_Ed/N_cr,y) [x 1/C_yy]; k_yz = C_mz μy/(1 - N_Ed/N_cr,z) [x 0.6sqrt(w_z/w_y)/C_yz]
    k_zy = C_my C_mLT μz/(1 - N_Ed/N_cr,y) [x 0.6sqrt(w_y/w_z)/C_zy]; k_zz = C_mz μz/(1 - N_Ed/N_cr,z) [x 1/C_zz]

    with the bracketed terms for Class 1 and 2 (plastic) only, μi = (1 - N_Ed/N_cr,i)/(1 - chi_i*N_Ed/N_cr,i), and C_my, C_mz,
    C_mLT from C_mi,0 (Table A.2) and the lambda_bar_0 criterion with C_1 = k_c⁻².

    Args:
        N_Ed: Design compression force (N)
        M_y_Ed, M_z_Ed: Maximum first-order moments along the member (Nmm)
        N_cr_y, N_cr_z: Elastic flexural buckling forces (N)
        N_cr_T, N_cr_TF: Elastic torsional and torsional-flexural buckling forces (N); inf when torsion is restrained
        chi_y, chi_z, chi_LT: Reduction factors (6.3.1, 6.3.2); chi_LT = 1 when not susceptible to torsional deformation
        lambda_bar_y, lambda_bar_z: Flexural slendernesses
        lambda_bar_0: LTB slenderness under uniform moment (psi = 1); 0 when not susceptible to torsional deformation
        C_my_0, C_mz_0: Table A.2 factors, see equivalent_moment_factor_A2()
        C_1: M_cr factor of the actual moment diagram; may be k_c⁻² (Table 6.6)
        A, fy: Gross area (mm²) and yield strength (N/mm²)
        W_el_y, W_el_z, W_pl_y, W_pl_z: Section moduli (mm³); plastic moduli for Class 1 and 2
        I_t, I_y: Torsional constant and major-axis second moment of area (mm⁴), for a_LT = 1 - I_t/I_y >= 0
        section_class: Class of the cross-section
        A_eff, W_eff_y: Class 4 effective properties, for epsilon_y
        gamma_M0: Partial factor; n_pl = N_Ed/(N_Rk/γM0) per A1:2014
    """
    cls: SectionClass = _as_section_class(section_class)
    N_cr_TF_value: float = N_cr_TF if N_cr_TF is not None else N_cr_T
    for name, N_cr in (("N_cr_y", N_cr_y), ("N_cr_z", N_cr_z), ("N_cr_T", N_cr_T), ("N_cr_TF", N_cr_TF_value)):
        if N_Ed >= _require_positive(N_cr, name):
            raise ValueError(f"N_Ed must be less than {name}; the member is unstable.")
    r_y, r_z, r_T, r_TF = N_Ed / N_cr_y, N_Ed / N_cr_z, N_Ed / N_cr_T, N_Ed / N_cr_TF_value
    mu_y: float = (1.0 - r_y) / (1.0 - chi_y * r_y)
    mu_z: float = (1.0 - r_z) / (1.0 - chi_z * r_z)
    a_LT: float = max(1.0 - I_t / _require_positive(I_y, "I_y"), 0.0)

    if cls == SectionClass.CLASS_4:
        A_ratio: float = _class_4_value(A_eff, "A_eff", "Table A.1") / _class_4_value(W_eff_y, "W_eff_y", "Table A.1")
    else:
        A_ratio = _require_positive(A, "A") / _require_positive(W_el_y, "W_el_y")
    epsilon_y: float = abs(M_y_Ed) / N_Ed * A_ratio if N_Ed > 0.0 else math.inf

    lambda_0_limit: float = 0.2 * math.sqrt(C_1) * ((1.0 - r_z) * (1.0 - r_TF)) ** 0.25
    if lambda_bar_0 <= lambda_0_limit:
        C_my, C_mz, C_mLT = C_my_0, C_mz_0, 1.0
    else:
        s: float = math.sqrt(epsilon_y) * a_LT
        share: float = 1.0 if math.isinf(s) else s / (1.0 + s)
        C_my = C_my_0 + (1.0 - C_my_0) * share
        C_mz = C_mz_0
        C_mLT = max(C_my**2 * a_LT / math.sqrt((1.0 - r_z) * (1.0 - r_T)), 1.0)

    k_yy: float = C_my * C_mLT * mu_y / (1.0 - r_y)
    k_yz: float = C_mz * mu_y / (1.0 - r_z)
    k_zy: float = C_my * C_mLT * mu_z / (1.0 - r_y)
    k_zz: float = C_mz * mu_z / (1.0 - r_z)
    metadata: dict[str, Any] = {"mu_y": mu_y, "mu_z": mu_z, "a_LT": a_LT, "epsilon_y": epsilon_y, "lambda_bar_0_limit": lambda_0_limit}

    if _is_plastic(cls):
        W_pl_y_value: float = _require_positive(W_pl_y, "W_pl_y")
        W_pl_z_value: float = _require_positive(W_pl_z, "W_pl_z")
        w_y: float = min(W_pl_y_value / W_el_y, 1.5)
        w_z: float = min(W_pl_z_value / W_el_z, 1.5)
        n_pl: float = N_Ed / (A * fy / gamma_M0)
        lambda_max: float = max(lambda_bar_y, lambda_bar_z)
        M_pl_y_Rd: float = W_pl_y_value * fy / gamma_M0
        M_pl_z_Rd: float = W_pl_z_value * fy / gamma_M0
        m_y: float = abs(M_y_Ed) / (C_my * chi_LT * M_pl_y_Rd)
        lz4: float = lambda_bar_z**4
        b_LT: float = 0.5 * a_LT * lambda_bar_0**2 * abs(M_y_Ed) / (chi_LT * M_pl_y_Rd) * abs(M_z_Ed) / M_pl_z_Rd
        c_LT: float = 10.0 * a_LT * lambda_bar_0**2 / (5.0 + lz4) * m_y
        d_LT: float = 2.0 * a_LT * lambda_bar_0 / (0.1 + lz4) * m_y * abs(M_z_Ed) / (C_mz * M_pl_z_Rd)
        e_LT: float = 1.7 * a_LT * lambda_bar_0 / (0.1 + lz4) * m_y
        C_yy: float = max(1.0 + (w_y - 1.0) * ((2.0 - 1.6 / w_y * C_my**2 * lambda_max - 1.6 / w_y * C_my**2 * lambda_max**2) * n_pl - b_LT), W_el_y / W_pl_y_value)
        C_yz: float = max(1.0 + (w_z - 1.0) * ((2.0 - 14.0 * C_mz**2 * lambda_max**2 / w_z**5) * n_pl - c_LT), 0.6 * math.sqrt(w_z / w_y) * W_el_z / W_pl_z_value)
        C_zy: float = max(1.0 + (w_y - 1.0) * ((2.0 - 14.0 * C_my**2 * lambda_max**2 / w_y**5) * n_pl - d_LT), 0.6 * math.sqrt(w_y / w_z) * W_el_y / W_pl_y_value)
        C_zz: float = max(1.0 + (w_z - 1.0) * ((2.0 - 1.6 / w_z * C_mz**2 * lambda_max - 1.6 / w_z * C_mz**2 * lambda_max**2) - e_LT) * n_pl, W_el_z / W_pl_z_value) # A1:2014
        k_yy /= C_yy
        k_yz *= 0.6 * math.sqrt(w_z / w_y) / C_yz
        k_zy *= 0.6 * math.sqrt(w_y / w_z) / C_zy
        k_zz /= C_zz
        metadata.update({"w_y": w_y, "w_z": w_z, "n_pl": n_pl, "C_yy": C_yy, "C_yz": C_yz, "C_zy": C_zy, "C_zz": C_zz})

    return InteractionFactors(k_yy=k_yy, k_yz=k_yz, k_zy=k_zy, k_zz=k_zz, method="A", C_my=C_my, C_mz=C_mz, C_mLT=C_mLT, metadata=metadata)


def member_interaction_utilisations(
    N_Ed: float,
    M_y_Ed: float,
    M_z_Ed: float,
    chi_y: float,
    chi_z: float,
    chi_LT: float,
    N_Rk: float,
    M_y_Rk: Optional[float],
    M_z_Rk: Optional[float],
    factors: InteractionFactors,
    delta_M_y_Ed: float = 0.0,
    delta_M_z_Ed: float = 0.0,
    gamma_M1: float = GAMMA_M1,
) -> tuple[float, float]:
    """EN 1993-1-1 Equations 6.61 and 6.62, on the magnitudes of the actions:

    N_Ed/(chi_y N_Rk/γM1) + k_yy (My,Ed + ΔMy,Ed)/(chi_LT My,Rk/γM1) + k_yz (Mz,Ed + ΔMz,Ed)/(Mz,Rk/γM1) <= 1 (6.61)
    N_Ed/(chi_z N_Rk/γM1) + k_zy (My,Ed + ΔMy,Ed)/(chi_LT My,Rk/γM1) + k_zz (Mz,Ed + ΔMz,Ed)/(Mz,Rk/γM1) <= 1 (6.62)
    """
    M_y: float = abs(M_y_Ed) + abs(delta_M_y_Ed)
    M_z: float = abs(M_z_Ed) + abs(delta_M_z_Ed)
    bending_y: float = M_y / (chi_LT * _require_positive(M_y_Rk, "M_y_Rk") / gamma_M1) if M_y != 0.0 else 0.0
    bending_z: float = M_z / (_require_positive(M_z_Rk, "M_z_Rk") / gamma_M1) if M_z != 0.0 else 0.0
    axial_y: float = abs(N_Ed) / (chi_y * N_Rk / gamma_M1)
    axial_z: float = abs(N_Ed) / (chi_z * N_Rk / gamma_M1)
    return (
        axial_y + factors.k_yy * bending_y + factors.k_yz * bending_z, # (6.61)
        axial_z + factors.k_zy * bending_y + factors.k_zz * bending_z, # (6.62)
    )


class BeamColumnResult(BaseModel):
    # 6.3.3 Uniform members in bending and axial compression, (6.61) and (6.62); the cross-sections at the member ends
    # ... are checked separately to 6.2 (6.3.3(2)), see check_cross_section()
    utilisation_y: float # (6.61)
    utilisation_z: float # (6.62)
    factors: InteractionFactors
    chi_y: float # 6.3.1
    chi_z: float # 6.3.1
    chi_LT: float # 6.3.2; 1.0 for members not susceptible to torsional deformation (Table 6.7 NOTE)
    lambda_bar_y: float
    lambda_bar_z: float
    lambda_bar_LT: Optional[float] = None
    N_cr_y: float # N
    N_cr_z: float # N
    M_cr: Optional[float] = None # Nmm
    N_Rk: float # Table 6.7, N
    M_y_Rk: Optional[float] = None # Table 6.7, Nmm
    M_z_Rk: Optional[float] = None # Table 6.7, Nmm
    delta_M_y_Ed: float = 0.0 # Table 6.7, e_N,y*N_Ed for Class 4, Nmm
    delta_M_z_Ed: float = 0.0 # Table 6.7, e_N,z*N_Ed for Class 4, Nmm
    section_class: SectionClass
    susceptible_to_torsion: bool
    N_Ed: float # N
    M_y_Ed: float # Nmm
    M_z_Ed: float # Nmm
    utilisation: UtilisationCheck
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_bending_and_axial_compression(
    section: Optional[BaseSection] = None,
    fy: float = 355.0,
    N_Ed: float = 0.0,
    M_y_Ed: float = 0.0,
    M_z_Ed: float = 0.0,
    L_cr_y: Optional[float] = None,
    L_cr_z: Optional[float] = None,
    L_LT: Optional[float] = None,
    L_cr_T: Optional[float] = None,
    psi_y: float = 1.0,
    psi_z: float = 1.0,
    psi_LT: Optional[float] = None,
    C_my: Optional[float] = None,
    C_mz: Optional[float] = None,
    C_mLT: Optional[float] = None,
    method: InteractionMethod = "B",
    susceptible_to_torsion: Optional[bool] = None,
    ltb_method: LTBMethod = "rolled",
    C_1: Optional[float] = None,
    M_cr: Optional[float] = None,
    section_class: Optional[SectionClassInput] = None,
    welded: bool = False,
    steel_grade: Optional[str] = None,
    A_eff: Optional[float] = None,
    W_eff_y: Optional[float] = None,
    W_eff_z: Optional[float] = None,
    e_N_y: float = 0.0,
    e_N_z: float = 0.0,
    gamma_M0: float = GAMMA_M0,
    gamma_M1: float = GAMMA_M1,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> BeamColumnResult:
    """EN 1993-1-1 6.3.3: Members in bending and axial compression, Equations 6.61 and 6.62 with k_ij from Annex A or B.

    The equivalent moment factors default to linear moment diagrams from psi_y, psi_z and psi_LT (Table B.3 row 1 for
    method B; Table A.2 row 1, as C_mi,0, for method A); pass C_my, C_mz and C_mLT (method B) or C_my and C_mz as C_mi,0
    (method A) for transverse loads, see equivalent_moment_factor_B3() and equivalent_moment_factor_A2(). 6.3.3 is written
    for doubly symmetric sections; for others see 6.3.4 and check_general_method().

    Args:
        section: EU/UK section; classified under N and M_y unless `section_class` is given
        fy: Yield strength (N/mm²)
        N_Ed: Design compression force (N), >= 0
        M_y_Ed, M_z_Ed: Maximum first-order moments along the member (Nmm)
        L_cr_y, L_cr_z: Flexural buckling lengths (mm)
        L_LT: Length between lateral restraints for LTB (mm); defaults to L_cr_z
        L_cr_T: Torsional buckling length (mm), method A; defaults to L_cr_z
        psi_y, psi_z: End moment ratios of linear moment diagrams about y and z
        psi_LT: End moment ratio between lateral restraints, for C_mLT, k_c and C_1; defaults to psi_y
        C_my, C_mz, C_mLT: Equivalent moment factor overrides
        method: "B" (Annex B, method 2) or "A" (Annex A, method 1)
        susceptible_to_torsion: Default True for open sections, False for hollow sections
        ltb_method: "rolled" (6.57) or "general" (6.56)
        C_1: M_cr moment factor; defaults to k_c⁻² from psi_LT
        M_cr: Elastic critical moment (Nmm); overrides the calculation (method B)
        section_class: Class to use instead of classifying
        welded: Welded section (Tables 6.2, 6.4, 6.5)
        steel_grade: e.g "S460"; selects the S460 column of Table 6.2
        A_eff, W_eff_y, W_eff_z, e_N_y, e_N_z: Class 4 effective properties (mm², mm³, mm)
        gamma_M0, gamma_M1: Partial factors
        E, G: Moduli (N/mm²)
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units
    """
    if N_Ed < 0.0:
        raise ValueError("6.3.3 covers axial compression; N_Ed must be >= 0 (compression positive).")
    section_type, data, raw = _section_data(section, section_type, properties)
    family: str = _family(section_type)
    fy = _require_positive(fy, "fy")
    cls: SectionClass = _class_for_actions(section, section_type, data, raw, fy, N_Ed, M_y_Ed, M_z_Ed, section_class) or SectionClass.CLASS_1
    susceptible: bool = susceptible_to_torsion if susceptible_to_torsion is not None else family not in ("RHS", "CHS", "EHS")
    L_cr_z_value: float = _require_positive(L_cr_z, "L_cr_z")
    notes: list[str] = []
    if family in ("channel", "angle"):
        notes.append("6.3.3(1) is written for doubly symmetric cross-sections; consider 6.3.4 for this section.")

    buckling: BucklingResult = check_buckling_resistance(
        section, fy, L_cr_y=_require_positive(L_cr_y, "L_cr_y"), L_cr_z=L_cr_z_value, section_class=cls, A_eff=A_eff,
        welded=welded, steel_grade=steel_grade, gamma_M1=gamma_M1, E=E, G=G, section_type=section_type, properties=properties,
    )
    mode_y, mode_z = buckling.modes[0], buckling.modes[1]

    chi_LT, lambda_bar_LT, M_cr_value = 1.0, None, None
    ltb_psi: float = psi_LT if psi_LT is not None else psi_y
    L_LT_value: float = L_LT if L_LT is not None else L_cr_z_value
    if susceptible and (M_y_Ed != 0.0 or method == "A"):
        ltb: LateralTorsionalBucklingResult = check_lateral_torsional_buckling(
            section, fy, L=L_LT_value, M_cr=M_cr, psi=ltb_psi, C_1=C_1, method=ltb_method, welded=welded, section_class=cls,
            W_eff_y=W_eff_y, gamma_M1=gamma_M1, E=E, G=G, section_type=section_type, properties=properties,
        )
        chi_LT, lambda_bar_LT, M_cr_value = ltb.chi_LT, ltb.lambda_bar_LT, ltb.M_cr

    N_Rk, M_y_Rk, M_z_Rk = characteristic_resistances(
        cls, fy, _get(data, "A"), data.get("W_pl_y"), data.get("W_pl_z"), data.get("W_el_y"), data.get("W_el_z"), A_eff, W_eff_y, W_eff_z
    )
    class_4: bool = cls == SectionClass.CLASS_4
    delta_M_y: float = e_N_y * N_Ed if class_4 else 0.0
    delta_M_z: float = e_N_z * N_Ed if class_4 else 0.0

    if method == "B":
        factors: InteractionFactors = interaction_factors_method_2(
            N_Ed=N_Ed,
            N_Rk=N_Rk,
            chi_y=mode_y.chi,
            chi_z=mode_z.chi,
            lambda_bar_y=mode_y.lambda_bar,
            lambda_bar_z=mode_z.lambda_bar,
            C_my=C_my if C_my is not None else equivalent_moment_factor_B3(psi_y),
            C_mz=C_mz if C_mz is not None else equivalent_moment_factor_B3(psi_z),
            C_mLT=C_mLT if C_mLT is not None else equivalent_moment_factor_B3(ltb_psi),
            section_class=cls,
            shape="RHS" if family in ("RHS", "CHS", "EHS") else "I",
            susceptible_to_torsion=susceptible,
            gamma_M1=gamma_M1,
        )
    else:
        lambda_bar_0: float = 0.0
        N_cr_T: float = math.inf
        if susceptible:
            I_w: float = _get(data, "I_w")
            I_t: float = _get(data, "I_t")
            M_cr_0: float = elastic_critical_moment(_get(data, "I_z"), I_t, L_LT_value, I_w, 1.0, E=E, G=G)
            W_y_0, _ = section_modulus_for_class(cls, W_pl=data.get("W_pl_y"), W_el=data.get("W_el_y"), W_eff=W_eff_y)
            lambda_bar_0 = ltb_slenderness(W_y_0, fy, M_cr_0)
            i_0: float = polar_radius_of_gyration(_get(data, "i_y"), _get(data, "i_z"))
            N_cr_T = elastic_torsional_buckling_force(I_t, I_w, L_cr_T if L_cr_T is not None else L_cr_z_value, i_0, E, G)
        factors = interaction_factors_method_1(
            N_Ed=N_Ed,
            M_y_Ed=M_y_Ed,
            M_z_Ed=M_z_Ed,
            N_cr_y=mode_y.N_cr,
            N_cr_z=mode_z.N_cr,
            N_cr_T=N_cr_T,
            chi_y=mode_y.chi,
            chi_z=mode_z.chi,
            chi_LT=chi_LT,
            lambda_bar_y=mode_y.lambda_bar,
            lambda_bar_z=mode_z.lambda_bar,
            lambda_bar_0=lambda_bar_0,
            C_my_0=C_my if C_my is not None else equivalent_moment_factor_A2(N_Ed, mode_y.N_cr, psi_y),
            C_mz_0=C_mz if C_mz is not None else equivalent_moment_factor_A2(N_Ed, mode_z.N_cr, psi_z),
            C_1=C_1 if C_1 is not None else correction_factor_kc(MomentDiagram.LINEAR, ltb_psi) ** -2,
            A=_get(data, "A"),
            fy=fy,
            W_el_y=_get(data, "W_el_y"),
            W_el_z=_get(data, "W_el_z"),
            W_pl_y=data.get("W_pl_y"),
            W_pl_z=data.get("W_pl_z"),
            I_t=data.get("I_t", 0.0),
            I_y=_get(data, "I_y"),
            section_class=cls,
            A_eff=A_eff,
            W_eff_y=W_eff_y,
            gamma_M0=gamma_M0,
        )

    utilisation_y, utilisation_z = member_interaction_utilisations(
        N_Ed, M_y_Ed, M_z_Ed, mode_y.chi, mode_z.chi, chi_LT, N_Rk, M_y_Rk, M_z_Rk, factors, delta_M_y, delta_M_z, gamma_M1
    )
    governing_y: bool = utilisation_y >= utilisation_z
    notes.append("Check the cross-sections at the member ends to 6.2 (6.3.3(2)).")
    return BeamColumnResult(
        utilisation_y=utilisation_y,
        utilisation_z=utilisation_z,
        factors=factors,
        chi_y=mode_y.chi,
        chi_z=mode_z.chi,
        chi_LT=chi_LT,
        lambda_bar_y=mode_y.lambda_bar,
        lambda_bar_z=mode_z.lambda_bar,
        lambda_bar_LT=lambda_bar_LT,
        N_cr_y=mode_y.N_cr,
        N_cr_z=mode_z.N_cr,
        M_cr=M_cr_value,
        N_Rk=N_Rk,
        M_y_Rk=M_y_Rk,
        M_z_Rk=M_z_Rk,
        delta_M_y_Ed=delta_M_y,
        delta_M_z_Ed=delta_M_z,
        section_class=cls,
        susceptible_to_torsion=susceptible,
        N_Ed=N_Ed,
        M_y_Ed=M_y_Ed,
        M_z_Ed=M_z_Ed,
        utilisation=_ratio_check(
            max(utilisation_y, utilisation_z), "6.3.3(4)", "6.61" if governing_y else "6.62", "Uniform members in bending and axial compression",
            utilisation_y=utilisation_y, utilisation_z=utilisation_z, method=method,
        ),
        reference=_reference("6.3.3", title="Uniform members in bending and axial compression", notes=f"Annex {method}"),
        metadata={"notes": notes},
    )


# --- 6.3.4 General method for lateral and lateral torsional buckling of structural components ---
class GeneralMethodResult(BaseModel):
    # 6.3.4 General method: out-of-plane buckling of components under compression and/or mono-axial in-plane bending
    alpha_ult_k: float # minimum load amplifier to the characteristic resistance of the critical cross-section, in-plane
    alpha_cr_op: float # minimum load amplifier to the elastic critical load for lateral or lateral torsional buckling
    lambda_bar_op: float # (6.64)
    chi: float # 6.3.1, at lambda_bar_op
    chi_LT: float # 6.3.2, at lambda_bar_op
    chi_op: float # 6.3.4(4)a) min(chi, chi_LT); for b), the equivalent interpolated value
    interpolated: bool # 6.3.4(4)b), (6.66)
    utilisation: UtilisationCheck # 1/(chi_op*alpha_ult,k/γM1), (6.63)
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def check_general_method(
    alpha_ult_k: float,
    alpha_cr_op: float,
    curve: str,
    ltb_curve_name: str,
    ltb_method: LTBMethod = "general",
    interpolate: bool = False,
    N_Ed: Optional[float] = None,
    N_Rk: Optional[float] = None,
    M_y_Ed: Optional[float] = None,
    M_y_Rk: Optional[float] = None,
    gamma_M1: float = GAMMA_M1,
) -> GeneralMethodResult:
    """EN 1993-1-1 6.3.4: chi_op*alpha_ult,k/γM1 >= 1.0 (6.63), with lambda_bar_op = sqrt(alpha_ult,k/alpha_cr,op) (6.64).

    a) chi_op = min(chi, chi_LT) at lambda_bar_op; b) with `interpolate`, and alpha_ult,k from 1/alpha_ult,k =
    N_Ed/N_Rk + My,Ed/My,Rk, the check is N_Ed/(chi N_Rk/γM1) + My,Ed/(chi_LT My,Rk/γM1) <= 1 (6.66).
    alpha_ult,k and alpha_cr,op may come from finite element analysis (6.3.4(3) NOTE).

    Args:
        alpha_ult_k: In-plane load amplifier to the characteristic resistance of the most critical cross-section
        alpha_cr_op: Load amplifier to the elastic critical load for lateral or lateral torsional buckling
        curve: Table 6.2 flexural buckling curve, for chi
        ltb_curve_name: Table 6.4 or 6.5 curve, for chi_LT
        ltb_method: "general" (6.56) or "rolled" (6.57) for chi_LT
        interpolate: Use 6.3.4(4)b) (6.66); needs N_Ed, N_Rk, M_y_Ed and M_y_Rk
        N_Ed, N_Rk: Design and characteristic axial forces (N)
        M_y_Ed, M_y_Rk: Design and characteristic moments (Nmm)
        gamma_M1: Partial factor for member instability
    """
    alpha_ult_k = _require_positive(alpha_ult_k, "alpha_ult_k")
    lambda_bar_op: float = math.sqrt(alpha_ult_k / _require_positive(alpha_cr_op, "alpha_cr_op")) # (6.64)
    chi: float = buckling_reduction_factor(lambda_bar_op, curve)
    chi_LT: float = ltb_reduction_factor(lambda_bar_op, ltb_curve_name, ltb_method)
    if interpolate:
        N_term: float = abs(_require_positive(N_Ed, "N_Ed")) / (chi * _require_positive(N_Rk, "N_Rk") / gamma_M1)
        M_term: float = abs(_require_positive(M_y_Ed, "M_y_Ed")) / (chi_LT * _require_positive(M_y_Rk, "M_y_Rk") / gamma_M1)
        utilisation: float = N_term + M_term # (6.66)
        chi_op: float = gamma_M1 / (utilisation * alpha_ult_k)
        equation: str = "6.66"
    else:
        chi_op = min(chi, chi_LT)
        utilisation = gamma_M1 / (chi_op * alpha_ult_k) # (6.63)
        equation = "6.63"
    return GeneralMethodResult(
        alpha_ult_k=alpha_ult_k,
        alpha_cr_op=alpha_cr_op,
        lambda_bar_op=lambda_bar_op,
        chi=chi,
        chi_LT=chi_LT,
        chi_op=chi_op,
        interpolated=interpolate,
        utilisation=_ratio_check(utilisation, "6.3.4", equation, "General method", lambda_bar_op=lambda_bar_op),
        reference=_reference("6.3.4", equation, "General method for lateral and lateral torsional buckling of structural components"),
    )


# --- 6.3.5 Lateral torsional buckling of members with plastic hinges ---
def stable_length(i_z: float, fy: float, psi: float = 1.0) -> float:
    """EN 1993-1-1 6.3.5.3(1)B, Equation 6.68: Stable length of a uniform I or H segment with h/t_f <= 40ε, under linear
    moment and without significant axial compression (mm).

    L_stable = 35ε*i_z for 0.625 <= psi <= 1; (60 - 40psi)ε*i_z for -1 <= psi <= 0.625, with psi = M_Ed,min/M_pl,Rd.
    """
    if not -1.0 <= psi <= 1.0:
        raise ValueError("psi must be between -1 and 1.")
    epsilon: float = _epsilon(fy)
    return (35.0 if psi >= 0.625 else 60.0 - 40.0 * psi) * epsilon * _require_positive(i_z, "i_z")


# --- 6.4 Uniform built-up compression members ---
# [NO PLAN TO IMPLEMENT BUILT-UP MEMBERS IN ANY CODE] # NOTE: laced (6.4.2) and battened (6.4.3) members, and closely
# ... spaced built-up members (6.4.4) with chords in contact or through packing plates.


if __name__ == "__main__":
    from steelsnakes.EU.sections.beams import IPE
    from steelsnakes.EU.sections.columns import HD

    beam = IPE("IPE-300")
    material = steel_material("S355", t=beam.tf)
    print(material.model_dump())
    print(check_cross_section(beam, material.fy, N_Ed=150e3, M_y_Ed=120e6, V_z_Ed=90e3).model_dump())
    print(check_lateral_torsional_buckling(beam, material.fy, L=4000.0, M_Ed=120e6, diagram=MomentDiagram.UDL_SIMPLY_SUPPORTED).model_dump())

    column = HD("HD-320x158")
    print(check_buckling_resistance(column, 355.0, L_cr_y=6000.0, L_cr_z=6000.0, N_Ed=2500e3).model_dump())
    print(check_bending_and_axial_compression(column, 355.0, N_Ed=2500e3, M_y_Ed=150e6, L_cr_y=6000.0, L_cr_z=6000.0, psi_y=0.0).model_dump())
    print("🐬")
