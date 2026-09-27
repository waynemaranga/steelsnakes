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
- `ElementStressDistribution`
- `StressPattern`

These are exported from `steelsnakes.EU.checks` and also from `steelsnakes.EU`.

`stress_pattern` accepts any of:

- a simple string such as `"compression"`, `"bending-major-axis"` or `"bending-minor-axis"`
- a `StressPattern` enum value: `COMPRESSION`, `MAJOR_AXIS_BENDING`, `MINOR_AXIS_BENDING` or `COMBINED`
- an `ElementStressDistribution` value, which applies that stress to every element

For hollow sections, the axis decides which walls act as webs (in bending) and which act as flanges (in compression).
An axis-free `"bending"` is major-axis bending: the h walls are in bending and the b walls in compression, as Table 5.2
Sheet 1 requires.

Outstand flanges of rolled sections are measured from the toe of the root radius, as on Table 5.2 Sheet 2, and as the
tabulated cf/tf: c = (b − tw − 2r)/2 for I- and H-sections and c = b − tw − r for parallel flange channels. Angles in
bending follow Sheet 3's "refer also to outstand flanges": each full leg is checked as an outstand in compression.

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

- the web is checked as an internal part in bending, c = d
- the flange is checked as an outstand part in compression, c = (b − tw − 2r)/2

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
    ElementStressDistribution,
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
            stress=ElementStressDistribution.COMBINED,
            alpha=0.70,
        ),
        ElementInput(
            name="flange",
            kind="outstand",
            c_mm=74.8,
            t_mm=10.9,
            stress=ElementStressDistribution.COMPRESSION,
        ),
    ],
)

print(result.section_class)
```

Use `alpha` for the Class 1 / 2 combined internal check.

Add `psi` when the Class 3 internal limit is needed.

### Outstands In Bending And Compression (Table 5.2 Sheet 2/3)

For outstand flanges, set `tip` to say whether the free edge is in compression or tension:

| | Class 1 | Class 2 | Class 3 |
|---|---|---|---|
| tip in compression | \(9\varepsilon/\alpha\) | \(10\varepsilon/\alpha\) | \(21\varepsilon\sqrt{k_\sigma}\) |
| tip in tension | \(9\varepsilon/(\alpha\sqrt{\alpha})\) | \(10\varepsilon/(\alpha\sqrt{\alpha})\) | \(21\varepsilon\sqrt{k_\sigma}\) |

\(k_\sigma\) is taken from EN 1993-1-5 Table 4.2 using `psi` (`outstand_buckling_factor(psi, tip)`). Without `psi`, the
Class 3 limit falls back to \(14\varepsilon\). Without `alpha`, the uniform-compression limits are used, which is
conservative.

```python
from steelsnakes.EU import ElementInput, ElementStressDistribution, classify_element

flange = ElementInput(
    name="flange", kind="outstand", c_mm=80.0, t_mm=5.0,
    stress=ElementStressDistribution.COMBINED, alpha=0.6, psi=-0.5, tip="tension",
)
print(classify_element(flange, fy_mpa=355.0).section_class)  # CLASS_2; k_sigma = 8.475
```

### Clauses 5.5.2(9) And 5.5.2(11)

- **5.5.2(9).** Set `sigma_com_ed_mpa` on an element to its maximum design compressive stress. A Class 4 element is
  then re-checked against the Class 3 limit with \(\varepsilon\) increased by
  \(\sqrt{(f_y/\gamma_{M0})/\sigma_{com,Ed}}\). The result carries a note that this does not apply to member buckling
  checks (5.5.2(10)).
- **5.5.2(11).** When a Class 3 web governs and the flanges are Class 1 or 2, `result.notes` records that the section
  may be treated as Class 2 with an effective web (6.2.2.4).

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
    stress=ElementStressDistribution.COMBINED,
    alpha=0.70,
)

print(payload.model_dump())
```

## Current Scope

Currently implemented in the lean preset API:

- hot-rolled I/H sections
- channels
- angles in compression (Sheet 3) and in bending (legs as outstands, Sheet 2)

For more specific stress distributions, use `custom_elements`.

## Recommendation

Use the API in this order:

1. `classify_section(...)` for ordinary section checks
2. `stress_pattern=StressPattern.MAJOR_AXIS_BENDING` for common beam checks
3. `custom_elements=[...]` when you need direct control of `stress`, `alpha`, or `psi`
