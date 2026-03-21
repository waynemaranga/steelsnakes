from dataclasses import dataclass, asdict
from typing import Any, cast

from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US.factory import get_US_factory


@dataclass
class Channel(BaseSection):
    # Identification
    designation: str
    section_type: str  # read as 'type' in database # TODO: change to section_type in database
    EDI_Std_Nomenclature: str = ""

    W: float = 0.0  # Nominal weight (lb/ft)
    A: float = 0.0  # Area (in²)
    d: float = 0.0  #
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
    x: float = 0.0
    eo: float = 0.0
    xp: float = 0.0
    b_t: float = 0.0
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
    Sw2: float = 0.0
    Sw3: float = 0.0
    Qf: float = 0.0
    Qw: float = 0.0
    ro: float = 0.0
    H: float = 0.0
    rts: float = 0.0
    ho: float = 0.0
    PA: float = 0.0
    PB: float = 0.0
    PC: float = 0.0
    PD: float = 0.0
    T: float = 0.0
    WGi: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return channel geometry as generic AISC classification elements."""
        from steelsnakes.US.checks.classification import channel_section_elements

        if self.h_tw <= 0.0:
            raise ValueError(
                "Channel classification requires the exact AISC web slenderness h/tw. "
                "Populate 'h_tw' from the section database instead of substituting d/tw."
            )
        h_over_tw = self.h_tw
        b_over_t = self.b_t if self.b_t > 0.0 else (self.bf / self.tf if self.bf > 0.0 and self.tf > 0.0 else 0.0)
        return channel_section_elements(h_over_tw=h_over_tw, b_over_t=b_over_t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self)


@dataclass
class StandardChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.C


@dataclass
class MiscellaneousChannel(Channel):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.MC


@dataclass
class DoubleStandardChannel(Channel):
    # TODO: Find way to implement Double Channel properties
    pass


@dataclass
class DoubleMiscellaneousChannel(Channel):
    pass


def C_channel(designation: str) -> Channel:
    return cast(Channel, get_US_factory().create_section(designation, SectionType.C))


def MC_channel(designation: str) -> MiscellaneousChannel:
    return cast(MiscellaneousChannel, get_US_factory().create_section(designation, SectionType.MC))


if __name__ == "__main__":
    from steelsnakes.US.checks.classification import ClassificationContext, classify_section

    section = C_channel("C6X10.5")
    print(section.get_properties())
    print(classify_section(section=section, Fy_ksi=50.0).model_dump())
    print(
        classify_section(
            section=section,
            Fy_ksi=50.0,
            classification_context=ClassificationContext.FLEXURE_MINOR_AXIS,
        ).model_dump()
    )
