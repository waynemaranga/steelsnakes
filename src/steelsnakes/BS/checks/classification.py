"""BS 5950-1:2000 Section 3.5: Classification of cross-sections.

Legacy BS 5950; since many people still use it anyway...

Implements:
    - Table 9   Design strength py (3.1.1)
    - 3.5.1     Element types; Figure 5 dimensions of compression elements
    - 3.5.2     Classes 1 plastic, 2 compact, 3 semi-compact and 4 slender
    - 3.5.3     Flanges of compound I- or H-sections (Figure 6)
    - Table 11  Limiting width-to-thickness ratios for sections other than CHS and RHS
    - Table 12  Limiting width-to-thickness ratios for CHS and RHS
    - 3.5.5     Stress ratios r1 and r2 for classification (Figure 7)
    - 3.5.6     Effective plastic modulus Seff of class 3 semi-compact sections (3.5.6.1 to 3.5.6.4)

Section objects come from the UK module; BS 5950 designs with the same rolled profiles (BS 4-1 ~ BS EN 10365).
Units: stresses N/mm² (MPa), dimensions mm, forces kN, areas cm², moduli cm³; i.e. as tabulated in the UK module.
Member checks (Sections 2.4 and 4) are in steelsnakes.BS.checks.uls, serviceability (2.5) in steelsnakes.BS.checks.sls.
"""

from __future__ import annotations

import difflib
import math
import re
from enum import Enum
from typing import Any, Iterable, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, Reference, SectionClass
from steelsnakes.base.renders import CheckBlock, Row, _frac, _m
from steelsnakes.base.sections import BaseSection, SectionType

BS_5950 = DesignCode.BS_5950_1

# --- Table 9: Design strength py ---
# Rolled sections: thickness is that of the thickest element i.e. the flange; hollow sections and plates: the wall/plate.
_PY_TABLE: dict[str, list[tuple[float, float]]] = {
    "S275": [(16, 275), (40, 265), (63, 255), (80, 245), (100, 235), (150, 225)],
    "S355": [(16, 355), (40, 345), (63, 335), (80, 325), (100, 315), (150, 295)],
    "S460": [(16, 460), (40, 440), (63, 430), (80, 410), (100, 400)],
}


def design_strength(t: float, steel_grade: str = "S275") -> float:
    """BS 5950-1:2000 Table 9: Design strength py (N/mm²) for a steel grade and governing thickness t (mm).

    Args:
        t: Thickness of the thickest element in the cross-section (mm); for rolled sections, the flange
        steel_grade: "S275", "S355" or "S460"; spaces, case and quality suffixes are ignored e.g. "s355 j2h"

    Returns:
        py: Design strength (N/mm²)
    """
    grade = re.sub(r"\s+", "", steel_grade.upper())[:4] # "s 355 J2H" -> "S355"
    if grade not in _PY_TABLE:
        raise ValueError(f"Unknown steel_grade {steel_grade!r}. Options: {list(_PY_TABLE)}")
    if t <= 0.0:
        raise ValueError("Thickness t must be positive.")
    for t_lim, py in _PY_TABLE[grade]:
        if t <= t_lim:
            return float(py)
    raise ValueError(f"Table 9 does not cover {grade} thicker than {_PY_TABLE[grade][-1][0]} mm; obtain py from the product standard.")


def epsilon(py: float) -> float:
    """BS 5950-1:2000 Table 11 note b: epsilon = (275/py)^0.5."""
    if py <= 0.0:
        raise ValueError("py must be positive.")
    return math.sqrt(275.0 / py)


# --- 3.5.2 Classification ---
CLASS_NAMES: dict[SectionClass, str] = {
    SectionClass.CLASS_1: "plastic",
    SectionClass.CLASS_2: "compact",
    SectionClass.CLASS_3: "semi-compact",
    SectionClass.CLASS_4: "slender",
}
_CLASS_RANK: dict[SectionClass, int] = {
    SectionClass.CLASS_1: 1,
    SectionClass.CLASS_2: 2,
    SectionClass.CLASS_3: 3,
    SectionClass.CLASS_4: 4,
}


class ElementKind(str, Enum):
    """Compression element rows of BS 5950-1:2000 Tables 11 and 12.

    The enum value is the string form used in the codebase e.g. `"outstand-flange-rolled"`.
    `description` names the table row; `ratio` is the width-to-thickness ratio it limits.
    """

    # Table 11: sections other than CHS and RHS
    OUTSTAND_FLANGE_ROLLED = "outstand-flange-rolled"
    OUTSTAND_FLANGE_WELDED = "outstand-flange-welded"
    INTERNAL_FLANGE = "internal-flange"
    WEB = "web"
    CHANNEL_WEB = "channel-web"
    ANGLE_LEG = "angle-leg"
    ANGLE = "angle"
    ANGLE_OUTSTAND_LEG = "angle-outstand-leg"
    TEE_STEM = "tee-stem"
    # Table 12: CHS and RHS
    CHS = "chs"
    HF_RHS_FLANGE = "hf-rhs-flange"
    HF_RHS_WEB = "hf-rhs-web"
    CF_RHS_FLANGE = "cf-rhs-flange"
    CF_RHS_WEB = "cf-rhs-web"

    @property
    def table(self) -> str:
        return "Table 12" if self in _TABLE_12_KINDS else "Table 11"

    @property
    def ratio(self) -> str:
        return _RATIO_LABELS[self]

    @property
    def description(self) -> str:
        return _KIND_DESCRIPTIONS[self]


_TABLE_12_KINDS = {
    ElementKind.CHS,
    ElementKind.HF_RHS_FLANGE,
    ElementKind.HF_RHS_WEB,
    ElementKind.CF_RHS_FLANGE,
    ElementKind.CF_RHS_WEB,
}
_RATIO_LABELS: dict[ElementKind, str] = {
    ElementKind.OUTSTAND_FLANGE_ROLLED: "b/T",
    ElementKind.OUTSTAND_FLANGE_WELDED: "b/T",
    ElementKind.INTERNAL_FLANGE: "b/T",
    ElementKind.WEB: "d/t",
    ElementKind.CHANNEL_WEB: "d/t",
    ElementKind.ANGLE_LEG: "b/t",
    ElementKind.ANGLE: "b/t",
    ElementKind.ANGLE_OUTSTAND_LEG: "b/t",
    ElementKind.TEE_STEM: "D/t",
    ElementKind.CHS: "D/t",
    ElementKind.HF_RHS_FLANGE: "b/t",
    ElementKind.HF_RHS_WEB: "d/t",
    ElementKind.CF_RHS_FLANGE: "b/t",
    ElementKind.CF_RHS_WEB: "d/t",
}
_KIND_DESCRIPTIONS: dict[ElementKind, str] = {
    ElementKind.OUTSTAND_FLANGE_ROLLED: "Outstand element of compression flange, rolled section",
    ElementKind.OUTSTAND_FLANGE_WELDED: "Outstand element of compression flange, welded section",
    ElementKind.INTERNAL_FLANGE: "Internal element of compression flange",
    ElementKind.WEB: "Web of an I-, H- or box section",
    ElementKind.CHANNEL_WEB: "Web of a channel",
    ElementKind.ANGLE_LEG: "Angle, compression due to bending (check both legs)",
    ElementKind.ANGLE: "Single angle, or double angles with the components separated, axial compression",
    ElementKind.ANGLE_OUTSTAND_LEG: "Outstand leg of an angle back-to-back in a double angle member, or in continuous contact with another component",
    ElementKind.TEE_STEM: "Stem of a T-section, rolled or cut from a rolled I- or H-section",
    ElementKind.CHS: "Circular hollow section",
    ElementKind.HF_RHS_FLANGE: "Hot finished RHS, flange",
    ElementKind.HF_RHS_WEB: "Hot finished RHS, web",
    ElementKind.CF_RHS_FLANGE: "Cold formed RHS, flange",
    ElementKind.CF_RHS_WEB: "Cold formed RHS, web",
}


class ElementStressDistribution(str, Enum):
    """Stress state of one compression element; the "Compression element" sub-rows of Tables 11 and 12.

    - COMPRESSION: axial compression
    - BENDING: compression due to bending; for webs, neutral axis at mid-depth
    - COMBINED: webs "generally" i.e. axial force and bending; needs stress ratios r1 (classes 1, 2) and r2 (class 3)
    """

    COMPRESSION = "compression"
    BENDING = "bending"
    COMBINED = "combined"


class StressPattern(str, Enum):
    """Section-level stress presets for `classify_section()` and `classify_section_from_dict()`."""

    COMPRESSION = "compression"
    MAJOR_AXIS_BENDING = "bending-major-axis"
    MINOR_AXIS_BENDING = "bending-minor-axis"
    COMBINED = "combined" # axial force + major axis bending; needs Fc_kN


_STRESS_PATTERN_ALIASES: dict[str, StressPattern] = {
    "compression": StressPattern.COMPRESSION,
    "axial": StressPattern.COMPRESSION,
    "axial-compression": StressPattern.COMPRESSION,
    "bending": StressPattern.MAJOR_AXIS_BENDING,
    "bending-major-axis": StressPattern.MAJOR_AXIS_BENDING,
    "major-axis-bending": StressPattern.MAJOR_AXIS_BENDING,
    "bending-minor-axis": StressPattern.MINOR_AXIS_BENDING,
    "minor-axis-bending": StressPattern.MINOR_AXIS_BENDING,
    "combined": StressPattern.COMBINED,
    "combined-bending-and-compression": StressPattern.COMBINED,
    "axial-and-bending": StressPattern.COMBINED,
}


def _normalize_stress_pattern(value: StressPattern | str) -> StressPattern:
    if isinstance(value, StressPattern):
        return value
    normalized = "-".join(part for part in str(value).strip().lower().replace("_", "-").replace(" ", "-").split("-") if part)
    pattern = _STRESS_PATTERN_ALIASES.get(normalized)
    if pattern is not None:
        return pattern
    suggestion = difflib.get_close_matches(normalized, list(_STRESS_PATTERN_ALIASES), n=1, cutoff=0.72)
    suggestion_text = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    raise ValueError(
        "Unsupported stress_pattern. Use a StressPattern value or one of: 'compression', "
        f"'bending-major-axis', 'bending-minor-axis' or 'combined'.{suggestion_text}"
    )


class ElementInput(BaseModel):
    """One compression element to classify per BS 5950-1:2000 Table 11 or Table 12.

    `b_mm` is the dimension in the numerator of the table's ratio (b, d or D per Figure 5) and `t_mm` the thickness
    in its denominator (T or t). Some rows need one more dimension:
        - ANGLE (axial compression): `leg_mm`, the other leg d, for d/t and (b + d)/t
        - HF_RHS_FLANGE / CF_RHS_FLANGE in bending: `web_d_mm`, the web depth d, for the d/t-dependent limits
    """

    name: str
    kind: ElementKind
    stress: ElementStressDistribution = ElementStressDistribution.COMPRESSION
    b_mm: float = Field(gt=0.0)
    t_mm: float = Field(gt=0.0)
    leg_mm: Optional[float] = Field(default=None, gt=0.0)
    web_d_mm: Optional[float] = Field(default=None, gt=0.0)
    r1: Optional[float] = None # 3.5.5; classes 1 and 2 of webs "generally"
    r2: Optional[float] = None # 3.5.5; class 3 of webs "generally" and in axial compression


class ElementClassification(BaseModel):
    """Classification of one compression element."""

    name: str
    kind: ElementKind
    stress: ElementStressDistribution
    b_mm: float
    t_mm: float
    ratio: float # b/T, d/t or D/t as per `ratio_label`
    ratio_label: str
    class_1_limit: Optional[float] # None where Table 11/12 says "Not applicable"
    class_2_limit: Optional[float]
    class_3_limit: Optional[float]
    section_class: SectionClass
    class_name: str # plastic, compact, semi-compact or slender
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Classification of a whole cross-section: the highest (least favourable) class of its elements (3.5.1)."""

    epsilon: float
    py_mpa: float
    elements: list[ElementClassification]
    section_class: SectionClass
    class_name: str
    governing_elements: list[str]
    is_slender: bool
    stress_pattern: Optional[StressPattern] = None
    r1: Optional[float] = None
    r2: Optional[float] = None
    notes: list[str] = Field(default_factory=list)
    reference: Reference = Field(default_factory=lambda: Reference(code=BS_5950, clause="3.5", title="Classification of cross-sections"))


class ElementLimits(BaseModel):
    """Limiting values (epsilon included) for one element, as tabulated in Table 11 or Table 12."""

    class_1_limit: Optional[float] = None
    class_2_limit: Optional[float] = None
    class_3_limit: Optional[float] = None
    note: Optional[str] = None


# --- 3.5.5 Stress ratios for classification ---
class StressRatios(BaseModel):
    """BS 5950-1:2000 3.5.5 stress ratios r1 and r2."""

    r1: float
    r2: float
    case: Literal["equal-flanges", "unequal-flanges", "box"]


def _clamp_r1(r1: float) -> float:
    return max(-1.0, min(r1, 1.0)) # but -1 < r1 <= 1


def stress_ratios(
    Fc_kN: float,
    d_mm: float,
    t_mm: float,
    pyw_mpa: float,
    Ag_cm2: Optional[float] = None,
    case: Literal["equal-flanges", "unequal-flanges", "box"] = "equal-flanges",
    pyf_mpa: Optional[float] = None,
    Bt_mm: Optional[float] = None,
    Tt_mm: Optional[float] = None,
    Bc_mm: Optional[float] = None,
    Tc_mm: Optional[float] = None,
    f1_mpa: Optional[float] = None,
    f2_mpa: Optional[float] = None,
) -> StressRatios:
    """BS 5950-1:2000 3.5.5: stress ratios r1 and r2 used in Tables 11 and 12.

    a) I- or H-sections with equal flanges: r1 = Fc/(d t pyw), r2 = Fc/(Ag pyw)
    b) I- or H-sections with unequal flanges: r1 = Fc/(d t pyw) + (Bt Tt - Bc Tc) pyf/(d t pyw), r2 = (f1 + f2)/(2 pyw)
    c) RHS or welded box sections with equal flanges: r1 = Fc/(2 d t pyw), r2 = Fc/(Ag pyw)
    with -1 < r1 <= 1 in all cases.

    Args:
        Fc_kN: Axial compression (kN); negative for tension
        d_mm: Web depth d (mm)
        t_mm: Web thickness t (mm)
        pyw_mpa: Design strength of the web (N/mm²), pyw <= pyf
        Ag_cm2: Gross cross-sectional area (cm²); cases a) and c)
        case: "equal-flanges", "unequal-flanges" or "box"
        pyf_mpa: Design strength of the flanges (N/mm²); case b), defaults to pyw
        Bt_mm: Width of the tension flange (mm); case b)
        Tt_mm: Thickness of the tension flange (mm); case b)
        Bc_mm: Width of the compression flange (mm); case b)
        Tc_mm: Thickness of the compression flange (mm); case b)
        f1_mpa: Maximum compressive stress in the web (N/mm²), see Figure 7; case b)
        f2_mpa: Minimum compressive stress in the web, negative for tension (N/mm²), see Figure 7; case b)
    """
    if d_mm <= 0.0 or t_mm <= 0.0 or pyw_mpa <= 0.0:
        raise ValueError("d_mm, t_mm and pyw_mpa must be positive.")
    Fc_N = Fc_kN * 1_000.0
    dtpyw = d_mm * t_mm * pyw_mpa

    match case:
        case "equal-flanges" | "box":
            if Ag_cm2 is None or Ag_cm2 <= 0.0:
                raise ValueError("Ag_cm2 must be positive for r2 = Fc/(Ag pyw).")
            r1 = Fc_N / (dtpyw if case == "equal-flanges" else 2.0 * dtpyw)
            r2 = Fc_N / (Ag_cm2 * 100.0 * pyw_mpa)
        case "unequal-flanges":
            if None in (Bt_mm, Tt_mm, Bc_mm, Tc_mm, f1_mpa, f2_mpa):
                raise ValueError("Unequal flanges need Bt_mm, Tt_mm, Bc_mm, Tc_mm, f1_mpa and f2_mpa.")
            pyf = pyf_mpa if pyf_mpa is not None else pyw_mpa
            if pyw_mpa > pyf:
                raise ValueError("pyw should not exceed pyf (3.5.5).")
            r1 = Fc_N / dtpyw + (Bt_mm * Tt_mm - Bc_mm * Tc_mm) * pyf / dtpyw # type: ignore[operator]
            r2 = (f1_mpa + f2_mpa) / (2.0 * pyw_mpa) # type: ignore[operator]
        case _:
            raise ValueError("case must be 'equal-flanges', 'unequal-flanges' or 'box'.")

    return StressRatios(r1=_clamp_r1(r1), r2=r2, case=case)


# --- Tables 11 and 12: limiting width-to-thickness ratios ---
def _at_least(value: float, floor: float) -> float:
    return max(value, floor) # "but >= 40ε" (Table 11 & HF RHS) or "but >= 35ε" (CF RHS)


def _generally_class_3(numerator: float, r2: float, floor: float) -> float:
    # 120ε/(1 + 2r2) but >= 40ε; a web with 1 + 2r2 <= 0 is predominantly in tension
    return math.inf if 1.0 + 2.0 * r2 <= 0.0 else _at_least(numerator / (1.0 + 2.0 * r2), floor)


def _require(value: Optional[float], name: str, kind: ElementKind, stress: ElementStressDistribution) -> float:
    if value is None:
        raise ValueError(f"{kind.value} elements in {stress.value} need {name} (BS 5950-1:2000 3.5.5).")
    return value


def element_limits(element: ElementInput, py: float) -> ElementLimits:
    """BS 5950-1:2000 Tables 11 and 12: limiting width-to-thickness ratios of one element, epsilon included.

    Webs in axial compression default to r2 = 1.0 (fully yielded web i.e. Fc = Ag pyw) when r2 is not given; this is
    conservative and gives the 40ε (HF) or 35ε (CF) floor.
    """
    eps = epsilon(py)
    eps2 = eps**2
    kind, stress = element.kind, element.stress

    match kind:
        case ElementKind.OUTSTAND_FLANGE_ROLLED | ElementKind.ANGLE_LEG | ElementKind.ANGLE_OUTSTAND_LEG:
            return ElementLimits(class_1_limit=9.0 * eps, class_2_limit=10.0 * eps, class_3_limit=15.0 * eps)
        case ElementKind.OUTSTAND_FLANGE_WELDED:
            return ElementLimits(class_1_limit=8.0 * eps, class_2_limit=9.0 * eps, class_3_limit=13.0 * eps)
        case ElementKind.INTERNAL_FLANGE:
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=40.0 * eps, note="Classes 1 and 2 not applicable to axial compression")
            return ElementLimits(class_1_limit=28.0 * eps, class_2_limit=32.0 * eps, class_3_limit=40.0 * eps)
        case ElementKind.WEB:
            if stress == ElementStressDistribution.BENDING:
                return ElementLimits(class_1_limit=80.0 * eps, class_2_limit=100.0 * eps, class_3_limit=120.0 * eps, note="Neutral axis at mid-depth")
            r2 = element.r2 if element.r2 is not None else 1.0
            class_3 = _generally_class_3(120.0 * eps, r2, 40.0 * eps)
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=class_3, note="Classes 1 and 2 not applicable to axial compression")
            r1 = _clamp_r1(_require(element.r1, "r1", kind, stress))
            if r1 <= -1.0:
                return ElementLimits(class_1_limit=math.inf, class_2_limit=math.inf, class_3_limit=class_3, note="Web wholly in tension")
            class_1 = _at_least(80.0 * eps / (1.0 + r1), 40.0 * eps)
            class_2 = 100.0 * eps / (1.0 + r1) if r1 < 0.0 else _at_least(100.0 * eps / (1.0 + 1.5 * r1), 40.0 * eps)
            return ElementLimits(class_1_limit=class_1, class_2_limit=class_2, class_3_limit=class_3, note="Generally")
        case ElementKind.CHANNEL_WEB:
            return ElementLimits(class_1_limit=40.0 * eps, class_2_limit=40.0 * eps, class_3_limit=40.0 * eps)
        case ElementKind.ANGLE:
            return ElementLimits(class_3_limit=15.0 * eps, note="Classes 1 and 2 not applicable; also d/t <= 15ε and (b + d)/t <= 24ε")
        case ElementKind.TEE_STEM:
            return ElementLimits(class_1_limit=8.0 * eps, class_2_limit=9.0 * eps, class_3_limit=18.0 * eps)
        case ElementKind.CHS:
            # 3.5.1: CHS should be classified separately for axial compression and for bending
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=80.0 * eps2, note="Classes 1 and 2 not applicable to axial compression")
            if stress == ElementStressDistribution.COMBINED:
                raise ValueError("CHS should be classified separately for axial compression and for bending (3.5.1).")
            return ElementLimits(class_1_limit=40.0 * eps2, class_2_limit=50.0 * eps2, class_3_limit=140.0 * eps2)
        case ElementKind.HF_RHS_FLANGE | ElementKind.CF_RHS_FLANGE:
            hot = kind == ElementKind.HF_RHS_FLANGE
            class_3 = (40.0 if hot else 35.0) * eps
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=class_3, note="Classes 1 and 2 not applicable to axial compression")
            d_t = _require(element.web_d_mm, "web_d_mm", kind, stress) / element.t_mm
            if hot:
                class_1 = min(28.0 * eps, 80.0 * eps - d_t) # 28ε but <= 80ε - d/t
                class_2 = min(32.0 * eps, 62.0 * eps - 0.5 * d_t) # 32ε but <= 62ε - 0.5d/t
            else:
                class_1 = min(26.0 * eps, 72.0 * eps - d_t) # 26ε but <= 72ε - d/t
                class_2 = min(28.0 * eps, 54.0 * eps - 0.5 * d_t) # 28ε but <= 54ε - 0.5d/t
            return ElementLimits(class_1_limit=class_1, class_2_limit=class_2, class_3_limit=class_3, note=f"Web d/t = {d_t:.2f}")
        case ElementKind.HF_RHS_WEB | ElementKind.CF_RHS_WEB:
            hot = kind == ElementKind.HF_RHS_WEB
            c1, c2, c3, floor = (64.0, 80.0, 120.0, 40.0) if hot else (56.0, 70.0, 105.0, 35.0)
            if stress == ElementStressDistribution.BENDING:
                return ElementLimits(class_1_limit=c1 * eps, class_2_limit=c2 * eps, class_3_limit=c3 * eps, note="Neutral axis at mid-depth")
            r2 = element.r2 if element.r2 is not None else 1.0
            class_3 = _generally_class_3(c3 * eps, r2, floor * eps)
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=class_3, note="Classes 1 and 2 not applicable to axial compression")
            r1 = _clamp_r1(_require(element.r1, "r1", kind, stress))
            if r1 <= -1.0:
                return ElementLimits(class_1_limit=math.inf, class_2_limit=math.inf, class_3_limit=class_3, note="Web wholly in tension")
            class_1 = _at_least(c1 * eps / (1.0 + 0.6 * r1), floor * eps)
            class_2 = _at_least(c2 * eps / (1.0 + r1), floor * eps)
            return ElementLimits(class_1_limit=class_1, class_2_limit=class_2, class_3_limit=class_3, note="Generally")
    raise NotImplementedError(f"No Table 11/12 limits for element kind '{kind}'.") # pragma: no cover


def _class_from_limits(ratio: float, limits: ElementLimits) -> SectionClass:
    for limit, section_class in (
        (limits.class_1_limit, SectionClass.CLASS_1),
        (limits.class_2_limit, SectionClass.CLASS_2),
        (limits.class_3_limit, SectionClass.CLASS_3),
    ):
        if limit is not None and ratio <= limit:
            return section_class
    return SectionClass.CLASS_4


def classify_element(element: ElementInput, py_mpa: float) -> ElementClassification:
    """Classify one compression element per BS 5950-1:2000 Table 11 or Table 12.

    Where a table gives "Not applicable" for classes 1 and 2 (axial compression), an element within the class 3 limit
    is reported as class 3 semi-compact i.e. not slender.

    Args:
        element: Element geometry, kind and stress state
        py_mpa: Design strength py (N/mm²); for the web of a hybrid section use pyf of the flanges (Table 11 note c)
    """
    limits = element_limits(element, py_mpa)
    ratio = element.b_mm / element.t_mm
    section_class = _class_from_limits(ratio, limits)
    metadata: dict[str, Any] = {
        "table": f"BS 5950-1:2000 {element.kind.table}",
        "row": element.kind.description,
        "stress_case": element.stress.value,
    }
    if limits.note:
        metadata["note"] = limits.note
    if element.r1 is not None:
        metadata["r1"] = element.r1
    if element.r2 is not None or (element.kind in {ElementKind.WEB, ElementKind.HF_RHS_WEB, ElementKind.CF_RHS_WEB} and element.stress != ElementStressDistribution.BENDING):
        metadata["r2"] = element.r2 if element.r2 is not None else 1.0

    if element.kind == ElementKind.ANGLE:
        # Single angle / separated double angles in axial compression: all three criteria should be satisfied
        if element.leg_mm is None:
            raise ValueError("Angle elements in axial compression need leg_mm, the other leg d.")
        eps = epsilon(py_mpa)
        d_t = element.leg_mm / element.t_mm
        b_plus_d_t = (element.b_mm + element.leg_mm) / element.t_mm
        checks = {"b/t": (ratio, 15.0 * eps), "d/t": (d_t, 15.0 * eps), "(b+d)/t": (b_plus_d_t, 24.0 * eps)}
        metadata.update({label: value for label, (value, _) in checks.items()})
        metadata.update({f"{label}_limit": limit for label, (_, limit) in checks.items()})
        metadata["governing_check"] = max(checks, key=lambda label: checks[label][0] / checks[label][1])
        section_class = SectionClass.CLASS_3 if all(value <= limit for value, limit in checks.values()) else SectionClass.CLASS_4

    return ElementClassification(
        name=element.name,
        kind=element.kind,
        stress=element.stress,
        b_mm=element.b_mm,
        t_mm=element.t_mm,
        ratio=ratio,
        ratio_label=element.kind.ratio,
        class_1_limit=limits.class_1_limit,
        class_2_limit=limits.class_2_limit,
        class_3_limit=limits.class_3_limit,
        section_class=section_class,
        class_name=CLASS_NAMES[section_class],
        metadata=metadata,
    )


def classify_elements(
    elements: Sequence[ElementInput],
    py_mpa: float,
    stress_pattern: Optional[StressPattern] = None,
    r1: Optional[float] = None,
    r2: Optional[float] = None,
) -> ClassificationResult:
    """BS 5950-1:2000 3.5.1: classify every element; the section takes the highest (least favourable) class."""
    if not elements:
        raise ValueError("At least one element must be provided.")

    results = [classify_element(element, py_mpa) for element in elements]
    governing_rank = max(_CLASS_RANK[result.section_class] for result in results)
    governing_class = next(item for item, rank in _CLASS_RANK.items() if rank == governing_rank)
    governing = [result.name for result in results if _CLASS_RANK[result.section_class] == governing_rank]

    notes: list[str] = []
    if any(result.class_1_limit is None for result in results):
        notes.append("Classes 1 and 2 are not applicable to elements in axial compression; class 3 means not slender.")
    if governing_class == SectionClass.CLASS_4:
        notes.append("Class 4 slender: make explicit allowance for local buckling e.g. effective areas/moduli (3.6).")

    return ClassificationResult(
        epsilon=epsilon(py_mpa),
        py_mpa=py_mpa,
        elements=results,
        section_class=governing_class,
        class_name=CLASS_NAMES[governing_class],
        governing_elements=governing,
        is_slender=governing_class == SectionClass.CLASS_4,
        stress_pattern=stress_pattern,
        r1=r1,
        r2=r2,
        notes=notes,
    )


# --- Figure 5: element geometry of standard sections ---
ROLLED_I_SECTION_TYPES = (SectionType.UB, SectionType.UC, SectionType.UBP)
CHANNEL_SECTION_TYPES = (SectionType.PFC,)
SINGLE_ANGLE_SECTION_TYPES = (SectionType.L_EQUAL, SectionType.L_UNEQUAL)
DOUBLE_ANGLE_SECTION_TYPES = (SectionType.L_EQUAL_B2B, SectionType.L_UNEQUAL_B2B)
HF_RHS_SECTION_TYPES = (SectionType.HFRHS, SectionType.HFSHS)
CF_RHS_SECTION_TYPES = (SectionType.CFRHS, SectionType.CFSHS)
CHS_SECTION_TYPES = (SectionType.HFCHS, SectionType.CFCHS)


def compound_flange_elements(b_mm: float, T_mm: float, bp_mm: float, tp_mm: float, bo_mm: Optional[float] = None) -> list[ElementInput]:
    """BS 5950-1:2000 3.5.3 / Figure 6: elements of the compression flange of a compound I- or H-section.

    a) outstand b of the compound flange to the original flange thickness T: outstand element, rolled section
    b) internal width bp of the plate between lines of welds or bolts to the plate thickness tp: internal element
    c) outstand bo of the plate beyond those lines to tp: outstand element, welded section

    Args:
        b_mm: Outstand of the compound flange (mm), Figure 6a
        T_mm: Thickness of the original flange (mm)
        bp_mm: Internal width of the plate between lines of welds or bolts (mm), Figure 6b
        tp_mm: Thickness of the flange plate (mm)
        bo_mm: Outstand of the plate beyond the lines of welds or bolts (mm), Figure 6c; omit if none
    """
    elements = [
        ElementInput(name="compound_flange_outstand", kind=ElementKind.OUTSTAND_FLANGE_ROLLED, stress=ElementStressDistribution.BENDING, b_mm=b_mm, t_mm=T_mm),
        ElementInput(name="flange_plate_internal", kind=ElementKind.INTERNAL_FLANGE, stress=ElementStressDistribution.BENDING, b_mm=bp_mm, t_mm=tp_mm),
    ]
    if bo_mm is not None:
        elements.append(ElementInput(name="flange_plate_outstand", kind=ElementKind.OUTSTAND_FLANGE_WELDED, stress=ElementStressDistribution.BENDING, b_mm=bo_mm, t_mm=tp_mm))
    return elements


def _parse_pair(*candidates: Any) -> Optional[tuple[float, float]]:
    """First two numbers in a designation-like string e.g. '200x100' or '200x100x5.0'."""
    for value in candidates:
        if not isinstance(value, str) or not value:
            continue
        numbers = re.findall(r"\d+(?:\.\d+)?", value)
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
    return None


def _number(data: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0:
            return float(value)
    return None


def _need(data: dict[str, Any], label: str, *keys: str) -> float:
    value = _number(data, *keys)
    if value is None:
        raise ValueError(f"Missing {label}; provide one of {', '.join(repr(key) for key in keys)}.")
    return value


class _Geometry(BaseModel):
    """Figure 5 geometry resolved from a section, in BS 5950 notation (mm, cm², cm³)."""

    section_type: SectionType
    D: Optional[float] = None # overall depth
    B: Optional[float] = None # overall width
    d: Optional[float] = None # web depth (I/H/channel: between fillets); RHS: D - 3t (HF) or D - 5t (CF)
    b: Optional[float] = None # flange outstand (I/H: B/2; channel: B); RHS: B - 3t (HF) or B - 5t (CF)
    t: float # web or wall thickness
    T: Optional[float] = None # flange thickness
    Ag: Optional[float] = None # cm²
    legs: Optional[tuple[float, float]] = None # angles (longer, shorter)


def _geometry(section_type: SectionType, data: dict[str, Any]) -> _Geometry:
    Ag = _number(data, "A", "Ag", "total_area")
    if section_type in ROLLED_I_SECTION_TYPES or section_type in CHANNEL_SECTION_TYPES:
        B = _need(data, "flange width B", "B", "b")
        T = _need(data, "flange thickness T", "T", "tf")
        t = _need(data, "web thickness t", "t", "tw")
        d = _need(data, "web depth d between fillets", "d")
        b = B / 2.0 if section_type in ROLLED_I_SECTION_TYPES else B # Figure 5: rolled I/H b = B/2, rolled channel b = B
        return _Geometry(section_type=section_type, D=_number(data, "D", "h"), B=B, d=d, b=b, t=t, T=T, Ag=Ag)

    if section_type in SINGLE_ANGLE_SECTION_TYPES or section_type in DOUBLE_ANGLE_SECTION_TYPES:
        t = _need(data, "thickness t", "t")
        pair = _parse_pair(data.get("hxb"), data.get("hxh"), data.get("designation"))
        if pair is None:
            h = _need(data, "leg length", "h", "D")
            pair = (h, _number(data, "b", "B") or h)
        return _Geometry(section_type=section_type, t=t, Ag=Ag, legs=(max(pair), min(pair)))

    if section_type in HF_RHS_SECTION_TYPES or section_type in CF_RHS_SECTION_TYPES:
        t = _need(data, "wall thickness t", "t")
        pair = _parse_pair(data.get("hxb"), data.get("hxh"), data.get("designation"))
        D = _number(data, "D", "h") or (pair[0] if pair else None)
        B = _number(data, "B", "b") or (pair[1] if pair else None)
        if D is None or B is None:
            raise ValueError("Missing RHS dimensions; provide 'D' and 'B' (or 'h' and 'b', or 'hxb').")
        k = 3.0 if section_type in HF_RHS_SECTION_TYPES else 5.0 # Table 12 note a: HF b = B - 3t, d = D - 3t; CF b = B - 5t, d = D - 5t
        return _Geometry(section_type=section_type, D=D, B=B, d=D - k * t, b=B - k * t, t=t, Ag=Ag)

    if section_type in CHS_SECTION_TYPES:
        t = _need(data, "wall thickness t", "t")
        D = _number(data, "D", "d")
        if D is None:
            D_t = _need(data, "D/t", "d_t", "D_t")
            D = D_t * t
        return _Geometry(section_type=section_type, D=D, t=t, Ag=Ag)

    if section_type == SectionType.HFEHS:
        raise NotImplementedError("BS 5950-1:2000 Tables 11 and 12 do not cover elliptical hollow sections.")
    raise NotImplementedError(
        f"No BS 5950 adapter for section type '{section_type.value}'. Provide custom_elements explicitly."
    )


def _elements_for_pattern(
    geometry: _Geometry,
    pattern: StressPattern,
    r1: Optional[float],
    r2: Optional[float],
    axial: bool = False,
) -> list[ElementInput]:
    """Figure 5 elements for one stress pattern. Bending of I/H/channels/RHS is taken about the axis named.

    `axial` marks a non-zero axial force acting with the bending; webs then use the "generally" rows with r1 and r2.
    """
    st = geometry.section_type
    C, B_, M = ElementStressDistribution.COMPRESSION, ElementStressDistribution.BENDING, ElementStressDistribution.COMBINED
    combined = pattern == StressPattern.COMBINED or (axial and pattern == StressPattern.MAJOR_AXIS_BENDING)

    if st in ROLLED_I_SECTION_TYPES or st in CHANNEL_SECTION_TYPES:
        assert geometry.b is not None and geometry.T is not None and geometry.d is not None
        flange_stress = C if pattern == StressPattern.COMPRESSION else B_
        flange = ElementInput(name="flange", kind=ElementKind.OUTSTAND_FLANGE_ROLLED, stress=flange_stress, b_mm=geometry.b, t_mm=geometry.T)
        if st in CHANNEL_SECTION_TYPES:
            web_stress = C if pattern == StressPattern.COMPRESSION else (M if combined else B_)
            return [flange, ElementInput(name="web", kind=ElementKind.CHANNEL_WEB, stress=web_stress, b_mm=geometry.d, t_mm=geometry.t)]
        if pattern == StressPattern.MINOR_AXIS_BENDING:
            if axial and (r2 or 0.0) > 0.0:
                # the web lies on the minor-axis neutral axis, so it carries the axial compression only
                return [flange, ElementInput(name="web", kind=ElementKind.WEB, stress=C, b_mm=geometry.d, t_mm=geometry.t, r2=r2)]
            return [flange] # the web lies on the neutral axis and is not in compression
        if pattern == StressPattern.COMPRESSION:
            web = ElementInput(name="web", kind=ElementKind.WEB, stress=C, b_mm=geometry.d, t_mm=geometry.t, r2=r2)
        elif combined:
            web = ElementInput(name="web", kind=ElementKind.WEB, stress=M, b_mm=geometry.d, t_mm=geometry.t, r1=r1, r2=r2)
        else:
            web = ElementInput(name="web", kind=ElementKind.WEB, stress=B_, b_mm=geometry.d, t_mm=geometry.t)
        return [flange, web]

    if st in SINGLE_ANGLE_SECTION_TYPES or st in DOUBLE_ANGLE_SECTION_TYPES:
        assert geometry.legs is not None
        longer, shorter = geometry.legs
        if st in DOUBLE_ANGLE_SECTION_TYPES:
            # Outstand leg of an angle in contact back-to-back; the longer leg is taken as the outstand (conservative)
            return [ElementInput(name="outstand_leg", kind=ElementKind.ANGLE_OUTSTAND_LEG, stress=C if pattern == StressPattern.COMPRESSION else B_, b_mm=longer, t_mm=geometry.t)]
        if pattern == StressPattern.COMPRESSION:
            return [ElementInput(name="angle", kind=ElementKind.ANGLE, stress=C, b_mm=longer, t_mm=geometry.t, leg_mm=shorter)]
        return [
            ElementInput(name="leg_b", kind=ElementKind.ANGLE_LEG, stress=B_, b_mm=longer, t_mm=geometry.t),
            ElementInput(name="leg_d", kind=ElementKind.ANGLE_LEG, stress=B_, b_mm=shorter, t_mm=geometry.t),
        ]

    if st in HF_RHS_SECTION_TYPES or st in CF_RHS_SECTION_TYPES:
        assert geometry.b is not None and geometry.d is not None
        hot = st in HF_RHS_SECTION_TYPES
        flange_kind = ElementKind.HF_RHS_FLANGE if hot else ElementKind.CF_RHS_FLANGE
        web_kind = ElementKind.HF_RHS_WEB if hot else ElementKind.CF_RHS_WEB
        # Table 12 note a: B, b are always flange dimensions and D, d always web dimensions, relative to the axis of bending
        web_d, flange_b = (geometry.b, geometry.d) if pattern == StressPattern.MINOR_AXIS_BENDING else (geometry.d, geometry.b)
        if pattern == StressPattern.COMPRESSION:
            return [
                ElementInput(name="flange_wall", kind=flange_kind, stress=C, b_mm=flange_b, t_mm=geometry.t),
                ElementInput(name="web_wall", kind=web_kind, stress=C, b_mm=web_d, t_mm=geometry.t, r2=r2),
            ]
        web = (
            ElementInput(name="web_wall", kind=web_kind, stress=M, b_mm=web_d, t_mm=geometry.t, r1=r1, r2=r2)
            if combined or axial
            else ElementInput(name="web_wall", kind=web_kind, stress=B_, b_mm=web_d, t_mm=geometry.t)
        )
        return [ElementInput(name="flange_wall", kind=flange_kind, stress=B_, b_mm=flange_b, t_mm=geometry.t, web_d_mm=web_d), web]

    if st in CHS_SECTION_TYPES:
        assert geometry.D is not None
        if pattern == StressPattern.COMBINED:
            raise ValueError("CHS should be classified separately for axial compression and for bending (3.5.1).")
        return [ElementInput(name="wall", kind=ElementKind.CHS, stress=C if pattern == StressPattern.COMPRESSION else B_, b_mm=geometry.D, t_mm=geometry.t)]

    raise NotImplementedError(f"No BS 5950 adapter for section type '{st.value}'.") # pragma: no cover


def _governing_thickness(geometry: _Geometry) -> float:
    return max(value for value in (geometry.T, geometry.t) if value is not None)


def _classify_geometry(
    geometry: _Geometry,
    py_mpa: Optional[float],
    steel_grade: str,
    stress_pattern: StressPattern | str,
    Fc_kN: Optional[float],
) -> ClassificationResult:
    pattern = _normalize_stress_pattern(stress_pattern)
    py = py_mpa if py_mpa is not None else design_strength(_governing_thickness(geometry), steel_grade)

    r1: Optional[float] = None
    r2: Optional[float] = None
    st = geometry.section_type
    web_section = st in ROLLED_I_SECTION_TYPES or st in HF_RHS_SECTION_TYPES or st in CF_RHS_SECTION_TYPES
    axial = Fc_kN is not None and Fc_kN != 0.0
    if Fc_kN is not None and web_section:
        assert geometry.d is not None and geometry.b is not None
        if geometry.Ag is None:
            raise ValueError("Gross area A is needed to calculate r2 from Fc_kN.")
        rhs_minor = pattern == StressPattern.MINOR_AXIS_BENDING and st not in ROLLED_I_SECTION_TYPES
        case: Literal["equal-flanges", "box"] = "equal-flanges" if st in ROLLED_I_SECTION_TYPES else "box"
        ratios = stress_ratios(Fc_kN=Fc_kN, d_mm=geometry.b if rhs_minor else geometry.d, t_mm=geometry.t, pyw_mpa=py, Ag_cm2=geometry.Ag, case=case)
        r1, r2 = ratios.r1, ratios.r2
    if pattern == StressPattern.COMBINED and web_section and r1 is None:
        raise ValueError("Stress pattern 'combined' needs Fc_kN to calculate the stress ratios r1 and r2 (3.5.5).")

    elements = _elements_for_pattern(geometry, pattern, r1, r2, axial=axial)
    result = classify_elements(elements, py, stress_pattern=pattern, r1=r1, r2=r2)
    if pattern == StressPattern.COMPRESSION and r2 is None and web_section:
        result.notes.append("Web in axial compression checked with r2 = 1.0 (Fc = Ag pyw); pass Fc_kN for the actual r2.")
    return result


def classify_section(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
    Fc_kN: Optional[float] = None,
    custom_elements: Optional[Iterable[ElementInput]] = None,
) -> ClassificationResult:
    """BS 5950-1:2000 3.5: classify a UK section (UB, UC, UBP, PFC, angles, RHS/SHS, CHS) or explicit elements.

    Args:
        section: UK section object e.g. `UB("457x191x67")`
        py_mpa: Design strength py (N/mm²); defaults to Table 9 for `steel_grade` and the thickest element
        steel_grade: "S275", "S355" or "S460"; used only when py_mpa is not given
        stress_pattern: "compression", "bending-major-axis", "bending-minor-axis" or "combined", or a StressPattern
        Fc_kN: Axial compression (kN, negative for tension) for the stress ratios r1 and r2 of webs (3.5.5); required
            for "combined". With major-axis bending, a non-zero Fc_kN moves the web to the "generally" row.
        custom_elements: Explicit elements; overrides `section`

    Returns:
        ClassificationResult with the class of every element and the governing (least favourable) class
    """
    if custom_elements is not None:
        if py_mpa is None:
            raise ValueError("py_mpa is required with custom_elements.")
        return classify_elements(list(custom_elements), py_mpa)
    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    data = dict(section.get_properties())
    data.setdefault("designation", section.designation)
    return _classify_geometry(_geometry(section.get_section_type(), data), py_mpa, steel_grade, stress_pattern, Fc_kN)


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, Any],
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
    Fc_kN: Optional[float] = None,
) -> ClassificationResult:
    """BS 5950-1:2000 3.5: classify a section given as a plain dictionary.

    Accepts BS 5950 notation (D, B, T, t, d, A) or the UK module's (h, b, tf, tw, d, A). RHS need D and B (or h and b,
    or an 'hxb' string like '200x100') and t; CHS need D (or d) and t, or d_t and t; angles need 'hxb' or h and b, and t.
    """
    return _classify_geometry(_geometry(section_type, dict(data)), py_mpa, steel_grade, stress_pattern, Fc_kN)


# --- 3.5.6 Effective plastic modulus ---
class EffectivePlasticModulusResult(BaseModel):
    """BS 5950-1:2000 3.5.6: effective plastic modulus Seff of a class 3 semi-compact section (cm³)."""

    axis: Literal["major", "minor"]
    S_eff: float # cm³
    Z: float # elastic modulus, cm³
    S: float # plastic modulus, cm³
    method: str
    web_factor: Optional[float] = None
    flange_factor: Optional[float] = None
    reference: Reference = Field(default_factory=lambda: Reference(code=BS_5950, clause="3.5.6", title="Effective plastic modulus"))


def effective_plastic_modulus_i_section(
    Sx: float,
    Zx: float,
    Sy: float,
    Zy: float,
    b_T: float,
    d_t: float,
    beta_2f: float,
    beta_3f: float,
    beta_2w: float,
    beta_3w: float,
) -> tuple[float, float, float, float]:
    """BS 5950-1:2000 3.5.6.2: effective plastic moduli of class 3 semi-compact I- or H-sections with equal flanges.

    Sx,eff = Zx + (Sx - Zx)[((β3w/(d/t))² - 1)/((β3w/β2w)² - 1)] but Sx,eff <= Zx + (Sx - Zx)[(β3f/(b/T) - 1)/(β3f/β2f - 1)]
    Sy,eff = Zy + (Sy - Zy)[(β3f/(b/T) - 1)/(β3f/β2f - 1)] but Sy,eff <= Sy

    where β2f, β3f are the limiting b/T of a class 2 and class 3 flange, and β2w, β3w the limiting d/t of a class 2
    and class 3 web, from Table 11 (epsilon included). Both results are also capped at the plastic moduli.

    Returns:
        (Sx_eff, Sy_eff, web_factor, flange_factor); moduli in the units of Sx, Zx, Sy, Zy
    """
    if beta_3w <= beta_2w or beta_3f <= beta_2f:
        raise ValueError("Class 3 limits must exceed class 2 limits.")
    web_factor = ((beta_3w / d_t) ** 2 - 1.0) / ((beta_3w / beta_2w) ** 2 - 1.0)
    flange_factor = (beta_3f / b_T - 1.0) / (beta_3f / beta_2f - 1.0)
    Sx_eff = Zx + (Sx - Zx) * min(web_factor, flange_factor, 1.0)
    Sy_eff = Zy + (Sy - Zy) * min(flange_factor, 1.0)
    return Sx_eff, Sy_eff, web_factor, flange_factor


def effective_plastic_modulus_rhs(S: float, Z: float, b_t: float, d_t: float, beta_2f: float, beta_3f: float, beta_2w: float, beta_3w: float) -> tuple[float, float, float]:
    """BS 5950-1:2000 3.5.6.3: effective plastic modulus of a class 3 semi-compact RHS, for either axis of bending.

    Seff = Z + (S - Z)[((β3w/(d/t))² - 1)/((β3w/β2w)² - 1)] but Seff <= Z + (S - Z)[(β3f/(b/t) - 1)/(β3f/β2f - 1)]

    where β2f, β3f are the limiting b/t of a class 2 and class 3 flange, and β2w, β3w the limiting d/t of a class 2 and
    class 3 web, from Table 12 (epsilon included); b and d are the flange and web of the axis of bending (Table 12 note a).
    The result is also capped at S.

    Returns:
        (Seff, web_factor, flange_factor); modulus in the units of S and Z
    """
    if beta_3w <= beta_2w or beta_3f <= beta_2f:
        raise ValueError("Class 3 limits must exceed class 2 limits.")
    web_factor = ((beta_3w / d_t) ** 2 - 1.0) / ((beta_3w / beta_2w) ** 2 - 1.0)
    flange_factor = (beta_3f / b_t - 1.0) / (beta_3f / beta_2f - 1.0)
    return Z + (S - Z) * min(web_factor, flange_factor, 1.0), web_factor, flange_factor


def effective_plastic_modulus_chs(S: float, Z: float, D_t: float, py: float) -> float:
    """BS 5950-1:2000 3.5.6.4: effective plastic modulus of a class 3 semi-compact CHS, capped at S.

    Seff = Z + 1.485[(140/(D/t))(275/py))^0.5 - 1](S - Z)
    """
    if D_t <= 0.0 or py <= 0.0:
        raise ValueError("D_t and py must be positive.")
    factor = 1.485 * (math.sqrt(140.0 / D_t * 275.0 / py) - 1.0)
    return Z + (S - Z) * min(max(factor, 0.0), 1.0)


def effective_plastic_modulus(
    section: Optional[BaseSection] = None,
    py_mpa: Optional[float] = None,
    steel_grade: str = "S275",
    axis: Literal["major", "minor"] = "major",
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> EffectivePlasticModulusResult:
    """BS 5950-1:2000 3.5.6: effective plastic modulus Seff of a UK section in bending.

    Class 1 and 2 sections return S and class 4 sections raise ValueError (use 3.6); class 3 sections take:
        - Rolled I- or H-sections (UB, UC, UBP): 3.5.6.2, with Table 11 limits for a rolled flange outstand and a web with
          the neutral axis at mid-depth
        - RHS and SHS: 3.5.6.3, with the Table 12 limits of the walls in bending about `axis`
        - CHS: 3.5.6.4
        - Other cross-sections: Seff = Z (3.5.6.1)

    Args:
        section: UK section object e.g. `UB("457x191x67")`
        py_mpa: Design strength py (N/mm²); defaults to Table 9 for `steel_grade` and the thickest element
        steel_grade: "S275", "S355" or "S460"; used only when py_mpa is not given
        axis: "major" or "minor"
        section_type: Section type when passing plain properties
        properties: Plain properties or overrides, in section-table units (UK keys e.g. "W_pl_yy")

    Returns:
        EffectivePlasticModulusResult; moduli in cm³ as tabulated
    """
    data: dict[str, Any] = {}
    if section is not None:
        data.update(section.get_properties())
        data.setdefault("designation", section.designation)
        section_type = section.get_section_type()
    data.update(properties or {})
    if section_type is None:
        raise ValueError("Provide either 'section' or 'section_type' with 'properties'.")
    suffix = "yy" if axis == "major" else "zz"
    Z = _number(data, f"W_el_{suffix}", "W_el")
    S = _number(data, f"W_pl_{suffix}", "W_pl")
    if Z is None or S is None:
        raise ValueError(f"Section has no elastic/plastic moduli for {axis}-axis bending.")

    hollow = section_type in HF_RHS_SECTION_TYPES or section_type in CF_RHS_SECTION_TYPES or section_type in CHS_SECTION_TYPES
    if section_type not in ROLLED_I_SECTION_TYPES and not hollow:
        return EffectivePlasticModulusResult(axis=axis, S_eff=Z, Z=Z, S=S, method="3.5.6.1: Seff = Z")

    pattern = StressPattern.MAJOR_AXIS_BENDING if axis == "major" else StressPattern.MINOR_AXIS_BENDING
    result = classify_section_from_dict(section_type, data, py_mpa=py_mpa, steel_grade=steel_grade, stress_pattern=pattern)
    if result.section_class in (SectionClass.CLASS_1, SectionClass.CLASS_2):
        return EffectivePlasticModulusResult(axis=axis, S_eff=S, Z=Z, S=S, method="Class 1/2: Seff = S")
    if result.section_class == SectionClass.CLASS_4:
        raise ValueError("Class 4 slender section: use effective section properties (3.6), not Seff.")

    elements = {element.name: element for element in result.elements}
    if section_type in CHS_SECTION_TYPES:
        wall = elements["wall"]
        S_eff = effective_plastic_modulus_chs(S=S, Z=Z, D_t=wall.ratio, py=result.py_mpa)
        return EffectivePlasticModulusResult(axis=axis, S_eff=S_eff, Z=Z, S=S, method="3.5.6.4: CHS")
    if hollow:
        flange, web = elements["flange_wall"], elements["web_wall"]
        S_eff, web_factor, flange_factor = effective_plastic_modulus_rhs(
            S=S,
            Z=Z,
            b_t=flange.ratio,
            d_t=web.ratio,
            beta_2f=flange.class_2_limit or 0.0,
            beta_3f=flange.class_3_limit or 0.0,
            beta_2w=web.class_2_limit or 0.0,
            beta_3w=web.class_3_limit or 0.0,
        )
        return EffectivePlasticModulusResult(axis=axis, S_eff=S_eff, Z=Z, S=S, method="3.5.6.3: RHS", web_factor=web_factor, flange_factor=flange_factor)

    flange = elements["flange"]
    # A minor-axis classification omits the web; its limits are still needed for the factors
    eps = result.epsilon
    web_ratio = _need(data, "web depth d", "d") / _need(data, "web thickness", "tw", "t")
    beta = dict(beta_2f=flange.class_2_limit or 10.0 * eps, beta_3f=flange.class_3_limit or 15.0 * eps, beta_2w=100.0 * eps, beta_3w=120.0 * eps)
    Sx_eff, Sy_eff, web_factor, flange_factor = effective_plastic_modulus_i_section(
        Sx=S if axis == "major" else _need(data, "W_pl_yy", "W_pl_yy"),
        Zx=Z if axis == "major" else _need(data, "W_el_yy", "W_el_yy"),
        Sy=S if axis == "minor" else _need(data, "W_pl_zz", "W_pl_zz"),
        Zy=Z if axis == "minor" else _need(data, "W_el_zz", "W_el_zz"),
        b_T=flange.ratio,
        d_t=web_ratio,
        **beta,
    )
    return EffectivePlasticModulusResult(
        axis=axis,
        S_eff=Sx_eff if axis == "major" else Sy_eff,
        Z=Z,
        S=S,
        method="3.5.6.2: I- or H-section with equal flanges",
        web_factor=web_factor,
        flange_factor=flange_factor,
    )


# --- Calculation sheet rendering (see steelsnakes.base.renders) ---
_CLASS_CSS: dict[SectionClass, str] = {
    SectionClass.CLASS_1: "pass",
    SectionClass.CLASS_2: "pass",
    SectionClass.CLASS_3: "note",
    SectionClass.CLASS_4: "fail",
}


def _limit_text(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return "∞" if math.isinf(value) else f"{value:.2f}"


def render_classification(result: ClassificationResult, title: str = "Section Classification") -> CheckBlock:
    """Render a ClassificationResult as calculation-sheet rows with inline LaTeX (base.renders.CheckBlock)."""
    rows: list[Row] = [
        Row(
            expr=_m(r"\varepsilon") + " = " + _m(rf"\sqrt{{275/{result.py_mpa:.0f}}} = {result.epsilon:.4f}"),
            value=f"{result.epsilon:.4f}",
            clause="Table 11 note b",
        )
    ]
    if result.r1 is not None and result.r2 is not None:
        rows.append(Row(expr=_m(f"r_1 = {result.r1:.4f}") + " &ensp; " + _m(f"r_2 = {result.r2:.4f}"), clause="3.5.5"))
    for element in result.elements:
        numerator, denominator = element.ratio_label.split("/")
        rows.append(
            Row(
                expr=(
                    f"{element.name}: "
                    + _m(_frac(numerator, denominator))
                    + " = "
                    + _m(_frac(f"{element.b_mm:.1f}", f"{element.t_mm:.1f}"))
                    + " = "
                    + _m(f"{element.ratio:.2f}")
                    + " &ensp;&rarr;&ensp; "
                    + f"P {_limit_text(element.class_1_limit)} &ensp;C {_limit_text(element.class_2_limit)} &ensp;SC {_limit_text(element.class_3_limit)}"
                ),
                value=f"{element.ratio:.2f}",
                clause=element.metadata.get("table", "").replace("BS 5950-1:2000 ", ""),
                status=_CLASS_CSS[element.section_class],
                badge=element.class_name.capitalize(),
            )
        )
    rank = _CLASS_RANK[result.section_class]
    rows.append(
        Row(
            expr=f"Governed by {', '.join(result.governing_elements)} &rarr; Class {rank}",
            clause="3.5.1",
            status=_CLASS_CSS[result.section_class],
            badge=f"Class {rank} — {result.class_name.capitalize()}",
        )
    )
    return CheckBlock(title=title, subtitle="BS 5950-1:2000 3.5", rows=rows, result=result, passed=not result.is_slender)


if __name__ == "__main__":
    from steelsnakes.UK import UB

    beam = UB("457x191x67")
    for pattern in StressPattern:
        fc = 500.0 if pattern == StressPattern.COMBINED else None
        outcome = classify_section(section=beam, steel_grade="S275", stress_pattern=pattern, Fc_kN=fc)
        print(pattern.value, outcome.section_class.value, outcome.class_name, outcome.governing_elements)
    print("🐬")
