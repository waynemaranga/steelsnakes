# UK Classification

This page documents the current UK classification API in `steelsnakes.UK`.

## Design Goal

The UK module reuses the shared EC3 classification engine from `steelsnakes.EU` and adapts it through UK section families.

That keeps the backend formula logic centralized while still giving the UK package a complete public API.

## What Reuses Directly

The same EN 1993-1-1 Table 5.2 helpers are reused for:

- `UB`, `UC`, and `UBP`
- `PFC`
- equal and unequal angles
- back-to-back angle variants
- hot-finished `HFRHS`, `HFSHS`, and `HFCHS`
- cold-formed `CFRHS`, `CFSHS`, and `CFCHS` through the same shared engine, with explicit Class 4 exits

The UK package exports the same main helpers as the EU package:

- `classify_section()`
- `classify_section_from_dict()`
- `classify_circular_hollow()`
- `classify_internal_part()`
- `classify_outstand_flange()`
- `ElementInput`
- `ElementStressCase`
- `StressPattern`

These are available from both:

- `steelsnakes.UK.checks`
- `steelsnakes.UK`

## Common Usage

```python
from steelsnakes.UK import UB, StressPattern, classify_section

section = UB("457x191x67")
result = classify_section(
    section=section,
    fy_mpa=355.0,
    stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
)

print(result.section_class)
for element in result.elements:
    print(element.name, element.stress, element.section_class)
```

Hollow sections use the same public entry point:

```python
from steelsnakes.UK import HFRHS, classify_section

section = HFRHS("50x30x3.2")
result = classify_section(section=section, fy_mpa=355.0)

print(result.section_class)
```

## Scope Notes

The UK classification surface is intentionally aligned with the EU API, and now includes the following hollow families:

| Section family | Status | Notes |
|----------------|--------|-------|
| `HFRHS` | Supported | Table 5.2 Sheet 1; uses `cw_t` / `cf_t` |
| `HFSHS` | Supported | Table 5.2 Sheet 1; uses `c_t` |
| `HFCHS` | Supported | Table 5.2 Sheet 3; uses `d_t` and the `e^2 = 235 / fy` rule |
| `CFRHS` | Supported | Table 5.2 Sheet 1; Class 4 raises and points to `EN 1993-1-3` |
| `CFSHS` | Supported | Table 5.2 Sheet 1; Class 4 raises and points to `EN 1993-1-3` |
| `CFCHS` | Supported | Table 5.2 Sheet 3; Class 4 raises and points to `EN 1993-1-3` |
| `HFEHS` | Deferred | No EN 1993-1-1 Table 5.2 rule is implemented |

When you need full manual control, pass `custom_elements` to `classify_section(...)`.

## API Reference

::: steelsnakes.UK.checks.classification.StressPattern

::: steelsnakes.UK.checks.classification.ElementStressCase

::: steelsnakes.UK.checks.classification.ElementInput

::: steelsnakes.UK.checks.classification.ElementClassification

::: steelsnakes.UK.checks.classification.ClassificationResult

::: steelsnakes.UK.checks.classification.classify_circular_hollow

::: steelsnakes.UK.checks.classification.classify_element

::: steelsnakes.UK.checks.classification.classify_internal_part

::: steelsnakes.UK.checks.classification.classify_outstand_flange

::: steelsnakes.UK.checks.classification.classify_elements

::: steelsnakes.UK.checks.classification.classify_section

::: steelsnakes.UK.checks.classification.classify_section_from_dict
