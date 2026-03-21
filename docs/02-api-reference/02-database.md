# Section Database & Factory

This page captures the shared infrastructure that keeps all regions inside `$steelsnakes$` synchronized: the data caches (`SectionDatabase`) and the wiring layer (`SectionFactory`) that turns cached rows into concrete section objects.

## SectionDatabase

1. **Discovery & caching.** When you instantiate `SectionDatabase`, it auto-discovers the correct `data/<REGION>/` directory via several fallback paths, optionally respects an injected `data_directory`, and loads every supported `SectionType` into a dictionary cache. Metadata like `_section_type` and `_region` are added to every entry so downstream tools understand the source.
2. **Fallback SQLite support.** The constructor accepts `use_sqlite=True`, in which case `_load_section_type` can attempt to read from an SQLite table named after each `SectionType` when JSON files are absent. Error handling already logs missing tables and malformed rows without breaking the entire initialization.
3. **Resilient lookup helpers.** `find_section` first tries an exact match, then `_fuzzy_find_section`:
   - Exact matches ignore case and normalize separators (` `, `-`, `_`, `×`).
   - Difflib-based similarity matching provides a controlled suggestion (cutoff 0.8) before falling back to `None`.
   - `get_similar_sections` can be called independently with `n` suggestions across all loaded types.
4. **Criteria-based search.** `search_sections(section_type, prop__gt=100, prop__eq="W")` filters the cached dict via comparison operators (`gt`, `lt`, `gte`, `lte`, `eq`, `ne`) and exact matches, so you can quickly find all sections that meet size thresholds.

<!-- prettier-ignore-start -->
!!! warning "Note"
    The current database is JSON-first and still mirrors early datasets, so not every region/type has fully verified values. Validate against the source CSV/JSON, especially when drafting code that depends on exact masses or moments of inertia.
<!-- prettier-ignore-end -->

## SectionFactory

`SectionFactory` bridges `SectionDatabase` with the concrete section classes.

1. **Automatic class loading.** If no `section_classes` mapping is provided, the factory inspects `database.region` and imports the relevant modules (`UK`, `EU`, `US`, `AU`, `NZ` are wired in), while gracefully logging if a region lacks exports.
2. **Region-aware wiring.** Each helper (e.g., `_load_UK_classes`) imports the region's section definitions (beams, channels, angles, hollow sections) and maps them to `SectionType` members. This keeps the factory thin while letting each region evolve independently.
3. **Extensibility.** Custom section classes or alternative databases can simply pass their own `section_classes` dict when instantiating the factory, so testing helpers can swap in fake sections without touching the auto-loader.

Pair any factory instance with the database you already created to request a section instance:

```python
from steelsnakes.base.database import SectionDatabase
from steelsnakes.base.factory import SectionFactory
from steelsnakes.base.sections import SectionType

db = SectionDatabase(region="UK")
factory = SectionFactory(database=db)
beam = factory.create_section("457x191x67", section_type=SectionType.UB)
```

The next page in this reference dives into the region-specific APIs for UK, EU, US, and additional locales.
