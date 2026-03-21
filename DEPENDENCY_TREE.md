# SteelSnakes - Features & Dependency Tree

**Version:** 0.0.1-alpha-7  
**Last Updated:** 2026-01-15  
**Python:** 3.11+

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Dependencies](#core-dependencies)
3. [Base System Architecture](#base-system-architecture)
4. [Regional Implementations](#regional-implementations)
5. [Analysis & Design Checks](#analysis--design-checks)
6. [CLI and Tooling](#cli-and-tooling)
7. [Feature Dependency Matrix](#feature-dependency-matrix)

---

## Project Overview

SteelSnakes is a comprehensive Python library for structural steel engineering, providing access to steel section properties, design checks, and analysis capabilities across multiple international standards.

### Supported Regions
- 🇬🇧 **UK** - Fully implemented (Primary)
- 🇪🇺 **EU** - Partially implemented
- 🇺🇸 **US** - Partially implemented
- 🇮🇳 **IN** - In development
- 🇦🇺 **AU** / 🇳🇿 **NZ** - Preliminary support
- **US_Metric** - US sections with metric units

### Considered for Future
🇯🇵 JP, 🇲🇽 MX, 🇿🇦 SA, 🇨🇳 CN, 🇨🇦 CA, 🇰🇷 KR

---

## Core Dependencies

### Runtime Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| **pydantic** | ≥2.11.7 | Data validation and settings management for section properties |
| **sqlalchemy** | ≥2.0.43 | Database ORM for optional SQLite acceleration |
| **numpy** | ≥2.3.2 | Numerical computations for section properties |

### Development Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | ≥8.4.1 | Testing framework |
| **pytest-cov** | ≥6.2.1 | Test coverage reporting |
| **coverage** | 7.10.0 | Code coverage measurement |
| **ruff** | (optional) | Linting and code formatting |

### Documentation Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| **mkdocs** | ≥1.6.1 | Documentation site generator |
| **mkdocs-shadcn** | 0.9.3 | Modern documentation theme |
| **mkdocstrings[python]** | ≥0.30.0 | API documentation from docstrings |
| **pymdown-extensions** | ≥10.16.1 | Markdown extensions for documentation |

---

## Base System Architecture

### 1. Section System (`steelsnakes.base.sections`)

**Purpose:** Foundation for all steel section types across all regions

**Key Components:**
- `SectionType` - Global enumeration of 40+ section types
- `BaseSection` - Abstract base class for all sections

**Dependencies:**
- Python Standard Library: `abc`, `dataclasses`, `enum`, `typing`, `logging`
- No external dependencies

**Supported Section Types:**

#### UK Sections
- **Universal Sections:** UB, UC, UBP
- **Channels:** PFC
- **Angles:** L_EQUAL, L_UNEQUAL, L_EQUAL_B2B, L_UNEQUAL_B2B
- **Hollow Sections (Hot Finished):** HFCHS, HFRHS, HFSHS, HFEHS
- **Hollow Sections (Cold Formed):** CFCHS, CFRHS, CFSHS

#### EU Sections
- **Beams:** IPE, HE, HL, HLZ
- **Columns:** HD
- **Bearing Piles:** HP
- **Channels:** UPE, UPN
- **Flats:** Sigma, Zed
- **Angles:** Shared with UK

#### US Sections
- **Beams:** W, S, M
- **Channels:** C, MC, C2C, MC2C
- **Angles:** L_EQUAL, L_UNEQUAL, L2L_EQUAL, L2L_UNEQUAL
- **Tees:** WT, MT
- **Bearing Piles:** HP (shared with EU)

---

### 2. Database System (`steelsnakes.base.database`)

**Purpose:** Generic database abstraction for loading and querying section data

**Key Components:**
- `SectionDatabase` - Abstract base class for region-specific databases
- JSON file loading and caching
- Optional SQLite support (experimental)

**Dependencies:**
- Python Standard Library: `abc`, `pathlib`, `json`, `sqlite3`, `logging`, `typing`
- **sqlalchemy** ≥2.0.43 (for SQLite functionality)

**Features:**
- JSON-based section property storage
- In-memory caching for fast lookups
- Fuzzy section searching
- Type-safe section retrieval

**Region Implementations:**
- `steelsnakes.UK.database.UKSectionDatabase`
- `steelsnakes.EU.database.EUSectionDatabase`
- `steelsnakes.US.database.USSectionDatabase`
- `steelsnakes.US_Metric.database.USMetricSectionDatabase`

---

### 3. Factory System (`steelsnakes.base.factory`)

**Purpose:** Generic factory pattern for creating section objects

**Key Components:**
- `SectionFactory` - Abstract base class for region-specific factories
- Section class registration system
- Intelligent error messages with suggestions

**Dependencies:**
- Python Standard Library: `abc`, `typing`, `logging`, `difflib`
- **steelsnakes.base.sections:** BaseSection, SectionType
- **steelsnakes.base.database:** SectionDatabase
- **steelsnakes.base.exceptions:** Custom exceptions

**Features:**
- Automatic section type detection
- Fuzzy matching for typos
- Cross-type designation checking
- Extensible registration system

**Region Implementations:**
- `steelsnakes.UK.factory.UKSectionFactory`
- `steelsnakes.EU.factory.EUSectionFactory`
- `steelsnakes.US.factory.USSectionFactory`
- `steelsnakes.US_Metric.factory.USMetricSectionFactory`

---

### 4. Checks & Analysis (`steelsnakes.base.checks`)

**Purpose:** Base classes for structural design checks and analysis

**Key Components:**
- `DesignCode` - Enumeration of design codes (EN 1993, AISC 360, IS 800, AS 4100, BS 5950)
- `LimitState` - Ultimate and serviceability limit states
- `SectionClass` - Cross-section classification (EU/UK: Class 1-4, US: Compact/Noncompact/Slender)
- `Classification` - Classification result model
- `UtilisationCheck` - Utilization check result model
- `BaseCheck` - Abstract base for all checks

**Dependencies:**
- Python Standard Library: `abc`, `enum`, `logging`, `typing`, `math`
- **pydantic** ≥2.11.7 (for BaseModel validation)

**Design Codes Supported:**
- EN_1993 (Eurocode 3)
- BS_EN_1993_UKNA (Eurocode 3 with UK National Annex)
- BS_5950_1 (British Standard)
- AISC_360 (American)
- IS_800 (Indian)
- AS_4100 (Australian)

**Limit States:**
- **EU/UK:** ULS, SLS
- **US (LRFD):** Tensile yielding/rupture, flexural/torsional/lateral-torsional buckling, plastic moment yielding, shear buckling, flange/web local buckling

---

### 5. Connectors System (`steelsnakes.base.connectors`)

**Purpose:** Base system for bolts, welds, and connections

**Key Components:**
- `ConnectorType` - Enumeration of connector types
- `BaseConnector` - Abstract base for all connectors

**Dependencies:**
- Python Standard Library: `abc`, `dataclasses`, `enum`, `logging`, `typing`

**Connector Types:**
- **Welds:** General weld specifications
- **Preloaded Bolts:** Grade 8.8, Grade 10.9
- **Non-preloaded Bolts:** (Planned: countersunk, hexagon, various grades)

**Status:** Foundation implemented, connector-specific implementations pending

---

### 6. Materials System (`steelsnakes.base.materials`)

**Purpose:** Material properties and specifications

**Status:** Placeholder - to be implemented

**Planned Materials:**
- **UK/EU:** S355, S460, S275 (deprecated)
- **US:** Various ASTM grades
- **Special:** Bolt/weld material properties

---

### 7. Exception System (`steelsnakes.base.exceptions`)

**Purpose:** Custom exception classes for error handling

**Dependencies:**
- Python Standard Library only

**Key Exceptions:**
- `SectionNotFoundError` - Section designation not found in database
- `SectionTypeNotRegisteredError` - Section type not registered in factory

---

## Regional Implementations

### 🇬🇧 UK Module (`steelsnakes.UK`)

**Status:** ✅ Fully implemented (Primary reference implementation)

**Data Source:** Steel Construction Institute (SCI) Blue Book

#### Section Types

##### Universal Sections (`steelsnakes.UK.universal`)
- **UniversalBeam (UB)** - I-shaped beams for primary structural members
- **UniversalColumn (UC)** - Heavy I-sections optimized for axial load
- **UniversalBearingPile (UBP)** - Heavy sections for foundation piles

**Properties:**
- Mass per metre, dimensional properties (h, b, tw, tf, r, d)
- Slenderness ratios (cw_tw, cf_tf)
- Clearances (C, N, n)
- Surface areas
- Second moments of area (I_yy, I_zz)
- Radii of gyration (i_yy, i_zz)
- Section moduli (W_el_yy, W_el_zz, W_pl_yy, W_pl_zz)
- Buckling parameters (U, X)
- Torsion properties (I_w, I_t)
- Cross-sectional area (A)

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.UK.factory

##### Channels (`steelsnakes.UK.channels`)
- **ParallelFlangeChannel (PFC)** - C-sections for secondary beams, purlins, cladding rails

**Properties:**
- Similar to universal sections
- Additional: Shear center (e0)

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.UK.factory

##### Angles (`steelsnakes.UK.angles`)
- **EqualAngle** - L-sections with equal legs for bracing and connections
- **UnequalAngle** - L-sections with unequal legs
- **EqualAngleBackToBack** - Double equal angles
- **UnequalAngleBackToBack** - Double unequal angles

**Properties:**
- Leg dimensions (hxh, hxb)
- Thickness (t)
- Radii (r_1, r_2)
- Centroidal distances (c, c_y, c_z)
- Principal axis properties (I_uu, I_vv, i_uu, i_vv)
- Geometric axis properties (I_yy, I_zz, i_yy, i_zz)
- Section moduli and cross-sectional area

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.UK.factory

##### Hollow Sections - Hot Finished (`steelsnakes.UK.hf_hollow`)
- **HotFinishedCHS** - Circular hollow sections
- **HotFinishedRHS** - Rectangular hollow sections
- **HotFinishedSHS** - Square hollow sections
- **HotFinishedEHS** - Elliptical hollow sections

**Properties:**
- Outer dimensions (D for circular, hxb for rectangular)
- Wall thickness (t)
- Corner radius (r) for rectangular/square
- Mass, area, surface areas
- Second moments of area and radii of gyration
- Section moduli (elastic and plastic)
- Torsion constant (I_t)

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.UK.factory

##### Hollow Sections - Cold Formed (`steelsnakes.UK.cf_hollow`)
- **ColdFormedCHS** - Circular hollow sections
- **ColdFormedRHS** - Rectangular hollow sections
- **ColdFormedSHS** - Square hollow sections

**Properties:** Similar to hot finished sections

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.UK.factory

##### Connectors (`steelsnakes.UK.preloaded_bolts`, `steelsnakes.UK.welds`)
**Status:** Commented out / Pending implementation

- **PreloadedBolt88** - Grade 8.8 preloaded bolts
- **PreloadedBolt109** - Grade 10.9 preloaded bolts
- **WeldSpecification** - Weld details

#### Design Checks (`steelsnakes.UK.checks`)

##### Classification (`steelsnakes.UK.checks.classification`)
**Status:** Placeholder
**Purpose:** EN 1993-1-1 Table 5.2 cross-section classification

##### Ultimate Limit State (`steelsnakes.UK.checks.uls`)
**Status:** In development
**Purpose:** ULS design checks per Eurocode 3 with UK NA

**Dependencies:**
- steelsnakes.base.checks
- steelsnakes.base.sections

##### Stability (`steelsnakes.UK.checks.stability`)
**Status:** Placeholder
**Purpose:** Member stability checks (buckling)

#### Database (`steelsnakes.UK.database`)
**Implementation:** UKSectionDatabase extends SectionDatabase

**Dependencies:**
- steelsnakes.base.database
- steelsnakes.base.sections
- JSON data files in `steelsnakes.UK.data/`

**Features:**
- UK-specific designation parsing (e.g., "457x191x67")
- Fuzzy finding for UK formats
- Support for all UK section types

#### Factory (`steelsnakes.UK.factory`)
**Implementation:** UKSectionFactory extends SectionFactory

**Registered Classes:**
- UniversalBeam, UniversalColumn, UniversalBearingPile
- ParallelFlangeChannel
- EqualAngle, UnequalAngle, EqualAngleBackToBack, UnequalAngleBackToBack
- HotFinishedCHS, HotFinishedRHS, HotFinishedSHS, HotFinishedEHS
- ColdFormedCHS, ColdFormedRHS, ColdFormedSHS

**Convenience Functions:**
```python
from steelsnakes.UK import UB, UC, UBP, PFC
section = UB("457x191x67")  # Direct instantiation
```

**Dependencies:**
- steelsnakes.base.factory
- steelsnakes.UK.database
- All UK section classes

---

### 🇪🇺 EU Module (`steelsnakes.EU`)

**Status:** ⚠️ Partially implemented

**Data Source:** ArcelorMittal Orange Book

#### Section Types

##### Beams (`steelsnakes.EU.beams`)
- **IPEBeam** - Parallel flange I-beams (IPE)
- **HEBeam** - Wide flange beams (HE)
- **HLBeam** - Extra wide flange beams (HL)
- **HLZBeam** - Extra wide flange beams with different properties (HLZ)

**Properties:** Similar to UK universal sections plus:
- `histar_fy` - Yield strength from Histar calculation

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.EU.factory

##### Columns (`steelsnakes.EU.columns`)
- **HDColumn** - Wide flange columns

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.EU.factory

##### Bearing Piles (`steelsnakes.EU.piles`)
- **HPPile** - Wide flange bearing piles

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.EU.factory

##### Channels (`steelsnakes.EU.channels`)
- **UPEChannel** - Parallel flange channels
- **UPNChannel** - Tapered flange channels

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.EU.factory

##### Angles (`steelsnakes.EU.angles`)
- Shares angle types with UK (EqualAngle, UnequalAngle, B2B variants)

##### Flats (`steelsnakes.EU.flats`)
- **SigmaSection** - Sigma sections
- **ZedSection** - Zed-butted sections

**Status:** Pending effective properties implementation

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.EU.factory

#### Design Checks (`steelsnakes.EU.checks`)

##### Ultimate Limit State (`steelsnakes.EU.checks.uls`)
**Status:** In development
**Purpose:** EN 1993-1-1 design checks

#### Database & Factory
**Implementation:** Similar to UK with EU-specific designation parsing

**Dependencies:**
- steelsnakes.base.database
- steelsnakes.base.factory
- JSON data in `steelsnakes.EU.data/`

---

### 🇺🇸 US Module (`steelsnakes.US`)

**Status:** ⚠️ Partially implemented (Imperial units)

**Data Source:** AISC Steel Construction Manual v16

#### Section Types

##### Beams (`steelsnakes.US.beams`)
- **WBeam** - Wide flange beams (most common)
- **SBeam** - Standard I-beams
- **MBeam** - Miscellaneous beams

**Properties (Imperial Units):**
- Weight per foot (W, lb/ft)
- Dimensions (d, bf, tw, tf - inches)
- Detailing dimensions (ddet, bfdet, twdet, tfdet, kdes, kdet, k1)
- Compact section criteria (bf_2tf, h_tw)
- Moment of inertia (Ix, Iy - in⁴)
- Section moduli (Sx, Sy - elastic, Zx, Zy - plastic, in³)
- Radii of gyration (rx, ry - inches)
- Torsion constant (J - in⁴)
- Warping constant (Cw - in⁶)
- Additional properties (Wno, Sw1, Qf, Qw, rts, ho)

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

##### Channels (`steelsnakes.US.channels`)
- **CChannel** - Standard channels
- **MCChannel** - Miscellaneous channels
- **C2CChannel** - Back-to-back standard channels
- **MC2CChannel** - Back-to-back miscellaneous channels

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

##### Angles (`steelsnakes.US.angles`)
- **LEqual** - Equal leg angles
- **LUnequal** - Unequal leg angles
- **L2LEqual** - Double equal angles
- **L2LUnequal** - Double unequal angles

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

##### Tees (`steelsnakes.US.tees`)
- **WTTee** - Structural tees cut from W-shapes
- **MTTee** - Structural tees cut from M-shapes

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

##### Bearing Piles (`steelsnakes.US.piles`)
- **HPPile** - HP bearing piles

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

##### Pipes & Hollow Sections (`steelsnakes.US.pipes`, `steelsnakes.US.hollow`)
- **Pipe** - Standard steel pipes
- **HSS** - Hollow structural sections

**Dependencies:**
- steelsnakes.base.sections
- steelsnakes.US.factory

#### Design Checks (`steelsnakes.US.checks`)

##### LRFD (`steelsnakes.US.checks.lrfd`)
**Status:** In development
**Purpose:** AISC 360 LRFD design checks

**Dependencies:**
- steelsnakes.base.checks
- steelsnakes.base.sections

##### Classification (`steelsnakes.US.checks.classification`)
**Status:** In development
**Purpose:** AISC 360 B4.1 section classification (compact, noncompact, slender)

**Dependencies:**
- steelsnakes.base.checks

#### Database & Factory
**Implementation:** US-specific with EDI nomenclature support

**Dependencies:**
- steelsnakes.base.database
- steelsnakes.base.factory
- JSON data in `steelsnakes.US.data/`

---

### 🇺🇸 US_Metric Module (`steelsnakes.US_Metric`)

**Status:** ⚠️ Partially implemented

**Purpose:** US sections with metric units for international projects

**Structure:** Mirrors US module but with metric conversions

**Dependencies:**
- steelsnakes.base modules
- **numpy** for unit conversions

---

### 🇮🇳 IN Module (`steelsnakes.IN`)

**Status:** 🚧 In development

**Data Source:** IS 800:2007

#### Planned Section Types
- Beams (`steelsnakes.IN.beams`)
- Columns (`steelsnakes.IN.columns`)
- Channels (`steelsnakes.IN.channels`)
- Angles (`steelsnakes.IN.angles`)
- Tees (`steelsnakes.IN.tees`)
- Bearing Piles (`steelsnakes.IN.bearing_piles`)

#### Design Checks
**Planned:** IS 800:2007 design checks

**Dependencies:**
- All base modules
- Potentially **sectionproperties** package for property calculations

---

### 🇦🇺 AU / 🇳🇿 NZ Module (`steelsnakes.AU`)

**Status:** 🚧 Preliminary

**Data Source:** To be determined (limited availability)

#### Current Implementation
- Basic section structure (`steelsnakes.AU.sections`)
- ULS checks placeholder (`steelsnakes.AU.checks.uls`)

**Note:** Comprehensive data scraping from web sources proved insufficient; seeking alternative data sources

**Dependencies:**
- steelsnakes.base modules

---

## Analysis & Design Checks

### Analysis Engine (`steelsnakes.engine.analysis`)

**Status:** 🚧 Early development

**Purpose:** Structural analysis capabilities

**Planned Features:**
- Member analysis
- Frame analysis
- Load combinations
- Deflection calculations
- Stability analysis

**Dependencies:**
- steelsnakes.base modules
- **numpy** for matrix operations
- Regional check modules

---

## CLI and Tooling

### Command Line Interface (`steelsnakes.cli`)

**Purpose:** CLI tools for section search and property display

**Features:**
- Search sections by designation
- List available sections by type
- Display section properties
- Multi-region support with auto-discovery

**Commands:**
```bash
steelsnakes search "457x191x67" --region UK
steelsnakes list --type UB --region UK --limit 20
```

**Dependencies:**
- Python Standard Library: `argparse`, `sys`, `importlib`, `pathlib`
- Regional database and factory modules

**Region Discovery:**
- Automatic detection of available regions
- Checks for `database.py` and `create_section` function
- Dynamic module import

---

### Main Demo (`steelsnakes.main`)

**Purpose:** Basic demonstration script

**Usage:**
```python
python src/steelsnakes/main.py
```

**Dependencies:**
- steelsnakes.UK.universal.UB
- steelsnakes.UK.angles.EqualAngle

---

## Feature Dependency Matrix

### Dependency Levels

#### Level 0: Python Standard Library
All modules depend on Python 3.11+ standard library

#### Level 1: External Packages (Foundation)
```
pydantic ≥2.11.7
  └─ Used by: base.checks, all section classes for validation
  
sqlalchemy ≥2.0.43
  └─ Used by: base.database (optional SQLite support)
  
numpy ≥2.3.2
  └─ Used by: engine.analysis, US_Metric conversions
```

#### Level 2: Base System
```
steelsnakes.base.sections
  ├─ Depends on: Python stdlib
  └─ Used by: ALL section implementations, ALL factories
  
steelsnakes.base.database
  ├─ Depends on: base.sections, sqlalchemy (optional)
  └─ Used by: ALL regional databases
  
steelsnakes.base.factory
  ├─ Depends on: base.sections, base.database, base.exceptions
  └─ Used by: ALL regional factories
  
steelsnakes.base.checks
  ├─ Depends on: pydantic
  └─ Used by: ALL regional check modules
  
steelsnakes.base.connectors
  ├─ Depends on: Python stdlib
  └─ Used by: connector implementations (pending)
  
steelsnakes.base.exceptions
  ├─ Depends on: Python stdlib
  └─ Used by: base.factory, all factories
```

#### Level 3: Regional Databases
```
steelsnakes.UK.database
  ├─ Depends on: base.database, base.sections
  └─ Provides: UK section data access
  
steelsnakes.EU.database
  ├─ Depends on: base.database, base.sections
  └─ Provides: EU section data access
  
steelsnakes.US.database
  ├─ Depends on: base.database, base.sections
  └─ Provides: US section data access
  
steelsnakes.US_Metric.database
  ├─ Depends on: base.database, base.sections, numpy
  └─ Provides: US metric section data access
```

#### Level 4: Regional Section Classes
```
steelsnakes.UK.universal
  ├─ Depends on: base.sections, UK.factory
  └─ Provides: UB, UC, UBP classes
  
steelsnakes.UK.channels
  ├─ Depends on: base.sections, UK.factory
  └─ Provides: PFC class
  
steelsnakes.UK.angles
  ├─ Depends on: base.sections, UK.factory
  └─ Provides: EqualAngle, UnequalAngle, B2B variants
  
steelsnakes.UK.hf_hollow
  ├─ Depends on: base.sections, UK.factory
  └─ Provides: HFCHS, HFRHS, HFSHS, HFEHS
  
steelsnakes.UK.cf_hollow
  ├─ Depends on: base.sections, UK.factory
  └─ Provides: CFCHS, CFRHS, CFSHS
  
[Similar structure for EU, US, US_Metric regions]
```

#### Level 5: Regional Factories
```
steelsnakes.UK.factory
  ├─ Depends on: base.factory, UK.database, ALL UK section classes
  └─ Provides: UKSectionFactory, convenience functions (UB, UC, etc.)
  
steelsnakes.EU.factory
  ├─ Depends on: base.factory, EU.database, ALL EU section classes
  └─ Provides: EUSectionFactory, convenience functions
  
steelsnakes.US.factory
  ├─ Depends on: base.factory, US.database, ALL US section classes
  └─ Provides: USSectionFactory, convenience functions
  
steelsnakes.US_Metric.factory
  ├─ Depends on: base.factory, US_Metric.database, section classes
  └─ Provides: USMetricSectionFactory
```

#### Level 6: Regional Design Checks
```
steelsnakes.UK.checks.uls
  ├─ Depends on: base.checks, base.sections
  └─ Provides: UK/EN 1993 ULS checks
  
steelsnakes.UK.checks.classification
  ├─ Depends on: base.checks
  └─ Provides: EN 1993-1-1 Table 5.2 classification
  
steelsnakes.UK.checks.stability
  ├─ Depends on: base.checks, base.sections
  └─ Provides: Member stability checks
  
steelsnakes.US.checks.lrfd
  ├─ Depends on: base.checks, base.sections
  └─ Provides: AISC 360 LRFD checks
  
steelsnakes.US.checks.classification
  ├─ Depends on: base.checks
  └─ Provides: AISC 360 B4.1 classification
  
[Similar for EU, AU, IN]
```

#### Level 7: Analysis Engine
```
steelsnakes.engine.analysis
  ├─ Depends on: base modules, regional sections, numpy
  └─ Provides: Structural analysis capabilities
```

#### Level 8: User Interface
```
steelsnakes.cli
  ├─ Depends on: ALL regional databases, ALL regional factories
  └─ Provides: Command-line interface
  
steelsnakes.main
  ├─ Depends on: UK.universal, UK.angles
  └─ Provides: Demo script
```

---

## Development Dependencies

### Testing
```
pytest ≥8.4.1
  └─ Used by: All test modules
  
pytest-cov ≥6.2.1
  ├─ Depends on: pytest, coverage
  └─ Provides: Coverage reporting for pytest
  
coverage 7.10.0
  └─ Used by: pytest-cov for coverage measurement
```

### Documentation
```
mkdocs ≥1.6.1
  └─ Core documentation generator
  
mkdocs-shadcn 0.9.3
  ├─ Depends on: mkdocs
  └─ Provides: Modern documentation theme
  
mkdocstrings[python] ≥0.30.0
  ├─ Depends on: mkdocs
  └─ Provides: API documentation from docstrings
  
pymdown-extensions ≥10.16.1
  ├─ Depends on: mkdocs
  └─ Provides: Enhanced markdown capabilities
```

### Code Quality
```
ruff (optional, install separately)
  └─ Provides: Fast linting and formatting
  
Configuration in pyproject.toml:
  - Ignores: F401, F841, E741 (see pyproject.toml for details)
```

---

## Cross-Cutting Dependencies

### JSON Data Files
Each region maintains JSON files with section properties:
```
steelsnakes/UK/data/*.json
steelsnakes/EU/data/*.json
steelsnakes/US/data/*.json
steelsnakes/US_Metric/data/*.json
steelsnakes/IN/data/*.json
steelsnakes/AU/data/*.json
```

**Format:** `{section_type}.json`
- Example: `UB.json`, `IPE.json`, `W.json`

**Structure:**
```json
{
  "designation": {
    "property1": value1,
    "property2": value2,
    ...
  }
}
```

---

## Build System

### Build Backend
```
uv_build ≥0.8.6, <0.9.0
  └─ Modern Python build backend (replaces setuptools)
```

### Installation Modes

#### Standard Installation (Editable)
```bash
pip install -e .
```
**Installs:**
- Core package
- All runtime dependencies (pydantic, sqlalchemy, numpy)
- All dev dependencies (pytest, coverage, mkdocs, etc.)

#### PYTHONPATH Mode (Network-restricted)
```bash
export PYTHONPATH=src
python -c "import steelsnakes; print('OK')"
```
**Use when:**
- Network access is restricted
- No installation of external packages possible
- Only local code execution needed

---

## Future Dependencies (Planned)

### Optional Features (Not Yet Implemented)
```python
# [project.optional-dependencies]
# extras = [
#     "streamlit",      # UI using Streamlit
#     "fastapi",        # Web API
#     "typer",          # Enhanced CLI
#     "sqlmodel",       # FastAPI's SQL integration
#     "pysqlite3-binary" # Optimized SQLite
# ]
```

### Additional Planned Dependencies
- **sectionproperties** - Section property calculations (for IN module)
- **pint** or **forallpeople** - Unit conversions and handling
- **Go binaries** - Performance-critical operations (experimental)

---

## Dependency Constraints & Compatibility

### Python Version
- **Minimum:** Python 3.11
- **Tested:** Python 3.12
- **Reason:** Uses modern type hints and dataclass features

### Key Version Constraints
- **pydantic** ≥2.11 - Requires Pydantic v2 (breaking changes from v1)
- **sqlalchemy** ≥2.0 - Uses modern SQLAlchemy API
- **numpy** ≥2.3 - Latest stable with Python 3.11+ support

### Platform Support
- **OS:** Cross-platform (Linux, macOS, Windows)
- **Architecture:** Any Python-supported architecture

---

## Installation Summary

### Minimal Installation (Runtime Only)
```bash
pip install steelsnakes
```
**Installs:** pydantic, sqlalchemy, numpy, mkdocs, mkdocstrings, coverage, pytest

### Development Installation
```bash
git clone https://github.com/waynemaranga/steelsnakes
cd steelsnakes
pip install -e .
pip install ruff  # Optional: for linting
```

### Documentation Build
```bash
mkdocs build  # or mkdocs serve
```
**Requires:** mkdocs, mkdocs-shadcn, mkdocstrings, pymdown-extensions (installed with package)

---

## Testing Dependencies

### Running Tests
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov=src/steelsnakes  # With coverage
```

**With PYTHONPATH:**
```bash
PYTHONPATH=src pytest
```

### Test Structure
```
tests/
  ├─ test_base/          # Base system tests
  ├─ test_UK/            # UK module tests
  ├─ test_EU/            # EU module tests
  ├─ test_US/            # US module tests
  └─ ...                 # Other regional tests
```

---

## Summary of Key Dependencies

### Critical Path (Must Have)
1. **Python 3.11+** - Language runtime
2. **pydantic ≥2.11.7** - Data validation
3. **Base System** - Foundation for all features
4. **Regional Database** - Section data access
5. **Regional Factory** - Section instantiation

### Optional but Recommended
- **sqlalchemy** - For SQLite optimization (experimental)
- **numpy** - For analysis and metric conversions
- **pytest** - For testing
- **mkdocs** - For documentation
- **ruff** - For code quality

### Future Enhancements
- **streamlit/fastapi** - GUI/Web interface
- **typer** - Enhanced CLI
- **sectionproperties** - Advanced calculations
- **pint/forallpeople** - Unit handling
- **Go binaries** - Performance optimization

---

## Notes on Architecture

### Design Principles
1. **Separation of Concerns:** Base system separated from regional implementations
2. **Extensibility:** Easy to add new regions and section types
3. **Type Safety:** Extensive use of type hints and Pydantic validation
4. **Data-Driven:** Section properties in JSON for easy updates
5. **Factory Pattern:** Centralized section creation with intelligent error handling
6. **ABC Pattern:** Clear contracts via abstract base classes

### Module Independence
- Base modules have minimal dependencies
- Regional modules are independent of each other
- Check modules depend only on base and relevant sections
- CLI discovers regions dynamically

### Performance Considerations
- In-memory caching of section databases
- Optional SQLite for large datasets
- Lazy loading of section types
- Fuzzy matching uses efficient difflib algorithm

---

## Version History

- **0.0.1-alpha-7** (Current) - Latest alpha release
- **0.0.1-alpha-6** - Previous alpha
- Development status: Alpha

---

## References

### Data Sources
- **UK:** Steel Construction Institute (SCI) Blue Book
- **EU:** ArcelorMittal Orange Book
- **US:** AISC Steel Construction Manual v16
- **IN:** IS 800:2007
- **AU/NZ:** Various sources (incomplete)

### Standards
- **EN 1993-1-1:2005** - Eurocode 3
- **BS EN 1993 + UK NA** - UK National Annex
- **BS 5950-1** - British Standard (legacy)
- **AISC 360-22** - US steel construction
- **IS 800:2007** - Indian steel code
- **AS 4100** - Australian steel standard

---

**End of Dependency Tree Documentation**

For more information:
- **GitHub:** https://github.com/waynemaranga/steelsnakes
- **Documentation:** https://steelsnakes.readthedocs.io/
- **Issues:** https://github.com/waynemaranga/steelsnakes/issues
