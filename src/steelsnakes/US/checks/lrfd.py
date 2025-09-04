# D: Tension - tensile yielding in gross section and tensile rupture in net section
# E: Compression - flexural buckling, torsional buckling, flexural-torsional buckling
# F: Flexure -
# G: Shear - 
# H: Combined Forces & Torsion - 

import numpy as np
from typing import Any, Optional, Union, Literal, cast
from steelsnakes.base.checks import UtilisationCheck, Scalar, Reference, SectionClass
from steelsnakes.base.sections import BaseSection, SectionType

# TODO: define custom errors for calculations... add graceful handling

# from steelsnakes.base.checks import BaseCheck   
# TODO: Write equations with clauses

# Designing strictly according to LFRD (equivalent to Eurocode's Limit State Design)
# TODO: ACI360, on every chapter, has a table user note with a selection table, chapters and importantly which Limit States to consider.
# -------------------------------------------------------------------------------
# Chapter D: Tension
# D1. Slenderness Limitation
# Slenderness ratio L/r ≤ 300 for tension members

def tension_slenderness(L: float, r: float):
    """ACI 360-22 Section D1-1: Slenderness ratio for tension members. Limited to 300.

    Args:
        L: Length of the member (in)
        r: Radius of gyration of the member (in)
    """
    slenderness_ratio = L/r
    return UtilisationCheck(
        utilisation=slenderness_ratio,
        metadata={},
        adequacy="OK" if slenderness_ratio <= 300 else "FAILS",
        reference=Reference(code="ACI_360", clause="D1-1", equation="D1-1") # Handle clause/Section difference between EU/US/IS etc.
    )
    

# D2. Tensile Strength; phi_t_Pn - design tensile strength, phi_t - resistance factor, Pn - nominal tensile strength
# eq. D2-1: for tensile yielding in gross section
# Pn = Fy * Ag, and phi_t = 0.9

def design_yielding_tensile_strength(Fy: float, Ag: float) -> Scalar | float:
    """ACI 360-22 Section D2-1: Design tensile strength for tensile yielding in gross section.
    
    Args:
        Fy: Specified minimum yield stress (kpsi) # FIXME: double check
        Ag: Gross area (in²)

    Returns:
        phi_t_Pn: Design tensile strength for yielding in gross section (kips) # FIXME: double check
    """
    Pn = Fy * Ag
    phi_t = 0.9
    return round(Pn * phi_t, ndigits=4)

# eq. D2-2: for tensile rupture in net section
# Pn = 0.75 * Fu * An, and phi_t = 0.75
# where: Ae: effective net area, Ag: gross area, Fy: specified minimum yield stress, Fu: specified minimum tensile strength

def design_rupture_tensile_strength(Fu: float, An: float) -> Scalar | float:
    """ACI 360-22 Section D2-2: Design tensile strength for tensile rupture in net section.
    
    Args:
        Fu: Specified minimum tensile strength (kpsi) # FIXME: double check
        An: Net area (in²)

    Returns:
        phi_t_Pn: Design tensile strength for rupture in net section (kips) # FIXME: double check
    """
    Pn = Fu * An
    phi_t = 0.75
    return round(Pn * phi_t, ndigits=4)

# D3. Effective Net Area Ae; Ag and An are determined in B4.3
# eq. D3-1: effective net area of tension members
# Ae = An * U; U is the shear lag factor; # TODO: read off U from tables in D3.1: Shear Lag Factors for Connections to Tension Members
# for now, default U = 1.0 (no shear lag)

def effective_net_area(U: float, An: float) -> Scalar | float:
    """ACI 360-22 Section D3-1: Effective net area of tension members.
    
    Args:
        U: Shear lag factor
        An: Net area (in²)

    Returns:
        Ae: Effective net area (in²)
    """
    Ae = An * U
    return round(Ae, ndigits=4)

# D4. Built-up Members
# [NO PLAN TO IMPLEMENT BUILT-UP MEMBERS IN ANY CODE]

# D5. Pin-Connected Members: lowest value of phi_t_Pn per tensile rupture, shear rupture, bearing and yielding
# D5.1(a): for tensile rupture on net effective area
# Pn = Fu * (2*t*be), and phi_t = 0.75; be = 2*t + 0.63 in or 2*t + 16 mm
# D5.1(b): for shear rupture on net effective area
# Pn = 0.6 * Fu * A_sf, and phi_sf = 0.75
# where: A_sf (area on shear path) = 2*t*(a + d/2);
# a is shortest distance from edge of the pin hole to the edge of the member parallel to the direction of the force
# be <= the actual distance from the edge of the hole to the edge of the part measured in the direction normal to the applied force
# D5.1(c): for bearing on gross area, seee J7
# D5.1(d): for yielding on gross area, see D2(a)

# -----------------------------------------------------------------------------

# Chapter E: Compression
# E1. General: design compressive strength phi_c_Pn, where phi_c is resistance factor, Pn is nominal compressive strength;
# should be lowest value considering flexural buckling, torsional buckling and flexural-torsional buckling
# NOTE: see selection table on User Note E1.1

# E2. Effective Length Lc - 
# determined according to Chapter C & Appendix 7
# Lc = K*L; K is effective length factor, L is laterally unbraced length
def effective_compression_length(K: float, L: float) -> Scalar | float:
    """ACI 360-22 Section E2-1: Effective length of compression members.
    
    Args:
        K: Effective length factor
        L: Laterally unbraced length (in)

    Returns:
        Lc: Effective length (in)
    """
    Lc = K * L
    return round(Lc, ndigits=4)

# Lc/r i.e effective slenderness ratio <= 200 for compression members; r is radius of gyration about axis of bending

def effective_compression_slenderness(Lc: float, r: float) -> UtilisationCheck:
    """ACI 360-22 Section E2-1: Effective slenderness ratio of compression members.
    
    Args:
        Lc: Effective length (in)
        r: Radius of gyration (in)
    """
    Lc_r = Lc / r
    return UtilisationCheck(
        utilisation=Lc_r,
        metadata={},
        adequacy="OK" if Lc_r <= 200 else "FAILS",
        reference=Reference(code="ACI_360", clause="E2-1", equation="E2-1") # Handle clause/Section difference between EU/US/IS etc.
    )


# E3. Flexural Buckling of members without slender elements
# Applies to nonslender-element compression members as defined in B4.1
# eq. E3-1: Nominal compressive strength Pn = Fcr * Ag

def nominal_compressive_strength(Fcr: float, Ag: float) -> Scalar | float:
    """ACI 360-22 Section E3-1: Nominal compressive strength of compression members.
    Applies to nonslender-element compression members as defined in Section B4.1
    
    Args:
        Fcr: Critical stress (kpsi)
        Ag: Gross area (in²)

    Returns:
        Pn: Nominal compressive strength (kips)
    """
    Pn = Fcr * Ag
    return round(Pn, ndigits=4)

# Critical stress Fcr is determined from:
# eq. E3-2: for 0 < Lc/r ≤ 4.71*sqrt(E/Fy) or Fy/Fe ≤ 2.25; Fy is specified minimum yield stress    
# Fcr = 0.658^(Fy/Fe) * Fy
# eq. E3-3: for Lc/r > 4.71*sqrt(E/Fy) or Fy/Fe > 2.25
# Fcr = 0.877*Fe
# eq. E3-4: Fe = (pi^2 * E) / (Lc/r)^2; i.e elastic buckling stress as in Appendix 7 or Euler's formula
# User Note: The two inequalities for calculating the limits of applicability of Sections E3(a) and E3(b),
# one based on L c /r and one based on Fy /Fe, provide the same result for flexural buckling.

def critical_compressive_stress(**kwargs) -> Scalar | float:
    # FIXME: correct naming?
    """AISC 360-22 Section E3: Critical stress of compression members.

    Provide either:
    - Fy and Fe; or
    - Fy, Lc, r, and E (Fe will be computed as pi^2*E/(Lc/r)^2).

    Returns the critical stress Fcr (same units as Fy).

    Args:
        **kwargs: Accepts keys: Fy, Fe, Lc, r, E # FIXME: implement better; keep this in alpha version
    """
    Fy = kwargs.get("Fy")
    Fe = kwargs.get("Fe")
    Lc = kwargs.get("Lc")
    r = kwargs.get("r")
    E = kwargs.get("E")

    if Fy is None:
        raise ValueError("'Fy' is required.")

    # Compute Fe from slenderness if not provided
    if Fe is None:
        if Lc is None or r is None or E is None:
            raise ValueError("Provide either 'Fe' or ('Lc', 'r', and 'E') to compute Fe.")
        slenderness = Lc / r
        if slenderness <= 0:
            raise ValueError("'Lc/r' must be positive.")
        Fe = (np.pi ** 2) * E / (slenderness ** 2)

    # Select Fcr per E3-2 / E3-3 using Fy/Fe criterion
    ratio = Fy / Fe
    if ratio <= 2.25:
        Fcr = (0.658 ** ratio) * Fy
    else:
        Fcr = 0.877 * Fe

    return round(float(Fcr), ndigits=4)


# E4. Torsional and Flexural-Torsional Buckling of Single Angles and Nonslender-Element Members
# Provisions apply to all single angles with b/t > 0.71*sqrt(E/Fy); b is width of longest leg, t is thickness.
# eq. E4-1: Nominal compressive strength Pn = Fcr * Ag
# Critical stress Fcr is determined from eq. E3-2 or E3-3, but with Fe calculated from:
# eq. E4-2: Fe for double-symmetric members twisting about the shear centre:
# Fe = [ (pi^2 *E*Cw)/Lcz^2 + GJ ] * (1/(Ix + Iy))
# eq. E4-3: Fe for single-symmetric members twisting about the shear centre where y-axis is axis of symmetry:
# Fe = ((Fe_y + Fe_z)/2*H) * [1 - sqrt(1 - (4*H*Fe_y*Fe_z)/(Fe_y + Fe_z)^2)]
# NOTE: For singly symmetric members with the x-axis as the axis of symmetry, such as channels, Equation E4-3 is applicable with Fey replaced by Fex.
# eq. E4-4: For unsymmetric members twisting about the shear center, Fe is the lowest root of the cubic equation... # TODO: no unsymmetric members implemented yet, so ignore for now

def flexural_torsional_buckling_stress(**kwargs) -> Scalar | float:
    """ACI 360-22 Equation E4-2: Flexural-torsional buckling stress of compression members.
    Currently only implemented for double-symmetric members twisting about the shear centre. # TODO: implement for other cases.
    
    Args:
        **kwargs: Keyword arguments
    """

    match kwargs.get("case"): # TODO: implement better; keep this in alpha version
        # -- E4-2: for double-symmetric members twisting about the shear centre
        case "E4-2": # FIXME: passing in equation names?
            E = kwargs.get("E") # use default AISC 360-22 value of 29000 ksi # TODO: idea, make functions fully units agnostic or make them strictly unit specific, or make them add units in args.
            Cw = kwargs.get("Cw") # warping constant; use section's value # TODO: check section type before using this
            Lc_z = kwargs.get("Lc_z")
            G = kwargs.get("G") # Shear modulus; default AISC 360-22 value of 11200 ksi
            J = kwargs.get("J") # Torsional constant; use section's value # TODO: check section type before using this
            Fe = (np.pi ** 2) * E*Cw / (Lc_z ** 2) + G*J
            return round(Fe, ndigits=4)

        # -- E4-3: for single-symmetric members twisting about the shear centre where y-axis is axis of symmetry
        case "E4-3":
            Fe_y = kwargs.get("Fe_y")
            Fe_z = kwargs.get("Fe_z")
            H = kwargs.get("H")
            Fe = ((Fe_y + Fe_z)/2*H) * [1 - np.sqrt(1 - (4*H*Fe_y*Fe_z)/(Fe_y + Fe_z)^2)]
            return round(Fe, ndigits=4)

        case "E4-4":
            raise NotImplementedError("Flexural-torsional buckling stress calculation not implemented for unsymmetric members (equation E4-4). Try passing in 'case' as 'E4-2' or 'E4-3'.")
        
        case _:
            raise NotImplementedError("Invalid case. Try passing in 'case' as 'E4-2' or 'E4-3'.")

def EQ_4_2(case = "E4-2", **kwargs) -> Scalar | float:
    """ACI 360-22 Equation E4-2: Flexural-torsional buckling stress of compression members. Alias for flexural_torsional_buckling_stress().""" # TODO: put link to actual function in docstring.
    return flexural_torsional_buckling_stress(**kwargs)

def EQ_4_3(case = "E4-3", **kwargs) -> Scalar | float:
    """ACI 360-22 Equation E4-3: Flexural-torsional buckling stress of compression members. Alias for flexural_torsional_buckling_stress().""" # TODO: put link to actual function in docstring.
    return flexural_torsional_buckling_stress(**kwargs)

# TODO: have more aliases especially with nested equations or equations with multiple cases/variations.


# Parameters: Cw: warping constant (in^6); J: torsional constant (in^4); G: shear modulus;
# Ix, Iy: moments of inertia about x- and y-axes (in^4); Kx, Ky: effective length factors for flexural buckling about x- and y-axes;
# Kz: effective length factor for torsional buckling about longitudinal axis;
# Lx, Ly, Lz: laterally unbraced lengths; Lc_x, Lc_y, Lc_z: eff. lengths for buckling about x-, y- and longitudinal axis.
# rx, ry: radii of gyration; x0, y0: coordinates of shear centre w.r.t centroid
# r0_bar: polar radius of gyration about shear centre;

# eq. E4-5: Fe_x = (pi^2 * E) / (Lc_x * rx)^2
# eq. E4-6: Fe_y = (pi^2 * E) / (Lc_y * ry)^2

def calc_Fe_x(Lc_x: float, E: float, rx: float) -> Scalar | float:
    """ACI 360-22 Equation E4-5: Elastic buckling stress about x-axis.
    
    Args:
        Lc_x: Effective length about x-axis (in)
        E: Modulus of elasticity (ksi)
        rx: Radius of gyration about x-axis (in)
    """
    return (np.pi ** 2) * E / (Lc_x * rx) ** 2


def calc_Fe_y(Lc_y: float, E: float, ry: float) -> Scalar | float:
    """ACI 360-22 Equation E4-6: Elastic buckling stress about y-axis.
    
    Args:
        Lc_y: Effective length about y-axis (in)
        E: Modulus of elasticity (ksi)
        ry: Radius of gyration about y-axis (in)
    """
    return (np.pi ** 2) * E / (Lc_y * ry) ** 2

def EQ_4_5(Lc_x: float, E: float, rx: float) -> Scalar | float:
    """ACI 360-22 Equation E4-5: Elastic buckling stress about x-axis. Alias for calc_Fe_x().""" # TODO: put link to actual function in docstring.
    return calc_Fe_x(Lc_x, E, rx)

def EQ_4_6(Lc_y: float, E: float, ry: float) -> Scalar | float:
    """ACI 360-22 Equation E4-6: Elastic buckling stress about y-axis. Alias for calc_Fe_y().""" # TODO: put link to actual function in docstring.
    return calc_Fe_y(Lc_y, E, ry)

# eq. E4-7: Fe_z = [(pi^2 * E*Cw)/Lc_z^2 + GJ] + 1/(Ag * rbar_0^2)

def calc_Fe_z(Lc_z: float, E: float, Cw: float, G: float, J: float, Ag: float, r0_bar: float) -> Scalar | float:
    """ACI 360-22 Equation E4-7: Elastic buckling stress about z-axis.
    
    Args:
        Lc_z: Effective length about z-axis (in)
        E: Modulus of elasticity (ksi)
        Cw: Warping constant (in^6)
        G: Shear modulus (ksi)
        J: Torsional constant (in^4)
        Ag: Gross area (in^2)
        r0_bar: Polar radius of gyration about shear centre (in)
    """
    return (((np.pi**2)*E*Cw / (Lc_z ** 2)) + G*J) * (1 / (Ag * r0_bar ** 2))


def EQ_4_7(Lc_z: float, E: float, Cw: float, G: float, J: float, Ag: float, r0_bar: float) -> Scalar | float:
    """ACI 360-22 Equation E4-7: Elastic buckling stress about z-axis. Alias for _Fe_z().""" # TODO: put link to actual function in docstring.
    return calc_Fe_z(Lc_z, E, Cw, G, J, Ag, r0_bar)


# eq. E4-8: H: 1 - (x0^2 + y0^2)/r0_bar^2 i.e flexural constant

def flexural_constant(x0: float, y0: float, r0_bar: float) -> Scalar | float:
    """ACI 360-22 Equation E4-8: Flexural constant.
    
    Args:
        x0: Coordinate of shear centre about x-axis (in)
        y0: Coordinate of shear centre about y-axis (in)
        r0_bar: Polar radius of gyration about shear centre (in)
    """
    return 1 - (x0**2 + y0**2) / (r0_bar**2)

def EQ_4_8(x0: float, y0: float, r0_bar: float) -> Scalar | float:
    """ACI 360-22 Equation E4-8: Flexural constant. Alias for flexural_constant().""" # TODO: put link to actual function in docstring.
    return flexural_constant(x0, y0, r0_bar)

# eq. E4-9: r0_bar^2: x0^2 + y0^2 + (Ix + Iy)/Ag  # TODO: find good symbol
def calc_r0_bar2(x0: float, y0: float, Ix: float, Iy: float, Ag: float) -> Scalar | float:
    """ACI 360-22 Equation E4-9: #FIXME: Find correct name but seems to be squared polar radius of gyration about shear centre.
    
    Args:
        x0: Coordinate of shear centre about x-axis (in)
        y0: Coordinate of shear centre about y-axis (in)
        Ix: Moment of inertia about x-axis (in^4)
        Iy: Moment of inertia about y-axis (in^4)
        Ag: Gross area (in^2)
    """
    return x0**2 + y0**2 + (Ix + Iy)/Ag

# TODO: have aliases of functions using equation signatures: eg def EQ_4_2() as an alias for def flexural_torsional_buckling_stress(**kwargs) -> Scalar | float:
# TODO:: put them in the aliases folder and document properly. Put link to actual function in docstring.

# NOTE: For doubly symmetric I-shaped sections, Cw may be taken as Iyho2/4, where ho is the distance between flange centroids, in lieu of a more precise analysis.
# NOTE: For tees and double angles, omit the term with Cw when computing Fez and take xo as 0.
# NOTE: For members with lateral bracing offset from the shear center, the elastic buckling stress, Fe, shall be determined by analysis.
# NOTE: Members with lateral bracing offset from the shear center are susceptible to constrained-axis torsional buckling, which is discussed in the Commentary.

# E5. Single Angle Compression Members
# TODO: is detailed/elaborate... implement later.

# E6. Built-up members
# [NO IMPLEMNETATION PLANNED]

# E7. Members with slender elements: applies to slender elements as defined in B4.1
# Pn lowest value for flexural buckling, torsional buckling and flexural-torsional buckling in interaction with local buckling.
# eq. E7-1: Pn = Fcr*Ae ; Ae:summation of the effective areas of the cross section based on reduced effective widths, be, de or he, or the area as given by Equations E7-6 or E7-7 
# Fcr: critical stress according to E3 or E4; NOTE: for single angles, determine according to E3 ONLY
# NOTE: The effective area, Ae, may be determined by deducting from the gross area, Ag, the reduction in area of each slender element determined as (b − be)t.

# Determing effective width be (is de for tees and he for webs)
# E7.1 All members excluding Round HSS
# eq. E7-2: when lambda <= lambda_r * sqrt(Fy/Fcr) then be = b 
# eq. E7-3: when lambda > lambda_r * sqrt(Fy/Fcr) then be = b * [ 1 - c1*(sqrt(Fel/Fcr))] * sqrt(Fel/Fcr)
# b = width (d for tees, h for web)
# c1 = effective width imperfection adjustment factor from table E7.1
# case (a), case (b) and case (c) # TODO: implement case (c) i.e all other elements - c1 = 0.22, c2 = 1.49
# eq E7.4: c2 = ( 1 - sqrt(1 - 4*c1))/2*c1
# lambda = width-to-thickness ratio for the element as defined in Section B4.1
# lambda_r = limiting width-to-thickness ratio as defined in Table B4.1a

def calc_effective_width_be(lambda_value: float, lambda_r: float, Fy: float, Fn: float, **kwargs) -> Scalar | float:
    """ACI 360-22 Equation E7-2 & E7-3: Effective width for slender elements.
    
    Args:
        lambda_value: Width-to-thickness ratio for the element as defined in Section B4.1
        lambda_r: Limiting width-to-thickness ratio as defined in Table B4.1a
        **kwargs: Keyword arguments
    """
    #// llr = lambda_value / lambda_r # FIXME: find better notation; python uses lambda keywork and Lambda is too close to it; implies uppercase lambda as
    conditional = lambda_r * np.sqrt(Fy/Fn)
    match lambda_value <= conditional:
        case True:
            b = kwargs.get("b")
            return b
        case False:
            c1 = kwargs.get("c1")
            Fel = kwargs.get("Fel")
            Fcr = kwargs.get("Fcr")
            return b * (1 - c1 * (np.sqrt(Fel / Fcr))) * np.sqrt(Fel / Fcr)
        case _:
            raise NotImplementedError("Function is still rudimentary & untested.")

def calc_c2(c1: float) -> Scalar | float:
    """ACI 360-22 Equation E7-4: Effective width imperfection adjustment factor from table E7.1.
    
    Args:
        c1: Effective width imperfection adjustment factor from table E7.1
    """
    # TODO: fix for other cases/make more robust
    return (1 - np.sqrt(1 - 4*c1)) / (2*c1)

# eq E7.5: Fel = (c2 * lambda_r/lambda)^2 * Fy i.e elastic local buckling stress; can be calculated

# E7.2: Round HSS
# Determine effective area Ae
# eq E7.6: when D/t <= 0.11*E/Fy then Ae = Ag
# eq E7.7: when 0.11*E/Fy < D/t < 0.45*E/Fy then Ae = [ 0.038E/Fy(D/t) + 2/3]*Ag; D: outside diameter, t: thickness

def Ae_for_round_HSS(D: float, t: float, Fy: float, Ag: float, E: float) -> Scalar | float:
    """ACI 360-22 Equation E7-6 and E7-7: Effective area for round HSS.
    
    Args:
        D: Outside diameter (in)
        t: Thickness (in)
        Fy: Specified minimum yield stress (kpsi)
        Ag: Gross area (in²)
        E: Modulus of elasticity (ksi)
    """
    if D/t <= 0.11*E/Fy:
        return Ag
    elif 0.11*E/Fy < D/t < 0.45*E/Fy:
        return (0.038*E/Fy*D/t + 2/3)*Ag
    else:
        raise NotImplementedError("Function is still rudimentary & untested.")

# ---------------------------------------------------------------------------------

# Chapter F: Flexure
# NOTE: see selection table on User Note F1.1
# F1. General provisions... # TODO: elaborate and useful; go over and document
# eq. F1-1 Cb, LTB modification factor for nonuniform BMDs when both ends of the segment are braced

# F2. Compact I-shaped members and channels bent about their major axis
# F2.1 Flexural Yielding
# F2.2 Lateral-Torsional Buckling

# F3. I-shaped members with compact webs and noncompact or slender flanges bent about their major axis
# F3.1 Lateral-Torsional Buckling: use F2.2
# F3.2 Compression Flange Local Buckling

# F4. Other I-shaped members with compact or noncompact webs bent about their major axis
# NOTE: preferrably designed conservatively to F5.
# F4.1 Compression Flange Yielding
# F4.2 Lateral-Torsional Buckling
# F4.3 Compression Flange Local Buckling
# F5.4 Tension Flange Yielding

# F5. I-shaped members with slender webs bent about their major axis
# F5.1 Compression Flange Yielding
# F5.2 Lateral-Torsional Buckling
# F5.3 Compression Flange Local Buckling
# F5.4 Tension Flange Yielding

# F6. I-shaped members bent about their minor axis
# F6.1 Yielding
# F6.2 Flange Local Buckling

# F7. Square and Rectangular HSS, and Box Sections
# F7.1 Yielding
# F7.2 Flange Local Buckling
# F7.3 Web Local Buckling
# F7.4 Lateral-Torsional Buckling

# F8. Round HSS
# F8.1 Yielding
# F8.2 Local Buckling

# F9. Tees and Double Angles loaded in the plane of symmetry
# F9.1 Yielding
# F9.2 Lateral-Torsional Buckling
# F9.3 Flange Local Buckling of Tees and Double-Angle legs
# F9.4 Local Buckling of Tee Stems and Double-Angle Web Legs in Flexurual Compression

# F10. Single Angles
# F10.1 Yielding
# F10.2 Lateral-Torsional Buckling
# F10.3 Leg Local Buckling

# F11. Rectangular Bars and Rounds # TODO: check if present,
# F11.1 Yielding
# F11.2 Lateral-Torsional Buckling

# F12. Unsymmetric Members
# [NO IMPLEMENTATION PLANNED] # FIXME: double check but doubtful any database has unsymmetric sections

# F13. Proportions of Beams & Girders
# TODO: seems necessary, implement for rolled sections.

# ---------------------------------------------------------------------------------
# Chapter G: Shear
# G2. I-shaped members and Channels
# G2.1 Shear Strength of Webs without Tension Field Action
# G2.2 Shear Strength of Interior Web Panels with a / h ≤ 3 Considering Tension Field Action
# G2.3 Transverse Stiffeners

# G3. Single Angles and Tees
# eq. G3-1: Nominal shear strength Vn of a single angle or tee
# Vn = 0.6 * Fy * bt * Cv2; Cv2 = web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 1.2

def calc_Vn_for_single_angle(b: float, t: float, Fy: float, Cv2: float) -> Scalar | float:
    """ACI 360-22 Equation G3-1: Nominal shear strength Vn of a single angle or tee.
    
    Args:
        b: Width (in)
        t: Thickness (in)
        Fy: Specified minimum yield stress (kpsi)
        Cv2: Web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 1.2
    """
    return 0.6 * Fy * b * t * Cv2

def calc_Vn_for_tee(b: float, t: float, Fy: float, Cv2: float) -> Scalar | float:
    """ACI 360-22 Equation G3-1: Nominal shear strength Vn of a tee.
    
    Args:
        b: Width (in)
        t: Thickness (in)
        Fy: Specified minimum yield stress (kpsi)
        Cv2: Web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 1.2
    """
    return calc_Vn_for_single_angle(b, t, Fy, Cv2)

def EQ_G3_1(b: float, t: float, Fy: float, Cv2: float) -> Scalar | float:
    """ACI 360-22 Equation G3-1: Nominal shear strength Vn of a single angle or tee. Alias for calc_Vn_for_single_angle_or_tee().""" # TODO: put link to actual function in docstring.
    return calc_Vn_for_single_angle(b, t, Fy, Cv2)

# G4. Rectangular HSS, Box Sections, and other singly/doubly symmetric members
# eq. G4-1: Nominal shear strength Vn
# Vn = 0.6 * Fy * Aw * Cv2; Cv2 = web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 5.0

def calc_Vn_for_rectangular_HSS(h: float, t: float, Fy: float, Cv2: float) -> Scalar | float:
    """ACI 360-22 Equation G4-1: Nominal shear strength Vn of rectangular HSS or box sections.
    
    Args:
        h: Width resisting the shear force (in)
        t: Wall thickness (in)
        Fy: Specified minimum yield stress (kpsi)
        Cv2: Web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 5.0
    """
    return 0.6 * Fy * h * t * Cv2

def calc_Vn_for_box_sections(h: float, t: float, Fy: float, Cv2: float) -> Scalar | float:
    """ACI 360-22 Equation G4-1: Nominal shear strength Vn of rectangular HSS or box sections.
    
    Args:
        h: Width resisting the shear force (in)
        t: Wall thickness (in)
        Fy: Specified minimum yield stress (kpsi)
        Cv2: Web shear buckling coefficient from G2.2 with hw/tw = b/t and kv = 5.0
    """
    return calc_Vn_for_rectangular_HSS(h, t, Fy, Cv2)

# For Rectangular HSS and Box Sections, 
# Aw = 2ht; t: wall thickness, h: width resisting the shear force i.e # TODO: complete.
# For other singly or doubly symmetric members, 
# Aw = d*tw; t: web thickness h = width resisting the shear force i.e # TODO: complete.

# G5. Round HSS
# eq. G5-8 Vn = Fcr * Ag/2; Ag: gross area
# eq. G5-9 Fcr is the larger of:
# (a) - 1.60E/(sqrt(Lv/D) * (D/t)^1.25); Lv: distance from maximum to zero shear force, 
# (b) - 0.78E/(D/t)^1.5;  D: outside diameter, t: thickness,
# NOTE: The shear buckling equations, Equations G5-2a and G5-2b, will control for D/ t over 100, high-strength steels, and long lengths.
# NOTE: For standard sections, shear yielding will usually control and Fcr = 0.6Fy.

# G6. Weak-axis shear in singly/doubly symmetric members
# eq. G6-1 Vn if loaded in the weak axis without torsion
# Vn = 0.6 * Fy * bf * tf * Cv2; bf: flange width, tf: flange thickness
# Cv2 = web shear buckling coefficient from G2.2 with h/tw = bf/tf for I sections & tees, or h/tw = bf/tf for channels, and kv = 1.2
# NOTE: For all ASTM A6 W, S, M and HP shapes, when Fy ≤ 70 ksi(485 MPa), Cv2 = 1.0.

# G7. Beams and Girders with Web Openings
# [NO IMPLEMENTATION PLANNED]

# ---------------------------------------------------------------------------------
# Chapter H: Combined Forces and Torsion
# addresses members subject to axial force and flexure about one or both axes, with or without torsion, and members subject to torsion only.
# H1. Doubly and Singly Symmetric Members Subject to Flexure and Axial Force
# H1.1. Singly/Doubly Symmetric Members Subject to Axial Compression and Flexure # NOTE: H2 is permitted in lieu of H1.1 
# eq. H1-1(a): when Pr/Pc >= 0.2 : Pr/Pc + 8/9 * (Mrx/Mcx + Mry/Mcy) ≤ 1.0
# eq. H1-1(b): when Pr/Pc < 0.2 : Pr/2*Pc + (Mrx/Mcx + Mry/Mcy) ≤ 1.0
# where Pr: required axial strength according to Chapter C; Pc: available* axial compressive strength from Chapter E # TODO: clarify available*, but from latter notes, seems to be design for LRFD and allowable for ASD
# and Mr: required flexural strength according to Chapter C; Mc: available* flexural strength from Chapter F
# for LRFD: Pc = phi_c*Pn and Mc = phi_b*Mn; phi_c = phi_b = 0.9

# H1.2 Doubly and Singly Symmetric Members Subject to Flexure and Tension
# if bent about x- and/or y-axis, use eq. H1-1(a) or H1-1(b) where Pc = phi_t*Pn; refer phi_t from Chapter D
# NOTE: for doubly symmetric members, Cb (LTB mod. factor) may be .... #  TODO: complete, but not urgent/important, but complete.

# H1.3 Doubly Symmetric Rolled Compact Members Subject to Single-Axis Flexure and Compression
# TODO: is elaborate, complete
# NOTE: check in-plane stability and out-of-plane stability or lateral-torsional buckling, separately in lieu of the combined approach in H1.1
# NOTE: For members with Mry/Mcy ≥ 0.05, the provisions of Section H1.1 shall be followed.
# NOTE: In Equation H1-3, Cb*Mcx may be larger than phi_b*Mpx(in LRFD). The yielding resistance of the beam-column is captured by eq. H1-1.
# For the limit state of in-plane instability, Equations H1-1a and H1-1b shall be used with Pc taken as the available compressive strength in the plane of bending and Mcx taken as the available flexural strength based on the limit state of yielding
# eq. H1-3: For the limit state of out-of-plane buckling and lateral-torsional buckling:
# Pr/Pcy * (1.5 - 0.5*Pr/Pcy) + (Mrx/Cb*Mcx)^2 ≤ 1.0; 
# Mcx: available* LTB strength for major axis bending in Chapter F when Cb = 1.0
# Pcy: available* compressive strength out of the plane of bending

# H2. Unsymmetric and Other Members Subject to Flexure and Axial Force
# NOTE: no unsymmetric sections implemented yet, so ignore for now

# H3. Members Subject to Torsion and Combined Torsion, Flexure, Shear, and/or Axial Force
# H3.1 Round and Rectangular HSS Subject to Torsion, for torsional yielding and torsional buckling limit states
# eq. H3-1: phi_T*Tn = Fcr*C; phi_T = 0.9 # NOTE: phi_T != phi_t, # TODO: resolve in docs i.e tricky_symbols.md for all EU/UK/US etc. include A, a i.e lowercase uppercase, greek letters and shared/common symbols
# C is the torsional constant for HSS
# NOTE: The torsional constant, C, may be conservatively taken as: # TODO: complete
# Fcr: ... # TODO: complete

# H3.2 HSS Subject to Combined Torsion, Shear, Flexure, and Axial Force
# #TODO: clarify provision for 20% Tr
# eq. H3-6: (Pr/Pc + Mr/Mc) + (Vr/Vc + Tr/Tc)^2 ≤ 1.0

# H3.3 Non-HSS Members Subject to Torsion and Combined Stress
# Will be lowest value of Fn in yielding under normal stress, shear yielding (under shear stress) or buckling
# Constrained local yielding is permitted adjacent to areas that remain elastic.
# eq. H3-7: for yielding under normal stress: Fn = Fy
# eq. H3-8: for shear yielding under shear stress: Fn = 0.6*Fy
# eq. H3-9: for buckling: Fn = Fcr; Fcr is determined by analysis.


# H4. Rupture of Flanges with Holes Subjected to Tension
# at location of bolt holes... [NO IMPLEMENTATION PLANNED]

# ---------------------------------------------------------------------------------

# Chapter I: Composite Members
# [NO IMPLEMENTATION PLANNED] for built-up members