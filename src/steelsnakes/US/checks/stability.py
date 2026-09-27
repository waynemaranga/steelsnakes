# C: DESIGN FOR STABILITY
# C1. General Stability Requirements; direct analysis method (default), or Appendix 7 alternatives
# C2. Calculation of Required Strengths
#   C2.1 General analysis requirements; second-order analysis, P-δ may be neglected under conditions
#   C2.2 Consideration of initial system imperfections; C2.2a direct modelling, C2.2b notional loads
#   C2.3 Adjustments to stiffness; 0.8 and τb
# C3. Calculation of Available Strengths; Lc = L for the direct analysis method
# APPENDIX 7: ALTERNATIVE METHODS OF DESIGN FOR STABILITY
#   7.2 Effective length method; 7.3 First-order analysis method
# APPENDIX 8: APPROXIMATE ANALYSIS
#   8.1 Approximate second-order elastic analysis; B1 (P-δ) and B2 (P-Δ) multipliers
#   8.2 Approximate inelastic moment redistribution
# NOTE: see codes/notional-loads-how-to-approach.pdf (Ericksen, MSC Jan 2011) for placing and directing notional loads.
# NOTE: alpha = 1.0 for LRFD and 1.6 for ASD throughout; ASD second-order analyses use 1.6 x ASD load combinations.

from __future__ import annotations

import math
from enum import Enum
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field

from steelsnakes.base.checks import DesignCode, Reference, UtilisationCheck
from steelsnakes.US.checks.classification import _require_positive
from steelsnakes.US.checks.compression import E_STEEL

ALPHA_LRFD = 1.0
ALPHA_ASD = 1.6
NOTIONAL_LOAD_COEFFICIENT = 0.002 # C2-1; a nominal initial story out-of-plumbness of 1/500 (Code of Standard Practice)
STIFFNESS_REDUCTION = 0.8 # C2.3(a)
DRIFT_RATIO_LIMIT_DIRECT_ANALYSIS = 1.7 # C2.1(b), C2.2a, C2.2b(d); with stiffnesses reduced per C2.3
DRIFT_RATIO_LIMIT_ELASTIC = 1.5 # App. 7.2.1(b), 7.3.1(c); nominal stiffnesses
DRIFT_RATIO_LIMIT_K_EQUALS_1 = 1.1 # App. 7.2.3(b) exception
REDISTRIBUTION_FY_LIMIT = 65.0 # ksi [is 450 MPa in US_Metric module]; App. 8.2, no moment redistribution above this Fy


class DesignMethod(str, Enum):
    """AISC 360-22 methods of design for stability (C1 and Appendix 7)."""

    DIRECT_ANALYSIS = "direct-analysis" # C1, C2, C3
    EFFECTIVE_LENGTH = "effective-length" # Appendix 7.2
    FIRST_ORDER = "first-order" # Appendix 7.3


def _alpha(alpha: float) -> float:
    if alpha not in (ALPHA_LRFD, ALPHA_ASD):
        raise ValueError("alpha must be 1.0 (LRFD) or 1.6 (ASD).")
    return alpha


# --- C2.1 General Analysis Requirements ---
def p_delta_negligible(drift_ratio: float, moment_frame_gravity_fraction: float, gravity_through_vertical_members: bool = True) -> bool:
    """AISC 360-22 Section C2.1(b): whether the effect of P-δ on the response of the structure may be neglected.

    All three conditions must hold: (1) gravity loads are supported primarily through nominally vertical columns,
    walls or frames; (2) the ratio of maximum second-order to first-order drift, with stiffnesses reduced per C2.3, is
    <= 1.7 in all stories; and (3) no more than one-third of the total gravity load is supported by columns of moment
    frames in the direction considered. P-δ must still be considered for individual beam-columns e.g. via B1.

    Args:
        drift_ratio: Maximum Δ2nd/Δ1st over all stories (LRFD, or 1.6 x ASD, load combinations)
        moment_frame_gravity_fraction: Fraction of the total gravity load carried by moment-frame columns
        gravity_through_vertical_members: Condition (1)
    """
    return gravity_through_vertical_members and drift_ratio <= DRIFT_RATIO_LIMIT_DIRECT_ANALYSIS and moment_frame_gravity_fraction <= 1.0 / 3.0


# --- C2.2b Use of Notional Loads to Represent Imperfections ---
def notional_load(Yi: float, alpha: float = ALPHA_LRFD, out_of_plumbness: float = NOTIONAL_LOAD_COEFFICIENT) -> float:
    """AISC 360-22 Equation C2-1: notional load at level i, Ni = 0.002*alpha*Yi.

    Per C2.2b(c), the 0.002 coefficient is the nominal out-of-plumbness of 1/500; where a different maximum
    out-of-plumbness is justified, the coefficient is adjusted proportionally e.g. out_of_plumbness=1/1000.

    Args:
        Yi: Gravity load applied at level i from the LRFD or ASD load combination (kips)
        alpha: 1.0 (LRFD) or 1.6 (ASD)
        out_of_plumbness: Initial story out-of-plumbness ratio Δ0/L; 1/500 by default

    Returns:
        Ni: Notional lateral load at level i (kips); distributed over the level like the gravity load (C2.2b(b))
    """
    if Yi < 0.0:
        raise ValueError("Gravity load Yi cannot be negative.")
    if out_of_plumbness <= 0.0:
        raise ValueError("out_of_plumbness must be positive.")
    return out_of_plumbness * _alpha(alpha) * Yi


def notional_loads(Y: Sequence[float], alpha: float = ALPHA_LRFD, out_of_plumbness: float = NOTIONAL_LOAD_COEFFICIENT) -> list[float]:
    """AISC 360-22 Equation C2-1 for every level; `Y` holds the gravity load applied at each level (kips)."""
    return [notional_load(Yi, alpha, out_of_plumbness) for Yi in Y]


def notional_loads_required_with_lateral_loads(drift_ratio: float) -> bool:
    """AISC 360-22 Section C2.2b(d): notional loads must be added to combinations with other lateral loads only when
    the ratio of maximum second-order to first-order drift (stiffnesses reduced per C2.3) exceeds 1.7 in any story.

    Otherwise they need only be applied in gravity-only load combinations.
    """
    return _require_positive(drift_ratio, "drift_ratio") > DRIFT_RATIO_LIMIT_DIRECT_ANALYSIS


# --- C2.3 Adjustments to Stiffness ---
def stiffness_reduction_tau_b(Pr: float, Pns: float, alpha: float = ALPHA_LRFD) -> float:
    """AISC 360-22 Equations C2-2a and C2-2b: stiffness reduction parameter τb for noncomposite members.

    τb = 1.0 when alpha*Pr/Pns <= 0.5 (C2-2a); τb = 4(alpha*Pr/Pns)[1 - (alpha*Pr/Pns)] otherwise (C2-2b).

    Args:
        Pr: Required axial compressive strength, LRFD or ASD (kips)
        Pns: Cross-section compressive strength; Fy*Ag, or Fy*Ae for slender-element sections with Fn = Fy (kips)
        alpha: 1.0 (LRFD) or 1.6 (ASD)
    """
    ratio = _alpha(alpha) * max(Pr, 0.0) / _require_positive(Pns, "Pns")
    if ratio > 1.0:
        raise ValueError(f"alpha*Pr/Pns = {ratio:.3f} > 1.0; the member cannot carry the required axial strength.")
    return 1.0 if ratio <= 0.5 else 4.0 * ratio * (1.0 - ratio)


class ReducedStiffness(BaseModel):
    """AISC 360-22 Section C2.3: stiffnesses for the direct analysis method."""

    tau_b: float
    EI_star: Optional[float] = None # 0.8*τb*EI, kip-in.² [N-mm²]
    EA_star: Optional[float] = None # 0.8*EA, kips [N]
    reference: Reference = Field(default_factory=lambda: Reference(code=DesignCode.AISC_360, clause="C2.3", title="Adjustments to stiffness"))


def reduced_stiffness(
    EI: Optional[float] = None,
    EA: Optional[float] = None,
    Pr: float = 0.0,
    Pns: Optional[float] = None,
    alpha: float = ALPHA_LRFD,
    tau_b: Optional[float] = None,
) -> ReducedStiffness:
    """AISC 360-22 Section C2.3(a) and (b): 0.8*τb for flexural stiffness and 0.8 for other stiffnesses.

    Pass `tau_b` directly, or Pr and Pns to calculate it; use tau_b=1.0 with the 0.001*alpha*Yi notional load of
    C2.3(c) (see `tau_b_notional_load`).
    """
    if tau_b is None:
        tau_b = stiffness_reduction_tau_b(Pr, Pns, alpha) if Pns is not None else 1.0
    return ReducedStiffness(
        tau_b=tau_b,
        EI_star=STIFFNESS_REDUCTION * tau_b * EI if EI is not None else None,
        EA_star=STIFFNESS_REDUCTION * EA if EA is not None else None,
    )


def tau_b_notional_load(Yi: float, alpha: float = ALPHA_LRFD) -> float:
    """AISC 360-22 Section C2.3(c): additional notional load 0.001*alpha*Yi permitting τb = 1.0 for all members.

    It is applied at all levels in all load combinations, in addition to any C2.2b notional loads, and is not subject
    to the C2.2b(d) exemption.
    """
    return notional_load(Yi, alpha, out_of_plumbness=0.001)


# --- Appendix 7. Alternative Methods of Design for Stability ---
def effective_length_method_permitted(drift_ratio: float, gravity_through_vertical_members: bool = True) -> bool:
    """AISC 360-22 Appendix 7.2.1: the effective length method needs Δ2nd/Δ1st <= 1.5 (nominal stiffnesses)."""
    return gravity_through_vertical_members and drift_ratio <= DRIFT_RATIO_LIMIT_ELASTIC


def k_equals_one_permitted(drift_ratio: float) -> bool:
    """AISC 360-22 Appendix 7.2.3(b) exception: K = 1.0 is permitted for all columns if Δ2nd/Δ1st <= 1.1."""
    return drift_ratio <= DRIFT_RATIO_LIMIT_K_EQUALS_1


def first_order_additional_lateral_load(Yi: float, delta_over_L: float, alpha: float = ALPHA_LRFD) -> float:
    """AISC 360-22 Equation A-7-3: additional lateral load of the first-order analysis method.

    Ni = 2.1*alpha*(Δ/L)*Yi >= 0.0042*Yi

    Args:
        Yi: Gravity load applied at level i, LRFD or ASD (kips)
        delta_over_L: Maximum ratio of first-order interstory drift to story height over all stories
        alpha: 1.0 (LRFD) or 1.6 (ASD)
    """
    if Yi < 0.0 or delta_over_L < 0.0:
        raise ValueError("Yi and delta_over_L cannot be negative.")
    return max(2.1 * _alpha(alpha) * delta_over_L * Yi, 0.0042 * Yi)


def check_first_order_method(
    drift_ratio: float,
    column_Pr: float,
    column_Pns: float,
    beam_Pr: float = 0.0,
    beam_I: Optional[float] = None,
    L: Optional[float] = None,
    alpha: float = ALPHA_LRFD,
    E: float = E_STEEL,
) -> UtilisationCheck:
    """AISC 360-22 Appendix 7.3.1: limitations of the first-order analysis method.

    (b) alpha*Pr <= 0.08*Pe in moment-frame beams, Pe = π²EI/L² (A-7-1)
    (c) Δ2nd/Δ1st <= 1.5 with nominal stiffnesses (B2 may be used)
    (d) alpha*Pr <= 0.5*Pns in members contributing to lateral stability (A-7-2)

    Utilisation is the largest of the three ratios to their limits.

    Args:
        drift_ratio: Maximum Δ2nd/Δ1st, or B2
        column_Pr: Required axial strength of the member contributing to lateral stability (kips)
        column_Pns: Its cross-section compressive strength (kips)
        beam_Pr: Required axial compressive strength of a moment-frame beam subject to bending (kips)
        beam_I: Its moment of inertia in the plane of bending (in.⁴)
        L: Height of story (in.); for Pe in A-7-1
    """
    alpha = _alpha(alpha)
    ratios: dict[str, float] = {
        "drift_ratio/1.5": drift_ratio / DRIFT_RATIO_LIMIT_ELASTIC,
        "alpha*Pr/(0.5*Pns)": alpha * column_Pr / (0.5 * _require_positive(column_Pns, "column_Pns")),
    }
    if beam_Pr:
        Pe = math.pi**2 * E * _require_positive(beam_I, "beam_I") / _require_positive(L, "L") ** 2
        ratios["alpha*Pr/(0.08*Pe)"] = alpha * beam_Pr / (0.08 * Pe)
    utilisation = max(ratios.values())
    return UtilisationCheck(
        utilisation=utilisation,
        metadata={**ratios, "governing": max(ratios, key=lambda key: ratios[key])},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",
        reference=Reference(code=DesignCode.AISC_360, clause="Appendix 7.3.1", equation="A-7-1, A-7-2", title="First-order analysis method limitations"),
    )


# --- Appendix 8.1 Approximate Second-Order Elastic Analysis ---
def calculate_Cm(
    M1: float = 0.0,
    M2: float = 1.0,
    curvature: Optional[Literal["single", "reverse"]] = None,
    transverse_loading: bool = False,
) -> float:
    """AISC 360-22 Equation A-8-4: equivalent uniform moment factor, Cm = 0.6 - 0.4*(M1/M2).

    M1 and M2 are the smaller and larger end moments of the portion unbraced in the plane of bending; M1/M2 is positive
    in reverse curvature and negative in single curvature. Pass signed M1, M2 in that convention, or their magnitudes
    with `curvature`. With transverse loading between supports, Cm is conservatively 1.0 (A-8.1.2(b)).
    """
    if transverse_loading:
        return 1.0
    if M2 == 0.0:
        raise ValueError("M2, the larger end moment, cannot be zero.")
    if abs(M1) > abs(M2):
        raise ValueError("M1 must be the smaller end moment.")
    ratio = M1 / M2
    if curvature is not None:
        ratio = abs(ratio) if curvature == "reverse" else -abs(ratio)
    return 0.6 - 0.4 * ratio


def calculate_Pe1(I: float, Lc1: float, E: float = E_STEEL, tau_b: float = 1.0, direct_analysis: bool = True) -> float:
    """AISC 360-22 Equation A-8-5: elastic critical buckling strength in the plane of bending, no sway, Pe1 = π²EI*/Lc1².

    EI* = 0.8*τb*EI for the direct analysis method, EI for the effective length and first-order analysis methods.

    Args:
        I: Moment of inertia in the plane of bending (in.⁴)
        Lc1: Effective length in the plane of bending, no lateral translation; the unbraced length unless less is justified (in.)
    """
    EI_star = (STIFFNESS_REDUCTION * tau_b if direct_analysis else 1.0) * E * _require_positive(I, "I")
    return math.pi**2 * EI_star / _require_positive(Lc1, "Lc1") ** 2


def calculate_B1(Cm: float, Pr: float, Pe1: float, alpha: float = ALPHA_LRFD) -> float:
    """AISC 360-22 Equation A-8-3: P-δ multiplier, B1 = Cm/(1 - alpha*Pr/Pe1) >= 1.

    Pr may be the first-order estimate Pnt + Plt. B1 = 1.0 for members not subjected to compression.
    """
    if Pr <= 0.0:
        return 1.0
    ratio = _alpha(alpha) * Pr / _require_positive(Pe1, "Pe1")
    if ratio >= 1.0:
        raise ValueError(f"alpha*Pr/Pe1 = {ratio:.3f} >= 1.0; the member is unstable in the plane of bending.")
    return max(Cm / (1.0 - ratio), 1.0)


def calculate_RM(Pmf: float, Pstory: float) -> float:
    """AISC 360-22 Equation A-8-8: RM = 1 - 0.15*(Pmf/Pstory); Pmf = 0 for braced frames (RM = 1.0)."""
    if Pmf < 0.0:
        raise ValueError("Pmf cannot be negative.")
    return 1.0 - 0.15 * Pmf / _require_positive(Pstory, "Pstory")


def calculate_Pe_story(H: float, L: float, delta_H: float, RM: float = 1.0) -> float:
    """AISC 360-22 Equation A-8-7: elastic critical buckling strength for the story, Pe_story = RM*H*L/ΔH.

    Args:
        H: Total story shear produced by the lateral forces used to compute ΔH (kips)
        L: Height of story (in.)
        delta_H: First-order interstory drift due to those lateral forces (in.); with C2.3 stiffnesses when using the
            direct analysis method
        RM: Per A-8-8; 1.0 without moment frames, 0.85 as a lower bound with them
    """
    return RM * _require_positive(H, "H") * _require_positive(L, "L") / _require_positive(delta_H, "delta_H")


def calculate_B2(Pstory: float, Pe_story: float, alpha: float = ALPHA_LRFD) -> float:
    """AISC 360-22 Equation A-8-6: P-Δ multiplier for the story, B2 = 1/(1 - alpha*Pstory/Pe_story) >= 1."""
    ratio = _alpha(alpha) * _require_positive(Pstory, "Pstory") / _require_positive(Pe_story, "Pe_story")
    if ratio >= 1.0:
        raise ValueError(f"alpha*Pstory/Pe_story = {ratio:.3f} >= 1.0; the story is unstable.")
    return max(1.0 / (1.0 - ratio), 1.0)


class SecondOrderResult(BaseModel):
    """AISC 360-22 Appendix 8.1: required second-order strengths."""

    Mr: float # required second-order flexural strength, B1*Mnt + B2*Mlt, kip-in. [N-mm] (A-8-1)
    Pr: float # required second-order axial strength, Pnt + B2*Plt, kips [N] (A-8-2)
    B1: float
    B2: float
    Mnt: float
    Mlt: float
    Pnt: float
    Plt: float
    reference: Reference = Field(default_factory=lambda: Reference(code=DesignCode.AISC_360, clause="Appendix 8.1", equation="A-8-1, A-8-2", title="Approximate second-order elastic analysis"))


def amplified_required_strengths(Mnt: float, Mlt: float = 0.0, Pnt: float = 0.0, Plt: float = 0.0, B1: float = 1.0, B2: float = 1.0) -> SecondOrderResult:
    """AISC 360-22 Equations A-8-1 and A-8-2: Mr = B1*Mnt + B2*Mlt and Pr = Pnt + B2*Plt.

    Args:
        Mnt: First-order moment with the structure restrained against lateral translation (kip-in.)
        Mlt: First-order moment due to lateral translation of the structure only (kip-in.)
        Pnt: First-order axial force with the structure restrained against lateral translation (kips)
        Plt: First-order axial force due to lateral translation of the structure only (kips)
        B1: P-δ multiplier of the member (A-8-3)
        B2: P-Δ multiplier of the story (A-8-6)
    """
    if B1 < 1.0 or B2 < 1.0:
        raise ValueError("B1 and B2 are not less than 1.0.")
    return SecondOrderResult(Mr=B1 * Mnt + B2 * Mlt, Pr=Pnt + B2 * Plt, B1=B1, B2=B2, Mnt=Mnt, Mlt=Mlt, Pnt=Pnt, Plt=Plt)


# --- Appendix 8.2 Approximate Inelastic Moment Redistribution ---
def moment_redistribution_Lm(
    M1: float,
    M2: float,
    ry: float,
    Fy: float,
    shape: Literal["i-shape", "box"] = "i-shape",
    E: float = E_STEEL,
    Fy_limit: float = REDISTRIBUTION_FY_LIMIT,
) -> float:
    """AISC 360-22 Equations A-8-9 and A-8-10: limiting unbraced length Lm for 10% negative moment redistribution.

    (a) I-shaped beams, Iyc >= Iyt: Lm = [0.12 + 0.076(M1/M2)](E/Fy)*ry (A-8-9)
    (b) solid rectangular bars, rectangular HSS and symmetric box beams, major axis:
        Lm = [0.17 + 0.10(M1/M2)](E/Fy)*ry >= 0.10(E/Fy)*ry (A-8-10)

    M1/M2 is positive for reverse curvature and negative for single curvature. Not permitted for Fy > 65 ksi [450 MPa];
    pass Fy_limit=450.0 with Fy and E in MPa.
    """
    if Fy > Fy_limit:
        raise ValueError(f"Moment redistribution is not permitted for Fy exceeding {Fy_limit:g} (65 ksi, 450 MPa).")
    if M2 == 0.0 or abs(M1) > abs(M2):
        raise ValueError("M2 must be the larger, non-zero end moment.")
    base = (E / _require_positive(Fy, "Fy")) * _require_positive(ry, "ry")
    if shape == "i-shape":
        return (0.12 + 0.076 * M1 / M2) * base
    return max((0.17 + 0.10 * M1 / M2) * base, 0.10 * base)


if __name__ == "__main__":
    # AISC Design Example C.1A (v16.0): Yi = 288 kips (LRFD), 192 kips (ASD)
    print(notional_load(288.0), notional_load(192.0, alpha=ALPHA_ASD)) # 0.576, 0.614 kips
    # AISC Design Example C.1C: B2 = 1.48 (LRFD)
    RM = calculate_RM(Pmf=144.0, Pstory=288.0)
    print(RM, calculate_B2(288.0, calculate_Pe_story(H=1.21, L=240.0, delta_H=0.304, RM=RM)))
    print("🐬")
