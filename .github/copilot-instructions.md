# SteelSnakes - Structural Steel Analysis Library

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap, Build, and Test the Repository

**Option 1: Full pip installation (recommended when network available)**
- `python --version` -- verify Python 3.11+ (tested with 3.12.3)
- `python -m venv venv`
- `source venv/bin/activate` -- On Windows: `venv\Scripts\activate`
- `pip install --upgrade pip`
- `pip install -e .` -- installs all dependencies and package in development mode -- takes 30-45 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
- `python -c "import steelsnakes; print('Installation successful!')"` -- verify installation

**Option 2: PYTHONPATH approach (when pip install fails due to network issues)**
- `python --version` -- verify Python 3.11+ (tested with 3.12.3)
- `export PYTHONPATH=src` -- adds src directory to Python path
- `PYTHONPATH=src python -c "import steelsnakes; print('Installation successful!')"` -- verify installation
- Always use `PYTHONPATH=src` prefix for all Python commands when using this method

### Run Tests
- **With pip installation**: `pytest` -- runs all tests -- takes less than 1 second. NEVER CANCEL. Set timeout to 30+ seconds.
- **With pip installation**: `pytest -v` -- verbose test output
- **With pip installation**: `pytest --cov=src/steelsnakes` -- run with coverage (configured in pytest.ini)
- **Without pip**: Test suite requires pytest installation. If pip install fails, validate functionality manually using the main demo.
- Test suite: 33 tests pass in ~0.18 seconds

### Run the Application
- ALWAYS run the bootstrapping steps first.
- **With pip installation**: `python src/steelsnakes/main.py` -- runs comprehensive demo
- **With PYTHONPATH**: `PYTHONPATH=src python src/steelsnakes/main.py` -- runs comprehensive demo  
- **With pip installation**: `steelsnakes --help` -- shows simple CLI help
- **Basic test with pip**: `python -c "from steelsnakes.core.sections.UK import UB; print(UB('457x191x67'))"`
- **Basic test with PYTHONPATH**: `PYTHONPATH=src python -c "from steelsnakes.core.sections.UK import UB; print(UB('457x191x67'))"`

## Validation

- Always manually validate any new code by running the main demo: 
  - **With pip**: `python src/steelsnakes/main.py`
  - **With PYTHONPATH**: `PYTHONPATH=src python src/steelsnakes/main.py`
- ALWAYS run through at least one complete end-to-end scenario after making changes.
- The demo loads 18 section types with over 1000 steel sections and demonstrates all core functionality.
- **Linting**: Install ruff separately: `pip install ruff` then run `ruff check src/` and `ruff format src/`
- **CI Requirements**: Always run linting before you are done or the CI (.github/workflows/python-app.yaml) will fail.
- **Documentation**: You can build documentation with `mkdocs build` but it fails due to network restrictions (tries to fetch icons). This is expected in sandboxed environments.

## Network Connectivity Issues

If `pip install` fails with timeout errors:
- This is common in sandboxed environments with limited network access
- Use the PYTHONPATH approach: `export PYTHONPATH=src` and prefix Python commands with `PYTHONPATH=src`
- Manual validation is still possible and comprehensive using the main demo
- The library works perfectly without external dependencies beyond Python standard library components

## Common Tasks

The following are outputs from frequently run commands. Reference them instead of viewing, searching, or running bash commands to save time.

### Repository Root Structure
```
steelsnakes/
├── .github/              # GitHub workflows and templates  
├── docs/                 # MkDocs documentation
├── src/steelsnakes/      # Main package source
│   ├── core/             # Core functionality
│   │   └── sections/     # Section definitions (UK, US, AUS, EU)
│   ├── data/             # Section databases (JSON files)
│   └── engine/           # Analysis engines (future)
├── tests/                # Test suite (pytest)
├── pyproject.toml        # Project configuration
├── requirements.txt      # Dependencies
├── mkdocs.yml           # Documentation config
└── pytest.ini          # Test configuration
```

### Key Commands and Expected Times
- **Installation (full)**: `pip install -e .` -- 30-45 seconds. NEVER CANCEL.
- **Installation (fallback)**: `export PYTHONPATH=src` -- immediate
- **Tests (with pip)**: `pytest` -- 0.18 seconds for 33 tests  
- **Tests (without pip)**: Use manual validation via main demo
- **Linting**: `ruff check src/` -- 0.01 seconds (after `pip install ruff`)
- **Formatting**: `ruff format src/` -- 0.01 seconds  
- **Demo run**: `python src/steelsnakes/main.py` or `PYTHONPATH=src python src/steelsnakes/main.py` -- 1-2 seconds

### Package Import Test
**With pip installation:**
```python
from steelsnakes.core.sections.UK import UB, UC, PFC
beam = UB("457x191x67")
column = UC("305x305x137") 
channel = PFC("430x100x64")
print(f"Beam I_yy: {beam.I_yy} cm⁴")  # Expected: 29400 cm⁴
print(f"Column mass: {column.mass_per_metre} kg/m")  # Expected: 136.9 kg/m
print(f"Channel e0: {channel.e0} mm")  # Expected: 3.27 mm
```

**With PYTHONPATH approach:**
```bash
PYTHONPATH=src python -c "
from steelsnakes.core.sections.UK import UB, UC, PFC
beam = UB('457x191x67')
print(f'Beam I_yy: {beam.I_yy} cm⁴')  # Expected: 29400 cm⁴
"
```

### Dependencies (from pyproject.toml)
Core dependencies: pydantic>=2.11.7, pandas>=2.3.2, polars>=1.32.3, pyarrow>=21.0.0, sqlalchemy>=2.0.43
Dev/test tools: pytest>=8.4.1, coverage==7.10.0, ruff (install separately)
Docs: mkdocs>=1.6.1, mkdocs-material, mkdocstrings[python]>=0.30.0

### Section Types Available
18 section types automatically loaded:
- **Universal Sections**: UB (107), UC (46), UBP (17)
- **Channels**: PFC (16)  
- **Angles**: L_EQUAL (42), L_UNEQUAL (39), L_EQUAL_B2B (33), L_UNEQUAL_B2B (32)
- **Hot Finished Hollow**: HFCHS (103), HFRHS (161), HFSHS (123), HFEHS (11)
- **Cold Formed Hollow**: CFCHS (106), CFRHS (137), CFSHS (96)
- **Connections**: WELDS (12), BOLT_PRE_88 (2), BOLT_PRE_109 (2)

### Database Search Examples
```python
from steelsnakes.core.sections.UK import get_database, SectionType
database = get_database()

# Heavy beams (>200 kg/m): 29 sections found
heavy_beams = database.search_sections(SectionType.UB, mass_per_metre__gt=200)

# Light channels (<20 kg/m): 3 sections found  
light_channels = database.search_sections(SectionType.PFC, mass_per_metre__lt=20)
```

## Critical Timeouts and Build Information

- **NEVER CANCEL**: All build and install commands. Use 60+ minute timeouts.
- **Installation timeout**: Set 60+ seconds for `pip install -e .`
- **Test timeout**: Set 30+ seconds for `pytest` (usually completes in <1 second)
- **Linting timeout**: Set 30+ seconds for `ruff` commands (usually completes in <1 second)

## Development Standards

### Code Quality Requirements
- Type hints required for all public APIs
- Docstrings must use Google format  
- Code style must pass `ruff check src/`
- Code formatting must pass `ruff format src/`
- Tests must achieve >90% coverage for new code

### File Modification Guidelines
- Main package code: `src/steelsnakes/`
- Section definitions: `src/steelsnakes/core/sections/UK/` (primary)
- Data files: `src/steelsnakes/data/sections/`
- Tests: `tests/`
- Documentation: `docs/`

### Key Project Files
- `pyproject.toml` -- project configuration, dependencies, build settings
- `pytest.ini` -- test configuration with coverage settings
- `mkdocs.yml` -- documentation configuration
- `src/steelsnakes/main.py` -- comprehensive demo and main entry point
- `.github/workflows/python-app.yaml` -- CI/CD pipeline

## Troubleshooting

### Common Issues
- **Import errors**: Run installation steps from scratch, or use PYTHONPATH approach
- **"No suitable beam found" in searches**: This is expected behavior when search criteria are too restrictive
- **Test failures**: Check if new code follows type hints and docstring requirements
- **Linting failures**: Install ruff first: `pip install ruff`, then run `ruff format src/` then `ruff check src/`
- **Documentation build fails**: Expected in sandboxed environments due to network restrictions
- **Network timeouts during pip install**: Common in sandboxed environments - use PYTHONPATH approach instead

### When Things Don't Work
- **Network issues with pip**: Use PYTHONPATH approach: `export PYTHONPATH=src`
- **Import errors**: Run installation steps from scratch, or use PYTHONPATH approach
- **Test failures**: Check if new code follows type hints and docstring requirements  
- **Linting failures**: Install ruff first: `pip install ruff`, then run `ruff format src/` then `ruff check src/`
- **Documentation build fails**: Expected in sandboxed environments due to network restrictions
- Always verify Python 3.11+ is being used
- Run the main demo to verify core functionality: 
  - **With pip**: `python src/steelsnakes/main.py`
  - **With PYTHONPATH**: `PYTHONPATH=src python src/steelsnakes/main.py`

## Validation Scenarios

### Basic Functionality Test
**With pip installation:**
Run: `python src/steelsnakes/main.py`
Expected: Demo loads 18 section types, shows section properties, database search examples, and completes successfully with "🎉 All demos completed successfully!"

**With PYTHONPATH approach:**
Run: `PYTHONPATH=src python src/steelsnakes/main.py`
Expected: Demo loads 18 section types, shows section properties, database search examples, and completes successfully with "🎉 All demos completed successfully!"

### Quick API Test  
**With pip installation:**
```python
from steelsnakes.core.sections.UK import UB
beam = UB("457x191x67")
assert beam.I_yy == 29400, f"Expected 29400, got {beam.I_yy}"
print("✅ Basic API working correctly")
```

**With PYTHONPATH approach:**
```bash
PYTHONPATH=src python -c "
from steelsnakes.core.sections.UK import UB
beam = UB('457x191x67')
assert beam.I_yy == 29400, f'Expected 29400, got {beam.I_yy}'
print('✅ Basic API working correctly')
"
```

### Test Suite Validation
**With pip installation:**
Run: `pytest -v`
Expected: 33 tests pass, 2 may be skipped, completes in <1 second

**Without pip installation:**
Tests require pytest package. Use manual validation via main demo and API tests above.

This library provides a comprehensive database of steel sections for structural analysis with a clean, type-safe Python API. The architecture supports UK sections (primary), with US, AUS, and EU sections planned for future releases.