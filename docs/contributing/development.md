# Development Guide

This guide covers setting up a development environment and contributing to SteelSnakes.

## Development Setup

### Prerequisites

- Python 3.11 or later
- Git
- A text editor or IDE (VS Code, PyCharm, etc.)

### Setting Up the Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/waynemaranga/steelsnakes.git
   cd steelsnakes
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[dev,test,docs]"
   ```

4. **Verify installation:**
   ```bash
   python -c "import steelsnakes; print('Installation successful!')"
   ```

## Project Structure

```
steelsnakes/
├── src/steelsnakes/           # Main package
│   ├── __init__.py
│   ├── core/                  # Core functionality
│   │   └── sections/          # Section definitions
│   │       ├── UK/            # UK section standards
│   │       ├── US/            # US section standards (future)
│   │       └── AUS/           # Australian standards (future)
│   ├── data/                  # Section databases
│   │   ├── sections/          # JSON data files
│   │   └── sqlite_driver.py   # Database interface
│   └── engine/                # Analysis engines (future)
├── tests/                     # Test suite
├── docs/                      # Documentation
├── demo/                      # Example scripts
└── pyproject.toml            # Project configuration
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=steelsnakes

# Run specific test file
pytest tests/test_sections.py

# Run with verbose output
pytest -v
```

### Writing Tests

Follow these guidelines when writing tests:

```python
import pytest
from steelsnakes.core.sections.UK import UB, get_database

def test_section_creation():
    """Test basic section creation."""
    beam = UB("457x191x67")
    assert beam.designation == "457x191x67"
    assert beam.mass_per_metre == 67.1

def test_section_properties():
    """Test section properties are accessible."""
    beam = UB("457x191x67")
    assert hasattr(beam, 'I_yy')
    assert isinstance(beam.I_yy, (int, float))

def test_database_search():
    """Test database search functionality."""
    database = get_database()
    results = database.search_sections(SectionType.UB, mass_per_metre__gt=100)
    assert len(results) > 0
```

## Code Style

### Formatting

We use `ruff` for linting and formatting:

```bash
# Check code style
ruff check src/

# Format code
ruff format src/
```

### Type Hints

All code should include comprehensive type hints:

```python
from typing import List, Optional, Dict, Any
from steelsnakes.core.sections.UK import BaseSection, SectionType

def search_sections(
    section_type: SectionType,
    criteria: Dict[str, Any]
) -> List[BaseSection]:
    """Search for sections matching criteria."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_capacity(section: BaseSection, load_type: str) -> float:
    """Calculate section capacity for given load type.
    
    Args:
        section: Steel section to analyze
        load_type: Type of loading ('moment', 'shear', 'axial')
        
    Returns:
        Design capacity in appropriate units
        
    Raises:
        ValueError: If load_type is not recognized
        
    Example:
        >>> beam = UB("457x191x67")
        >>> capacity = calculate_capacity(beam, "moment")
        >>> print(f"Moment capacity: {capacity} kNm")
    """
    pass
```

## Adding New Section Types

### 1. Create Section Class

```python
from dataclasses import dataclass
from steelsnakes.core.sections.UK.base import BaseSection, SectionType

@dataclass
class NewSectionType(BaseSection):
    """Description of new section type."""
    
    # Define properties specific to this section type
    property1: float
    property2: float
    
    @classmethod
    def get_section_type(cls) -> SectionType:
        """Return the section type enum."""
        return SectionType.NEW_TYPE
```

### 2. Add to SectionType Enum

```python
class SectionType(str, Enum):
    # ... existing types ...
    NEW_TYPE = "NEW_TYPE"
```

### 3. Create Data File

Create `data/sections/UK/NEW_TYPE.json` with section data:

```json
{
    "designation1": {
        "designation": "designation1",
        "property1": 100.0,
        "property2": 200.0,
        "mass_per_metre": 50.0
    }
}
```

### 4. Register with Factory

```python
# In __init__.py
from .NewSectionType import NewSectionType

# Register with factory
factory = get_factory()
factory.register_section_class(NewSectionType)
```

### 5. Write Tests

```python
def test_new_section_type():
    """Test new section type creation."""
    section = NewSectionType("designation1")
    assert section.property1 == 100.0
    assert section.get_section_type() == SectionType.NEW_TYPE
```

## Documentation

### Building Documentation

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

### Writing Documentation

- Use clear, concise language
- Include practical examples
- Add type hints to all code examples
- Use admonitions for important notes

```markdown
!!! tip "Pro Tip"
    This is helpful information for users.

!!! warning "Important"
    This is something users need to be careful about.
```

## Performance Guidelines

### Database Queries

- Cache database instances when possible
- Use specific search criteria to limit results
- Consider pagination for large result sets

```python
# Good: Cache database
database = get_database()
for criteria in search_list:
    results = database.search_sections(SectionType.UB, **criteria)

# Avoid: Recreating database
for criteria in search_list:
    database = get_database()  # Inefficient
    results = database.search_sections(SectionType.UB, **criteria)
```

### Memory Usage

- Avoid loading unnecessary section data
- Use generators for large datasets
- Clean up temporary objects

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commit format:

```
type(scope): description

- feat: new feature
- fix: bug fix
- docs: documentation updates
- style: formatting changes
- refactor: code refactoring
- test: test updates
- chore: maintenance tasks
```

Examples:
```
feat(sections): add support for castellated beams
fix(database): handle missing data files gracefully
docs(api): update section type documentation
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with appropriate tests
3. Update documentation if needed
4. Ensure all tests pass
5. Create pull request with clear description
6. Address review feedback
7. Merge after approval

## Release Process

### Version Updates

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag
4. Build and publish to PyPI

### Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changelog is updated
- [ ] Version number is bumped
- [ ] No breaking changes (or properly documented)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/waynemaranga/steelsnakes/issues)
- **Discussions**: [GitHub Discussions](https://github.com/waynemaranga/steelsnakes/discussions)
- **Email**: [waynemaranga@gmail.com](mailto:waynemaranga@gmail.com)

## Contributing Guidelines

See [Contributing Guidelines](guidelines.md) for detailed information about contributing to SteelSnakes.
