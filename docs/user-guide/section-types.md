# Section Types

SteelSnakes supports 18 different UK/European steel section types, organized into logical categories. This guide provides comprehensive coverage of each type with examples and use cases.

## Universal Sections

Universal sections are the most common structural steel sections, used for beams, columns, and bearing piles.

### Universal Beams (UB)

**Standard:** BS EN 10365  
**Use Cases:** Primary and secondary beams, lintels, crane rails

```python
from steelsnakes.core.sections.UK import UB

# Create Universal Beam
beam = UB("457x191x67")

# Key properties
print(f"Height: {beam.h} mm")
print(f"Width: {beam.b} mm")  
print(f"Web thickness: {beam.t_w} mm")
print(f"Flange thickness: {beam.t_f} mm")
print(f"Root radius: {beam.r} mm")
print(f"Major axis inertia: {beam.I_yy} cm⁴")
print(f"Minor axis inertia: {beam.I_zz} cm⁴")
```

**Available Properties:**
- Geometric: `h`, `b`, `t_w`, `t_f`, `r`
- Cross-sectional: `A`, `A_v`, `A_w`
- Moment of inertia: `I_yy`, `I_zz`, `I_w`
- Section modulus: `W_el_y`, `W_el_z`, `W_pl_y`, `W_pl_z`
- Radius of gyration: `i_y`, `i_z`
- Buckling: `I_T`, `C_w`

### Universal Columns (UC)

**Standard:** BS EN 10365  
**Use Cases:** Columns, compression members, heavy beams

```python
from steelsnakes.core.sections.UK import UC

column = UC("305x305x137")
print(f"Designation: {column.designation}")
print(f"Dimensions: {column.h} x {column.b} mm")
print(f"Mass: {column.mass_per_metre} kg/m")
```

### Universal Bearing Piles (UBP)

**Standard:** BS EN 10365  
**Use Cases:** Bearing piles, marine structures, heavy foundations

```python
from steelsnakes.core.sections.UK import UBP

pile = UBP("305x305x223")
print(f"Heavy pile: {pile.designation}")
print(f"Mass: {pile.mass_per_metre} kg/m")
```

## Channel Sections

### Parallel Flange Channels (PFC)

**Standard:** BS EN 10365  
**Use Cases:** Secondary beams, purlins, cladding rails, composite sections

```python
from steelsnakes.core.sections.UK import PFC

channel = PFC("430x100x64")

# Channel-specific properties
print(f"Height: {channel.h} mm")
print(f"Width: {channel.b} mm")
print(f"Web thickness: {channel.t_w} mm")
print(f"Flange thickness: {channel.t_f} mm")
print(f"Shear center offset: {channel.e0} mm")  # Key for channel analysis
```

**Key Feature:** Channels have a shear center offset (`e0`) that's critical for torsional analysis.

## Angle Sections

Angle sections are L-shaped and come in equal and unequal leg variants, with optional back-to-back configurations.

### Equal Angles (L_EQUAL)

**Standard:** BS EN 10365  
**Use Cases:** Bracing, lattice structures, connections

```python
from steelsnakes.core.sections.UK import L_EQUAL

angle = L_EQUAL("200x200x24.0")

print(f"Leg size: {angle.hxh}")
print(f"Thickness: {angle.t} mm")
print(f"Principal moments: I_uu={angle.I_uu}, I_vv={angle.I_vv} cm⁴")
print(f"Centroid offset: x_cg={angle.x_cg}, y_cg={angle.y_cg} mm")
```

### Unequal Angles (L_UNEQUAL)

**Standard:** BS EN 10365  
**Use Cases:** Asymmetric bracing, connections, supports

```python
from steelsnakes.core.sections.UK import L_UNEQUAL

unequal_angle = L_UNEQUAL("200x150x12")

print(f"Legs: {unequal_angle.hxb}")
print(f"Thickness: {unequal_angle.t} mm")
print(f"Different leg lengths: h={unequal_angle.h}, b={unequal_angle.b}")
```

### Back-to-Back Angles

For increased capacity, angles can be used back-to-back:

```python
from steelsnakes.core.sections.UK import L_EQUAL_B2B, L_UNEQUAL_B2B

# Back-to-back equal angles
b2b_equal = L_EQUAL_B2B("150x150x12")
print(f"B2B Equal: {b2b_equal.designation}")

# Back-to-back unequal angles  
b2b_unequal = L_UNEQUAL_B2B("200x150x15")
print(f"B2B Unequal: {b2b_unequal.designation}")
```

## Hollow Sections

Hollow sections are closed profiles offering excellent torsional properties and architectural appeal.

### Hot Finished Hollow Sections

Hot finished sections have better dimensional tolerances and material properties.

#### Circular Hollow Sections (HFCHS)

```python
from steelsnakes.core.sections.UK import HFCHS

circular = HFCHS("168.3x10.0")

print(f"Outside diameter: {circular.d} mm")
print(f"Wall thickness: {circular.t} mm") 
print(f"Internal diameter: {circular.d - 2*circular.t} mm")
print(f"Polar moment: {circular.I_p} cm⁴")
```

#### Rectangular Hollow Sections (HFRHS)

```python
from steelsnakes.core.sections.UK import HFRHS

rectangular = HFRHS("300x200x10.0")

print(f"Height: {rectangular.h} mm")
print(f"Width: {rectangular.b} mm")
print(f"Thickness: {rectangular.t} mm")
print(f"Internal dimensions: {rectangular.h-2*rectangular.t} x {rectangular.b-2*rectangular.t}")
```

#### Square Hollow Sections (HFSHS)

```python
from steelsnakes.core.sections.UK import HFSHS

square = HFSHS("200x200x8.0")
print(f"Square: {square.hxh}, t={square.t} mm")
```

#### Elliptical Hollow Sections (HFEHS)

```python
from steelsnakes.core.sections.UK import HFEHS

elliptical = HFEHS("400x200x12.5")
print(f"Elliptical: {elliptical.h} x {elliptical.b} mm")
```

### Cold Formed Hollow Sections

Cold formed sections are more economical but with slightly different properties.

```python
from steelsnakes.core.sections.UK import CFCHS, CFRHS, CFSHS

# Cold formed sections
cf_circular = CFCHS("48.3x4.0")
cf_rectangular = CFRHS("150x100x5.0") 
cf_square = CFSHS("100x100x4.0")

print(f"CF Circular: {cf_circular.designation}")
print(f"CF Rectangular: {cf_rectangular.designation}")
print(f"CF Square: {cf_square.designation}")
```

## Connection Elements

### Preloaded Bolts

SteelSnakes includes data for preloaded bolt specifications.

#### Grade 8.8 Bolts

```python
from steelsnakes.core.sections.UK import BOLT_PRE_88

bolt_88 = BOLT_PRE_88("M20")

print(f"Bolt: {bolt_88.designation}")
print(f"Nominal diameter: {bolt_88.d} mm")
print(f"Tensile stress area: {bolt_88.A_s} mm²")
print(f"Preload force: {bolt_88.F_p_C} kN")
```

#### Grade 10.9 Bolts

```python
from steelsnakes.core.sections.UK import BOLT_PRE_109

bolt_109 = BOLT_PRE_109("M24")
print(f"High strength bolt: {bolt_109.designation}")
print(f"Higher preload: {bolt_109.F_p_C} kN")
```

### Weld Specifications

```python
from steelsnakes.core.sections.UK import WELD

weld = WELD("6.0")

print(f"Weld size: {weld.designation}")
print(f"Throat size: {weld.s} mm")
print(f"Throat area per unit length: {weld.a} mm²/mm")
```

## Section Type Detection

The library can automatically detect section types:

```python
from steelsnakes.core.sections.UK import get_factory

factory = get_factory()

test_designations = [
    "457x191x67",      # UB
    "305x305x137",     # UC
    "430x100x64",      # PFC  
    "200x200x24.0",    # L_EQUAL
    "168.3x10.0",      # HFCHS
    "150x100x5.0",     # CFRHS
    "M20",             # BOLT_PRE_88
    "6.0"              # WELD
]

print("Auto-detection results:")
for designation in test_designations:
    try:
        section = factory.create_section(designation)
        section_type = section.get_section_type()
        print(f"{designation:15} → {section_type.value}")
    except ValueError as e:
        print(f"{designation:15} → Error: {e}")
```

## Property Comparison

Different section types have different available properties:

<div class="section-table">

| Section Type | Geometric Props | Moments | Torsion | Special |
|--------------|----------------|---------|---------|---------|
| **UB/UC/UBP** | h, b, t_w, t_f, r | I_yy, I_zz | I_T, C_w | A_v, A_w |
| **PFC** | h, b, t_w, t_f, r | I_yy, I_zz | I_T, C_w | e0 |
| **L_EQUAL** | h, t, r | I_uu, I_vv | - | x_cg, y_cg |
| **L_UNEQUAL** | h, b, t, r | I_uu, I_vv | - | x_cg, y_cg |
| **HFCHS** | d, t | I_yy, I_zz | I_p | - |
| **HFRHS** | h, b, t | I_yy, I_zz | I_T | - |
| **CFCHS** | d, t | I_yy, I_zz | I_p | - |
| **BOLTS** | d | A_s | - | F_p_C |
| **WELDS** | s | a | - | - |

</div>

## Usage Guidelines

### When to Use Each Type

| Application | Recommended Types | Notes |
|-------------|------------------|-------|
| **Primary Beams** | UB, UBP | High moment capacity |
| **Columns** | UC, HFSHS, HFCHS | Compression members |
| **Secondary Beams** | UB, PFC | Lighter sections |
| **Bracing** | L_EQUAL, L_UNEQUAL, CFCHS | Tension/compression |
| **Purlins** | PFC, CFRHS | Roof structures |
| **Architectural** | HFCHS, HFRHS, HFEHS | Exposed structures |
| **Connections** | BOLT_PRE_88/109, WELD | Joints |

### Performance Considerations

```python
from steelsnakes.core.sections.UK import get_database, SectionType

database = get_database()

# Check available section counts
for section_type in SectionType:
    count = len(database.list_sections(section_type))
    print(f"{section_type.value:15}: {count:4d} sections")
```

## Advanced Usage

### Custom Property Calculations

```python
def calculate_plastic_modulus_ratio(beam_designation: str) -> float:
    """Calculate shape factor (plastic/elastic modulus ratio)."""
    beam = UB(beam_designation)
    return beam.W_pl_y / beam.W_el_y

# Shape factors for different beams
beams = ["203x133x25", "457x191x67", "914x305x201"]
for beam_designation in beams:
    ratio = calculate_plastic_modulus_ratio(beam_designation)
    print(f"{beam_designation:15}: Shape factor = {ratio:.2f}")
```

### Section Optimization

```python
def find_optimal_beam(required_moment: float, max_depth: float = 600) -> str:
    """Find lightest beam meeting moment requirement."""
    database = get_database()
    
    # Required section modulus (simplified)
    required_w = required_moment * 1e6 / 165  # cm³
    
    candidates = database.search_sections(
        SectionType.UB,
        W_el_y__gte=required_w,
        h__lte=max_depth
    )
    
    if not candidates:
        return None
        
    # Sort by mass
    candidates.sort(key=lambda x: x[1]['mass_per_metre'])
    return candidates[0][0]

optimal_beam = find_optimal_beam(250.0, 500.0)  # 250 kNm, max 500mm deep
print(f"Optimal beam: {optimal_beam}")
```

## Next Steps

- **[Database System](database.md)** - Deep dive into search capabilities
- **[Factory Pattern](factory.md)** - Advanced factory usage
- **[Examples](../examples/basic.md)** - Real-world applications
- **[API Reference](../reference/sections.md)** - Complete API documentation

!!! tip "Section Standards"
    All section data conforms to BS EN 10365 and related UK/European standards. Properties are sourced from official UK steel supplier tables.
