import numpy as np
from typing import Any, Optional, Union, Literal, cast
from steelsnakes.base.checks import UtilisationCheck, Scalar, Reference, SectionClass
from steelsnakes.base.sections import BaseSection, SectionType

# from steelsnakes.base.checks import BaseCheck   
# TODO: Write equations with clauses

# 6 - ULS
# 6.1.1 - General
# Partial factors according to 2.4.3
gamma_m0 = 1.0 # x-section resistance, whatever the class
gamma_m1 = 1.0 # resistance of members to instability assessed by member checks
gamma_m2 = 1.25 # resistance of x-sections in tension to fracture; is 1.10 in UK NA to EN 1993-1-1:2005 

# --------------------------------------------------------------------------------------
# eq. 6.2; for Class 1, 2, 3 sections
# (N_Ed/N_Rd + My_Ed/My_Rd + Mz_Ed/Mz_Rd) <= 1.0
# eq. 6.3; for Class 4 sections
# Cl. 6.2.3 Tension (Axial)
# eq. 6.5
# N_Ed/N_tRd <= 1.0; N_tRd = design tension resistance

def tension_utilisation(N_Ed: float, N_tRd: float) -> UtilisationCheck:
    # FIXME: Fix referencing style to be useful & consistent. Pick codes' versions e.g AISC 360-22, EN 1993-1-1:2005, BS EN 1993-1-1:2022, etc.
    """EN 1993-1-1:2005 equation 6.5: Tension utilisation for Class 1, 2 & 3 sections. Class 4 sections are not implemented in `steelsnakes`.
    Args:
        N_Ed: Design axial force (N)
        N_tRd: Design axial tension resistance (N)

    Returns:
        Tension utilisation (N_Ed / N_tRd)
    """
    utilisation = np.divide(N_Ed, N_tRd) # N_Ed / N_tRd
    return UtilisationCheck(
        utilisation=round(utilisation, ndigits=3),
        metadata={},
        adequacy="OK" if utilisation <= 1.0 else "FAILS",  # TODO: improve, check against tolerances using numpy
        reference=Reference(code="EN_1993", clause="6.2.3", equation="6.5")
    )

# --------------------------------------------------------------------------------------

# Cl. 6.2.4 Compression (Axial)
# eq. 6.9
# N_Ed/N_cRd <= 1.0; N_cRd = design compression resistance

def compression_utilisation(N_Ed: float, N_cRd: float) -> UtilisationCheck:
    """EN 1993-1-1:2005 equation 6.9: Compression utilisation for Class 1, 2 & 3 sections. Class 4 sections are not implemented in `steelsnakes`.
    
    Args:
        N_Ed: Design axial force (N)
        N_cRd: Design axial compression resistance (N)

    Returns:
        Compression utilisation (N_Ed / N_cRd)
    """
    utilisation = np.divide(N_Ed, N_cRd) # N_Ed / N_cRd
    # return {
    #     "Utilisation": np.round(utilisation, ndigits=3),
    #     "Adequacy": "OK" if utilisation <= 1.0 else "FAILS", # TODO: improve, check against tolerances using numpy
    #     "Metadata": {},
    #     # "Clause": ClauseRef(code="6.2.4", clause="Compression (Axial)") # TODO: I like this.

    # }

    return UtilisationCheck(utilisation=utilisation, metadata={}, adequacy="OK" if utilisation <= 1.0 else "FAILS", reference=Reference(code="EN_1993", clause="6.2.4", equation="6.9"))

# eq. 6.10, for Class 1, 2, 3 sections
# N_cRd = A * f_y / gamma_M0; f_y = design yield strength

def design_axial_compression_resistance(A: float, fy: float, gamma_M0: float = 1.0) -> Scalar | float: # FIXME: resolve in design
    """EN 1993-1-1:2005 equation 6.10: Design axial compression resistance N_cRd for Class 1, 2 & 3 sections. Class 4 sections are not implemented in `steelsnakes`.
    
    Args:
        A: Cross-sectional area (mm²)
        fy: Design yield strength (N/mm²)
        gamma_M0: Partial safety factor for resistance of x-sections. Default is 1.0.

    Returns:
        Design axial compression resistance N_cRd (N)
    """
    N_cRd = np.divide(A*fy, gamma_M0)
    # return Scalar(value=N_cRd, units="N") # TODO: will other programs/apps break when Scalar type is used?
    return round(N_cRd, ndigits=4) # TODO: resolve in design
    # FIXME: round everything to 4 decimal places? probably unnecessary.


# --------------------------------------------------------------------------------------

# Cl. 6.2.5 Bending moment
# eq. 6.12
# M_Ed/M_cRd <= 1.0; M_cRd = design moment resistance
def moment_utilisation(M_Ed: float, M_cRd: float) -> UtilisationCheck | dict[str, Any]:
    """EN 1993-1-1:2005 equation 6.12: Bending moment utilisation
    
    Args:
        M_Ed: Design bending moment (Nm)
        M_cRd: Design moment resistance (Nm)

    Returns:
        Moment utilisation (M_Ed / M_cRd)
    """
    utilisation = np.divide(M_Ed, M_cRd) # M_Ed / M_cRd
    return {
        "Utilisation": round(utilisation, ndigits=3),
        "Metadata": {}
    }


# eq 6.13, for Class 1 & 2 sections
# M_cRd = M_plRd = W_pl * f_y / gamma_M0; W_pl = plastic section modulus
def design_moment_resistance(section_class: SectionClass, W_el: Optional[float], W_pl: Optional[float], fy: float, gamma_M0: float = 1.0) -> Scalar | float: # FIXME: resolve in design
    # FIXME: should take 1, class 1, class 2, CLASS 2 etc
    """EN 1993-1-1:2005 equation 6.13: Design moment resistance M_cRd for Class 1, 2 sections. Class 4 sections are not implemented in `steelsnakes`.
    
    Args:
        section_class: Section class
        W_el: Elastic section modulus (mm³)
        W_pl: Plastic section modulus (mm³)
        fy: Design yield strength (N/mm²)
        gamma_M0: Partial safety factor for resistance of x-sections. Default is 1.0.

    Returns:
        Design moment resistance M_cRd (Nmm)
    """
    match section_class:
        case SectionClass.CLASS_1 | SectionClass.CLASS_2:
            if W_pl is None:
                raise ValueError("Plastic section modulus W_pl is required for Class 1 and Class 2 sections.")
            M_cRd = np.divide(W_pl*fy, gamma_M0) # FIXME: assuming data from tables is used directly, check units...
        case SectionClass.CLASS_3:
            if W_el is None:
                raise ValueError("Elastic section modulus W_el is required for Class 3 sections.")
            M_cRd = np.divide(W_el*fy, gamma_M0) # FIXME: assuming data from tables is used directly, check units...
        case SectionClass.CLASS_4:
            raise NotImplementedError("Class 4 sections are not implemented in `steelsnakes`.")
        case _:
            raise ValueError(f"Section class {section_class} is not implemented in `steelsnakes`.")
    
    # TODO: steelsnakes 2.0 should ship units in code and database
    # return Scalar(value=round(M_cRd, ndigits=4), units="Nmm", metadata={"section_class": section_class}) # TODO: will other programs/apps break when Scalar type is used?
    return round(M_cRd, ndigits=4)


# eq 6.14, for Class 3 sections
# M_cRd = M_elRd = W_el * f_y / gamma_M0 ; W_el = elastic section modulus
# FIXME: not implementing class 4 sections
# eq 6.15, for Class 4 sections
# M_cRd = W_eff_min or W_el_min * f_y / gamma_M0; W_eff_min = minimum effective section modulus

# --------------------------------------------------------------------------------------

# Cl. 6.2.6 Shear
# eq. 6.17
# V_Ed/V_cRd <= 1.0; V_cRd = design shear resistance; is V_plRd for plastic design and V_leRd for elastic design

def shear_utilisation(V_Ed: float, V_cRd: float) -> UtilisationCheck:
    """EN 1993-1-1:2005 equation 6.17: Shear utilisation
    
    Args:
        V_Ed: Design shear force (N)
        V_cRd: Design shear resistance (N)

    Returns:
        Shear utilisation (V_Ed / V_cRd)
    """
    utilisation = np.divide(V_Ed, V_cRd) # V_Ed / V_cRd
    # return {"Utilisation": np.round(utilisation, ndigits=3), "Metadata": {}}
    return UtilisationCheck(utilisation=utilisation, metadata={}, adequacy="OK" if utilisation <= 1.0 else "FAILS", reference=Reference(code="EN_1993", clause="6.2.6", equation="6.17"))


# eq. 6.18, in absence of torsion
# V_plRd = Av * (f_y / sqrt(3)) / gamma_M0; Av = shear area

def design_shear_resistance(Av: float, fy: float, gamma_M0: float = 1.0) -> Scalar | float:
    """EN 1993-1-1:2005 equation 6.18: Design shear resistance V_cRd in the absence of torsion
    
    Args:
        Av: Shear area (mm²)
        fy: Design yield strength (N/mm²)
        gamma_M0: Partial safety factor for resistance of x-sections. Default is 1.0.
    """
    V_cRd = np.divide(Av*100 * fy, gamma_M0)
    # return Scalar(value=V_cRd, units="N")
    return round(V_cRd, ndigits=4)

# Cl 6.2.6.3 Shear Area Av
# Cl 6.2.6.3(a) - Rolled I/H sections - Av = A - 2*b*tf + (tw + 2*r)*tf, but > eta*hw*tw # TODO: perform this check... but take eta conservatively as zero; make sure to include all conservative values in docs/specs
# Cl 6.2.6.3(b) - Rolled Channels; load // web - 
# Cl 6.2.6.3(c) - Rolled T; load // web - 
# Cl 6.2.6.3(f) - Rolled RHS: load // d and load // b - 
# Cl 6.2.6.3(g) - All CHS - Av = 2 * A / pi

def shear_area(section: Optional[BaseSection] = None, properties: Optional[dict[str, Any]] = None) -> Any:
    """
    EN 1993-1-1:2005 clause 6.2.6.3: Shear area Av.
    eta = 1.00 in Clause NA.2.4 of UK NA to EN 1993-1-1:2005
    Provide either a section valid for EU/UK or a dictionary of properties. # TODO: implement resolution for properties, but for now just throw an error.
    """
    # ... but can't provide both section and properties
    match section, properties:
        # Neither section nor properties provided
        case (None, None):
            raise ValueError("Either section or properties must be provided.")
        
        # Only properties provided, calculate using given properties
        case (None, _):
            # section = BaseSection.from_properties(properties)
            return NotImplementedError("Shear area for custom section properties is not yet implemented in `steelsnakes`.") # TODO: implement
        
        # Only section provided, calculate using given section
        case (_, None):
            # section = BaseSection.from_section(section) #FIXME: should be a check if section is/abstracts BaseSection
            section_type: SectionType = section.get_section_type()
            match section_type:
                # Rolled I/H sections: UB, UC, UBP, HE, IPE, HE, HL, HLZ, HD, HP, 
                case SectionType.IPE | SectionType.HE | SectionType.HL | SectionType.HLZ | SectionType.HD | SectionType.HP | SectionType.UB | SectionType.UC | SectionType.UBP:
                    Av = section.A*100 - 2*section.b*section.tf + (section.tw + 2*section.r)*section.tf # FIXME: Because in A (cm2) in EU/UK tables
                    eta = 1.00 # in Clause NA.2.4 of UK NA to EN 1993-1-1:2005
                    # if section.hw is None:
                    #     hw = section.h - 2*section.tf - 2*section.r # clear height of web
                    #     Av_min = eta*hw*section.tw # for rolled I/H sections only, loaded parallel to web
                    # else:
                    #     Av_min = eta*section.hw*section.tw # FIXME: unlikely, handle as edge case e.g user added custom section and included hw in parameters
                    hw = section.h - 2*section.tf - 2*section.r # clear height of web
                    Av_min = eta*hw*section.tw # for rolled I/H sections only, loaded parallel to web
                    return {"Av": Av, "Av_min": Av_min}
        
                # Rolled Channels: PFC, UPE, UPN; loaded parallel to web
                case SectionType.PFC | SectionType.UPE | SectionType.UPN:
                    return section.A*100 - 2*section.b*section.tf + (section.tw + section.r)*section.tf

                # Rolled RHS: // depth and // width
                case SectionType.RHS:
                    return {
                        "// depth": section.A*100*section.h / (section.b + section.h),
                        "// width": section.A*100*section.b / (section.b + section.h)
                    }

                # CHS: loaded parallel to depth
                case SectionType.CFCHS | SectionType.CFRHS | SectionType.CFSHS | SectionType.HFCHS | SectionType.HFRHS | SectionType.HFSHS | SectionType.HFEHS:
                    return 2*section.A*100 / np.pi
                
                # NO IMPLEMENTATION FOR WELDED/BUILT-UP SECTIONs
        
        # Both section and properties provided, raise error
        case (_, _):
            raise ValueError("Either section or properties must be provided, not both.")
    


# TODO: Complete and verify
#// eq. 6.19, shear stress verification
#// tau_Ed/(f_y / (sqrt(3)) * gamma_M0) <= 1.0; tau_Ed = design shear stress
#// eq. 6.20, shear stress
#// tau_Ed = (V_Ed * S)/(It)
# TODO: see note for cl. 6.2.6.4
# Cl. 6.2.6.5; shear stress in web for I/H sections
# eq. 6.21
# tau_Ed = (V_Ed * Aw) if Af >= 0.6Aw; Af is area in one flange, Aw is area in the web i.e hw*tw
def web_shear_stress(
    V_Ed: float, 
    section: Optional[BaseSection] = None,
    properties: Optional[dict[str, Any]] = None,
    Aw: Optional[float] = None, # Area in the web: hw*tw
    Af: Optional[float] = None) -> Scalar: # Area of the tension flange: b*tf
    """EN 1993-1-1:2005 equation 6.21: Shear stress in web for I/H sections
    
    Args: ...

    Returns:
        Shear stress (tau_Ed)
    """
    match section, properties:
        case (None, None):
            raise ValueError("Either section or properties must be provided.")
        case (_, None):
            hw = section.h - 2*section.tf - 2*section.r # clear height of web
            Aw = hw*section.tw
            Af = section.b*section.tf
            tau_Ed = np.multiply(V_Ed, Aw)
            return round(tau_Ed, ndigits=4)
        case (_, _):
            raise ValueError("Either section or properties must be provided, not both.")


# --------------------------------------------------------------------------------------

# Cl. 6.2.7 Torsion
# TODO: do worked example and implement

# --------------------------------------------------------------------------------------

# Cl. 6.2.8 Bending & Shear
# eq. 6.29 - Reduced plastic moment resistance due to shear # TODO: include in docs that resitance [EN] is capacity [UK]; compare with American codes
# fy_reduced = f_y * (1 - rho); rho = ((2*V_Ed / V_plRd) - 1)^2

def reduced_yield_strength(fy: float, V_Ed: float, V_plRd: float) -> Scalar:
    """EN 1993-1-1:2005 equation 6.29: Reduced yield strength due to shear.
    Calculates rho as V_Ed/V_plRd.
    
    Args:
        fy: Design yield strength (N/mm²)
        V_Ed: Design shear force (N)
        V_plRd: Design plastic shear resistance (N)
    """
    rho = np.power(2*V_Ed / V_plRd - 1, 2)
    fy_reduced = fy * (1 - rho)
    return round(fy_reduced, ndigits=4)

# TODO: implement effect on torsion [not urgent]
# eq. 6.30 - reduced design plastic resistance moment for I/H sections with equal flanges and bending about major axis
# My_VRd = (W_pl_y - rho....) # TODO: complete...
# TODO: complete...

# --------------------------------------------------------------------------------------
# TODO: implement feature that some checks/equations/clauses are only applicable to certain section types e.g just rolled hollow, just RHS, just I/H, etc.

# Cl. 6.2.9 Bending & Axial Force
# Cl. 6.2.9.1 Class 1 & 2 sections
# Cl. 6.2.9.1(4) - checks for allowance of axial force on bending resistance for double symmetric I/H sections... # TODO: complete docs
# eq. 6.33 N_Ed < 0.25*N_plRd ; about y-y axis (major)
# eq. 6.34 N_Ed <= 0.5*hw*tw*f_y/gamma_M0 ; about y-y axis (major)
# eq. 6.35 N_Ed <= hw*tw*f_y/gamma_M0 ; about z-z axis (minor)
# Cl. 6.2.9.1(5) - ...
# ... for RHS of uniform thickness (rolled only)
# eq. 6.39 M_NyRd = M_plyRd(1 - n)/(1 - 0.5*aw) but <= M_plyRd
# eq. 6.40 M_NzRd = M_plzRd(1 - n)/(1 - 0.5*af) but <= M_plzRd
# where  aw = (A - 2*b*t)/A but <= 0.5; af = (A - 2*h*t)/A but <= 0.5; n = N_Ed/N_plRd
# Cl. 6.2.9.1(6) Biaxial Bending
# eq. 6.41 interaction formula for biaxial bending about major and minor axis
# (My_Ed/M_NyRd)^alpha + (Mz_Ed/M_NzRd)*beta <= 1.0

def biaxial_bending_utilisation(My_Ed: float, Mz_Ed: float, M_NyRd: float, M_NzRd: float, alpha: float = 1.0, beta: float = 1.0) -> UtilisationCheck:
    """EN 1993-1-1:2005 equation 6.41: Biaxial bending utilisation for Class 1 and Class 2 sections only.
    
    Args:
        My_Ed: Design bending moment about major axis (Nm)
        Mz_Ed: Design bending moment about minor axis (Nm)
        M_NyRd: Design bending moment resistance about major axis (Nm)
        M_NzRd: Design bending moment resistance about minor axis (Nm)
        alpha: Constant. Default is 1.0. See EN 1993-1-1:2005 Clause 6.2.9(6).
        beta: Constant. Default is 1.0. See EN 1993-1-1:2005 Clause 6.2.9(6).
    """
    # TODO: implemetation with section type not necessary; simply pass in required values
    utilisation = (My_Ed/M_NyRd)**alpha + (Mz_Ed/M_NzRd)**beta
    return UtilisationCheck(utilisation=utilisation, metadata={}, adequacy="OK" if utilisation <= 1.0 else "FAILS", reference=Reference(code="EN_1993", clause="6.2.9.1", equation="6.41"))

# conservatively, alpha = beta = 1.0 # TODO: implement more accurate values from code per section
# I/H sections: alpha = 2.0, beta = 5n but >= 1.0;
# CHS: alpha = beta = 2.0
# RHS: ... TODO: complete; just use 1.0

# Cl. 6.2.9.2 Class 3 sections
# Cl. 6.2.9.2(1) in absence of shear force, check maximum longitudinal stress sigma_xEd
# sigma_xEd <= f_y/gamma_M0; calculated as design value of local longitudinal stress due to moment and axial force accounting for holes... see 6.2.3, 6.2.4 & 6.2.5

# def sigma_xED # TODO: complete; correct previous function to Class 1 & 2 only...

# FIXME: not implementing class 4 sections

# --------------------------------------------------------------------------------------

# Cl. 6.2.10 Bending, Shear & Axial Force
# TODO: do worked example and implement

# --------------------------------------------------------------------------------------


if __name__ == "__main__":
    # check = BaseCheck()
    # print(check)
    print("")
    from steelsnakes.UK import UB
    from steelsnakes.EU.beams import IPE
    from steelsnakes.EU.channels import UPN, PFC
    from steelsnakes.UK.cf_hollow import CFCHS
    # element = IPE("IPE-500")
    element = UB("457x191x67")
    # element = PFC("430x100x64")
    # element = CFCHS("300x300x10")
    print(shear_area(element))
    print(web_shear_stress(1000, element))