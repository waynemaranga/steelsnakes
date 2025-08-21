# Quick Start

This guide will get you up and running with SteelSnakes in just a few minutes. We'll cover the most common use cases and show you the power of the library.

## Your First Section

Let's start by creating a simple steel beam:

```python
from steelsnakes.core.sections.UK import UB

# Create a Universal Beam
beam = UB("457x191x67")

print(f"Section: {beam}")
print(f"Height: {beam.h} mm")
print(f"Width: {beam.b} mm")
print(f"Mass: {beam.mass_per_metre} kg/m")
print(f"Moment of Inertia (major): {beam.I_yy} cm⁴")
```

**Output:**
```
Section: 457x191x67
Height: 460.0 mm
Width: 191.3 mm
Mass: 67.1 kg/m
Moment of Inertia (major): 42200.0 cm⁴
```

That's it! You've just created your first steel section and accessed its properties.

## Multiple Section Types

SteelSnakes supports 18 different section types. Here are some common ones:

```python
from steelsnakes.core.sections.UK import UB, UC, PFC, L_EQUAL, CFCHS

# Universal sections
beam = UB("457x191x67")           # Universal Beam
column = UC("305x305x137")        # Universal Column

# Other sections
channel = PFC("430x100x64")       # Parallel Flange Channel
angle = L_EQUAL("200x200x24.0")   # Equal Angle
tube = CFCHS("48.3x4.0")         # Cold Formed Circular Hollow

# Display properties
sections = [beam, column, channel, angle, tube]
for section in sections:
    print(f"{section.designation:15} - {section.mass_per_metre:6.1f} kg/m")
```

**Output:**
```
457x191x67      -   67.1 kg/m
305x305x137     -  137.0 kg/m
430x100x64      -   64.4 kg/m
200x200x24.0    -   73.6 kg/m
48.3x4.0        -    5.4 kg/m
```

## Auto-Detection with Factory

Don't know the section type? Let the factory figure it out:

```python
from steelsnakes.core.sections.UK import get_factory

factory = get_factory()

# Auto-detect section types
sections = [
    factory.create_section("457x191x67"),    # Will be detected as UB
    factory.create_section("305x305x137"),   # Will be detected as UC
    factory.create_section("430x100x64"),    # Will be detected as PFC
]

for section in sections:
    section_type = section.get_section_type()
    print(f"{section.designation:15} is a {section_type.value}")
```

**Output:**
```
457x191x67      is a UB
305x305x137     is a UC
430x100x64      is a PFC
```

## Searching the Database

Find sections that meet your criteria:

```python
from steelsnakes.core.sections.UK import get_database, SectionType

database = get_database()

# Find all heavy beams (>100 kg/m)
heavy_beams = database.search_sections(
    SectionType.UB, 
    mass_per_metre__gt=100
)

print(f"Found {len(heavy_beams)} heavy beams:")
for designation, data in heavy_beams[:5]:  # Show first 5
    print(f"  {designation:15} - {data['mass_per_metre']} kg/m")
```

**Output:**
```
Found 23 heavy beams:
  533x210x101     - 101.0 kg/m
  533x210x109     - 109.0 kg/m
  610x229x101     - 101.0 kg/m
  610x229x113     - 113.0 kg/m
  610x229x125     - 125.0 kg/m
```

## Advanced Search

Combine multiple criteria:

```python
# Find medium-depth, wide flange channels
channels = database.search_sections(
    SectionType.PFC,
    h__gte=200,      # Height ≥ 200mm
    h__lt=400,       # Height < 400mm
    b__gt=100        # Width > 100mm
)

print(f"Found {len(channels)} medium channels with wide flanges:")
for designation, data in channels:
    print(f"  {designation:15} - {data['h']}x{data['b']} mm")
```

## Section Comparison

Compare different options easily:

```python
from steelsnakes.core.sections.UK import UB

# Compare beam options
beam_options = ["406x178x54", "457x191x67", "533x210x82"]
beams = [UB(designation) for designation in beam_options]

print("Beam Comparison:")
print(f"{'Designation':15} {'Mass':>8} {'I_yy':>10} {'W_el_y':>10}")
print("-" * 50)

for beam in beams:
    print(f"{beam.designation:15} "
          f"{beam.mass_per_metre:8.1f} "
          f"{beam.I_yy:10.0f} "
          f"{beam.W_el_y:10.0f}")
```

**Output:**
```
Beam Comparison:
Designation          Mass       I_yy     W_el_y
--------------------------------------------------
406x178x54           54.1      15600       769
457x191x67           67.1      42200      1840
533x210x82           82.0      47500      1780
```

## Working with Properties

All section properties are available as attributes:

```python
beam = UB("457x191x67")

# Geometric properties
print(f"Dimensions: {beam.h} x {beam.b} mm")
print(f"Web thickness: {beam.t_w} mm")
print(f"Flange thickness: {beam.t_f} mm")

# Section properties
print(f"Area: {beam.A} cm²")
print(f"Major axis inertia: {beam.I_yy} cm⁴")
print(f"Minor axis inertia: {beam.I_zz} cm⁴")
print(f"Section modulus: {beam.W_el_y} cm³")

# Mass properties
print(f"Mass per metre: {beam.mass_per_metre} kg/m")
```

## Real-World Example

Let's design a simple beam:

```python
from steelsnakes.core.sections.UK import get_database, SectionType

def find_suitable_beam(min_moment_capacity):
    """Find beams with sufficient section modulus."""
    database = get_database()
    
    # Find beams with sufficient section modulus
    # Assuming allowable stress of 165 N/mm²
    min_section_modulus = min_moment_capacity * 1e6 / 165  # cm³
    
    suitable_beams = database.search_sections(
        SectionType.UB,
        W_el_y__gte=min_section_modulus
    )
    
    # Sort by mass (lightest first)
    suitable_beams.sort(key=lambda x: x[1]['mass_per_metre'])
    
    return suitable_beams

# Find beam for 250 kNm moment
suitable_beams = find_suitable_beam(250)  # 250 kNm

print(f"Suitable beams for 250 kNm moment:")
for designation, data in suitable_beams[:5]:
    efficiency = data['W_el_y'] / data['mass_per_metre']
    print(f"  {designation:15} - {data['mass_per_metre']:5.1f} kg/m "
          f"(efficiency: {efficiency:.1f} cm³/kg/m)")
```

## Next Steps

You now know the basics of SteelSnakes! Here's what to explore next:

1. **[Basic Usage](basic-usage.md)** - Learn more about the core concepts
2. **[Section Types](../user-guide/section-types.md)** - Detailed guide to all 18 section types
3. **[Database System](../user-guide/database.md)** - Advanced database features
4. **[Examples](../examples/basic.md)** - More practical examples

## Common Patterns

Here are some patterns you'll use frequently:

=== "Create by Designation"

    ```python
    from steelsnakes.core.sections.UK import UB, UC, PFC
    
    beam = UB("457x191x67")
    column = UC("305x305x137")
    channel = PFC("430x100x64")
    ```

=== "Auto-Detection"

    ```python
    from steelsnakes.core.sections.UK import get_factory
    
    factory = get_factory()
    section = factory.create_section("457x191x67")
    ```

=== "Search Database"

    ```python
    from steelsnakes.core.sections.UK import get_database, SectionType
    
    db = get_database()
    heavy_beams = db.search_sections(SectionType.UB, mass_per_metre__gt=100)
    ```

=== "List Available Sections"

    ```python
    db = get_database()
    all_beams = db.list_sections(SectionType.UB)
    print(f"Available beams: {len(all_beams)}")
    ```

!!! tip "Pro Tip"
    Use tab completion in Jupyter notebooks or IPython to explore available properties on any section object. All properties are fully documented with type hints.
