# UK Steel Sections

Comprehensive implementation of UK steel sections according to BS EN 10365:2017 and related British/European standards.

## Overview

The UK module provides the most complete implementation in SteelSnakes, covering all major structural steel section types used in UK construction:

- **Universal Sections**: Beams (UB), Columns (UC), Bearing Piles (UBP)
- **Channel Sections**: Parallel Flange Channels (PFC)
- **Angle Sections**: Equal and Unequal angles, including back-to-back variants
- **Hollow Sections**: Hot finished and cold formed (circular, square, rectangular, elliptical)
- **Connection Components**: Preloaded bolts and weld specifications

## Quick Start

```python
from steelsnakes.UK import UB, UC, PFC

# Create sections using standard designations
beam = UB("457x191x67")           # 457mm deep Universal Beam
column = UC("305x305x137")        # 305x305mm Universal Column  
channel = PFC("430x100x64")       # 430mm deep Parallel Flange Channel

# Access properties immediately
print(f"Beam area: {beam.A} cm²")                    # 85.5 cm²
print(f"Column moment of inertia: {column.I_yy} cm⁴") # 29800 cm⁴
print(f"Channel mass: {channel.mass_per_metre} kg/m") # 64.4 kg/m
```

## Section Types Reference

### Universal Sections
::: steelsnakes.UK.universal
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4
      members: ["UniversalBeam", "UniversalColumn", "UniversalBearingPile"]

The most commonly used structural sections in UK construction:

| Section Type | Designation Format | Typical Use |
|--------------|-------------------|-------------|
| **UB** (Universal Beam) | `"457x191x67"` | Primary beams, rafters |
| **UC** (Universal Column) | `"305x305x137"` | Columns, heavy beams |
| **UBP** (Universal Bearing Pile) | `"254x254x71"` | Driven piles, foundations |

**Example Usage:**
```python
from steelsnakes.UK import UB, UC, UBP

# Create universal sections
beam = UB("533x210x92")       # 533mm deep beam, 92 kg/m
column = UC("254x254x107")    # 254x254mm column, 107 kg/m  
pile = UBP("305x305x79")      # 305x305mm bearing pile, 79 kg/m

# Compare section properties
sections = [beam, column, pile]
for section in sections:
    print(f"{section.designation}: A={section.A} cm², I_yy={section.I_yy} cm⁴")
```

### Channel Sections
::: steelsnakes.UK.channels
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4
      members: ["ParallelFlangeChannel"]

Parallel Flange Channels for secondary structural elements:

| Section Type | Designation Format | Typical Use |
|--------------|-------------------|-------------|
| **PFC** (Parallel Flange Channel) | `"430x100x64"` | Purlins, side rails, lintels |

**Example Usage:**
```python
from steelsnakes.UK import PFC

# Create parallel flange channels
purlin = PFC("200x90x30")     # Light purlin
rail = PFC("380x100x54")      # Side rail
lintel = PFC("430x100x64")    # Heavy lintel

# Check shear center location (important for channels)
print(f"Shear center offset: {lintel.e0} mm")
```

### Angle Sections
::: steelsnakes.UK.angles
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4
      members: ["EqualAngle", "UnequalAngle", "EqualAngleBackToBack", "UnequalAngleBackToBack"]

Equal and unequal angles for bracing and connections:

| Section Type | Designation Format | Typical Use |
|--------------|-------------------|-------------|
| **L_EQUAL** | `"200x200x20"` | Bracing, trusses |
| **L_UNEQUAL** | `"200x100x15"` | Asymmetric connections |
| **L_EQUAL_B2B** | `"150x150x12"` | Built-up compression members |
| **L_UNEQUAL_B2B** | `"150x90x12"` | Built-up asymmetric members |

**Example Usage:**
```python
from steelsnakes.UK import L_EQUAL, L_UNEQUAL, L_EQUAL_B2B

# Create angle sections
brace = L_EQUAL("100x100x10")        # Equal angle brace
cleat = L_UNEQUAL("150x90x12")       # Unequal angle cleat
built_up = L_EQUAL_B2B("200x200x20") # Back-to-back equal angles

# Compare properties
print(f"Equal angle area: {brace.A} cm²")
print(f"Unequal angle I_uu: {cleat.I_uu} cm⁴")
print(f"Built-up area: {built_up.A} cm²")  # ~2x single angle
```

### Hollow Sections
::: steelsnakes.UK.hf_hollow
    options:
      show_root_heading: false  
      show_source: false
      heading_level: 4
      members: ["HotFinishedCircularHollowSection", "HotFinishedSquareHollowSection", "HotFinishedRectangularHollowSection", "HotFinishedEllipticalHollowSection"]

::: steelsnakes.UK.cf_hollow
    options:
      show_root_heading: false
      show_source: false  
      heading_level: 4
      members: ["ColdFormedCircularHollowSection", "ColdFormedSquareHollowSection", "ColdFormedRectangularHollowSection"]

Circular, square, rectangular and elliptical hollow sections:

| Section Type | Designation Format | Manufacturing | Typical Use |
|--------------|-------------------|---------------|-------------|
| **HFCHS** | `"273.0x12.5"` | Hot Finished | Columns, compression members |
| **HFSHS** | `"200x200x8.0"` | Hot Finished | Columns, architectural |
| **HFRHS** | `"300x200x10.0"` | Hot Finished | Beams, architectural |
| **HFEHS** | `"300x150x8.0"` | Hot Finished | Architectural features |
| **CFCHS** | `"114.3x3.6"` | Cold Formed | Light structures |
| **CFSHS** | `"100x100x4.0"` | Cold Formed | Light structures |
| **CFRHS** | `"120x80x5.0"` | Cold Formed | Light structures |

**Example Usage:**
```python
from steelsnakes.UK import HFCHS, HFSHS, HFRHS, CFCHS

# Hot finished hollow sections (heavier duty)
column = HFCHS("273.0x12.5")         # Heavy circular column
architectural = HFSHS("200x200x8.0") # Square architectural member
beam = HFRHS("400x200x12.5")         # Rectangular beam

# Cold formed hollow sections (lighter duty)
tube = CFCHS("88.9x3.2")             # Light circular tube
frame = CFRHS("100x50x3.0")          # Rectangular frame member

# Compare torsional properties (important for hollow sections)
print(f"Hot finished torsion constant: {column.J} cm⁴")
print(f"Cold formed torsion constant: {tube.J} cm⁴")
```

## Section Properties

All UK sections provide comprehensive properties according to BS EN standards:

### Geometric Properties
- **Dimensions**: Overall depth (h), width (b), thickness values
- **Areas**: Cross-sectional area (A), root radius (r1)
- **Centroids**: Location of section centroid

### Section Properties  
- **Second Moments**: Major axis (I_yy), minor axis (I_zz), product (I_yz)
- **Section Moduli**: Elastic (Z_yy, Z_zz), plastic (S_yy, S_zz)  
- **Radii of Gyration**: Major axis (r_yy), minor axis (r_zz)
- **Torsional**: Torsion constant (J), warping constant (C_w)

### Physical Properties
- **Mass**: Mass per unit length (kg/m)
- **Surface Area**: Surface area per unit length (m²/m)
- **Paint Area**: Area requiring protective coating

### Example Property Access

```python
from steelsnakes.UK import UB

beam = UB("610x229x113")

# Geometric properties
print(f"Depth: {beam.h} mm")
print(f"Width: {beam.b} mm") 
print(f"Web thickness: {beam.tw} mm")
print(f"Flange thickness: {beam.tf} mm")

# Section properties
print(f"Area: {beam.A} cm²")
print(f"I_yy: {beam.I_yy} cm⁴") 
print(f"Z_yy: {beam.Z_yy} cm³")
print(f"S_yy: {beam.S_yy} cm³")

# Physical properties
print(f"Mass: {beam.mass_per_metre} kg/m")
print(f"Surface area: {beam.surface_area_per_metre} m²/m")
```

## Standards Compliance

All UK section data is sourced from official standards:

- **BS EN 10365:2017**: Hot rolled structural steel sections - Dimensions and sectional properties
- **BS EN 10210**: Hot finished structural hollow sections of non-alloy and fine grain steels
- **BS EN 10219**: Cold formed welded structural hollow sections of non-alloy and fine grain steels

Section properties are validated against:
- Steel Construction Institute (SCI) publications
- UK Steel sector guidance
- Major UK steel supplier catalogs

!!! tip "Data Accuracy"
    All section properties are cross-referenced with multiple authoritative sources to ensure accuracy. Values match those used in major structural analysis software.

## Database and Factory

The UK module includes optimized database and factory systems:

```python
from steelsnakes.UK.database import UKSectionDatabase
from steelsnakes.UK.factory import UKSectionFactory

# Database for section data management
db = UKSectionDatabase()
heavy_beams = db.filter_sections(
    section_type="UB",
    min_mass=80,  # kg/m
    min_depth=500  # mm
)

# Factory for section creation
factory = UKSectionFactory(db)
sections = [
    factory.create_section("457x191x67", SectionType.UB),
    factory.create_section("305x305x137", SectionType.UC)
]
```

For detailed database and factory documentation, see:
- [Database System](../../core/database.md)
- [Factory Pattern](../../core/factory.md)

Explanatory Notes: https://www.steelforlifebluebook.co.uk/explanatory-notes/ec3-ukna/

UK steel sections conforming to BS EN standards. This module provides comprehensive access to British/European steel section data and specifications.

## Database and Factory

::: steelsnakes.UK.database.UKSectionDatabase
    options:
        show_root_heading: true
        show_source: true
        heading_level: 3
        members_order: source
        show_bases: true

::: steelsnakes.UK.factory.UKSectionFactory
    options:
        show_root_heading: true
        show_source: true
        heading_level: 3
        members_order: source
        show_bases: true

## Section Categories

- **[Universal Sections](universal/index.md)**: Universal beams (UB), columns (UC), and bearing piles (UBP)
- **[Channels](channels/index.md)**: Parallel flange channels (PFC)
- **[Angles](angles/index.md)**: Equal and unequal angles, including back-to-back configurations
- **[Hollow Sections](hollow/index.md)**: Cold formed and hot finished hollow sections
- **[Connections](connections/index.md)**: Bolts and weld specifications
