"""European column sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from steelsnakes.EU.factory import get_EU_factory
from steelsnakes.EU.sections.beams import Beam
from steelsnakes.base.sections import SectionType


@dataclass
class Column(Beam):
    """Base class for European hot-rolled column sections."""


@dataclass
class WideFlangeColumn(Column):
    """Wide flange HD column section."""

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.HD


@dataclass
class UniversalColumn(Column):
    """Universal UC column section."""

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.UC


def HD(designation: str) -> WideFlangeColumn:
    return cast(WideFlangeColumn, get_EU_factory().create_section(designation, SectionType.HD))


def UC(designation: str) -> UniversalColumn:
    return cast(UniversalColumn, get_EU_factory().create_section(designation, SectionType.UC))


if __name__ == "__main__":
    print(UC("356x406x1299").get_properties(), "\n")
    print(HD("HD-400x421").get_properties())
