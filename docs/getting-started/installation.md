# Installation

## Requirements

SteelSnakes requires Python 3.11 or later. It depends on:

- **Pydantic** (≥2.11.7) - For type safety and validation
- **Python Standard Library** - No heavy dependencies!

## Install from PyPI

The recommended way to install SteelSnakes is via pip:

```bash
pip install steelsnakes
```

## Install from Source

For development or to get the latest features:

=== "Using Git"

    ```bash
    git clone https://github.com/waynemaranga/steelsnakes.git
    cd steelsnakes
    pip install -e .
    ```

=== "Using uv (Recommended)"

    ```bash
    git clone https://github.com/waynemaranga/steelsnakes.git
    cd steelsnakes
    uv pip install -e .
    ```

=== "Development Install"

    ```bash
    git clone https://github.com/waynemaranga/steelsnakes.git
    cd steelsnakes
    pip install -e ".[dev,test,docs]"
    ```

## Verify Installation

Test your installation by running:

```python
import steelsnakes
from steelsnakes.core.sections.UK import UB

# Create a simple beam
beam = UB("457x191x67")
print(f"Successfully created: {beam}")
print(f"Moment of inertia: {beam.I_yy} cm⁴")
```

You should see output like:

```
Successfully created: 457x191x67
Moment of inertia: 42200.0 cm⁴
```

## Virtual Environments

It's recommended to use a virtual environment:

=== "venv"

    ```bash
    python -m venv steelsnakes-env
    source steelsnakes-env/bin/activate  # On Windows: steelsnakes-env\Scripts\activate
    pip install steelsnakes
    ```

=== "conda"

    ```bash
    conda create -n steelsnakes python=3.11
    conda activate steelsnakes
    pip install steelsnakes
    ```

=== "poetry"

    ```bash
    poetry new my-steel-project
    cd my-steel-project
    poetry add steelsnakes
    poetry shell
    ```

## Troubleshooting

### Python Version Issues

If you get a Python version error:

```bash
# Check your Python version
python --version

# If using pyenv
pyenv install 3.11.5
pyenv global 3.11.5
```

### Import Errors

If you encounter import errors, ensure the package is installed in the correct environment:

```python
# Check if steelsnakes is installed
import sys
print(sys.path)

# Try importing specific modules
from steelsnakes.core.sections.UK import UB
```

### Data File Issues

If section data isn't loading:

```python
from steelsnakes.core.sections.UK import get_database

db = get_database()
print(f"Available types: {[t.value for t in db.get_available_types()]}")
```

This should show available section types. If the list is empty, there may be an issue with data file locations.

## Next Steps

Now that SteelSnakes is installed, you can:

1. **[Quick Start Guide](quickstart.md)** - Get started with basic usage
2. **[Basic Usage](basic-usage.md)** - Learn the core concepts
3. **[Examples](../examples/basic.md)** - See practical examples

## Optional Dependencies

For enhanced functionality, you might want to install:

```bash
# For development
pip install pytest coverage ruff

# For documentation building
pip install mkdocs mkdocs-material mkdocstrings[python]

# For advanced analysis
pip install numpy pandas matplotlib
```

!!! tip "Performance Tip"
    SteelSnakes loads section data lazily. The first import may take a moment as it builds the internal database, but subsequent operations are very fast.

!!! warning "Windows Users"
    On Windows, you may need to use `py` instead of `python` depending on your installation:
    ```bash
    py -m pip install steelsnakes
    ```
