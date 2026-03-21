"""European bearing pile sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from steelsnakes.EU.factory import get_EU_factory
from steelsnakes.EU.sections.beams import Beam
from steelsnakes.base.sections import SectionType


@dataclass
class BearingPile(Beam):
    """Base class for European bearing pile sections."""


@dataclass
class WideFlangeBearingPile(BearingPile):
    """Wide flange HP bearing pile section."""

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HP


@dataclass
class UniversalBearingPile(BearingPile):
    """Universal UBP bearing pile section."""

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UBP


def HP(designation: str) -> WideFlangeBearingPile:
    return cast(WideFlangeBearingPile, get_EU_factory().create_section(designation, SectionType.HP))


def UBP(designation: str) -> UniversalBearingPile:
    return cast(UniversalBearingPile, get_EU_factory().create_section(designation, SectionType.UBP))


if __name__ == "__main__":
    from steelsnakes.EU.checks.classification import classify_section

    section = UBP("356x368x109")
    print(section.get_properties())

    classification_result = classify_section(section=section, fy_mpa=235.0)
    print(f"Compression class: {classification_result.model_dump_json(indent=2)}")
    print(f"Compression class: {classification_result.section_class}")
