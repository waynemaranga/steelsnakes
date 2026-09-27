"""Section analysis: the properties of cross-sections from their geometry, by the finite element method of `sectionproperties`.

Draws the sections the regional modules tabulate from their dimensions, and takes any other section, e.g built-up or
welded, as a `sectionproperties` geometry. Applying forces to a section (stress analysis) comes later.
"""

# NOTE: units are mm: dimensions are converted from the section-table units on read (e.g US inches), and results are in
# ... mm, mm², mm³, mm⁴ and mm⁶; `SectionAnalysis.to_properties()` converts them to a module's section-table keys and units.
# NOTE: axes follow EN 1993-1-1 1.7: y-y major (horizontal), z-z minor (vertical), u-u and v-v principal. Sections are
# ... drawn depth-vertical, so y-y is the major axis of I-sections, channels, tees and hollow sections; angles are drawn
# ... with the long leg vertical, as tabulated.
# NOTE: sectionproperties (https://sectionproperties.readthedocs.io) meshes the geometry with 6-noded triangles. The
# ... geometric and plastic properties are exact for the drawn polygon; I_t and I_w converge to within 1 % at the default
# ... mesh of A/200. Radii are polylines of `n_r` points, and circles and ellipses of 8·n_r points.
from __future__ import annotations

import math
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from sectionproperties.analysis.section import Section
from sectionproperties.pre.geometry import CompoundGeometry, Geometry
from sectionproperties.pre.library import (
    angle_section,
    channel_section,
    circular_hollow_section,
    elliptical_hollow_section,
    i_section,
    rectangular_hollow_section,
    tee_section,
)

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.engine.units import LENGTH_UNITS, SECTION_TABLE_UNITS

N_R = 16 # points on each root, toe or corner radius
MESH_DIVISIONS = 200 # default maximum element area is A/200

# --- Section families drawn from their tabulated dimensions
I_SECTION_TYPES = (
    SectionType.UB, SectionType.UC, SectionType.UBP, # UK, EU
    SectionType.IPE, SectionType.HE, SectionType.HL, SectionType.HLZ, SectionType.HD, SectionType.HP, # EU; HP also US
    SectionType.W, SectionType.M, # US
)
CHANNEL_SECTION_TYPES = (SectionType.PFC, SectionType.UPE) # parallel flanges
TEE_SECTION_TYPES = (SectionType.WT, SectionType.MT) # cut from W and M shapes
ANGLE_SECTION_TYPES = (SectionType.L_EQUAL, SectionType.L_UNEQUAL)
HOT_FINISHED_RHS_SECTION_TYPES = (SectionType.HFRHS, SectionType.HFSHS)
COLD_FORMED_RHS_SECTION_TYPES = (SectionType.CFRHS, SectionType.CFSHS)
HSS_RECTANGULAR_SECTION_TYPES = (SectionType.HSS_RCT, SectionType.HSS_SQR)
CHS_SECTION_TYPES = (SectionType.HFCHS, SectionType.CFCHS, SectionType.HSS_RND, SectionType.PIPE)
EHS_SECTION_TYPES = (SectionType.HFEHS,)
US_REGIONS = ("US", "US_METRIC")


class SectionAnalysis(BaseModel):
    """Properties of a cross-section from the finite element analysis of its geometry, in mm units."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    designation: Optional[str] = None
    section_type: Optional[SectionType] = None
    # Geometric properties, about the centroidal axes
    A: float # mm², cross-sectional area
    y_c: float # mm, centroid from the origin of the geometry, horizontal
    z_c: float # mm, centroid from the origin of the geometry, vertical
    I_y: float # mm⁴, second moment of area about y-y
    I_z: float # mm⁴, second moment of area about z-z
    I_yz: float # mm⁴, product of area; 0 for sections symmetric about y-y or z-z
    i_y: float # mm, radius of gyration about y-y
    i_z: float # mm, radius of gyration about z-z
    W_el_y: float # mm³, elastic modulus about y-y, to the extreme fibre furthest from it
    W_el_z: float # mm³, elastic modulus about z-z, to the extreme fibre furthest from it
    # ... principal axes: u-u major, v-v minor; the same as y-y and z-z unless I_yz is not 0, e.g angles
    I_u: float # mm⁴
    I_v: float # mm⁴
    i_u: float # mm
    i_v: float # mm
    alpha: float # degrees, from y-y to u-u, anticlockwise
    # Plastic properties
    W_pl_y: float # mm³, plastic modulus about the plastic neutral axis parallel to y-y
    W_pl_z: float # mm³, plastic modulus about the plastic neutral axis parallel to z-z
    # Warping properties; None when the warping analysis is skipped
    I_t: Optional[float] = None # mm⁴, St Venant torsion constant
    I_w: Optional[float] = None # mm⁶, warping constant about the shear centre
    y_s: Optional[float] = None # mm, shear centre from the centroid, horizontal
    z_s: Optional[float] = None # mm, shear centre from the centroid, vertical
    i_0: Optional[float] = None # mm, polar radius of gyration about the shear centre, i_0² = i_y² + i_z² + y_s² + z_s²
    mesh_elements: int # 6-noded triangles
    model: Optional[Section] = Field(default=None, exclude=True, repr=False) # sectionproperties Section, for stress analysis

    def to_properties(self, region: str) -> dict[str, float]:
        """Properties in a module's section-table keys and units, e.g for the `properties` of its checks.

        Principal axes are included only for sections with I_yz, e.g angles, and warping properties only when analysed.

        Args:
            region: "UK", "EU", "BS" (the UK tables in BS 5950 symbols), "US" or "US_METRIC"

        Returns:
            e.g {"A": 53.8, "I_yy": 8356.0, ..., "I_w": 0.126} for "EU", in cm², cm⁴, cm³, cm and dm⁶
        """
        key: str = region.upper()
        if key not in SECTION_TABLE_UNITS:
            raise ValueError(f"Unknown region '{region}'; expected one of {', '.join(SECTION_TABLE_UNITS)}.")
        values: dict[str, Any] = self.model_dump()
        if self.i_0 is not None and self.y_s is not None and self.z_s is not None:
            values["H"] = 1.0 - (self.y_s**2 + self.z_s**2) / self.i_0**2 # AISC 360-22 Eq. E4-8
        asymmetric: bool = abs(self.I_yz) > 1e-6 * max(self.I_y, self.I_z)

        properties: dict[str, float] = {}
        for name, (table_key, unit) in SECTION_TABLE_UNITS[key].items():
            value: Optional[float] = values.get(name)
            if value is None or (name in ("I_u", "I_v", "i_u", "i_v") and not asymmetric):
                continue
            properties[table_key] = unit.from_mm(value)
        return properties


# --- Helpers ---
def _region(section: Optional[BaseSection], region: Optional[str]) -> str:
    """Region of the section tables: as given, else the package of the section's class, e.g steelsnakes.US_Metric."""
    key: str = ""
    if region is not None:
        key = region.upper()
    elif section is not None:
        parts: list[str] = type(section).__module__.split(".")
        key = parts[1].upper() if len(parts) > 2 and parts[0] == "steelsnakes" else ""
    if key not in LENGTH_UNITS:
        raise ValueError(f"Pass `region` as one of {', '.join(LENGTH_UNITS)}, for the keys and units of the dimensions; got '{region or key}'.")
    return key


def _section_data(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
) -> tuple[SectionType, dict[str, Any]]:
    """Resolve a section and/or plain properties (section-table units) into (section_type, raw data).

    `properties` overrides or supplements the section's own values, e.g "r" of a welded section.
    """
    raw: dict[str, Any] = {}
    if section is not None:
        raw.update(section.get_properties())
        raw.setdefault("designation", section.designation)
        section_type = section.get_section_type()
    raw.update(properties or {})
    if section_type is None:
        raise ValueError("Provide either 'section', or both 'section_type' and 'properties'.")
    return section_type, raw


def _positive(raw: dict[str, Any], key: str) -> Optional[float]:
    value = raw.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0:
        return float(value)
    return None


def _dimension(raw: dict[str, Any], key: str, scale: float) -> float:
    value: Optional[float] = _positive(raw, key)
    if value is None:
        raise ValueError(f"Section dimension '{key}' is not available; pass it through `properties` (section-table units).")
    return value * scale


def _size(raw: dict[str, Any], scale: float) -> tuple[float, float]:
    """(h, b) of angles and hollow sections; the UK and EU tables store them as "h x b" text, e.g "200x100"."""
    h: Optional[float] = _positive(raw, "h")
    b: Optional[float] = _positive(raw, "b")
    size = raw.get("hxb") or raw.get("hxh")
    if (h is None or b is None) and isinstance(size, str):
        numbers: list[float] = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", size)]
        if len(numbers) >= 2:
            h = h if h is not None else numbers[0]
            b = b if b is not None else numbers[1]
    if h is None or b is None:
        raise ValueError("Section size is not available; pass 'h' and 'b' through `properties` (section-table units).")
    return h * scale, b * scale


def _us_root_radius(raw: dict[str, Any], t: float, scale: float) -> float:
    """Root radius of US shapes: "r" if given, else kdes - t; AISC tabulates kdes, the design distance from the outer
    face of the flange (or the heel of an angle) to the toe of the fillet, not r."""
    r: Optional[float] = _positive(raw, "r")
    if r is not None:
        return r * scale
    return max(_dimension(raw, "kdes", scale) - t, 0.0)


def _cold_formed_corner_radius(t: float) -> float:
    """External corner radius r_o of cold formed hollow sections for calculating their properties (EN 10219-2)."""
    if t <= 6.0:
        return 2.0 * t
    if t <= 10.0:
        return 2.5 * t
    return 3.0 * t


# --- Geometry ---
def section_geometry(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    n_r: int = N_R,
) -> Geometry:
    """Geometry of a section drawn from its tabulated dimensions, in mm, with its depth vertical.

    The geometry can be plotted (`.plot_geometry()`), or combined with plates into a built-up section and passed to
    `analyse_section(geometry=...)`, e.g `section_geometry(UB("457x191x67")) + rectangular_section(...).align_to(...)`.

    Args:
        section: Section from a regional module, e.g `UB("457x191x67")` or `W("W14X90")`
        section_type: Section type when passing plain properties
        properties: Plain dimensions, or overrides for the section's own, in section-table units, e.g {"r": 0.0}
        region: "UK", "EU", "US" or "US_METRIC", for the keys and units of the dimensions; by default, the section's
        n_r: Points on each root, toe or corner radius; circles and ellipses take 8·n_r

    Returns:
        sectionproperties Geometry, in mm

    Raises:
        NotImplementedError: For tapered flanges (UPN, S, C, MC, ST), back-to-back angles, Sigma and Zed sections, and
            the IN sections; pass their geometry to `analyse_section(geometry=...)` instead
    """
    region_: str = _region(section, region)
    section_type, raw = _section_data(section, section_type, properties)
    scale: float = LENGTH_UNITS[region_].mm
    us: bool = region_ in US_REGIONS

    # I and H sections; US W, M and HP; root radius r at the four web-to-flange junctions
    if section_type in I_SECTION_TYPES:
        d: float = _dimension(raw, "d" if us else "h", scale)
        b: float = _dimension(raw, "bf" if us else "b", scale)
        tw: float = _dimension(raw, "tw", scale)
        tf: float = _dimension(raw, "tf", scale)
        r: float = _us_root_radius(raw, tf, scale) if us else (_positive(raw, "r") or 0.0) * scale
        return i_section(d=d, b=b, t_f=tf, t_w=tw, r=r, n_r=n_r)

    # Parallel flange channels, web on the left
    if section_type in CHANNEL_SECTION_TYPES:
        return channel_section(
            d=_dimension(raw, "h", scale),
            b=_dimension(raw, "b", scale),
            t_f=_dimension(raw, "tf", scale),
            t_w=_dimension(raw, "tw", scale),
            r=(_positive(raw, "r") or 0.0) * scale,
            n_r=n_r,
        )

    # Structural tees, flange on top
    if section_type in TEE_SECTION_TYPES:
        tf = _dimension(raw, "tf", scale)
        return tee_section(
            d=_dimension(raw, "d", scale),
            b=_dimension(raw, "bf", scale),
            t_f=tf,
            t_w=_dimension(raw, "tw", scale),
            r=_us_root_radius(raw, tf, scale),
            n_r=n_r,
        )

    # Angles, long leg vertical; UK/EU root radius r_1 and toe radius r_2 (no larger than t), US root radius kdes - t
    if section_type in ANGLE_SECTION_TYPES:
        if us:
            legs: tuple[float, float] = (_dimension(raw, "d", scale), _dimension(raw, "b", scale))
            t: float = _dimension(raw, "t", scale)
            r_root: float = _us_root_radius(raw, t, scale)
            r_toe: float = 0.0
        else:
            legs = _size(raw, scale)
            t = _dimension(raw, "t", scale)
            r_root = (_positive(raw, "r_1") or 0.0) * scale
            r_toe = min((_positive(raw, "r_2") or 0.0) * scale, t) # a few EU rows give r_2 > t, e.g 45x45x3.0
        return angle_section(d=max(legs), b=min(legs), t=t, r_r=r_root, r_t=r_toe, n_r=n_r)

    # Rectangular and square hollow sections: EN 10210-2 r_o = 1.5t, r_i = t (hot finished); EN 10219-2 r_o by t
    # ... (cold formed); AISC r_o = 2t_des, on the design wall thickness t_des = 0.93t_nom (B4.2)
    if section_type in HOT_FINISHED_RHS_SECTION_TYPES or section_type in COLD_FORMED_RHS_SECTION_TYPES:
        h, b = _size(raw, scale)
        t = _dimension(raw, "t", scale)
        if section_type in HOT_FINISHED_RHS_SECTION_TYPES:
            return rectangular_hollow_section(d=h, b=b, t=t, r_out=1.5 * t, r_in=t, n_r=n_r)
        return rectangular_hollow_section(d=h, b=b, t=t, r_out=_cold_formed_corner_radius(t), n_r=n_r)
    if section_type in HSS_RECTANGULAR_SECTION_TYPES:
        t = _dimension(raw, "tdes", scale)
        return rectangular_hollow_section(d=_dimension(raw, "Ht", scale), b=_dimension(raw, "B", scale), t=t, r_out=2.0 * t, n_r=n_r)

    # Circular hollow sections; the UK tables give the outside diameter as d
    if section_type in CHS_SECTION_TYPES:
        if us:
            return circular_hollow_section(d=_dimension(raw, "OD", scale), t=_dimension(raw, "tdes", scale), n=8 * n_r)
        return circular_hollow_section(d=_dimension(raw, "d", scale), t=_dimension(raw, "t", scale), n=8 * n_r)

    # Elliptical hollow sections, major axis vertical
    if section_type in EHS_SECTION_TYPES:
        h, b = _size(raw, scale)
        return elliptical_hollow_section(d_x=b, d_y=h, t=_dimension(raw, "t", scale), n=8 * n_r)

    raise NotImplementedError(
        f"No geometry for {section_type.value} sections; tapered flanges (UPN, S, C, MC, ST), back-to-back angles, "
        "Sigma and Zed sections and the IN sections are not drawn yet. Pass a sectionproperties geometry to "
        "`analyse_section(geometry=...)`."
    )


# --- Analysis ---
def analyse_section(
    section: Optional[BaseSection] = None,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    geometry: Optional[Geometry | CompoundGeometry] = None,
    warping: bool = True,
    mesh_size: Optional[float] = None,
    n_r: int = N_R,
) -> SectionAnalysis:
    """Geometric, plastic and warping properties of a cross-section, by the finite element method.

    Args:
        section: Section from a regional module, e.g `UB("457x191x67")` or `W("W14X90")`
        section_type: Section type when passing plain properties
        properties: Plain dimensions, or overrides for the section's own, in section-table units
        region: "UK", "EU", "US" or "US_METRIC", for the keys and units of the dimensions; by default, the section's
        geometry: Any sectionproperties geometry in mm, e.g a built-up or welded section, instead of a tabulated one;
            it is meshed in place
        warping: Run the warping analysis for I_t, I_w and the shear centre; the slowest step
        mesh_size: Maximum element area (mm²); by default A/200
        n_r: Points on each root, toe or corner radius, for tabulated sections

    Returns:
        SectionAnalysis in mm units; `.to_properties(region)` gives them in section-table keys and units
    """
    designation: Optional[str] = section.designation if section is not None else None
    if geometry is None:
        geometry = section_geometry(section, section_type, properties, region, n_r)
        section_type = section.get_section_type() if section is not None else section_type
        if designation is None and properties is not None:
            designation = properties.get("designation")

    area: float = geometry.calculate_area()
    geometry.create_mesh(mesh_sizes=[mesh_size if mesh_size is not None else area / MESH_DIVISIONS])
    model: Section = Section(geometry=geometry)
    model.calculate_geometric_properties()
    model.calculate_plastic_properties()

    y_c, z_c = model.get_c()
    I_y, I_z, I_yz = model.get_ic()
    i_y, i_z = model.get_rc()
    z_y_top, z_y_bottom, z_z_right, z_z_left = model.get_z()
    I_u, I_v = model.get_ip()
    i_u, i_v = model.get_rp()
    W_pl_y, W_pl_z = model.get_s()

    I_t: Optional[float] = None
    I_w: Optional[float] = None
    y_s: Optional[float] = None
    z_s: Optional[float] = None
    i_0: Optional[float] = None
    if warping:
        model.calculate_warping_properties()
        x_se, y_se = model.get_sc() # from the origin of the geometry
        I_t = float(model.get_j())
        I_w = float(model.get_gamma())
        y_s = float(x_se - y_c)
        z_s = float(y_se - z_c)
        i_0 = math.sqrt(i_y**2 + i_z**2 + y_s**2 + z_s**2) # EN 1993-1-3 6.2.3; AISC 360-22 Eq. E4-9

    return SectionAnalysis(
        designation=designation,
        section_type=section_type,
        A=float(model.get_area()),
        y_c=float(y_c),
        z_c=float(z_c),
        I_y=float(I_y),
        I_z=float(I_z),
        I_yz=float(I_yz),
        i_y=float(i_y),
        i_z=float(i_z),
        W_el_y=float(min(z_y_top, z_y_bottom)),
        W_el_z=float(min(z_z_right, z_z_left)),
        I_u=float(I_u),
        I_v=float(I_v),
        i_u=float(i_u),
        i_v=float(i_v),
        alpha=float(model.get_phi()),
        W_pl_y=float(W_pl_y),
        W_pl_z=float(W_pl_z),
        I_t=I_t,
        I_w=I_w,
        y_s=y_s,
        z_s=z_s,
        i_0=i_0,
        mesh_elements=len(model.mesh["triangles"]),
        model=model,
    )


if __name__ == "__main__":
    from steelsnakes.EU import IPE

    ipe_300 = IPE("IPE-300")
    analysis: SectionAnalysis = analyse_section(ipe_300)
    print(analysis)
    print(analysis.to_properties("EU"))
    print({key: ipe_300.get_properties()[key] for key in analysis.to_properties("EU")})
    print("🐬")
