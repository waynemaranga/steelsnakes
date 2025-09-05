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

###
