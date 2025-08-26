## SteelSnakes — Copilot Instructions

Always use this file first. If reality deviates (APIs, paths, commands), prefer these instructions and only fall back to searching the repo or running commands when necessary.

### Scope and Status
- Python: 3.11+ (tested with 3.12)
- Version: 0.0.1-alpha-5
- Regions: UK is the primary supported region today. EU/US/AU/IS modules exist but are incomplete and evolving.
 

### Bootstrap, Build, Test

Option 1 — Install in editable mode (recommended when network is available)
- `python --version` (expect 3.11+)
- `python -m venv venv`
- `source venv/bin/activate`  (Windows: `venv\Scripts\activate`)
- `pip install --upgrade pip`
- `pip install -e .`  (installs package + deps; allow 30–60s)
- `python -c "import steelsnakes; print('Installation OK')"`

Option 2 — PYTHONPATH (when install is blocked by network)
- `export PYTHONPATH=src`
- `PYTHONPATH=src python -c "import steelsnakes; print('Import OK')"`
- Prefix subsequent Python commands with `PYTHONPATH=src`.

Run tests
- `pytest` or `pytest -v`
- With PYTHONPATH: `PYTHONPATH=src pytest`
- Coverage is optional in alpha: `pytest --cov=src/steelsnakes` if you need it.

### Running Demos and Quick Checks
- Demo script: `python src/steelsnakes/main.py` (or `PYTHONPATH=src python src/steelsnakes/main.py`)
- Quick API example (UK, convenience function):
```python
from steelsnakes.UK.universal import UB
beam = UB("457x191x67")
print(beam.A)
```
- Factory-based creation:
```python
from steelsnakes.UK import create_section
from steelsnakes.base.sections import SectionType
section = create_section("457x191x67", SectionType.UB)
print(section.get_properties())
```

 

### Validation
- Run the demo end-to-end after changes: `python src/steelsnakes/main.py`
- Lint with Ruff (install separately): `pip install ruff` then `ruff format src/` and `ruff check src/`
- Docs: `mkdocs build` (may require network; if it fails in sandboxed environments, skip and validate locally without network)

### Repository Layout (orientation)
```
steelsnakes/
├── src/steelsnakes/
│   ├── main.py               # Demo entry point
│   ├── base/                 # Core: database, factory, section types
│   ├── UK/                   # UK sections (primary, fully wired)
│   ├── EU/, US/, AU/, IS/    # Present, partially implemented
│   └── engine/               # Analysis engines (early)
├── tests/                    # Pytest suite
├── pyproject.toml            # Build, scripts, deps
└── mkdocs.yaml               # Docs configuration
```

### Dependencies (pyproject.toml)
- Runtime: pydantic>=2.11, sqlalchemy>=2.0
- Dev/Test: pytest>=8.4, coverage==7.10.0, ruff (install separately)
- Docs: mkdocs>=1.6, mkdocstrings[python]>=0.30.0, mkdocs-shadcn, pymdown-extensions

Note: This library does depend on external packages; use the PYTHONPATH approach if network is restricted and you only need to run code locally.

### Development Standards (alpha-friendly)
- Type hints for all public APIs
- Docstrings in Google style
- Must pass: `ruff check src/` and `ruff format src/`
- Tests: add focused, necessary tests for new behavior; keep them minimal and high-signal
- Backward compatibility is best-effort during alpha; APIs may change as regions and features expand

### Troubleshooting
- Install issues: use the PYTHONPATH approach
- Import errors: ensure `PYTHONPATH=src` or that the venv is active
- Linting issues: `pip install ruff`, then `ruff format src/` and `ruff check src/`
- Docs build fails: likely due to network; skip in sandboxed environments

### Roadmap Cues (to keep instructions future-proof)
- Regions: broaden EU/US/AU/IS coverage and wire them into the CLI discovery
- Data backends: optional SQLite acceleration via tools in `steelsnakes.base.database`
- Analysis: build out `engine/` for structural checks and design utilities
 

These instructions are intentionally concise and alpha-friendly: prefer the simplest happy path, verify with the demo, and expand iteratively.
