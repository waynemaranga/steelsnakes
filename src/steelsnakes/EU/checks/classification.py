from __future__ import annotations

import difflib
import math
from enum import Enum
from typing import Callable, Iterable, Literal, Optional, Sequence, cast

from pydantic import BaseModel, Field

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.exceptions import SectionClass4Error
from steelsnakes.base.sections import BaseSection, SectionType

GAMMA_M0 = 1.0 # EN 1993-1-1 6.1(1) recommended value; also the UK NA value

ElementKind = Literal[
    "internal", # Table 5.2 Sheet 1/3
    "outstand", # Table 5.2, Sheet 2/3
    "angle",    # Table 5.2, Sheet 3/3
    "tubular"   # Table 5.2, Sheet 3/3
    ]  # TODO: expose to Public API: INTERNAL COMPRESSION ELEMENT, OUTSTAND FLANGE AND ANGLE


class ElementStressDistribution(str, Enum):
    """Stress pattern applied to one classification element i.e "part subject to..." """
    COMPRESSION = "compression"
    BENDING = "bending"
    COMBINED = ("combined")  # TODO: expose to Public API it's COMBINED BENDING AND COMPRESSION


class StressPattern(str, Enum):
    """Section-level stress presets for `classify_section()` and `classify_section_from_dict()`.

    Each preset maps onto element stress distributions; the axis matters for hollow sections, where it selects which
    walls are webs (in bending) and which are flanges (in compression).
    """
    COMPRESSION = "compression"
    MAJOR_AXIS_BENDING = "bending-major-axis"
    MINOR_AXIS_BENDING = "bending-minor-axis"
    COMBINED = "combined"


OutstandTip = Literal["compression", "tension"] # Table 5.2 Sheet 2/3, part subject to bending and compression


# --- Section types for classification checks ---
ROLLED_I_SECTION_TYPES = (
    # Includes H-sections
    SectionType.IPE,
    SectionType.HE,
    SectionType.HL,
    SectionType.HLZ,
    SectionType.UB,
    SectionType.HD,
    SectionType.HP,
    SectionType.UC,
    SectionType.UBP,
)

BUILT_UP_I_SECTION_TYPES = () # TODO: implement built-up sections

CHANNEL_SECTION_TYPES = (
    SectionType.PFC,
    SectionType.UPE,
    SectionType.UPN,
)

BOX_SECTION_TYPES = () # TODO: implement built-up box sections

ANGLE_SECTION_TYPES = (
    SectionType.L_EQUAL,
    SectionType.L_UNEQUAL,
    SectionType.L_EQUAL_B2B,
    SectionType.L_UNEQUAL_B2B,
)
RECTANGULAR_HOLLOW_SECTION_TYPES = (
    SectionType.HFRHS,
    SectionType.CFRHS,
)
SQUARE_HOLLOW_SECTION_TYPES = (
    SectionType.HFSHS,
    SectionType.CFSHS,
)
ROUND_HOLLOW_SECTION_TYPES = (
    SectionType.HFCHS,
    SectionType.CFCHS,
)
ELLIPTICAL_HOLLOW_SECTION_TYPES = (SectionType.HFEHS,)
HOLLOW_INTERNAL_SECTION_TYPES = (
    RECTANGULAR_HOLLOW_SECTION_TYPES + SQUARE_HOLLOW_SECTION_TYPES
)


class ElementInput(BaseModel):
    """Input data for section's element to classify according to EN 1993-1-1 Table 5.2."""
    name: str
    kind: ElementKind
    stress: ElementStressDistribution = ElementStressDistribution.COMPRESSION
    c_mm: float = Field(gt=0.0)
    t_mm: float = Field(gt=0.0)
    h_mm: Optional[float] = None # for angles, longer leg, Table 5.2 Sheet 3/3
    b_mm: Optional[float] = None # for angles, shorter leg, Table 5.2 Sheet 3/3
    dia_mm: Optional[float] = None # for tubular sections, Table 5.2 Sheet 3/3; won't use 'd'
    alpha: Optional[float] = None
    psi: Optional[float] = None
    tip: Optional[OutstandTip] = None # outstands in combined bending and compression: is the free edge (tip) in compression or tension
    sigma_com_ed_mpa: Optional[float] = Field(default=None, gt=0.0) # 5.5.2(9): max design compressive stress in the part


class ElementClassification(BaseModel):
    """Classification result for one plate element."""

    name: str
    kind: ElementKind
    stress: ElementStressDistribution
    c_mm: float
    t_mm: float
    c_over_t: float
    class_1_limit: Optional[float]
    class_2_limit: Optional[float]
    class_3_limit: Optional[float]
    section_class: SectionClass
    metadata: dict[str, float | str] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Aggregate section classification from one or more element classifications i.e for a whole section or built-up part."""

    epsilon: float
    fy_mpa: float
    elements: list[ElementClassification]
    section_class: SectionClass
    governing_elements: list[str]
    notes: list[str] = Field(default_factory=list)


class ClassificationLimits(BaseModel):
    """Limits container for EC3 section-classification checks."""

    class_1_limit: Optional[float] = None
    class_2_limit: Optional[float] = None
    class_3_limit: Optional[float] = None
    secondary_class_3_limit: Optional[float] = None


def _normalize_stress_pattern(value: StressPattern | ElementStressDistribution | str) -> ElementStressDistribution:
    """Normalize stress-pattern input to a ElementStressDistribution value.

    Accepts canonical values and legacy aliases, and suggests close matches for
    misspellings to keep the API user-friendly.
    """
    if isinstance(value, ElementStressDistribution):
        return value
    if isinstance(value, StressPattern):
        value = value.value

    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    normalized = "-".join(part for part in normalized.split("-") if part)

    aliases: dict[str, ElementStressDistribution] = {
        "compression": ElementStressDistribution.COMPRESSION,
        "comprression": ElementStressDistribution.COMPRESSION,
        "bending": ElementStressDistribution.BENDING,
        "major-axis-bending": ElementStressDistribution.BENDING,
        "bending-major-axis": ElementStressDistribution.BENDING,
        "minor-axis-bending": ElementStressDistribution.BENDING,
        "bending-minor-axis": ElementStressDistribution.BENDING,
        "combined": ElementStressDistribution.COMBINED,
        "combined-bending": ElementStressDistribution.COMBINED,
        "combined-bending-and-compression": ElementStressDistribution.COMBINED,
    }

    pattern = aliases.get(normalized)
    if pattern is not None:
        return pattern

    suggestion = difflib.get_close_matches(normalized, list(aliases), n=1, cutoff=0.72)
    suggestion_text = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    raise ValueError(
        "Unsupported stress_pattern. Use a StressPattern or ElementStressDistribution value or one of: "
        "'compression', 'bending-major-axis', 'bending-minor-axis', 'bending', or 'combined'."
        f"{suggestion_text}"
    )

# --- I-sections/H-sections ---
def i_section_elements(d_mm: float, tw_mm: float, b_mm: float, tf_mm: float, r_mm: float = 0.0) -> list[ElementInput]:
    """Build classification elements for doubly-symmetric hot-rolled I/H sections.

    Table 5.2 Sheet 1/3: web c = d, the depth between the root radii. Sheet 2/3, rolled sections: flange c = (b - tw - 2r)/2,
    from the toe of the root radius to the tip, as the tabulated cf/tf. With r_mm = 0, c = (b - tw)/2, which is conservative.
    """
    return [
        ElementInput(name="web", kind="internal", c_mm=d_mm, t_mm=tw_mm), # Table 5.2 Sheet 1/3
        ElementInput(
            name="flange",
            kind="outstand",
            c_mm=(b_mm - tw_mm - 2.0 * r_mm) / 2.0,
            t_mm=tf_mm,
        ), # Table 5.2 Sheet 2/3
    ]

# --- Channel sections ---
def channel_section_elements(d_mm: float, tw_mm: float, b_mm: float, tf_mm: float, r_mm: float = 0.0) -> list[ElementInput]:
    """Build classification elements for channel sections.

    Table 5.2 Sheet 1/3: web c = d. Sheet 2/3, rolled sections: flange c = b - tw - r, one root radius, as the tabulated
    cf/tf of parallel flange channels. Tapered flange channels (UPN) keep r_mm = 0, i.e c = b - tw with the mean flange
    thickness; Table 5.2 has no rule for tapered flanges, and the producer's tabulated UPN cf/tf follows no single one.
    """
    return [
        ElementInput(name="web", kind="internal", c_mm=d_mm, t_mm=tw_mm),
        ElementInput(name="flange", kind="outstand", c_mm=b_mm - tw_mm - r_mm, t_mm=tf_mm), # Table 5.2 Sheet 2/3
    ]

# --- Angle sections ---
# Does not apply to angles in continuous contact with other components
def angle_section_elements(leg_1_mm: float, leg_2_mm: float, t_mm: float) -> list[ElementInput]:
    """Build classification elements for angle sections."""
    longer_leg_mm = max(leg_1_mm, leg_2_mm)
    shorter_leg_mm = min(leg_1_mm, leg_2_mm)
    return [
        ElementInput(
            name="angle",
            kind="angle",
            c_mm=longer_leg_mm,
            h_mm=longer_leg_mm,
            b_mm=shorter_leg_mm,
            t_mm=t_mm,
        ), # Table 5.2 Sheet 3/3
    ] # TODO: add iff for angles with equal legs, with some tolerance

# --- RHS and SHS sections ---
def rectangular_hollow_section_elements(cw_t: float, cf_t: float, t_mm: float) -> list[ElementInput]:
    """Build classification elements for rectangular hollow sections from stored c/t ratios.

    web_wall: the two h walls, cw = h - 3t; flange_wall: the two b walls, cf = b - 3t (Table 5.2 Sheet 1/3, as tabulated).
    Under bending, one pair of walls is in bending and the other in compression; see _hollow_axis_bending_element().
    """

    return [
        ElementInput(name="web_wall", kind="internal", c_mm=cw_t * t_mm, t_mm=t_mm), # h walls
        ElementInput(
            name="flange_wall",
            kind="internal",
            c_mm=cf_t * t_mm,
            t_mm=t_mm,
        ), # b walls
    ]


def square_hollow_section_elements(c_t: float, t_mm: float) -> list[ElementInput]:
    """Build classification elements for square hollow sections from the stored c/t ratio."""

    return [
        ElementInput(name="web_wall", kind="internal", c_mm=c_t * t_mm, t_mm=t_mm),
        ElementInput(name="flange_wall", kind="internal", c_mm=c_t * t_mm, t_mm=t_mm),
    ]


# --- Epsilon ---
def _epsilon(fy_mpa: float) -> float:
    if fy_mpa <= 0.0:
        raise ValueError("fy_mpa must be positive.")
    return math.sqrt(235.0 / fy_mpa)


def _epsilon_squared(fy_mpa: float) -> float:
    if fy_mpa <= 0.0:
        raise ValueError("fy_mpa must be positive.")
    return 235.0 / fy_mpa

# --- Classification limits ---
# --- Compression ---
def _compression_limits(
    kind: ElementKind, epsilon: float, epsilon_squared: Optional[float] = None
) -> ClassificationLimits:
    match kind:
        case "internal":
            return ClassificationLimits(class_1_limit=33.0 * epsilon, class_2_limit=38.0 * epsilon, class_3_limit=42.0 * epsilon)
        case "outstand":
            return ClassificationLimits(class_1_limit=9.0 * epsilon, class_2_limit=10.0 * epsilon, class_3_limit=14.0 * epsilon)
        case "angle":
            return ClassificationLimits(class_3_limit=15.0 * epsilon, secondary_class_3_limit=11.5 * epsilon)
        case "tubular":
            if epsilon_squared is None:
                raise ValueError("epsilon_squared is required for tubular compression limits.")
            return ClassificationLimits(class_1_limit=50.0 * epsilon_squared, class_2_limit=70.0 * epsilon_squared, class_3_limit=90.0 * epsilon_squared)
            
# --- Bending ---
def _bending_limits(kind: ElementKind, epsilon: float, epsilon_squared: Optional[float]) -> ClassificationLimits:
    match kind:
        case "internal":
            return ClassificationLimits(class_1_limit=72.0 * epsilon, class_2_limit=83.0 * epsilon, class_3_limit=124.0 * epsilon)
        case "outstand":
            return ClassificationLimits(class_1_limit=9.0 * epsilon, class_2_limit=10.0 * epsilon, class_3_limit=14.0 * epsilon)
        case "tubular":
            if epsilon_squared is None:
                raise ValueError("epsilon_squared is required for tubular bending limits.")
            return ClassificationLimits(class_1_limit=50.0 * epsilon_squared, class_2_limit=70.0 * epsilon_squared, class_3_limit=90.0 * epsilon_squared)

# --- Combined bending and compression ---
def _combined_limits(alpha: float, psi: Optional[float], epsilon: float) -> ClassificationLimits:
    if alpha <= 0.0 or alpha > 1.0:
        raise ValueError("alpha must be greater than 0.0 and at most 1.0.")

    if psi is None:
        class_3_limit = None
    elif psi > -1.0:
        class_3_limit = 42.0 * epsilon / (0.67 + 0.33 * psi)
    else:
        class_3_limit = 62.0 * epsilon * (1.0 - psi) * math.sqrt(-psi)

    if alpha > 0.5:
        return ClassificationLimits(
            class_1_limit=396.0 * epsilon / (13.0 * alpha - 1.0),
            class_2_limit=456.0 * epsilon / (13.0 * alpha - 1.0),
            class_3_limit=class_3_limit,
        )

    return ClassificationLimits(
        class_1_limit=36.0 * epsilon / alpha,
        class_2_limit=41.5 * epsilon / alpha,
        class_3_limit=class_3_limit,
    )


# --- Combined bending and compression: outstands (Table 5.2 Sheet 2/3) ---
def outstand_buckling_factor(psi: float, tip: OutstandTip) -> float:
    """Buckling factor k_sigma of an outstand compression element, EN 1993-1-5 Table 4.2 (for EN 1993-1-1 Table 5.2).

    psi = sigma_2/sigma_1, the ratio of end stresses with sigma_1 the maximum compressive stress.
    - tip="compression": maximum compression at the free edge; k = 0.57 - 0.21psi + 0.07psi^2 for 1 >= psi >= -3
    - tip="tension": maximum compression at the supported edge; k = 0.578/(psi + 0.34) for 1 >= psi >= 0,
      k = 1.70 - 5psi + 17.1psi^2 for 0 >= psi >= -1 (0.43 at psi = 1, 1.70 at 0, 23.8 at -1)
    """
    if tip == "compression":
        if not -3.0 <= psi <= 1.0:
            raise ValueError("EN 1993-1-5 Table 4.2 covers 1 >= psi >= -3 for outstands with the tip in compression.")
        return 0.57 - 0.21 * psi + 0.07 * psi**2
    if not -1.0 <= psi <= 1.0:
        raise ValueError("EN 1993-1-5 Table 4.2 covers 1 >= psi >= -1 for outstands with the supported edge most compressed.")
    return 0.578 / (psi + 0.34) if psi >= 0.0 else 1.70 - 5.0 * psi + 17.1 * psi**2


def _combined_outstand_limits(alpha: float, psi: Optional[float], tip: OutstandTip, epsilon: float) -> ClassificationLimits:
    """Table 5.2 Sheet 2/3, outstand flanges in bending and compression.

    Tip in compression: c/t <= 9eps/alpha (Class 1), 10eps/alpha (Class 2)
    Tip in tension:     c/t <= 9eps/(alpha*sqrt(alpha)) (Class 1), 10eps/(alpha*sqrt(alpha)) (Class 2)
    Class 3:            c/t <= 21eps*sqrt(k_sigma); k_sigma per EN 1993-1-5 (needs psi, else 14eps is used)
    """
    if alpha <= 0.0 or alpha > 1.0:
        raise ValueError("alpha must be greater than 0.0 and at most 1.0.")
    divisor = alpha if tip == "compression" else alpha * math.sqrt(alpha)
    class_3 = 21.0 * epsilon * math.sqrt(outstand_buckling_factor(psi, tip)) if psi is not None else 14.0 * epsilon
    return ClassificationLimits(class_1_limit=9.0 * epsilon / divisor, class_2_limit=10.0 * epsilon / divisor, class_3_limit=class_3)


def _class_rank(value: SectionClass) -> int:
    rank: dict[SectionClass, int] = {
        SectionClass.CLASS_1: 1,
        SectionClass.CLASS_2: 2,
        SectionClass.CLASS_3: 3,
        SectionClass.CLASS_4: 4,
    }
    return rank[value]


def _class_from_limits(c_over_t: float, lim1: float, lim2: float, lim3: float) -> SectionClass:
    if c_over_t <= lim1:
        return SectionClass.CLASS_1
    if c_over_t <= lim2:
        return SectionClass.CLASS_2
    if c_over_t <= lim3:
        return SectionClass.CLASS_3
    return SectionClass.CLASS_4

# --- 🌟 Classify the section's element ---
def classify_element(element: ElementInput, fy_mpa: float) -> ElementClassification:
    """Classify one element using the stress case stored on the element."""

    if element.c_mm <= 0.0 or element.t_mm <= 0.0:
        raise ValueError("c_mm and t_mm must both be positive.")

    eps, eps_2 = _epsilon(fy_mpa), _epsilon_squared(fy_mpa)
    reported_c_mm = element.c_mm
    if element.kind == "tubular":
        if element.dia_mm is None:
            raise ValueError("Tubular elements require dia_mm.")
        reported_c_mm = element.dia_mm

    c_over_t = reported_c_mm / element.t_mm
    lim1: Optional[float]
    lim2: Optional[float]
    lim3: Optional[float]
    metadata: dict[str, float | str] = {
        "table": "EN 1993-1-1 Table 5.2",
        "stress_case": element.stress.value,
    }
    if element.kind == "tubular" and element.dia_mm is not None:
        metadata["diameter_mm"] = element.dia_mm
    if element.alpha is not None:
        metadata["alpha"] = element.alpha
    if element.psi is not None:
        metadata["psi"] = element.psi

    # --- Compression ---
    if element.stress == ElementStressDistribution.COMPRESSION:
        limits = _compression_limits(element.kind, eps, eps_2)
        # --- Special case/limits for angles since the classification depends on two ratios ...
        if element.kind == "angle":
            if element.h_mm is None or element.b_mm is None:
                raise ValueError("Angle elements require h_mm and b_mm.")

            h_over_t = element.h_mm / element.t_mm
            b_plus_h_over_2t = (element.b_mm + element.h_mm) / (2.0 * element.t_mm)
            h_limit = limits.class_3_limit
            b_plus_h_limit = limits.secondary_class_3_limit
            if h_limit is None or b_plus_h_limit is None:
                raise ValueError("Angle compression limits are incomplete.")

            h_utilization = h_over_t / h_limit
            b_plus_h_utilization = b_plus_h_over_2t / b_plus_h_limit
            
            if h_utilization >= b_plus_h_utilization:
                reported_c_mm = element.h_mm
                c_over_t = h_over_t
                lim3 = h_limit
                governing_check = "h_over_t"
            else:
                reported_c_mm = (element.b_mm + element.h_mm) / 2.0
                c_over_t = b_plus_h_over_2t
                lim3 = b_plus_h_limit
                governing_check = "b_plus_h_over_2t"

            lim1 = None
            lim2 = None
            section_class = (
                SectionClass.CLASS_3
                if h_over_t <= h_limit and b_plus_h_over_2t <= b_plus_h_limit
                else SectionClass.CLASS_4
            )
            metadata["table_case"] = "angle"
            metadata["h_over_t"] = h_over_t
            metadata["h_over_t_limit"] = h_limit
            metadata["b_plus_h_over_2t"] = b_plus_h_over_2t
            metadata["b_plus_h_over_2t_limit"] = b_plus_h_limit
            metadata["governing_check"] = governing_check
        
        # -- everything else...
        else:
            lim1 = limits.class_1_limit
            lim2 = limits.class_2_limit
            lim3 = limits.class_3_limit
            if lim1 is None or lim2 is None or lim3 is None:
                raise ValueError(f"Compression limits are incomplete for kind '{element.kind}'.")

            # --- 🌟 Business Logic    
            section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
            metadata["table_case"] = "compression"

    # --- Bending ---
    elif element.stress == ElementStressDistribution.BENDING:
        if element.kind not in {"internal", "outstand", "tubular"}:
            raise NotImplementedError(
                f"Bending classification is not implemented for kind '{element.kind}'."
            )
        bending_limits = _bending_limits(element.kind, eps, eps_2)
        lim1 = bending_limits.class_1_limit
        lim2 = bending_limits.class_2_limit
        lim3 = bending_limits.class_3_limit
        if lim1 is None or lim2 is None or lim3 is None:
            raise ValueError(f"Bending limits are incomplete for kind '{element.kind}'.")
        section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
        metadata["table_case"] = "bending"
    elif (
        element.stress == ElementStressDistribution.COMBINED
        and element.kind == "internal"
    ):
        if element.alpha is None:
            raise ValueError("Internal elements in combined stress require alpha.")

        combined_limits = _combined_limits(element.alpha, element.psi, eps)
        lim1 = combined_limits.class_1_limit
        lim2 = combined_limits.class_2_limit
        if lim1 is None or lim2 is None:
            raise ValueError("Combined stress limits are incomplete for internal elements.")
        metadata["table_case"] = "combined_bending_and_compression"

        if c_over_t <= lim1:
            section_class = SectionClass.CLASS_1
            lim3 = None
        elif c_over_t <= lim2:
            section_class = SectionClass.CLASS_2
            lim3 = None
        else:
            if combined_limits.class_3_limit is None:
                raise ValueError(
                    "Internal elements in combined stress require psi when the "
                    "Class 3 limit is needed."
                )
            lim3 = combined_limits.class_3_limit
            section_class = (
                SectionClass.CLASS_3 if c_over_t <= lim3 else SectionClass.CLASS_4
            )
    elif (
        element.stress == ElementStressDistribution.COMBINED
        and element.kind == "outstand"
    ):
        if element.alpha is None:
            # Without alpha, the uniform-compression limits (alpha = 1, tip in compression) are used; conservative
            limits = _compression_limits(element.kind, eps, eps_2)
            metadata["table_case"] = "rolled_outstand"
            metadata["note"] = "alpha not given; compression limits used"
        else:
            tip: OutstandTip = element.tip or "compression"
            limits = _combined_outstand_limits(element.alpha, element.psi, tip, eps)
            metadata["table_case"] = f"outstand_bending_and_compression_tip_in_{tip}"
            if element.psi is not None:
                metadata["k_sigma"] = outstand_buckling_factor(element.psi, tip)
        lim1 = limits.class_1_limit
        lim2 = limits.class_2_limit
        lim3 = limits.class_3_limit
        if lim1 is None or lim2 is None or lim3 is None:
            raise ValueError("Outstand compression limits are incomplete.")
        section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
    else:
        raise NotImplementedError(
            f"Combined classification is not implemented for kind '{element.kind}'."
        )

    # --- 5.5.2(9): Class 4 parts may be treated as Class 3 with epsilon increased by sqrt((fy/gamma_M0)/sigma_com_Ed)
    if section_class == SectionClass.CLASS_4 and element.sigma_com_ed_mpa is not None:
        factor = math.sqrt(fy_mpa / GAMMA_M0 / element.sigma_com_ed_mpa)
        scale = factor**2 if element.kind == "tubular" else factor # tubular limits are in epsilon squared
        if element.kind == "angle":
            relaxed = (
                float(metadata["h_over_t"]) <= float(metadata["h_over_t_limit"]) * scale
                and float(metadata["b_plus_h_over_2t"]) <= float(metadata["b_plus_h_over_2t_limit"]) * scale
            )
        else:
            relaxed = lim3 is not None and c_over_t <= lim3 * scale
        metadata["sigma_com_ed_mpa"] = element.sigma_com_ed_mpa
        metadata["epsilon_factor_5_5_2_9"] = factor
        if relaxed:
            section_class = SectionClass.CLASS_3
            metadata["clause"] = "5.5.2(9)"
            metadata["note"] = "Class 4 treated as Class 3 per 5.5.2(9); not for member buckling checks (5.5.2(10))"

    return ElementClassification(
        name=element.name,
        kind=element.kind,
        stress=element.stress,
        c_mm=reported_c_mm,
        t_mm=element.t_mm,
        c_over_t=c_over_t,
        class_1_limit=lim1,
        class_2_limit=lim2,
        class_3_limit=lim3,
        section_class=section_class,
        metadata=metadata,
    )


def classify_internal_part(
    c_mm: float,
    t_mm: float,
    fy_mpa: float,
    name: str = "internal",
    stress: ElementStressDistribution = ElementStressDistribution.COMPRESSION,
    alpha: Optional[float] = None,
    psi: Optional[float] = None,
) -> ElementClassification:
    """Classify one internal plate element."""

    return classify_element(
        ElementInput(
            name=name,
            kind="internal",
            c_mm=c_mm,
            t_mm=t_mm,
            stress=stress,
            alpha=alpha,
            psi=psi,
        ),
        fy_mpa=fy_mpa,
    )


def classify_outstand_flange(
    c_mm: float,
    t_mm: float,
    fy_mpa: float,
    name: str = "outstand",
    stress: ElementStressDistribution = ElementStressDistribution.COMPRESSION,
) -> ElementClassification:
    """Classify one outstand plate element."""

    return classify_element(ElementInput(name=name, kind="outstand", c_mm=c_mm, t_mm=t_mm, stress=stress), fy_mpa=fy_mpa)


def classify_elements(elements: Sequence[ElementInput], fy_mpa: float) -> ClassificationResult:
    """Classify all provided elements and return the governing class."""

    if not elements:
        raise ValueError("At least one element must be provided.")

    eps = _epsilon(fy_mpa)
    results = [classify_element(element, fy_mpa) for element in elements]

    governing_rank = max(_class_rank(result.section_class) for result in results)
    governing_class = next(section_class for section_class in SectionClass if section_class.name == f"CLASS_{governing_rank}")
    governing_elements = [result.name for result in results if _class_rank(result.section_class) == governing_rank]

    notes: list[str] = []
    flanges = [result for result in results if "flange" in result.name]
    if (
        governing_class == SectionClass.CLASS_3
        and flanges
        and all("web" in name for name in governing_elements)
        and all(_class_rank(result.section_class) <= 2 for result in flanges)
    ):
        notes.append("5.5.2(11): Class 3 web with Class 1 or 2 flanges; may be classified as Class 2 with an effective web per 6.2.2.4.")
    if any(result.metadata.get("clause") == "5.5.2(9)" for result in results):
        notes.append("5.5.2(9) applied: not valid for member buckling resistance checks to 6.3 (5.5.2(10)).")

    return ClassificationResult(
        epsilon=eps,
        fy_mpa=fy_mpa,
        elements=results,
        section_class=governing_class,
        governing_elements=governing_elements,
        notes=notes,
    )


def classify_circular_hollow(
    d_t: float,
    fy_mpa: float,
    *,
    class4_reference: str = "EN 1993-1-6",
) -> ClassificationResult:
    """Classify a circular hollow section per EN 1993-1-1 Table 5.2 Sheet 3.

    The CHS rule is load-independent and uses epsilon squared = 235 / fy.
    """

    if d_t <= 0.0:
        raise ValueError("d_t must be positive.")

    eps2 = _epsilon_squared(fy_mpa)
    lim1 = 50.0 * eps2
    lim2 = 70.0 * eps2
    lim3 = 90.0 * eps2

    if d_t <= lim1:
        section_class = SectionClass.CLASS_1
    elif d_t <= lim2:
        section_class = SectionClass.CLASS_2
    elif d_t <= lim3:
        section_class = SectionClass.CLASS_3
    else:
        raise SectionClass4Error(
            f"CHS d/t={d_t:.1f} exceeds 90e^2={lim3:.2f}. "
            f"Class 4 CHS - refer to {class4_reference} for effective section properties."
        )

    element = ElementClassification(
        name="wall",
        kind="internal",
        stress=ElementStressDistribution.COMPRESSION,
        c_mm=d_t,
        t_mm=1.0,
        c_over_t=d_t,
        class_1_limit=lim1,
        class_2_limit=lim2,
        class_3_limit=lim3,
        section_class=section_class,
        metadata={
            "table": "EN 1993-1-1 Table 5.2",
            "table_sheet": "sheet_3",
            "table_case": "circular_hollow_section",
            "stress_case": "bending_and_or_compression",
            "epsilon_squared": eps2,
        },
    )
    return ClassificationResult(
        epsilon=math.sqrt(eps2),
        fy_mpa=fy_mpa,
        elements=[element],
        section_class=section_class,
        governing_elements=["wall"],
    )


def _get_section_elements(section: BaseSection) -> list[ElementInput]:
    extractor = getattr(section, "classification_elements", None)
    if not callable(extractor):
        raise NotImplementedError(
            f"Section type '{section.get_section_type().value}' must implement "
            "classification_elements() in its section module."
        )

    typed_extractor = cast(Callable[[], Sequence[ElementInput]], extractor)
    return list(typed_extractor())


def _hollow_axis_bending_element(
    stress_pattern: StressPattern | ElementStressDistribution | str,
) -> str | None:
    """Map a bending stress pattern to the hollow-section walls that use the bending limits.

    Table 5.2 Sheet 1/3: in bending about either axis, one pair of walls are webs, "part subject to bending", and the other
    pair are flanges, "part subject to compression". Major-axis bending puts the h walls (web_wall) in bending and the b
    walls in compression; minor-axis bending the reverse. An axis-free "bending" is taken as major-axis bending, as for
    I-sections; bending limits on all four walls would be unconservative for the flanges.
    This stays private and hollow-only so the geometry builders remain purely geometric.
    """
    if isinstance(stress_pattern, (StressPattern, ElementStressDistribution)):
        stress_pattern = stress_pattern.value

    normalized = stress_pattern.strip().lower().replace("_", "-").replace(" ", "-")
    normalized = "-".join(part for part in normalized.split("-") if part)
    if normalized in {"bending", "major-axis-bending", "bending-major-axis"}:
        return "web_wall"
    if normalized in {"minor-axis-bending", "bending-minor-axis"}:
        return "flange_wall"
    return None


def _angle_leg_outstands(element: ElementInput) -> list[ElementInput]:
    """Table 5.2 Sheet 3/3, angles in bending: "Refer also to outstand flanges (see sheet 2 of 3)".

    Each leg is an outstand, taken over its full width with the whole leg in compression (alpha = 1, tip in compression),
    i.e c/t against 9ε, 10ε and 14ε; this covers either sense of bending about either axis and is conservative, since the
    leg in a stress gradient has alpha < 1 and a higher k_sigma.
    """
    legs: tuple[tuple[str, Optional[float]], ...] = (("leg_h", element.h_mm), ("leg_b", element.b_mm))
    return [
        ElementInput(name=name, kind="outstand", stress=ElementStressDistribution.BENDING, c_mm=leg_mm, t_mm=element.t_mm)
        for name, leg_mm in legs
        if leg_mm
    ]


def _apply_stress_pattern(
    elements: Sequence[ElementInput],
    section_type: SectionType,
    stress_pattern: ElementStressDistribution,
    hollow_bending_element: str | None = None,
) -> list[ElementInput]:
    if stress_pattern == ElementStressDistribution.COMPRESSION:
        return list(elements)

    if stress_pattern == ElementStressDistribution.BENDING:
        if (
            hollow_bending_element is not None
            and section_type in HOLLOW_INTERNAL_SECTION_TYPES
        ):
            return [
                element.model_copy(
                    update={
                        "stress": (
                            ElementStressDistribution.BENDING
                            if element.name == hollow_bending_element
                            else ElementStressDistribution.COMPRESSION
                        ),
                        "alpha": None,
                        "psi": None,
                    }
                )
                for element in elements
            ]

        bent: list[ElementInput] = []
        for element in elements:
            if element.kind == "angle":
                bent.extend(_angle_leg_outstands(element)) # Sheet 3/3 -> Sheet 2/3
            else:
                bent.append(element.model_copy(update={"stress": ElementStressDistribution.BENDING, "alpha": None, "psi": None}))
        return bent

    if stress_pattern == ElementStressDistribution.COMBINED:
        raise NotImplementedError(
            "Stress pattern 'combined' needs element-specific alpha and psi values. "
            "Use custom_elements for explicit control."
        )

    raise NotImplementedError(f"Unsupported stress pattern '{stress_pattern.value}'.")


def _class4_reference_for_section_type(section_type: SectionType) -> str | None:
    if (
        section_type in RECTANGULAR_HOLLOW_SECTION_TYPES
        or section_type in SQUARE_HOLLOW_SECTION_TYPES
    ):
        if section_type in (SectionType.CFRHS, SectionType.CFSHS):
            return "EN 1993-1-3"
        return "EN 1993-1-5"
    if section_type == SectionType.CFCHS:
        return "EN 1993-1-3"
    if section_type == SectionType.HFCHS:
        return "EN 1993-1-6"
    return None


def _raise_for_hollow_class4(
    section_type: SectionType, result: ClassificationResult
) -> None:
    if result.section_class != SectionClass.CLASS_4:
        return

    reference = _class4_reference_for_section_type(section_type)
    if reference is None:
        return

    raise SectionClass4Error(
        f"Class 4 {section_type.value} - effective section properties per {reference}, not implemented."
    )


def _float_value(data: dict[str, float | str | bool], key: str) -> float:
    value = data.get(key)
    if value is None:
        raise ValueError(f"Missing required key '{key}'.")
    return float(value)


def _optional_float_value(
    data: dict[str, float | str | bool], key: str
) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    return float(value)


def _rectangular_hollow_elements_from_dict(
    data: dict[str, float | str | bool],
) -> list[ElementInput]:
    t = _float_value(data, "t")
    cw_t = _optional_float_value(data, "cw_t")
    cf_t = _optional_float_value(data, "cf_t")
    if cw_t is None:
        h = _optional_float_value(data, "h")
        if h is None:
            raise ValueError("Missing required key 'cw_t'.")
        cw_t = (h - 3.0 * t) / t
    if cf_t is None:
        b = _optional_float_value(data, "b")
        if b is None:
            raise ValueError("Missing required key 'cf_t'.")
        cf_t = (b - 3.0 * t) / t
    return rectangular_hollow_section_elements(cw_t=cw_t, cf_t=cf_t, t_mm=t)


def _square_hollow_elements_from_dict(
    data: dict[str, float | str | bool],
) -> list[ElementInput]:
    t = _float_value(data, "t")
    c_t = _optional_float_value(data, "c_t")
    if c_t is None:
        h = _optional_float_value(data, "h")
        if h is None:
            b = _optional_float_value(data, "b")
            if b is None:
                raise ValueError("Missing required key 'c_t'.")
            h = b
        c_t = (h - 3.0 * t) / t
    return square_hollow_section_elements(c_t=c_t, t_mm=t)


def _d_t_from_dict(data: dict[str, float | str | bool]) -> float:
    d_t = _optional_float_value(data, "d_t")
    if d_t is not None:
        return d_t
    d = _optional_float_value(data, "d")
    t = _optional_float_value(data, "t")
    if d is None or t is None:
        raise ValueError("Missing required key 'd_t'.")
    return d / t


def classify_section(
    section: Optional[BaseSection] = None,
    fy_mpa: float = 355.0,
    custom_elements: Optional[Iterable[ElementInput]] = None,
    stress_pattern: StressPattern | ElementStressDistribution | str = ElementStressDistribution.COMPRESSION,
) -> ClassificationResult:
    """Classify a section using section-derived or explicit element data.
    Default stress_pattern is COMPRESSION, which applies compression limits to all elements.

    `stress_pattern` is a lean convenience preset aligned with EN 1993-1-1
    Table 5.2 wording ("part subject to compression", "part subject to
    bending", or "part subject to combined bending and compression").
    It may be passed as a string such as "compression", "bending-major-axis",
    "bending-minor-axis" or "combined", as a StressPattern preset, or as an
    ElementStressDistribution enum value. For hollow sections the axis selects
    which walls are in bending. For combined bending and compression, pass explicit
    `custom_elements` with `stress`, `alpha`, `psi` (and `tip` for outstands) as needed.
    """

    if custom_elements is not None:
        return classify_elements(list(custom_elements), fy_mpa)

    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    pattern = _normalize_stress_pattern(stress_pattern)
    section_type = section.get_section_type()
    hollow_bending_element = _hollow_axis_bending_element(stress_pattern)

    if (
        section_type in ROUND_HOLLOW_SECTION_TYPES
        or section_type in ELLIPTICAL_HOLLOW_SECTION_TYPES
    ):
        classifier = getattr(section, "classify", None)
        if callable(classifier):
            typed_classifier = cast(Callable[[float], ClassificationResult], classifier)
            return typed_classifier(fy_mpa)

    elements = _apply_stress_pattern(
        _get_section_elements(section),
        section.get_section_type(),
        pattern,
        hollow_bending_element=hollow_bending_element,
    )
    if not elements:
        raise ValueError(
            f"No valid classification elements could be extracted from section '{section}'. "
            "Use custom_elements for explicit control."
        )

    result = classify_elements(elements, fy_mpa)
    _raise_for_hollow_class4(section_type, result)
    return result


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, float | str | bool],
    fy_mpa: float = 355.0,
    stress_pattern: StressPattern | ElementStressDistribution | str = ElementStressDistribution.COMPRESSION,
) -> ClassificationResult:
    """Classify a custom section represented as a plain dictionary.

    `stress_pattern` accepts the same compression/bending string or enum values as
    `classify_section()`.
    """
    if "stress_case" in data:
        raw_pattern: StressPattern | ElementStressDistribution | str = str(data["stress_case"])
    else:
        raw_pattern = stress_pattern
    pattern = _normalize_stress_pattern(raw_pattern)
    hollow_bending_element = _hollow_axis_bending_element(raw_pattern)

    if section_type in ROLLED_I_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        r = float(data.get("r", 0.0) or 0.0) # root radius; flange c = (b - tw - 2r)/2
        elements = i_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf, r_mm=r)
        return classify_elements(
            _apply_stress_pattern(
                elements,
                section_type,
                pattern,
                hollow_bending_element=hollow_bending_element,
            ),
            fy_mpa,
        )

    if section_type in CHANNEL_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        r = 0.0 if section_type == SectionType.UPN else float(data.get("r", 0.0) or 0.0) # flange c = b - tw - r; UPN tapered
        elements = channel_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf, r_mm=r)
        return classify_elements(
            _apply_stress_pattern(
                elements,
                section_type,
                pattern,
                hollow_bending_element=hollow_bending_element,
            ),
            fy_mpa,
        )

    if section_type in ANGLE_SECTION_TYPES:
        t = float(data.get("t", 0.0) or 0.0)
        h = float(data.get("h", 0.0) or 0.0)
        b = float(data.get("b", h) or 0.0)
        return classify_elements(
            _apply_stress_pattern(angle_section_elements(leg_1_mm=h, leg_2_mm=b, t_mm=t), section_type, pattern), fy_mpa
        )

    if section_type in RECTANGULAR_HOLLOW_SECTION_TYPES:
        elements = _rectangular_hollow_elements_from_dict(data)
        result = classify_elements(
            _apply_stress_pattern(
                elements,
                section_type,
                pattern,
                hollow_bending_element=hollow_bending_element,
            ),
            fy_mpa,
        )
        _raise_for_hollow_class4(section_type, result)
        return result

    if section_type in SQUARE_HOLLOW_SECTION_TYPES:
        elements = _square_hollow_elements_from_dict(data)
        result = classify_elements(
            _apply_stress_pattern(
                elements,
                section_type,
                pattern,
                hollow_bending_element=hollow_bending_element,
            ),
            fy_mpa,
        )
        _raise_for_hollow_class4(section_type, result)
        return result

    if section_type in ROUND_HOLLOW_SECTION_TYPES:
        d_t = _d_t_from_dict(data)
        return classify_circular_hollow(
            d_t=d_t,
            fy_mpa=fy_mpa,
            class4_reference=_class4_reference_for_section_type(section_type)
            or "EN 1993-1-6",
        )

    if section_type in ELLIPTICAL_HOLLOW_SECTION_TYPES:
        raise NotImplementedError(
            "HFEHS classification is not covered by EN 1993-1-1 Table 5.2. "
            "No EC3 Part 1.1 rule exists for elliptical hollow sections."
        )

    raise NotImplementedError(
        f"No dictionary adapter is registered for section type '{section_type.value}'. "
        "Provide custom_elements explicitly."
    )


if __name__ == "__main__":
    custom = [
        ElementInput(
            name="custom_web",
            kind="internal",
            c_mm=280.0,
            t_mm=8.0,
            stress=ElementStressDistribution.BENDING,
        ),
        ElementInput(name="custom_flange", kind="outstand", c_mm=95.0, t_mm=10.0),
    ]
    print(custom[0].model_dump())
    print(classify_section(custom_elements=custom, fy_mpa=355.0).model_dump())
