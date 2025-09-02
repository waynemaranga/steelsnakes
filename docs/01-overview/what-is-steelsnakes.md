# What is `steelsnakes`?

`steelsnakes` is a comprehensive Python library designed for structural engineers and developers working with steel construction. It provides a unified, object-oriented interface to access standardized steel section properties and perform structural steel calculations.

## Why `steelsnakes`?

### **Multi-Regional Support**

- **🇬🇧 UK**: BS EN 10365:2017 compliant sections (UB, UC, PFC, angles, hollow sections)
- **🇺🇸 US**: AISC standard sections (W, S, M, C, angles, HSS, pipes)
- **🇪🇺 EU**: European standard sections per EN 10365:2017
- **🇮🇳 IN**: Indian standard sections per IS 808:2021 _(in development)_
- **🇦🇺 AU**: Australian standard sections _(planned)_

### **Developer-Friendly Design**

```python
from steelsnakes.UK import UB, UC, PFC

# Simple, intuitive section creation
beam = UB("457x191x67")           # Universal Beam
column = UC("305x305x137")        # Universal Column
channel = PFC("430x100x64")       # Parallel Flange Channel

# Immediate access to all properties
print(f"Beam area: {beam.A} cm²")
print(f"Column I_yy: {column.I_yy} cm⁴")
print(f"Channel mass: {channel.mass_per_metre} kg/m")
```

### **Complete Section Properties**

Each section object provides access to:

- **Geometric properties**: Area, perimeter, dimensions
- **Section properties**: Second moments of area (I_xx, I_yy), section moduli (Z_xx, Z_yy)
- **Physical properties**: Mass per meter, surface area per meter
- **Specialized properties**: Shear center, torsional constants, warping constants

### **Engineering Applications**

#### Structural Analysis

```python
from steelsnakes.UK import UB

beam = UB("533x210x92")
load = 50  # kN/m

# Calculate maximum moment for simply supported beam
L = 6.0  # meters
M_max = load * L**2 / 8  # kN⋅m

# Check bending capacity (simplified)
stress = M_max * 1000 / beam.Z_xx  # N/mm²
print(f"Bending stress: {stress:.1f} N/mm²")
```

#### Database Integration

```python
from steelsnakes.UK.database import UKSteelDatabase

db = UKSteelDatabase()

# Find sections meeting criteria
beams = db.filter_sections(
    section_type="UB",
    min_depth=400,  # mm
    max_mass=100,   # kg/m
    min_I_yy=20000  # cm⁴
)

for beam in beams:
    print(f"{beam.designation}: {beam.mass_per_metre} kg/m")
```

## Architecture Overview

SteelSnakes is built on three core principles:

### 1. **Factory Pattern**

Unified creation interface across all regions:

```python
from steelsnakes.UK import create_section
from steelsnakes.base.sections import SectionType

section = create_section("457x191x67", SectionType.UB)
```

### 2. **Regional Modularity**

Each region is self-contained with its own standards:

```python
# UK sections (BS EN standards)
from steelsnakes.UK import UB, UC, PFC

# US sections (AISC standards)
from steelsnakes.US import W, S, C

# EU sections (EN standards)
from steelsnakes.EU import IPE, HE, UPE
```

### 3. **Database-Driven**

All section data is stored in optimized databases with:

- Fast lookups and filtering
- Comprehensive property calculations
- Data validation and integrity checks

## Who Should Use SteelSnakes?

### **Structural Engineers**

- Rapid section selection and sizing
- Automated property lookups
- Multi-standard compliance checking
- Integration with analysis software

### **Software Developers**

- Building structural engineering applications
- CAD/BIM software integration
- Web-based steel design tools
- Educational software development

### **Students & Researchers**

- Learning structural steel design
- Academic research projects
- Parametric studies
- Code verification and validation

## Standards Compliance

All section data in SteelSnakes is sourced from official standards and industry publications:

| Region | Specification Standard | Design Standard     |
| ------ | ---------------------- | ------------------- |
| UK     | BS EN 10365:2017       | BS EN 1993-1-1:2022 |
| US     | ASTM A6/A6M-24b        | AISC 360-16         |
| EU     | EN 10365:2017          | EN 1993-1-1:2022    |
| IN     | IS 808:2021            | IS 800:2007         |

!!! tip "Accuracy Guarantee"
All section properties are derived from official manufacturer data and industry-standard publications. Values are validated against multiple sources to ensure accuracy.

## Next Steps

Ready to get started? Choose your path:

- **[Installation →](../02-getting-started/installation.md)** - Install SteelSnakes in your environment
- **[Quick Start →](../02-getting-started/quickstart.md)** - Get up and running in 5 minutes
- **[Basic Usage →](../02-getting-started/basic-usage.md)** - Learn the fundamentals
- **[Examples →](../04-examples/basic.md)** - See practical applications
