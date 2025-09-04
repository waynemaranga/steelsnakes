""""""
from __future__ import annotations
import numpy as np
from steelsnakes.base.checks import Classification, SectionClass
# B4. Member Properties
# B4.1. Classification of Sections for Local Buckling
# -- For axial compression: nonslender-element members have with-to-thickness ratios <= lambda_r from table B4.1a, else slender-element.
# --- For flexure: compact sections have width-to-thickness ratios <= lambda_p from table B4.1b, else noncompact if <= lambda_r, else slender-element.
# B4.1a. Unstiffened elements
# B4.1b. Stiffened elements
# TODO: Reproduce necessary tables in documentation e.g Tables B4.1a, B4.1b.
# TODO: For programming and documentation, only provide case numbers and checks per case, user should refer to tables
# TODO: In section libraries, have functions referring to case as eq. et cetera
# TODO: Clarify stiffened vs unstiffened elements in docstring and documentation especially for UK/EU people

# Table B4.1a. lambda_r for compression elements 
# (Unstiffened: cases 1, 2, 3 and 4)
# Case 1: wttr = b/t; lambda_r = 0.56*sqrt(E/Fy);
# Case 2: wttr = b/t; lambda_r = 0.64*sqrt(kc*E/Fy); and kc = 4/sqrt(h/tw) but 0.35 <= kc <= 0.76
# Case 3: wttr = b/t; lambda_r = 0.45*sqrt(E/Fy);
# Case 4: wttr = d/t; lambda_r = 0.75*sqrt(E/Fy);
# (Stiffened: cases 5, 6, 7, 8 and 9)
# Case 5: wttr = h/tw; lambda_r = 1.49*sqrt(E/Fy);
# Case 6: wttr = b/t; lambda_r = 1.40*sqrt(E/Fy);
# Case 7: wttr = b/t; lambda_r = 1.40*sqrt(E/Fy);
# Case 8: wttr = d/t; lambda_r = 1.49*sqrt(E/Fy);
# Case 9: wttr = D/t; lambda_r = 0.11*E/Fy;

def classify_compression(case: str, **kwargs):
    """ACI 360-22 Section B4.1a: Classification of sections for local buckling.
    wttr is width-to-thickness ratio.
    Unstiffened Elements: Compression elements supported along only one edge parallel to the direction of compression force.
    Stiffened Elements: Compression elements supported along two edges parallel to the direction of compression force.
    """
    E = kwargs.get("E")
    Fy = kwargs.get("Fy")
    match case.lower().strip():
        # Case 1: flanges of rolled I-, tees & channels; outstanding legs of continuously connected angles; plates projecting from I/H sections
        case "case1":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            lambda_r = 0.56*np.sqrt(E/Fy)

            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata e.g case number, case details verbatim from code
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
        
        # Case 2: flanges of built-up I-; plates or angles projecting from built-up I-
        case "case2":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            h = kwargs.get("h")
            tw = kwargs.get("tw")
            kc = kwargs.get("kc") if kwargs.get("kc") is not None else 4 * np.sqrt(h/tw)
            kc = max(0.35, min(kc, 0.76)) # TODO: fancy way of approximating 0.35 <= kc <= 0.76
            lambda_r = 0.64*np.sqrt(kc*E/Fy)

            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"NOTE: steelsnakes does not yet implement built-up sections.": None, "wttr": wttr, "lambda_r": lambda_r})
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"NOTE: steelsnakes does not yet implement built-up sections.": None, "wttr": wttr, "lambda_r": lambda_r})
       
        # Case 3: legs of single angles; legs of double angles with separators; all other unstiffened elements
        case "case3":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            lambda_r = 0.45*np.sqrt(E/Fy)

            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
        
        # Case 4: Stems of tees
        case "case4":
            d = kwargs.get("d")
            t = kwargs.get("t")
            wttr = d/t
            lambda_r = 0.75*np.sqrt(E/Fy)

            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
       
        # Case 5: Webs of doubly-symmetric rolled I- and channels; webs of built-up I- and channels
        case "case5":
            h = kwargs.get("h")
            tw = kwargs.get("tw")
            wttr = h/tw
            lambda_r = 1.49*np.sqrt(E/Fy)

            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
        
        # Case 6: Walls of Rectangular HSS
        case "case6":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            lambda_r = 1.40*np.sqrt(E/Fy)
            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata

        # Case 7: Flange cover plates between lines of fasteners or welds
        case "case7":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            lambda_r = 1.40*np.sqrt(E/Fy)
            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata

        # case 8: All other stiffened elements
        case "case8":
            b = kwargs.get("b")
            t = kwargs.get("t")
            wttr = b/t
            lambda_r = 1.49*np.sqrt(E/Fy)
            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
        
        # Case 9: Round HSS
        case "case9":
            D = kwargs.get("D")
            t = kwargs.get("t")
            wttr = D/t
            lambda_r = 0.11*E/Fy
            if wttr <= lambda_r:
                return Classification(section_class=SectionClass.NONSLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
            else:
                return Classification(section_class=SectionClass.SLENDER_ELEMENT, metadata={"wttr": wttr, "lambda_r": lambda_r}) # TODO: Enrich metadata
        
        case _:
            raise ValueError("Invalid case for compression classification. Try passing in 'case' as 'case1', 'case2', 'case3', 'case4', 'case5', 'case6', 'case7', 'case8', or 'case9'.")

# Table B4.1b. lambda_p and lambda_r for flexural elements
# Unstiffened i.e cases 10, 11, 12, 13, and 14
# Case 10: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 1.0*sqrt(E/Fy);
# Case 11: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 0.95*sqrt(kc*E/Fl); and kc = 4/sqrt(h/tw) but 0.35 <= kc <= 0.76
# ... Fl = 0.7*Fy for ... # TODO: is elaborate. Complete.
# Case 12: wttr = b/t; lambda_p = 0.54*sqrt(E/Fy); lambda_r = 0.91*sqrt(E/Fy);
# Case 13: wttr = b/t; lambda_p = 0.38*sqrt(E/Fy); lambda_r = 1.0*sqrt(E/Fy);
# Case 14: wttr = d/t; lambda_p = 0.84*sqrt(E/Fy); lambda_r = 1.52*sqrt(E/Fy);
# Stiffened i.e cases 15, 16, 17, 18, and 21
# Case 15: wttr = h/tw: lambda_p = 3.76*sqrt(E/Fy); lambda_r = 5.70*sqrt(E/Fy);
# Case 16: wttr = hc/tw: lambda_p = [UNSUPPORTED]; lambda_r = 5.70*sqrt(E/Fy); # TODO: implement support for case 16 tho. no implementation currently for unsymmetric sections.
# Case 17: wttr = b/t: lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.40*sqrt(E/Fy);
# Case 18: wttr = b/t: lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.40*sqrt(E/Fy);
# Case 19: wttr = h/t: lambda_p = 2.42*sqrt(E/Fy); lambda_r = 5.70*sqrt(E/Fy);
# Case 20: wttr = D/t: lambda_p = 0.07*sqrt(E/Fy); lambda_r = 5.70*sqrt(E/Fy);
# Case 21: wttr = b/t; lambda_p = 1.12*sqrt(E/Fy); lambda_r = 1.49*sqrt(E/Fy);

def classify_flexure(case: str, **kwargs):
    """ACI 360-22 Section B4.1b: Classification of sections for local buckling.
    wttr is width-to-thickness ratio.
    Unstiffened Elements: Compression elements supported along only one edge parallel to the direction of compression force.
    Stiffened Elements: Compression elements supported along two edges parallel to the direction of compression force.
    """
    E = kwargs.get("E")
    Fy = kwargs.get("Fy")

    match case.lower().strip():
        # Case 10:
        case "case10":
            return
        
        # Case 11:
        case "case11":
            return
        
        # Case 12:
        case "case12":
            return
        
        # Case 13:
        case "case13":
            return
        
        # Case 14:
        case "case14":
            return
        
        # Case 15:
        case "case15":
            return
        
        # Case 16:
        case "case16":
            return
        
        # Case 17:
        case "case17":
            return
        
        # Case 18:
        case "case18":
            return
        
        # Case 19:
        case "case19":
            return
        
        # Case 20:
        case "case20":
            return
        
        # Case 21:
        case "case21":
            return
        
        case _:
            raise ValueError("Invalid case for flexure classification. Try passing in 'case' as 'case10', 'case11', 'case12', 'case13', 'case14', 'case15', 'case16', 'case17', 'case18', 'case19', 'case20', or 'case21'.")

if __name__ == "__main__":
    from steelsnakes.US.beams import W
    from steelsnakes.US.hollow import HSS_RND
    beam = W("W44X408")
    # rnd = HSS_RND("HSS28X.750") # TODO: see designation vs EDI_Std_Nomenclature in data/HSS_RND.json
    rnd = HSS_RND("HSS28.000X0.750") # FIXME: for round HSS, make EDI_Std_Nomenclature rather than AISC_Manual_Label the designation.
    # FIXME: [IMPORTANT] investigate designations as AISC_Manual_Label vs EDI_Std_Nomenclature for round HSS, pipes and other interesting sections.
    # FIXME: [IMPORTANT] include EDI_Std_Nomenclature in fuzzy search for US or implement as different function
    beam_properties = beam.get_properties()
    rnd_properties = rnd.get_properties()
    # print(beam_properties)
    # print(rnd_properties)
    US_E = 29000000 # Young's modulus for steel (psi)
    US_Fy = 50000 # Yield strength for steel (psi)

    print(classify_compression(case="case1", E=US_E, Fy=US_Fy, b=beam_properties["bf"], t=beam_properties["tf"]))
    print(classify_compression(case="case9", E=US_E, Fy=US_Fy, D=rnd.OD, t=rnd.tnom))