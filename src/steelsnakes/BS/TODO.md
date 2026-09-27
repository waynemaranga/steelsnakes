# BS 5950 TODO

Backlog and status of `steelsnakes.BS`, the BS 5950-1:2000 module (BSI 05-2001, with Corrigendum No. 1).

The code is at `codes/BS 5950-1-2000 Structural Use of Steelwork in Building (Rolled & Welded Sections).pdf`.
The general wishlist stays in the repository's `TODO.md`; this file only tracks BS 5950.

Tick an item with ` _done: ..._`, as in `TASKS.md` and `TODO.md`.

## How to work an item

Every item below is finished only when all of these hold:

- [ ] **Clause comments.** The code follows the house style: `Optional[...]`, annotated locals, trailing clause and unit
  comments, and a module `__main__` that ends in `print("🐬")`.
- [ ] **Units.** Use kN, kNm, N/mm² and mm. Section properties stay in the table units: A cm², Z and S cm³, I and J
  cm⁴, r cm, H dm⁶.
- [ ] **Arguments and results.** Arguments carry their unit, e.g `Fc_kN`, `LE_mm`, `An_cm2`. Results are pydantic
  models with a unit comment on every field, a `UtilisationCheck` when the action is given, and a `Reference` to the
  clause.
- [ ] **Properties.** `properties=` accepts both the UK table keys and BS notation, through `_section_data()` in `uls.py`.
- [ ] **Tests.** Tests go in `tests/test_BS_uls.py` or `tests/test_BS_sls.py`, function-based with `-> None`. They
  reproduce a table of the code or an independent worked example, never only the implementation's own numbers.
- [ ] **Exports.** Public names go in `BS/checks/__init__.py`; the main entry points also go in `BS/__init__.py`.
- [ ] **Docs.** Add a row to the module map in `docs/02-api-reference/09-bs-member-checks.md`, and an example if the
  item is user-facing.
- [ ] **Changelog.** Add a line under the open section of `CHANGELOG.md`.

### Reading the PDF

- `pdftotext -layout` interleaves the lines of stacked equations, so fractions come out scrambled.
- `pdftotext -raw <pdf> out.txt`, then `cat -v`, gives the equation tokens in order.
- The Symbol-font glyphs decode as follows:
    - `M-<` is ε, `M-F` is λ, `M-6` is β, `M-Lb` is φb
    - `M--` is a minus sign, `M-$` a fraction slash, `M-#` is ≤
    - `M-h M-x` and `M-f M-v` are bracket pieces
- Page images cannot be rendered on this machine (no `pdftoppm`).
- Cross-check every decoded formula against a table of the code or a hand calculation before trusting it.
- Charts (Figures E.1, E.2, G.4 to G.6) cannot be read from the text at all.

## Done

- [x] 3.5 classification, Tables 9, 11 and 12, 3.5.3 compound flanges, 3.5.5 r1 and r2
  _done: `checks/classification.py`, alpha-9_
- [x] 3.5.6 effective plastic modulus: 3.5.6.2 I and H, 3.5.6.3 RHS, 3.5.6.4 CHS
  _done: `effective_plastic_modulus()`, `_rhs()`, `_chs()`, alpha-10_
- [x] 2.4.1 Table 2 load factors and load combinations 1 to 3 _done: `load_factor()`, `factored_load()`_
- [x] 2.4.2 notional horizontal forces, the 1 % minimum wind load, λcr = h/200δ, non-sway or sway-sensitive, kamp
  _done: `check_sway_stability()`_
- [x] 4.3.2, 4.3.3 and 4.7.1.2 restraint forces, kr _done: `lateral_restraint_forces()`, `restraint_reduction_factor()`_
- [x] 2.4.4 brittle fracture from the t1 formula, with Tables 3 and 7
  _done: `check_brittle_fracture()`; reproduces Tables 4 and 5_
- [x] 2.4.5 tie forces _done: `tie_force()`_
- [x] 3.4 net area with staggered holes (Figure 3), Ke _done: `net_area()`, `effective_net_area_coefficient()`_
- [x] 3.6.2.2, 3.6.2.3, 3.6.4, 3.6.5 and 3.6.6 effective properties
  _done: `effective_section()`, for doubly symmetric I, H, RHS and SHS, equal angles, CHS, else pyr_
- [x] 4.2.3 shear area and Pv; 4.2.4 limit 0.7py _done: `check_shear()`, `shear_area()`_
- [x] 4.4.5.2 simple shear buckling Vw = d t qw, H.1 qw, H.2 qcr, 4.4.5.4 Vcr
  _done: `check_shear()`; reproduces Table 21_
- [x] 4.2.5 moment capacity, low and high shear, the 4.2.5.1 limit of 1.2pyZ or 1.5pyZ; 4.2.5.4 notched ends;
  4.2.5.5 bolt holes _done: `check_bending()`_
- [x] 4.3.5 Tables 13 and 14 effective lengths _done: `beam_effective_length()`, `segment_effective_length()`,
  `cantilever_effective_length()`_
- [x] 4.3.6 lateral-torsional buckling, covering:
  _done: `check_lateral_torsional_buckling()`; reproduces Tables 16, 17 and 20_
    - Table 18 mLT and B.2.1/B.2.2 pb
    - λLT = u v λ βW^0.5, with B.2.3 u and x
    - the 4.3.7 simple method, which is u = 0.9 and x = D/T
    - RHS to Table 15 and B.2.6, B.2.7 plates
    - B.2.9 angle slenderness (helper only)
    - 4.3.8.3 simplified method for equal angles
- [x] 4.5.2.1 bearing and 4.5.3.1 buckling of unstiffened webs _done: `check_web_bearing()`_
- [x] 4.6 tension, per-element Ae, 4.6.3 simple ties _done: `check_tension()`_
- [x] 4.7 compression: Tables 22 to 24, Annex C, class 4 pcs, the 40 mm to 50 mm average
  _done: `check_compression()`; reproduces Table 24_
- [x] 4.7.7 simple columns _done: `check_simple_column()`_
- [x] 4.7.10 and Table 25 angle, channel and T struts _done: `check_angle_strut()` and the slenderness helpers_
- [x] 4.8.2 tension with moments (4.8.2.2, 4.8.2.3 with I.2) _done: `check_tension_and_bending()`_
- [x] 4.8.3 and 4.9 compression with moments _done: `check_compression_and_bending()`_
    - 4.8.3.2 cross-section capacity
    - 4.8.3.3.1 simplified method
    - 4.8.3.3.2 I and H, 4.8.3.3.3 CHS and RHS
    - I.1 stocky members, I.2 reduced plastic moduli
    - Table 26 m factors
- [x] I.4.3 simplified method for single equal angles _done: `check_single_angle_compression_and_bending()`_
- [x] B.3, C.3 and I.5 internal moments _done: `strut_action_moment()`, `lateral_torsional_internal_moment()`,
  `amplified_moment()`, `internal_moment_at()`_
- [x] 2.5 serviceability loads, Table 8 deflections, 2.5.3 vibration (SCI P076 3 Hz)
  _done: `checks/sls.py`_

## Open decisions

These need an answer before or during the work below.

- [ ] **Web under axial force and minor axis moment.**
    - `classify_section(..., "bending-minor-axis", Fc_kN=...)` puts the web of an I or H section in the Table 11
      "axial compression" row. The section is then class 3 at best, and I.1 (stocky) cannot be used.
    - Table 11's "generally" row, with r1 = Fc/(d t pyw) clamped to 1, would give class 1 and 2 limits.
    - This is conservative, and `tests/test_BS_classification.py::test_minor_axis_bending_skips_web_unless_axial_compression_acts`
      pins the current behaviour. Decide whether to change it.
- [ ] **4.2.5.1 default.** `simple_span=True` (1.2pyZ) is the default everywhere, including beam-columns and continuous
  members. It is conservative, and matches the SCI Blue Book tables. Keep it, or default to False (1.5pyZ) in the
  beam-column checks?
- [ ] **Net area default.** `check_tension()` with only `An_cm2` does not apply Ke (Ae = An), since the holes may all be
  in one element. Keep it conservative, or treat An as one element (Ae = min(Ke·An, Ag))?
- [ ] **Table 4 typo?** The S 460 QL row at -45 °C reads 21 mm, but the code's own t1 formula gives 31.8 mm. The same
  row matches the formula at every other temperature, and "66 55 46 38 21" is also the S 355 J2 row, so it looks
  copied. The tests avoid that cell; confirm against a later print of the code.
- [ ] **Validation sources.** The code's tables cover pb, pc, qw and t1 only. Plate girders, Annex G and connections
  need independent worked examples, e.g:
    - SCI P-202, Steelwork design guide to BS 5950-1, Volume 1 (reference [5] of the code)
    - the SCI worked examples to BS 5950
    - Steel Designers' Manual (6th edition, BS 5950)
    - SCI P-252 (single-span portal frames to BS 5950-1:2000) and P-292 (in-plane stability of portal frames, reference
      [10]) for Annex G and Section 5

  Put any you have in `codes/`.
- [ ] **Scope.** Which of plate girders, portal frames (Section 5 with Annex G) and connections (Section 6) are needed?
  The plan below assumes plate girders yes, the other two to be confirmed.

## Phase 1: Welded (plate-built) I-section

Prerequisite for Phase 3 and for every unequal-flange item. Size: M.

Today every check reads the rolled UK tables. `welded=True` only changes the strut and pb curves (and py - 20 for pc);
classification still uses the rolled limits, and properties cannot be built from plates.

- [ ] **The section class.** A `WeldedISection` (name open), or a function returning a `properties` dict, built from:
    - top flange Bt x Tt and bottom flange Bb x Tb (equal by default)
    - web d x t, and the weld leg (optional, for the plate girder rules)
    - pyf and pyw separately (hybrid girders; 3.5.5 needs pyw <= pyf)
    - `SectionType`: reuse UB, or add a welded type in `base/sections.py`; decide which (affects `_family()`)
- [ ] **Computed properties.**
    - D, A, the elastic centroid, Ix, Iy, Zx (top and bottom), Zy, rx, ry
    - the plastic neutral axis, Sx, Sy
    - J ≈ Σ bt³/3, H of a monosymmetric I
    - hs = D - (Tc + Tt)/2
    - u and x from B.2.3 or B.2.4.1; x also by the welded alternative, (D - T)[(2BT + dt)/(2BT³ + dt³)]^0.5
- [ ] **Unequal flanges (4.3.6.7).** The flange ratio η = Iyc/(Iyc + Iyt), and the monosymmetry index ψ exactly from
  B.2.4.1 (not only the 4.3.6.7 approximation).
- [ ] **Classification.** Welded Table 11 rows: OUTSTAND_FLANGE_WELDED (8ε, 9ε, 13ε) and welded webs. The classifier
  already has the element kinds; a geometry adapter for the new section type is needed in
  `classification._geometry()`.
- [ ] **Unequal flanges in the checks.**
    - 3.5.5 b) r1, r2 (already in `stress_ratios(case="unequal-flanges")`)
    - 4.2.5.3 Sv = S - Sf
    - 4.3.6.3 and B.2.4.2 double-curvature bending: Mx,1 <= Mb,1 and Mx,2 <= Mb,2, one for each flange in compression
- [ ] **3.6.3 singly symmetric class 4 sections.** The additional moment Fc·eN from the centroid shift of the effective
  section, in 4.2, 4.3, 4.7 and 4.8. This also lets channels leave the 3.6.5 fallback.
- [ ] **Cover plates.** Table 23 rows for rolled sections with welded flange cover plates (Figure 14, U/B ranges), and
  compound flanges (3.5.3) as a builder input.
- [ ] **I.3 asymmetric members.** The stress-summation form of the linear interactions (4.8.2.2, 4.8.3.2a, 4.8.3.3.1),
  using the section modulus of each fibre.
- [ ] **Tests.** Properties against an SCI welded section table or hand calculation. A doubly symmetric plate I built to
  the dimensions of a UB must reproduce that UB's A, Ix, Zx, u and x within tabulation error (no root radius, so
  expect small differences).

## Phase 2: Quick wins

Small, self-contained, low risk. Size: S each.

- [ ] **Unequal angles in bending (4.3.8.2, B.2.9.3, I.4.2).**
    - The UK tables already carry `phi_a_min`, `phi_a_max` and `psi_a` for L_UNEQUAL, and `phi_a` for L_EQUAL.
    - Compute Zu and Zv from the leg geometry: toe and heel coordinates, `tan_alpha` and the centroid `c_y`/`c_z`
      from the tables.
    - Resolve moments into u-u and v-v; Mb about u-u from λLT = 2.25νa(φa λv)^0.5 and B.2.1; Mc about v-v; then 4.9
      or I.4.2.
    - Settle which of `phi_a_min` and `phi_a_max` applies (smaller or larger Zu) from the SCI table notes.
    - This replaces the `NotImplementedError` in `check_lateral_torsional_buckling()` for unequal angles.
- [ ] **Annex D effective lengths (simple structures).**
    - D.1 single-storey side and valley columns, Figures D.1 to D.5: x-x and y-y effective lengths as multiples of L,
      L1, L2, L3, with and without crane gantries and intermediate restraint.
    - D.1.2 variations: 0.85L becomes 1.0L when the base is not restrained in direction; tops held in position go to
      Table 22 a).
    - D.2 internal platform floors: Table D.1.
    - Encode as lookups like Table 22, e.g `simple_column_effective_length(case, axis, L, L1=..., ...)`.
    - The figures are drawings: read the effective-length labels from the text extraction and check each against the
      figure captions.
- [ ] **4.13 column bases.**
    - 4.13.1: bearing strength 0.6fcu.
    - 4.13.2.1: effective area as a strip c around the column profile (Figure 15), from the axial force and 0.6fcu.
    - 4.13.2.2: tp = c(3w/pyp)^0.5, with pyp from Table 9 for the plate thickness; iterate, since py depends on tp.
    - 4.13.2.3 applied moments, 4.13.2.4 holding-down bolts (6.6), 4.13.3 connection of the baseplate: decode, then
      implement or document as not covered.
    - `check_base_plate(section, Fc_kN, fcu_mpa, plate B x L, pyp=...)`.
- [ ] **4.12.4 empirical purlins and side rails.**
    - Only hollow sections and hot rolled angles qualify.
    - 4.12.4.2 conditions: S 275 minimum, spans, slopes, loads.
    - Table 27 purlin and Table 28 side rail minimum Z, D and B, as fractions of W L and of L.
    - Decode Tables 27 and 28, which are in the plain extraction near "Table 27 -- Empirical values for purlins".
- [ ] **Annex F frame stability.**
    - F.2 deflection method: λcr = 1/(200φmax), with sway index φ = (δu - δL)/h per storey. This is the same number as
      `check_sway_stability()`: add the F.2 reference, or an alias taking the top and bottom deflections.
    - F.3 partial sway bracing, which is linked to E.3.
- [ ] **4.10 lattice frames and trusses.**
    - Read the clause first: it sets effective lengths of chord and web members, and when joint eccentricity and
      secondary moments may be ignored.
    - Likely a helper next to `effective_length()`.
- [ ] **Calculation sheets.** `render_*()` → `base.renders.CheckBlock` for the main ULS results, like
  `render_classification()`. Optional; the EU and US modules have none either, so decide across codes first.

## Phase 3: Plate girders (4.4, 4.5, Annex H)

Needs Phase 1. Size: L.

- [ ] **4.4.2 Design strength.** pyf and pyw separately; pyw <= pyf.
- [ ] **4.4.3 Dimensions of webs and flanges.** `check_web_thickness()`:
    - 4.4.3.2 serviceability:
        - t >= d/250 without intermediate stiffeners, or with stiffener spacing a > d
        - t >= (d/250)(a/d)^0.5 with a <= d
        - longitudinal stiffeners are out of scope (BS 5400-3)
    - 4.4.3.3 compression flange buckling into the web:
        - t >= (d/250)(pyf/345) without intermediate stiffeners, or with a > 1.5d
        - t >= (d/250)(pyf/455)^0.5 with a <= 1.5d
- [ ] **4.4.4 Moment capacity.**
    - 4.4.4.1: d/t <= 62ε, use 4.2.5 (`check_bending()`).
    - 4.4.4.2 a) low shear, Fv <= 0.6Vw: 4.2.5.
    - 4.4.4.2 b) high shear, "flanges only": Mf, from the flanges alone, each at a uniform stress <= pyf; the web then
      carries the shear only.
    - 4.4.4.2 c) high shear, general method: the web designed to H.3 for the shear together with any moment beyond Mf,
      provided the applied moment is within the low shear capacity.
    - 4.4.4.3 axial force: Mf from the flanges resisting the moment and the axial force together.
    - Figure 12 (interaction of Fv/Vw with M) sets the logic; reproduce it as a test.
    - `check_bending()` currently only notes "4.4.4 not implemented" for d/t > 70ε; replace the note with this.
- [ ] **4.4.5.3 More exact shear buckling (tension field).**
    - Vb = Vw if ff = pyf; else Vb = Vw + Vf <= Pv.
    - Vf = Pv(d/a)[1 - (ff/pyf)²]/(1 + 0.15Mpw/Mpf), decoded and not yet cross-checked; check against Figure 12 b) or a
      worked example.
    - Mpf is the plastic moment of the smaller flange about its own equal-area axis perpendicular to the web (with pyf);
      Mpw is the same for the web (with pyw); ff is the mean longitudinal stress in the smaller flange.
- [ ] **4.4.5.4 End anchorage and H.4.**
    - Anchorage is needed unless Vw = Pv, or Fv <= Vcr (Vcr is already done).
    - Otherwise the anchor force Hq (Figure H.1), with the end post designed as:
        - a single stiffener end post (H.4.2)
        - a twin stiffener end post (H.4.3)
        - an anchor panel (H.4.4)
    - 4.4.5.5: panels with openings > 10 % of the smaller panel dimension go to 4.15, and cannot be anchor panels.
- [ ] **4.4.6 Intermediate transverse stiffeners.**
    - 4.4.6.2 spacing (4.4.3); 4.4.6.3 outstand (4.5.1.2).
    - 4.4.6.4 minimum stiffness: Is >= 0.75d·tmin³ for a/d >= √2, else 1.5(d/a)²d·tmin³. tmin is the minimum web
      thickness for the actual spacing a; the ≥/< sign on √2 is garbled in the extraction, so confirm it.
    - 4.4.6.5 additional stiffness: Iext = Fx·ex·D²/(E t) for eccentric transverse forces, 2Fh·D³/(E t) for lateral
      forces at the compression flange.
    - 4.4.6.6 buckling resistance: Fq = V - Vcr <= Pq, with V the larger shear of the two adjacent panels and Pq from
      4.5.5. Stiffeners with external loads also meet 4.5.3.3 and:
        - (Fq - Fx)/Pq + Fx/Px + Ms/Mys <= 1 if Fq > Fx
        - Fx/Px + Ms/Mys <= 1 otherwise
        - Ms = Fx·ex + Fh·D
    - 4.4.6.7 connection to the web: decode.
- [ ] **4.5 Stiffeners.**
    - 4.5.1.2 maximum outstand 19εts; between 13εts and 19εts, design on an outstand of 13εts. Add this as a validation
      helper.
    - 4.5.1.3 stiff bearing length b1 from Figure 13, e.g `stiff_bearing_length(...)`. `check_web_bearing()`
      currently takes b1 as input.
    - 4.5.2.2 bearing stiffeners: Ps = As,net·py, for the force beyond Pbw; the smaller py where the web and the
      stiffener differ.
    - 4.5.3.2 loads applied between stiffeners: decode.
    - 4.5.3.3 load-carrying stiffeners: Px = As·pc, where:
        - As is a cruciform: the stiffeners (outstand per 4.5.1.2) plus 15t of web each side of their centreline
        - pc is from strut curve c, with r about the axis parallel to the web, and py the lower of web and stiffener
        - there is no 20 N/mm² reduction unless the stiffeners are welded sections
        - LE = 0.7L if the loaded flange is restrained against rotation in the plane of the stiffener, else 1.0L,
          with L the stiffener length clear between the flanges
        - also check them as bearing stiffeners (4.5.2.2)
        - a stiffener loaded by a compression member without lateral restraint is part of that member (C.3)
    - 4.5.4 tension stiffeners; 4.5.5 intermediate stiffeners (links to 4.4.6).
    - 4.5.6 diagonal stiffeners.
    - 4.5.7 torsion stiffeners at supports: Is >= 0.34αs·D³·Tc, where:
        - αs = 0.006 for λ <= 50, 0.3/λ for 50 < λ <= 100, and 30/λ² for λ > 100
        - λ = LE/ry of the member
        - Tc is the maximum compression flange thickness in the span
    - 4.5.8 to 4.5.10 connections and length of stiffeners: weld design forces. These may wait for Section 6.
- [ ] **H.3 Web under combined effects.**
    - H.3.2 ρ from Fv/Vw (the same formula as `shear_reduction_factor()`, with Vw).
    - H.3.3 sections other than RHS:
        - H.3.3.1 shear, moment and axial compression, for class 1 to 3 webs and for class 4 webs
        - H.3.3.2 shear, moment and axial tension
        - H.3.3.3 shear, moment and edge loading
    - H.3.4 RHS: H.3.4.1 compression, H.3.4.2 tension.
    - The web actions are an axial force Fcw or Ftw at mid-depth of the web plus a moment Mw about it. For RHS and welded
      boxes, include the strut action (C.3) and amplification (I.5.1) moments, which are already implemented.
    - The interaction expressions are garbled in `-layout`: decode from `-raw`.
- [ ] **3.6.2.4 Slender webs in bending, done fully.**
    - `slender_web_effective_width()` exists; `_effective_modulus()` raises for slender webs, and callers fall back
      to 3.6.5.
    - Build the effective section: 0.4beff next to the compression flange, 0.6beff next to the elastic neutral axis
      of the effective section (Figure 9), with fcw and ftw from the section with the web fully effective and the
      effective compression flange.
    - Iterate until the neutral axis settles.
- [ ] **Validation.**
    - Table 21 already covers qw.
    - Add at least one full plate girder worked example: an SCI or Steel Designers' Manual girder with and without
      intermediate stiffeners, covering 4.4.3, 4.4.4 b) and c), 4.4.5.3, H.4 and the bearing stiffener.

## Phase 4: Annex E (effective lengths in continuous structures)

Size: M.

- [ ] **E.1: the charts problem.** The effective length ratio LE/L comes from Figure E.1 (non-sway) or Figure E.2
  (sway), which are charts with no formula in the text. Options:
    - the closed-form approximations of ENV 1993-1-1 Annex E (Wood's charts), labelled as not BS text:
        - non-sway: LE/L = [1 + 0.145(k1 + k2) - 0.265k1k2]/[2 - 0.364(k1 + k2) - 0.247k1k2]
        - sway: LE/L = {[1 - 0.2(k1 + k2) - 0.12k1k2]/[1 - 0.8(k1 + k2) + 0.6k1k2]}^0.5
    - or E.6 only (see below), which needs λcr
    - recommended: both, with the chart approximation flagged in the docstring and docs
- [ ] **E.2 limited frame method.** Distribution factors k = ΣKc/(ΣKc + ΣKb) for the ends of a column-length (Figure E.3).
    - E.2.2 beam stiffness Kb: Table E.1 (buildings with floor slabs), Table E.2 (general), Table E.3 (beams under axial
      compression).
    - E.2.3 base stiffness; E.2.4 column stiffness.
    - k = 1 at an end whose moment exceeds 90 % of Mr.
    - Members missing or not rigidly connected count as zero stiffness.
- [ ] **E.3 partial sway bracing.**
    - Infill wall panels: E.3.2 wall panels, E.3.3 relative stiffness kp, E.3.4 stiffness of panels.
    - Figures E.4 and E.5 (kp = 1, 2) are charts too.
- [ ] **E.4 other compression members.** E.4.1 other rectilinear frames; E.4.2 effect of axial force in the restraining
  members.
- [ ] **E.5 mixed frames.** Simple columns braced by rigid frames: increase the in-plane effective lengths of the sway
  columns.
- [ ] **E.6 from λcr.** The effective length from the elastic critical load factor and the vertical loads on the whole
  structure; λcr from `check_sway_stability()` or F.2.
- [ ] **Tests.** The ENV formulas against values read from Figures E.1 and E.2 by hand; E.6 against a hand calculation.

## Needs a scope decision

### Portal frames: Section 5, 5.3, Annex G and B.2.5

Size: XL, plus frame analysis, which the library does not have (`engine/analysis` is a stub).

- [ ] **B.2.5 tapered or haunched members.** mLT = 1.0, Mb checked along the segment with the properties at each point,
  and the slenderness multiplied by n = (1.5 - 0.5Rf) >= 1.0 for Rf >= 0.2, where Rf is the flange ratio. Decode Rf.
- [ ] **Annex G: members with one flange laterally restrained.**
    - This is the out-of-plane stability of portal rafters and columns, with purlins or rails on the tension flange.
    - G.1.2 types of haunching; G.1.3 section properties; G.1.4 procedure.
    - G.2 lateral buckling resistance:
        - G.2.1 uniform members; G.2.2 tapered or haunched members
        - G.2.3 slenderness λTC; G.2.4 equivalent slenderness λTB, for uniform members (G.2.4.1) and haunched or
          tapered members (G.2.4.2)
        - G.2.5 taper factor, Figures G.3 and G.4 (νt, a chart)
    - G.3 lateral restraint next to plastic hinges: G.3.3 segments next to a hinge, limiting length Lk (G.3.3.3).
    - G.4 non-uniform moments: G.4.2 mt (Table G.1, Figures G.5 and G.6); G.4.3 nt.
    - The charts need a digitisation or formula source.
- [ ] **5.3 out-of-plane stability for plastic analysis.** 5.3.2 restraints at plastic hinges; 5.3.3 the segment next to
  a hinge (Lm); 5.3.4 segments with one flange restrained (links to G.3); 5.3.5 three- and two-flange haunches.
- [ ] **Sections 5.1, 5.2 and 5.4 to 5.7.**
    - 5.1.2 pattern loading rules and 5.1.3 base stiffness (rigid, pinned, 20 % semi-rigid): helpers.
    - 5.2.3 conditions for plastic analysis: class 1 at hinges, fu/fy, stiffeners at hinges. This is a checker.
    - 5.5.4 portal in-plane stability:
        - 5.5.4.2 sway-check method (h/1000 deflection rule, and the gravity-load formula)
        - 5.5.4.3 snap-through (λr)
        - 5.5.4.4 amplified moments
        - 5.5.4.5 second-order analysis
    - 5.6 and 5.7 multi-storey frames, 5.7.3.2 frame stability check.
    - Most of this needs an analysis model; the formula checks (sway-check, snap-through, 5.7.3.2) can stand alone.
- [ ] **Validation.** SCI P-252 and P-292 portal frame worked examples, or equivalent.

### Connections: Section 6

Size: L. The UK module already ships `UK/data/BOLT_PRE_88.json`, `BOLT_PRE_109.json` and `WELDS.json`.

No code in steelsnakes has connections yet: EN 1993-1-8 was skipped for EU and UK, and the US module stops at Chapter H.
Design one connections layer (bolt groups, weld groups, components) across codes before starting, and consider doing
EN 1993-1-8 first, since the UK designs to the Eurocode.

- [ ] **6.1 General.** 6.1.7 vibration, load reversal and fatigue; 6.1.8 splices (compression, tension, beams);
  6.1.9 column web panel zone.
- [ ] **6.2 Bolts.**
    - 6.2.1 spacing: minimum, maximum in unstiffened plates.
    - 6.2.2 edge and end distances: Table 29, oversize holes, maximum distances.
    - 6.2.3 effect of bolt holes on shear capacity.
    - 6.2.4 block shear (Figure 22).
- [ ] **6.3 Non-preloaded bolts.**
    - 6.3.1 effective areas; 6.3.2 shear capacity with Table 30, reduced for:
        - packing (6.3.2.2)
        - large grip lengths (6.3.2.3)
        - kidney-shaped slots (6.3.2.4)
        - long joints (6.3.2.5)
    - 6.3.3 bearing, of the bolt (Table 31) and of the connected part (Table 32 pbs).
    - 6.3.4 tension: Table 34, simple and more exact methods (prying), combined shear and tension.
    - Tables 33 and 36 hole dimensions.
- [ ] **6.4 Preloaded (HSFG) bolts.** 6.4.2 slip resistance; 6.4.3 slip factors (Table 35); 6.4.4 capacity after slip;
  6.4.5 combined shear and tension; 6.4.6 holes.
- [ ] **6.5 Pin connections.** Pin-ended tension members (Figure 26); pin plates; pins in shear, bearing and bending.
- [ ] **6.6 Holding-down bolts.** Links to 4.13.2.4.
- [ ] **6.7 Welded connections.** 6.7.1 through-thickness tension; 6.7.2 details (end connections, single and intermittent
  fillets); 6.7.3 hollow section details; 6.7.5 connections to unstiffened flanges (Figure 28).
- [ ] **6.8 Fillet welds.** Effective throat (Figure 29), deep penetration (Figure 30), Table 37 pw, and the simple
  and directional methods (Figure 31).
- [ ] **6.9 Butt welds.** Full and partial penetration (Figure 32).
- [ ] **Validation.** SCI P-212 (Joints in steel construction: simple connections) and P-207 (moment connections) are
  the BS 5950 references.

### Gantry girders: 4.11

Size: S to M, mostly rules around existing checks.

- [ ] 4.11.1 load combinations, and 2.4.1.3 dynamic allowances (2.2.3).
- [ ] 4.11.2 crabbing of the trolley (loading classes Q1 to Q4 of BS 2573).
- [ ] 4.11.3 lateral-torsional buckling with the destabilizing wheel loads and the horizontal loads on the top flange.
  Check that `check_compression_and_bending()` covers it, or add a wrapper.
- [ ] 4.11.4 local compression under wheels; 4.11.5 welded girders.
- [ ] Table 8 c) crane girder deflections are already in `sls.py`.

## Won't do unless asked

- [ ] **4.14 cased sections.** 4.14.2 cased columns, 4.14.3 in bending, 4.14.4 in axial force and moment. Niche today;
  the ry increase and the concrete contribution are simple if needed.
- [ ] **4.15 web openings and castellated beams.** 4.15.2 to 4.15.5 point to SCI P-068 and P-100. The simple rules
  (isolated circular unreinforced openings, 4.15.2.1) could be a small helper.
- [ ] **4.16 separators and diaphragms.** Detailing rules only.
- [ ] **4.17 eccentric loads on beams.** Torsion, pointing to SCI P-057; would share work with EN 1993-1-1 6.2.7.
- [ ] **Lateral-torsional buckling of T-sections (B.2.8).** There are no T-sections in the UK tables. The formulas
  (u, v, w, ψ, H of a T) are decoded in the PDF text if tees are ever added.
- [ ] **Section 7 loading tests, Annex A (safety format), 3.3 castings and forgings.**

## Housekeeping

- [ ] **`BS/checks/classification.py.md`.** The superseded draft carries the 1990 Table 7 limits and wrong S460 py
  values. Delete it; `docs/02-api-reference/06-bs-classification.md` mentions it in a warning, so update that warning.
- [ ] **`BS/data/UC.json`.** A BS-notation copy (D, B, t, T, I_xx) of the UK UC table, used only by
  `test_BS_classification.py` for dictionary input. Keep it as a test fixture (move it to `tests/`?), or generate BS
  notation tables for every section type.
- [ ] **Docstring warnings.** The `a, b: ...` combined-Args idiom in `uls.py` gives about 29 griffe warnings (and 1 in
  `sls.py`). This matters only if strict documentation builds are adopted across the repo.
- [ ] **Naming.** Check names against the other codes before 1.0: `check_bending()` is BS "moment capacity" (Mc);
  `check_simple_column()`; `effective_length()` (Table 22) vs `beam_effective_length()` (Table 13).
- [ ] **One bending entry point.** An `analyse_member()` or `check_member()` that runs 4.2, 4.3 and 4.8 together from
  forces, lengths and restraint descriptions, like a Blue Book member table. Decide the API across codes first.
