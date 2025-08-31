from __future__ import annotations
from dataclasses import dataclass
from steelsnakes.base import BaseSection, SectionType

@dataclass
class Channel(BaseSection):
    M: float = 0.0 # Mass per metre (kg/m)
    area: float = 0.0 # Area (x10² mm²)
    D: float = 0.0 # Depth (mm)
    B: float = 0.0 # Width (mm)
    t: float = 0.0 # Web thickness (mm)
    T: float = 0.0 # Flange thickness (mm)
    alpha: float = 0.0 # Flange slope (deg)
    R1: float = 0.0 # Root radius (mm)
    R2: float = 0.0 # Toe radius (mm), for tapered flanges # TODO: check other stuff
    C_y: float = 0.0 # B - ey (mm)
    
    I_yy: float = 0.0 # Second moment of area, y-axis (x10⁴ mm⁴)
    r_y: float = 0.0 # Radius of gyration, y-axis (mm)
    Z_yy: float = 0.0 # Elastic section modulus, y-axis (x10³ mm³)
    Z_py: float = 0.0 # Plastic section modulus, y-axis (x10³ mm³)

    I_zz: float = 0.0 # Second moment of area, z-axis (x10⁴ mm⁴)
    r_z: float = 0.0 # Radius of gyration, z-axis (mm)
    Z_zz: float = 0.0 # Elastic section modulus, z-axis (x10³ mm³)
    Z_pz: float = 0.0 # Plastic section modulus, z-axis (x10³ mm³)

    I_t: float = 0.0 # Torsional constant (x10⁴ mm⁴)
    I_w: float = 0.0 # Warping constant (x10⁶ mm⁶)


@dataclass
class JuniorChannel(Channel):
    pass

@dataclass
class LightWeightChannel(Channel):
    pass

@dataclass
class MediumWeightChannel(Channel):
    pass

@dataclass
class MediumWeightParallelFlangeChannel(Channel):
    pass

@dataclass
class JC(JuniorChannel):
    pass

@dataclass
class LWC(LightWeightChannel):
    pass

@dataclass
class MWC(MediumWeightChannel):
    pass

@dataclass
class MPC(MediumWeightParallelFlangeChannel):
    pass