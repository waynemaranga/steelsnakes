"""
Channel steel sections for UK module.

This module implements Parallel Flange Channels (PFC).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, cast

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.UK.factory import UKSectionFactory, get_UK_factory


@dataclass
class ParallelFlangeChannel(BaseSection):
    """
    Parallel Flange Channel (PFC) section.
    
    C-shaped section with parallel flanges, commonly used for
    secondary beams, purlins, and cladding rails.
    """

    # Identification
    serial_size: str = ""
    is_additional: bool = False
    
    # Physical properties
    mass_per_metre: float = 0.0
    h: float = 0.0
    b: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    r: float = 0.0
    d: float = 0.0
    cw_tw: float = 0.0
    cf_tf: float = 0.0
    e0: float = 0.0
    C: float = 0.0
    N: float = 0.0
    n: float = 0.0
    surface_area_per_metre: float = 0.0
    surface_area_per_tonne: float = 0.0
    I_yy: float = 0.0
    I_zz: float = 0.0
    i_yy: float = 0.0
    i_zz: float = 0.0
    W_el_yy: float = 0.0
    W_el_zz: float = 0.0
    W_pl_yy: float = 0.0
    W_pl_zz: float = 0.0
    U: float = 0.0
    X: float = 0.0
    I_w: float = 0.0
    I_t: float = 0.0
    A: float = 0.0

    def classification_elements(self) -> list[Any]:
        """Return UK channel geometry as generic EC3 classification elements."""
        from steelsnakes.EU.checks.classification import channel_section_elements

        return channel_section_elements(d_mm=self.d, tw_mm=self.tw, b_mm=self.b, tf_mm=self.tf)

    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PFC

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        # SAFE: returns a detached dictionary representation of the dataclass.
        return asdict(self)


def PFC(designation: str, data_directory: Optional[Path] = None) -> ParallelFlangeChannel:
    """Create a Parallel Flange Channel section by designation."""
    factory: UKSectionFactory = get_UK_factory(data_directory)
    return cast(ParallelFlangeChannel, factory.create_section(designation, SectionType.PFC))
