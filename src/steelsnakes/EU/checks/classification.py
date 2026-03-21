from __future__ import annotations
import math
from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Literal, Optional, Sequence, cast
from pydantic import BaseModel, Field
from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import BaseSection, SectionType

ElementKind = Literal["internal", "outstand"] # TODO: expose to public API internal -> INTERNAL COMPRESSION PART, outstand -> OUTSTAND FLANGE
I_SECTION_TYPES: frozenset[SectionType] = frozenset(
    {
        SectionType.IPE,
        SectionType.HE,
        SectionType.HL,
        SectionType.HLZ,
        SectionType.UB,
        SectionType.HD,
        SectionType.HP,
        SectionType.UC,
        SectionType.UBP,
    }
)
CHANNEL_SECTION_TYPES: frozenset[SectionType] = frozenset(
    {
        SectionType.PFC,
        SectionType.UPE,
        SectionType.UPN,
    }
)
ANGLE_SECTION_TYPES: frozenset[SectionType] = frozenset(
    {
        SectionType.L_EQUAL,
        SectionType.L_UNEQUAL,
        SectionType.L_EQUAL_B2B,
        SectionType.L_UNEQUAL_B2B,
    }
)

@dataclass(frozen=True)
class ElementInput:
    """A plate element to classify according to EN 1993 Table 5.2 (compression)."""
    name: str
    kind: ElementKind
    c_mm: float
    t_mm: float


class ElementClassification(BaseModel):
    """Classification result for one plate element."""
    name: str
    kind: ElementKind
    c_mm: float
    t_mm: float
    c_over_t: float
    class_1_limit: float
    class_2_limit: float
    class_3_limit: float
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


def _build_elements(parts: Sequence[tuple[str, ElementKind, float, float]]) -> list[ElementInput]:
    return [
        ElementInput(name=name, kind=kind, c_mm=c_mm, t_mm=t_mm)
        for name, kind, c_mm, t_mm in parts
        if c_mm > 0.0 and t_mm > 0.0
    ]


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


def _limits(kind: ElementKind, epsilon: float) -> tuple[float, float, float]:
    # EN 1993-1-1 Table 5.2 limits for compression elements (psi = 1.0).
    if kind == "internal":
        return (33.0 * epsilon, 38.0 * epsilon, 42.0 * epsilon)
    return (9.0 * epsilon, 10.0 * epsilon, 14.0 * epsilon)


def _classify_ratio(c_over_t: float, kind: ElementKind, epsilon: float) -> tuple[SectionClass, tuple[float, float, float]]:
    lim1, lim2, lim3 = _limits(kind, epsilon)
    if c_over_t <= lim1:
        return SectionClass.CLASS_1, (lim1, lim2, lim3)
    if c_over_t <= lim2:
        return SectionClass.CLASS_2, (lim1, lim2, lim3)
    if c_over_t <= lim3:
        return SectionClass.CLASS_3, (lim1, lim2, lim3)
    return SectionClass.CLASS_4, (lim1, lim2, lim3)


def classify_element(element: ElementInput, fy_mpa: float) -> ElementClassification:
    """Classify a single element regardless of kind."""
    if element.c_mm <= 0.0 or element.t_mm <= 0.0:
        raise ValueError("c_mm and t_mm must both be positive.")

    eps = _epsilon(fy_mpa)
    c_over_t: float = element.c_mm / element.t_mm
    section_class, (lim1, lim2, lim3) = _classify_ratio(c_over_t, element.kind, eps)
    return ElementClassification(
        name=element.name,
        kind=element.kind,
        c_mm=element.c_mm,
        t_mm=element.t_mm,
        c_over_t=c_over_t,
        class_1_limit=lim1,
        class_2_limit=lim2,
        class_3_limit=lim3,
        section_class=section_class,
        metadata={"table": "EN 1993-1-1 Table 5.2", "psi": "1.0"},
    )


def classify_internal_part(c_mm: float, t_mm: float, fy_mpa: float, name: str = "internal") -> ElementClassification:
    """Classify one internal compression element.

    Args:
        c_mm: Flat width of the element in mm.
        t_mm: Thickness in mm.
        fy_mpa: Yield strength in MPa.
        name: Friendly element name.
    """
    return classify_element(
        ElementInput(name=name, kind="internal", c_mm=c_mm, t_mm=t_mm),
        fy_mpa=fy_mpa,
    )


def classify_outstand_flange(c_mm: float, t_mm: float, fy_mpa: float, name: str = "outstand") -> ElementClassification:
    """Classify one outstand compression element.

    Args:
        c_mm: Flat width of the element in mm.
        t_mm: Thickness in mm.
        fy_mpa: Yield strength in MPa.
        name: Friendly element name.
    """
    return classify_element(
        ElementInput(name=name, kind="outstand", c_mm=c_mm, t_mm=t_mm),
        fy_mpa=fy_mpa,
    )


def _class_rank(value: SectionClass) -> int:
    rank: dict[SectionClass, int] = {
        SectionClass.CLASS_1: 1,
        SectionClass.CLASS_2: 2,
        SectionClass.CLASS_3: 3,
        SectionClass.CLASS_4: 4,
    }
    return rank[value]


def classify_elements(elements: Sequence[ElementInput], fy_mpa: float) -> ClassificationResult:
    """Classify a section by classifying all provided elements and taking the worst class."""
    if not elements:
        raise ValueError("At least one element must be provided.")

    eps = _epsilon(fy_mpa)
    results: list[ElementClassification] = [classify_element(element, fy_mpa) for element in elements]

    governing_rank = max(_class_rank(r.section_class) for r in results)
    governing_class = next(sc for sc in SectionClass if sc.name == f"CLASS_{governing_rank}")
    governing_elements = [r.name for r in results if _class_rank(r.section_class) == governing_rank]

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


def classify_section(
    section: Optional[BaseSection] = None,
    fy_mpa: float = 355.0,
    custom_elements: Optional[Iterable[ElementInput]] = None,
) -> ClassificationResult:
    """Classify a section using either section-derived or custom element data.

    Args:
        section: A predefined steelsnakes section object.
        fy_mpa: Yield stress in MPa.
        custom_elements: Optional explicit element list (recommended for built-up/custom shapes).

    Returns:
        A section-level classification with per-element details.
    """
    if custom_elements is not None:
        elements = list(custom_elements)
        return classify_elements(elements, fy_mpa)

    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    elements = _get_section_elements(section)

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
) -> ClassificationResult:
    """Classify a custom section represented as a plain dictionary."""
    if section_type in I_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        return classify_elements(i_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf), fy_mpa)

    if section_type in CHANNEL_SECTION_TYPES:
        d = float(data.get("d", 0.0) or 0.0)
        tw = float(data.get("tw", 0.0) or 0.0)
        b = float(data.get("b", 0.0) or 0.0)
        tf = float(data.get("tf", 0.0) or 0.0)
        return classify_elements(channel_section_elements(d_mm=d, tw_mm=tw, b_mm=b, tf_mm=tf), fy_mpa)

    if section_type in ANGLE_SECTION_TYPES:
        t = float(data.get("t", 0.0) or 0.0)
        h = float(data.get("h", 0.0) or 0.0)
        b = float(data.get("b", h) or 0.0)
        return classify_elements(angle_section_elements(leg_1_mm=h, leg_2_mm=b, t_mm=t), fy_mpa)

    raise NotImplementedError(
        f"No dictionary adapter is registered for section type '{section_type.value}'. "
        "Provide custom_elements explicitly."
    )


if __name__ == "__main__":
    # Example usage with manual elements for a built-up/custom section.
    custom = [
        ElementInput(name="custom_web", kind="internal", c_mm=280.0, t_mm=8.0),
        ElementInput(name="custom_flange", kind="outstand", c_mm=95.0, t_mm=10.0),
    ]
    print(asdict(custom[0]))
    print(classify_section(custom_elements=custom, fy_mpa=355.0).model_dump())
    
