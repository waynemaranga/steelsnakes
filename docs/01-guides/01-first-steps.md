# First Steps

$steelsnakes$ is for civil & structural engineers with beginner to intermediate Python skill.

## Installation

<!-- prettier-ignore-start -->
/// tab | pip

    :::bash
    pip install steelsnakes
///

/// tab | uv

    :::bash
    uv add steelsnakes
///

/// tab | poetry

    :::bash
    poetry add steelsnakes
///
<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->
!!!warning "Installing in Colab"
    As of September 2025, installing $steelsnakes$ in Google Colab replaces the pre-installed `numpy` version with a newer one, and Colab prompts to restart the runtime, losing the runtime's state and local variables. Future implementations of $steelsnakes$ will resolve this by using a version of `numpy` compatible with Colab (2.0.2 in September 2025) or doing away with `numpy` as a dependency altogether.

<!-- prettier-ignore-end -->

## Basic Usage

### Getting Section Properties

```python
from steelsnakes.UK.universal import UB
from steelsnakes.US.beams import W

beam_1 = UB(designation="457x191x67")
beam_2 = W("W44X335")

print(beam_1.h) # returns h as a float
print(beam_1.list_properties()) # returns list of all available properties
print(beam_1.get_properties()) # returns dictionary of all properties and their values

print(beam_2)
print(beam_2.A)

```

### Building on the API

The basic usage above relies on `steelsnakes.<region>` imports, but most automated workflows should build on the shared base modules:

- `steelsnakes.base.database.SectionDatabase` discovers JSON datasets by region, caches every supported `SectionType`, and exposes fuzzy lookups and comparison filters so pipelines can tolerate slight naming variations.
- `steelsnakes.base.factory.SectionFactory` wires that cache to the concrete classes defined in each region (`UK`, `EU`, `US`, etc.) and exposes `create_section(...)` so you can programmatically assemble any section without hard-coding the class name.

See the API reference page (`docs/02-api-reference/02-database.md`) for examples of how the database and factory collaborate, and expect similar patterns to appear in the future for connectors and checks.

<!-- prettier-ignore-start -->
!!!warning "Note"
    The package does not currently enforce unit conversions or normalized inputs. Always feed inputs in the units the region expects (e.g., millimetres/kN if you are using Eurocode sections) and double-check the results before relying on them.
<!-- prettier-ignore-end -->

### What else is coming

If you're exploring the docs, the `Codes and Standards` page is the best place to see what design standards each region is aiming to cover; expect more guides (installation modes, CLI usage, contributed data) once the codebase stabilizes.
