# `SteelSnakes`

<div class="hero">
  <img src="./logo-4.png" alt="SteelSnakes Logo" class="hero-logo"/>
  <!-- <h1>SteelSnakes</h1> -->
  <p>A powerful Python library for working with UK/European steel sections. Access comprehensive steel section properties with a unified, type-safe interface.</p>
  
  <div class="hero-buttons">
    <a href="getting-started/installation/" class="hero-button">Get Started</a>
    <a href="examples/basic/" class="hero-button hero-button--secondary">View Examples</a>
  </div>
</div>

## Features

<div class="features">
  <div class="feature-card">
    <!-- <span class="feature-icon">🏗️</span> -->
    <h3>Section Properties</h3>
    <p>Dimensional, geometric, and mass properties for standard/retail structural steel sections.</p>
  </div>
  
  <div class="feature-card">
    <!-- <span class="feature-icon">🔍</span> -->
    <h3>Advanced Search</h3>
    <p>Database search with comparison operators. Find sections by dimensions, mass, or any property.</p>
  </div>
  
  <div class="feature-card">
    <!-- <span class="feature-icon">🎯</span> -->
    <h3>Type Safety</h3>
    <p>Built with Pydantic models for complete type safety and validation. Catch errors at development time.</p>
  </div>
  
  <div class="feature-card">
    <!-- <span class="feature-icon">⚡</span> -->
    <h3>High Performance</h3>
    <p>Efficient JSON-based database with smart caching. Fast lookups and minimal memory footprint.</p>
  </div>
  
  <div class="feature-card">
    <!-- <span class="feature-icon">🔧</span> -->
    <h3>Factory Pattern</h3>
    <p>Auto-detection of section types from designations. Clean, consistent API across all section types.</p>
  </div>
  
  <div class="feature-card">
    <!-- <span class="feature-icon">📐</span> -->
    <h3>Complete Properties</h3>
    <p>All geometric and mass properties included. Moment of inertia, section modulus, radii of gyration, and more.</p>
  </div>

</div>

## Quick Start

Get up and running with SteelSnakes in minutes:

=== "Installation"

    ```bash
    pip install steelsnakes
    ```

=== "Basic Usage"

    ```python
    from steelsnakes.core.sections.UK import UB, UC, PFC
    
    # Create sections using simple designations
    beam = UB("457x191x67")
    column = UC("305x305x137")
    channel = PFC("430x100x64")
    
    # Access properties immediately
    print(f"Beam moment of inertia: {beam.I_yy} cm⁴")
    print(f"Column mass: {column.mass_per_metre} kg/m")
    print(f"Channel shear center: {channel.e0} mm")
    ```

=== "Advanced Search"

    ```python
    from steelsnakes.core.sections.UK import get_database, SectionType
    
    database = get_database()
    
    # Find heavy beams
    heavy_beams = database.search_sections(
        SectionType.UB, 
        mass_per_metre__gt=200
    )
    
    # Find deep channels
    deep_channels = database.search_sections(
        SectionType.PFC,
        h__gt=300,
        b__gt=100
    )
    ```

## Section Types Supported
### UK 

| Category                | Types                            | Count | Standards       |
| ----------------------- | -------------------------------- | ----- | --------------- |
| **Universal Sections**  | UB, UC, UBP                      | 3     | BS EN 10365     |
| **Channels**            | PFC                              | 1     | BS EN 10365     |
| **Angles**              | L_EQUAL, L_UNEQUAL, B2B variants | 4     | BS EN 10365     |
| **Hot Finished Hollow** | HFCHS, HFRHS, HFSHS, HFEHS       | 4     | BS EN 10365     |
| **Cold Formed Hollow**  | CFCHS, CFRHS, CFSHS              | 3     | BS EN 10365     |
| **Connection Elements** | Bolts (8.8, 10.9), Welds         | 3     | BS EN standards |

<!-- !!! engineering "Engineering Note"
    All section data conforms to current UK/European standards (BS EN 10365, BS EN 1993) and includes the latest section properties from major UK steel suppliers. -->

<!-- ## Why SteelSnakes?

SteelSnakes was born from the need for a modern, type-safe approach to steel section data in Python. Traditional approaches often involve:

- ❌ Scattered CSV files and manual lookups
- ❌ No type safety or validation
- ❌ Inconsistent interfaces between section types
- ❌ Limited search capabilities

SteelSnakes provides:

- ✅ **Unified interface** - Same API for all section types
- ✅ **Type safety** - Pydantic models catch errors early
- ✅ **Comprehensive database** - 18+ section types included
- ✅ **Advanced search** - Query by any property with operators
- ✅ **Modern Python** - Uses latest language features and best practices -->

## Getting Help

- **Documentation**: You're reading it! Check the sidebar for detailed guides
- **Issues**: [GitHub Issues](https://github.com/waynemaranga/steelsnakes/issues)
- **Discussions**: [GitHub Discussions](https://github.com/waynemaranga/steelsnakes/discussions)
- **Email**: [waynemaranga@gmail.com](mailto:waynemaranga@gmail.com)

## License

SteelSnakes is released under the GPLv2 License. See the [LICENSE](https://github.com/waynemaranga/steelsnakes/blob/main/LICENSE.md) file for details.

---

<div style="text-align: center; padding: 2rem; background: var(--md-code-bg-color); border-radius: 0.5rem; margin: 2rem 0;">
  <strong>Ready to get started?</strong><br>
  <a href="getting-started/installation/" class="hero-button" style="margin-top: 1rem;">Install SteelSnakes →</a>
</div>
