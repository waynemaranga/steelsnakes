# Contributing Guidelines

Thank you for your interest in contributing to SteelSnakes! This guide outlines how to contribute effectively to the project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct:

- **Be respectful** - Treat all contributors with respect and kindness
- **Be inclusive** - Welcome contributors of all backgrounds and skill levels
- **Be constructive** - Provide helpful feedback and suggestions
- **Be collaborative** - Work together toward common goals

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to avoid duplicates
2. **Use the issue template** if provided
3. **Provide clear reproduction steps** for bugs
4. **Include relevant information** (Python version, OS, etc.)

#### Bug Reports

Include the following information:

```
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Import module '...'
2. Call function '...'
3. See error

**Expected Behavior**
A clear description of what you expected to happen.

**Environment**
- Python version: [e.g. 3.11.5]
- SteelSnakes version: [e.g. 0.1.0]
- OS: [e.g. Ubuntu 22.04]

**Additional Context**
Add any other context about the problem here.
```

#### Feature Requests

For feature requests, please:

1. **Describe the use case** - Why is this feature needed?
2. **Provide examples** - How would the feature be used?
3. **Consider alternatives** - What other solutions have you considered?
4. **Discuss impact** - How would this affect existing functionality?

### Contributing Code

#### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your changes
4. **Set up development environment** (see [Development Guide](development.md))

#### Making Changes

1. **Follow code style** guidelines
2. **Write comprehensive tests** for new functionality
3. **Update documentation** as needed
4. **Ensure all tests pass** before submitting

#### Pull Request Process

1. **Create a clear title** describing the change
2. **Fill out the PR template** completely
3. **Link related issues** using keywords (fixes #123)
4. **Request review** from maintainers
5. **Address feedback** promptly and respectfully

## Development Standards

### Code Quality

- **Type hints** are required for all public APIs
- **Docstrings** must use Google format
- **Tests** must achieve >90% coverage for new code
- **Code style** must pass `ruff` checks

### Commit Messages

Use conventional commit format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Formatting, missing semi colons, etc
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Changes to build process or auxiliary tools

Examples:
```
feat(sections): add support for tapered beams

Add TaperedBeam class with variable depth properties.
Includes JSON data loader and factory registration.

Closes #42
```

### Testing Requirements

All contributions must include appropriate tests:

#### Unit Tests
```python
def test_section_creation():
    """Test basic section creation from designation."""
    beam = UB("457x191x67")
    assert beam.designation == "457x191x67"
    assert isinstance(beam.mass_per_metre, float)
```

#### Integration Tests
```python
def test_factory_auto_detection():
    """Test factory can auto-detect section types."""
    factory = get_factory()
    section = factory.create_section("457x191x67")
    assert section.get_section_type() == SectionType.UB
```

#### Property Tests
```python
@pytest.mark.parametrize("designation", [
    "203x133x25", "457x191x67", "914x305x201"
])
def test_beam_properties(designation):
    """Test beam properties are positive and reasonable."""
    beam = UB(designation)
    assert beam.mass_per_metre > 0
    assert beam.I_yy > 0
    assert beam.A > 0
```

### Documentation Requirements

All public APIs must be documented:

#### Class Documentation
```python
class UniversalBeam(BaseSection):
    """Universal Beam section (UB) per BS EN 10365.
    
    Universal beams are I-shaped sections primarily used for
    bending applications such as floor beams and roof beams.
    
    Attributes:
        h: Overall depth in mm
        b: Flange width in mm
        t_w: Web thickness in mm
        t_f: Flange thickness in mm
        r: Root radius in mm
        
    Example:
        >>> beam = UB("457x191x67")
        >>> print(f"Moment of inertia: {beam.I_yy} cm⁴")
        Moment of inertia: 42200.0 cm⁴
    """
```

#### Method Documentation
```python
def search_sections(
    self, 
    section_type: SectionType, 
    **criteria: Any
) -> List[Tuple[str, Dict[str, Any]]]:
    """Search sections by property criteria.
    
    Supports comparison operators for flexible filtering:
    - `__gt`: Greater than
    - `__lt`: Less than  
    - `__gte`: Greater than or equal
    - `__lte`: Less than or equal
    - `__eq`: Equal to
    - `__ne`: Not equal to
    
    Args:
        section_type: Type of section to search
        **criteria: Property filters with optional operators
        
    Returns:
        List of (designation, properties) tuples matching criteria
        
    Raises:
        ValueError: If section_type is not available
        
    Example:
        >>> db = get_database()
        >>> heavy_beams = db.search_sections(
        ...     SectionType.UB, 
        ...     mass_per_metre__gt=100
        ... )
        >>> len(heavy_beams)
        23
    """
```

## Types of Contributions

### High Priority
- **Bug fixes** - Always welcome
- **Performance improvements** - Especially for database operations
- **Documentation improvements** - Examples, guides, API docs
- **Test coverage** - Improve existing test coverage

### Medium Priority
- **New section types** - Additional steel section standards
- **Analysis features** - Design capacity calculations
- **Data validation** - Improved error handling and validation
- **Utility functions** - Helper functions for common tasks

### Future Considerations
- **International standards** - US (AISC), Australian, etc.
- **Advanced analysis** - Buckling, vibration analysis
- **GUI interface** - Desktop or web application
- **CAD integration** - Export to CAD formats

## Review Process

### For Contributors

1. **Self-review** your changes before submitting
2. **Test thoroughly** on different Python versions if possible
3. **Update documentation** for any API changes
4. **Be responsive** to review feedback

### For Reviewers

1. **Be constructive** and helpful in feedback
2. **Focus on code quality** and maintainability
3. **Check test coverage** and documentation
4. **Approve promptly** when standards are met

### Review Criteria

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New features have comprehensive tests
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact is acceptable

## Recognition

Contributors will be recognized in:

- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **Documentation** credits
- **GitHub contributors** page

## Questions?

If you have questions about contributing:

1. **Check existing documentation** first
2. **Search closed issues** for similar questions
3. **Ask in discussions** for general questions
4. **Create an issue** for specific problems
5. **Email maintainers** for sensitive matters

## License

By contributing to SteelSnakes, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to SteelSnakes! Your efforts help make structural engineering software more accessible and reliable for everyone.
