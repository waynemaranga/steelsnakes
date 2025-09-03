# API Reference

Complete API documentation for the SteelSnakes library with full source code, docstrings, and examples.

## Package Overview

::: steelsnakes
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

## Core Components

The foundation classes and infrastructure that power the SteelSnakes library:

### [Base Classes](core/base.md)
Core abstract classes and enumerations used throughout the library.

- **BaseSection** - Abstract base class for all steel sections
- **SectionType** - Global enumeration of all section types
- **BaseConnector** - Abstract base class for connection components
- **ConnectorType** - Enumeration of connection component types

### [Database System](core/database.md)
Steel section data management and storage infrastructure.

- **SectionDatabase** - Abstract base class for regional databases
- **SQLiteJSONInterface** - High-performance SQLite integration
- **UKSectionDatabase** - UK-specific database implementation
- **USSectionDatabase** - US-specific database implementation

### [Factory Pattern](core/factory.md)
Unified section creation interface across all regions.

- **SectionFactory** - Abstract factory for creating sections
- **UKSectionFactory** - UK-specific section factory
- **USSectionFactory** - US-specific section factory
- **Exception classes** - Comprehensive error handling

## Regional Steel Sections

Steel sections organized by regional standards and specifications:

### [UK (British Standards)](regional/UK/index.md)
Complete implementation of UK steel sections per BS EN 10365:2017.

#### [Universal Sections](regional/UK/universal/index.md)
- **UniversalBeam (UB)** - I-sections for beams and rafters
- **UniversalColumn (UC)** - I-sections for columns and heavy beams
- **UniversalBearingPile (UBP)** - I-sections for driven piles

#### [Channel Sections](regional/UK/channels/index.md)
- **ParallelFlangeChannel (PFC)** - C-sections for purlins and side rails

#### [Angle Sections](regional/UK/angles/index.md)
- **EqualAngle** - L-sections with equal legs
- **UnequalAngle** - L-sections with unequal legs
- **Back-to-Back variants** - Built-up angle combinations

#### [Hollow Sections](regional/UK/hollow/index.md)
- **Hot Finished (HF)** - Circular, square, rectangular, elliptical per BS EN 10210
- **Cold Formed (CF)** - Circular, square, rectangular per BS EN 10219

#### [Connection Components](regional/UK/connections/index.md)
- **Preloaded Bolts** - Bolt specifications per BS EN 14399
- **Weld Specifications** - Weld properties and classifications

### [US (American Standards)](regional/US/index.md)
American steel sections per AISC standards and ASTM A6/A6M.

- **Wide Flange Beams (W)** - Primary structural beams
- **Standard Beams (S)** - American standard I-beams
- **Miscellaneous Beams (M)** - Specialty beam sections
- **Standard Channels (C)** - American standard channels
- **Miscellaneous Channels (MC)** - Specialty channel sections
- **Angles** - Equal and unequal angles, double angles
- **Hollow Structural Sections (HSS)** - Round, square, rectangular
- **Pipe Sections** - Standard and extra strong pipes
- **Tee Sections (WT, ST, MT)** - Structural tees

### [EU (European Standards)](regional/EU/index.md)
European steel sections per EN 10365:2017.

- **IPE Beams** - European standard I-beams
- **HE Beams** - European wide flange beams (HEA, HEB, HEM)
- **UPE/UPN Channels** - European parallel and tapered channels
- **Angles** - Equal and unequal angles
- **Flat Sections** - European flat bar sections

### [Indian Standards](regional/IS/index.md) *(In Development)*
Indian steel sections per IS 808:2021.

- **ISJB, ISLB, ISMB** - Junior, light, and medium weight beams
- **ISWB, ISNPB, ISWBP** - Wide flange and parallel flange beams
- **ISSC, ISHB** - Standard columns and heavy beams
- **ISJC, ISLC, ISMC** - Junior, light, and medium weight channels
- **ISA** - Equal and unequal angles
- **ISPBP** - Bearing pile sections

### [Australian Standards](regional/AU/index.md) *(Planned)*
Australian steel sections per AS/NZS 3679.1:2016.

## CLI and Main Module

### Command Line Interface

::: steelsnakes.cli
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

### Main Module

::: steelsnakes.main
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

## Quick Reference

### Most Common Classes

| Class | Purpose | Example |
|-------|---------|---------|
| `UB` | UK Universal Beam | `UB("457x191x67")` |
| `UC` | UK Universal Column | `UC("305x305x137")` |
| `PFC` | UK Parallel Flange Channel | `PFC("430x100x64")` |
| `W` | US Wide Flange Beam | `W("W18x50")` |
| `C` | US Standard Channel | `C("C10x20")` |
| `IPE` | EU I-Beam | `IPE("IPE400")` |

### Core Infrastructure

| Class | Purpose | Module |
|-------|---------|--------|
| `BaseSection` | Base class for all sections | `steelsnakes.base.sections` |
| `SectionType` | Section type enumeration | `steelsnakes.base.sections` |
| `SectionDatabase` | Database interface | `steelsnakes.base.database` |
| `SectionFactory` | Factory pattern | `steelsnakes.base.factory` |

### Error Classes

| Exception | When Raised | Module |
|-----------|-------------|--------|
| `SectionNotFoundError` | Invalid section designation | `steelsnakes.base.exceptions` |
| `SectionTypeNotRegisteredError` | Unsupported section type | `steelsnakes.base.exceptions` |
| `SectionFactoryError` | Factory creation failure | `steelsnakes.base.exceptions` |

!!! tip "Getting Started"
    New to SteelSnakes? Start with the [Getting Started Guide](../02-getting-started/installation.md) and [Basic Usage Examples](../04-examples/basic.md).

!!! info "Source Code"
    All API documentation includes full source code. Use the mkdocstrings configuration to show/hide source as needed.