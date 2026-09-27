"""Units of the section tables in `steelsnakes`, and conversions between them."""

# TODO: Units, Units, Unts
# --- SI ---
# Create a system of units (pun-intended), have aliases, representations descriptions etc
# Use pint or forallpeople and strict validation
# Use the same units intereface to bridge sections accross regions
# NOTE: for now, only lengths and powers of length, i.e the dimensions and properties of cross-sections. The checks keep
# ... plain floats in their own units: EU N and mm; BS kN, kNm, N/mm² and mm; US kips, ksi and in; US_Metric N, MPa and mm.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    """A unit of length, or of a power of length e.g cm⁴, with its size in mm."""

    symbol: str # e.g "cm⁴"
    power: int # power of length, e.g 4 for a second moment of area
    mm: float # size in mm^power, e.g 1 cm⁴ = 1e4 mm⁴
    aliases: tuple[str, ...] = ()

    def to_mm(self, value: float) -> float:
        """Convert `value` in this unit to mm^power."""
        return value * self.mm

    def from_mm(self, value: float) -> float:
        """Convert `value` in mm^power to this unit."""
        return value / self.mm


# --- Length
MM = Unit("mm", 1, 1.0, ("millimetre", "millimetres"))
CM = Unit("cm", 1, 10.0, ("centimetre", "centimetres"))
M = Unit("m", 1, 1_000.0, ("metre", "metres"))
INCH = Unit("in", 1, 25.4, ("inch", "inches")) # because `in` is a python keyword
# --- Area
MM2 = Unit("mm²", 2, 1.0, ("mm2", "mm^2", "mm**2", "square millimetre"))
CM2 = Unit("cm²", 2, 1e2, ("cm2", "cm^2", "cm**2", "square centimetre"))
IN2 = Unit("in²", 2, 25.4**2, ("in2", "in^2", "in**2", "square inch"))
# --- Section moduli
MM3 = Unit("mm³", 3, 1.0, ("mm3", "mm^3", "mm**3"))
MM3_E3 = Unit("10³ mm³", 3, 1e3, ("10^3 mm3", "10^3 mm^3"))
CM3 = Unit("cm³", 3, 1e3, ("cm3", "cm^3", "cm**3"))
IN3 = Unit("in³", 3, 25.4**3, ("in3", "in^3", "in**3"))
# --- Second moments of area and torsion constants
MM4 = Unit("mm⁴", 4, 1.0, ("mm4", "mm^4", "mm**4"))
MM4_E3 = Unit("10³ mm⁴", 4, 1e3, ("10^3 mm4", "10^3 mm^4"))
MM4_E6 = Unit("10⁶ mm⁴", 4, 1e6, ("10^6 mm4", "10^6 mm^4"))
CM4 = Unit("cm⁴", 4, 1e4, ("cm4", "cm^4", "cm**4"))
IN4 = Unit("in⁴", 4, 25.4**4, ("in4", "in^4", "in**4"))
# --- Warping constants
MM6 = Unit("mm⁶", 6, 1.0, ("mm6", "mm^6", "mm**6"))
MM6_E9 = Unit("10⁹ mm⁶", 6, 1e9, ("10^9 mm6", "10^9 mm^6"))
CM6 = Unit("cm⁶", 6, 1e6, ("cm6", "cm^6", "cm**6"))
DM6 = Unit("dm⁶", 6, 1e12, ("dm6", "dm^6", "dm**6"))
IN6 = Unit("in⁶", 6, 25.4**6, ("in6", "in^6", "in**6"))
# --- Ratios
ONE = Unit("-", 0, 1.0, ("", "dimensionless"))

UNITS: dict[str, Unit] = {
    name: unit
    for unit in (MM, CM, M, INCH, MM2, CM2, IN2, MM3, MM3_E3, CM3, IN3, MM4, MM4_E3, MM4_E6, CM4, IN4, MM6, MM6_E9, CM6, DM6, IN6, ONE)
    for name in (unit.symbol, *unit.aliases)
}


def get_unit(name: str) -> Unit:
    """Look up a unit by its symbol or an alias, e.g "cm⁴", "cm4", "cm^4" or "cm**4"."""
    unit = UNITS.get(name.strip())
    if unit is None:
        raise ValueError(f"Unknown unit '{name}'; expected one of {', '.join(sorted({u.symbol for u in UNITS.values()}))}.")
    return unit


# --- Section tables
# Unit of the dimensions (h, b, tw, tf, r, t, ...) of each region's section tables
LENGTH_UNITS: dict[str, Unit] = {
    "UK": MM, # SCI Blue Book
    "EU": MM, # ArcelorMittal Orange Book
    "US": INCH, # AISC Shapes Database v16.0
    "US_METRIC": MM, # AISC Shapes Database v16.0 (metric)
}

# Section-table key and unit of each property of `steelsnakes.engine.sections.SectionAnalysis`, per module
# NOTE: EU/UK tabulate I_w in dm⁶ (IPE 300: 0.126); BS reads the UK tables in BS 5950 symbols (x-x major, y-y minor, H
# ... the warping constant); US angles tabulate their principal axes as w-w (Iw) and z-z (Iz, rz), and US H is the
# ... flexural constant of E4 (Eq. E4-8), with ro the polar radius of gyration about the shear centre (Eq. E4-9).
SECTION_TABLE_UNITS: dict[str, dict[str, tuple[str, Unit]]] = {
    "UK": {
        "A": ("A", CM2),
        "I_y": ("I_yy", CM4), "I_z": ("I_zz", CM4), "I_u": ("I_uu", CM4), "I_v": ("I_vv", CM4),
        "i_y": ("i_yy", CM), "i_z": ("i_zz", CM), "i_u": ("i_uu", CM), "i_v": ("i_vv", CM),
        "W_el_y": ("W_el_yy", CM3), "W_el_z": ("W_el_zz", CM3),
        "W_pl_y": ("W_pl_yy", CM3), "W_pl_z": ("W_pl_zz", CM3),
        "I_t": ("I_t", CM4),
        "I_w": ("I_w", DM6),
    },
    "BS": {
        "A": ("A", CM2),
        "I_y": ("Ix", CM4), "I_z": ("Iy", CM4), "I_u": ("Iu", CM4), "I_v": ("Iv", CM4),
        "i_y": ("rx", CM), "i_z": ("ry", CM), "i_u": ("ru", CM), "i_v": ("rv", CM),
        "W_el_y": ("Zx", CM3), "W_el_z": ("Zy", CM3), # elastic modulus
        "W_pl_y": ("Sx", CM3), "W_pl_z": ("Sy", CM3), # plastic modulus
        "I_t": ("J", CM4),
        "I_w": ("H", DM6),
    },
    "US": {
        "A": ("A", IN2),
        "I_y": ("Ix", IN4), "I_z": ("Iy", IN4), "I_u": ("Iw", IN4), "I_v": ("Iz", IN4),
        "i_y": ("rx", INCH), "i_z": ("ry", INCH), "i_v": ("rz", INCH),
        "W_el_y": ("Sx", IN3), "W_el_z": ("Sy", IN3),
        "W_pl_y": ("Zx", IN3), "W_pl_z": ("Zy", IN3),
        "I_t": ("J", IN4),
        "I_w": ("Cw", IN6),
        "i_0": ("ro", INCH), # E4-9
        "H": ("H", ONE), # E4-8
    },
    "US_METRIC": {
        "A": ("A", MM2),
        "I_y": ("Ix", MM4_E6), "I_z": ("Iy", MM4_E6), "I_u": ("Iw", MM4_E6), "I_v": ("Iz", MM4_E6),
        "i_y": ("rx", MM), "i_z": ("ry", MM), "i_v": ("rz", MM),
        "W_el_y": ("Sx", MM3_E3), "W_el_z": ("Sy", MM3_E3),
        "W_pl_y": ("Zx", MM3_E3), "W_pl_z": ("Zy", MM3_E3),
        "I_t": ("J", MM4_E3),
        "I_w": ("Cw", MM6_E9),
        "i_0": ("ro", MM), # E4-9
        "H": ("H", ONE), # E4-8
    },
}
SECTION_TABLE_UNITS["EU"] = SECTION_TABLE_UNITS["UK"] # the same table layout


if __name__ == "__main__":
    print(get_unit("cm^4").to_mm(8356.0)) # IPE 300 I_y, mm⁴
    print(DM6.from_mm(1.26e11)) # IPE 300 I_w, dm⁶
    print("🐬")
