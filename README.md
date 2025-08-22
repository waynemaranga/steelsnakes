# `SteelSnakes`

<!-- Centered HTML-image logo -->
<p align="center"><img src="https://imgur.com/a/xp0MJrV" alt="SteelSnakes Logo" width="200"/></p>


[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-GPLv2-blue.svg)](./LICENSE.md)
[![PyPI Version](https://img.shields.io/pypi/v/steelsnakes.svg)](https://pypi.org/project/steelsnakes/)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://steelsnakes.readthedocs.io/)
<!-- [![Build Status](https://img.shields.io/github/actions/workflow/status/steelsnakes/steelsnakes/ci.yml?branch=main)]( -->

A Python library for structural steel analysis and design, providing easy access to a comprehensive database of steel sections and their properties. Currently supports UK steel sections according to BS EN 10365.

Currently Developing: US and AUS


## Quick Start

### Installation

```bash
pip install steelsnakes
```

### Basic Usage

```python
from steelsnakes.core.sections.UK import UB, UC, PFC

# Create section objects using the designations
beam = UB("457x191x67") # Universal Beam
column = UC("305x305x137") # Universal Column
channel = PFC("430x100x64") # Parallel Flange Channel

# Access properties immediately
print(f"Beam moment of inertia: {beam.I_yy} cm⁴")
print(f"Column mass: {column.mass_per_metre} kg/m")
print(f"Channel shear center: {channel.e0} mm")
```

<!-- ### Advanced Search

```python
from steelsnakes.core.sections.UK import get_database, SectionType

database = get_database()

# Find heavy beams
heavy_beams = database.search_sections(SectionType.UB, mass_per_metre__gt=200)

# Find deep channels
deep_channels = database.search_sections(SectionType.PFC, h__gt=300,b__gt=100
)
``` -->

## Documentation

- **[Installation Guide](https://steelsnakes.readthedocs.io/getting-started/installation/)** - Get started quickly
- **[User Guide](https://steelsnakes.readthedocs.io/user-guide/section-types/)** - Comprehensive feature documentation
- **[Examples](https://steelsnakes.readthedocs.io/examples/basic/)** - Practical usage examples
- **[API Reference](https://steelsnakes.readthedocs.io/reference/core/)** - Complete API documentation

## Section Types Supported
### UK Sections

| Category                | Types                             | Standards       |
| ----------------------- | --------------------------------- | --------------- |
| **Universal Sections**  | UB, UC, UBP                       | BS EN 10365     |
| **Channels**            | PFC                               | BS EN 10365     |
| **Angles**              | L_EQUAL, L_UNEQUAL, B2B variants  | BS EN 10365     |
| **Hot Finished Hollow** | HFCHS, HFRHS, HFSHS, HFEHS        | BS EN 10365     |
| **Cold Formed Hollow**  | CFCHS, CFRHS, CFSHS               | BS EN 10365     |
| **Connection Elements** | PreloadedBolts (8.8, 10.9), Welds | BS EN standards |

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://steelsnakes.readthedocs.io/contributing/guidelines/) for details.

## License

This project is licensed under the GPLv2 License - see the [LICENSE.md](./LICENSE.md) file for details.

## Acknowledgments

- SCI (The Steel Construction Institute) for the [Interactive Blue Book](https://www.steelforlifebluebook.co.uk/)
- 
- [Steelweb.info](http://www.steelweb.info/) for Australian steel section data
