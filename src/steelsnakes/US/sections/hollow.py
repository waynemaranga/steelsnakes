from dataclasses import dataclass, asdict
from typing import Any, cast

from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import get_US_factory


@dataclass
class HollowStructuralSection(BaseSection):
    designation: str
    section_type: str  # read as 'type' in database # TODO: change to section_type in database
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0  # Nominal weight (lb/ft)
    A: float = 0.0  # Area (in²)

    tnom: float = 0.0
    tdes: float = 0.0

    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    J: float = 0.0
    C: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return HSS geometry as generic AISC classification elements."""
        return []

    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all section properties."""
        return asdict(self)


@dataclass
class RectangularHSS(HollowStructuralSection):
    Ht: float = 0.0
    h: float = 0.0
    B: float = 0.0
    b: float = 0.0
    b_tdes: float = 0.0
    h_tdes: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return rectangular HSS geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import rectangular_hss_section_elements

        if self.h_tdes > 0.0:
            h_over_tdes = self.h_tdes
        elif self.h > 0.0 and self.tdes > 0.0:
            h_over_tdes = self.h / self.tdes
        elif self.Ht > 0.0 and self.tdes > 0.0:
            h_over_tdes = (self.Ht - 3.0 * self.tdes) / self.tdes
        else:
            raise ValueError("Rectangular HSS classification requires h_tdes, clear h, or Ht with tdes.")

        if self.b_tdes > 0.0:
            b_over_tdes = self.b_tdes
        elif self.b > 0.0 and self.tdes > 0.0:
            b_over_tdes = self.b / self.tdes
        elif self.B > 0.0 and self.tdes > 0.0:
            b_over_tdes = (self.B - 3.0 * self.tdes) / self.tdes
        else:
            raise ValueError("Rectangular HSS classification requires b_tdes, clear b, or B with tdes.")

        return rectangular_hss_section_elements(h_over_tdes=h_over_tdes, b_over_tdes=b_over_tdes)

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_RCT


@dataclass
class SquareHSS(HollowStructuralSection):
    Ht: float = 0.0
    h: float = 0.0
    B: float = 0.0
    b: float = 0.0
    b_tdes: float = 0.0
    h_tdes: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return square HSS geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import rectangular_hss_section_elements

        if self.h_tdes > 0.0:
            h_over_tdes = self.h_tdes
        elif self.h > 0.0 and self.tdes > 0.0:
            h_over_tdes = self.h / self.tdes
        elif self.Ht > 0.0 and self.tdes > 0.0:
            h_over_tdes = (self.Ht - 3.0 * self.tdes) / self.tdes
        else:
            raise ValueError("Square HSS classification requires h_tdes, clear h, or Ht with tdes.")

        if self.b_tdes > 0.0:
            b_over_tdes = self.b_tdes
        elif self.b > 0.0 and self.tdes > 0.0:
            b_over_tdes = self.b / self.tdes
        elif self.B > 0.0 and self.tdes > 0.0:
            b_over_tdes = (self.B - 3.0 * self.tdes) / self.tdes
        else:
            raise ValueError("Square HSS classification requires b_tdes, clear b, or B with tdes.")

        return rectangular_hss_section_elements(h_over_tdes=h_over_tdes, b_over_tdes=b_over_tdes)

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_SQR


@dataclass
class RoundHSS(HollowStructuralSection):
    OD: float = 0.0
    D_t: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return round HSS geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import round_hss_section_elements

        D_over_t = self.D_t if self.D_t > 0.0 else (self.OD / self.tdes if self.OD > 0.0 and self.tdes > 0.0 else 0.0)
        return round_hss_section_elements(D_over_t=D_over_t)

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HSS_RND


def HSS_RCT(designation: str) -> RectangularHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(RectangularHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_RCT))


def HSS_SQR(designation: str) -> SquareHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(SquareHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_SQR))


def HSS_RND(designation: str) -> RoundHSS:
    """Note: Case insensitive - accepts both "x" and "X" separators"""
    return cast(RoundHSS, get_US_factory().create_section(designation.upper().strip(), SectionType.HSS_RND))


if __name__ == "__main__":
    from steelsnakes.US.checks.classification import ClassificationContext, classify_section

    rect = HSS_RCT("HSS10X6X1/2")
    print(rect.get_properties())
    print(classify_section(section=rect, Fy_ksi=46.0).model_dump())
    print(
        classify_section(
            section=rect,
            Fy_ksi=46.0,
            classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
        ).model_dump()
    )
    print(HSS_RND("HSS5.563X0.134").get_properties())
