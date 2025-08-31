from __future__ import annotations
from dataclasses import dataclass
from steelsnakes.base import BaseSection, SectionType

@dataclass
class Angle(BaseSection):
    M: float = 0.0 # Mass per metre (kg/m)
    area: float = 0.0 # Area (x10² mm²)
    a: float = 0.0 # Leg length a (mm)
    b: float = 0.0 # Leg length b (mm)
    t: float = 0.0 # Thickness (mm)
    R1: float = 0.0 # Root radius (mm)
    R2: float = 0.0 # Toe radius (mm), for tapered flanges # TODO: check other stuff
    alpha: float = 0.0 # Flange slope (deg) # TODO: check other stuff
    
    C_y: float = 0.0 # b - ey (mm)
    I_yy: float = 0.0 # Second moment of area, y-axis (x10⁴ mm⁴)
    r_y: float = 0.0 # Radius of gyration, y-axis (mm)
    Z_yy: float = 0.0 # Elastic section modulus, y-axis (x10³ mm³)
    Z_py: float = 0.0 # Plastic section modulus, y-axis (x10³ mm³)

    C_z: float = 0.0 # a - ez (mm)
    I_zz: float = 0.0 # Second moment of area, z-axis (x10⁴ mm⁴)
    r_z: float = 0.0 # Radius of gyration, z-axis (mm)
    Z_zz: float = 0.0 # Elastic section modulus, z-axis (x10³ mm³)
    Z_pz: float = 0.0 # Plastic section modulus, z-axis (x10³ mm³)

    I_uu: float = 0.0 # Second moment of area, u-axis (max) (x10⁴ mm⁴)
    I_vy: float = 0.0 # Second moment of area, v-axis (min) (x10⁴ mm⁴)
    r_u: float = 0.0 # Radius of gyration, u-axis (max) (mm)
    r_v: float = 0.0 # Radius of gyration, v-axis (min) (mm)
    
    I_t: float = 0.0 # Torsional constant (x10⁴ mm⁴)


@dataclass
class EqualAngle(Angle):
    pass

@dataclass
class UnequalAngle(Angle):
    pass

@dataclass
class EA(EqualAngle):
    pass

@dataclass
class UA(UnequalAngle):
    pass