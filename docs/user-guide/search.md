# Search & Filtering

SteelSnakes provides powerful search and filtering capabilities that allow you to find sections based on any property with sophisticated comparison operators. This guide covers all search features with practical examples.

## Search Fundamentals

### Basic Search Syntax

All searches follow this pattern:

```python
database.search_sections(section_type, **criteria)
```

Where criteria can be:
- Simple property matches: `mass_per_metre=67.1`
- Comparison operations: `mass_per_metre__gt=100`
- Multiple criteria combined with AND logic

### Supported Operators

| Operator | Symbol | Description | Example |
|----------|--------|-------------|---------|
| **Equal** | `__eq` or none | Exact match | `t_f=16.0` or `t_f__eq=16.0` |
| **Not Equal** | `__ne` | Not equal to | `r__ne=10.2` |
| **Greater Than** | `__gt` | Strictly greater | `mass_per_metre__gt=100` |
| **Less Than** | `__lt` | Strictly less | `h__lt=400` |
| **Greater or Equal** | `__gte` | Greater than or equal | `I_yy__gte=10000` |
| **Less or Equal** | `__lte` | Less than or equal | `b__lte=200` |

## Basic Examples

### Simple Property Matching

```python
from steelsnakes.core.sections.UK import get_database, SectionType

database = get_database()

# Find all beams with exactly 16mm flange thickness
thick_flanges = database.search_sections(SectionType.UB, t_f=16.0)
print(f"Beams with 16mm flanges: {len(thick_flanges)}")

# Find channels with 100mm flange width
channels_100 = database.search_sections(SectionType.PFC, b=100)
print(f"Channels with 100mm flanges: {len(channels_100)}")
```

### Range Searches

```python
# Find medium-weight beams (50-100 kg/m)
medium_beams = database.search_sections(
    SectionType.UB,
    mass_per_metre__gte=50,
    mass_per_metre__lte=100
)

print(f"Medium-weight beams: {len(medium_beams)}")
for designation, data in medium_beams[:5]:
    print(f"  {designation}: {data['mass_per_metre']} kg/m")
```

### Minimum/Maximum Searches

```python
# Find the heaviest beams (>150 kg/m)
heavy_beams = database.search_sections(
    SectionType.UB,
    mass_per_metre__gt=150
)

# Find compact sections (depth < 300mm)
compact_beams = database.search_sections(
    SectionType.UB,
    h__lt=300
)

print(f"Heavy beams: {len(heavy_beams)}")
print(f"Compact beams: {len(compact_beams)}")
```

## Advanced Search Patterns

### Multi-Criteria Searches

Combine multiple criteria to find exactly what you need:

```python
# Find efficient long-span beams
efficient_beams = database.search_sections(
    SectionType.UB,
    h__gte=450,               # Deep enough for long spans
    h__lte=600,               # Not too deep for practical reasons
    mass_per_metre__lt=120,   # Reasonable weight
    I_yy__gt=30000,          # High moment of inertia
    b__gte=150               # Wide flange for lateral stability
)

print(f"Efficient long-span beams: {len(efficient_beams)}")

# Sort by efficiency (I_yy/mass ratio)
if efficient_beams:
    efficient_beams.sort(
        key=lambda x: x[1]['I_yy'] / x[1]['mass_per_metre'], 
        reverse=True
    )
    
    print("Top 5 most efficient:")
    for designation, data in efficient_beams[:5]:
        efficiency = data['I_yy'] / data['mass_per_metre']
        print(f"  {designation:15} - {efficiency:.1f} cm⁴/(kg/m)")
```

### Section-Specific Searches

Different section types have different properties. Tailor searches accordingly:

#### Universal Beam Searches

```python
# Find beams suitable for composite construction
composite_beams = database.search_sections(
    SectionType.UB,
    h__gte=400,               # Deep for reduced deflections
    b__gte=180,               # Wide for shear connector placement
    t_f__gte=12.0,           # Thick flange for shear connectors
    mass_per_metre__lt=100    # Weight limit
)
```

#### Channel Searches

```python
# Find channels for purlin applications
purlin_channels = database.search_sections(
    SectionType.PFC,
    h__gte=150,               # Minimum depth for spanning
    h__lte=300,               # Maximum depth for roof slope
    mass_per_metre__lt=30,    # Weight limit for roof structure
    t_f__gte=8.0             # Minimum flange for connections
)

# Check shear center offset for torsional considerations
for designation, data in purlin_channels[:3]:
    print(f"{designation}: e0 = {data.get('e0', 'N/A')} mm")
```

#### Hollow Section Searches

```python
# Find architectural circular hollow sections
architectural_chs = database.search_sections(
    SectionType.HFCHS,
    d__gte=100,               # Minimum size for visual impact
    d__lte=300,               # Maximum for typical applications
    t__gte=5.0               # Minimum thickness
)

# Find structural rectangular hollow sections
structural_rhs = database.search_sections(
    SectionType.HFRHS,
    h__gte=150,               # Adequate depth
    b__gte=100,               # Adequate width
    t__gte=6.0,              # Structural thickness
    mass_per_metre__lt=80     # Weight consideration
)
```

#### Angle Searches

```python
# Find equal angles for bracing
bracing_angles = database.search_sections(
    SectionType.L_EQUAL,
    h__gte=80,                # Minimum leg size
    h__lte=150,               # Maximum for typical bracing
    t__gte=6.0,              # Minimum thickness
    mass_per_metre__lt=20     # Weight limit
)

# Find unequal angles for specific applications
asymmetric_angles = database.search_sections(
    SectionType.L_UNEQUAL,
    h__gt=150,                # Long leg minimum
    b__lt=100,                # Short leg maximum
    t__gte=10.0              # Adequate thickness
)
```

## Specialized Search Functions

### Create reusable search functions for common requirements:

```python
def find_beams_for_loading(
    moment_knm: float,
    deflection_limit: float = None,
    depth_limit_mm: float = None
) -> list:
    """Find beams suitable for given moment and deflection."""
    database = get_database()
    
    # Calculate required section modulus (assuming fy = 355 N/mm²)
    required_w = (moment_knm * 1e6) / (0.66 * 355)  # cm³
    
    # Base criteria
    criteria = {
        'W_el_y__gte': required_w / 1000  # Convert to cm³
    }
    
    # Add depth limit if specified
    if depth_limit_mm:
        criteria['h__lte'] = depth_limit_mm
    
    # Find candidates
    candidates = database.search_sections(SectionType.UB, **criteria)
    
    # Apply deflection check if specified
    if deflection_limit and candidates:
        # This would require additional calculation
        # For now, just return the initial results
        pass
    
    return candidates

def find_columns_for_load(
    axial_load_kn: float,
    length_m: float,
    slenderness_limit: float = 150
) -> list:
    """Find columns suitable for axial load and length."""
    database = get_database()
    
    # Estimate required area (simplified)
    # Assuming design strength of 200 N/mm² (conservative)
    required_area = axial_load_kn * 1000 / 200  # mm²
    required_area_cm2 = required_area / 100
    
    # Find candidates
    candidates = database.search_sections(
        SectionType.UC,
        A__gte=required_area_cm2
    )
    
    # Filter by slenderness if needed
    if slenderness_limit and candidates:
        filtered = []
        for designation, data in candidates:
            # Simplified slenderness check
            if 'i_y' in data:
                slenderness = (length_m * 1000) / (data['i_y'] * 10)
                if slenderness <= slenderness_limit:
                    filtered.append((designation, data))
        candidates = filtered
    
    return candidates

# Example usage
suitable_beams = find_beams_for_loading(200, depth_limit_mm=500)
suitable_columns = find_columns_for_load(1000, 4.0)

print(f"Beams for 200 kNm: {len(suitable_beams)}")
print(f"Columns for 1000 kN, 4m: {len(suitable_columns)}")
```

### Optimization Searches

Find the most efficient sections for given criteria:

```python
def find_lightest_sections(section_type: SectionType, min_property: str, min_value: float, count: int = 5):
    """Find the lightest sections meeting minimum property requirement."""
    database = get_database()
    
    # Create search criteria
    criteria = {f"{min_property}__gte": min_value}
    
    # Get all matching sections
    candidates = database.search_sections(section_type, **criteria)
    
    if not candidates:
        return []
    
    # Sort by mass (lightest first)
    candidates.sort(key=lambda x: x[1]['mass_per_metre'])
    
    return candidates[:count]

def find_most_efficient_sections(section_type: SectionType, efficiency_metric: str = 'I_yy', count: int = 5):
    """Find sections with best efficiency (property/mass ratio)."""
    database = get_database()
    
    # Get all sections of this type
    all_sections = database.search_sections(section_type)
    
    if not all_sections:
        return []
    
    # Calculate efficiency for each section
    sections_with_efficiency = []
    for designation, data in all_sections:
        if efficiency_metric in data and 'mass_per_metre' in data:
            efficiency = data[efficiency_metric] / data['mass_per_metre']
            sections_with_efficiency.append((designation, data, efficiency))
    
    # Sort by efficiency (highest first)
    sections_with_efficiency.sort(key=lambda x: x[2], reverse=True)
    
    # Return top sections (without efficiency value)
    return [(d, data) for d, data, eff in sections_with_efficiency[:count]]

# Examples
lightest_strong_beams = find_lightest_sections(SectionType.UB, 'W_el_y', 1000)
most_efficient_beams = find_most_efficient_sections(SectionType.UB, 'I_yy')

print("Lightest beams with W_el_y >= 1000 cm³:")
for designation, data in lightest_strong_beams:
    print(f"  {designation}: {data['mass_per_metre']} kg/m")

print("\nMost efficient beams (I_yy/mass):")
for designation, data in most_efficient_beams:
    efficiency = data['I_yy'] / data['mass_per_metre']
    print(f"  {designation}: {efficiency:.1f} cm⁴/(kg/m)")
```

## Complex Search Scenarios

### Multi-Stage Filtering

Perform searches in stages for complex requirements:

```python
def find_optimal_beam_system(
    primary_span_m: float,
    secondary_span_m: float,
    load_kn_m2: float
) -> dict:
    """Find optimal primary and secondary beam combination."""
    database = get_database()
    
    # Stage 1: Find primary beams
    primary_moment = load_kn_m2 * secondary_span_m * primary_span_m**2 / 8
    required_primary_w = (primary_moment * 1e6) / (0.66 * 355 * 1000)  # cm³
    
    primary_candidates = database.search_sections(
        SectionType.UB,
        W_el_y__gte=required_primary_w,
        h__lte=primary_span_m * 1000 / 20,  # Depth limit
        h__gte=primary_span_m * 1000 / 25   # Minimum depth
    )
    
    # Stage 2: Find secondary beams
    secondary_moment = load_kn_m2 * secondary_span_m**2 / 8
    required_secondary_w = (secondary_moment * 1e6) / (0.66 * 355 * 1000)  # cm³
    
    secondary_candidates = database.search_sections(
        SectionType.UB,
        W_el_y__gte=required_secondary_w,
        h__lte=secondary_span_m * 1000 / 20,
        h__gte=secondary_span_m * 1000 / 25
    )
    
    # Stage 3: Find optimal combination
    if not primary_candidates or not secondary_candidates:
        return None
    
    # Sort by mass
    primary_candidates.sort(key=lambda x: x[1]['mass_per_metre'])
    secondary_candidates.sort(key=lambda x: x[1]['mass_per_metre'])
    
    return {
        'primary_beam': primary_candidates[0],
        'secondary_beam': secondary_candidates[0],
        'primary_alternatives': primary_candidates[1:3],
        'secondary_alternatives': secondary_candidates[1:3]
    }

# Example usage
beam_system = find_optimal_beam_system(12.0, 6.0, 5.0)  # 12m x 6m grid, 5 kN/m²

if beam_system:
    primary_designation, primary_data = beam_system['primary_beam']
    secondary_designation, secondary_data = beam_system['secondary_beam']
    
    print(f"Optimal beam system:")
    print(f"  Primary: {primary_designation} ({primary_data['mass_per_metre']} kg/m)")
    print(f"  Secondary: {secondary_designation} ({secondary_data['mass_per_metre']} kg/m)")
```

### Statistical Analysis

Use search results for statistical analysis:

```python
def analyze_section_distribution(section_type: SectionType) -> dict:
    """Analyze the distribution of properties for a section type."""
    database = get_database()
    
    all_sections = database.search_sections(section_type)
    if not all_sections:
        return {}
    
    # Extract properties
    masses = [data['mass_per_metre'] for _, data in all_sections]
    
    analysis = {
        'count': len(all_sections),
        'mass_stats': {
            'min': min(masses),
            'max': max(masses),
            'mean': sum(masses) / len(masses),
            'range': max(masses) - min(masses)
        }
    }
    
    # Add section-specific analysis
    if section_type in [SectionType.UB, SectionType.UC]:
        heights = [data.get('h', 0) for _, data in all_sections if 'h' in data]
        if heights:
            analysis['height_stats'] = {
                'min': min(heights),
                'max': max(heights),
                'mean': sum(heights) / len(heights)
            }
    
    return analysis

# Analyze all major section types
for section_type in [SectionType.UB, SectionType.UC, SectionType.PFC]:
    stats = analyze_section_distribution(section_type)
    if stats:
        print(f"\n{section_type.value} Statistics:")
        print(f"  Count: {stats['count']}")
        print(f"  Mass range: {stats['mass_stats']['min']:.1f} - {stats['mass_stats']['max']:.1f} kg/m")
        print(f"  Average mass: {stats['mass_stats']['mean']:.1f} kg/m")
        
        if 'height_stats' in stats:
            print(f"  Height range: {stats['height_stats']['min']:.0f} - {stats['height_stats']['max']:.0f} mm")
```

## Search Performance Tips

### Efficient Search Strategies

1. **Use specific criteria** to reduce result sets
2. **Cache database instances** for repeated searches
3. **Combine criteria** rather than filtering afterwards
4. **Use appropriate operators** for your needs

```python
# Good: Specific search
efficient_search = database.search_sections(
    SectionType.UB,
    mass_per_metre__gte=50,
    mass_per_metre__lte=100,
    h__gte=400
)

# Less efficient: Broad search with post-filtering
broad_search = database.search_sections(SectionType.UB)
filtered = [(d, data) for d, data in broad_search 
           if 50 <= data['mass_per_metre'] <= 100 and data.get('h', 0) >= 400]
```

### Caching Search Results

```python
class SectionSearcher:
    """Example class with search result caching."""
    
    def __init__(self):
        self.database = get_database()
        self._cache = {}
    
    def search_with_cache(self, section_type, **criteria):
        """Search with result caching."""
        # Create cache key
        cache_key = (section_type, tuple(sorted(criteria.items())))
        
        if cache_key not in self._cache:
            self._cache[cache_key] = self.database.search_sections(section_type, **criteria)
        
        return self._cache[cache_key]
    
    def clear_cache(self):
        """Clear search cache."""
        self._cache.clear()

# Usage
searcher = SectionSearcher()
results1 = searcher.search_with_cache(SectionType.UB, mass_per_metre__gt=100)
results2 = searcher.search_with_cache(SectionType.UB, mass_per_metre__gt=100)  # From cache
```

## Next Steps

- **[Database System](database.md)** - Understanding the underlying database
- **[Section Types](section-types.md)** - Properties available for each type
- **[Examples](../examples/basic.md)** - Practical search examples
- **[API Reference](../reference/database.md)** - Complete search API

!!! tip "Search Strategy"
    Start with broad criteria and refine progressively. Use the most selective criteria first to improve performance.

!!! note "Property Availability"
    Not all properties are available for all section types. Check the [Section Types](section-types.md) guide for property availability by type.
