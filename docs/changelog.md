# Changelog

All notable changes to SteelSnakes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete MkDocs documentation with Material theme
- Comprehensive API reference documentation
- User guide with detailed examples
- Installation and quick start guides

### Changed
- Enhanced README with better project description
- Improved code organization and structure

## [0.0.1] - 2024-01-XX

### Added
- Initial release of SteelSnakes
- Support for 18 UK/European steel section types:
  - Universal Beams (UB)
  - Universal Columns (UC)
  - Universal Bearing Piles (UBP)
  - Parallel Flange Channels (PFC)
  - Equal Angles (L_EQUAL)
  - Unequal Angles (L_UNEQUAL)
  - Back-to-Back Angles (L_EQUAL_B2B, L_UNEQUAL_B2B)
  - Hot Finished Hollow Sections (HFCHS, HFRHS, HFSHS, HFEHS)
  - Cold Formed Hollow Sections (CFCHS, CFRHS, CFSHS)
  - Preloaded Bolts (BOLT_PRE_88, BOLT_PRE_109)
  - Weld Specifications (WELDS)

- Unified database system with automatic data loading
- Factory pattern for automatic section type detection
- Advanced search capabilities with comparison operators
- Type-safe section properties using Pydantic
- Comprehensive section property database
- JSON-based data storage for all section types
- Automatic path resolution for data files

### Features
- **Type Safety**: Full type hints and Pydantic validation
- **Performance**: Efficient JSON-based database with lazy loading
- **Search**: Advanced filtering with operators (gt, lt, gte, lte, eq, ne)
- **Extensibility**: Easy to add new section types and data
- **Standards Compliance**: All data based on BS EN 10365 and UK standards

### Dependencies
- Python ≥ 3.11
- Pydantic ≥ 2.11.7
- Standard library only (no heavy dependencies)

### Documentation
- Comprehensive docstrings for all classes and methods
- Type hints throughout the codebase
- Example usage in demo scripts

---

## Development Notes

### Version Numbering
SteelSnakes follows semantic versioning:
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards compatible manner
- **PATCH**: Backwards compatible bug fixes

### Release Process
1. Update version in `pyproject.toml`
2. Update this changelog
3. Create git tag with version number
4. Build and publish to PyPI

### Planned Features
See the [project roadmap](https://github.com/waynemaranga/steelsnakes/issues) for upcoming features and improvements.

### Contributing
See [CONTRIBUTING.md](contributing/guidelines.md) for development guidelines and how to contribute to SteelSnakes.
