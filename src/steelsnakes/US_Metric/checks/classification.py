# B4. MEMBER PROPERTIES, in SI units for the US_Metric sections
# B4.1 Classification of Sections for Local Buckling; Tables B4.1a (axial compression) and B4.1b (flexure)
# NOTE: the limits of Tables B4.1a and B4.1b are functions of E/Fy, so steelsnakes.US.checks.classification holds in any
# ... consistent units; only the section data is converted here, and E and Fy are passed in MPa.
# NOTE: the US_Metric tables follow the AISC Shapes Database v16.0 (metric): dimensions and radii of gyration in mm, A in
# ... mm², I in 10⁶ mm⁴, Z, S, Q and the HSS torsional constant C in 10³ mm³, J in 10³ mm⁴, Cw in 10⁹ mm⁶, Wno in mm²
# ... and Sw1 to Sw3 in 10⁶ mm⁴; `metric_properties()` converts them all to mm on read.
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import (
    ClassificationContext,
    ElementClassification,
    _section_properties,
)
from steelsnakes.US.checks.classification import classify_section_from_dict as _us_classify_section_from_dict

E_STEEL = 200_000.0 # MPa [29,000 ksi]; modulus of elasticity of steel, AISC 360-22 Symbols and Glossary
G_STEEL = 77_200.0 # MPa [11,200 ksi]; shear modulus of elasticity of steel
FY_A992 = 345.0 # MPa [50 ksi]; ASTM A992/A992M, W shapes
FU_A992 = 450.0 # MPa [65 ksi]; ASTM A992/A992M

# Section-table key -> factor to mm units; keys not listed are already in mm, mm², kg/m or dimensionless ratios
METRIC_SCALE: dict[str, float] = {
    # 10⁶ mm⁴
    "Ix": 1e6, "Iy": 1e6, "Iz": 1e6, "Iw": 1e6, "Sw1": 1e6, "Sw2": 1e6, "Sw3": 1e6,
    # 10³ mm³
    "Zx": 1e3, "Sx": 1e3, "Zy": 1e3, "Sy": 1e3, "Sz": 1e3,
    "SwA": 1e3, "SwB": 1e3, "SwC": 1e3, "SzA": 1e3, "SzB": 1e3, "SzC": 1e3,
    "Qf": 1e3, "Qw": 1e3,
    "C": 1e3, # HSS torsional constant, H3.1
    # 10³ mm⁴
    "J": 1e3,
    # 10⁹ mm⁶
    "Cw": 1e9,
}


def to_mm_units(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert section-table values (METRIC_SCALE, e.g Ix in 10⁶ mm⁴) to mm, mm³, mm⁴ and mm⁶; other keys are copied."""
    data: dict[str, Any] = {}
    for key, value in raw.items():
        scale: Optional[float] = METRIC_SCALE.get(key)
        if scale is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
            data[key] = float(value) * scale
        else:
            data[key] = value
    return data


def metric_properties(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> tuple[SectionType, dict[str, Any]]:
    """Resolve a US_Metric section and/or plain properties into (section_type, properties in mm units).

    Values read from the section, and values passed in `properties`, are both taken in the section-table units of
    METRIC_SCALE (e.g Ix in 10⁶ mm⁴) and converted to mm, mm³, mm⁴ and mm⁶.

    Args:
        section: US_Metric section
        section_type: Section type when passing plain properties
        properties: Plain properties, or overrides for the section's own, in section-table units e.g {"J": 1690.0}
    """
    section_type_, raw = _section_properties(section, section_type, properties)
    return section_type_, to_mm_units(raw)


class ClassificationResult(BaseModel):
    """AISC 360-22 B4.1 classification of a US_Metric section; E and Fy in MPa."""

    E_MPa: float # modulus of elasticity, MPa
    Fy_MPa: float # specified minimum yield stress, MPa
    classification_context: ClassificationContext # axial compression (B4.1a), or flexure about an axis (B4.1b)
    elements: list[ElementClassification] # one per element; width-to-thickness ratios are dimensionless
    section_class: SectionClass # NONSLENDER_ELEMENT or SLENDER_ELEMENT (B4.1a); COMPACT, NONCOMPACT or SLENDER_ELEMENT (B4.1b)
    governing_elements: list[str]

    @property
    def stress_pattern(self) -> ClassificationContext:
        """Alias matching steelsnakes.US.checks.ClassificationResult."""
        return self.classification_context


def classify_section_from_dict(
    section_type: SectionType,
    data: dict[str, Any],
    Fy_MPa: float = FY_A992,
    E_MPa: float = E_STEEL,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
) -> ClassificationResult:
    """AISC 360-22 Section B4.1: Classify a US_Metric section held as a plain dictionary (section-table units).

    Args:
        section_type: Section type, e.g SectionType.W
        data: Section properties, e.g {"h_tw": 25.9, "bf_2tf": 10.2} or the dimensions (mm) behind them
        Fy_MPa: Specified minimum yield stress (MPa); default 345 MPa (ASTM A992)
        E_MPa: Modulus of elasticity (MPa); default 200 000 MPa
        classification_context: Axial compression (Table B4.1a), or flexure about the major or minor axis (Table B4.1b)
    """
    section_type_, converted = metric_properties(section_type=section_type, properties=data)
    result = _us_classify_section_from_dict(section_type_, converted, E_ksi=E_MPa, Fy_ksi=Fy_MPa, classification_context=classification_context)
    return ClassificationResult(
        E_MPa=E_MPa,
        Fy_MPa=Fy_MPa,
        classification_context=result.classification_context,
        elements=result.elements,
        section_class=result.section_class,
        governing_elements=result.governing_elements,
    )


def classify_section(
    section: Optional[BaseSection] = None,
    Fy_MPa: float = FY_A992,
    E_MPa: float = E_STEEL,
    classification_context: ClassificationContext | str = ClassificationContext.AXIAL_COMPRESSION,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> ClassificationResult:
    """AISC 360-22 Section B4.1: Classify a US_Metric section for local buckling.

    Axial compression: each element is nonslender (<= lambda_r) or slender, Table B4.1a.
    Flexure: each element is compact (<= lambda_p), noncompact (<= lambda_r) or slender, Table B4.1b.
    The section takes the class of its most slender element.

    Args:
        section: US_Metric section, e.g W("W360X134")
        Fy_MPa: Specified minimum yield stress (MPa); default 345 MPa (ASTM A992)
        E_MPa: Modulus of elasticity (MPa); default 200 000 MPa
        classification_context: ClassificationContext or its value, e.g "flexure_major_axis"
        section_type: Section type when passing plain properties
        properties: Plain properties, or overrides for the section's own, in section-table units
    """
    if section is not None:
        section_type_: SectionType = section.get_section_type()
        raw: dict[str, Any] = dict(section.get_properties())
    elif section_type is not None:
        section_type_, raw = section_type, {}
    else:
        raise ValueError("Provide either 'section', or 'section_type' with 'properties'.")
    raw.update(properties or {}) # section-table units; scaled once, in classify_section_from_dict()
    return classify_section_from_dict(section_type_, raw, Fy_MPa=Fy_MPa, E_MPa=E_MPa, classification_context=classification_context)


if __name__ == "__main__":
    from steelsnakes.US_Metric.sections.beams import W
    from steelsnakes.US_Metric.sections.hollow import HSS_RCT

    # 🌟 - W360X134 (W14X90): noncompact flanges in flexure for Fy = 345 MPa (User Note F2)
    print(classify_section(W("W360X134"), classification_context="flexure_major_axis").model_dump())
    print(classify_section(HSS_RCT("HSS304.8X203.2X12.7")).model_dump())
    print("🐬")
