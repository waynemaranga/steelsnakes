# EU Member Checks (EN 1993-1-1)

This page documents the ultimate limit state checks in `steelsnakes.EU.checks.uls`, covering EN 1993-1-1:2005+A1:2014
Section 6: cross-section resistance (6.2), member buckling (6.3.1 to 6.3.5) and the interaction factors of Annexes A
and B.

Every check returns a Pydantic result carrying the resistances, the intermediate values an engineer would write on a
calculation sheet, the utilisation when the design action is given, and a `Reference` to the clause and equation.

!!! warning "Units"
    The checks work in N, mm and N/mm². Moments are in Nmm, so 1 kNm = `1e6`.
    Section properties are read from the tables (cm², cm³, cm⁴, cm, dm⁶) and converted.
    Values passed through `properties=` use the section-table units; keyword arguments such as `A_net` or `A_eff`
    are in mm².

!!! note "Nationally Determined Parameters"
    The defaults are the recommended values: γM0 = γM1 = 1.00, γM2 = 1.25, λLT,0 = 0.4, β = 0.75 and
    kfl = 1.10. η is 1.0, as the 6.2.6(3) note allows.
    Pass your National Annex values where they differ; for example, the UK NA uses γM2 = 1.10.
    The UK NA's own lateral-torsional buckling curve selection is not built in.

## Module map

| Clause | Check | What it covers |
|---|---|---|
| 3.2.1 | `steel_material()` | Table 3.1 fy and fu for EN 10025-2 to -6, EN 10210-1 and EN 10219-1 |
| 6.2.1 | `yield_criterion_utilisation()`, `linear_interaction_utilisation()` | Eq. 6.1 and 6.2 |
| 6.2.2.2 | `net_area()` | Net area with straight or staggered holes (Eq. 6.3) |
| 6.2.3 | `check_tension()` | N_pl,Rd, N_u,Rd, N_net,Rd (Eq. 6.5 to 6.8) |
| 6.2.4 | `check_compression()` | N_c,Rd (Eq. 6.9 to 6.11) |
| 6.2.5 | `check_bending()` | M_c,Rd by class (Eq. 6.12 to 6.16) |
| 6.2.6, 6.2.7 | `check_shear()`, `shear_area()` | A_v cases (a) to (g), V_pl,Rd, V_pl,T,Rd with torsion (Eq. 6.17 to 6.28) |
| 6.2.8 to 6.2.10 | `check_cross_section()` | N, V_y, V_z, M_y and M_z together (Eq. 6.29 to 6.45) |
| 6.3.1 | `check_buckling_resistance()` | Flexural, torsional and torsional-flexural buckling (Tables 6.1 and 6.2) |
| 6.3.2 | `check_lateral_torsional_buckling()` | General and rolled-section methods (Eq. 6.54 to 6.58, Tables 6.3 to 6.6) |
| 6.3.2.4 | `check_restrained_beam()` | Equivalent compression flange method (Eq. 6.59, 6.60) |
| 6.3.3 | `check_bending_and_axial_compression()` | Eq. 6.61 and 6.62, with Annex A (method 1) or Annex B (method 2) |
| 6.3.4 | `check_general_method()` | Eq. 6.63 to 6.66 from load amplifiers |
| 6.3.5.3 | `stable_length()` | Eq. 6.68 |

The checks classify the section to Table 5.2 unless you pass `section_class=`. `check_cross_section()` classifies for
the actions given. With compression and major-axis bending, the web of an I-section or channel is classified in
bending and compression, using α = (1 + N_Ed/(c·t_w·fy))/2 and ψ = 2N_Ed/(A·fy) − 1. Other combinations with
compression use the uniform-compression limits, which is conservative.

## Cross-sections

```python
from steelsnakes.EU import IPE, steel_material, check_cross_section

beam = IPE("IPE-300")
material = steel_material("S355", t=beam.tf)  # fy = 355, fu = 490
result = check_cross_section(beam, material.fy, N_Ed=150e3, M_y_Ed=120e6, V_z_Ed=90e3)
print(result.governing, result.utilisation.utilisation)  # M_y (6.31), 0.538
print(result.utilisations)  # {"V_z (6.17)": 0.171, "N (6.9)": 0.079, "M_y (6.31)": 0.538}
```

`check_cross_section()` works through the following, in order:

1. **Shear.** Where V_Ed > 0.5·V_pl,Rd, it applies the reduced yield strength (1 − ρ)fy to the shear area.
   I-sections under V_z use Eq. 6.30; other cases take (1 − ρ) on the whole moment resistance, which is conservative.
2. **Class 1 and 2.** It reduces the plastic moments for axial force: Eq. 6.36 to 6.38 for I and H sections,
   Eq. 6.39 and 6.40 for RHS, and M_pl(1 − n^1.7) for CHS. Bi-axial bending then uses Eq. 6.41 with the α and β of
   6.2.9.1(6). Shapes without an approximation, such as channels, use the linear summation of Eq. 6.2.
3. **Class 3.** It checks elastic stresses to Eq. 6.42.
4. **Class 4.** It uses Eq. 6.44 with your effective properties (`A_eff`, `W_eff_y`, `W_eff_z`, `e_N_y`, `e_N_z`).

Fastener holes are not accounted for, as 6.2.9.1(5) requires. Check net sections with `check_tension()` and
`tension_flange_holes_negligible()`.

!!! warning "Class 4"
    Effective widths to EN 1993-1-5 are not implemented. A Class 4 check raises `SectionClass4Error` until you
    pass the effective properties it needs.

## Members

```python
from steelsnakes.EU import HD, IPE, MomentDiagram
from steelsnakes.EU import check_buckling_resistance, check_lateral_torsional_buckling, check_bending_and_axial_compression

column = HD("HD-320x158")
buckling = check_buckling_resistance(column, 355.0, L_cr_y=6000.0, L_cr_z=6000.0, N_Ed=2500e3)
print(buckling.governing_mode, buckling.N_b_Rd / 1e3)  # z, 3751 kN (curve c, χz = 0.526)

ltb = check_lateral_torsional_buckling(IPE("IPE-300"), 355.0, L=4000.0, M_Ed=120e6, diagram=MomentDiagram.UDL_SIMPLY_SUPPORTED)
print(ltb.M_cr / 1e6, ltb.chi_LT, ltb.M_b_Rd / 1e6)  # 180.3 kNm, 0.647 (f = 0.976), 144.2 kNm

beam_column = check_bending_and_axial_compression(column, 355.0, N_Ed=2500e3, M_y_Ed=150e6, L_cr_y=6000.0, L_cr_z=6000.0, psi_y=0.0)
print(beam_column.utilisation_y, beam_column.utilisation_z)  # 0.516 (6.61), 0.792 (6.62); Annex B
```

- **Buckling curves.** Table 6.2 picks the curve from the section type, h/b, t_f and the steel grade (the S460
  column). Torsional and torsional-flexural modes use the z-axis curve. Pass `y_0` for channels, whose shear centre
  is offset.
- **M_cr.** EN 1993-1-1 does not give M_cr. `elastic_critical_moment()` uses the NCCI SN003 formula for doubly
  symmetric sections, with C₁ = k_c⁻² from Table 6.6 unless you pass `C_1` or `M_cr`. Circular and square hollow
  sections are not susceptible (6.3.2.1(2)).
- **Equivalent moment factors.** These default to linear moment diagrams from `psi_y`, `psi_z` and `psi_LT`
  (`psi_LT` defaults to `psi_y`). For transverse loads, use `equivalent_moment_factor_B3()` (Annex B) or
  `equivalent_moment_factor_A2()` (Annex A) and pass the results as `C_my`, `C_mz` and `C_mLT`.
- **End cross-sections.** 6.3.3 checks the member. Check the cross-sections at its ends with
  `check_cross_section()` (6.3.3(2)).

## Validation

The tests check the following against independent hand calculations:

- The buckling reduction factors against the tabulated values behind Figure 6.4, for example χ(1.0, b) = 0.597.
- M_cr of an IPE 300 over 4 m (159.3 kNm).
- The IPE 300 shear area (25.7 cm²).
- Every Table 6.2 row and every Table B.3 case.

Built-up members (6.4) and the Annex BB provisions are not implemented.

## API objects

::: steelsnakes.EU.checks.uls
