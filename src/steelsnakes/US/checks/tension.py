# D: DESIGN OF MEMBERS FOR TENSION
# D1. Slenderness Limitations
# D2. Tensile Strength
# D3. Effective Net Area
# D4. Built-Up Members
# D5. Pin-Connected Members
# D6. Eyebars
from __future__ import annotations
from pydantic import BaseModel

class TensionResult(BaseModel):
    # D1. Slenderness Limitations
    # No slenderness limitations for tension members, 
    # D2. Tensile Strength; lower value for either tensile yielding of gross section [D2-1] or tensile rupture of net section [D2-2]
    phi_t: float # Resistance factor for tension
    Pn: float # Nominal tensile strength
    Fy: float # Specified minimum yield strength of the material, ksi [MPa] # TODO: use this notation to prepare for US_Metric module
    Fu: float # Specified minimum tensile strength of the material, ksi MPa]
    Ag: float # Gross area, in^2 [mm^2]
    Ae: float # Effective net area, in^2 [mm^2]
    # D3. Effective Net Area; per B4.3
    An: float # Net area, in^2 [mm^2]
    U: float # Shear lag factor, per Table D3.1, cases 1-8
    # D4. Built-Up Members; 
    # ...

# SHEAR_LAG_FACTORS = {}
def calculate_effective_net_area(An: float, U: float) -> float:
    # TODO: consider, in future, implementing individual checks to build larger check
    Ae = U * An
    return round(Ae) # TODO: note likelyhood of this as a good implementation, but need to be concise :)


def tension() -> TensionResult:

    return NotImplemented

class PinConnectedMemberResult(BaseModel):
    # D5. Pin-Connected Members; 
    # - for tensile rupture (D5-1)
    # - for shear rupture (D5-2)
    Asf: float # area on shear failure path, in^2 [mm^2]
    t: float # thickness of the plate, in [mm]
    d: float # diameter of the pin, in [mm]
    dh: float # hole diameter, in [mm]
    be: float # 2t+0.63in [2t+16mm] but...TODO: complete formula & definition
    a: float # shortest distance from the edge of pin hole to.... # TODO: complete definition
    Cr: float # reduction factor for shear rupture on pin-connected members; dependent on ratio of d and dh;

    # - for bearing on pin's projected area (J7)
    # - for yielding on gross section (D2(a))


    pass

def check_pin_connected_member() -> PinConnectedMemberResult:
    return NotImplemented


if __name__ == "__main__":

    print("🐬")