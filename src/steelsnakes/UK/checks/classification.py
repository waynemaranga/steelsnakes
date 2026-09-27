"""UK EN 1993 classification helpers.

The UK classification surface intentionally reuses the shared EC3 engine from
``steelsnakes.EU.checks.classification``. UK-specific behavior is handled by the
section families that provide the correct classification geometry.
"""

from steelsnakes.EU.checks.classification import (
    ClassificationResult,
    ElementClassification,
    ElementInput,
    ElementStressDistribution,
    StressPattern,
    outstand_buckling_factor,
    classify_circular_hollow,
    classify_element,
    classify_elements,
    classify_internal_part,
    classify_outstand_flange,
    classify_section,
    classify_section_from_dict,
)

__all__: list[str] = [
    "ElementInput",
    "ElementClassification",
    "ClassificationResult",
    "ElementStressDistribution",
    "StressPattern",
    "outstand_buckling_factor",
    "classify_circular_hollow",
    "classify_element",
    "classify_internal_part",
    "classify_outstand_flange",
    "classify_elements",
    "classify_section",
    "classify_section_from_dict",
]
