# E1. General Provisions
# E2. Effective Length
# E3. Flexural Buckling of Members Without Slender Elements
# E4. Torsional and Flexural-Torsional Buckling of Single Angles and Members Without Slender Elements
# E5. Single-Angle Compression Members
# E6. Built-Up Members
# E7. Members with Slender Elements
# User Note: for cases not included...


from __future__ import annotations
from pydantic import BaseModel

class CompressionResult(BaseModel):
    # E1. General Provisions: Pn is lowest value from FB, TB and LTB
    phi_c: float # compression resistance factor
    Pn: float # nominal compressive strength, ksi [MPa]
    # E2. Effective Length
    # E3. Flexural Buckling of Members Without Slender Elements
    # E4. Torsional and Flexural-Torsional Buckling of Single Angles and Members Without Slender Elements
    # E5. Single-Angle Compression Members
    # E6. Built-Up Members
    # E7. Members with Slender Elements
    pass