# API Reference

Complete API documentation for the SteelSnakes library. This reference covers all modules, classes, and functions available in the library.

## Core Components

The foundation classes and infrastructure that power the SteelSnakes library:

- **[Base Classes](core/base.md)** - Fundamental base classes and types
- **[Database System](core/database.md)** - Steel section data management
- **[Factory Pattern](core/factory.md)** - Unified section creation interface

## Regional Steel Sections

Steel sections organized by regional standards and specifications:

### UK (British Standards)
- **[Overview](regional/UK/index.md)** - UK steel sections overview
- **[Universal Sections](regional/UK/universal/index.md)** - UB, UC, UBP sections
- **[Channels](regional/UK/channels/index.md)** - Parallel flange channels (PFC)
- **[Angles](regional/UK/angles/index.md)** - Equal and unequal angles
- **[Hollow Sections](regional/UK/hollow/index.md)** - Cold formed and hot finished
- **[Connections](regional/UK/connections/index.md)** - Bolts and weld specifications

### Other Regions
- **[US (American)](regional/US/index.md)** - AISC standard sections *(coming soon)*
- **[EU (European)](regional/EU/index.md)** - Eurocode sections *(coming soon)*
- **[AU (Australian)](regional/AU/index.md)** - AS standard sections *(coming soon)*
- **[IS (Indian)](regional/IS/index.md)** - IS standard sections *(coming soon)*

## Quick Navigation

### Most Common Sections
- [Universal Beams (UB)](regional/UK/universal/index.md#universal-beams-ub)
- [Universal Columns (UC)](regional/UK/universal/index.md#universal-columns-uc)
- [Parallel Flange Channels (PFC)](regional/UK/channels/index.md)
- [Equal Angles](regional/UK/angles/index.md#equal-angles)

### Core Infrastructure
- [BaseSection](core/base.md#steelsnakes.base.sections.BaseSection) - All sections inherit from this
- [SectionDatabase](core/database.md#steelsnakes.base.database.SectionDatabase) - Database interface
- [SectionFactory](core/factory.md#steelsnakes.base.factory.SectionFactory) - Factory pattern implementation

!!! tip "Getting Started"
    New to SteelSnakes? Start with the [Getting Started Guide](../getting-started/installation.md) and [Basic Usage Examples](../examples/basic.md).
