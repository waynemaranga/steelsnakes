# API Reference

The reference is split into the shared base modules that power all regions, followed by the region-specific packages that tailor steel sections, databases, factories, and checks to each code.

## Base modules

1. `sections` — Provides the `SectionType` enumerations plus the abstract `BaseSection`. Every concrete section class inherits the helpers (`get_properties`, `list_properties`, `from_dictionary`) so consumers can enumerate attributes consistently.
2. `database` — The new `SectionDatabase` page (`02-database.md`) explains how JSON datasets are auto-discovered, cached, and exposed through fuzzy search, comparison filtering, and similarity helpers for resilient designation lookups.
3. `factory` — `SectionFactory` maps the cached data to region-aware section classes, auto-loading UK/EU/US modules and warning when a region does not yet have a concrete implementation.
4. `checks` — Limit-state helpers live here so they can be shared by multiple regions; current helpers cover ULS/stability (UK) and LRFD/classification (US), while other regions can plug in their variants.

## Regions

1. `UK`
2. `EU`
3. `US` and `US_Metric`
4. `IN`

Each region still provides its own `sections`, `database`, `factory`, and `checks` modules. Check the corresponding regional README files (linked from the guide pages) to see exactly which standards and section profiles are currently packaged.
