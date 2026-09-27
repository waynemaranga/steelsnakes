# E1. General Provisions
# E2. Effective Length
# E3. Flexural Buckling of Members Without Slender Elements
# E4. Torsional and Flexural-Torsional Buckling of Single Angles and Members Without Slender Elements
# E5. Single-Angle Compression Members
# E6. Built-Up Members
# E7. Members with Slender Elements
# User Note: for cases not included in this chapter, the following sections apply:
# • H1–H2 Members subjected to combined axial compression and flexure
# • H3 Members subjected to axial compression and torsion
# • I2 Composite axially loaded members
# • J4.4 Compressive strength of connecting elements
# NOTE: see selection table on User Note E1.1 (checks/tables): FB, TB, FTB and LB per cross section


from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal, Optional, Sequence

import numpy as np
from pydantic import BaseModel, Field, SerializeAsAny

from steelsnakes.base.checks import DesignCode, LimitState, Reference, SectionClass, UtilisationCheck, compute_utilisation
from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.US.checks.classification import (
    CHANNEL_SECTION_TYPES,
    I_SECTION_TYPES,
    RECT_HSS_SECTION_TYPES,
    ROUND_HSS_SECTION_TYPES,
    TEE_SECTION_TYPES,
    ClassificationContext,
    CompressionCase,
    _positive_value,
    _require_positive,
    _section_properties,
    classify_compression,
    classify_section_from_dict,
)

E_STEEL = 29000 # ksi [is 200_000 MPa in US_Metric module]
G_STEEL = 11200 # ksi [is 77_200 MPa in US_Metric module]
PHI_C = 0.90 # E1; LRFD
COMPRESSION_SLENDERNESS_LIMIT = 200 # User Note E2; Lc/r preferably should not exceed 200

SINGLE_ANGLE_SECTION_TYPES = (SectionType.L_EQUAL, SectionType.L_UNEQUAL)
DOUBLE_ANGLE_SECTION_TYPES = (SectionType.L2L_EQUAL, SectionType.L2L_LLBB, SectionType.L2L_SLBB)


class CompressionResult(BaseModel):
    # E1. General Provisions: Pn is lowest value from FB, TB and FTB
    phi_c: float = PHI_C # compression resistance factor
    Pn: float # nominal compressive strength, kips [N]
    phi_c_Pn: float # design compressive strength, kips [N]
    limit_state: LimitState # governing limit state
    # E2. Effective Length
    L: Optional[float] = None # laterally unbraced length, in [mm]
    Lc: Optional[float] = None # effective length, in [mm] = KL
    K: Optional[float] = None # effective length factor
    r: Optional[float] = None # radius of gyration, in [mm]

    # NOTE: limit Lc/r < 200 for compression members;
    # NOTE: fabricated L/r_min preferably < 300 (User Note E2)

    # E3. Flexural Buckling of Members Without Slender Elements
    # NOTE: only applies to nonslender-element compression members per B4.1 for elements in axial compression;
    # NOTE: when torsional eff. length > lateral eff. length, E4 governs
    Fn: float # nominal stress, ksi [MPa]
    Ag: float # gross area, in^2 [mm^2]
    Ae: Optional[float] = None # effective area, in^2 [mm^2]; per E7, equals Ag for nonslender-element members
    Fe: float # elastic buckling stress, ksi [MPa], per E3-4, Appendix 7.2.3(b) or through manual elastic buckling analysis
    Fy: float # specified minimum yield strength of the material, ksi [MPa]
    E: float = E_STEEL # modulus of elasticity, ksi [MPa]
    # NOTE: the inequalities Lc/r <= 4.71*sqrt(E/Fy) and Fy/Fe <= 2.25 give the same result for flexural buckling only; Fy/Fe is used for all modes

    # E4. Torsional and Flexural-Torsional Buckling of Single Angles and Members Without Slender Elements
    # E5. Single-Angle Compression Members
    # E6. Built-Up Members
    # E7. Members with Slender Elements
    section_class: Optional[SectionClass] = None # NONSLENDER_ELEMENT or SLENDER_ELEMENT per B4.1a
    checks: list[SerializeAsAny[CompressionResult]] = Field(default_factory=list) # every limit state evaluated by compression()
    reference: Optional[Reference] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- E2. Effective Length ---
def effective_length(K: float, L: float) -> float:
    """AISC 360-22 Section E2: Effective length, Lc = K*L.

    Args:
        K: Effective length factor, per Chapter C or Appendix 7
        L: Laterally unbraced length of the member (in)
    """
    return _require_positive(K, "K") * _require_positive(L, "L")


def check_compression_slenderness(Lc: float, r: float) -> UtilisationCheck:
    """AISC 360-22 Section E2 (User Note): Effective slenderness ratio, Lc/r, preferably should not exceed 200.

    Args:
        Lc: Effective length (in)
        r: Radius of gyration (in)
    """
    Lc_r = _require_positive(Lc, "Lc") / _require_positive(r, "r")
    utilisation = Lc_r / COMPRESSION_SLENDERNESS_LIMIT
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Lc_r": Lc_r, "limit": COMPRESSION_SLENDERNESS_LIMIT, "note": "Recommendation only."},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="E2", title="Effective length (User Note)"),
    )


# --- E3. Flexural Buckling of Members Without Slender Elements ---
def elastic_buckling_stress(Lc: float, r: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation E3-4: Elastic buckling stress, Fe = pi^2*E / (Lc/r)^2.

    Args:
        Lc: Effective length (in)
        r: Radius of gyration (in)
        E: Modulus of elasticity (ksi)
    """
    Lc_r = _require_positive(Lc, "Lc") / _require_positive(r, "r")
    return math.pi**2 * E / Lc_r**2


def nominal_stress(Fy: float, Fe: float) -> float:
    """AISC 360-22 Equations E3-2 and E3-3: Nominal stress, Fn.

    (a) Fy/Fe <= 2.25: Fn = 0.658^(Fy/Fe) * Fy (E3-2)
    (b) Fy/Fe > 2.25: Fn = 0.877*Fe (E3-3)

    Args:
        Fy: Specified minimum yield stress (ksi)
        Fe: Elastic buckling stress (ksi); flexural, torsional or flexural-torsional
    """
    ratio = _require_positive(Fy, "Fy") / _require_positive(Fe, "Fe")
    if ratio <= 2.25:
        return 0.658**ratio * Fy
    return 0.877 * Fe


class FlexurialBucklingResult(CompressionResult):
    # E3. Flexural Buckling of Members Without Slender Elements
    # NOTE: only applies to nonslender-element compression members per B4.1 for elements in axial compression;
    # NOTE: when torsional eff. length > lateral eff. length, E4 governs
    # Fn, Ag, Fe, Fy per CompressionResult
    axis: Optional[str] = None # buckling axis; "x", "y", or principal "w", "z" for single angles
    Lc_r: float # effective slenderness ratio
    # NOTE: # TODO: complete user note on inequalites calc. same value for ...


FlexuralBucklingResult = FlexurialBucklingResult # alias; correctly spelt


def check_flexural_buckling(
    Fy: float,
    Ag: float,
    r: float,
    L: Optional[float] = None,
    K: float = 1.0,
    Lc: Optional[float] = None,
    E: float = E_STEEL,
    axis: Optional[str] = None,
) -> FlexurialBucklingResult:
    """AISC 360-22 Section E3: Flexural buckling of members without slender elements, Pn = Fn*Ag (E3-1).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area (in²)
        r: Radius of gyration about the buckling axis (in)
        L: Laterally unbraced length (in); used with K if Lc is not given
        K: Effective length factor
        Lc: Effective length (in); overrides K*L
        E: Modulus of elasticity (ksi)
        axis: Label of the buckling axis, for reporting
    """
    if Lc is None:
        if L is None:
            raise ValueError("Provide either Lc or L (with K).")
        Lc = effective_length(K, L)
    Ag = _require_positive(Ag, "Ag")
    Fe = elastic_buckling_stress(Lc, r, E)
    Fn = nominal_stress(Fy, Fe)
    Pn = Fn * Ag
    return FlexurialBucklingResult(
        Pn=Pn,
        phi_c_Pn=PHI_C * Pn,
        limit_state=LimitState.FLEXURAL_BUCKLING,
        L=L,
        Lc=Lc,
        K=K if L is not None else None,
        r=r,
        Fn=Fn,
        Ag=Ag,
        Ae=Ag,
        Fe=Fe,
        Fy=Fy,
        E=E,
        axis=axis,
        Lc_r=Lc / r,
        reference=Reference(code=DesignCode.AISC_360, clause="E3", equation="E3-2" if Fy / Fe <= 2.25 else "E3-3", title="Flexural buckling of members without slender elements"),
        metadata={"Fy_Fe": Fy / Fe, "Lc_r_limit": 4.71 * math.sqrt(E / Fy)},
    )


# --- E4. Torsional and Flexural-Torsional Buckling ---
class TorsionalBucklingCase(str, Enum):
    """AISC 360-22 Section E4 elastic buckling stress cases, keyed by equation."""

    DOUBLY_SYMMETRIC = "E4-2" # (a) doubly symmetric members twisting about the shear center
    SINGLY_SYMMETRIC = "E4-3" # (b) singly symmetric members twisting about the shear center
    UNSYMMETRIC = "E4-4" # (c) unsymmetric members; lowest root of cubic
    MINOR_AXIS_BRACING_OFFSET = "E4-10" # (d) doubly symmetric I-shapes, minor-axis bracing offset from shear center
    MAJOR_AXIS_BRACING_OFFSET = "E4-12" # (e) doubly symmetric I-shapes, major-axis bracing offset from shear center

    @property
    def label(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        descriptions: dict[TorsionalBucklingCase, str] = {
            TorsionalBucklingCase.DOUBLY_SYMMETRIC: "Doubly symmetric members twisting about the shear center (torsional buckling)",
            TorsionalBucklingCase.SINGLY_SYMMETRIC: "Singly symmetric members twisting about the shear center (flexural-torsional buckling); y or x axis of symmetry",
            TorsionalBucklingCase.UNSYMMETRIC: "Unsymmetric members twisting about the shear center; lowest root of the cubic E4-4",
            TorsionalBucklingCase.MINOR_AXIS_BRACING_OFFSET: "Doubly symmetric I-shaped members with minor-axis lateral bracing offset from the shear center",
            TorsionalBucklingCase.MAJOR_AXIS_BRACING_OFFSET: "Doubly symmetric I-shaped members with major-axis lateral bracing offset from the shear center",
        }
        return descriptions[self]


def calculate_Fex(Lcx: float, rx: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation E4-5: Flexural buckling stress about the x-axis, Fex = pi^2*E / (Lcx/rx)^2."""
    return elastic_buckling_stress(Lcx, rx, E)


def calculate_Fey(Lcy: float, ry: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equation E4-6: Flexural buckling stress about the y-axis, Fey = pi^2*E / (Lcy/ry)^2."""
    return elastic_buckling_stress(Lcy, ry, E)


def calculate_Fez(Lcz: float, J: float, Ag: float, r0_bar: float, Cw: float = 0.0, E: float = E_STEEL, G: float = G_STEEL) -> float:
    """AISC 360-22 Equation E4-7: Torsional buckling stress, Fez = (pi^2*E*Cw/Lcz^2 + G*J) * 1/(Ag*r0_bar^2).

    Args:
        Lcz: Effective length for buckling about the longitudinal axis (in)
        J: Torsional constant (in⁴)
        Ag: Gross area (in²)
        r0_bar: Polar radius of gyration about the shear center (in)
        Cw: Warping constant (in⁶); may be omitted (0) for tees and double angles
        E: Modulus of elasticity (ksi)
        G: Shear modulus (ksi)
    """
    return (math.pi**2 * E * Cw / _require_positive(Lcz, "Lcz") ** 2 + G * J) / (_require_positive(Ag, "Ag") * _require_positive(r0_bar, "r0_bar") ** 2)


def calculate_H(x0: float, y0: float, r0_bar: float) -> float:
    """AISC 360-22 Equation E4-8: Flexural constant, H = 1 - (x0^2 + y0^2)/r0_bar^2."""
    return 1.0 - (x0**2 + y0**2) / _require_positive(r0_bar, "r0_bar") ** 2


def calculate_r0_bar2(x0: float, y0: float, Ix: float, Iy: float, Ag: float) -> float:
    """AISC 360-22 Equation E4-9: Square of the polar radius of gyration about the shear center, x0^2 + y0^2 + (Ix + Iy)/Ag."""
    return x0**2 + y0**2 + (Ix + Iy) / _require_positive(Ag, "Ag")


def calculate_r02_bracing_offset(rx: float, ry: float, xa: float = 0.0, ya: float = 0.0) -> float:
    """AISC 360-22 Equation E4-11: ro^2 = rx^2 + ry^2 + xa^2 + ya^2 for bracing offset from the shear center."""
    return rx**2 + ry**2 + xa**2 + ya**2


def _lowest_cubic_root(Fex: float, Fey: float, Fez: float, x0: float, y0: float, r0_bar: float) -> float:
    # E4-4: (Fe - Fex)(Fe - Fey)(Fe - Fez) - Fe^2(Fe - Fey)(x0/r0)^2 - Fe^2(Fe - Fex)(y0/r0)^2 = 0, expanded in powers of Fe
    a = (x0 / r0_bar) ** 2
    b = (y0 / r0_bar) ** 2
    coefficients = [
        1.0 - a - b,
        -(Fex + Fey + Fez) + a * Fey + b * Fex,
        Fex * Fey + Fex * Fez + Fey * Fez,
        -Fex * Fey * Fez,
    ]
    roots = [float(root.real) for root in np.roots(coefficients) if abs(root.imag) <= 1e-9 * max(1.0, abs(root.real)) and root.real > 0.0]
    if not roots:
        raise ValueError("Equation E4-4 has no positive real root; check the section properties.")
    return min(roots)


class TorsionalBucklingResult(CompressionResult):
    # E4. Torsional and Flexural-Torsional Buckling of Single Angles and Members Without Slender Elements
    case: TorsionalBucklingCase # equation used for Fe
    Cw: Optional[float] = None   # warping constant, in^6 [mm^6]; # NOTE: may be Iy*h0^2/4 for I-sections; # NOTE: term with Cw may be omitted for tees and double angles
    Fex: Optional[float] = None  # flexural buckling stress about x-axis, ksi [MPa]; per E4-5
    Fey: Optional[float] = None  # flexural buckling stress about y-axis, ksi [MPa]; per E4-6
    Fez: Optional[float] = None  # torsional buckling stress, ksi [MPa]; per E4-7
    H: Optional[float] = None    # flexural constant; per E4-8
    Ix: Optional[float] = None   # moment of inertia about x-axis, in^4 [mm^4]
    Iy: Optional[float] = None   # moment of inertia about y-axis, in^4 [mm^4]
    J: Optional[float] = None    # torsional constant, in^4 [mm^4]
    Lx: Optional[float] = None   # laterally unbraced length for x-axis, in [mm]
    Ly: Optional[float] = None   # laterally unbraced length for y-axis, in [mm]
    Lz: Optional[float] = None   # laterally unbraced length for longitudinal axis, in [mm]
    Kx: Optional[float] = None   # effective length factor for flexural buckling about x-axis
    Ky: Optional[float] = None   # effective length factor for flexural buckling about y-axis
    Kz: Optional[float] = None   # effective length factor for torsional buckling about longitudinal (z-z) axis
    Lcx: Optional[float] = None  # effective length for buckling about x-axis, in [mm] - Kx*Lx
    Lcy: Optional[float] = None  # effective length for buckling about y-axis, in [mm] - Ky*Ly
    Lcz: Optional[float] = None  # effective length for buckling about longitudinal axis, in [mm] - Kz*Lz
    rx: Optional[float] = None   # radius of gyration about x-axis, in [mm]
    ry: Optional[float] = None   # radius of gyration about y-axis, in [mm]
    x0_y0: Optional[tuple[float, float]] = None # coordinates of shear center wrt centroid, (in, in) [mm, mm]
    r0_bar: Optional[float] = None # polar radius of gyration about shear center, in [mm]
    r0_bar2: Optional[float] = None # ; per E4-9
    # h0: Optional[float] # distance between flange centroids for I-sections, in [mm]; may be used to calculate Cw
    h0: Optional[float] = None   # distance between flange centroids for I-sections, in [mm]; may be used to calculate Cw
    # Fe: float   # ; per E4-10 # NOTE: Fe on CompressionResult
    r02: Optional[float] = None  # ; per E4-11
    xa: float = 0   # bracing offset distance along x-axis, in. (mm)
    ya: float = 0 # bracing offset distance along y-axis, in. (mm)


def check_torsional_buckling(
    case: TorsionalBucklingCase | str,
    Fy: float,
    Ag: float,
    J: float,
    Lz: float,
    Kz: float = 1.0,
    Cw: float = 0.0,
    Ix: Optional[float] = None,
    Iy: Optional[float] = None,
    rx: Optional[float] = None,
    ry: Optional[float] = None,
    Lx: Optional[float] = None,
    Ly: Optional[float] = None,
    Kx: float = 1.0,
    Ky: float = 1.0,
    x0: float = 0.0,
    y0: float = 0.0,
    r0_bar: Optional[float] = None,
    h0: Optional[float] = None,
    xa: float = 0.0,
    ya: float = 0.0,
    axis_of_symmetry: Literal["x", "y"] = "y",
    Fex: Optional[float] = None,
    Fey: Optional[float] = None,
    E: float = E_STEEL,
    G: float = G_STEEL,
) -> TorsionalBucklingResult:
    """AISC 360-22 Section E4: Torsional and flexural-torsional buckling, Pn = Fn*Ag (E4-1).

    Fn is determined by E3-2 or E3-3 using the torsional or flexural-torsional elastic buckling stress, Fe:
        E4-2: doubly symmetric; Fe = (pi^2*E*Cw/Lcz^2 + G*J) * 1/(Ix + Iy)
        E4-3: singly symmetric; Fe = (Fey + Fez)/2H * [1 - sqrt(1 - 4*Fey*Fez*H/(Fey + Fez)^2)]; Fex replaces Fey for x-axis symmetry (channels)
        E4-4: unsymmetric; lowest root of the cubic
        E4-10: doubly symmetric I-shapes with minor-axis bracing offset ya; Fe = [pi^2*E*Iy/Lcz^2*(h0^2/4 + ya^2) + G*J] * 1/(Ag*ro^2)
        E4-12: doubly symmetric I-shapes with major-axis bracing offset xa; Fe = [pi^2*E*Iy/Lcz^2*(h0^2/4 + Ix/Iy*xa^2) + G*J] * 1/(Ag*ro^2)

    Args:
        case: TorsionalBucklingCase or its equation string e.g "E4-2"
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area (in²)
        J: Torsional constant (in⁴)
        Lz, Kz: Unbraced length (in) and effective length factor for torsional buckling
        Cw: Warping constant (in⁶)
        Ix, Iy: Moments of inertia about the principal axes (in⁴)
        rx, ry: Radii of gyration (in)
        Lx, Ly, Kx, Ky: Unbraced lengths (in) and effective length factors for flexural buckling
        x0, y0: Shear center coordinates with respect to the centroid (in)
        r0_bar: Polar radius of gyration about the shear center (in); computed from E4-9 if not given
        h0: Distance between flange centroids (in); E4-10 and E4-12
        xa, ya: Bracing offset distances (in); E4-12 and E4-10
        axis_of_symmetry: "y" (tees, double angles) or "x" (channels); E4-3
        Fex, Fey: Flexural buckling stresses (ksi); override E4-5/E4-6 e.g for E6 modified slenderness or principal axes of angles
        E: Modulus of elasticity (ksi)
        G: Shear modulus (ksi)
    """
    try:
        case_key = case if isinstance(case, TorsionalBucklingCase) else TorsionalBucklingCase(case.strip().upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in TorsionalBucklingCase)
        raise ValueError(f"Invalid case '{case}'. Expected one of: {allowed}.") from exc

    Ag = _require_positive(Ag, "Ag")
    J = _require_positive(J, "J")
    Lcz = effective_length(Kz, Lz)
    Lcx = Kx * Lx if Lx is not None else None
    Lcy = Ky * Ly if Ly is not None else None
    Fex_value = Fex if Fex is not None else (calculate_Fex(Lcx, rx, E) if Lcx is not None and rx else None)
    Fey_value = Fey if Fey is not None else (calculate_Fey(Lcy, ry, E) if Lcy is not None and ry else None)

    r0_bar2: Optional[float] = None
    r02: Optional[float] = None
    Fez: Optional[float] = None
    H: Optional[float] = None
    limit_state = LimitState.TORSIONAL_FLEXURAL_BUCKLING

    match case_key:
        case TorsionalBucklingCase.DOUBLY_SYMMETRIC:
            Ix = _require_positive(Ix, "Ix")
            Iy = _require_positive(Iy, "Iy")
            Fe = (math.pi**2 * E * Cw / Lcz**2 + G * J) / (Ix + Iy) # E4-2
            limit_state = LimitState.TORSIONAL_BUCKLING
        case TorsionalBucklingCase.SINGLY_SYMMETRIC | TorsionalBucklingCase.UNSYMMETRIC:
            if r0_bar is None:
                r0_bar2 = calculate_r0_bar2(x0, y0, _require_positive(Ix, "Ix"), _require_positive(Iy, "Iy"), Ag)
                r0_bar = math.sqrt(r0_bar2)
            else:
                r0_bar2 = r0_bar**2
            H = calculate_H(x0, y0, r0_bar)
            Fez = calculate_Fez(Lcz, J, Ag, r0_bar, Cw, E, G)
            if case_key == TorsionalBucklingCase.SINGLY_SYMMETRIC:
                # NOTE: For singly symmetric members with the x-axis as the axis of symmetry, such as channels, E4-3 is applicable with Fey replaced by Fex.
                Fe_flexural = Fey_value if axis_of_symmetry == "y" else Fex_value
                Fe_flexural = _require_positive(Fe_flexural, f"Fe{axis_of_symmetry} (or r{axis_of_symmetry} and L{axis_of_symmetry})")
                Fe = (Fe_flexural + Fez) / (2.0 * H) * (1.0 - math.sqrt(1.0 - 4.0 * Fe_flexural * Fez * H / (Fe_flexural + Fez) ** 2)) # E4-3
            else:
                Fe = _lowest_cubic_root(
                    _require_positive(Fex_value, "Fex (or rx and Lx)"),
                    _require_positive(Fey_value, "Fey (or ry and Ly)"),
                    Fez,
                    x0,
                    y0,
                    r0_bar,
                ) # E4-4
        case TorsionalBucklingCase.MINOR_AXIS_BRACING_OFFSET | TorsionalBucklingCase.MAJOR_AXIS_BRACING_OFFSET:
            Ix = _require_positive(Ix, "Ix")
            Iy = _require_positive(Iy, "Iy")
            h0 = _require_positive(h0, "h0")
            rx = rx if rx else math.sqrt(Ix / Ag)
            ry = ry if ry else math.sqrt(Iy / Ag)
            if case_key == TorsionalBucklingCase.MINOR_AXIS_BRACING_OFFSET:
                xa = 0.0 # xa = 0 for E4-10
                offset_term = ya**2
            else:
                ya = 0.0 # ya = 0 for E4-12
                offset_term = Ix / Iy * xa**2
            r02 = calculate_r02_bracing_offset(rx, ry, xa, ya) # E4-11
            Fe = (math.pi**2 * E * Iy / Lcz**2 * (h0**2 / 4.0 + offset_term) + G * J) / (Ag * r02) # E4-10 / E4-12
            limit_state = LimitState.TORSIONAL_BUCKLING
        case _:
            raise NotImplementedError(f"Torsional buckling case '{case_key.value}' is not implemented.")

    Fn = nominal_stress(Fy, Fe)
    Pn = Fn * Ag
    return TorsionalBucklingResult(
        Pn=Pn,
        phi_c_Pn=PHI_C * Pn,
        limit_state=limit_state,
        Lc=Lcz,
        K=Kz,
        L=Lz,
        Fn=Fn,
        Ag=Ag,
        Ae=Ag,
        Fe=Fe,
        Fy=Fy,
        E=E,
        case=case_key,
        Cw=Cw,
        Fex=Fex_value,
        Fey=Fey_value,
        Fez=Fez,
        H=H,
        Ix=Ix,
        Iy=Iy,
        J=J,
        Lx=Lx,
        Ly=Ly,
        Lz=Lz,
        Kx=Kx,
        Ky=Ky,
        Kz=Kz,
        Lcx=Lcx,
        Lcy=Lcy,
        Lcz=Lcz,
        rx=rx,
        ry=ry,
        x0_y0=(x0, y0),
        r0_bar=r0_bar,
        r0_bar2=r0_bar2,
        h0=h0,
        r02=r02,
        xa=xa,
        ya=ya,
        reference=Reference(code=DesignCode.AISC_360, clause="E4", equation=case_key.value, title="Torsional and flexural-torsional buckling"),
        metadata={"Fy_Fe": Fy / Fe, "axis_of_symmetry": axis_of_symmetry if case_key == TorsionalBucklingCase.SINGLY_SYMMETRIC else None},
    )


# --- E5. Single-Angle Compression Members ---
class SingleAngleCompressionResult(CompressionResult):
    # E5. Single-Angle Compression Members: Pn is lowest value of FB per E3 or E7, or FTB per E4;
    # NOTE: No need for FTB check if b/t <= 0.71*(E/Fy)^0.5
    # NOTE: Requirements to ignore eccentricity per E5: (1) loaded at the ends through the same one leg; (2) welded or >= 2 bolts;
    # ... (3) no intermediate transverse loads; (4) Lc/r per E5 <= 200; (5) unequal legs, bl/bs < 1.7
    # NOTE: if not as above, check for combined axial & flexure per H.
    # L: laterally unbraced length, in [mm]; length between work points at truss chord centerlines
    # Lc: effective length for buckling about the minor axis, in [mm] = KL
    # r: radius of gyration, in [mm]; taken as ra
    bl: float # longer leg length, in [mm]
    bs: float # shorter leg length, in [mm]
    ra: float # radius of gyration about axis parallel to connected leg, in [mm]
    rz: float # radius of gyration about the minor principal axis, in [mm]
    Lc_r: float # effective slenderness ratio per E5-1 to E5-4
    connected_leg: Literal["long", "short"] = "long"
    truss: Literal["planar", "box"] = "planar" # (a) individual members / planar truss webs, (b) box or space truss webs
    equation: str # E5-1, E5-2, E5-3 or E5-4


def calculate_single_angle_slenderness(
    L: float,
    ra: float,
    rz: float,
    bl: float,
    bs: float,
    connected_leg: Literal["long", "short"] = "long",
    truss: Literal["planar", "box"] = "planar",
) -> tuple[float, str]:
    """AISC 360-22 Section E5: Effective slenderness ratio, Lc/r, of single angles loaded through one leg.

    (a) individual members or webs of planar trusses: E5-1 (L/ra <= 80) or E5-2 (L/ra > 80);
        connected through the shorter leg: + 4[(bl/bs)^2 - 1], but not less than 0.95 L/rz
    (b) webs of box or space trusses: E5-3 (L/ra <= 75) or E5-4 (L/ra > 75);
        connected through the shorter leg: + 6[(bl/bs)^2 - 1], but not less than 0.82 L/rz

    Returns:
        (Lc/r, equation)
    """
    L_ra = _require_positive(L, "L") / _require_positive(ra, "ra")
    L_rz = L / _require_positive(rz, "rz")
    ratio = _require_positive(bl, "bl") / _require_positive(bs, "bs")
    short_leg = connected_leg == "short" and ratio > 1.0

    match truss:
        case "planar":
            Lc_r, equation = (72.0 + 0.75 * L_ra, "E5-1") if L_ra <= 80.0 else (32.0 + 1.25 * L_ra, "E5-2")
            if short_leg:
                Lc_r = max(Lc_r + 4.0 * (ratio**2 - 1.0), 0.95 * L_rz)
        case "box":
            Lc_r, equation = (60.0 + 0.8 * L_ra, "E5-3") if L_ra <= 75.0 else (45.0 + L_ra, "E5-4")
            if short_leg:
                Lc_r = max(Lc_r + 6.0 * (ratio**2 - 1.0), 0.82 * L_rz)
        case _:
            raise ValueError("truss must be 'planar' (E5(a)) or 'box' (E5(b)).")
    return Lc_r, equation


def check_single_angle_compression(
    Fy: float,
    Ag: float,
    L: float,
    ra: float,
    rz: float,
    bl: float,
    bs: float,
    t: float,
    connected_leg: Literal["long", "short"] = "long",
    truss: Literal["planar", "box"] = "planar",
    E: float = E_STEEL,
) -> SingleAngleCompressionResult:
    """AISC 360-22 Section E5: Single-angle compression members loaded through one leg, as axially loaded members.

    Flexural buckling per E3 (or E7 for slender legs) using the effective slenderness ratio of E5-1 to E5-4.
    Flexural-torsional buckling per E4 must also be considered when b/t > 0.71*sqrt(E/Fy); see compression().

    Args:
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area (in²)
        L: Length of member between work points at truss chord centerlines (in)
        ra: Radius of gyration about the geometric axis parallel to the connected leg (in)
        rz: Radius of gyration about the minor principal axis (in)
        bl, bs: Longer and shorter leg lengths (in)
        t: Leg thickness (in)
        connected_leg: "long" or "short"; equal-leg angles are treated as "long"
        truss: "planar" (E5(a)) or "box" (E5(b))
        E: Modulus of elasticity (ksi)
    """
    if bl < bs:
        bl, bs = bs, bl
    if bl / bs >= 1.7:
        raise ValueError("E5 requires bl/bs < 1.7 for unequal-leg angles; evaluate for combined axial load and flexure per Chapter H.")
    Lc_r, equation = calculate_single_angle_slenderness(L, ra, rz, bl, bs, connected_leg, truss)
    if Lc_r > COMPRESSION_SLENDERNESS_LIMIT:
        raise ValueError(f"E5 requires Lc/r <= 200 (Lc/r = {Lc_r:.1f}); evaluate for combined axial load and flexure per Chapter H.")

    Ag = _require_positive(Ag, "Ag")
    Fe = math.pi**2 * E / Lc_r**2
    Fn = nominal_stress(Fy, Fe)
    elements = [
        SlenderElementInput(name="long_leg", b=bl, t=t, lambda_r=0.45 * math.sqrt(E / Fy), case=EffectiveWidthCase.OTHER),
        SlenderElementInput(name="short_leg", b=bs, t=t, lambda_r=0.45 * math.sqrt(E / Fy), case=EffectiveWidthCase.OTHER),
    ]
    Ae, widths = _effective_area_from_elements(Fn, Ag, elements, Fy)
    Pn = Fn * Ae
    return SingleAngleCompressionResult(
        Pn=Pn,
        phi_c_Pn=PHI_C * Pn,
        limit_state=LimitState.FLEXURAL_BUCKLING,
        L=L,
        Lc=Lc_r * ra,
        r=ra,
        Fn=Fn,
        Ag=Ag,
        Ae=Ae,
        Fe=Fe,
        Fy=Fy,
        E=E,
        bl=bl,
        bs=bs,
        ra=ra,
        rz=rz,
        Lc_r=Lc_r,
        connected_leg=connected_leg,
        truss=truss,
        equation=equation,
        reference=Reference(code=DesignCode.AISC_360, clause="E5", equation=equation, title="Single-angle compression members"),
        metadata={
            "L_ra": L / ra,
            "effective_widths": widths,
            "ftb_required": bl / t > 0.71 * math.sqrt(E / Fy), # E4 applies to single angles with b/t > 0.71*sqrt(E/Fy)
        },
    )


# --- E6. Built-Up Members ---
BUILT_UP_Ki: dict[str, float] = {
    "angles": 0.50, # angles back-to-back
    "channels": 0.75, # channels back-to-back
    "other": 0.86, # all other cases
}


class BuiltUpCompressionResult(CompressionResult):
    # E6. Built-Up Members
    # NOTE: built-up members are classified as either flexural buckling or torsional buckling per E3 and E4, respectively;
    # NOTE: for built-up members with slender elements, E7 governs
    Lc_r_o: float # slenderness ratio of built-up member acting as a unit in the buckling direction being addressed
    Lc_r_m: float # modified slenderness ratio of built-up member; per E6-1, E6-2a or E6-2b
    a: float # distance between connectors, in [mm]
    ri: float # minimum radius of gyration of individual component, in [mm]
    Ki: float # 0.50 angles back-to-back, 0.75 channels back-to-back, 0.86 all other cases
    connectors: Literal["snug_tight", "welded", "pretensioned"] = "welded"


def calculate_modified_slenderness(
    Lc_r_o: float,
    a: float,
    ri: float,
    connectors: Literal["snug_tight", "welded", "pretensioned"] = "welded",
    Ki: float = BUILT_UP_Ki["other"],
) -> tuple[float, str]:
    """AISC 360-22 Section E6.1: Modified slenderness ratio, (Lc/r)m, of built-up members.

    (a) snug-tight bolted intermediate connectors: (Lc/r)m = sqrt((Lc/r)o^2 + (a/ri)^2) (E6-1)
    (b) welded or pretensioned (Class A or B) intermediate connectors:
        a/ri <= 40: (Lc/r)m = (Lc/r)o (E6-2a)
        a/ri > 40: (Lc/r)m = sqrt((Lc/r)o^2 + (Ki*a/ri)^2) (E6-2b)

    Returns:
        ((Lc/r)m, equation)
    """
    a_ri = _require_positive(a, "a") / _require_positive(ri, "ri")
    match connectors:
        case "snug_tight":
            return math.sqrt(Lc_r_o**2 + a_ri**2), "E6-1"
        case "welded" | "pretensioned":
            if a_ri <= 40.0:
                return Lc_r_o, "E6-2a"
            return math.sqrt(Lc_r_o**2 + (Ki * a_ri) ** 2), "E6-2b"
        case _:
            raise ValueError("connectors must be 'snug_tight', 'welded' or 'pretensioned'.")


def check_built_up_compression(
    Fy: float,
    Ag: float,
    Lc: float,
    r: float,
    a: float,
    ri: float,
    connectors: Literal["snug_tight", "welded", "pretensioned"] = "welded",
    components: Literal["angles", "channels", "other"] = "other",
    E: float = E_STEEL,
) -> BuiltUpCompressionResult:
    """AISC 360-22 Section E6: Flexural buckling of built-up members of two shapes interconnected by bolts or welds.

    For buckling modes that produce shear forces in the connectors, Lc/r is replaced by (Lc/r)m per E6-1, E6-2a or E6-2b.

    Args:
        Fy: Specified minimum yield stress (ksi)
        Ag: Gross area of the built-up member (in²)
        Lc: Effective length of the built-up member (in)
        r: Radius of gyration of the built-up member acting as a unit (in)
        a: Distance between connectors (in)
        ri: Minimum radius of gyration of an individual component (in)
        connectors: "snug_tight", "welded" or "pretensioned"
        components: "angles" (back-to-back), "channels" (back-to-back) or "other"; sets Ki
        E: Modulus of elasticity (ksi)
    """
    Ki = BUILT_UP_Ki[components]
    Lc_r_o = _require_positive(Lc, "Lc") / _require_positive(r, "r")
    Lc_r_m, equation = calculate_modified_slenderness(Lc_r_o, a, ri, connectors, Ki)
    Ag = _require_positive(Ag, "Ag")
    Fe = math.pi**2 * E / Lc_r_m**2
    Fn = nominal_stress(Fy, Fe)
    Pn = Fn * Ag
    return BuiltUpCompressionResult(
        Pn=Pn,
        phi_c_Pn=PHI_C * Pn,
        limit_state=LimitState.FLEXURAL_BUCKLING,
        Lc=Lc,
        r=r,
        Fn=Fn,
        Ag=Ag,
        Ae=Ag,
        Fe=Fe,
        Fy=Fy,
        E=E,
        Lc_r_o=Lc_r_o,
        Lc_r_m=Lc_r_m,
        a=a,
        ri=ri,
        Ki=Ki,
        connectors=connectors,
        reference=Reference(code=DesignCode.AISC_360, clause="E6", equation=equation, title="Built-up members"),
        metadata={
            "a_ri": a / ri,
            # E6.2(a): a/ri of each component between fasteners <= 3/4 of the governing slenderness ratio of the built-up member
            "E6.2(a)_ok": a / ri <= 0.75 * Lc_r_m,
        },
    )


# --- E7. Members with Slender Elements ---
class EffectiveWidthCase(str, Enum):
    """AISC 360-22 Table E7.1: Effective width imperfection adjustment factors, c1 and c2."""

    STIFFENED = "a" # stiffened elements except walls of square and rectangular HSS
    HSS_WALL = "b" # walls of square and rectangular HSS
    OTHER = "c" # all other elements

    @property
    def c1(self) -> float:
        return {EffectiveWidthCase.STIFFENED: 0.18, EffectiveWidthCase.HSS_WALL: 0.20, EffectiveWidthCase.OTHER: 0.22}[self]

    @property
    def c2(self) -> float:
        return {EffectiveWidthCase.STIFFENED: 1.31, EffectiveWidthCase.HSS_WALL: 1.38, EffectiveWidthCase.OTHER: 1.49}[self]


class SlenderElementInput(BaseModel):
    """One element for the AISC 360-22 Section E7.1 effective width reduction; lambda = b/t."""

    name: str
    b: float = Field(gt=0.0) # width of the element (for tees this is d; for webs this is h), in [mm]
    t: float = Field(gt=0.0) # thickness of the element, in [mm]
    lambda_r: float = Field(gt=0.0) # limiting width-to-thickness ratio per Table B4.1a
    case: EffectiveWidthCase = EffectiveWidthCase.OTHER # Table E7.1 case
    count: int = Field(default=1, ge=1) # number of identical elements in the cross section


def calculate_c2(c1: float) -> float:
    """AISC 360-22 Equation E7-4: c2 = (1 - sqrt(1 - 4*c1)) / (2*c1)."""
    return (1.0 - math.sqrt(1.0 - 4.0 * c1)) / (2.0 * c1)


def elastic_local_buckling_stress(lambda_: float, lambda_r: float, Fy: float, c2: float) -> float:
    """AISC 360-22 Equation E7-5: Elastic local buckling stress, Fel = (c2*lambda_r/lambda)^2 * Fy."""
    return (c2 * lambda_r / _require_positive(lambda_, "lambda")) ** 2 * Fy


def effective_width(b: float, lambda_: float, lambda_r: float, Fy: float, Fn: float, case: EffectiveWidthCase = EffectiveWidthCase.OTHER) -> float:
    """AISC 360-22 Equations E7-2 and E7-3: Effective width, be (de for tees, he for webs).

    (a) lambda <= lambda_r*sqrt(Fy/Fn): be = b (E7-2)
    (b) lambda > lambda_r*sqrt(Fy/Fn): be = b*(1 - c1*sqrt(Fel/Fn))*sqrt(Fel/Fn) (E7-3)

    Args:
        b: Width of the element (in)
        lambda_: Width-to-thickness ratio for the element as defined in Section B4.1
        lambda_r: Limiting width-to-thickness ratio as defined in Table B4.1a
        Fy: Specified minimum yield stress (ksi)
        Fn: Nominal stress per E3 or E4 (ksi)
        case: Table E7.1 case
    """
    Fn = _require_positive(Fn, "Fn")
    if lambda_ <= lambda_r * math.sqrt(Fy / Fn):
        return b # E7-2
    Fel = elastic_local_buckling_stress(lambda_, lambda_r, Fy, case.c2)
    return b * (1.0 - case.c1 * math.sqrt(Fel / Fn)) * math.sqrt(Fel / Fn) # E7-3


def round_hss_effective_area(D: float, t: float, Ag: float, Fy: float, E: float = E_STEEL) -> float:
    """AISC 360-22 Equations E7-6 and E7-7: Effective area, Ae, of round HSS.

    (a) D/t <= 0.11*E/Fy: Ae = Ag (E7-6)
    (b) 0.11*E/Fy < D/t < 0.45*E/Fy: Ae = [0.038*E/(Fy*(D/t)) + 2/3]*Ag (E7-7)
    """
    D_t = _require_positive(D, "D") / _require_positive(t, "t")
    if D_t <= 0.11 * E / Fy:
        return Ag
    if D_t < 0.45 * E / Fy:
        return (0.038 * E / (Fy * D_t) + 2.0 / 3.0) * Ag
    raise ValueError(f"Round HSS with D/t = {D_t:.1f} >= 0.45E/Fy are not covered by E7.2.")


def _effective_area_from_elements(Fn: float, Ag: float, elements: Sequence[SlenderElementInput], Fy: float) -> tuple[float, dict[str, float]]:
    # NOTE: Ae may be determined by deducting from Ag the reduction in area of each slender element, (b - be)*t.
    Ae = Ag
    widths: dict[str, float] = {}
    for element in elements:
        be = effective_width(element.b, element.b / element.t, element.lambda_r, Fy, Fn, element.case)
        widths[element.name] = be
        Ae -= element.count * (element.b - be) * element.t
    return Ae, widths


class SlenderElementCompressionResult(CompressionResult):
    # E7. Members with Slender Elements
    # Pn: nominal compressive strength, kips [N]; lowest value from FB, TB, FTB in interaction with local buckling (E7-1)
    # Fn: nominal stress, ksi [MPa]; per E3 or E4; for single angles per E3 only;
    # Ae: effective area, in^2 [mm^2]; summation of effective areas based on be, de or he, or per E7-6 / E7-7
    effective_widths: dict[str, float] = Field(default_factory=dict) # be, de or he per element, in [mm]


def check_slender_element_compression(
    Fy: float,
    Fn: float,
    Ag: float,
    elements: Optional[Sequence[SlenderElementInput]] = None,
    D: Optional[float] = None,
    t: Optional[float] = None,
    Fe: Optional[float] = None,
    limit_state: LimitState = LimitState.FLEXURAL_BUCKLING,
    E: float = E_STEEL,
) -> SlenderElementCompressionResult:
    """AISC 360-22 Section E7: Members with slender elements, Pn = Fn*Ae (E7-1).

    Provide `elements` for E7.1 (members excluding round HSS), or D and t for E7.2 (round HSS).

    Args:
        Fy: Specified minimum yield stress (ksi)
        Fn: Nominal stress per E3 or E4 (ksi)
        Ag: Gross area (in²)
        elements: Elements of the cross section, see SlenderElementInput
        D, t: Outside diameter and design wall thickness of round HSS (in)
        Fe: Elastic buckling stress used for Fn (ksi); for reporting
        limit_state: Global buckling limit state interacting with local buckling
        E: Modulus of elasticity (ksi)
    """
    Ag = _require_positive(Ag, "Ag")
    if D is not None and t is not None:
        Ae = round_hss_effective_area(D, t, Ag, Fy, E)
        widths: dict[str, float] = {}
        equation = "E7-7" if Ae < Ag else "E7-6"
    elif elements is not None:
        Ae, widths = _effective_area_from_elements(Fn, Ag, elements, Fy)
        equation = "E7-3" if Ae < Ag else "E7-2"
    else:
        raise ValueError("Provide either 'elements' (E7.1) or 'D' and 't' (E7.2).")

    Pn = Fn * Ae
    return SlenderElementCompressionResult(
        Pn=Pn,
        phi_c_Pn=PHI_C * Pn,
        limit_state=limit_state,
        Fn=Fn,
        Ag=Ag,
        Ae=Ae,
        Fe=Fe if Fe is not None else Fn,
        Fy=Fy,
        E=E,
        effective_widths=widths,
        reference=Reference(code=DesignCode.AISC_360, clause="E7", equation=equation, title="Members with slender elements"),
    )


# --- Section adapters for compression() ---
def _slender_elements(section_type: SectionType, data: dict[str, Any], Fy: float, E: float) -> list[SlenderElementInput]:
    """Plate elements of standard shapes for the E7.1 effective area; lambda = b/t with limits from Table B4.1a."""

    def _lambda_r(case: CompressionCase) -> float:
        return float(classify_compression(case, E=E, Fy=Fy, wttr=1.0).metadata["lambda_r"])

    if section_type in I_SECTION_TYPES:
        tw = _require_positive(_positive_value(data, "tw"), "tw")
        tf = _require_positive(_positive_value(data, "tf"), "tf")
        h = _require_positive(_positive_value(data, "h_tw"), "h_tw") * tw
        return [
            SlenderElementInput(name="web", b=h, t=tw, lambda_r=_lambda_r(CompressionCase.CASE_5), case=EffectiveWidthCase.STIFFENED),
            SlenderElementInput(name="flange", b=_positive_value(data, "bf") / 2.0, t=tf, lambda_r=_lambda_r(CompressionCase.CASE_1), case=EffectiveWidthCase.OTHER, count=4),
        ]
    if section_type in CHANNEL_SECTION_TYPES:
        tw = _require_positive(_positive_value(data, "tw"), "tw")
        tf = _require_positive(_positive_value(data, "tf"), "tf")
        h = _require_positive(_positive_value(data, "h_tw"), "h_tw") * tw
        return [
            SlenderElementInput(name="web", b=h, t=tw, lambda_r=_lambda_r(CompressionCase.CASE_5), case=EffectiveWidthCase.STIFFENED),
            SlenderElementInput(name="flange", b=_positive_value(data, "bf"), t=tf, lambda_r=_lambda_r(CompressionCase.CASE_1), case=EffectiveWidthCase.OTHER, count=2),
        ]
    if section_type in TEE_SECTION_TYPES:
        tw = _require_positive(_positive_value(data, "tw"), "tw")
        tf = _require_positive(_positive_value(data, "tf"), "tf")
        return [
            SlenderElementInput(name="stem", b=_positive_value(data, "d"), t=tw, lambda_r=_lambda_r(CompressionCase.CASE_4), case=EffectiveWidthCase.OTHER),
            SlenderElementInput(name="flange", b=_positive_value(data, "bf") / 2.0, t=tf, lambda_r=_lambda_r(CompressionCase.CASE_1), case=EffectiveWidthCase.OTHER, count=2),
        ]
    if section_type in RECT_HSS_SECTION_TYPES:
        t = _require_positive(_positive_value(data, "tdes", "tnom"), "tdes")
        h = _positive_value(data, "h_tdes") * t or _positive_value(data, "h")
        b = _positive_value(data, "b_tdes") * t or _positive_value(data, "b")
        return [
            SlenderElementInput(name="web", b=_require_positive(h, "h"), t=t, lambda_r=_lambda_r(CompressionCase.CASE_6), case=EffectiveWidthCase.HSS_WALL, count=2),
            SlenderElementInput(name="flange", b=_require_positive(b, "b"), t=t, lambda_r=_lambda_r(CompressionCase.CASE_6), case=EffectiveWidthCase.HSS_WALL, count=2),
        ]
    if section_type in SINGLE_ANGLE_SECTION_TYPES or section_type in DOUBLE_ANGLE_SECTION_TYPES:
        t = _require_positive(_positive_value(data, "t"), "t")
        count = 2 if section_type in DOUBLE_ANGLE_SECTION_TYPES else 1
        return [
            SlenderElementInput(name="leg_d", b=_positive_value(data, "d"), t=t, lambda_r=_lambda_r(CompressionCase.CASE_3), case=EffectiveWidthCase.OTHER, count=count),
            SlenderElementInput(name="leg_b", b=_positive_value(data, "b"), t=t, lambda_r=_lambda_r(CompressionCase.CASE_3), case=EffectiveWidthCase.OTHER, count=count),
        ]
    raise NotImplementedError(f"No E7 element adapter for section type '{section_type.value}'.")


def _single_angle_shear_center(data: dict[str, Any]) -> tuple[float, float]:
    """Shear center of a single angle, (w0, z0), in principal axes with respect to the centroid.

    The shear center is at the intersection of the leg mid-thickness lines, (t/2, t/2) from the heel;
    the centroid is at (x, y) from the heel; principal axes are rotated by alpha, tan(alpha) per the database.
    """
    t = _require_positive(_positive_value(data, "t"), "t")
    x = _require_positive(_positive_value(data, "x"), "x")
    y = _require_positive(_positive_value(data, "y"), "y")
    alpha = math.atan(_require_positive(_positive_value(data, "tan_alpha"), "tan_alpha"))
    dx, dy = t / 2.0 - x, t / 2.0 - y
    w0 = dx * math.cos(alpha) + dy * math.sin(alpha)
    z0 = -dx * math.sin(alpha) + dy * math.cos(alpha)
    return w0, z0


def _double_angle_J(data: dict[str, Any]) -> float:
    # Thin-walled approximation, 2 * (d + b - t)*t^3/3, when J is not tabulated for double angles
    t = _require_positive(_positive_value(data, "t"), "t")
    return 2.0 * (_positive_value(data, "d") + _positive_value(data, "b") - t) * t**3 / 3.0


def compression(
    section: Optional[BaseSection] = None,
    Fy: float = 50.0,
    L: Optional[float] = None,
    K: float = 1.0,
    Lx: Optional[float] = None,
    Ly: Optional[float] = None,
    Lz: Optional[float] = None,
    Kx: Optional[float] = None,
    Ky: Optional[float] = None,
    Kz: Optional[float] = None,
    E: float = E_STEEL,
    G: float = G_STEEL,
    section_type: Optional[SectionType] = None,
    properties: Optional[dict[str, Any]] = None,
    single_angle_method: Literal["E5", "E3"] = "E5",
    connected_leg: Literal["long", "short"] = "long",
    truss: Literal["planar", "box"] = "planar",
    a: Optional[float] = None,
    ri: Optional[float] = None,
    connectors: Literal["snug_tight", "welded", "pretensioned"] = "welded",
) -> CompressionResult:
    """AISC 360-22 Chapter E: Design compressive strength, phi_c*Pn, of a US section.

    Pn is the lowest value from the applicable limit states per Table User Note E1.1:
        W, S, M, HP: FB (E3) about x and y, TB (E4-2)
        C, MC: FB about x and y, FTB (E4-3, x-axis of symmetry)
        WT, ST, MT, 2L: FB about x and y, FTB (E4-3, y-axis of symmetry); E6 for 2L when a and ri are given
        L: FB with E5 effective slenderness (or E3 about principal axes), FTB (E4) when b/t > 0.71*sqrt(E/Fy)
        HSS, Pipe: FB about x and y
    Slender-element sections use E7 i.e Pn = Fn*Ae for each limit state.

    Args:
        section: US section object
        Fy: Specified minimum yield stress (ksi); default 50 ksi
        L, K: Unbraced length (in) and effective length factor used for every axis unless overridden
        Lx, Ly, Lz, Kx, Ky, Kz: Per-axis unbraced lengths (in) and effective length factors; z is torsional
        E, G: Moduli (ksi)
        section_type, properties: Section as a plain dictionary, or property overrides e.g J for double angles
        single_angle_method: "E5" (loaded through one leg) or "E3" (concentric, principal axes)
        connected_leg, truss: E5 options
        a, ri, connectors: E6 options for double angles; connector spacing (in) and component min radius of gyration (in)
    """
    section_type_, data = _section_properties(section, section_type, properties)
    Lx_ = Lx if Lx is not None else L
    Ly_ = Ly if Ly is not None else L
    Lz_ = Lz if Lz is not None else L
    if Lx_ is None or Ly_ is None or Lz_ is None:
        raise ValueError("Provide L, or all of Lx, Ly and Lz.")
    Kx_ = Kx if Kx is not None else K
    Ky_ = Ky if Ky is not None else K
    Kz_ = Kz if Kz is not None else K

    Ag = _require_positive(_positive_value(data, "A", "Ag"), "A")
    classification = classify_section_from_dict(section_type_, data, E_ksi=E, Fy_ksi=Fy, classification_context=ClassificationContext.AXIAL_COMPRESSION)
    slender = classification.section_class == SectionClass.SLENDER_ELEMENT
    checks: list[CompressionResult] = []
    notes: list[str] = []

    rx = _positive_value(data, "rx")
    ry = _positive_value(data, "ry")
    J = _positive_value(data, "J")
    Cw = _positive_value(data, "Cw")
    Ix = _positive_value(data, "Ix")
    Iy = _positive_value(data, "Iy")

    if section_type_ in I_SECTION_TYPES:
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(rx, "rx"), L=Lx_, K=Kx_, E=E, axis="x"))
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(ry, "ry"), L=Ly_, K=Ky_, E=E, axis="y"))
        checks.append(check_torsional_buckling(TorsionalBucklingCase.DOUBLY_SYMMETRIC, Fy, Ag, _require_positive(J, "J"), Lz_, Kz_, Cw=_require_positive(Cw, "Cw"), Ix=Ix, Iy=Iy, E=E, G=G))

    elif section_type_ in CHANNEL_SECTION_TYPES:
        x0 = _require_positive(_positive_value(data, "x"), "x") + _require_positive(_positive_value(data, "eo"), "eo") # centroid to shear center, both measured from the web back
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(rx, "rx"), L=Lx_, K=Kx_, E=E, axis="x"))
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(ry, "ry"), L=Ly_, K=Ky_, E=E, axis="y"))
        checks.append(
            check_torsional_buckling(
                TorsionalBucklingCase.SINGLY_SYMMETRIC, Fy, Ag, _require_positive(J, "J"), Lz_, Kz_, Cw=Cw, Ix=Ix, Iy=Iy, rx=rx, ry=ry,
                Lx=Lx_, Ly=Ly_, Kx=Kx_, Ky=Ky_, x0=x0, y0=0.0, axis_of_symmetry="x", E=E, G=G,
            )
        )

    elif section_type_ in TEE_SECTION_TYPES or section_type_ in DOUBLE_ANGLE_SECTION_TYPES:
        is_double_angle = section_type_ in DOUBLE_ANGLE_SECTION_TYPES
        flange_t = _positive_value(data, "t") if is_double_angle else _positive_value(data, "tf")
        y0 = _require_positive(_positive_value(data, "y"), "y") - _require_positive(flange_t, "t" if is_double_angle else "tf") / 2.0
        if is_double_angle and J <= 0.0:
            J = _double_angle_J(data)
            notes.append("J approximated as 2(d + b - t)t^3/3 for the double angle; pass properties={'J': ...} to override.")
        Cw_ftb = 0.0 if is_double_angle else Cw # User Note E4: Cw term may be omitted for tees and double angles
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(rx, "rx"), L=Lx_, K=Kx_, E=E, axis="x"))

        Fey: Optional[float] = None
        if is_double_angle and a is not None:
            built_up = check_built_up_compression(
                Fy, Ag, effective_length(Ky_, Ly_), _require_positive(ry, "ry"), a, _require_positive(ri, "ri"), connectors, "angles", E
            )
            checks.append(built_up)
            Fey = built_up.Fe # E6: modified slenderness also used for the flexural term in E4-3
        else:
            checks.append(check_flexural_buckling(Fy, Ag, _require_positive(ry, "ry"), L=Ly_, K=Ky_, E=E, axis="y"))
            if is_double_angle:
                notes.append("E6 modified slenderness not applied; pass a and ri for intermediate connectors.")
        checks.append(
            check_torsional_buckling(
                TorsionalBucklingCase.SINGLY_SYMMETRIC, Fy, Ag, J, Lz_, Kz_, Cw=Cw_ftb, Ix=Ix, Iy=Iy, rx=rx, ry=ry,
                Lx=Lx_, Ly=Ly_, Kx=Kx_, Ky=Ky_, x0=0.0, y0=y0, axis_of_symmetry="y", Fey=Fey, E=E, G=G,
            )
        )

    elif section_type_ in SINGLE_ANGLE_SECTION_TYPES:
        t = _require_positive(_positive_value(data, "t"), "t")
        bl = max(_positive_value(data, "d"), _positive_value(data, "b"))
        bs = min(_positive_value(data, "d"), _positive_value(data, "b"))
        rz = _require_positive(_positive_value(data, "rz"), "rz")
        Lc = effective_length(Kx_, Lx_)
        if single_angle_method == "E5":
            # y-axis is parallel to the long leg in the database (ry is about the axis parallel to the long leg)
            ra = _require_positive(ry if connected_leg == "long" else rx, "ra")
            checks.append(check_single_angle_compression(Fy, Ag, Lx_, ra, rz, bl, bs, t, connected_leg, truss, E))
        else:
            rw = math.sqrt(_require_positive(_positive_value(data, "Iw"), "Iw") / Ag)
            checks.append(check_flexural_buckling(Fy, Ag, rz, Lc=Lc, E=E, axis="z"))
            checks.append(check_flexural_buckling(Fy, Ag, rw, Lc=Lc, E=E, axis="w"))

        if bl / t > 0.71 * math.sqrt(E / Fy): # E4 applies to single angles with b/t > 0.71*sqrt(E/Fy)
            w0, z0 = _single_angle_shear_center(data)
            r0_bar = _positive_value(data, "ro") or math.sqrt(calculate_r0_bar2(w0, z0, _positive_value(data, "Iw"), _positive_value(data, "Iz"), Ag))
            rw = math.sqrt(_require_positive(_positive_value(data, "Iw"), "Iw") / Ag)
            Few = elastic_buckling_stress(Lc, rw, E)
            Fe_z = elastic_buckling_stress(Lc, rz, E)
            if section_type_ == SectionType.L_EQUAL:
                ftb = check_torsional_buckling(
                    TorsionalBucklingCase.SINGLY_SYMMETRIC, Fy, Ag, _require_positive(J, "J"), Lz_, Kz_, Cw=Cw, x0=0.0, y0=w0,
                    r0_bar=r0_bar, axis_of_symmetry="y", Fey=Few, E=E, G=G,
                ) # principal w-axis is the axis of symmetry
            else:
                ftb = check_torsional_buckling(
                    TorsionalBucklingCase.UNSYMMETRIC, Fy, Ag, _require_positive(J, "J"), Lz_, Kz_, Cw=Cw, x0=w0, y0=z0,
                    r0_bar=r0_bar, Fex=Few, Fey=Fe_z, E=E, G=G,
                ) # principal axes: x -> w (major), y -> z (minor)
            ftb.metadata["note"] = "Single-angle FTB per E4 (Commentary E5); principal axes w, z."
            checks.append(ftb)

    elif section_type_ in RECT_HSS_SECTION_TYPES:
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(rx, "rx"), L=Lx_, K=Kx_, E=E, axis="x"))
        checks.append(check_flexural_buckling(Fy, Ag, _require_positive(ry, "ry"), L=Ly_, K=Ky_, E=E, axis="y"))

    elif section_type_ in ROUND_HSS_SECTION_TYPES:
        r = _require_positive(rx or ry, "rx") # rx = ry = r for round HSS and pipe
        checks.append(check_flexural_buckling(Fy, Ag, r, Lc=max(effective_length(Kx_, Lx_), effective_length(Ky_, Ly_)), E=E, axis="x"))

    else:
        raise NotImplementedError(f"Compression is not implemented for section type '{section_type_.value}'.")

    # E7. Members with slender elements: Pn = Fn*Ae for each limit state, in interaction with local buckling
    if slender:
        if section_type_ in ROUND_HSS_SECTION_TYPES:
            D = _require_positive(_positive_value(data, "OD", "D"), "OD")
            t_wall = _require_positive(_positive_value(data, "tdes", "tnom"), "tdes")
            Ae_round = round_hss_effective_area(D, t_wall, Ag, Fy, E)
            checks = [check.model_copy(update={"Ae": Ae_round, "Pn": check.Fn * Ae_round, "phi_c_Pn": PHI_C * check.Fn * Ae_round}) for check in checks]
        else:
            elements = _slender_elements(section_type_, data, Fy, E)
            reduced: list[CompressionResult] = []
            for check in checks:
                Ae, widths = _effective_area_from_elements(check.Fn, Ag, elements, Fy)
                reduced.append(
                    check.model_copy(update={"Ae": Ae, "Pn": check.Fn * Ae, "phi_c_Pn": PHI_C * check.Fn * Ae, "metadata": {**check.metadata, "effective_widths": widths}})
                )
            checks = reduced
        notes.append("Slender-element section; E7 applied to every limit state (Pn = Fn*Ae).")

    governing = min(checks, key=lambda check: check.Pn)
    Lc_r_max = max((check.Lc / check.r) for check in checks if check.Lc and check.r) if any(check.Lc and check.r for check in checks) else None
    return governing.model_copy(
        update={
            "section_class": classification.section_class,
            "checks": checks,
            "metadata": {
                **governing.metadata,
                "section_type": section_type_.value,
                "governing_elements": classification.governing_elements,
                "Lc_r_max": Lc_r_max,
                "slenderness_ok": (Lc_r_max <= COMPRESSION_SLENDERNESS_LIMIT) if Lc_r_max is not None else None,
                "notes": notes,
            },
        }
    )


def compression_utilisation(Pu: float, phi_c_Pn: float) -> UtilisationCheck:
    """AISC 360-22 Section E1: Compression utilisation, Pu / phi_c*Pn (LRFD).

    Args:
        Pu: Required compressive strength (kips)
        phi_c_Pn: Design compressive strength (kips)
    """
    utilisation = compute_utilisation(abs(Pu), phi_c_Pn)
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={"Pu": Pu, "phi_c_Pn": phi_c_Pn},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="E1", title="Compressive strength"),
    )


if __name__ == "__main__":
    from steelsnakes.US.sections.beams import W_beam
    from steelsnakes.US.sections.tees import WT

    # AISC Design Example E.1D: W14x90, Lcx = 30 ft, Lcy = Lcz = 15 ft; phi_c*Pn = 927 kips
    print(compression(section=W_beam("W14X90"), Fy=50.0, Lx=360.0, Ly=180.0, Lz=180.0).model_dump(exclude={"checks"}))
    # AISC Design Example E.8: WT7x15, L = 20 ft; phi_c*Pn = 36.6 kips (FTB)
    print(compression(section=WT("WT7X15"), Fy=50.0, L=240.0).model_dump(exclude={"checks"}))
    print("🐬")
