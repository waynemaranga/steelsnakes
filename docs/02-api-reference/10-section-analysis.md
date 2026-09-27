# Section Analysis (engine)

This page documents `steelsnakes.engine`, which works out the properties of a cross-section from its geometry. It
covers both the sections the regional modules tabulate and sections they do not, such as welded plate girders or a
universal beam with a cover plate. The finite element analysis is done by
[sectionproperties](https://sectionproperties.readthedocs.io), which is already a dependency.

The engine sits next to the regional modules, not above them. It reads their sections, converts its results into their
section-table keys and units, and those results go into their checks through `properties`.

!!! warning "Units and axes"
    The engine works in mm: A in mm², W in mm³, I and I_t in mm⁴, I_w in mm⁶. Dimensions are converted from the section
    tables on read, so US inches become mm. `to_properties(region)` converts back to a module's table units.
    Axes follow EN 1993-1-1 1.7: y-y is major (horizontal), z-z is minor (vertical), and u-u and v-v are principal.

!!! note "Coming later"
    Applying forces to a section (stress analysis) and member analysis (`steelsnakes.engine.analysis`) come later.
    `SectionAnalysis.model` keeps the sectionproperties `Section` for that.

## Module map

| Object | What it does |
|---|---|
| `analyse_section()` | Geometric, plastic and warping properties of a section, a set of plain dimensions, or any sectionproperties geometry |
| `section_geometry()` | The geometry of a tabulated section, drawn from its dimensions in mm, to plot or to build on |
| `SectionAnalysis` | The results in mm; `.to_properties(region)` gives them in `"UK"`, `"EU"`, `"BS"`, `"US"` or `"US_METRIC"` table keys and units |
| `engine.units` | `Unit`, `get_unit()` (with aliases such as `cm4`, `cm^4`, `cm**4`), `LENGTH_UNITS` and `SECTION_TABLE_UNITS` |

## Sections it draws

| Family | Section types | Drawn with |
|---|---|---|
| I and H | UB, UC, UBP, IPE, HE, HL, HLZ, HD, HP, W, M | Root radius r; for US shapes, r = kdes − tf |
| Channels | PFC, UPE | Parallel flanges, root radius r |
| Tees | WT, MT | Root radius r = kdes − tf |
| Angles | L_EQUAL, L_UNEQUAL | Long leg vertical. UK/EU use root radius r_1 and toe radius r_2 (capped at t). US use root radius kdes − t |
| RHS and SHS | HFRHS, HFSHS, CFRHS, CFSHS, HSS_RCT, HSS_SQR | Corner radii: EN 10210-2 r_o = 1.5t, r_i = t (hot finished); EN 10219-2 r_o = 2t, 2.5t or 3t (cold formed); AISC r_o = 2t_des |
| CHS | HFCHS, CFCHS, HSS_RND, PIPE | Outside diameter and t (t_des for US) |
| EHS | HFEHS | A true ellipse |

The engine does not draw these yet:

- Tapered flanges (UPN, S, C, MC, ST), because the tables do not give the flange slope and toe radius.
- Back-to-back angles, Sigma and Zed sections, and the IN sections.

For these, `section_geometry()` raises `NotImplementedError`. Pass their geometry to `analyse_section(geometry=...)`
instead.

## Examples

```python
from steelsnakes.EU import IPE
from steelsnakes.engine import analyse_section

analysis = analyse_section(IPE("IPE-300"))
print(analysis.A, analysis.I_y, analysis.I_t, analysis.I_w)  # 5382 mm², 8.358e7 mm⁴, 1.98e5 mm⁴, 1.24e11 mm⁶
print(analysis.to_properties("EU"))  # {"A": 53.82, "I_yy": 8358.4, ..., "I_t": 19.81, "I_w": 0.1242} in cm², cm⁴, dm⁶
```

A welded I-section from its dimensions, in the UK table keys:

```python
from steelsnakes.base.sections import SectionType
from steelsnakes.engine import analyse_section

girder = analyse_section(
    section_type=SectionType.UB,
    properties={"h": 1040.0, "b": 300.0, "tw": 10.0, "tf": 20.0, "r": 0.0},
    region="UK",
)
print(girder.W_pl_y)  # 8.62e6 mm³, 2·300·20·510 + 10·1000²/4
```

A universal beam with a cover plate on its top flange:

```python
from sectionproperties.pre.library import rectangular_section
from steelsnakes.UK import UB
from steelsnakes.engine import analyse_section, section_geometry

beam = section_geometry(UB("457x191x67"))
plate = rectangular_section(d=15.0, b=250.0).align_center(beam).align_to(beam, on="top")
built_up = analyse_section(geometry=beam + plate)
```

Engine properties in a regional check, here the EN 1993-1-1 6.2.5 bending resistance of a UB:

```python
from steelsnakes.base.sections import SectionType
from steelsnakes.EU.checks.uls import check_bending
from steelsnakes.UK import UB
from steelsnakes.engine import analyse_section

ub = UB("457x191x67")
dimensions = {key: ub.get_properties()[key] for key in ("h", "b", "tw", "tf", "r", "d")}
properties = {**dimensions, **analyse_section(ub).to_properties("UK")}
print(check_bending(section_type=SectionType.UB, properties=properties, fy=355.0).M_c_Rd)
```

## Validation

The tests check the engine against the section tables of every region it draws, within 1.5% for A, I, W and i and
within 4% for I_t and I_w. The tables work I_t and I_w out from closed-form approximations; the engine analyses the
drawn shape, fillets included. Sampled across the tables, most families agree with their tables to within 1% on A, I
and W_pl. There are some exceptions:

- A few small US shapes, such as M4X4.08 and HP8X36, differ by up to 4%, because AISC gives kdes, not r.
- Some US pipes differ by up to 3.5%.
- The EU `L_EQUAL` 200x200x16.0 row gives I_yy = 2430 cm⁴, where the UK table and the geometry give 2340 cm⁴.

The welded I-section, the mono-symmetric plate girder and the cover-plated beam are checked against their closed forms.
The plate girder's I_w is compared with the thin-walled h_s²·I_f1·I_f2/(I_f1 + I_f2).

## API objects

::: steelsnakes.engine.sections

::: steelsnakes.engine.units
