# Installation

SteelSnakes requires Python 3.11 or higher and can be installed using pip.

## Requirements

- **Python**: 3.11+ (tested with 3.12)
- **Operating System**: Windows, macOS, Linux
- **Dependencies**: Automatically installed with the package

## Install from PyPI

The easiest way to install SteelSnakes is from PyPI using pip:

```bash
pip install steelsnakes
```

## Install from Source

For the latest development version or to contribute to the project:

```bash
# Clone the repository
git clone https://github.com/waynemaranga/steelsnakes.git
cd steelsnakes

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## Verify Installation

Test your installation by running:

```python
import steelsnakes
print("SteelSnakes version:", steelsnakes.__version__)

# Quick functionality test
from steelsnakes.UK import UB
beam = UB("457x191x67")
print(f"Test beam area: {beam.A} cm²")
```

You should see the version number and a beam area value, confirming the installation is working correctly.

## Virtual Environment (Recommended)

We strongly recommend using a virtual environment to avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv steelsnakes-env

# Activate it
source steelsnakes-env/bin/activate  # Linux/macOS
# or
steelsnakes-env\Scripts\activate     # Windows

# Install SteelSnakes
pip install steelsnakes
```

## Development Installation

If you plan to contribute or need the latest features:

```bash
# Clone and enter directory
git clone https://github.com/waynemaranga/steelsnakes.git
cd steelsnakes

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies and package in editable mode
pip install --upgrade pip
pip install -e .

# Verify installation
python -c "import steelsnakes; print('Development installation OK')"
```

## Troubleshooting

### Python Version Issues
If you encounter version errors, ensure you're using Python 3.11+:

```bash
python --version  # Should show 3.11.x or higher
```

### Permission Errors
On some systems, you may need to use `--user` flag:

```bash
pip install --user steelsnakes
```

### Import Errors
If you get import errors after installation:

1. Restart your Python interpreter
2. Check that you're in the correct virtual environment
3. Verify the installation: `pip list | grep steelsnakes`

!!! tip "Ready to Start?"
    Once installed, head to the [Quick Start Guide](quickstart.md) to begin using SteelSnakes!