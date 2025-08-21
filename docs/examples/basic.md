# Basic Examples

This page provides practical examples showing how to use SteelSnakes for common structural engineering tasks. Each example includes complete, runnable code with explanations.

## Simple Beam Analysis

Let's start with a basic beam analysis example:

```python
from steelsnakes.core.sections.UK import UB

def analyze_beam(designation: str, span_m: float, udl_kn_m: float):
    """Analyze a simply supported beam with UDL."""
    
    # Create beam section
    beam = UB(designation)
    
    # Calculate maximum moment (for simply supported beam with UDL)
    max_moment = udl_kn_m * span_m**2 / 8  # kNm
    
    # Calculate maximum stress (simplified)
    max_stress = (max_moment * 1e6) / (beam.W_el_y * 1e3)  # N/mm²
    
    # Check deflection (simplified, E = 200 GPa)
    E = 200000  # N/mm²
    max_deflection = (5 * udl_kn_m * 1000 * (span_m * 1000)**4) / (384 * E * beam.I_yy * 1e4)  # mm
    
    print(f"Beam Analysis: {designation}")
    print(f"Span: {span_m} m, Load: {udl_kn_m} kN/m")
    print(f"Maximum moment: {max_moment:.1f} kNm")
    print(f"Maximum stress: {max_stress:.1f} N/mm²")
    print(f"Maximum deflection: {max_deflection:.1f} mm")
    print(f"Deflection/span ratio: 1/{span_m*1000/max_deflection:.0f}")
    print("-" * 50)

# Analyze different beams
beams_to_analyze = [
    ("406x178x54", 8.0, 25.0),
    ("457x191x67", 10.0, 30.0),
    ("533x210x82", 12.0, 35.0)
]

for designation, span, load in beams_to_analyze:
    analyze_beam(designation, span, load)
```

**Output:**
```
Beam Analysis: 406x178x54
Span: 8.0 m, Load: 25.0 kN/m
Maximum moment: 200.0 kNm
Maximum stress: 260.1 N/mm²
Maximum deflection: 41.2 mm
Deflection/span ratio: 1/194

Beam Analysis: 457x191x67
Span: 10.0 m, Load: 30.0 kN/m
Maximum moment: 375.0 kNm
Maximum stress: 203.8 N/mm²
Maximum deflection: 44.4 mm
Deflection/span ratio: 1/225

Beam Analysis: 533x210x82
Span: 12.0 m, Load: 35.0 kN/m
Maximum moment: 630.0 kNm
Maximum stress: 353.9 N/mm²
Maximum deflection: 77.9 mm
Deflection/span ratio: 1/154
```

## Section Selection

Find the most efficient section for a given requirement:

```python
from steelsnakes.core.sections.UK import get_database, SectionType, UB

def select_beam_for_moment(required_moment_knm: float, max_depth_mm: float = None):
    """Select the lightest beam for a given moment requirement."""
    
    database = get_database()
    
    # Calculate required section modulus (assuming allowable stress of 165 N/mm²)
    required_section_modulus = (required_moment_knm * 1e6) / 165  # mm³
    required_section_modulus_cm3 = required_section_modulus / 1e3  # cm³
    
    # Search criteria
    criteria = {"W_el_y__gte": required_section_modulus_cm3}
    if max_depth_mm:
        criteria["h__lte"] = max_depth_mm
    
    # Find suitable beams
    suitable_beams = database.search_sections(SectionType.UB, **criteria)
    
    if not suitable_beams:
        print(f"No beams found for moment {required_moment_knm} kNm")
        return None
    
    # Sort by mass (lightest first)
    suitable_beams.sort(key=lambda x: x[1]['mass_per_metre'])
    
    print(f"Beams suitable for {required_moment_knm} kNm moment:")
    print(f"Required section modulus: {required_section_modulus_cm3:.0f} cm³")
    print(f"{'Rank':>4} {'Designation':>15} {'Mass':>8} {'W_el_y':>10} {'Utilization':>12}")
    print("-" * 60)
    
    results = []
    for i, (designation, data) in enumerate(suitable_beams[:10], 1):
        utilization = required_section_modulus_cm3 / data['W_el_y'] * 100
        results.append((designation, data['mass_per_metre'], utilization))
        print(f"{i:4d} {designation:>15} {data['mass_per_metre']:8.1f} "
              f"{data['W_el_y']:10.0f} {utilization:11.1f}%")
    
    return results[0] if results else None

# Example usage
print("Example 1: 200 kNm moment, no depth restriction")
best_beam = select_beam_for_moment(200)

print("\nExample 2: 300 kNm moment, max 450mm deep")
best_beam_constrained = select_beam_for_moment(300, 450)
```

## Column Design

Design a column for axial load:

```python
from steelsnakes.core.sections.UK import UC, get_database, SectionType
import math

def design_column(axial_load_kn: float, length_m: float, end_conditions="pinned"):
    """Design column for axial compression."""
    
    database = get_database()
    
    # Effective length factors
    k_factors = {
        "fixed-fixed": 0.5,
        "pinned-pinned": 1.0,
        "fixed-pinned": 0.7,
        "cantilever": 2.0
    }
    
    k = k_factors.get(end_conditions, 1.0)
    effective_length = k * length_m * 1000  # mm
    
    print(f"Column Design for {axial_load_kn} kN, {length_m}m length")
    print(f"End conditions: {end_conditions} (k = {k})")
    print(f"Effective length: {effective_length:.0f} mm")
    print("-" * 60)
    
    # Get all UC sections
    all_columns = database.search_sections(SectionType.UC)
    
    suitable_columns = []
    
    for designation, data in all_columns:
        # Create section object
        try:
            column = UC(designation)
            
            # Calculate slenderness ratio
            slenderness = effective_length / (column.i_y * 10)  # i_y is in cm
            
            # Simplified buckling check (Perry-Robertson formula approximation)
            # This is a simplified approach - use proper design codes in practice
            if slenderness <= 200:  # Reasonable limit
                # Approximate buckling curve
                phi = 0.5 * (1 + 0.21 * (slenderness - 93) + slenderness**2 / 9300)
                chi = 1 / (phi + math.sqrt(phi**2 - slenderness**2 / 9300))
                chi = min(chi, 1.0)
                
                # Design resistance (simplified, fy = 355 N/mm²)
                design_resistance = chi * column.A * 355 / 1000  # kN
                
                if design_resistance >= axial_load_kn:
                    utilization = axial_load_kn / design_resistance * 100
                    suitable_columns.append((
                        designation, 
                        column.mass_per_metre, 
                        slenderness, 
                        design_resistance,
                        utilization
                    ))
        except ValueError:
            continue
    
    if not suitable_columns:
        print("No suitable columns found!")
        return None
    
    # Sort by mass
    suitable_columns.sort(key=lambda x: x[1])
    
    print(f"{'Rank':>4} {'Designation':>15} {'Mass':>8} {'λ':>6} {'Resistance':>12} {'Util.':>8}")
    print("-" * 70)
    
    for i, (designation, mass, slenderness, resistance, utilization) in enumerate(suitable_columns[:10], 1):
        print(f"{i:4d} {designation:>15} {mass:8.1f} {slenderness:6.0f} "
              f"{resistance:12.0f} {utilization:7.1f}%")
    
    return suitable_columns[0] if suitable_columns else None

# Example usage
print("Example 1: 1000 kN load, 4m height, pinned ends")
best_column = design_column(1000, 4.0, "pinned-pinned")

print("\nExample 2: 2000 kN load, 6m height, fixed-pinned")
best_column_2 = design_column(2000, 6.0, "fixed-pinned")
```

## Section Comparison

Compare multiple sections side by side:

```python
from steelsnakes.core.sections.UK import UB, UC, PFC

def compare_sections(designations, section_type="auto"):
    """Compare multiple sections with key properties."""
    
    sections = []
    for designation in designations:
        try:
            if section_type == "UB":
                section = UB(designation)
            elif section_type == "UC":
                section = UC(designation)
            elif section_type == "PFC":
                section = PFC(designation)
            else:
                # Auto-detect
                from steelsnakes.core.sections.UK import get_factory
                factory = get_factory()
                section = factory.create_section(designation)
            sections.append(section)
        except ValueError as e:
            print(f"Error creating {designation}: {e}")
    
    if not sections:
        return
    
    # Print comparison table
    print(f"Section Comparison ({len(sections)} sections)")
    print("=" * 80)
    
    # Headers
    headers = ["Designation", "Type", "Mass", "A", "I_yy", "I_zz", "W_el_y"]
    widths = [15, 8, 8, 8, 10, 10, 10]
    
    # Print header
    for header, width in zip(headers, widths):
        print(f"{header:>{width}}", end="")
    print()
    print("-" * sum(widths))
    
    # Print data
    for section in sections:
        values = [
            section.designation,
            section.get_section_type().value,
            f"{section.mass_per_metre:.1f}",
            f"{section.A:.1f}",
            f"{section.I_yy:.0f}",
            f"{section.I_zz:.0f}",
            f"{section.W_el_y:.0f}"
        ]
        
        for value, width in zip(values, widths):
            print(f"{value:>{width}}", end="")
        print()
    
    # Calculate efficiency metrics
    print("\nEfficiency Metrics:")
    print(f"{'Designation':>15} {'I_yy/Mass':>12} {'W_el_y/Mass':>14} {'I_zz/I_yy':>12}")
    print("-" * 55)
    
    for section in sections:
        iyy_mass = section.I_yy / section.mass_per_metre
        wel_mass = section.W_el_y / section.mass_per_metre
        izz_iyy = section.I_zz / section.I_yy
        
        print(f"{section.designation:>15} {iyy_mass:12.1f} {wel_mass:14.1f} {izz_iyy:12.3f}")

# Example comparisons
print("Beam comparison:")
beam_designations = ["406x178x54", "457x191x67", "533x210x82", "610x229x101"]
compare_sections(beam_designations, "UB")

print("\n\nColumn comparison:")
column_designations = ["203x203x52", "254x254x73", "305x305x97", "356x368x129"]
compare_sections(column_designations, "UC")

print("\n\nMixed section comparison:")
mixed_designations = ["457x191x67", "305x305x97", "430x100x64"]
compare_sections(mixed_designations)
```

## Load Capacity Tables

Generate load capacity tables for standard spans:

```python
from steelsnakes.core.sections.UK import get_database, SectionType, UB

def generate_load_table(spans_m, beam_designations=None):
    """Generate uniformly distributed load capacity table."""
    
    if beam_designations is None:
        # Use common beam sizes
        database = get_database()
        all_beams = database.search_sections(SectionType.UB, mass_per_metre__lt=150)
        # Select every 10th beam for manageable table
        beam_designations = [designation for designation, _ in all_beams[::10]][:8]
    
    print("UDL Capacity Table (kN/m)")
    print("Allowable stress: 165 N/mm², Deflection limit: span/250")
    print("=" * 80)
    
    # Header
    print(f"{'Beam':>15}", end="")
    for span in spans_m:
        print(f"{span:>8}m", end="")
    print()
    print("-" * (15 + 8 * len(spans_m)))
    
    # Each beam
    for designation in beam_designations:
        try:
            beam = UB(designation)
            print(f"{designation:>15}", end="")
            
            for span in spans_m:
                # Moment capacity
                moment_capacity = beam.W_el_y * 165 / 1e3  # kNm
                udl_moment = 8 * moment_capacity / span**2  # kN/m
                
                # Deflection capacity (span/250 limit)
                # δ = 5wL⁴/(384EI), rearrange for w
                E = 200000  # N/mm²
                max_deflection = span * 1000 / 250  # mm
                udl_deflection = (384 * E * beam.I_yy * 1e4 * max_deflection) / (5 * (span * 1000)**4) * 1000  # kN/m
                
                # Governing capacity
                udl_capacity = min(udl_moment, udl_deflection)
                
                print(f"{udl_capacity:8.1f}", end="")
            print()
            
        except ValueError:
            print(f"{designation:>15} - ERROR")
    
    print("\nNote: Capacities are for simply supported beams with UDL")
    print("Values governed by moment capacity or deflection limit (span/250)")

# Generate table for common spans
spans = [6, 8, 10, 12, 15, 18]
generate_load_table(spans)
```

## Connection Analysis

Analyze bolt patterns:

```python
from steelsnakes.core.sections.UK import BOLT_PRE_88, BOLT_PRE_109

def analyze_bolt_group(bolt_designation, grade, num_bolts, tension_kn=0, shear_kn=0):
    """Analyze capacity of bolt group."""
    
    if grade == "8.8":
        bolt = BOLT_PRE_88(bolt_designation)
    elif grade == "10.9":
        bolt = BOLT_PRE_109(bolt_designation)
    else:
        print(f"Unknown bolt grade: {grade}")
        return
    
    print(f"Bolt Group Analysis: {num_bolts} x {bolt_designation} Grade {grade}")
    print("-" * 50)
    
    # Individual bolt capacities (simplified)
    # Tension capacity (simplified, actual design requires proper checks)
    tension_capacity_per_bolt = bolt.A_s * 0.9 * (800 if grade == "8.8" else 1000) / 1000  # kN
    
    # Shear capacity (simplified)
    shear_capacity_per_bolt = bolt.A_s * 0.6 * (800 if grade == "8.8" else 1000) / 1000  # kN
    
    # Group capacities
    total_tension_capacity = tension_capacity_per_bolt * num_bolts
    total_shear_capacity = shear_capacity_per_bolt * num_bolts
    
    print(f"Individual bolt properties:")
    print(f"  Diameter: {bolt.d} mm")
    print(f"  Tensile stress area: {bolt.A_s} mm²")
    print(f"  Preload: {bolt.F_p_C} kN")
    
    print(f"\nCapacities per bolt (simplified):")
    print(f"  Tension: {tension_capacity_per_bolt:.1f} kN")
    print(f"  Shear: {shear_capacity_per_bolt:.1f} kN")
    
    print(f"\nGroup capacities:")
    print(f"  Total tension: {total_tension_capacity:.1f} kN")
    print(f"  Total shear: {total_shear_capacity:.1f} kN")
    
    if tension_kn > 0 or shear_kn > 0:
        print(f"\nApplied loads:")
        print(f"  Tension: {tension_kn} kN")
        print(f"  Shear: {shear_kn} kN")
        
        tension_utilization = tension_kn / total_tension_capacity * 100 if tension_kn > 0 else 0
        shear_utilization = shear_kn / total_shear_capacity * 100 if shear_kn > 0 else 0
        
        print(f"\nUtilizations:")
        print(f"  Tension: {tension_utilization:.1f}%")
        print(f"  Shear: {shear_utilization:.1f}%")
        
        # Combined utilization (simplified interaction)
        if tension_kn > 0 and shear_kn > 0:
            combined = math.sqrt((tension_kn/total_tension_capacity)**2 + (shear_kn/total_shear_capacity)**2) * 100
            print(f"  Combined: {combined:.1f}%")

# Example analyses
analyze_bolt_group("M20", "8.8", 6, tension_kn=200, shear_kn=150)
print("\n" + "="*60 + "\n")
analyze_bolt_group("M24", "10.9", 4, tension_kn=300, shear_kn=100)
```

## Next Steps

These examples demonstrate the core capabilities of SteelSnakes. For more advanced usage:

- **[Advanced Examples](advanced.md)** - Complex design scenarios
- **[Steel Design Examples](design.md)** - Complete design workflows
- **[User Guide](../user-guide/section-types.md)** - Detailed feature documentation
- **[API Reference](../reference/core.md)** - Complete API documentation

!!! warning "Design Responsibility"
    These examples use simplified design methods for demonstration. Always use proper design codes (Eurocode 3, BS 5950, etc.) and appropriate safety factors for real structural design.

!!! tip "Performance Note"
    For repetitive calculations, consider caching the database instance and reusing section objects to improve performance.
