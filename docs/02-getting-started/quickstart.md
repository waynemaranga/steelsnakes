# Quick Start Guide

Get up and running with SteelSnakes in under 5 minutes! This guide shows you the essential features through practical examples.

## Your First Section

```python
from steelsnakes.UK import UB

# Create a Universal Beam
beam = UB("457x191x67")

# Access properties immediately
print(f"Section: {beam.designation}")
print(f"Area: {beam.A} cm²")
print(f"Depth: {beam.h} mm")
print(f"Mass: {beam.mass_per_metre} kg/m")
```

Output:
```
Section: 457x191x67
Area: 85.5 cm²
Depth: 457 mm
Mass: 67.1 kg/m
```

## Multiple Section Types

SteelSnakes supports all major steel section types:

```python
from steelsnakes.UK import UB, UC, PFC

# I-sections
beam = UB("533x210x92")      # Universal Beam
column = UC("254x254x107")    # Universal Column

# Channels
channel = PFC("380x100x54")   # Parallel Flange Channel

# Display key properties
for section in [beam, column, channel]:
    print(f"{section.designation}: {section.A} cm²")
```

## Property Access

Every section provides comprehensive geometric and material properties:

```python
from steelsnakes.UK import UB

beam = UB("457x191x67")

# Geometric properties
print(f"Cross-sectional area: {beam.A} cm²")
print(f"Overall depth: {beam.h} mm")
print(f"Overall width: {beam.b} mm")

# Section properties
print(f"Second moment of area (major): {beam.I_yy} cm⁴")
print(f"Section modulus (major): {beam.Z_yy} cm³")
print(f"Radius of gyration: {beam.r_yy} cm")

# Physical properties
print(f"Mass per meter: {beam.mass_per_metre} kg/m")
print(f"Surface area per meter: {beam.surface_area_per_metre} m²/m")
```

## Regional Flexibility

Switch between regional standards seamlessly:

```python
# UK Sections (BS EN standards)
from steelsnakes.UK import UB as UB_UK
uk_beam = UB_UK("457x191x67")

# US Sections (AISC standards)
from steelsnakes.US import W as W_US
us_beam = W_US("W18x50")

# EU Sections (EN standards)
from steelsnakes.EU import IPE
eu_beam = IPE("IPE400")

print(f"UK beam mass: {uk_beam.mass_per_metre} kg/m")
print(f"US beam mass: {us_beam.mass_per_metre} kg/m") 
print(f"EU beam mass: {eu_beam.mass_per_metre} kg/m")
```

## Factory Pattern

Create sections using the factory pattern for dynamic applications:

```python
from steelsnakes.UK import create_section
from steelsnakes.base.sections import SectionType

# Create different section types
beam = create_section("457x191x67", SectionType.UB)
column = create_section("305x305x137", SectionType.UC)
channel = create_section("430x100x64", SectionType.PFC)

# All sections have the same interface
for section in [beam, column, channel]:
    props = section.get_properties()
    print(f"{props['designation']}: {props['A']} cm²")
```

## Simple Structural Calculation

Let's do a quick beam analysis:

```python
from steelsnakes.UK import UB

# Select a beam
beam = UB("533x210x92")

# Beam parameters
span = 8.0  # meters
load = 25.0  # kN/m

# Calculate maximum moment (simply supported)
M_max = load * span**2 / 8  # kN⋅m
print(f"Maximum moment: {M_max:.1f} kN⋅m")

# Calculate bending stress
stress = M_max * 1000 / beam.Z_yy  # N/mm²
print(f"Bending stress: {stress:.1f} N/mm²")

# Material properties (example)
fy = 355  # N/mm² (S355 steel)
utilisation = stress / fy
print(f"Utilisation ratio: {utilisation:.2f}")

if utilisation < 1.0:
    print("✅ Section is adequate for bending")
else:
    print("❌ Section is overstressed")
```

## Database Queries

Find sections that meet your criteria:

```python
from steelsnakes.UK.database import UKSteelDatabase

db = UKSteelDatabase()

# Find Universal Beams with specific requirements
beams = db.filter_sections(
    section_type="UB",
    min_depth=400,      # mm
    max_mass=80,        # kg/m
    min_Z_yy=1500      # cm³
)

print(f"Found {len(beams)} suitable beams:")
for beam in beams[:5]:  # Show first 5
    print(f"  {beam.designation}: {beam.mass_per_metre} kg/m")
```

## Error Handling

SteelSnakes provides helpful error messages for invalid inputs:

```python
from steelsnakes.UK import UB

try:
    # Invalid designation
    beam = UB("999x999x999")
except ValueError as e:
    print(f"Error: {e}")
    
try:
    # Valid designation  
    beam = UB("457x191x67")
    print(f"Success: {beam.designation}")
except ValueError as e:
    print(f"Error: {e}")
```

## What's Next?

Now that you've seen the basics, explore more advanced features:

- **[Basic Usage](basic-usage.md)** - Detailed explanation of core concepts
- **[User Guide](../03-user-guide/sections.md)** - Comprehensive documentation
- **[Examples](../04-examples/basic.md)** - Practical applications and use cases
- **[API Reference](../05-api-reference/index.md)** - Complete API documentation

!!! tip "Pro Tip"
    Use your IDE's autocomplete feature to discover available properties and methods on section objects!