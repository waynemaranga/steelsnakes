from dataclasses import dataclass, asdict
from typing import Any, cast

from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import get_US_factory


@dataclass
class Pile(BaseSection):
    # Identification
    section_type: str
    EDI_Std_Nomenclature: str = ""
    T_F: str = ""

    W: float = 0.0
    A: float = 0.0
    d: float = 0.0
    ddet: float = 0.0
    bf: float = 0.0
    bfdet: float = 0.0
    tw: float = 0.0
    twdet: float = 0.0
    twdet_2: float = 0.0
    tf: float = 0.0
    tfdet: float = 0.0
    kdes: float = 0.0
    kdet: float = 0.0
    k1: float = 0.0

    bf_2tf: float = 0.0
    h_tw: float = 0.0

    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0

    J: float = 0.0
    Cw: float = 0.0
    Wno: float = 0.0
    Sw1: float = 0.0
    Qf: float = 0.0
    Qw: float = 0.0
    rts: float = 0.0
    ho: float = 0.0
    PA: float = 0.0
    PB: float = 0.0
    PC: float = 0.0
    PD: float = 0.0
    T: float = 0.0
    WGi: float = 0.0
    WGo: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return pile geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import i_section_elements

        if self.h_tw <= 0.0:
            raise ValueError(
                "Pile classification requires the exact AISC web slenderness h/tw. "
                "Populate 'h_tw' from the section database instead of substituting d/tw."
            )
        h_over_tw = self.h_tw
        bf_over_2tf = self.bf_2tf if self.bf_2tf > 0.0 else (self.bf / (2.0 * self.tf) if self.bf > 0.0 and self.tf > 0.0 else 0.0)
        return i_section_elements(h_over_tw=h_over_tw, bf_over_2tf=bf_over_2tf)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self)


@dataclass
class BearingPile(Pile):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HP


def HP(designation: str) -> BearingPile:
    return cast(BearingPile, get_US_factory().create_section(designation, SectionType.HP))


if __name__ == "__main__":
    from steelsnakes.US.checks.classification import ClassificationContext, classify_section

    pile = HP("HP14X73")
    print(pile.get_properties())
    print(classify_section(section=pile, Fy_ksi=50.0).model_dump())
    print(
        classify_section(
            section=pile,
            Fy_ksi=50.0,
            classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
        ).model_dump()
    )
