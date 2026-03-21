"""
Angle steel sections for EU module.
This module implements Equal Angles, Unequal Angles, and their Back-to-Back variants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from steelsnakes.EU.factory import EUSectionFactory, get_EU_factory
from steelsnakes.base.sections import BaseSection, SectionType


def _parse_leg_pair(*candidates: str) -> tuple[float, float] | None:
    for value in candidates:
        if not value:
            continue
        numbers = re.findall(r"\d+(?:\.\d+)?", value)
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
    return None


def _angle_elements(leg_hint: str, designation: str, t: float) -> list[Any]:
    from steelsnakes.EU.checks.classification import angle_section_elements

    if t <= 0.0:
        return []

    pair = _parse_leg_pair(leg_hint, designation)
    if pair is None:
        return []

    leg_1, leg_2 = pair
    return angle_section_elements(leg_1_mm=leg_1, leg_2_mm=leg_2, t_mm=t)


@dataclass
class EqualAngle(BaseSection):
    """
    Equal Angle (L_EQUAL) section.

    L-shaped section with equal leg lengths, commonly used for
    bracing, connections, and structural framing applications.
    """

    hxh: str = ""
    t: float = 0.0
    histar_fy: bool = False
    mass_per_metre: float = 0.0
    r_1: float = 0.0
    r_2: float = 0.0
    c: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    I_uu: float = 0.0
    I_vv: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    i_uu: float = 0.0
    i_vv: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    I_t: float = 0.0
    phi_a: float = 0.0
    A: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxh, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class UnequalAngle(BaseSection):
    """
    Unequal Angle (L_UNEQUAL) section.

    L-shaped section with different leg lengths, commonly used for
    specialized structural applications where asymmetry is beneficial.
    """

    hxb: str = ""
    t: float = 0.0
    histar_fy: bool = False
    mass_per_metre: float = 0.0
    r_1: float = 0.0
    r_2: float = 0.0
    c_y: float = 0.0
    c_z: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    I_uu: float = 0.0
    I_vv: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    i_uu: float = 0.0
    i_vv: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    A: float = 0.0
    tan_alpha: float = 0.0
    I_t: float = 0.0
    phi_a_min: float = 0.0
    phi_a_max: float = 0.0
    psi_a: float = 0.0

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxb, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class EqualAngleBackToBack(BaseSection):
    """
    Back-to-Back Equal Angles (L_EQUAL_B2B) section.

    Two equal angles arranged back-to-back, commonly used for
    compression members and built-up sections.
    """

    hxh: str = ""
    t: float = 0.0
    histar_fy: bool = False
    total_mass_per_metre: float = 0.0
    n_y: float = 0.0
    total_area: float = 0.0
    I_yy: float = 0.0
    i_yy: float = 0.0
    W_el_yy: float = 0.0
    i_zz: Any = ()

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_EQUAL_B2B

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxh, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class UnequalAngleBackToBack(BaseSection):
    """
    Back-to-Back Unequal Angles (L_UNEQUAL_B2B) section.

    Two unequal angles arranged back-to-back, commonly used for
    specialized structural applications requiring built-up sections.
    """

    hxb: str = ""
    t: float = 0.0
    histar_fy: bool = False
    total_mass_per_metre: float = 0.0
    n_y: float = 0.0
    total_area: float = 0.0
    I_yy: float = 0.0
    i_yy: float = 0.0
    W_el_yy: float = 0.0
    i_zz: Any = ()

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.L_UNEQUAL_B2B

    def classification_elements(self) -> list[Any]:
        """Return angle geometry as generic EC3 classification elements."""
        return _angle_elements(self.hxb, self.designation, self.t)

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        from dataclasses import asdict

        return asdict(self)


def L_EQUAL(designation: str, data_directory: Optional[Path] = None) -> EqualAngle:
    """Create an Equal Angle section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    return cast(EqualAngle, factory.create_section(designation, SectionType.L_EQUAL))


def L_UNEQUAL(designation: str, data_directory: Optional[Path] = None) -> UnequalAngle:
    """Create an Unequal Angle section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    return cast(UnequalAngle, factory.create_section(designation, SectionType.L_UNEQUAL))


def L_EQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> EqualAngleBackToBack:
    """Create a Back-to-Back Equal Angles section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    return cast(EqualAngleBackToBack, factory.create_section(designation, SectionType.L_EQUAL_B2B))


def L_UNEQUAL_B2B(designation: str, data_directory: Optional[Path] = None) -> UnequalAngleBackToBack:
    """Create a Back-to-Back Unequal Angles section by designation."""
    factory: EUSectionFactory = get_EU_factory(data_directory)
    return cast(UnequalAngleBackToBack, factory.create_section(designation, SectionType.L_UNEQUAL_B2B))


if __name__ == "__main__":
    from steelsnakes.EU.checks.classification import classify_section

    section = L_UNEQUAL("250x90x16")
    print(section.get_properties())

    classification_result = classify_section(section=section, fy_mpa=355.0)
    print(f"Compression class: {classification_result.section_class}")
    for element in classification_result.elements:
        print(
            f" - {element.name}: kind={element.kind}, stress={element.stress}, "
            f"c={element.c_mm}mm, t={element.t_mm}mm, class={element.section_class}"
        )
