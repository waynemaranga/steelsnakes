from dataclasses import dataclass, asdict
from typing import Any, cast

from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import get_US_factory


@dataclass
class SteelPipe(BaseSection):
    section_type: str = ""
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0
    A: float = 0.0
    OD: float = 0.0
    ID: float = 0.0
    tnom: float = 0.0
    tdes: float = 0.0
    D_t: float = 0.0
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    J: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return pipe geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import round_hss_section_elements

        D_over_t = self.D_t if self.D_t > 0.0 else (self.OD / self.tdes if self.OD > 0.0 and self.tdes > 0.0 else 0.0)
        return round_hss_section_elements(D_over_t=D_over_t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self)


@dataclass
class Pipe(SteelPipe):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PIPE


def PIPE(designation: str) -> Pipe:
    return cast(Pipe, get_US_factory().create_section(designation, SectionType.PIPE))


if __name__ == "__main__":
    from steelsnakes.US.checks.classification import ClassificationContext, classify_section

    pipe = PIPE("Pipe24STD")
    print(pipe.get_properties())
    print(classify_section(section=pipe, Fy_ksi=35.0).model_dump())
    print(
        classify_section(
            section=pipe,
            Fy_ksi=35.0,
            classification_context=ClassificationContext.FLEXURE_MAJOR_AXIS,
        ).model_dump()
    )
