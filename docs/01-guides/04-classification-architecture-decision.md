# EU Classification Architecture Decision Guide

This note compares two architecture styles for section classification and recommends a path suitable for an open source side project that still has strong quality standards.

## Goal

Keep classification logic:
- Correct and easy to trust
- Easy to extend to beams, channels, angles, SHS/RHS/CHS, and built-up/custom sections
- Fast enough to develop and maintain as one maintainer or a small team

## Option A: Robust Architecture (engine + adapters)

### Shape

- One central classification engine with all formula/limit logic
- Section-specific adapters that only extract geometry into generic elements
- One public API that accepts:
  - Predefined section objects
  - Custom element inputs (for built-up and user-defined sections)
- Strong validation, typed models, and structured results (metadata, governing element, traceability)

### Pros

- Single source of truth for classification logic
- Lower risk of duplicated/contradictory formulas
- Easiest to test deeply and trust over time
- Best long-term support for custom and built-up sections
- Future-proof for adding more codes/checks

### Cons

- More initial structure and abstractions
- Slightly slower to ship first versions of each section type
- Requires discipline in adapter conventions

## Option B: Concise Architecture (per-section direct logic)

### Shape

- Each section module performs its own classification checks directly
- Inputs and formulas handled close to section classes
- Minimal shared core and fewer abstractions

### Pros

- Fastest to write and iterate early
- Easy to understand locally in each module
- Lower initial cognitive overhead

### Cons

- Logic duplication grows quickly
- Harder to keep formulas consistent across section types
- Built-up/custom support becomes fragmented
- Testing needs to repeat similar scenarios in many modules
- Refactors become expensive later

## Direct Comparison

| Criterion | Robust (Engine + Adapters) | Concise (Per-Section Direct) |
|---|---|---|
| Initial dev speed | Medium | High |
| Long-term maintainability | High | Low-Medium |
| Consistency of formulas | High | Medium-Low |
| Built-up/custom support | High | Medium-Low |
| Debugging traceability | High | Medium |
| Risk of regressions | Lower with tests | Higher over time |
| Best for | Growing library | Small short-lived scripts |

## Recommendation for This Project

Use a hybrid with a robust core and concise adapters.

Why this fits your context:
- You are building an open source library, not a one-off script.
- You already expect multiple section families and built-up inputs.
- You care about quality standards, not only speed.

### Practical interpretation

- Keep the classification math centralized.
- Keep adapters thin and simple.
- Allow quick contribution by making adapter files short and obvious.
- Avoid over-engineering with too many base classes or inheritance layers.

## Decision Rule (simple)

Choose robust core if at least 2 are true:
- More than 3 section families will share similar checks.
- Built-up/custom inputs are required.
- You want contributors to extend without changing formulas.
- You need confident regression testing.

For this repo, all 4 are true.

## Minimal Standard You Can Enforce

1. One formula implementation per check type.
2. No duplicate limit constants across section modules.
3. Every adapter has 2 tests:
   - Extraction correctness
   - Governing class behavior
4. Every check result includes:
   - Element ratios
   - Limits used
   - Governing class and governing element(s)

## Lean Roadmap

1. Keep current engine + adapter pattern.
2. Add stress-state support next (pure compression, bending, combined via psi).
3. Add hollow section adapters (SHS/RHS/CHS).
4. Add built-up helper that creates custom elements from user geometry.
5. Add one docs page with worked examples for each section family.

## When to Simplify Further

Simplify only if:
- You stop supporting custom/built-up sections, or
- You freeze section coverage and no longer expand families.

Until then, robust core + concise adapters is the best balance of speed and quality.

## Suggested Decision

Adopt: Robust core, concise adapters, strict tests.

This gives you side-project velocity now and avoids a painful rewrite later.
