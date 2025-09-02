# `steelsnakes`

![Logo](./logo-4.png)

<div align="center">
  <p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version" style="margin: 2px;"/></a> <a href="./LICENSE.md"><img src="https://img.shields.io/badge/license-GPLv2-blue.svg" alt="License" style="margin: 2px;"/></a> <a href="https://pypi.org/project/steelsnakes/"><img src="https://img.shields.io/pypi/v/steelsnakes.svg" alt="PyPI Version" style="margin: 2px;"/></a> <a href="https://steelsnakes.readthedocs.io/"><img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" style="margin: 2px;"/></a>
    <!-- <a href="#"><img src="https://img.shields.io/github/actions/workflow/status/steelsnakes/steelsnakes/ci.yml?branch=main" alt="Build Status" style="margin: 2px;</a> -->
  </p>
</div>

A python library for structural steel.
Currently supports 🇬🇧 UK, 🇪🇺 EU, 🇺🇸 US.
Developing 🇮🇳 IN.
Considering 🇦🇺 AU / 🇳🇿 NZ, 🇯🇵 JP, 🇲🇽 MX, 🇿🇦 SA, 🇨🇳 CN, 🇨🇦 CA, 🇰🇷 KR.

## Quick Start

### Installation

```bash
pip install steelsnakes
```

### Basic Usage

```python
from steelsnakes.UK import UB, UC, PFC

# Create section objects using the designations
beam = UB("457x191x67") # Universal Beam
column = UC("305x305x137") # Universal Column
channel = PFC("430x100x64") # Parallel Flange Channel

# Access properties immediately
print(f"Beam moment of inertia: {beam.I_yy} cm⁴")
print(f"Column mass: {column.mass_per_metre} kg/m")
print(f"Channel shear center: {channel.e0} mm")
```

## Documentation

Comprehensive documentation to get you started and master SteelSnakes:

- **[Overview](01-overview/what-is-steelsnakes.md)** - What is SteelSnakes and why use it?
- **[Getting Started](02-getting-started/installation.md)** - Installation and quick start guide
- **[User Guide](03-user-guide/sections.md)** - In-depth guides and concepts
- **[Examples](04-examples/basic.md)** - Practical code examples and use cases
- **[API Reference](05-api-reference/index.md)** - Complete API documentation

### Quick Navigation

| I want to... | Go to... |
|---------------|----------|
| **Install SteelSnakes** | [Installation Guide →](02-getting-started/installation.md) |
| **Learn the basics** | [Quick Start Guide →](02-getting-started/quickstart.md) |
| **See code examples** | [Basic Examples →](04-examples/basic.md) |
| **Find a specific API** | [API Reference →](05-api-reference/index.md) |
| **Understand section types** | [Section Types Guide →](03-user-guide/sections.md) |

## Contributing

All contributions are welcome! See the [Contributing Guidelines](https://steelsnakes.readthedocs.io/en/latest/contributing/) for details.

## License

This project is licensed under the GNU General Public License v2.0. See the [LICENSE](https://github.com/waynemaranga/steelsnakes/blob/main/LICENSE.md) file for details.

## Acknowledgments

- SCI (Steel Construction Institute)
- ArcelorMittal
- AISC (American Institute of Steel Construction)
- SAISC (South African Institute of Steel Construction)

---
