# EU Serviceability Checks (EN 1993-1-1)

This page documents the serviceability limit state checks in `steelsnakes.EU.checks.sls`, covering EN 1993-1-1:2005+A1:2014
Section 7. It covers deflections (7.2.1, 7.2.2), vibration (7.2.3) and elastic stresses where plastic global analysis is used
for the ULS (7.1(4)). It also includes the EN 1990 combinations of actions that these checks need.

As with the [EU Member Checks](07-eu-member-checks.md), every check returns a Pydantic result with the intermediate values, a
`utilisation` and a `Reference`. Each result also carries a `limit_state`: `VERTICAL_DEFLECTION`, `HORIZONTAL_DEFLECTION`,
`VIBRATION` or `SERVICEABILITY_STRESS`.

```{warning} Units
    The checks work in N, mm and N/mm². Line loads are in N/mm, which is the same number as kN/m. Deflections are in mm,
    masses per unit length in kg/m and frequencies in Hz.
    Section properties are read from the tables and converted, as in the ULS checks.
  ```

```{note} Where the limits come from
    EN 1993-1-1 sets no serviceability limits. Clause 7.2 refers to EN 1990 Annex A1.4, and the limits are to be
    specified for each project and agreed with the client, or given by the National Annex.
    The default deflection limits here are the suggested values of the UK NA to BS EN 1993-1-1. The UK NA applies
    them to the deflection under the characteristic combination of the variable actions, without the permanent
    actions. Pass your own span or height ratios where your project or National Annex differs.
  ```

## Module map

| Clause | Check | What it covers |
|---|---|---|
| EN 1990 6.5.3, Table A1.1 | `sls_combination()`, `psi_factors()` | Characteristic, frequent and quasi-permanent combinations (Eq. 6.14b to 6.16b) |
| 7.1(4) | `check_serviceability_stresses()` | Elastic stresses under the SLS combination, to EN 1993-2 7.3 (Eq. 7.1 to 7.3) |
| 7.2.1 | `check_vertical_deflection()` | w_1, w_2, w_3, w_c, w_tot and w_max of EN 1990 Figure A1.1 against L/n |
| 7.2.1 | `check_beam_deflection()`, `beam_deflection()` | Deflection of single-span beams and cantilevers from their loads |
| 7.2.2 | `check_horizontal_deflection()` | Storey drifts u_i/H_i and the overall u/H of EN 1990 Figure A1.2 |
| 7.2.3 | `check_vibration()`, `natural_frequency()` | First natural frequency of a floor beam against f_min (EN 1990 A1.4.4) |

## Deflection limits

| Key | Limit | Applies to |
|---|---|---|
| `VERTICAL_DEFLECTION_LIMITS["cantilever"]` | length/180 | Cantilevers |
| `VERTICAL_DEFLECTION_LIMITS["brittle_finish"]` | span/360 | Beams carrying plaster or other brittle finish |
| `VERTICAL_DEFLECTION_LIMITS["beam"]` | span/200 | Other beams, except purlins and sheeting rails |
| `VERTICAL_DEFLECTION_LIMITS["purlin"]` | to suit the cladding | Purlins and sheeting rails; pass `span_ratio_w_3` |
| `HORIZONTAL_DEFLECTION_LIMITS["single_storey"]` | height/300 | Tops of columns in single storey buildings, except portal frames |
| `HORIZONTAL_DEFLECTION_LIMITS["portal_frame"]` | to suit the cladding | Columns in portal frames without crane runways; pass `height_ratio_u_i` |
| `HORIZONTAL_DEFLECTION_LIMITS["multi_storey"]` | storey height/300 | Each storey of a building with more than one storey |

## Deflections

```python
from steelsnakes.EU import IPE, sls_combination, check_beam_deflection, check_horizontal_deflection

beam = IPE("IPE-300")
Q_k = sls_combination(variable=[(10.0, "B")])  # characteristic combination of the variable actions, kN/m
result = check_beam_deflection(beam, L=6000.0, G_k=5.0, Q_k=Q_k, member="brittle_finish", self_weight=True)
print(result.w_3, result.w_3_limit, result.utilisation.utilisation)  # 9.61 mm, 16.67 mm (L/360), 0.577
print(result.w_1, result.w_max)  # 5.20 mm (G_k and self weight), 14.82 mm

frame = check_horizontal_deflection([8.0, 9.5, 7.0], [3500.0, 3500.0, 3500.0], height_ratio_u=500.0)
print(frame.utilisations)  # {"u_1": 0.686, "u_2": 0.814, "u_3": 0.6, "u": 1.167}; H/500 governs and FAILS
```

- **Figure A1.1.** w_tot = w_1 + w_2 + w_3, and w_max = w_tot − w_c after the precamber. `check_vertical_deflection()`
  limits w_3 by `member` or `span_ratio_w_3`. It also limits w_max when you pass `span_ratio_w_max`, as some National
  Annexes require.
- **From loads.** `check_beam_deflection()` works out w_1 from `G_k` (and the self weight, with `self_weight=True`) and
  w_3 from `Q_k`. Supports are `simply_supported`, `both_ends_fixed`, `one_end_fixed` (propped) and `cantilever`, under
  `uniform` or `concentrated` loading. A concentrated load is at mid-span, or at the tip of a cantilever. For other
  cases, use the deflections from your analysis in `check_vertical_deflection()`.
- **Several variable actions.** Combine them with `sls_combination()` first. With a linear analysis, the deflections
  from each load case combine the same way as the loads.

## Vibration

```python
from steelsnakes.EU import IPE, check_vibration

result = check_vibration(IPE("IPE-300"), L=6000.0, w=5.0)  # 5 kN/m of floor, plus the beam's 42.2 kg/m
print(result.m, result.f, result.utilisation.utilisation)  # 551.9 kg/m, 7.78 Hz, 0.386 (f_min = 3 Hz)
```

EN 1990 A1.4.4(4) keeps the natural frequency above a value agreed with the client. The default `F_MIN` is 3 Hz, the
minimum for floors on which people walk in the former ENV 1993-1-1. Floors for rhythmic activity, such as gymnasia,
used 5 Hz there. `natural_frequency()` is the Euler-Bernoulli value for a uniform beam under uniform mass.
`natural_frequency_from_deflection()` gives the equivalent 18/√δ. Where f < f_min, EN 1990 A1.4.4(5) calls for a
refined analysis of the dynamic response, such as SCI P354 in the UK; the result then carries a note.

## Stresses at the serviceability limit state

```python
from steelsnakes.EU import IPE, check_serviceability_stresses

result = check_serviceability_stresses(IPE("IPE-300"), 355.0, M_y_Ed_ser=100e6, V_z_Ed_ser=100e3)
print(result.sigma_Ed_ser, result.tau_Ed_ser, result.utilisation.utilisation)  # 179.5, 50.6 N/mm², 0.563 (Eq. 7.3)
```

7.1(4) asks for the effects of plastic redistribution at the SLS to be considered where plastic global analysis is used
for the ULS. The check keeps the SLS stresses elastic, using the limits of EN 1993-2 7.3 with γM,ser = 1.00:
σ ≤ fy/γM,ser, τ ≤ fy/(√3·γM,ser), and √(σ² + 3τ²) ≤ fy/γM,ser.

- σ adds the elastic stresses at the most stressed fibre.
- τ is V/A_w on the web of I-sections and channels loaded parallel to the web. For other cases it is V/A_v.
- Eq. 7.3 combines σ and τ as if they act at the same point, which is conservative.

## Validation

The tests check the following against independent hand calculations:

- The deflection of an IPE 300 over 6 m (5wL⁴/384EI = 9.61 mm under 10 kN/m).
- The propped-cantilever coefficients, sampled from the elastic curves.
- That the natural frequency matches (π/2)√(5g/384δ) = 17.75/√δ for the same beam.
- The σ, τ and Eq. 7.3 stresses of an IPE 300 and an RHS.

## API objects

::: steelsnakes.EU.checks.sls
