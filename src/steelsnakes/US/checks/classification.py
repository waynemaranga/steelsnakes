""""""
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalOperand=false
# pyright: reportOperatorIssue=false
# pyright: reportMissingImports=false
# pyright: reportArgumentType=false

from __future__ import annotations

import math
from enum import Enum
from typing import Callable, Iterable, Optional, Sequence, TypeVar, cast

from pydantic import BaseModel, Field

from steelsnakes.base.checks import Classification, DesignCode, Reference, SectionClass
from steelsnakes.base.sections import BaseSection, SectionType

# B4. Member Properties
# B4.1. Classification of Sections for Local Buckling
# -- For axial compression: nonslender-element members have with-to-thickness ratios <= lambda_r from table B4.1a, else slender-element.
# --- For flexure: compact sections have width-to-thickness ratios <= lambda_p from table B4.1b, else noncompact if <= lambda_r, else slender-element.
# B4.1a. Unstiffened elements
# B4.1b. Stiffened elements
# TODO: Reproduce necessary tables in documentation e.g Tables B4.1a, B4.1b.
# TODO: For programming and documentation, only provide case numbers and checks per case, user should refer to tables
# TODO: In section libraries, have functions referring to case as eq. et cetera
# TODO: Clarify stiffened vs unstiffened elements in docstring and documentation especially for UK/EU people

# Table B4.1a. lambda_r for compression elements
# (Unstiffened: cases 1, 2, 3 and 4)
# Case 1: wttr = b/t; lambda_r = 0.56*sqrt(E/Fy);
# Case 2: wttr = b/t; lambda_r = 0.64*sqrt(kc*E/Fy); and kc = 4/sqrt(h/tw) but 0.35 <= kc <= 0.76
# Case 3: wttr = b/t; lambda_r = 0.45*sqrt(E/Fy);
# Case 4: wttr = d/t; lambda_r = 0.75*sqrt(E/Fy);
# (Stiffened: cases 5, 6, 7, 8 and 9)
# Case 5: wttr = h/tw; lambda_r = 1.49*sqrt(E/Fy);
# Case 6: wttr = b/t; lambda_r = 1.40*sqrt(E/Fy);
# Case 7: wttr = b/t; lambda_r = 1.40*sqrt(E/Fy);
# Case 8: wttr = b/t; lambda_r = 1.49*sqrt(E/Fy);
# Case 9: wttr = D/t; lambda_r = 0.11*E/Fy;

# Table B4.1b. lambda_p and lambda_r for flexural elements
# Unstiffened i.e cases 10, 11, 12, 13, and 14
# Case 10: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 1.0*sqrt(E/Fy);
# Case 11: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 0.95*sqrt(kc*E/Fl); and kc = 4/sqrt(h/tw) but 0.35 <= kc <= 0.76
# ... Fl = 0.7*Fy for ... # TODO: is elaborate. Complete.
# Case 12: wttr = b/t; lambda_p = 0.54*sqrt(E/Fy); lambda_r = 0.91*sqrt(E/Fy);
# Case 13: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 1.0*sqrt(E/Fy);
# Case 14: wttr = d/t; lambda_p = 0.84*sqrt(E/Fy); lambda_r = 1.52*sqrt(E/Fy);
# Stiffened i.e cases 15, 16, 17, 18, and 21
# Case 15: wttr = h/tw: lambda_p = 3.76*sqrt(E/Fy); lambda_r = 5.70*sqrt(E/Fy);
# Case 16: wttr = hc/tw: lambda_p = [UNSUPPORTED]; lambda_r = 5.70*sqrt(E/Fy); # TODO: implement support for case 16 tho. no implementation currently for unsymmetric sections.
# Case 17: wttr = b/t: lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.40*sqrt(E/Fy);
# Case 18: wttr = b/t: lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.40*sqrt(E/Fy);
# Case 19: wttr = h/t: lambda_p = 2.42*sqrt(E/Fy); lambda_r = 5.70*sqrt(E/Fy);
# Case 20: wttr = D/t: lambda_p = 0.07*(E/Fy); lambda_r = 0.31*(E/Fy);  # NOTE: linear E/Fy, not sqrt
# Case 21: wttr = b/t; lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.49*sqrt(E/Fy);

# NOTE: round HSS / pipe flexure uses the linear E/Fy limits in Table B4.1b.
# The original working note above is retained intentionally because the user asked
# for notes and concerns to remain in the module while the implementation matures.

class CompressionCase(str, Enum):
    """AISC Table B4.1a compression case identifiers.

    The enum value is the string form used in the codebase, e.g. `"case1"`.
    `description` is a short viewing guide for users; the case id remains the
    authoritative selector for calculations.
    """

    CASE_1 = "case1"
    CASE_2 = "case2"
    CASE_3 = "case3"
    CASE_4 = "case4"
    CASE_5 = "case5"
    CASE_6 = "case6"
    CASE_7 = "case7"
    CASE_8 = "case8"
    CASE_9 = "case9"

    @property
    def label(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        descriptions: dict[CompressionCase, str] = {
            CompressionCase.CASE_1: "Flanges of rolled I-shaped sections; Plates projecting from rolled I-shaped sections; Outstanding legs of pairs of angles connected with continuous contact; Flanges of channels; Flanges of tees",
            CompressionCase.CASE_2: "Flanges of built-up I-shaped sections; Plates or angles projecting from built-up I-shaped sections",
            CompressionCase.CASE_3: "Legs of single angles; legs of double angles with separators; all other unstiffened elements",
            CompressionCase.CASE_4: "Stems of tees",
            CompressionCase.CASE_5: "Webs of doubly symmetric rolled I-shaped sections and channels; webs of built-up I-shaped sections and channels",
            CompressionCase.CASE_6: "Walls of rectangular HSS",
            CompressionCase.CASE_7: "Flange cover plates between lines of fasteners or welds",
            CompressionCase.CASE_8: "All other stiffened elements",
            CompressionCase.CASE_9: "Round HSS",
        }
        return descriptions[self]


class FlexureCase(str, Enum):
    """AISC Table B4.1b flexure case identifiers.

    The enum value is the string form used in the codebase, e.g. `"case10"`.
    `description` is a short viewing guide for users; the case id remains the
    authoritative selector for calculations.
    """

    CASE_10 = "case10"
    CASE_11 = "case11"
    CASE_12 = "case12"
    CASE_13 = "case13"
    CASE_14 = "case14"
    CASE_15 = "case15"
    CASE_16 = "case16"
    CASE_17 = "case17"
    CASE_18 = "case18"
    CASE_19 = "case19"
    CASE_20 = "case20"
    CASE_21 = "case21"

    @property
    def label(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        descriptions: dict[FlexureCase, str] = {
            FlexureCase.CASE_10: "Compression flanges of doubly symmetric I-shaped members and channels in flexure; also tee flanges checked with bf/2tf",
            FlexureCase.CASE_11: "Compression flanges of built-up I-shaped members in flexure using kc and Fl",
            FlexureCase.CASE_12: "Legs of single angles in flexure (unstiffened element); b/t with lambda_p = 0.54 sqrt(E/Fy), lambda_r = 0.91 sqrt(E/Fy)",
            FlexureCase.CASE_13: "Flanges of all I-shaped sections and channels in flexure about their minor axis",
            FlexureCase.CASE_14: "Tee stems using d/t in flexure",
            FlexureCase.CASE_15: "Webs of doubly symmetric I-shaped members and channels in major-axis flexure",
            FlexureCase.CASE_16: "Unsymmetric flexural web case using hc/tw; not implemented yet",
            FlexureCase.CASE_17: "Rectangular or square HSS compression flanges using b/t",
            FlexureCase.CASE_18: "Other stiffened flexural flange elements using b/t",
            FlexureCase.CASE_19: "Rectangular or square HSS webs using h/t",
            FlexureCase.CASE_20: "Round HSS and pipe using D/t",
            FlexureCase.CASE_21: "Other stiffened flexural elements using b/t with lambda_r = 1.49 sqrt(E/Fy)",
        }
        return descriptions[self]


ClassificationCase = CompressionCase | FlexureCase
CaseEnumT = TypeVar("CaseEnumT", CompressionCase, FlexureCase)


def _coerce_enum_case(enum_cls: type[CaseEnumT], value: CaseEnumT | str) -> CaseEnumT:
    if isinstance(value, enum_cls):
        return value
    text = value.strip().lower()
    try:
        return enum_cls(text)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_cls)
        raise ValueError(f"Invalid case '{value}'. Expected one of: {allowed}.") from exc

I_SECTION_TYPES = (
    SectionType.W,
    SectionType.S,
    SectionType.M,
    SectionType.HP,
)
CHANNEL_SECTION_TYPES = (
    SectionType.C,
    SectionType.MC,
)
ANGLE_SECTION_TYPES = (
    SectionType.L_EQUAL,
    SectionType.L_UNEQUAL,
    SectionType.L2L_EQUAL,
    SectionType.L2L_LLBB,
    SectionType.L2L_SLBB,
)
TEE_SECTION_TYPES = (
    SectionType.WT,
    SectionType.ST,
    SectionType.MT,
)
RECT_HSS_SECTION_TYPES = (
    SectionType.HSS_RCT,
    SectionType.HSS_SQR,
)
ROUND_HSS_SECTION_TYPES = (
    SectionType.HSS_RND,
    SectionType.PIPE,
)


class ClassificationContext(str, Enum):
    """US local-buckling classification context.

    In AISC B4.1, the classification driver is not an EC3-style stress-gradient
    normalization across each plate element. The driver is:
    1. which element is in compression for the member action being checked; and
    2. which AISC Table B4.1 case applies to that element.

    The legacy names are retained as enum aliases for backward compatibility.
    """

    AXIAL_COMPRESSION = "axial_compression"
    FLEXURE_MAJOR_AXIS = "flexure_major_axis"
    FLEXURE_MINOR_AXIS = "flexure_minor_axis"

    COMPRESSION = "axial_compression"
    MAJOR_AXIS_BENDING = "flexure_major_axis"
    MINOR_AXIS_BENDING = "flexure_minor_axis"


StressPattern = ClassificationContext


class ClassificationMode(str, Enum):
    """Internal classification mode used to pick the correct AISC B4.1 limits."""

    COMPRESSION = "compression"
    FLEXURE = "flexure"


class ElementInput(BaseModel):
    """One AISC Table B4.1 classification element."""

    name: str
    ratio_label: str
    wttr: float
    compression_case: Optional[CompressionCase] = None
    flexure_case: Optional[FlexureCase] = None
    width_in: Optional[float] = None
    thickness_in: Optional[float] = None
    metadata: dict[str, float | str | None] = Field(default_factory=dict)


class ElementClassification(BaseModel):
    """Classification result for one local-buckling element."""

    name: str
    ratio_label: str
    wttr: float
    classification_context: ClassificationContext
    case: ClassificationCase
    lambda_p: Optional[float]
    lambda_r: float
    section_class: SectionClass
    metadata: dict[str, float | str | None] = Field(default_factory=dict)

    @property
    def stress_pattern(self) -> ClassificationContext:
        """Backward-compatible alias for older US API naming."""
        return self.classification_context


class ClassificationResult(BaseModel):
    """Aggregate section classification from one or more AISC element checks."""

    E_ksi: float
    Fy_ksi: float
    classification_context: ClassificationContext
    elements: list[ElementClassification]
    section_class: SectionClass
    governing_elements: list[str]

    @property
    def stress_pattern(self) -> ClassificationContext:
        """Backward-compatible alias for older US API naming."""
        return self.classification_context


SectionElementAdapter = Callable[[BaseSection], Sequence[ElementInput]]
_SECTION_ADAPTERS: dict[SectionType, SectionElementAdapter] = {}


def _normalize_classification_context(value: ClassificationContext | str) -> ClassificationContext:
    if isinstance(value, ClassificationContext):
        return value

    text = value.strip().lower()
    aliases = {
        "axial_compression": ClassificationContext.AXIAL_COMPRESSION,
        "compression": ClassificationContext.AXIAL_COMPRESSION,
        "comprression": ClassificationContext.AXIAL_COMPRESSION,
        "flexure_major_axis": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "major_axis_bending": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "major-axis-bending": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "bending-major-axis": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "major_axis_flexure": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "major-axis-flexure": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "flexure-major-axis": ClassificationContext.FLEXURE_MAJOR_AXIS,
        "flexure_minor_axis": ClassificationContext.FLEXURE_MINOR_AXIS,
        "minor_axis_bending": ClassificationContext.FLEXURE_MINOR_AXIS,
        "minor-axis-bending": ClassificationContext.FLEXURE_MINOR_AXIS,
        "bending-minor-axis": ClassificationContext.FLEXURE_MINOR_AXIS,
    }
    context = aliases.get(text)
    if context is None:
        raise ValueError(
            "Unsupported classification_context. Use a ClassificationContext value or one of: "
            "'axial_compression', 'flexure-major-axis', 'flexure-minor-axis'."
        )
    return context


def _require_positive(value: float | None, name: str) -> float:
    if value is None or value <= 0.0:
        raise ValueError(f"{name} must be positive.")
    return float(value)


def _require_ratio_value(value: float, name: str) -> float:
    if value <= 0.0:
        raise ValueError(f"{name} must be positive and explicitly available for faithful AISC classification.")
    return float(value)


def _build_elements(
    parts: Sequence[
        tuple[
            str,
            str,
            float,
            Optional[CompressionCase],
            Optional[FlexureCase],
        ]
    ],
) -> list[ElementInput]:
    elements: list[ElementInput] = []
    for name, ratio_label, wttr, compression_case, flexure_case in parts:
        if wttr > 0.0:
            elements.append(
                ElementInput(
                    name=name,
                    ratio_label=ratio_label,
                    wttr=wttr,
                    compression_case=compression_case,
                    flexure_case=flexure_case,
                )
            )
    return elements


def i_section_elements(h_over_tw: float, bf_over_2tf: float) -> list[ElementInput]:
    """Build classification elements for rolled I-shaped sections and HP piles."""

    return _build_elements(
        [
            ("web", "h/tw", h_over_tw, CompressionCase.CASE_5, FlexureCase.CASE_15),
            ("flange", "bf/2tf", bf_over_2tf, CompressionCase.CASE_1, FlexureCase.CASE_10),
        ]
    )


def channel_section_elements(h_over_tw: float, b_over_t: float) -> list[ElementInput]:
    """Build classification elements for channels."""

    return _build_elements(
        [
            ("web", "h/tw", h_over_tw, CompressionCase.CASE_5, FlexureCase.CASE_15),
            ("flange", "b/t", b_over_t, CompressionCase.CASE_1, FlexureCase.CASE_10),
        ]
    )


def angle_section_elements(
    leg_1_over_t: float,
    leg_2_over_t: float,
    continuous_contact: bool = False,
) -> list[ElementInput]:
    """Build classification elements for single and double angles.

    Flexural angle classification stays explicit for now; compression support is
    wired through section adapters because that is already well-defined by B4.1a.
    """
    compression_case = CompressionCase.CASE_1 if continuous_contact else CompressionCase.CASE_3

    return _build_elements(
        [
            ("leg_1", "b/t", leg_1_over_t, compression_case, None),
            ("leg_2", "b/t", leg_2_over_t, compression_case, None),
        ]
    )


def tee_section_elements(d_over_t: float, bf_over_2tf: float) -> list[ElementInput]:
    """Build classification elements for structural tees."""

    return _build_elements(
        [
            ("stem", "d/t", d_over_t, CompressionCase.CASE_4, FlexureCase.CASE_14),
            ("flange", "bf/2tf", bf_over_2tf, CompressionCase.CASE_1, FlexureCase.CASE_10),
        ]
    )


def rectangular_hss_section_elements(h_over_tdes: float, b_over_tdes: float) -> list[ElementInput]:
    """Build classification elements for rectangular and square HSS."""

    return _build_elements(
        [
            ("web", "h/tdes", h_over_tdes, CompressionCase.CASE_6, FlexureCase.CASE_19),
            ("flange", "b/tdes", b_over_tdes, CompressionCase.CASE_6, FlexureCase.CASE_17),
        ]
    )


def round_hss_section_elements(D_over_t: float) -> list[ElementInput]:
    """Build classification elements for round HSS and pipe."""

    return _build_elements(
        [
            ("wall", "D/t", D_over_t, CompressionCase.CASE_9, FlexureCase.CASE_20),
        ]
    )


def _compression_rank(value: SectionClass) -> int:
    return {
        SectionClass.NONSLENDER_ELEMENT: 1,
        SectionClass.SLENDER_ELEMENT: 2,
    }[value]


def _flexure_rank(value: SectionClass) -> int:
    return {
        SectionClass.COMPACT: 1,
        SectionClass.NONCOMPACT: 2,
        SectionClass.SLENDER_ELEMENT: 3,
    }[value]


def _ratio_from_kwargs(case: ClassificationCase, kwargs: dict[str, float | None]) -> float:
    explicit = kwargs.get("wttr")
    if explicit is not None:
        return _require_positive(explicit, "wttr")

    if case in {
        CompressionCase.CASE_1,
        CompressionCase.CASE_2,
        CompressionCase.CASE_3,
        CompressionCase.CASE_6,
        CompressionCase.CASE_7,
        CompressionCase.CASE_8,
        FlexureCase.CASE_10,
        FlexureCase.CASE_11,
        FlexureCase.CASE_12,
        FlexureCase.CASE_13,
        FlexureCase.CASE_17,
        FlexureCase.CASE_18,
        FlexureCase.CASE_21,
    }:
        return _require_positive(kwargs.get("b"), "b") / _require_positive(kwargs.get("t"), "t")

    if case in {CompressionCase.CASE_4, FlexureCase.CASE_14}:
        return _require_positive(kwargs.get("d"), "d") / _require_positive(kwargs.get("t"), "t")

    if case in {CompressionCase.CASE_5, FlexureCase.CASE_15, FlexureCase.CASE_16}:
        return _require_positive(kwargs.get("h"), "h") / _require_positive(kwargs.get("tw"), "tw")

    if case == FlexureCase.CASE_19:
        denominator = kwargs.get("t")
        if denominator is not None:
            return _require_positive(kwargs.get("h"), "h") / _require_positive(denominator, "t")
        return _require_positive(kwargs.get("h"), "h") / _require_positive(kwargs.get("tw"), "tw")

    if case in {CompressionCase.CASE_9, FlexureCase.CASE_20}:
        return _require_positive(kwargs.get("D"), "D") / _require_positive(kwargs.get("t"), "t")

    raise ValueError(f"No ratio definition is implemented for '{case.value}'.")


def _kc_from_kwargs(kwargs: dict[str, float | None]) -> tuple[float, dict[str, float]]:
    provided = kwargs.get("kc")
    if provided is not None:
        kc_raw = _require_positive(provided, "kc")
    else:
        h = _require_positive(kwargs.get("h"), "h")
        tw = _require_positive(kwargs.get("tw"), "tw")
        kc_raw = 4.0 / math.sqrt(h / tw)

    kc = max(0.35, min(kc_raw, 0.76))
    return kc, {"kc": kc, "kc_raw": kc_raw}


def _Fl_case11(Fy: float, kwargs: dict[str, float | bool | None]) -> float:
    explicit = kwargs.get("Fl")
    if explicit is not None:
        return _require_positive(cast(Optional[float], explicit), "Fl")

    web_is_slender = kwargs.get("web_is_slender")
    if web_is_slender is None:
        raise ValueError("case11 requires either Fl or web_is_slender together with the needed section-modulus inputs.")

    if bool(web_is_slender):
        return 0.7 * Fy

    Sxt = _require_positive(cast(Optional[float], kwargs.get("Sxt")), "Sxt")
    Sxc = _require_positive(cast(Optional[float], kwargs.get("Sxc")), "Sxc")
    ratio = Sxt / Sxc
    if ratio >= 0.7:
        return 0.7 * Fy
    return max(Fy * ratio, 0.5 * Fy)


def _rectangular_hss_ratio(
    ratio_value: float,
    clear_dimension: float,
    outside_dimension: float,
    thickness: float,
    ratio_name: str,
) -> float:
    if ratio_value > 0.0:
        return ratio_value
    if clear_dimension > 0.0 and thickness > 0.0:
        return clear_dimension / thickness
    if outside_dimension > 0.0 and thickness > 0.0:
        return (outside_dimension - 3.0 * thickness) / thickness
    raise ValueError(
        f"{ratio_name} is required. Provide the precomputed ratio, the clear flat width, "
        "or the outside dimension together with the design thickness."
    )


def _compression_lambda_r(
    case: CompressionCase,
    E: float,
    Fy: float,
    kwargs: dict[str, float | None],
) -> tuple[float, dict[str, float | str | None]]:
    metadata: dict[str, float | str | None] = {}

    match case:
        case CompressionCase.CASE_1:
            return 0.56 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_2:
            kc, kc_metadata = _kc_from_kwargs(kwargs)
            metadata.update(kc_metadata)
            metadata["note"] = "steelsnakes does not yet implement built-up sections."
            return 0.64 * math.sqrt(kc * E / Fy), metadata
        case CompressionCase.CASE_3:
            return 0.45 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_4:
            return 0.75 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_5:
            return 1.49 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_6:
            return 1.40 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_7:
            return 1.40 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_8:
            return 1.49 * math.sqrt(E / Fy), metadata
        case CompressionCase.CASE_9:
            return 0.11 * E / Fy, metadata
        case _:
            raise ValueError(
                "Invalid case for compression classification. Try passing in 'case' as "
                "'case1', 'case2', 'case3', 'case4', 'case5', 'case6', 'case7', 'case8', or 'case9'."
            )


def _flexure_limits(
    case: FlexureCase,
    E: float,
    Fy: float,
    kwargs: dict[str, float | None],
) -> tuple[float, float, dict[str, float | str | None]]:
    metadata: dict[str, float | str | None] = {}

    match case:
        case FlexureCase.CASE_10:
            return 0.38 * math.sqrt(E / Fy), 1.0 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_11:
            kc, kc_metadata = _kc_from_kwargs(kwargs)
            metadata.update(kc_metadata)
            Fl = _Fl_case11(Fy, kwargs)
            metadata["Fl"] = Fl
            metadata["note"] = "steelsnakes does not yet implement built-up sections."
            return 0.38 * math.sqrt(E / Fy), 0.95 * math.sqrt(kc * E / Fl), metadata
        case FlexureCase.CASE_12:
            return 0.54 * math.sqrt(E / Fy), 0.91 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_13:
            return 0.38 * math.sqrt(E / Fy), 1.0 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_14:
            return 0.84 * math.sqrt(E / Fy), 1.52 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_15:
            return 3.76 * math.sqrt(E / Fy), 5.70 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_16:
            raise NotImplementedError(
                "Flexure case16 is reserved for unsymmetric sections and is not implemented yet."
            )
        case FlexureCase.CASE_17:
            return 1.12 * math.sqrt(E / Fy), 1.40 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_18:
            return 1.12 * math.sqrt(E / Fy), 1.40 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_19:
            return 2.42 * math.sqrt(E / Fy), 5.70 * math.sqrt(E / Fy), metadata
        case FlexureCase.CASE_20:
            return 0.07 * E / Fy, 0.31 * E / Fy, metadata
        case FlexureCase.CASE_21:
            return 1.12 * math.sqrt(E / Fy), 1.49 * math.sqrt(E / Fy), metadata
        case _:
            raise ValueError(
                "Invalid case for flexure classification. Try passing in 'case' as "
                "'case10', 'case11', 'case12', 'case13', 'case14', 'case15', 'case16', "
                "'case17', 'case18', 'case19', 'case20', or 'case21'."
            )


def classify_compression(case: CompressionCase | str, **kwargs) -> Classification:
    """AISC 360-22 Section B4.1a: Classification of sections for local buckling.

    wttr is width-to-thickness ratio.
    Unstiffened Elements: Compression elements supported along only one edge parallel
    to the direction of compression force.
    Stiffened Elements: Compression elements supported along two edges parallel to
    the direction of compression force.
    """

    E = _require_positive(kwargs.get("E"), "E")
    Fy = _require_positive(kwargs.get("Fy"), "Fy")
    case_key = _coerce_enum_case(CompressionCase, case)
    wttr = _ratio_from_kwargs(case_key, kwargs)
    lambda_r, extra = _compression_lambda_r(case_key, E, Fy, kwargs)

    return Classification(
        section_class=SectionClass.NONSLENDER_ELEMENT if wttr <= lambda_r else SectionClass.SLENDER_ELEMENT,
        metadata={
            "mode": ClassificationMode.COMPRESSION.value,
            "case": case_key.value,
            "case_description": case_key.description,
            "wttr": wttr,
            "lambda_r": lambda_r,
            **extra,
        },
        reference=Reference(
            code=DesignCode.AISC_360,
            clause="B4.1a",
            title="Classification of sections for local buckling in compression",
        ),
    )


def classify_flexure(case: FlexureCase | str, **kwargs) -> Classification:
    """AISC 360-22 Section B4.1b: Classification of sections for local buckling.

    wttr is width-to-thickness ratio.
    Unstiffened Elements: Compression elements supported along only one edge parallel
    to the direction of compression force.
    Stiffened Elements: Compression elements supported along two edges parallel to
    the direction of compression force.
    """

    E = _require_positive(kwargs.get("E"), "E")
    Fy = _require_positive(kwargs.get("Fy"), "Fy")
    case_key = _coerce_enum_case(FlexureCase, case)
    wttr = _ratio_from_kwargs(case_key, kwargs)
    lambda_p, lambda_r, extra = _flexure_limits(case_key, E, Fy, kwargs)

    if wttr <= lambda_p:
        section_class = SectionClass.COMPACT
    elif wttr <= lambda_r:
        section_class = SectionClass.NONCOMPACT
    else:
        section_class = SectionClass.SLENDER_ELEMENT

    return Classification(
        section_class=section_class,
        metadata={
            "mode": ClassificationMode.FLEXURE.value,
            "case": case_key.value,
            "case_description": case_key.description,
            "wttr": wttr,
            "lambda_p": lambda_p,
            "lambda_r": lambda_r,
            **extra,
        },
        reference=Reference(
            code=DesignCode.AISC_360,
            clause="B4.1b",
            title="Classification of sections for local buckling in flexure",
        ),
    )


def classify_element(
    element: ElementInput,
    E_ksi: float = 29000.0,
    Fy_ksi: float = 50.0,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
    stress_pattern: ClassificationContext | str | None = None,
) -> ElementClassification:
    """Classify one US local-buckling element for a given member action context.

    `stress_pattern` is retained only as a backward-compatible alias. For US B4.1,
    this input is better understood as the member-action context selecting the
    relevant compression element checks.
    """

    context_input = stress_pattern if stress_pattern is not None else classification_context
    context = _normalize_classification_context(context_input)
    E = _require_positive(E_ksi, "E_ksi")
    Fy = _require_positive(Fy_ksi, "Fy_ksi")
    wttr = _require_positive(element.wttr, "element.wttr")
    metadata: dict[str, float | str | None] = {
        "ratio_label": element.ratio_label,
        "classification_context": context.value,
        **element.metadata,
    }

    if context == ClassificationContext.AXIAL_COMPRESSION:
        if element.compression_case is None:
            raise NotImplementedError(
                f"Compression classification is not implemented for element '{element.name}'."
            )
        result = classify_compression(element.compression_case, E=E, Fy=Fy, wttr=wttr)
        metadata.update(result.metadata)
        return ElementClassification(
            name=element.name,
            ratio_label=element.ratio_label,
            wttr=wttr,
            classification_context=context,
            case=element.compression_case,
            lambda_p=None,
            lambda_r=float(result.metadata["lambda_r"]),
            section_class=result.section_class,
            metadata=metadata,
        )

    if context == ClassificationContext.FLEXURE_MAJOR_AXIS:
        if element.flexure_case is None:
            raise NotImplementedError(
                f"Major-axis flexural classification is not implemented for element '{element.name}'."
            )
        result = classify_flexure(element.flexure_case, E=E, Fy=Fy, wttr=wttr)
        metadata.update(result.metadata)
        return ElementClassification(
            name=element.name,
            ratio_label=element.ratio_label,
            wttr=wttr,
            classification_context=context,
            case=element.flexure_case,
            lambda_p=float(result.metadata["lambda_p"]),
            lambda_r=float(result.metadata["lambda_r"]),
            section_class=result.section_class,
            metadata=metadata,
        )

    if context == ClassificationContext.FLEXURE_MINOR_AXIS:
        if element.flexure_case is None:
            raise NotImplementedError(
                f"Minor-axis flexural classification is not implemented for element '{element.name}'."
            )
        result = classify_flexure(element.flexure_case, E=E, Fy=Fy, wttr=wttr)
        metadata.update(result.metadata)
        return ElementClassification(
            name=element.name,
            ratio_label=element.ratio_label,
            wttr=wttr,
            classification_context=context,
            case=element.flexure_case,
            lambda_p=float(result.metadata["lambda_p"]),
            lambda_r=float(result.metadata["lambda_r"]),
            section_class=result.section_class,
            metadata=metadata,
        )

    raise NotImplementedError(
        f"Classification context '{context.value}' is not implemented for US classification yet."
    )


def classify_elements(
    elements: Sequence[ElementInput],
    E_ksi: float = 29000.0,
    Fy_ksi: float = 50.0,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
    stress_pattern: ClassificationContext | str | None = None,
) -> ClassificationResult:
    """Classify all provided US elements and return the governing element class."""

    if not elements:
        raise ValueError("At least one element must be provided.")

    context_input = stress_pattern if stress_pattern is not None else classification_context
    context = _normalize_classification_context(context_input)
    results = [classify_element(element, E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context) for element in elements]

    if context == ClassificationContext.AXIAL_COMPRESSION:
        governing_rank = max(_compression_rank(result.section_class) for result in results)
        governing_class = (
            SectionClass.NONSLENDER_ELEMENT
            if governing_rank == 1
            else SectionClass.SLENDER_ELEMENT
        )
        governing_elements = [
            result.name for result in results if _compression_rank(result.section_class) == governing_rank
        ]
    else:
        governing_rank = max(_flexure_rank(result.section_class) for result in results)
        governing_class = {
            1: SectionClass.COMPACT,
            2: SectionClass.NONCOMPACT,
            3: SectionClass.SLENDER_ELEMENT,
        }[governing_rank]
        governing_elements = [
            result.name for result in results if _flexure_rank(result.section_class) == governing_rank
        ]

    return ClassificationResult(
        E_ksi=E_ksi,
        Fy_ksi=Fy_ksi,
        classification_context=context,
        elements=results,
        section_class=governing_class,
        governing_elements=governing_elements,
    )


def register_section_adapter(section_type: SectionType, adapter: SectionElementAdapter) -> None:
    """Register a section-type adapter that extracts US classification elements."""

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


def _validate_classification_context(
    elements: Sequence[ElementInput],
    section_type: SectionType,
    classification_context: ClassificationContext,
) -> list[ElementInput]:
    if classification_context == ClassificationContext.AXIAL_COMPRESSION:
        return list(elements)

    if classification_context == ClassificationContext.FLEXURE_MAJOR_AXIS:
        if all(element.flexure_case is None for element in elements):
            raise NotImplementedError(
                f"Classification context '{classification_context.value}' is not implemented for section type '{section_type.value}'. "
                "Use custom_elements for explicit control."
            )
        return list(elements)

    if classification_context == ClassificationContext.FLEXURE_MINOR_AXIS:
        if section_type not in I_SECTION_TYPES and section_type not in CHANNEL_SECTION_TYPES:
            raise NotImplementedError(
                f"Classification context '{classification_context.value}' is not implemented for section type '{section_type.value}'. "
                "Use custom_elements for explicit control."
            )

        flange_elements = [
            element.model_copy(update={"flexure_case": FlexureCase.CASE_13})
            for element in elements
            if element.name == "flange"
        ]
        if not flange_elements:
            raise NotImplementedError(
                f"Minor-axis flexural classification requires a 'flange' element for section type '{section_type.value}'."
            )
        return flange_elements

    raise NotImplementedError(
        f"Classification context '{classification_context.value}' is not implemented for section type '{section_type.value}'. "
        "Use custom_elements for explicit control."
    )


def classify_section(
    section: Optional[BaseSection] = None,
    E_ksi: float = 29000.0,
    Fy_ksi: float = 50.0,
    custom_elements: Optional[Iterable[ElementInput]] = None,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
    stress_pattern: ClassificationContext | str | None = None,
) -> ClassificationResult:
    """Classify a US section using section-derived or explicit element data.

    For US AISC B4.1, `classification_context` is the clearer concept: axial
    compression versus flexure about a given axis. `stress_pattern` is accepted as
    a legacy alias to avoid breaking callers that used the earlier EU-flavored name.
    """

    context_input = stress_pattern if stress_pattern is not None else classification_context
    context = _normalize_classification_context(context_input)

    if custom_elements is not None:
        return classify_elements(list(custom_elements), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    if section is None:
        raise ValueError("Provide either 'section' or 'custom_elements'.")

    elements = _validate_classification_context(_get_section_elements(section), section.get_section_type(), context)
    if not elements:
        raise ValueError(
            f"No valid classification elements could be extracted from section '{section}'. "
            "Use custom_elements for explicit control."
        )

    return classify_elements(elements, E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)


def _dict_value(data: dict[str, float | str | bool], *keys: str) -> float:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return float(value)
    return 0.0


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, float | str | bool],
    E_ksi: float = 29000.0,
    Fy_ksi: float = 50.0,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
    stress_pattern: ClassificationContext | str | None = None,
) -> ClassificationResult:
    """Classify a custom US section represented as a plain dictionary."""

    context_input = stress_pattern if stress_pattern is not None else classification_context
    context = _normalize_classification_context(context_input)

    if section_type in I_SECTION_TYPES:
        h_over_tw_value = _dict_value(data, "h_tw")
        if h_over_tw_value <= 0.0:
            h = _dict_value(data, "h")
            tw = _dict_value(data, "tw")
            h_over_tw_value = h / tw if h > 0.0 and tw > 0.0 else 0.0
        elements = i_section_elements(
            h_over_tw=_require_ratio_value(h_over_tw_value, "h_tw"),
            bf_over_2tf=_dict_value(data, "bf_2tf") or (_dict_value(data, "bf") / (2.0 * _dict_value(data, "tf"))),
        )
        return classify_elements(_validate_classification_context(elements, section_type, context), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    if section_type in CHANNEL_SECTION_TYPES:
        h_over_tw_value = _dict_value(data, "h_tw")
        if h_over_tw_value <= 0.0:
            h = _dict_value(data, "h")
            tw = _dict_value(data, "tw")
            h_over_tw_value = h / tw if h > 0.0 and tw > 0.0 else 0.0
        elements = channel_section_elements(
            h_over_tw=_require_ratio_value(h_over_tw_value, "h_tw"),
            b_over_t=_dict_value(data, "b_t") or (_dict_value(data, "b", "bf") / _dict_value(data, "tf")),
        )
        return classify_elements(_validate_classification_context(elements, section_type, context), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    if section_type in ANGLE_SECTION_TYPES:
        if context != ClassificationContext.AXIAL_COMPRESSION:
            raise NotImplementedError(
                f"Classification context '{context.value}' is not implemented for section type '{section_type.value}'. "
                "Use custom_elements for explicit control."
            )
        t = _dict_value(data, "t")
        leg_1 = _dict_value(data, "d", "b")
        leg_2 = _dict_value(data, "b", "d")
        return classify_elements(
            angle_section_elements(leg_1_over_t=leg_1 / t, leg_2_over_t=leg_2 / t),
            E_ksi=E_ksi,
            Fy_ksi=Fy_ksi,
            classification_context=context,
        )

    if section_type in TEE_SECTION_TYPES:
        elements = tee_section_elements(
            d_over_t=_dict_value(data, "D_t") or (_dict_value(data, "d") / _dict_value(data, "tw", "t")),
            bf_over_2tf=_dict_value(data, "bf_2tf") or (_dict_value(data, "bf") / (2.0 * _dict_value(data, "tf"))),
        )
        return classify_elements(_validate_classification_context(elements, section_type, context), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    if section_type in RECT_HSS_SECTION_TYPES:
        elements = rectangular_hss_section_elements(
            h_over_tdes=_rectangular_hss_ratio(
                ratio_value=_dict_value(data, "h_tdes"),
                clear_dimension=_dict_value(data, "h"),
                outside_dimension=_dict_value(data, "Ht"),
                thickness=_dict_value(data, "tdes", "tnom"),
                ratio_name="h_tdes",
            ),
            b_over_tdes=_rectangular_hss_ratio(
                ratio_value=_dict_value(data, "b_tdes"),
                clear_dimension=_dict_value(data, "b"),
                outside_dimension=_dict_value(data, "B"),
                thickness=_dict_value(data, "tdes", "tnom"),
                ratio_name="b_tdes",
            ),
        )
        return classify_elements(_validate_classification_context(elements, section_type, context), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    if section_type in ROUND_HSS_SECTION_TYPES:
        elements = round_hss_section_elements(
            D_over_t=_dict_value(data, "D_t") or (_dict_value(data, "D", "OD") / _dict_value(data, "tdes", "tnom")),
        )
        return classify_elements(_validate_classification_context(elements, section_type, context), E_ksi=E_ksi, Fy_ksi=Fy_ksi, classification_context=context)

    raise NotImplementedError(
        f"No dictionary adapter is registered for section type '{section_type.value}'. "
        "Provide custom_elements explicitly."
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.beams import W_beam
    from steelsnakes.US.sections.hollow import HSS_RND

    beam = W_beam("W44X408")
    rnd = HSS_RND("HSS28.000X0.750")

    print(classify_section(section=beam, Fy_ksi=50.0).model_dump())
    print(
        classify_section(
            section=beam,
            Fy_ksi=50.0,
            classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
        ).model_dump()
    )
    print(classify_section(section=rnd, Fy_ksi=50.0).model_dump())
