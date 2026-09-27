# BS 5950 Classification

This page documents BS 5950-1:2000 Section 3.5, classification of cross-sections, in `steelsnakes.BS`.

BS 5950 has been withdrawn, but it is still widely used. The module runs on the same UK section objects as the
Eurocode checks and re-exports their constructors, so both codes can be checked from one place:

```python
from steelsnakes.BS import UB, classify_section

result = classify_section(UB("457x191x67"), steel_grade="S275", stress_pattern="bending-major-axis")
print(result.section_class, result.class_name)  # SectionClass.CLASS_1 plastic
```

## What is implemented

| Clause / table | Function or object |
|---|---|
| Table 9: design strength py | `design_strength(t, steel_grade)` |
| Table 11 note b: ε = (275/py)^0.5 | `epsilon(py)` |
| 3.5.1, Figure 5: element dimensions | `classify_section()`, `classify_section_from_dict()` adapters |
| 3.5.2: classes 1 plastic, 2 compact, 3 semi-compact, 4 slender | `SectionClass`, `CLASS_NAMES` |
| 3.5.3, Figure 6: compound flanges | `compound_flange_elements()` |
| Table 11: sections other than CHS and RHS | `ElementKind.OUTSTAND_FLANGE_ROLLED` … `ElementKind.TEE_STEM` |
| Table 12: CHS and RHS | `ElementKind.CHS`, `HF_RHS_*`, `CF_RHS_*` |
| 3.5.5, Figure 7: stress ratios r1, r2 | `stress_ratios()` |
| 3.5.6.1, 3.5.6.2: effective plastic modulus | `effective_plastic_modulus()`, `effective_plastic_modulus_i_section()` |
| Calculation sheet rows | `render_classification()` → `base.renders.CheckBlock` |

## Stress patterns

| `stress_pattern` | I/H sections | Channels | RHS/SHS | CHS |
|---|---|---|---|---|
| `"compression"` | flange outstand + web, axial compression | flange + channel web | both walls, axial compression | axial compression |
| `"bending-major-axis"` | flange + web with neutral axis at mid-depth | flange + channel web | flange (B side) + web (D side) | bending |
| `"bending-minor-axis"` | flange only; the web lies on the neutral axis | flange + channel web | walls swapped: flange (D side) + web (B side) | bending |
| `"combined"` | flange + web "generally", with r1 and r2 from `Fc_kN` | flange + channel web | flange + web "generally" | not allowed (3.5.1) |

Passing `Fc_kN` with major-axis bending moves the web to the "generally" row, because the neutral axis is no longer at
mid-depth.

## Behaviour worth knowing

- **Axial compression.** Tables 11 and 12 say "Not applicable" for classes 1 and 2 of webs, internal flanges, angles
  and CHS in axial compression. An element within the class 3 limit is reported as class 3 semi-compact, meaning
  *not slender*, and `result.notes` says so.
- **r2 default.** Webs in axial compression default to r2 = 1.0, i.e. Fc = Ag·pyw. That gives the 40ε floor, which is
  conservative. Pass `Fc_kN` to use the actual stress ratio. For example, UB 457x191x67 in S275 has d/t = 48 > 40ε,
  so it is slender in pure compression but plastic in bending.
- **py from Table 9.** When `py_mpa` is omitted, py comes from Table 9 using the thickest element, which for rolled
  sections is the flange.
- **Figure 5 dimensions.**
    - Rolled I/H outstand: b = B/2.
    - Rolled channel outstand: b = B.
    - RHS walls: b = B − 3t and d = D − 3t for hot finished, B − 5t and D − 5t for cold formed (Table 12 note a).
    - Back-to-back double angles: the longer leg is taken as the outstand, which is conservative.
- **Effective plastic modulus.** Seff follows 3.5.6.2 for class 3 UB/UC/UBP. For other sections it returns Z, which
  3.5.6.1 permits. The RHS and CHS formulas of 3.5.6.3 and 3.5.6.4 are not implemented.
- **Elliptical hollow sections.** HFEHS are not covered by Tables 11 and 12 and raise `NotImplementedError`.

## Examples

### Explicit elements

```python
from steelsnakes.BS import ElementInput, ElementKind, ElementStressDistribution, classify_element

web = ElementInput(
    name="web",
    kind=ElementKind.WEB,
    stress=ElementStressDistribution.COMBINED,
    b_mm=407.6,
    t_mm=8.5,
    r1=0.525,
    r2=0.213,
)
print(classify_element(web, py_mpa=275.0).class_1_limit)  # 80ε/(1 + r1) = 52.5
```

### Stress ratios and effective modulus

```python
from steelsnakes.BS import UC, effective_plastic_modulus, stress_ratios

ratios = stress_ratios(Fc_kN=500.0, d_mm=407.6, t_mm=8.5, pyw_mpa=275.0, Ag_cm2=85.5)
seff = effective_plastic_modulus(UC("152x152x23"), steel_grade="S355")  # semi-compact flange
print(ratios.r1, ratios.r2, seff.S_eff)  # 0.525, 0.213, 170.5 cm³
```

### Dictionary input in BS notation

```python
from steelsnakes.base.sections import SectionType
from steelsnakes.BS import classify_section_from_dict

result = classify_section_from_dict(
    SectionType.UC,
    {"B": 476.0, "T": 140.0, "t": 100.0, "d": 290.0, "A": 1650.0},
    steel_grade="S275",
    stress_pattern="bending",
)
```

!!! warning "Design strength of S460"
    The S460 row of Table 9 is taken as 460/440/430/410/400 N/mm² for t ≤ 16/40/63/80/100 mm. The earlier draft in
    `BS/checks/classification.py.md` had 445 and 415 for the 40 mm and 80 mm steps. Check these against your copy of
    BS 5950-1:2000 before relying on S460 results. The draft also used the superseded BS 5950-1:1990 Table 7 limits
    (8.5ε, 9.5ε, 15ε and 79ε, 98ε, 120ε).

## API objects

::: steelsnakes.BS.checks.classification
