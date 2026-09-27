# US Member Checks (AISC 360-22)

This page documents the LRFD member checks in `steelsnakes.US`, covering AISC 360-22 Chapters C to H and
Appendices 7 and 8.

Every check returns a Pydantic result carrying the governing limit state, the nominal and design strengths, the
intermediate values an engineer would write on a calculation sheet, and a `Reference` to the clause and equation.

!!! warning "Units"
    The `US` module works in kips, inches and ksi, as tabulated in the AISC Shapes Database v16.0.
    Moments are in kip-in. Divide by 12 for kip-ft.

## Module map

| Chapter | Module | Dispatcher | What it covers |
|---|---|---|---|
| C, App. 7, App. 8 | `steelsnakes.US.checks.stability` | – | Notional loads, τb, B1/B2, first-order method limits |
| D | `steelsnakes.US.checks.tension` | `tension()` | Yielding, rupture, net area, shear lag (Table D3.1), pins, eyebars |
| E | `steelsnakes.US.checks.compression` | `compression()` | FB, TB, FTB, single angles (E5), built-up members (E6), slender elements (E7) |
| F | `steelsnakes.US.checks.flexure` | `flexure()` | F2 to F13 per Table User Note F1.1 |
| G | `steelsnakes.US.checks.shear` | `shear()` | Webs, tension field action, stiffeners, HSS, angles, tees, minor axis |
| H | `steelsnakes.US.checks.combined` | – | H1 and H2 interaction, H3 torsion, H4 flange rupture |

The dispatchers read the section type and pick the applicable sections of each chapter:

```python
from steelsnakes.US import flexure
from steelsnakes.US.sections.beams import W_beam

result = flexure(section=W_beam("W18X50"), Fy=50.0, Lb=11.7 * 12, Cb=1.01)
print(result.limit_state, result.Mn)  # LATERAL_TORSIONAL_BUCKLING, ~4060 kip-in.; Design Example F.1-2B
```

## Tension: Chapter D

```python
from steelsnakes.US.checks.tension import calculate_net_area, shear_lag_factor
from steelsnakes.US import tension
from steelsnakes.US.sections.beams import W_beam

beam = W_beam("W8X21")
An = calculate_net_area(beam.A, beam.tf, hole_diameters=[13 / 16] * 4)
U = shear_lag_factor("case7", bf=beam.bf, d=beam.d, n=3, x_bar=0.831, l=9.0)  # the larger of Case 7 and Case 2
result = tension(section=beam, An=An, U=U, L=25 * 12)

print(result.limit_state, result.phi_t_Pn)  # TENSILE_RUPTURE, Design Example D.1
```

`shear_lag_factor()` implements every case of Table D3.1, as well as the D3 lower bound U ≥ A_connected/Ag for open
sections. `check_pin_connected_member()` covers D5 and `check_eyebar()` covers D6.

## Compression: Chapter E

```python
from steelsnakes.US import compression
from steelsnakes.US.sections.hollow import HSS_RCT

result = compression(section=HSS_RCT("HSS12X8X3/16"), Fy=50.0, L=24 * 12)
print(result.limit_state, result.Fn, result.Ae, result.phi_c_Pn)  # Design Example E.10
```

Per-axis lengths and factors (`Lx`, `Ly`, `Lz`, `Kx`, `Ky`, `Kz`), the E5 options for single angles, and the E6 inputs
for built-up members (`a`, `ri`, `connectors`) are all keyword arguments. `result.checks` holds every limit state
that was evaluated.

## Flexure: Chapter F

`flexure()` follows Table User Note F1.1: it classifies the flanges and web (Table B4.1b), then routes to F2 through
F13. Pass `axis="minor"` for minor-axis bending, and for single angles use `geometric_axis=True` and
`restrained_at_max_moment=True` as needed. `calculate_Cb()` implements Equation F1-1.

## Shear: Chapter G

`shear()` handles rolled and built-up I-shapes (G2.1, and tension field action per G2.2), channels, single angles and
tees (G3), rectangular and round HSS (G4, G5), and minor-axis shear (G6). `check_transverse_stiffener()` covers G2.3
and G2.4.

## Combined forces and torsion: Chapter H

```python
from steelsnakes.US import check_axial_flexure_interaction

check = check_axial_flexure_interaction(Pr=174.0, Pc=1080.0, Mrx=2304.0, Mcx=5904.0, Mry=811.2, Mcy=2016.0, axial="tension")
print(check.reference.equation, check.utilisation)  # H1-1b, 0.873; Design Example H.3
```

!!! note
    Required strengths must already include second-order effects (Chapter C). Chapter H applies no amplification.

## Stability: Chapter C and Appendices 7 and 8

The stability helpers turn frame-analysis output into the quantities Chapter C asks for. α is 1.0 for LRFD and 1.6
for ASD.

| Function | Clause | Equation |
|---|---|---|
| `notional_load(Yi, alpha, out_of_plumbness=1/500)` | C2.2b | \(N_i = 0.002\alpha Y_i\) (C2-1) |
| `notional_loads_required_with_lateral_loads(drift_ratio)` | C2.2b(d) | only when \(\Delta_{2nd}/\Delta_{1st} > 1.7\) |
| `stiffness_reduction_tau_b(Pr, Pns, alpha)` | C2.3(b) | \(\tau_b = 4(\alpha P_r/P_{ns})[1-\alpha P_r/P_{ns}]\) (C2-2b) |
| `reduced_stiffness(EI, EA, ...)` | C2.3(a) | \(EI^* = 0.8\tau_b EI\), \(EA^* = 0.8EA\) |
| `tau_b_notional_load(Yi, alpha)` | C2.3(c) | \(0.001\alpha Y_i\) in lieu of \(\tau_b < 1\) |
| `first_order_additional_lateral_load(Yi, delta_over_L, alpha)` | App. 7.3.2 | \(N_i = 2.1\alpha(\Delta/L)Y_i \ge 0.0042Y_i\) (A-7-3) |
| `check_first_order_method(...)` | App. 7.3.1 | A-7-1, A-7-2, drift ratio ≤ 1.5 |
| `calculate_Cm(M1, M2, curvature)` | App. 8.1.2 | \(C_m = 0.6 - 0.4(M_1/M_2)\) (A-8-4) |
| `calculate_Pe1(I, Lc1, tau_b, direct_analysis)` | App. 8.1.2 | \(P_{e1} = \pi^2EI^*/L_{c1}^2\) (A-8-5) |
| `calculate_B1(Cm, Pr, Pe1, alpha)` | App. 8.1.2 | \(B_1 = C_m/(1-\alpha P_r/P_{e1}) \ge 1\) (A-8-3) |
| `calculate_RM(Pmf, Pstory)` | App. 8.1.3 | \(R_M = 1 - 0.15P_{mf}/P_{story}\) (A-8-8) |
| `calculate_Pe_story(H, L, delta_H, RM)` | App. 8.1.3 | \(P_{e\,story} = R_M HL/\Delta_H\) (A-8-7) |
| `calculate_B2(Pstory, Pe_story, alpha)` | App. 8.1.3 | \(B_2 = 1/(1-\alpha P_{story}/P_{e\,story}) \ge 1\) (A-8-6) |
| `amplified_required_strengths(Mnt, Mlt, Pnt, Plt, B1, B2)` | App. 8.1.1 | A-8-1, A-8-2 |
| `moment_redistribution_Lm(M1, M2, ry, Fy, shape)` | App. 8.2 | A-8-9, A-8-10 |

```python
from steelsnakes.US.checks import ALPHA_ASD, calculate_B2, calculate_Pe_story, calculate_RM, notional_load

print(notional_load(288.0))                   # 0.576 kips; Design Example C.1A (LRFD)
print(notional_load(192.0, alpha=ALPHA_ASD))  # 0.614 kips (ASD)

RM = calculate_RM(Pmf=144.0, Pstory=288.0)    # 0.925
Pe_story = calculate_Pe_story(H=1.21, L=240.0, delta_H=0.304, RM=RM)  # 884 kips
print(calculate_B2(288.0, Pe_story))          # 1.48; Design Example C.1C
```

!!! tip "Placing notional loads"
    Per C2.2b(b), distribute Ni over each level in the same way as the gravity load, and apply it in the most
    destabilizing direction. For gravity-only combinations, that means four cases (±X, ±Y). The Modern Steel
    Construction article in `codes/notional-loads-how-to-approach.pdf` explains how to apply them as point loads at
    every column.

## Validation

The test suite reproduces the AISC Design Examples v16.0 (`codes/v16-0-vol-1-design-examples.pdf`): C.1A, C.1C,
D.1 to D.9, E.1B, E.1C, E.1D, E.1E, E.5, E.6, E.7, E.8, E.9, E.10, E.11, E.14A, F.1, F.2, F.3, F.5, F.6, F.7, F.8, F.9,
F.10, F.11A to F.11C, F.12, F.13, G.1 to G.8, H.1B, H.3, H.4 (B1), H.5A to H.5C, and the Part III frame example
(B1 and B2).
Most remaining differences come from the examples rounding intermediate values. Two cases differ by method:

- E.1B: the example reads Manual Table 4-1a at a conservative equivalent length.
- F.11B: the example reuses the conservative leg local buckling result from F.11A.

## API objects

::: steelsnakes.US.checks.stability
