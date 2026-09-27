"""BS 5950-1:2000 checks; legacy, since many people still use it anyway...

BS 5950 designs with the same rolled profiles as the UK module (BS 4-1 ~ BS EN 10365), so the UK section constructors
are re-exported here: `from steelsnakes.BS import UB, classify_section`.
"""

from steelsnakes.BS.checks import (
    CLASS_NAMES,
    ClassificationResult,
    EffectivePlasticModulusResult,
    ElementClassification,
    ElementInput,
    ElementKind,
    ElementLimits,
    ElementStressDistribution,
    StressPattern,
    StressRatios,
    classify_element,
    classify_elements,
    classify_section,
    classify_section_from_dict,
    compound_flange_elements,
    design_strength,
    effective_plastic_modulus,
    effective_plastic_modulus_i_section,
    element_limits,
    epsilon,
    render_classification,
    stress_ratios,
)
from steelsnakes.UK.sections.angles import L_EQUAL, L_EQUAL_B2B, L_UNEQUAL, L_UNEQUAL_B2B
from steelsnakes.UK.sections.cf_hollow import CFCHS, CFRHS, CFSHS
from steelsnakes.UK.sections.channels import PFC
from steelsnakes.UK.sections.hf_hollow import HFCHS, HFRHS, HFSHS
from steelsnakes.UK.sections.universal import UB, UBP, UC

__all__: list[str] = [
    # Checks; BS 5950-1:2000 Section 3.5
    "CLASS_NAMES",
    "ClassificationResult",
    "EffectivePlasticModulusResult",
    "ElementClassification",
    "ElementInput",
    "ElementKind",
    "ElementLimits",
    "ElementStressDistribution",
    "StressPattern",
    "StressRatios",
    "classify_element",
    "classify_elements",
    "classify_section",
    "classify_section_from_dict",
    "compound_flange_elements",
    "design_strength",
    "effective_plastic_modulus",
    "effective_plastic_modulus_i_section",
    "element_limits",
    "epsilon",
    "render_classification",
    "stress_ratios",
    # Sections; from the UK module
    "UB",
    "UC",
    "UBP",
    "PFC",
    "L_EQUAL",
    "L_UNEQUAL",
    "L_EQUAL_B2B",
    "L_UNEQUAL_B2B",
    "HFCHS",
    "HFRHS",
    "HFSHS",
    "CFCHS",
    "CFRHS",
    "CFSHS",
]
