# `steelsnakes`

![Logo](./docs/logo-4.png)

<div align="center">
  <p>
  <!-- python version -->
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version" style="margin: 2px;"/></a>
    <!-- license -->
     <a href="./LICENSE.md"><img src="https://img.shields.io/badge/license-GPLv2-blue.svg" alt="License" style="margin: 2px;"/></a>
    <!-- pypi version -->
     <a href="https://pypi.org/project/steelsnakes/"><img src="https://img.shields.io/pypi/v/steelsnakes.svg" alt="PyPI Version" style="margin: 2px;"/></a>
    <!-- documentation -->
     <a href="https://steelsnakes.readthedocs.io/"><img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" style="margin: 2px;"/></a>
    <!-- build status -->
    <!-- <a href="#"><img src="https://img.shields.io/github/actions/workflow/status/steelsnakes/steelsnakes/ci.yml?branch=main" alt="Build Status" style="margin: 2px;</a> -->
    <!-- pypi stats -->
    <a href="https://pepy.tech/projects/steelsnakes"><img src="https://static.pepy.tech/personalized-badge/steelsnakes?period=total&units=ABBREVIATION&left_color=GREY&right_color=BLUE&left_text=downloads" alt="PyPI Downloads"></a>
    

  </p>
</div>

A python library for structural steel.
Currently supports 🇬🇧 UK, 🇪🇺 EU, 🇺🇸 US
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

- **[Installation Guide](https://steelsnakes.readthedocs.io/en/latest/getting-started/installation/)** - Get started quickly
- **[User Guide](https://steelsnakes.readthedocs.io/en/latest/user-guide/section-types/)** - Comprehensive feature documentation
- **[Examples](https://steelsnakes.readthedocs.io/en/latest/examples/basic/)** - Practical usage examples
- **[API Reference](https://steelsnakes.readthedocs.io/en/latest/reference/core/)** - Complete API documentation

## Eurocode Classification Example

```python
from steelsnakes.EU import (
    IPE,
    ElementInput,
    ElementStressCase,
    StressPattern,
    classify_section,
)

section = IPE("IPE-750x220")

compression_result = classify_section(section=section, fy_mpa=355.0)

bending_result = classify_section(
    section=section,
    fy_mpa=355.0,
    stress_pattern="bending-major-axis",
)

combined_result = classify_section(
    fy_mpa=275.0,
    custom_elements=[
        ElementInput(
            name="web",
            kind="internal",
            c_mm=360.4,
            t_mm=7.7,
            stress=ElementStressCase.COMBINED,
            alpha=0.70,
        )
    ],
)

print(compression_result.section_class)
print(bending_result.section_class)
print(combined_result.section_class)
```

`stress_pattern` accepts either a simple string like `"compression"` or `"bending-major-axis"`, or the enum value `StressPattern.MAJOR_AXIS_BENDING`.

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
