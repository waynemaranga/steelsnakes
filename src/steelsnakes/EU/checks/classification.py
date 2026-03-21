from __future__ import annotations

import math
from enum import Enum
from typing import Callable, Iterable, Literal, Optional, Sequence, cast

from pydantic import BaseModel, Field

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import BaseSection, SectionType

ElementKind = Literal["internal", "outstand"] # TODO: expose to Public API: INTERNAL COMPRESSION ELEMENT and OUTSTAND FLANGE


class ElementStressCase(str, Enum):
    """Stress pattern applied to one classification element."""

    COMPRESSION = "compression"
    BENDING = "bending"
    COMBINED = "combined" # TODO: expose to Public API it's COMBINED BENDING AND COMPRESSION


class StressPattern(str, Enum):
    """Convenience patterns that assign stress cases to section elements."""

    COMPRESSION = "compression"
    MAJOR_AXIS_BENDING = "major_axis_bending"
    MINOR_AXIS_BENDING = "minor_axis_bending"
    COMBINED = "combined"


I_SECTION_TYPES = (
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
CHANNEL_SECTION_TYPES = (
    SectionType.PFC,
    SectionType.UPE,
    SectionType.UPN,
)
ANGLE_SECTION_TYPES = (
    SectionType.L_EQUAL,
    SectionType.L_UNEQUAL,
    SectionType.L_EQUAL_B2B,
    SectionType.L_UNEQUAL_B2B,
)


class ElementInput(BaseModel):
    """One plate element to classify according to EN 1993-1-1 Table 5.2."""

    name: str
    kind: ElementKind
    c_mm: float
    t_mm: float
    stress: ElementStressCase = ElementStressCase.COMPRESSION
    alpha: Optional[float] = None
    psi: Optional[float] = None


class ElementClassification(BaseModel):
    """Classification result for one plate element."""

    name: str
    kind: ElementKind
    stress: ElementStressCase
    c_mm: float
    t_mm: float
    c_over_t: float
    class_1_limit: Optional[float]
    class_2_limit: Optional[float]
    class_3_limit: Optional[float]
    section_class: SectionClass
    metadata: dict[str, float | str] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Aggregate section classification from one or more element classifications."""

    epsilon: float
    fy_mpa: float
    elements: list[ElementClassification]
    section_class: SectionClass
    governing_elements: list[str]


SectionElementAdapter = Callable[[BaseSection], Sequence[ElementInput]]
_SECTION_ADAPTERS: dict[SectionType, SectionElementAdapter] = {}


def _normalize_stress_pattern(value: StressPattern | str) -> StressPattern:
    """Normalize a stress_pattern input to a StressPattern enum value, accepting common string aliases.
    Explanation: This allows users to pass stress patterns as either enum values or more user-friendly strings, while ensuring that the internal logic always works with a consistent StressPattern type.
    """
    if isinstance(value, StressPattern):
        return value

    text = value.strip().lower()
    aliases = {
        "compression": StressPattern.COMPRESSION,
        "comprression": StressPattern.COMPRESSION,
        "bending-major-axis": StressPattern.MAJOR_AXIS_BENDING,
        "major-axis-bending": StressPattern.MAJOR_AXIS_BENDING,
        "major_axis_bending": StressPattern.MAJOR_AXIS_BENDING,
        "bending-minor-axis": StressPattern.MINOR_AXIS_BENDING,
        "minor-axis-bending": StressPattern.MINOR_AXIS_BENDING,
        "minor_axis_bending": StressPattern.MINOR_AXIS_BENDING,
        "combined": StressPattern.COMBINED,
        "combined-bending": StressPattern.COMBINED,
        "combined-bending-and-compression": StressPattern.COMBINED,
    } # FIXME: there must be a better way to handle this, maybe with regex or a more robust parsing system, but this is a start for common cases and typos.
    pattern = aliases.get(text)
    if pattern is None:
        raise ValueError(
            "Unsupported stress_pattern. Use a StressPattern value or one of: "
            "'compression', 'bending-major-axis', 'bending-minor-axis', 'combined'."
        )
    return pattern


def _build_elements(parts: Sequence[tuple[str, ElementKind, float, float]]) -> list[ElementInput]:
    elements: list[ElementInput] = []
    for name, kind, c_mm, t_mm in parts:
        if c_mm > 0.0 and t_mm > 0.0:
            elements.append(ElementInput(name=name, kind=kind, c_mm=c_mm, t_mm=t_mm))
    return elements


def i_section_elements(d_mm: float, tw_mm: float, b_mm: float, tf_mm: float) -> list[ElementInput]:
    """Build classification elements for doubly-symmetric hot-rolled I/H sections."""

    return _build_elements(
        [
            ("web", "internal", d_mm, tw_mm),
            ("flange", "outstand", (b_mm - tw_mm) / 2.0, tf_mm),
        ]
    )


def channel_section_elements(d_mm: float, tw_mm: float, b_mm: float, tf_mm: float) -> list[ElementInput]:
    """Build classification elements for channel sections."""

    return _build_elements(
        [
            ("web", "internal", d_mm, tw_mm),
            ("flange", "outstand", b_mm - tw_mm, tf_mm),
        ]
    )


def angle_section_elements(leg_1_mm: float, leg_2_mm: float, t_mm: float) -> list[ElementInput]:
    """Build classification elements for angle sections."""

    return _build_elements(
        [
            ("leg_1", "outstand", leg_1_mm - t_mm, t_mm),
            ("leg_2", "outstand", leg_2_mm - t_mm, t_mm),
        ]
    )


def _epsilon(fy_mpa: float) -> float:
    if fy_mpa <= 0.0:
        raise ValueError("fy_mpa must be positive.")
    return math.sqrt(235.0 / fy_mpa)


def _compression_limits(kind: ElementKind, epsilon: float) -> tuple[float, float, float]:
    if kind == "internal":
        return (33.0 * epsilon, 38.0 * epsilon, 42.0 * epsilon)
    return (9.0 * epsilon, 10.0 * epsilon, 14.0 * epsilon)


def _bending_limits(kind: ElementKind, epsilon: float) -> tuple[float, float, float]:
    if kind == "internal":
        return (72.0 * epsilon, 83.0 * epsilon, 124.0 * epsilon)
    return _compression_limits(kind, epsilon)


def _combined_internal_class12_limits(alpha: float, epsilon: float) -> tuple[float, float]:
    if alpha <= 0.0 or alpha > 1.0:
        raise ValueError("alpha must be greater than 0.0 and at most 1.0.")

    if alpha > 0.5:
        return (
            396.0 * epsilon / (13.0 * alpha - 1.0),
            456.0 * epsilon / (13.0 * alpha - 1.0),
        )

    return (
        36.0 * epsilon / alpha,
        41.5 * epsilon / alpha,
    )


def _combined_internal_class3_limit(psi: float, epsilon: float) -> float:
    if psi > -1.0:
        return 42.0 * epsilon / (0.67 + 0.33 * psi)
    return 62.0 * epsilon * (1.0 - psi) * math.sqrt(-psi)


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


def classify_element(element: ElementInput, fy_mpa: float) -> ElementClassification:
    """Classify one element using the stress case stored on the element."""

    if element.c_mm <= 0.0 or element.t_mm <= 0.0:
        raise ValueError("c_mm and t_mm must both be positive.")

    eps = _epsilon(fy_mpa)
    c_over_t = element.c_mm / element.t_mm
    metadata: dict[str, float | str] = {
        "table": "EN 1993-1-1 Table 5.2",
        "stress_case": element.stress.value,
    }
    if element.alpha is not None:
        metadata["alpha"] = element.alpha
    if element.psi is not None:
        metadata["psi"] = element.psi

    if element.stress == ElementStressCase.COMPRESSION:
        lim1, lim2, lim3 = _compression_limits(element.kind, eps)
        section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
        metadata["table_case"] = "compression"
    elif element.stress == ElementStressCase.BENDING:
        lim1, lim2, lim3 = _bending_limits(element.kind, eps)
        section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
        metadata["table_case"] = "bending"
    elif element.kind == "internal":
        if element.alpha is None:
            raise ValueError("Internal elements in combined stress require alpha.")

        lim1, lim2 = _combined_internal_class12_limits(element.alpha, eps)
        metadata["table_case"] = "combined_bending_and_compression"

        if c_over_t <= lim1:
            section_class = SectionClass.CLASS_1
            lim3 = None
        elif c_over_t <= lim2:
            section_class = SectionClass.CLASS_2
            lim3 = None
        else:
            if element.psi is None:
                raise ValueError(
                    "Internal elements in combined stress require psi when the "
                    "Class 3 limit is needed."
                )
            lim3 = _combined_internal_class3_limit(element.psi, eps)
            section_class = SectionClass.CLASS_3 if c_over_t <= lim3 else SectionClass.CLASS_4
    else:
        lim1, lim2, lim3 = _compression_limits(element.kind, eps)
        section_class = _class_from_limits(c_over_t, lim1, lim2, lim3)
        metadata["table_case"] = "rolled_outstand"

    return ElementClassification(
        name=element.name,
        kind=element.kind,
        stress=element.stress,
        c_mm=element.c_mm,
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
    stress: ElementStressCase = ElementStressCase.COMPRESSION,
    alpha: Optional[float] = None,
    psi: Optional[float] = None,
) -> ElementClassification:
    """Classify one internal plate element."""

    return classify_element(
        ElementInput(name=name, kind="internal", c_mm=c_mm, t_mm=t_mm, stress=stress, alpha=alpha, psi=psi),
        fy_mpa=fy_mpa,
    )


def classify_outstand_flange(
    c_mm: float,
    t_mm: float,
    fy_mpa: float,
    name: str = "outstand",
    stress: ElementStressCase = ElementStressCase.COMPRESSION,
) -> ElementClassification:
    """Classify one outstand plate element."""

    return classify_element(
        ElementInput(name=name, kind="outstand", c_mm=c_mm, t_mm=t_mm, stress=stress),
        fy_mpa=fy_mpa,
    )


def classify_elements(elements: Sequence[ElementInput], fy_mpa: float) -> ClassificationResult:
    """Classify all provided elements and return the governing class."""

    if not elements:
        raise ValueError("At least one element must be provided.")

    eps = _epsilon(fy_mpa)
    results = [classify_element(element, fy_mpa) for element in elements]

    governing_rank = max(_class_rank(result.section_class) for result in results)
    governing_class = next(section_class for section_class in SectionClass if section_class.name == f"CLASS_{governing_rank}")
    governing_elements = [result.name for result in results if _class_rank(result.section_class) == governing_rank]

    return ClassificationResult(
        epsilon=eps,
        fy_mpa=fy_mpa,
        elements=results,
        section_class=governing_class,
        governing_elements=governing_elements,
    )


def register_section_adapter(section_type: SectionType, adapter: SectionElementAdapter) -> None:
    """Register a section-type adapter that extracts classification elements."""

    _SECTION_ADAPTERS[section_type] = adapter


def _get_section_elements(section: BaseSection) -> list[ElementInput]:
    extractor = getattr(section, "classification_elements", None)
    if callable(extractor):
        typed_extractor = cast(Callable[[], Sequence[ElementInput]], extractor)
        return list(typed_extractor())

    adapter = _SECTION_ADAPTERS.get(section.get_section_type())
    if adapter is None:
        raise NotImplementedError(
            f"No adapter found for section type '{section.get_section_type().value}'. "
            "Implement section.classification_elements() in its section module or "
            "register an adapter with register_section_adapter()."
        )
    return list(adapter(section))


def _apply_stress_pattern(
    elements: Sequence[ElementInput],
    section_type: SectionType,
    stress_pattern: StressPattern,
) -> list[ElementInput]:
    if stress_pattern == StressPattern.COMPRESSION:
        return list(elements)

    if stress_pattern == StressPattern.MAJOR_AXIS_BENDING:
        if section_type not in I_SECTION_TYPES and section_type not in CHANNEL_SECTION_TYPES:
            raise NotImplementedError(
                f"Stress pattern '{stress_pattern.value}' is not implemented for section type '{section_type.value}'. "
                "Use custom_elements for explicit control."
            )

        updated: list[ElementInput] = []
        for element in elements:
            if element.name == "web" and element.kind == "internal":
                updated.append(element.model_copy(update={"stress": ElementStressCase.BENDING, "alpha": None, "psi": None}))
            else:
                updated.append(element.model_copy(update={"stress": ElementStressCase.COMPRESSION, "alpha": None, "psi": None}))
        return updated

    if stress_pattern == StressPattern.MINOR_AXIS_BENDING:
        raise NotImplementedError(
            f"Stress pattern '{stress_pattern.value}' is not implemented for section type '{section_type.value}'. "
            "Use custom_elements for explicit control."
        )

    if stress_pattern == StressPattern.COMBINED:
        raise NotImplementedError(
            "Stress pattern 'combined' needs element-specific alpha and psi values. "
            "Use custom_elements for explicit control."
        )

    raise NotImplementedError(f"Unsupported stress pattern '{stress_pattern.value}'.")


def classify_section(
    section: Optional[BaseSection] = None,
    fy_mpa: float = 355.0,
    custom_elements: Optional[Iterable[ElementInput]] = None,
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
) -> ClassificationResult:
    """Classify a section using section-derived or explicit element data.
    Default stress_pattern is COMPRESSION, which applies compression limits to all elements.

    `stress_pattern` is a lean convenience preset for common hot-rolled checks.
    It may be passed as a string such as "compression" or
    "bending-major-axis", or as a StressPattern enum value.
    For combined bending and compression, pass explicit `custom_elements`
    with `stress`, `alpha`, and `psi` values as needed.
    """

    if custom_elements is not None:
        return classify_elements(list(custom_elements), fy_mpa)

    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    pattern = _normalize_stress_pattern(stress_pattern)
    elements = _apply_stress_pattern(_get_section_elements(section), section.get_section_type(), pattern)
    if not elements:
        raise ValueError(
            f"No valid classification elements could be extracted from section '{section}'. "
            "Use custom_elements for explicit control."
        )

    return classify_elements(elements, fy_mpa)


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, float | str | bool],
    fy_mpa: float = 355.0,
    stress_pattern: StressPattern | str = StressPattern.COMPRESSION,
) -> ClassificationResult:
    """Classify a custom section represented as a plain dictionary.

    `stress_pattern` accepts the same string or enum values as
    `classify_section()`.
    """
    pattern = _normalize_stress_pattern(stress_pattern)

    if section_type in I_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        elements = i_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf)
        return classify_elements(_apply_stress_pattern(elements, section_type, pattern), fy_mpa)

    if section_type in CHANNEL_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        elements = channel_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf)
        return classify_elements(_apply_stress_pattern(elements, section_type, pattern), fy_mpa)

    if section_type in ANGLE_SECTION_TYPES:
        if pattern != StressPattern.COMPRESSION:
            raise NotImplementedError(
                f"Stress pattern '{pattern.value}' is not implemented for section type '{section_type.value}'. "
                "Use custom_elements for explicit control."
            )
        t = float(data.get("t", 0.0) or 0.0)
        h = float(data.get("h", 0.0) or 0.0)
        b = float(data.get("b", h) or 0.0)
        return classify_elements(angle_section_elements(leg_1_mm=h, leg_2_mm=b, t_mm=t), fy_mpa)

    raise NotImplementedError(
        f"No dictionary adapter is registered for section type '{section_type.value}'. "
        "Provide custom_elements explicitly."
    )


if __name__ == "__main__":
    custom = [
        ElementInput(name="custom_web", kind="internal", c_mm=280.0, t_mm=8.0, stress=ElementStressCase.BENDING),
        ElementInput(name="custom_flange", kind="outstand", c_mm=95.0, t_mm=10.0),
    ]
    print(custom[0].model_dump())
    print(classify_section(custom_elements=custom, fy_mpa=355.0).model_dump())
