"""IS 800:2025 (draft) 10.8: Classification of cross sections.

Indian Standard General Construction in Steel, Code of Practice: the fourth revision of IS 800, wide circulation draft
CED 07 (27869) WC of April 2025. Clause numbers are the draft's; classification is 10.8 (3.7 in IS 800:2007).

Implements:
    - Table 1   Yield and ultimate stress of IS 2062 steels (9.2.4.2)
    - 10.8.2    Classes 1 plastic, 2 compact, 3 semi-compact and 4 slender
    - 10.8.3    Internal elements, outstands and tapered elements (the average thickness tabulated in IS 808)
    - 10.8.4    Compound elements in built-up sections
    - Table 2   Limiting width to thickness ratios, with the stress ratios r1 and r2 of its note 5
    - Fig. 2A   Dimensions of the elements of rolled, hollow and built-up sections
    - 10.8.2 d) Effective width of slender elements, the width in excess of the semi-compact limit deducted

Table 2 is EN 1993-1-1 Table 5.2 restated with ε = (250/fy)^0.5, e.g 9ε(235) = 8.7ε(250) and 72ε = 70ε. The draft leaves
the semi-compact limit of outstands under non-uniform stress blank ("---"); the uniform compression limit 13.6ε is used
there, which is conservative.

Section objects come from the IN module (IS 808 sections). Hollow sections have no IN section type yet, so they are
classified from plain properties with the hot finished and cold formed types (HFRHS, HFSHS, CFRHS, CFSHS, HFCHS, CFCHS).
Units: stresses N/mm² (MPa), dimensions mm, forces kN, areas cm²; i.e. as tabulated in IS 808.
Member checks (Sections 13 to 16) are in steelsnakes.IN.checks.uls, serviceability (12.6) in steelsnakes.IN.checks.sls.
"""

from __future__ import annotations

import difflib
import math
import re
from enum import Enum
from typing import Any, Iterable, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, Reference, SectionClass
from steelsnakes.base.renders import CheckBlock, Row, _frac, _m
from steelsnakes.base.sections import BaseSection, SectionType

IS_800 = DesignCode.IS_800
EDITION = "IS 800:2025 (draft for comments, CED 07 (27869) WC, April 2025)"

# --- Table 1: Tensile properties of IS 2062 structural steel ---
# grade: ((fy for t < 20 mm, 20 to 40 mm, > 40 mm), fu) in MPa; the qualities A, BR, B0 and C share a row
IS_2062_GRADES: dict[str, tuple[tuple[float, float, float], float]] = {
    "E250": ((250.0, 240.0, 230.0), 410.0),
    "E275": ((275.0, 265.0, 255.0), 430.0),
    "E300": ((300.0, 290.0, 280.0), 440.0),
    "E350": ((350.0, 330.0, 320.0), 490.0),
    "E410": ((410.0, 390.0, 380.0), 540.0),
    "E450": ((450.0, 430.0, 420.0), 570.0),
}


def _grade(steel_grade: str) -> str:
    match: Optional[re.Match[str]] = re.search(r"E\s*(\d{3})", steel_grade.upper()) # "e 350 BR" -> "E350"
    grade: str = f"E{match.group(1)}" if match else steel_grade.strip().upper()
    if grade not in IS_2062_GRADES:
        raise ValueError(f"Unknown steel_grade {steel_grade!r}. Options: {list(IS_2062_GRADES)}")
    return grade


def yield_stress(t: float, steel_grade: str = "E250") -> float:
    """IS 800:2025 Table 1: Yield stress fy (MPa) of an IS 2062 grade for the thickness t (mm).

    Args:
        t: Thickness of the thickest element in the cross section (mm); for rolled sections, the flange
        steel_grade: "E250" to "E450"; spaces, case and quality suffixes are ignored e.g. "e350 br"

    Returns:
        fy: Yield stress (MPa); for t < 20 mm, 20 mm to 40 mm, or > 40 mm
    """
    fy: tuple[float, float, float] = IS_2062_GRADES[_grade(steel_grade)][0]
    if t <= 0.0:
        raise ValueError("Thickness t must be positive.")
    if t < 20.0:
        return fy[0]
    if t <= 40.0:
        return fy[1]
    return fy[2]


def ultimate_stress(steel_grade: str = "E250") -> float:
    """IS 800:2025 Table 1: Ultimate tensile stress fu (MPa) of an IS 2062 grade, e.g. 410 MPa for E250."""
    return IS_2062_GRADES[_grade(steel_grade)][1]


def epsilon(fy: float) -> float:
    """IS 800:2025 Table 2 note 2: ε = (250/fy)^0.5."""
    if fy <= 0.0:
        raise ValueError("fy must be positive.")
    return math.sqrt(250.0 / fy)


# --- 10.8.2 Classification ---
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
    """Compression element rows of IS 800:2025 Table 2.

    The enum value is the string form used in the codebase e.g. `"outstand"`.
    `description` names the table row; `ratio` is the width to thickness ratio it limits.
    """

    OUTSTAND = "outstand" # i) outstanding element e.g. flange overhang of an I-section, stem of a T (10.8.3 b))
    INTERNAL = "internal" # ii) web of an I, channel, H or box section, and other internal elements (10.8.3 a))
    ANGLE_LEG = "angle-leg" # iii) angle, compression due to bending
    ANGLE = "angle" # iv) single angle, or double angles with the components separated, axial compression
    ANGLE_OUTSTAND_LEG = "angle-outstand-leg" # v) outstanding leg of an angle in contact back-to-back
    CHS = "chs" # vi) circular hollow tube, including welded tube

    @property
    def ratio(self) -> str:
        return _RATIO_LABELS[self]

    @property
    def description(self) -> str:
        return _KIND_DESCRIPTIONS[self]


_RATIO_LABELS: dict[ElementKind, str] = {
    ElementKind.OUTSTAND: "b/tf",
    ElementKind.INTERNAL: "d/tw",
    ElementKind.ANGLE_LEG: "b/t",
    ElementKind.ANGLE: "b/t",
    ElementKind.ANGLE_OUTSTAND_LEG: "d/t",
    ElementKind.CHS: "D/t",
}
_KIND_DESCRIPTIONS: dict[ElementKind, str] = {
    ElementKind.OUTSTAND: "i) Outstanding element",
    ElementKind.INTERNAL: "ii) Web of I, channel, H or box section",
    ElementKind.ANGLE_LEG: "iii) Angle, compression due to bending (both criteria)",
    ElementKind.ANGLE: "iv) Single angle, or double angles with the components separated, axial compression (all three criteria)",
    ElementKind.ANGLE_OUTSTAND_LEG: "v) Outstanding leg of an angle in contact back-to-back in a double angle member or with another component",
    ElementKind.CHS: "vi) Circular hollow tube, including welded tube",
}


class ElementStressDistribution(str, Enum):
    """Stress state of one compression element; the "Compression element" sub-rows of Table 2.

    - COMPRESSION: uniform compression; the "axial compression" rows
    - BENDING: webs with the neutral axis at mid-depth; outstands and CHS in bending (moment)
    - COMBINED: webs under axial force and bending; needs r1 (classes 1 and 2) and r2 (class 3), Table 2 note 5
    - TIP_COMPRESSION, TIP_TENSION: outstands under non-uniform stress; need r1, the part of the outstand in compression
    """

    COMPRESSION = "compression"
    BENDING = "bending"
    COMBINED = "combined"
    TIP_COMPRESSION = "tip-compression"
    TIP_TENSION = "tip-tension"


class StressPattern(str, Enum):
    """Section-level stress presets for `classify_section()` and `classify_section_from_dict()`."""

    COMPRESSION = "compression"
    MAJOR_AXIS_BENDING = "bending-major-axis" # about z-z
    MINOR_AXIS_BENDING = "bending-minor-axis" # about y-y
    COMBINED = "combined" # axial force + major axis bending; needs P_kN


_STRESS_PATTERN_ALIASES: dict[str, StressPattern] = {
    "compression": StressPattern.COMPRESSION,
    "axial": StressPattern.COMPRESSION,
    "axial-compression": StressPattern.COMPRESSION,
    "bending": StressPattern.MAJOR_AXIS_BENDING,
    "bending-major-axis": StressPattern.MAJOR_AXIS_BENDING,
    "major-axis-bending": StressPattern.MAJOR_AXIS_BENDING,
    "bending-z": StressPattern.MAJOR_AXIS_BENDING,
    "bending-minor-axis": StressPattern.MINOR_AXIS_BENDING,
    "minor-axis-bending": StressPattern.MINOR_AXIS_BENDING,
    "bending-y": StressPattern.MINOR_AXIS_BENDING,
    "combined": StressPattern.COMBINED,
    "combined-bending-and-compression": StressPattern.COMBINED,
    "axial-and-bending": StressPattern.COMBINED,
}


def _normalize_stress_pattern(value: StressPattern | str) -> StressPattern:
    if isinstance(value, StressPattern):
        return value
    normalized: str = "-".join(part for part in str(value).strip().lower().replace("_", "-").replace(" ", "-").split("-") if part)
    pattern: Optional[StressPattern] = _STRESS_PATTERN_ALIASES.get(normalized)
    if pattern is not None:
        return pattern
    suggestion: list[str] = difflib.get_close_matches(normalized, list(_STRESS_PATTERN_ALIASES), n=1, cutoff=0.72)
    suggestion_text: str = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    raise ValueError(
        "Unsupported stress_pattern. Use a StressPattern value or one of: 'compression', "
        f"'bending-major-axis', 'bending-minor-axis' or 'combined'.{suggestion_text}"
    )


class ElementInput(BaseModel):
    """One compression element to classify per IS 800:2025 Table 2.

    `b_mm` is the dimension in the numerator of the table's ratio (b, d or D per Fig. 2A) and `t_mm` the thickness in
    its denominator. Some rows need more:
        - ANGLE (axial compression): `leg_mm`, the other leg d, for d/t and (b + d)/t
        - INTERNAL in COMBINED: r1 (classes 1 and 2) and r2 (class 3)
        - OUTSTAND in TIP_COMPRESSION or TIP_TENSION: r1, the part of the outstand in compression
    """

    name: str
    kind: ElementKind
    stress: ElementStressDistribution = ElementStressDistribution.COMPRESSION
    b_mm: float = Field(gt=0.0)
    t_mm: float = Field(gt=0.0)
    leg_mm: Optional[float] = Field(default=None, gt=0.0)
    r1: Optional[float] = None # Table 2 note 5: depth under compression/overall depth
    r2: Optional[float] = None # Table 2 note 5: minimum/maximum compressive stress, negative for tension


class ElementClassification(BaseModel):
    """Classification of one compression element."""

    name: str
    kind: ElementKind
    stress: ElementStressDistribution
    b_mm: float
    t_mm: float
    ratio: float # b/tf, d/tw, b/t, d/t or D/t as per `ratio_label`
    ratio_label: str
    class_1_limit: Optional[float] # None where Table 2 says "Not applicable"
    class_2_limit: Optional[float]
    class_3_limit: Optional[float]
    section_class: SectionClass
    class_name: str # plastic, compact, semi-compact or slender
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Classification of a whole cross section: the least favourable class of its elements (10.8.2, Table 2 note 4)."""

    epsilon: float
    fy_mpa: float
    elements: list[ElementClassification]
    section_class: SectionClass
    class_name: str
    governing_elements: list[str]
    is_slender: bool
    stress_pattern: Optional[StressPattern] = None
    r1: Optional[float] = None
    r2: Optional[float] = None
    notes: list[str] = Field(default_factory=list)
    reference: Reference = Field(default_factory=lambda: Reference(code=IS_800, clause="10.8", title="Classification of cross sections", notes=EDITION))


class ElementLimits(BaseModel):
    """Limiting values (epsilon included) for one element, as tabulated in Table 2."""

    class_1_limit: Optional[float] = None
    class_2_limit: Optional[float] = None
    class_3_limit: Optional[float] = None
    note: Optional[str] = None


# --- Table 2 note 5: Stress ratios ---
class StressRatios(BaseModel):
    """IS 800:2025 Table 2 note 5 stress ratios r1 and r2."""

    r1: float # depth under compression/overall depth, 0 <= r1 <= 1
    r2: float # minimum/maximum compressive stress (tensile if negative), r2 <= 1


def stress_ratios(P_kN: float, d_mm: float, tw_mm: float, fy_mpa: float, A_cm2: float, webs: int = 1) -> StressRatios:
    """IS 800:2025 Table 2 note 5: stress ratios r1 and r2 of a web under axial force and bending.

    r1 = 0.5[1 + P/(n d tw fy)], the plastic depth in compression, with 0 <= r1 <= 1
    r2 = 2P/(A fy) - 1, the elastic stress ratio with the extreme fibre at yield, r2 <= 1

    where n is the number of webs (2 for a box or RHS). These are the plastic and elastic stress distributions of
    EN 1993-1-1 Table 5.2 (α and ψ), which Table 2 restates as r1 and r2.

    Args:
        P_kN: Axial compression (kN); negative for tension
        d_mm: Depth of the web d (mm), Fig. 2A
        tw_mm: Thickness of the web (mm)
        fy_mpa: Yield stress (MPa)
        A_cm2: Gross area of the cross section (cm²)
        webs: Number of webs
    """
    if d_mm <= 0.0 or tw_mm <= 0.0 or fy_mpa <= 0.0 or A_cm2 <= 0.0 or webs < 1:
        raise ValueError("d_mm, tw_mm, fy_mpa, A_cm2 and webs must be positive.")
    P_N: float = P_kN * 1_000.0
    r1: float = 0.5 * (1.0 + P_N / (webs * d_mm * tw_mm * fy_mpa))
    r2: float = 2.0 * P_N / (A_cm2 * 100.0 * fy_mpa) - 1.0
    return StressRatios(r1=max(0.0, min(r1, 1.0)), r2=min(r2, 1.0))


# --- Table 2: limiting width to thickness ratios ---
def _require(value: Optional[float], name: str, kind: ElementKind, stress: ElementStressDistribution) -> float:
    if value is None:
        raise ValueError(f"{kind.value} elements in {stress.value} need {name} (IS 800:2025 Table 2 note 5).")
    return value


def element_limits(element: ElementInput, fy: float) -> ElementLimits:
    """IS 800:2025 Table 2: limiting width to thickness ratios of one element, epsilon included."""
    eps: float = epsilon(fy)
    eps2: float = eps**2
    kind, stress = element.kind, element.stress

    match kind:
        case ElementKind.OUTSTAND:
            if stress in (ElementStressDistribution.TIP_COMPRESSION, ElementStressDistribution.TIP_TENSION):
                r1: float = min(_require(element.r1, "r1", kind, stress), 1.0)
                if r1 <= 0.0:
                    return ElementLimits(class_1_limit=math.inf, class_2_limit=math.inf, class_3_limit=math.inf, note="Outstand wholly in tension")
                factor: float = r1 if stress == ElementStressDistribution.TIP_COMPRESSION else r1 * math.sqrt(r1) # 8.7ε/r1 or 8.7ε/(r1√r1)
                return ElementLimits(
                    class_1_limit=8.7 * eps / factor,
                    class_2_limit=9.7 * eps / factor,
                    class_3_limit=13.6 * eps,
                    note="Non-uniform stress; Table 2 gives no class 3 limit, the uniform compression 13.6ε is used",
                )
            return ElementLimits(class_1_limit=8.7 * eps, class_2_limit=9.7 * eps, class_3_limit=13.6 * eps, note="Uniform compression")
        case ElementKind.INTERNAL:
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_1_limit=32.0 * eps, class_2_limit=36.8 * eps, class_3_limit=40.7 * eps, note="Axial compression")
            if stress == ElementStressDistribution.BENDING:
                return ElementLimits(class_1_limit=70.0 * eps, class_2_limit=80.0 * eps, class_3_limit=120.0 * eps, note="Neutral axis at mid-depth")
            if stress != ElementStressDistribution.COMBINED:
                raise ValueError(f"Internal elements take compression, bending or combined stress, not {stress.value}.")
            r1 = max(0.0, min(_require(element.r1, "r1", kind, stress), 1.0))
            r2: float = min(_require(element.r2, "r2", kind, stress), 1.0)
            if r1 > 0.5:
                class_1, class_2 = 384.0 * eps / (13.0 * r1 - 1.0), 442.0 * eps / (13.0 * r1 - 1.0)
            elif r1 > 0.0:
                class_1, class_2 = 35.0 * eps / r1, 40.2 * eps / r1
            else:
                class_1 = class_2 = math.inf # web wholly in tension
            class_3: float = 40.7 * eps / (0.67 + 0.33 * r2) if r2 > -1.0 else 60.0 * eps * (1.0 - r2) * math.sqrt(-r2)
            return ElementLimits(class_1_limit=class_1, class_2_limit=class_2, class_3_limit=class_3, note="Non-uniform stress")
        case ElementKind.ANGLE_LEG | ElementKind.ANGLE_OUTSTAND_LEG:
            return ElementLimits(class_1_limit=8.7 * eps, class_2_limit=9.7 * eps, class_3_limit=14.5 * eps)
        case ElementKind.ANGLE:
            return ElementLimits(class_3_limit=14.5 * eps, note="Classes 1 and 2 not applicable; also d/t <= 14.5ε and (b + d)/t <= 22.3ε")
        case ElementKind.CHS:
            if stress == ElementStressDistribution.COMPRESSION:
                return ElementLimits(class_3_limit=86.0 * eps2, note="Axial compression; classes 1 and 2 not applicable")
            return ElementLimits(class_1_limit=47.0 * eps2, class_2_limit=66.0 * eps2, class_3_limit=85.0 * eps2, note="Moment")
    raise NotImplementedError(f"No Table 2 limits for element kind '{kind}'.") # pragma: no cover


def _class_from_limits(ratio: float, limits: ElementLimits) -> SectionClass:
    for limit, section_class in (
        (limits.class_1_limit, SectionClass.CLASS_1),
        (limits.class_2_limit, SectionClass.CLASS_2),
        (limits.class_3_limit, SectionClass.CLASS_3),
    ):
        if limit is not None and ratio <= limit:
            return section_class
    return SectionClass.CLASS_4


def classify_element(element: ElementInput, fy_mpa: float) -> ElementClassification:
    """Classify one compression element per IS 800:2025 Table 2.

    Where Table 2 gives "Not applicable" for classes 1 and 2 (axial compression of angles and CHS), an element within the
    class 3 limit is reported as class 3 semi-compact i.e. not slender.

    Args:
        element: Element geometry, kind and stress state
        fy_mpa: Yield stress fy (MPa)
    """
    limits: ElementLimits = element_limits(element, fy_mpa)
    ratio: float = element.b_mm / element.t_mm
    section_class: SectionClass = _class_from_limits(ratio, limits)
    metadata: dict[str, Any] = {
        "table": "IS 800:2025 Table 2",
        "row": element.kind.description,
        "stress_case": element.stress.value,
    }
    if limits.note:
        metadata["note"] = limits.note
    if element.r1 is not None:
        metadata["r1"] = element.r1
    if element.r2 is not None:
        metadata["r2"] = element.r2

    if element.kind == ElementKind.ANGLE:
        # Single angle / separated double angles in axial compression: all three criteria should be satisfied
        if element.leg_mm is None:
            raise ValueError("Angle elements in axial compression need leg_mm, the other leg d.")
        eps: float = epsilon(fy_mpa)
        d_t: float = element.leg_mm / element.t_mm
        b_plus_d_t: float = (element.b_mm + element.leg_mm) / element.t_mm
        checks: dict[str, tuple[float, float]] = {"b/t": (ratio, 14.5 * eps), "d/t": (d_t, 14.5 * eps), "(b+d)/t": (b_plus_d_t, 22.3 * eps)}
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
    fy_mpa: float,
    stress_pattern: Optional[StressPattern] = None,
    r1: Optional[float] = None,
    r2: Optional[float] = None,
) -> ClassificationResult:
    """IS 800:2025 10.8.2: classify every element; the section takes the least favourable class (Table 2 note 4)."""
    if not elements:
        raise ValueError("At least one element must be provided.")

    results: list[ElementClassification] = [classify_element(element, fy_mpa) for element in elements]
    governing_rank: int = max(_CLASS_RANK[result.section_class] for result in results)
    governing_class: SectionClass = next(item for item, rank in _CLASS_RANK.items() if rank == governing_rank)
    governing: list[str] = [result.name for result in results if _CLASS_RANK[result.section_class] == governing_rank]

    notes: list[str] = []
    if any(result.class_1_limit is None for result in results):
        notes.append("Classes 1 and 2 are not applicable to angles and CHS in axial compression; class 3 means not slender.")
    eps: float = epsilon(fy_mpa)
    for result in results:
        if result.kind == ElementKind.INTERNAL and result.name.startswith("web") and result.ratio > 67.0 * eps:
            notes.append(f"Table 2 note 3: {result.name} d/t = {result.ratio:.1f} > 67ε; check shear buckling (15.4.2).")
    if governing_class == SectionClass.CLASS_4:
        notes.append("Class 4 slender: use the effective section, deducting the width in excess of the semi-compact limit (10.8.2 d)).")

    return ClassificationResult(
        epsilon=eps,
        fy_mpa=fy_mpa,
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


def effective_width(b_mm: float, t_mm: float, class_3_limit: float) -> float:
    """IS 800:2025 10.8.2 d): effective width of a slender element, the width in excess of the semi-compact limit
    deducted, b_eff = min(b, β3 t) with β3 the class 3 limit of Table 2 (epsilon included) (mm)."""
    if b_mm <= 0.0 or t_mm <= 0.0:
        raise ValueError("b_mm and t_mm must be positive.")
    return min(b_mm, class_3_limit * t_mm)


# --- Fig. 2A: element geometry of standard sections ---
ROLLED_I_SECTION_TYPES = (
    SectionType.JB,
    SectionType.LWB,
    SectionType.MWB,
    SectionType.WFB,
    SectionType.NPB,
    SectionType.WPB,
    SectionType.SC,
    SectionType.HWB,
    SectionType.PBP,
)
CHANNEL_SECTION_TYPES = (SectionType.JC, SectionType.LWC, SectionType.MWC, SectionType.MPC)
ANGLE_SECTION_TYPES = (SectionType.EA, SectionType.UA)
HOT_ROLLED_RHS_SECTION_TYPES = (SectionType.HFRHS, SectionType.HFSHS)
COLD_FORMED_RHS_SECTION_TYPES = (SectionType.CFRHS, SectionType.CFSHS)
RHS_SECTION_TYPES = HOT_ROLLED_RHS_SECTION_TYPES + COLD_FORMED_RHS_SECTION_TYPES
CHS_SECTION_TYPES = (SectionType.HFCHS, SectionType.CFCHS)
COLD_FORMED_SECTION_TYPES = (SectionType.CFRHS, SectionType.CFSHS, SectionType.CFCHS)


def compound_flange_elements(
    be_mm: float,
    te_mm: float,
    bi_mm: Optional[float] = None,
    tp_mm: Optional[float] = None,
    bo_mm: Optional[float] = None,
) -> list[ElementInput]:
    """IS 800:2025 10.8.4 / Fig. 2A: elements of a compound element of a built-up section, each to its own thickness.

    a) outstanding width be of the compound element: outstand
    b) internal width bi of each added plate between the lines of welds or fasteners: internal element
    c) outstand bo of the added plate beyond those lines: outstand

    Args:
        be_mm: Outstanding width of the compound element (mm)
        te_mm: Its thickness (mm)
        bi_mm: Internal width of the added plate between lines of welds or fasteners (mm); omit if none
        tp_mm: Thickness of the added plate (mm)
        bo_mm: Outstand of the added plate beyond the lines of welds or fasteners (mm); omit if none
    """
    elements: list[ElementInput] = [ElementInput(name="compound_outstand", kind=ElementKind.OUTSTAND, b_mm=be_mm, t_mm=te_mm)]
    if (bi_mm is not None or bo_mm is not None) and tp_mm is None:
        raise ValueError("tp_mm, the thickness of the added plate, is needed with bi_mm or bo_mm.")
    if bi_mm is not None:
        elements.append(ElementInput(name="plate_internal", kind=ElementKind.INTERNAL, b_mm=bi_mm, t_mm=tp_mm)) # type: ignore[arg-type]
    if bo_mm is not None:
        elements.append(ElementInput(name="plate_outstand", kind=ElementKind.OUTSTAND, b_mm=bo_mm, t_mm=tp_mm)) # type: ignore[arg-type]
    return elements


def _parse_pair(*candidates: Any) -> Optional[tuple[float, float]]:
    """First two numbers in a designation-like string e.g. 'ISA 100x75x8' or '200x100x5.0'."""
    for value in candidates:
        if not isinstance(value, str) or not value:
            continue
        numbers: list[str] = re.findall(r"\d+(?:\.\d+)?", value)
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
    value: Optional[float] = _number(data, *keys)
    if value is None:
        raise ValueError(f"Missing {label}; provide one of {', '.join(repr(key) for key in keys)}.")
    return value


class _Geometry(BaseModel):
    """Fig. 2A geometry resolved from a section, in IS 808 notation (mm, cm²)."""

    section_type: SectionType
    D: Optional[float] = None # overall depth, or outside diameter of CHS
    B: Optional[float] = None # overall width
    d: Optional[float] = None # web depth (I/channel: clear of the root fillets); RHS: D - 3t
    b: Optional[float] = None # flange outstand (I: B/2; channel: B); RHS: B - 3t
    t: float # web or wall thickness
    T: Optional[float] = None # flange thickness (the average thickness of tapered flanges, 10.8.3 c))
    A: Optional[float] = None # cm²
    legs: Optional[tuple[float, float]] = None # angles (longer, shorter)


def _geometry(section_type: SectionType, data: dict[str, Any]) -> _Geometry:
    A: Optional[float] = _number(data, "area", "A", "Ag")
    if section_type in ROLLED_I_SECTION_TYPES or section_type in CHANNEL_SECTION_TYPES:
        D: float = _need(data, "depth D", "D", "h")
        B: float = _need(data, "flange width B", "B", "b")
        T: float = _need(data, "flange thickness T", "T", "tf")
        t: float = _need(data, "web thickness t", "tw", "t")
        R1: float = _number(data, "R1", "r1", "r") or 0.0
        d: float = _number(data, "d") or D - 2.0 * (T + R1) # Fig. 2A: depth of the web clear of the root fillets
        b: float = B / 2.0 if section_type in ROLLED_I_SECTION_TYPES else B # Fig. 2A: rolled beams B/2, rolled channels B
        return _Geometry(section_type=section_type, D=D, B=B, d=d, b=b, t=t, T=T, A=A)

    if section_type in ANGLE_SECTION_TYPES:
        t = _need(data, "thickness t", "t")
        legs: Optional[tuple[float, float]] = None
        leg_a, leg_b = _number(data, "a", "h", "D"), _number(data, "b", "B")
        if leg_a is not None:
            legs = (leg_a, leg_b or leg_a)
        else:
            legs = _parse_pair(data.get("hxb"), data.get("designation"))
        if legs is None:
            raise ValueError("Missing angle legs; provide 'a' and 'b' (or 'hxb', or a designation like 'ISA 100x75x8').")
        return _Geometry(section_type=section_type, t=t, A=A, legs=(max(legs), min(legs)))

    if section_type in RHS_SECTION_TYPES:
        t = _need(data, "wall thickness t", "t")
        pair: Optional[tuple[float, float]] = _parse_pair(data.get("hxb"), data.get("hxh"), data.get("designation"))
        depth: Optional[float] = _number(data, "D", "h") or (pair[0] if pair else None)
        width: Optional[float] = _number(data, "B", "b") or (pair[1] if pair else None)
        if depth is None or width is None:
            raise ValueError("Missing RHS dimensions; provide 'D' and 'B' (or 'h' and 'b', or 'hxb').")
        # Fig. 2A: the flat widths between the corners, taken as B - 3t and D - 3t as in EN 1993-1-1 practice
        return _Geometry(section_type=section_type, D=depth, B=width, d=depth - 3.0 * t, b=width - 3.0 * t, t=t, A=A)

    if section_type in CHS_SECTION_TYPES:
        t = _need(data, "wall thickness t", "t")
        diameter: Optional[float] = _number(data, "D", "d")
        if diameter is None:
            diameter = _need(data, "D/t", "D_t", "d_t") * t
        return _Geometry(section_type=section_type, D=diameter, t=t, A=A)

    raise NotImplementedError(
        f"No IS 800 adapter for section type '{section_type.value}'. Provide custom_elements explicitly."
    )


def _elements_for_pattern(
    geometry: _Geometry,
    pattern: StressPattern,
    r1: Optional[float],
    r2: Optional[float],
    axial: bool = False,
) -> list[ElementInput]:
    """Fig. 2A elements for one stress pattern; bending of I, channel and RHS is about the axis named.

    `axial` marks a non-zero axial force acting with the bending; webs then use the non-uniform rows with r1 and r2.
    """
    st: SectionType = geometry.section_type
    C, B_, M = ElementStressDistribution.COMPRESSION, ElementStressDistribution.BENDING, ElementStressDistribution.COMBINED
    combined: bool = pattern == StressPattern.COMBINED or (axial and pattern == StressPattern.MAJOR_AXIS_BENDING)

    if st in ROLLED_I_SECTION_TYPES or st in CHANNEL_SECTION_TYPES:
        assert geometry.b is not None and geometry.T is not None and geometry.d is not None
        if st in ROLLED_I_SECTION_TYPES and pattern == StressPattern.MINOR_AXIS_BENDING:
            # the whole outstand is in compression, from zero at the web to a maximum at the tip: r1 = 1
            flange = ElementInput(name="flange", kind=ElementKind.OUTSTAND, stress=ElementStressDistribution.TIP_COMPRESSION, b_mm=geometry.b, t_mm=geometry.T, r1=1.0)
        else:
            # channels in minor axis bending are taken in uniform compression, which is conservative
            flange = ElementInput(name="flange", kind=ElementKind.OUTSTAND, stress=C, b_mm=geometry.b, t_mm=geometry.T)
        if pattern == StressPattern.MINOR_AXIS_BENDING:
            if st in CHANNEL_SECTION_TYPES or (axial and (r2 or -1.0) > -1.0):
                # the web of a channel lies to one side of the minor axis, taken in compression; the web of an I-section lies
                # on it and carries the axial compression only
                return [flange, ElementInput(name="web", kind=ElementKind.INTERNAL, stress=C, b_mm=geometry.d, t_mm=geometry.t)]
            return [flange] # the web lies on the neutral axis and is not in compression
        if pattern == StressPattern.COMPRESSION:
            web = ElementInput(name="web", kind=ElementKind.INTERNAL, stress=C, b_mm=geometry.d, t_mm=geometry.t)
        elif combined:
            web = ElementInput(name="web", kind=ElementKind.INTERNAL, stress=M, b_mm=geometry.d, t_mm=geometry.t, r1=r1, r2=r2)
        else:
            web = ElementInput(name="web", kind=ElementKind.INTERNAL, stress=B_, b_mm=geometry.d, t_mm=geometry.t)
        return [flange, web]

    if st in ANGLE_SECTION_TYPES:
        assert geometry.legs is not None
        longer, shorter = geometry.legs
        if pattern == StressPattern.COMPRESSION:
            return [ElementInput(name="angle", kind=ElementKind.ANGLE, stress=C, b_mm=longer, t_mm=geometry.t, leg_mm=shorter)]
        return [
            ElementInput(name="leg_b", kind=ElementKind.ANGLE_LEG, stress=B_, b_mm=longer, t_mm=geometry.t),
            ElementInput(name="leg_d", kind=ElementKind.ANGLE_LEG, stress=B_, b_mm=shorter, t_mm=geometry.t),
        ]

    if st in RHS_SECTION_TYPES:
        assert geometry.b is not None and geometry.d is not None
        # the flange walls are those parallel to the axis of bending
        web_d, flange_b = (geometry.b, geometry.d) if pattern == StressPattern.MINOR_AXIS_BENDING else (geometry.d, geometry.b)
        flange_wall = ElementInput(name="flange_wall", kind=ElementKind.INTERNAL, stress=C, b_mm=flange_b, t_mm=geometry.t)
        if pattern == StressPattern.COMPRESSION:
            return [flange_wall, ElementInput(name="web_wall", kind=ElementKind.INTERNAL, stress=C, b_mm=web_d, t_mm=geometry.t)]
        if combined or axial:
            return [flange_wall, ElementInput(name="web_wall", kind=ElementKind.INTERNAL, stress=M, b_mm=web_d, t_mm=geometry.t, r1=r1, r2=r2)]
        return [flange_wall, ElementInput(name="web_wall", kind=ElementKind.INTERNAL, stress=B_, b_mm=web_d, t_mm=geometry.t)]

    if st in CHS_SECTION_TYPES:
        assert geometry.D is not None
        # Table 2 vi): a) moment, b) axial compression; axial force with moment takes the moment row (85ε² < 86ε²)
        return [ElementInput(name="wall", kind=ElementKind.CHS, stress=C if pattern == StressPattern.COMPRESSION else B_, b_mm=geometry.D, t_mm=geometry.t)]

    raise NotImplementedError(f"No IS 800 adapter for section type '{st.value}'.") # pragma: no cover


def _governing_thickness(geometry: _Geometry) -> float:
    return max(value for value in (geometry.T, geometry.t) if value is not None)


def _classify_geometry(
    geometry: _Geometry,
    fy_mpa: Optional[float],
    steel_grade: str,
    stress_pattern: StressPattern | str,
    P_kN: Optional[float],
) -> ClassificationResult:
    pattern: StressPattern = _normalize_stress_pattern(stress_pattern)
    fy: float = fy_mpa if fy_mpa is not None else yield_stress(_governing_thickness(geometry), steel_grade)

    r1: Optional[float] = None
    r2: Optional[float] = None
    st: SectionType = geometry.section_type
    web_section: bool = st in ROLLED_I_SECTION_TYPES or st in CHANNEL_SECTION_TYPES or st in RHS_SECTION_TYPES
    axial: bool = P_kN is not None and P_kN != 0.0
    if P_kN is not None and web_section and pattern != StressPattern.COMPRESSION:
        assert geometry.d is not None and geometry.b is not None
        if geometry.A is None:
            raise ValueError("Gross area A is needed to calculate r1 and r2 from P_kN.")
        rhs: bool = st in RHS_SECTION_TYPES
        web_depth: float = geometry.b if (rhs and pattern == StressPattern.MINOR_AXIS_BENDING) else geometry.d
        ratios: StressRatios = stress_ratios(P_kN=P_kN, d_mm=web_depth, tw_mm=geometry.t, fy_mpa=fy, A_cm2=geometry.A, webs=2 if rhs else 1)
        r1, r2 = ratios.r1, ratios.r2
    if pattern == StressPattern.COMBINED and web_section and r1 is None:
        raise ValueError("Stress pattern 'combined' needs P_kN to calculate the stress ratios r1 and r2 (Table 2 note 5).")

    elements: list[ElementInput] = _elements_for_pattern(geometry, pattern, r1, r2, axial=axial)
    result: ClassificationResult = classify_elements(elements, fy, stress_pattern=pattern, r1=r1, r2=r2)
    if st in CHS_SECTION_TYPES and pattern == StressPattern.COMBINED:
        result.notes.append("CHS under axial force and moment: Table 2 vi) a), the moment row, is used.")
    return result


def classify_section(
    section: Optional[BaseSection] = None,
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
    P_kN: Optional[float] = None,
    custom_elements: Optional[Iterable[ElementInput]] = None,
) -> ClassificationResult:
    """IS 800:2025 10.8: classify an IS 808 section (beams, columns, piles, channels, angles) or explicit elements.

    Args:
        section: IN section object e.g. `MediumWeightBeam(designation="ISMB 300", ...)`
        fy_mpa: Yield stress fy (MPa); defaults to Table 1 for `steel_grade` and the thickest element
        steel_grade: IS 2062 grade "E250" to "E450"; used only when fy_mpa is not given
        stress_pattern: "compression", "bending-major-axis", "bending-minor-axis" or "combined", or a StressPattern
        P_kN: Axial compression (kN, negative for tension) for the stress ratios r1 and r2 of webs (Table 2 note 5);
            required for "combined". With major axis bending, a non-zero P_kN moves the web to the non-uniform rows.
        custom_elements: Explicit elements; overrides `section`

    Returns:
        ClassificationResult with the class of every element and the governing (least favourable) class
    """
    if custom_elements is not None:
        if fy_mpa is None:
            raise ValueError("fy_mpa is required with custom_elements.")
        return classify_elements(list(custom_elements), fy_mpa)
    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    data: dict[str, Any] = dict(section.get_properties())
    data.setdefault("designation", section.designation)
    return _classify_geometry(_geometry(section.get_section_type(), data), fy_mpa, steel_grade, stress_pattern, P_kN)


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, Any],
    fy_mpa: Optional[float] = None,
    steel_grade: str = "E250",
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
    P_kN: Optional[float] = None,
) -> ClassificationResult:
    """IS 800:2025 10.8: classify a section given as a plain dictionary.

    Accepts IS 808 notation (D, B, T, t, R1, area) or the common aliases (h, b, tf, tw, r, A). I-sections and channels
    need D, B, T, t and R1 (or d); angles need 'a' and 'b' (or 'hxb') and t; RHS need D and B (or h and b, or 'hxb') and
    t; CHS need D (or d) and t, or D_t and t.
    """
    return _classify_geometry(_geometry(section_type, dict(data)), fy_mpa, steel_grade, stress_pattern, P_kN)


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
            expr=_m(r"\varepsilon") + " = " + _m(rf"\sqrt{{250/{result.fy_mpa:.0f}}} = {result.epsilon:.4f}"),
            value=f"{result.epsilon:.4f}",
            clause="Table 2 note 2",
        )
    ]
    if result.r1 is not None and result.r2 is not None:
        rows.append(Row(expr=_m(f"r_1 = {result.r1:.4f}") + " &ensp; " + _m(f"r_2 = {result.r2:.4f}"), clause="Table 2 note 5"))
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
                clause="Table 2",
                status=_CLASS_CSS[element.section_class],
                badge=element.class_name.capitalize(),
            )
        )
    rank: int = _CLASS_RANK[result.section_class]
    rows.append(
        Row(
            expr=f"Governed by {', '.join(result.governing_elements)} &rarr; Class {rank}",
            clause="10.8.2",
            status=_CLASS_CSS[result.section_class],
            badge=f"Class {rank} — {result.class_name.capitalize()}",
        )
    )
    return CheckBlock(title=title, subtitle="IS 800:2025 10.8", rows=rows, result=result, passed=not result.is_slender)


if __name__ == "__main__":
    from steelsnakes.IN.sections import MediumWeightBeam

    # ISMB 300 (IS 808): D = 300, B = 140, t = 7.5, T = 12.4, R1 = 14 mm, A = 56.26 cm²
    beam = MediumWeightBeam(designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26)
    for pattern in StressPattern:
        load: Optional[float] = 500.0 if pattern == StressPattern.COMBINED else None
        outcome: ClassificationResult = classify_section(section=beam, steel_grade="E250", stress_pattern=pattern, P_kN=load)
        print(pattern.value, outcome.section_class.value, outcome.class_name, outcome.governing_elements)
    print("🐬")
