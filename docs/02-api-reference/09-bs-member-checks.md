# BS 5950 Member Checks

This page documents the BS 5950-1:2000 member checks: the ultimate limit states in `steelsnakes.BS.checks.uls`
and the serviceability limit states in `steelsnakes.BS.checks.sls`. Together they cover:

- the ultimate limit states of Section 2.4
- net areas (3.4) and slender cross-sections (3.6)
- the design of members in Section 4
- Annexes B (lateral-torsional buckling), C (compressive strength), H (shear buckling) and I (combined axial force and
  bending)
- the serviceability limit states of 2.5

Like the classification, the checks run on the UK section objects, and the main entry points are re-exported from
`steelsnakes.BS`.

Every check returns a Pydantic result. It carries the capacities, the values an engineer would write on a
calculation sheet (py, λ, pc, λLT, pb, ρ and so on) and, when the design action is given, a `UtilisationCheck`.
Each result also has a `Reference` to the clause.

```{warning} Units
    The checks use BS 5950 units: kN, kNm, N/mm² and mm.
    Section properties stay in the table units: A cm², Z and S cm³, I and J cm⁴, r cm and H dm⁶.
    Arguments carry their unit, e.g `Fc_kN`, `Mx_kNm`, `LE_mm` and `An_cm2`.
    Values passed through `properties=` take either the UK table keys (`h`, `tw`, `W_pl_yy`, `I_w` …) or BS notation
    (`D`, `t`, `Sx`, `H` …).
  ```

```{note} Axes and design strength
    BS 5950 takes x-x as the major axis and y-y as the minor axis. These are y-y and z-z in the UK tables.
    Angles use u-u and v-v for their principal axes.
    When `py_mpa` is omitted, py comes from Table 9 for `steel_grade` and the thickest element, as in the
    classification.
  ```

## Module map

| Clause | Function | What it covers |
|---|---|---|
| 2.4.1, Table 2 | `load_factor()`, `factored_load()` | γf and load combinations 1 to 3 |
| 2.4.2 | `notional_horizontal_force()`, `minimum_horizontal_wind_load()`, `check_sway_stability()`, `amplification_factor()` | Notional forces, λcr = h/200δ, non-sway or sway-sensitive, kamp |
| 2.4.4, Tables 3 and 7 | `check_brittle_fracture()`, `limiting_thickness()`, `charpy_temperature()` | t <= K t1, with t1 from the formula alternative to Tables 4 and 5 |
| 2.4.5 | `tie_force()` | Tying forces, 75 kN minimum |
| 3.4 | `net_area()`, `effective_net_area_coefficient()`, `effective_net_area()` | Staggered holes (Figure 3), Ke |
| 3.6 | `effective_section()` | Aeff and Zeff (3.6.2.2, 3.6.2.3, 3.6.4, 3.6.6), or pyr (3.6.5) |
| 4.2.3, 4.4.5, H.1, H.2 | `check_shear()`, `shear_area()`, `shear_buckling_strength()` | Pv = 0.6pyAv, Vw = d t qw, Vcr |
| 4.2.5 | `check_bending()`, `notched_end_moment_capacity()` | Mc for low and high shear, the 1.2pyZ / 1.5pyZ limit |
| 4.3.5, Tables 13 and 14 | `beam_effective_length()`, `segment_effective_length()`, `cantilever_effective_length()` | LE for lateral-torsional buckling |
| 4.3.6, Table 18, Annex B | `check_lateral_torsional_buckling()`, `bending_strength()`, `equivalent_uniform_moment_factor_mLT()` | Mb = pb S, λLT = u v λ βW^0.5, RHS (Table 15, B.2.6), angles (4.3.8.3) |
| 4.5.2, 4.5.3 | `check_web_bearing()` | Pbw and Px (or Pxr) of unstiffened webs |
| 4.6 | `check_tension()` | Pt = pyAe; simple ties with eccentric connections (4.6.3) |
| 4.7, Tables 22 to 24, Annex C | `check_compression()`, `effective_length()`, `strut_curve()`, `compressive_strength()` | Pc = Ag pc or Aeff pcs, per axis |
| 4.7.7 | `check_simple_column()` | Columns in simple structures, λLT = 0.5L/ry |
| 4.7.10, Table 25 | `check_angle_strut()`, `single_angle_slenderness()`, `double_angle_slenderness()`, `channel_slenderness()`, `tee_slenderness()` | Angle, channel and T struts |
| 4.8.2 | `check_tension_and_bending()` | 4.8.2.2 and 4.8.2.3 with I.2 |
| 4.8.3, 4.9, Table 26, Annex I | `check_compression_and_bending()`, `equivalent_uniform_moment_factor_m()`, `reduced_plastic_moduli()` | 4.8.3.2, 4.8.3.3.1 to 4.8.3.3.3, I.1 |
| I.4.3 | `check_single_angle_compression_and_bending()` | Simplified method for equal angles |
| B.3, C.3, I.5 | `strut_action_moment()`, `lateral_torsional_internal_moment()`, `amplified_moment()` | Internal second-order moments |
| 2.5.1, 2.5.2, Table 8 | `serviceability_load()`, `check_vertical_deflection()`, `check_beam_deflection()`, `check_horizontal_deflection()` | Unfactored loads, suggested deflection limits |
| 2.5.3 | `check_vibration()` | f = 18/√δ against 3 Hz (SCI P076) |

## Beams

```python
from steelsnakes.BS import (
    UB,
    beam_effective_length,
    check_bending,
    check_lateral_torsional_buckling,
    check_shear,
    equivalent_uniform_moment_factor_mLT,
)

beam = UB("457x191x67")
print(check_shear(beam, steel_grade="S275", Fv_kN=500.0).Pv)            # 635.9 kN
print(check_bending(beam, steel_grade="S275", M_kNm=300.0, Fv_kN=500.0).Mc)  # 364.9 kNm: high shear, ρ = 0.328

LE = beam_effective_length(4000.0, "both_flanges_free")                  # Table 13: 1.0LLT
mLT = equivalent_uniform_moment_factor_mLT(M2=0.75, M3=1.0, M4=0.75, M_max=1.0)  # uniform load: 0.925
ltb = check_lateral_torsional_buckling(beam, steel_grade="S275", LE_mm=LE, Mx_kNm=200.0, mLT=mLT)
print(ltb.lambda_LT, ltb.pb, ltb.Mb)  # 78.9, 167.4 N/mm², 246.1 kNm
print(ltb.governing, ltb.utilisation.utilisation)  # mLT Mx/Mb (4.3.6.2), 0.752
```

- **Moment capacity.** `check_bending()` returns pyS for class 1 and 2, pyZ or pySeff for class 3 (3.5.6, now
  including RHS and CHS), and pyZeff for class 4. Where Fv > 0.6Pv it reduces this by ρSv (4.2.5.3). The 4.2.5.1
  limit applies throughout: 1.2pyZ by default (`simple_span=True`) or 1.5pyZ with `simple_span=False`.
- **Lateral-torsional buckling.** u and x come from the section tables, else from B.2.3, else from the 4.3.6.8
  approximations. `approximate=True` uses u = 0.9 and x = D/T, which reproduces Table 20 (the 4.3.7 simple method).
  CHS and square sections are never susceptible. An RHS is only checked beyond the Table 15 limit, using the next
  higher D/B row, which is conservative. A destabilizing load sets mLT = 1.0.
- **Shear buckling.** Webs with d/t > 70ε (62ε welded) get Vw = d t qw from H.1, which reproduces Table 21.
  The moment capacity of such webs (4.4.4) is not implemented; the result carries a note.

## Columns

```python
from steelsnakes.BS import UC, check_compression, check_compression_and_bending, effective_length

column = UC("254x254x73")
result = check_compression(column, steel_grade="S275", Fc_kN=1200.0, LEx_mm=5000.0, LEy_mm=effective_length(5000.0, "fixed_pinned"))
print([(mode.axis, mode.curve, mode.pc) for mode in result.modes])  # x: b, 243.5; y: c, 190.1 (λy = 65.6)
print(result.Pc, result.utilisation.utilisation)  # 1769 kN, 0.678

beam_column = check_compression_and_bending(
    column, steel_grade="S275", Fc_kN=800.0, Mx_kNm=50.0, My_kNm=8.0,
    LEx_mm=5000.0, LEy_mm=5000.0, LE_LT_mm=5000.0, mx=0.9, my=0.9, mLT=0.925,
)
print(beam_column.governing, beam_column.utilisation.utilisation)  # lateral-torsional (4.8.3.3.2c), 0.851
```

- **Compressive strength.** pc is the Perry formula of Annex C, which reproduces Table 24. The strut curve comes from
  Table 23. UB are I-sections (D/B > 1.2); UC and UBP are H-sections. Welded I, H and box sections use py − 20 N/mm²,
  and thicknesses of 40 mm to 50 mm average the two rows.
- **Class 4.** Slender sections use Aeff and pcs at λ(Aeff/Ag)^0.5. UB webs in compression are often slender with
  r2 = 1, so pass `Fc_kN` to classify at the actual stress ratio.
- **Beam-column classification.** `check_compression_and_bending()` classifies for the moments with the axial force
  (4.8.1): webs use the "generally" row with r1 and r2. The axial compression class only counts when it is slender,
  because Table 11 has no class 1 or 2 for webs in axial compression.
- **Methods.** `method="exact"` (the default) uses 4.8.3.3.2 for I and H sections and 4.8.3.3.3 for CHS and RHS.
  Other shapes fall back to the simplified method. `method="simplified"` uses 4.8.3.3.1, and `method="stocky"` uses
  I.1 for doubly symmetric class 1 and 2 sections.
- **Cross-section check.** Class 1 and 2 cross-sections also try the 4.8.2.3 alternative with the reduced moments of
  I.2, and keep the smaller result.
- **Member moment capacities.** The member checks take Mcx and Mcy without shear, since buckling resistance is
  unaffected by shear (4.8.1). The cross-section check includes the co-existing shear.
- **Lateral restraint.** Without `LE_LT_mm`, the segment is taken as fully restrained (4.2.2), so Mb = Mcx.

## Ties, struts and simple columns

```python
from steelsnakes.BS import L_EQUAL, UC, check_angle_strut, check_simple_column, check_tension, net_area

angle = L_EQUAL("80x80x8.0")
tie = check_tension(angle, steel_grade="S275", Ft_kN=200.0, An_cm2=net_area(12.3, 8.0, 22.0, n_holes=1), connection="bolted")
print(tie.Pt, tie.method)  # 234.2 kN, 4.6.3.1: py(Ae - 0.5a2)
print(check_angle_strut(angle, Fc_kN=100.0, L_mm=2000.0).Pc)  # 137.3 kN: λ = 0.85Lv/rv = 109.0, curve c

column = check_simple_column(UC("254x254x73"), Fc_kN=1000.0, Mx_kNm=20.0, My_kNm=5.0, LEx_mm=5000.0, LEy_mm=5000.0)
print(column.Mbs, column.utilisation.utilisation)  # 263.0 kNm, 0.779
```

- **Effective net area.** Ae is the sum over the elements of ae = Ke·an <= ag (3.4.3). Pass the elements as
  `elements=[(ag, an), ...]`. With `An_cm2` alone, Ke is not applied, because the holes may all lie in one element.
  Simple ties (`connection=`) take the holes in the connected element.

## Serviceability

```python
from steelsnakes.BS import UB, check_beam_deflection, check_horizontal_deflection, serviceability_load

beam = UB("457x191x67")
result = check_beam_deflection(beam, L=6000.0, imposed=serviceability_load(imposed=20.0), member="brittle_finish")
print(result.delta, result.limit)  # 5.60 mm against span/360 = 16.67 mm
print(check_horizontal_deflection(9.0, 3500.0).utilisation.utilisation)  # storey height/300: 0.771
```

The Table 8 limits are suggestions (2.5.2), and every check takes a `span_ratio` to override them. Purlins, portal
frame columns and crane columns have no numerical limit, so they need one.

## Not implemented

The following are not implemented:

- plate girders (4.4), except the shear buckling resistance of 4.4.5.2
- stiffener design (4.5.2.2 onwards)
- the web checks of H.3
- members with one flange laterally restrained (Annex G)
- effective lengths from Annexes D and E
- tapered members (B.2.5)
- T-sections and unequal angles in lateral-torsional buckling; only the helper functions exist
- continuous structures (Section 5)
- connections (Section 6)

The classification of an I-section under axial force and minor axis bending puts the web in the "axial compression"
row, so such sections are at best class 3. This is conservative.

## API objects

::: steelsnakes.BS.checks.uls

::: steelsnakes.BS.checks.sls
