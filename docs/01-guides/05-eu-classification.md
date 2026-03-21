# EU Classification

This guide documents the current Eurocode classification API in `steelsnakes.EU`.

## Design Goal

The implementation keeps a simple split:

- Section modules provide geometry through `classification_elements()`
- The check module chooses the stress case and applies the EN 1993-1-1 Table 5.2 limits

This keeps the section classes lean while still allowing different limits for:

- pure compression
- bending
- combined bending and compression

## Public API

The main public entry points are:

- `classify_section()`
- `classify_section_from_dict()`
- `classify_internal_part()`
- `classify_outstand_flange()`
- `ElementInput`
- `ElementStressCase`
- `StressPattern`

These are exported from `steelsnakes.EU.checks` and also from `steelsnakes.EU`.

`stress_pattern` accepts either:

- a simple string such as `"compression"` or `"bending-major-axis"`
- a `StressPattern` enum value

## Common Usage

### 1. Section In Compression

```python
from steelsnakes.EU import IPE, classify_section

section = IPE("IPE-750x220")
result = classify_section(section=section, fy_mpa=355.0)

print(result.section_class)
print(result.governing_elements)
```

This is the default case.

### 2. Major-Axis Bending

```python
from steelsnakes.EU import IPE, StressPattern, classify_section

section = IPE("IPE-750x220")
result = classify_section(
    section=section,
    fy_mpa=355.0,
    stress_pattern="bending-major-axis",
)

for element in result.elements:
    print(element.name, element.stress, element.section_class)
```

For the current hot-rolled beam/channel convenience path:

- the web is checked as an internal part in bending
- the flange is checked as an outstand part in compression

If you prefer explicit enums, this is equivalent to:

```python
result = classify_section(
    section=section,
    fy_mpa=355.0,
    stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
)
```

## Explicit Combined Loading

For combined bending and compression, the lean API is explicit:

```python
from steelsnakes.EU import (
    ElementInput,
    ElementStressCase,
    classify_section,
)

result = classify_section(
    fy_mpa=275.0,
    custom_elements=[
        ElementInput(
            name="web",
            kind="internal",
            c_mm=360.4,
            t_mm=7.7,
            stress=ElementStressCase.COMBINED,
            alpha=0.70,
        ),
        ElementInput(
            name="flange",
            kind="outstand",
            c_mm=74.8,
            t_mm=10.9,
            stress=ElementStressCase.COMPRESSION,
        ),
    ],
)

print(result.section_class)
```

Use `alpha` for the Class 1 / 2 combined internal check.

Add `psi` when the Class 3 internal limit is needed.

## FastAPI / Pydantic Friendly Inputs

`ElementInput`, `ElementClassification`, and `ClassificationResult` are Pydantic models, so they are easy to:

- validate
- serialize
- return from APIs
- document in request and response schemas

Example payload shape:

```python
payload = ElementInput(
    name="web",
    kind="internal",
    c_mm=360.4,
    t_mm=7.7,
    stress=ElementStressCase.COMBINED,
    alpha=0.70,
)

print(payload.model_dump())
```

## Current Scope

Currently implemented in the lean preset API:

- hot-rolled I/H sections
- channels
- angles for compression-only section-level classification

For more specific stress distributions, use `custom_elements`.

## Recommendation

Use the API in this order:

1. `classify_section(...)` for ordinary section checks
2. `stress_pattern=StressPattern.MAJOR_AXIS_BENDING` for common beam checks
3. `custom_elements=[...]` when you need direct control of `stress`, `alpha`, or `psi`
