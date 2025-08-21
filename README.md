# 🐍 SteelSnakes

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.md)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://steelsnakes.readthedocs.io/)

A powerful Python library for working with UK/European steel sections. Access comprehensive steel section properties with a unified, type-safe interface.

## ✨ Features

- **18 Section Types** - Universal beams, columns, channels, angles, hollow sections, bolts, and welds
- **Advanced Search** - Powerful database search with comparison operators
- **Type Safety** - Built with Pydantic models for complete type safety and validation
- **High Performance** - Efficient JSON-based database with smart caching
- **Factory Pattern** - Auto-detection of section types from designations
- **Complete Properties** - All geometric and mass properties included

## 🚀 Quick Start

### Installation

```bash
pip install steelsnakes
```

### Basic Usage

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

### Advanced Search

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

## 📚 Documentation

- **[Installation Guide](https://steelsnakes.readthedocs.io/getting-started/installation/)** - Get started quickly
- **[User Guide](https://steelsnakes.readthedocs.io/user-guide/section-types/)** - Comprehensive feature documentation
- **[Examples](https://steelsnakes.readthedocs.io/examples/basic/)** - Practical usage examples
- **[API Reference](https://steelsnakes.readthedocs.io/reference/core/)** - Complete API documentation

## 🔧 Section Types Supported

| Category | Types | Count | Standards |
|----------|-------|-------|-----------|
| **Universal Sections** | UB, UC, UBP | 3 | BS EN 10365 |
| **Channels** | PFC | 1 | BS EN 10365 |
| **Angles** | L_EQUAL, L_UNEQUAL, B2B variants | 4 | BS EN 10365 |
| **Hot Finished Hollow** | HFCHS, HFRHS, HFSHS, HFEHS | 4 | BS EN 10365 |
| **Cold Formed Hollow** | CFCHS, CFRHS, CFSHS | 3 | BS EN 10365 |
| **Connection Elements** | Bolts (8.8, 10.9), Welds | 3 | BS EN standards |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://steelsnakes.readthedocs.io/contributing/guidelines/) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgments

- Steel section data sourced from official UK steel supplier tables
- Conforms to BS EN 10365 and related UK/European standards
- Built with modern Python best practices
