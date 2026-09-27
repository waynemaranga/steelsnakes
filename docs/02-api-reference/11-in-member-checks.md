# IS 800 Member Checks

This page documents the IS 800:2025 checks in `steelsnakes.IN.checks`:

- `classification`: classification of cross sections (10.8)
- `uls`: the ultimate limit states
- `sls`: the serviceability limit states

They follow the fourth revision of IS 800, "General Construction in Steel — Code of Practice". This is the wide
circulation draft CED 07 (27869) WC of April 2025, and the clause numbers are the draft's, which differ from
IS 800:2007:

| Topic | IS 800:2025 draft | IS 800:2007 |
|---|---|---|
| Classification | 10.8 | 3.7 |
| Partial safety factors | 12.3 and 12.4 | 5.3 and 5.4 |
| Tension | 13 | 6 |
| Compression | 14 | 7 |
| Bending | 15 | 8 |
| Combined forces | 16 | 9 |

The draft brings in parts of EN 1993-1-1:2022:

- Table 2 is EN 1993-1-1 Table 5.2 restated with ε = (250/fy)^0.5.
- There are two new buckling classes, a0 and d.
- Lateral torsional buckling takes the moment gradient factor fm and the weak axis slenderness λy.

The checks run on the IN section objects (IS 808). The IN module ships no section data yet, so build the sections with
their properties, or pass plain properties with a `section_type`. The main entry points are re-exported from
`steelsnakes.IN`.

Every check returns a Pydantic result. It carries the capacities, the values an engineer would write on a calculation
sheet (fy, λ, χ, fcd, λLT, χLT, β and so on) and, when the design action is given, a `UtilisationCheck`. Each result
also has a `Reference` to the clause.

```{warning} Units
    The checks use IS 800 units: kN, kNm, N/mm² and mm.
    Section properties stay in the IS 808 table units: area cm², I and I_t cm⁴, Z cm³, I_w cm⁶ (10⁶ mm⁶) and r mm.
    Arguments carry their unit, e.g `P_kN`, `Mz_kNm`, `KLy_mm` and `An_cm2`.
    Values passed through `properties=` take the IN keys (`D`, `B`, `t`, `T`, `R1`, `area`, `I_zz`, `Z_pz`, `I_t`,
    `I_w` …) or the common aliases (`h`, `b`, `tw`, `tf`, `A`, `Iz`, `Zpz` …).
  ```

```{note} Axes and yield stress
    IS 800 takes z-z as the major axis, parallel to the flanges, and y-y as the minor axis (8).
    Angles also use u-u and v-v for their principal axes.
    For I-sections and channels, the larger of I_zz and I_yy is taken as z-z, whichever key holds it.
    When `fy_mpa` is omitted, fy comes from Table 1 (IS 2062) for `steel_grade` and the thickest element, e.g 250,
    240 or 230 MPa for E250 below 20 mm, from 20 mm to 40 mm, and above 40 mm.
  ```

## Module map

| Clause | Function | What it covers |
|---|---|---|
| Table 1, 9.2.4 | `yield_stress()`, `ultimate_stress()`, `E_STEEL`, `G_STEEL` | IS 2062 fy and fu, E = 2.0 × 10⁵ MPa, G = 0.769 × 10⁵ MPa |
| 10.8, Table 2 | `classify_section()`, `classify_section_from_dict()`, `stress_ratios()`, `effective_width()` | Classes 1 to 4, r1 and r2, 10.8.2 d) effective widths |
| 10.9, Table 3 | `check_slenderness()` | Maximum KL/r |
| 12.3.3, Table 4 | `load_factors()`, `factored_load()` | γf of the strength and serviceability combinations |
| 12.4.1, Table 5 | `GAMMA_M0`, `GAMMA_M1`, `connection_safety_factor()` | γm0 = 1.10, γm1 = 1.25; connections |
| 13.2 to 13.4 | `check_tension()`, `net_area()`, `shear_lag_factor()`, `block_shear_strength()` | Tdg, Tdn with β (angles, 13.3.4), Tdb |
| 14.1, Tables 7 to 10 | `check_compression()`, `buckling_class()`, `design_compressive_stress()`, `stress_reduction_factor()` | Pd = Ae fcd per axis; torsional flexural buckling (14.1.2.2) |
| 14.2, Table 11, Annex D | `effective_length()`, `frame_effective_length_factor()`, `stiffness_ratio()` | KL of members, K of columns in frames |
| 14.3.2, 10.8.2 d) | `effective_sectional_area()` | Ae of slender sections |
| 14.5.1, Table 12 | `check_angle_strut()`, `angle_strut_modification_factor()` | Single angles, concentric or through one leg (Kf) |
| 15.2.1, 16.2 | `check_bending()`, `high_shear_design_moment()` | Md = βb Zp fy/γm0 <= 1.2Ze fy/γm0, Mdv |
| 15.2.1.4, 15.2.1.5 | `tension_flange_holes_negligible()`, `shear_lag_negligible()` | Holes and shear lag in flanges |
| 15.2.2, Tables 13 and 14 | `check_lateral_torsional_buckling()`, `lateral_torsional_reduction_factor()`, `moment_gradient_factor()` | Md = βb Zp fbd, χLT with fm and λy |
| 15.2.2.1, Annex E, Table 42 | `elastic_critical_moment()`, `critical_bending_stress()`, `elastic_critical_moment_general()`, `annex_e_constants()` | Mcr |
| 15.3, Tables 15 and 16 | `beam_effective_length()`, `segment_effective_length()`, `cantilever_effective_length()` | LLT |
| 15.4 | `check_shear()`, `shear_area()`, `shear_buckling_stress()`, `tension_field_shear_resistance()` | Vd, simple post-critical and tension field methods |
| 16.3.1, Table 17 | `reduced_flexural_strength()`, `interaction_exponents()` | Mnd and α1, α2 |
| 16.3.2, Table 18 | `check_tension_and_bending()`, `check_compression_and_bending()`, `equivalent_uniform_moment_factor()` | Meff; the Ky, Kz and KLT interaction |
| 12.6.1, Table 6 | `check_vertical_deflection()`, `check_beam_deflection()`, `check_horizontal_deflection()`, `check_crane_rail_displacement()` | Deflection limits, 12.6.1.1 camber |
| 12.6.2, Annex C | `check_vibration()`, `floor_frequency()`, `heel_impact_acceleration()` | f1, fr against 5 Hz or 8 Hz; a0/g |

## Beams

```python
from steelsnakes.IN import (
    MediumWeightBeam,
    beam_effective_length,
    check_bending,
    check_lateral_torsional_buckling,
    check_shear,
    moment_gradient_factor,
)

# ISMB 300 (IS 808); I_t and I_w from Σbt³/3 and Iy hf²/4
beam = MediumWeightBeam(
    designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26,
    I_zz=8603.6, I_yy=453.9, Z_zz=573.6, Z_yy=64.8, Z_pz=651.7, Z_py=111.0, I_t=21.7, I_w=93_870.0,
)
print(check_shear(beam, V_kN=200.0).Vd)                    # 295.2 kN = Av fyw/(√3 γm0)
print(check_bending(beam, M_kNm=100.0, V_kN=250.0).Md)     # 129.7 kNm: high shear, β = 0.481 (16.2.2)

LLT = beam_effective_length(4000.0, "no_warping_restraint")  # Table 15 v): 1.0L
ltb = check_lateral_torsional_buckling(beam, LLT_mm=LLT, Mz_kNm=80.0, fm=moment_gradient_factor("udl"))
print(ltb.Mcr, ltb.lambda_LT, ltb.lambda_y, ltb.chi_LT)  # 125.8 kNm, 1.138, 1.585, 0.553
print(ltb.Md, ltb.utilisation.utilisation)               # 81.9 kNm, 0.977
```

- **Design bending strength.** `check_bending()` returns βb Zp fy/γm0, capped at 1.2Ze fy/γm0, or 1.5Ze fy/γm0 with
  `cantilever=True` (15.2.1.2). βb is 1.0 for plastic and compact sections and Ze/Zp for semi-compact ones. Slender
  sections need `Z_eff_cm3`. Under V > 0.6Vd the result is Mdv of 16.2.2, where Mfd is the plastic strength less
  that of the shear area. Webs with d/tw > 67ε carry a note pointing to 15.2.1.1.
- **Lateral torsional buckling.**
    - Mcr comes from 15.2.2.1 when I_t and I_w are given, otherwise from the approximate fcr,b. You can also pass
      `Mcr_kNm`, for instance from `elastic_critical_moment_general()` with the c1, c2 and c3 of Table 42.
    - I-sections use the doubly symmetric χLT, with fm from Table 14 and λy for the distance between lateral
      supports (`Ly_mm`, by default `LLT_mm`).
    - Channels take αLT = 0.76 and the general formula.
    - Hollow sections (15.2.2 b)) and beams with λLT < 0.4 (15.2.2 c)) are treated as laterally supported.
- **Shear.** Webs with d/tw > 67εw are checked for shear buckling, using Vcr = Av τb (simple post-critical), or the
  tension field method with `c_mm` and `method="tension_field"`. `Avn_cm2` applies the fastener hole rule in the
  note to 15.4.1.1.

## Columns

```python
from steelsnakes.IN import check_compression, check_compression_and_bending, effective_length, equivalent_uniform_moment_factor, moment_gradient_factor

result = check_compression(beam, P_kN=350.0, KLz_mm=4000.0, KLy_mm=effective_length(4000.0, "pinned_pinned"))
print([(mode.axis, mode.buckling_class, mode.KL_r, mode.fcd) for mode in result.modes])
# z: a, 32.3, 218.6 MPa; y: b, 140.8, 71.1 MPa (Table 10, rolled I with h/bf > 1.2)
print(result.Pd, result.utilisation.utilisation)  # 400.0 kN, 0.875

Cm = equivalent_uniform_moment_factor(psi=0.0)  # Table 18: 0.6
beam_column = check_compression_and_bending(
    beam, P_kN=150.0, Mz_kNm=40.0, KLy_mm=4000.0, KLz_mm=4000.0, LLT_mm=4000.0,
    Cmz=Cm, CmLT=Cm, fm=moment_gradient_factor("end_moments", psi=0.0),
)
print(beam_column.governing, beam_column.utilisation.utilisation)  # member, y-y (16.3.2.2), 0.795
```

- **Design compressive strength.** fcd = χ fy/γm0 with χ from 14.1.2.1, which reproduces Table 8 and the fcd of
  Table 9. The buckling class comes from Table 10 via `buckling_shape()`, or can be passed as `buckling_classes`.
  `welded=True` selects the welded I and box rows.
- **Slender sections.** Ae is Ag less the width of every slender element in excess of its semi-compact limit
  (10.8.2 d)), or `A_eff_cm2`. `A_holes_cm2` deducts holes not fitted with fasteners (14.3.2).
- **Torsional flexural buckling.** 14.1.2.2 needs fcrTF, for which the draft gives no formula. Pass `f_cr_TF_mpa`,
  for instance from `elastic_torsional_buckling_stress()` or `elastic_torsional_flexural_buckling_stress()`, which
  give the classical elastic values.
- **Combined forces.**
    - Section strength (16.3.1): plastic and compact sections use the 16.3.1.2 approximations for rolled and welded
      I, RHS and CHS, with Table 17. The linear form is also computed, and the smaller of the two is the result.
      Semi-compact sections and channels use the linear form.
    - Member strength (16.3.2.2): uses Pdy and Pdz from 14.1.2, Mdz from 15.2.2 when `LLT_mm` is given, and Cm from
      Table 18. It needs both `KLy_mm` and `KLz_mm`.

## Ties and struts

```python
from steelsnakes.IN import UnequalAngle, check_angle_strut, check_tension

angle = UnequalAngle(designation="ISA 100x75x8", a=100.0, b=75.0, t=8.0, area=13.36, I_zz=133.2, I_yy=64.1, I_uu=162.0, I_vy=35.3)
tie = check_tension(angle, T_kN=250.0, An_cm2=13.36 - 1.6, Lc_mm=150.0, g_mm=55.0)
print(tie.Tdg, tie.Tdn, tie.beta, tie.governing)  # 303.6 kN, 314.6 kN, 1.047, yielding

strut = check_angle_strut(angle, P_kN=100.0, L_mm=1500.0, connection="two_bolts", fixity="hinged")
print(strut.lambda_bar, strut.Kf, strut.fcd, strut.Pd)  # λaa 0.771, Kf 0.597, fcde 100.7 MPa, 134.5 kN
```

- **Shear lag.** With `Lc_mm`, angles connected through one leg take Tdn = 0.9Anc fu/γm1 + βAgo fy/γm0 (13.3.3). Ago
  is (w − t/2)t, and bs is w (welded) or w + g − t (bolted, Fig. 6). Other sections connected by one element (13.3.4)
  need `Ago_cm2`, `w_mm`, `t_mm` and `bs_mm`. Without `Lc_mm`, Tdn is 0.9An fu/γm1 (13.3.1).
- **Angles loaded through one leg.** fcde = Kf χaa fy/γm0 (14.5.1.2). χaa is for class b about the axis parallel to
  the connected leg, and `fixity` may be a fraction between hinged (0) and fixed (1), per note 1 of Table 12.

## Serviceability

```python
from steelsnakes.IN import check_beam_deflection, check_vibration, serviceability_load

result = check_beam_deflection(beam, L=6000.0, imposed=serviceability_load(imposed=10.0), member="floor_susceptible")
print(result.delta, result.limit)  # 9.81 mm against span/360 = 16.67 mm
print(check_vibration(I_T_cm4=40_000.0, W_kN_m=8.0, L_mm=9000.0).f)  # 6.09 Hz >= 5 Hz (Annex C-3)
```

The Table 6 limits are recommendations (12.6.1), and every check takes a `span_ratio` to override them.

## Draft misprints

Where the draft misprints a formula, the checks follow the draft's own tables or the text it restates. Where the draft
is only inconsistent, the checks follow it as printed. The docstrings flag each case:

| Clause | As printed | As implemented |
|---|---|---|
| 14.1.2.1, 14.1.2.2 | χ = 1/[φ + (φ² + λ²)^0.5] | φ² − λ², which Table 8 follows (e.g 0.579 for class a, fy = 250 MPa, KL/r = 100) |
| 14.1.2.2 | λy is "the distance between intermediate lateral support and shear centre" | That is dy; λy is taken as the non-dimensional slenderness about y-y |
| 14.1.2.2 | fcrTF, the torsional buckling stress, has no formula | Passed in; classical elastic helpers are provided |
| 15.2.2 | φLT contains αLT(λLT − 0.2) | αLT(λy − 0.2), as EN 1993-1-1:2022 (8.82), which the draft adopts; conservative for rolled I-sections |
| 15.2.2 | χLT is given only for doubly symmetric sections | Other sections use the IS 800:2007 form, φLT = 0.5[1 + αLT(λLT − 0.2) + λLT²] |
| Table 14 | fm for M0/Mh < 0 is not given | 1.0, as EN 1993-1-1:2022 |
| Table 2 | Class 3 of outstands under non-uniform stress is blank | 13.6ε, the uniform compression limit (conservative) |
| Table 2 | CHS axial compression 86ε², moment 85ε² | As printed |
| Table 10 | "Channel, Angle, T and Solid" is class c, but its figure has no angle and later rows give rolled angles b (a above 420 MPa) | The angle rows |
| Table 13 | Welded I 0.12(Zez/Zey)^0.5 <= 0.34 for both thicknesses; rolled h/b <= 1.2 the same | As printed (EN 1993-1-1:2022 has 0.21/0.64, 0.25/0.76 and 0.16/0.49) |
| Table 18 | 0.2(1 − ψ) − 0.8αs and 0.95 − 0.05αh | As printed (EN 1993-1-1 Table B.3 has 0.2(−ψ) and 0.95 + 0.05αh) |
| 16.3.2.2 | KLT uses λLT | As printed (EN 1993-1-1 Annex B has λz) |
| Table 42 | c1 for ψ = −3/4 at K = 0.7 and 0.5 repeats ψ = −1/2 | As printed (as in IS 800:2007) |
| Fig. 2B, 2C | Effective widths 15.7ε and 21ε of IS 800:2007 | The 10.8.2 d) rule with the Table 2 limits |

## Not implemented

The following are not implemented:

- connections (17) and lug angles
- column bases (14.4), laced and battened columns (14.6, 14.7) and back-to-back members (14.8)
- plate girder flanges, webs and stiffeners (15.6, 15.7), except the shear buckling resistance of 15.4.2
- box girders, purlins and bending in a non-principal plane (15.8 to 15.10)
- earthquake design (18), fatigue (19), fire (22) and the frame analysis of Section 11 and Annex B
- stepped columns (Annex D, D-2)
- the effective modulus of slender sections in bending (pass `Z_eff_cm3`)
- Mcr of angles and tees (pass `Mcr_kNm`)
- tees, since the IN module has no tee sections yet

## API objects

::: steelsnakes.IN.checks.classification

::: steelsnakes.IN.checks.uls

::: steelsnakes.IN.checks.sls
