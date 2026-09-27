# CHANGELOG

## 0.0.1-alpha-9 (unreleased)

### Added

- `US`: AISC 360-22 member checks (LRFD) across Chapters D to H; the dispatchers are `tension()`, `compression()`,
  `flexure()` and `shear()`, and Chapter H lives in `steelsnakes.US.checks.combined`.
- `US`: `steelsnakes.US.checks.stability`, covering:
    - C2.1(b) conditions for neglecting P-δ
    - C2.2b notional loads (Eq. C2-1)
    - C2.3 stiffness reduction τb and the 0.001αYi notional load
    - Appendix 7 effective-length and first-order method limits (Eq. A-7-3)
    - Appendix 8.1 B1, B2, Cm, Pe1, RM and Pe story (Eqs. A-8-1 to A-8-8)
    - Appendix 8.2 moment redistribution Lm
- `BS`: BS 5950-1:2000 Section 3.5 classification on UK sections, covering:
    - Table 9 design strength
    - Tables 11 and 12
    - 3.5.3 compound flanges
    - 3.5.5 stress ratios r1 and r2
    - 3.5.6.2 effective plastic modulus
    - calculation-sheet rendering
- `EU`/`UK`: Table 5.2 Sheet 2/3 outstands in combined bending and compression, using α, the tip in compression or
  tension, and kσ from EN 1993-1-5 Table 4.2.
- `EU`/`UK`: 5.5.2(9) σcom,Ed relaxation of Class 4 parts, and a 5.5.2(11) note for Class 3 webs with Class 1/2
  flanges.
- Tests reproducing the AISC Design Examples v16.0: C.1A, C.1C, D.1 to D.9, E.6, E.9, F.6, F.11B, H.3, H.4 (B1), and
  the Part III frame (B1/B2), in addition to the existing E, F, G and H examples.
- Docs: "US Member Checks" and "BS 5950 Classification" API pages.

### Fixed

- `EU`/`UK`: restored the public `StressPattern` preset enum (`COMPRESSION`, `MAJOR_AXIS_BENDING`,
  `MINOR_AXIS_BENDING`, `COMBINED`); the README and docs examples imported it and failed.
- `BS/checks/classification.py` could not be imported (invalid default `"S275" | "S355" | "S460"`).
- The `steelsnakes` console script pointed at `steelsnakes:main`, which does not exist; it now runs
  `steelsnakes.main:main`.
- Docs home page example imported `steelsnakes.UK.universal` and `steelsnakes.US.beams`, which do not exist.
- The `main.py` minor-axis RHS example now uses `StressPattern.MINOR_AXIS_BENDING`.


## 0.0.1-alpha-10 (unreleased)

### Added

- `EU`: EN 1993-1-1 Section 6 ultimate limit state checks in `steelsnakes.EU.checks.uls`, covering:
    - Table 3.1 steel strengths (`steel_material()`)
    - 6.2 cross-section resistance: tension with net areas, compression, bending, shear areas (a) to (g), torsion,
      and N, V and M together (`check_cross_section()`, Eq. 6.29 to 6.45)
    - 6.3.1 flexural, torsional and torsional-flexural buckling (Tables 6.1 and 6.2)
    - 6.3.2 lateral-torsional buckling, general and rolled methods, with f and k_c (Tables 6.3 to 6.6) and M_cr
      from NCCI SN003
    - 6.3.2.4 equivalent compression flange method
    - 6.3.3 beam-columns with Annex A (method 1) or Annex B (method 2)
    - 6.3.4 general method
    - 6.3.5.3 stable length
- `EU`: EN 1993-1-1 Section 7 serviceability limit state checks in `steelsnakes.EU.checks.sls`, covering:
    - EN 1990 6.5.3 characteristic, frequent and quasi-permanent combinations with the Table A1.1 ψ factors
      (`sls_combination()`)
    - 7.1(4) elastic stresses under the SLS combination, to EN 1993-2 7.3 (`check_serviceability_stresses()`)
    - 7.2.1 vertical deflections to EN 1990 Figure A1.1, from deflections or from the loads on single-span beams and
      cantilevers (`check_vertical_deflection()`, `check_beam_deflection()`)
    - 7.2.2 storey and overall horizontal deflections to EN 1990 Figure A1.2 (`check_horizontal_deflection()`)
    - 7.2.3 natural frequency of floor beams to EN 1990 A1.4.4 (`check_vibration()`)
    - the UK NA suggested deflection limits as defaults, since EN 1993-1-1 recommends none
- `base`: SLS limit states `VERTICAL_DEFLECTION`, `HORIZONTAL_DEFLECTION`, `VIBRATION` and `SERVICEABILITY_STRESS`.
- Docs: "EU Member Checks" and "EU Serviceability Checks" API pages.
- `US_Metric`: wired into the shared database and factory as region `US_METRIC`, so `W("W310X38.7")`, `C()`, `L_EQUAL()`
  etc. build sections from the packaged SI data; before, every lookup failed.
- `base`: `SectionFactory.create_section()` takes the section type as a `SectionType` or its value, e.g `"UB"`.
- `base`: `SectionDatabase(..., sqlite_db_path=...)` for the experimental SQLite fallback.
- `EU`: `ExtraWideFlangeBeamHLZ` and `ParallelFlangeChannelUPE`, so HLZ and UPE sections report their own section type.
- Tests: restored `tests/test_UK_module.py` and `tests/test_fuzzy_matching.py`; added `tests/test_US_Metric_module.py`,
  SQLite fallback tests, and a test that builds every packaged section in UK, EU, US and US_METRIC.
- `US_Metric`: AISC 360-22 checks in SI units (N, mm, MPa) in `steelsnakes.US_Metric.checks`, also exported from
  `steelsnakes.US_Metric`, covering:
    - `classify_section()` (B4.1) and the `tension()`, `compression()`, `flexure()`, `shear()` and `hss_torsion()`
      dispatchers
    - the metric tables converted to mm on read (I in 10⁶ mm⁴, Z, S and C in 10³ mm³, J in 10³ mm⁴, Cw in 10⁹ mm⁶)
    - the SI constants of B4.3b (2 mm), D5 (16 mm; 1 and 2 mm), D6 (13 mm, 1 mm, 485 MPa), Appendix 8.2 (450 MPa) and
      Commentary Table C-F10.1 (βw in mm)
- `US`: Table B4.1b case 16 (webs of singly symmetric I-shapes), classification of angles in flexure (case 12), and
  minor-axis flexure classification of rectangular HSS (the h walls become the flanges), round HSS and single angles.
- `US`: `ElementInput.metadata` carries the case inputs (kc, Fl, hc_hp, Mp_My) through `classify_element()`.
- `US`: `built_up=True` on the F4 and F5 checks uses Table B4.1b case 11 for the flange limits.
- `US`: the inch and ksi constants of D5, D6 and Appendix 8.2 are parameters (`be_offset`, `clearances`, `t_min`,
  `hole_clearance`, `Fy_limit`); `angle_beta_w()` takes a `tolerance`.
- `EU`/`UK`: angles in bending classify each leg as an outstand (Table 5.2 Sheet 3 to Sheet 2).
- `EU`/`UK`: under compression and bending about one axis, `check_cross_section()` and the member checks classify the
  two RHS/SHS walls in bending with α = (1 + N_Ed/(2c·t·fy))/2.
- `EU`/`UK`: a Class 1 or 2 section without a tabulated W_pl, such as an angle, uses W_el (6.2.1(4)).
- Tests: `tests/test_US_Metric_checks.py`, which reproduces AISC Design Examples on the metric twins and compares every
  section type with its imperial twin.
- `BS`: BS 5950-1:2000 ultimate limit states in `steelsnakes.BS.checks.uls`, in kN, kNm, N/mm² and mm, with the section
  tables in their own units, covering:
    - 2.4.1 Table 2 load factors and load combinations 1 to 3 (`factored_load()`)
    - 2.4.2 notional horizontal forces, λcr = h/200δ, non-sway or sway-sensitive frames and kamp
      (`check_sway_stability()`), and the restraint forces of 4.3.2, 4.3.3 and 4.7.1
    - 2.4.4 brittle fracture from the t1 formula with Tables 3 and 7 (`check_brittle_fracture()`), and 2.4.5 tie forces
    - 3.4 net areas with staggered holes and the effective net area coefficient Ke
    - 3.6 effective properties of slender sections: Aeff and Zeff of I, H, RHS and SHS (3.6.2.2, 3.6.2.3), equal angles
      (3.6.4) and CHS (3.6.6), or the reduced design strength pyr (3.6.5) (`effective_section()`)
    - 4.2 shear capacity with the shear buckling resistance of 4.4.5.2 and Annex H.1/H.2 (`check_shear()`), and the
      moment capacity with high shear and the 1.2pyZ/1.5pyZ limit (`check_bending()`)
    - 4.3 lateral-torsional buckling: Tables 13 and 14 effective lengths, Table 18 mLT, pb from Annex B (Tables 16 and
      17), λLT = u v λ βW^0.5 with u and x from the tables or B.2.3, the 4.3.7 simple method, RHS to Table 15 and B.2.6,
      and single angles to 4.3.8.3 (`check_lateral_torsional_buckling()`)
    - 4.5.2 and 4.5.3 web bearing and buckling of unstiffened webs (`check_web_bearing()`)
    - 4.6 tension with the effective net area and the simple ties of 4.6.3 (`check_tension()`)
    - 4.7 compression with Tables 22 to 24 and Annex C (`check_compression()`), angle, channel and T struts to 4.7.10 and
      Table 25 (`check_angle_strut()`), and columns in simple structures, 4.7.7 (`check_simple_column()`)
    - 4.8 and 4.9 combined moment and axial force: 4.8.2 (`check_tension_and_bending()`); 4.8.3.2, 4.8.3.3.1 to
      4.8.3.3.3 and the stocky members of I.1, with the reduced plastic moduli of I.2 and Table 26
      (`check_compression_and_bending()`); I.4.3 for equal angles
    - the internal moments of B.3, C.3 and I.5
- `BS`: BS 5950-1:2000 2.5 serviceability limit states in `steelsnakes.BS.checks.sls`: serviceability loads (2.5.1),
  the Table 8 deflection limits for beams, columns and crane girders (2.5.2), and floor frequency (2.5.3, SCI P076).
- `BS`: 3.5.6.3 and 3.5.6.4, the effective plastic modulus of class 3 RHS and CHS (`effective_plastic_modulus_rhs()`,
  `effective_plastic_modulus_chs()`); `effective_plastic_modulus()` also takes `section_type` and `properties`.
- Docs: "BS 5950 Member Checks" API page.
- Tests: `tests/test_BS_uls.py` and `tests/test_BS_sls.py`, against Tables 4, 16, 17, 18, 20, 21, 24 and 26 of the
  code and hand calculations on UK sections.
- `engine`: section analysis with sectionproperties in `steelsnakes.engine.sections`:
    - `analyse_section()` works out A, I, i, W_el, W_pl, the principal axes, I_t, I_w, the shear centre and i_0
    - it takes a tabulated section, plain dimensions (e.g a welded I-section) or any sectionproperties geometry
      (e.g a plate girder, or a beam with a cover plate from `section_geometry()`)
    - it draws I/H, parallel flange channels, tees, angles, RHS/SHS, CHS and EHS from the UK, EU, US and US_METRIC
      tables, with the EN 10210-2, EN 10219-2 and AISC corner radii
    - `SectionAnalysis.to_properties()` returns the UK, EU, BS, US or US_METRIC table keys and units, for the
      `properties` of the checks; for US this includes ro and H of E4
- `engine`: `steelsnakes.engine.units`, with units of length powers and their aliases (`get_unit("cm^4")`), and the
  dimension and property units of every region's section tables (`LENGTH_UNITS`, `SECTION_TABLE_UNITS`).
- `base`: exports `SectionClass4Error`, `SectionDatabaseError` and the shared check models (`DesignCode`, `LimitState`,
  `SectionClass`, `Reference`, `UtilisationCheck`, ...); adds `get_US_Metric_factory()`.
- Docs: "Section Analysis" API page.
- Tests: `tests/test_engine.py`, which checks the engine against the tables of each region and against closed forms
  for welded and built-up sections; `tests/test_base.py`.

### Changed

- `BS`: `effective_plastic_modulus()` returns S for class 1 and 2 RHS and CHS, as it does for I-sections; before, every
  section other than UB, UC and UBP returned Z.
- `base`: `UtilisationCheck` sets `adequacy` from `utilisation` ("FAILS" above 1.0) when it is left out, as every
  code module does; before, it defaulted to "OK".
- `base`: `get_UK_factory()`, `get_EU_factory()` and `get_US_factory()` in `base.factory` return the regional factories
  (`UKSectionFactory`, ...) from the regional modules, instead of building their own.
- `base`: `materials.py` is an index of where each code's materials live (`EU.checks.uls.steel_material()`,
  `BS.checks.classification.design_strength()`, ...); `renders.py` no longer defines E and G, which it did not use
  and which disagreed with BS 5950 3.1.3 (G = 80 000 against E/2.6 = 78 846 N/mm²).

### Fixed

- `pytest.ini` used `[tool:pytest]`, so pytest ignored it; coverage and the 80% gate are now enforced.
- `base`: `find_section()` could silently return a different section for a typo, e.g `"254x146x30"` gave 254x146x37
  because it was as close as 254x146x31. A tie now raises `SectionNotFoundError` with both as suggestions.
- `base`: passing a string section type to `create_section()` crashed with `AttributeError`.
- `base`: EU supported types listed Sigma and Zed twice.
- `US`/`US_Metric`: `MT2.5X9.45` (`MT65X14.05`) could not be created; `MiscellaneousTee` was missing `WGi`.
- `EU`: HLZ sections reported `SectionType.HL`, and UPE sections reported `SectionType.PFC`.
- `UK`/`EU`: back-to-back angles used `()` as the default for `i_zz`, which the data holds as a dict of radius of
  gyration per spacing; it now defaults to an empty dict per instance.
- `EU`/`UK`: an axis-free `"bending"` stress pattern put all four RHS/SHS walls on the bending limits
  (72ε, 83ε, 124ε), which is unconservative for the flanges. It is now major-axis bending: the h walls are in bending
  and the b walls in compression, per Table 5.2 Sheet 1.
- `EU`/`UK`: the flange outstand c of rolled I/H sections and parallel flange channels now excludes the root radius,
  c = (b − tw − 2r)/2 and b − tw − r, per Table 5.2 Sheet 2 and as the tabulated cf/tf. Before, (b − tw)/2
  overstated c/t and could put a flange in a higher class than the code gives.
- `US`: the Table B4.1b case descriptions for cases 10, 11, 16, 18 and 21 did not match the Specification.
- `US_Metric`: the section unit comments said in, in² and lb/ft; the data is in SI.
- Docs: the US classification page's examples passed `context=`, `Fy=` and `ratio=`, which the API does not take.
- `base`: the US factory registered C and MC channels twice; `L2L_SLBB`'s comment was cut off; `list_properties()`
  said it printed the properties, and `find_section()` re-imported `json`.
