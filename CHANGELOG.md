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
