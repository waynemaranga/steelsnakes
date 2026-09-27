# API Reference

This reference is intentionally **lean**.

Use it to answer three questions quickly:

1. **Where does data come from?** `SectionDatabase`
2. **How do I get a section object?** `SectionFactory`
3. **Where do classification checks live?** Regional `checks` modules

/// card | Core architecture
`steelsnakes` currently has a practical internal architecture:

- **data files** hold section properties
- **database classes** load and search them
- **factory classes** build section objects
- **regional section classes** expose geometry/properties
- **regional checks** perform code-specific verification
///

## Mental model

```mermaid
flowchart LR
    A[JSON section tables] --> B[SectionDatabase]
    B --> C[SectionFactory]
    C --> D[Regional section class\nUB / IPE / W / HSS]
    D --> E[Checks module\nEU / UK / US]
    E --> F[Classification or design result]
```

## Package layout

| Layer | Main modules | Why it exists |
|---|---|---|
| Shared core | `steelsnakes.base.sections`, `steelsnakes.base.database`, `steelsnakes.base.factory` | Common section typing, data loading, lookup, and object creation |
| Regional data | `steelsnakes.<region>.data` | Region-specific section tables |
| Regional sections | `steelsnakes.<region>.sections` | Concrete classes such as `UB`, `UC`, `IPE`, `W`, `HSS` |
| Regional checks | `steelsnakes.EU.checks`, `steelsnakes.UK.checks`, `steelsnakes.US.checks`, `steelsnakes.BS.checks` | Code-specific classification and design helpers |

## What to read next

- **Section Database & Factory** if you are automating section lookup, data access, or object creation.
- **UK Classification** if you are using EC3-style classification through the UK package.
- **US Classification** if you are using AISC local slenderness / compactness checks.
- **US Member Checks** for AISC 360-22 tension, compression, flexure, shear, combined forces and stability (Chapters C to H).
- **EU Member Checks** for EN 1993-1-1 Section 6: cross-section resistance, buckling, lateral-torsional buckling and beam-columns (Annexes A and B).
- **EU Serviceability Checks** for EN 1993-1-1 Section 7: deflections, vibration and SLS stresses, with the EN 1990 combinations.
- **BS 5950 Classification** for BS 5950-1:2000 Section 3.5 on UK sections.
- **BS 5950 Member Checks** for BS 5950-1:2000 Sections 2.4, 3.4, 3.6, 4 and 2.5: stability, tension, compression, bending, lateral-torsional buckling, combined forces and deflections.

## Current public API stance

The current API is best understood as a **working engineering API**, not yet a final polished public interface.

That means:

- the **architecture is already useful** for scripts and engineering workflows
- the **classification entry points are usable today**
- a simpler, more unified public API can still be added later without losing the current structure

A good rule is:

\[
\text{workflow today} = \text{data access} + \text{section object} + \text{regional check}
\]

That is the pattern this documentation now emphasizes.
