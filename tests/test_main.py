"""
Essential tests for steelsnakes main module imports.
"""

import pytest


def test_import_steelsnakes():
    """Test that steelsnakes package can be imported."""
    import steelsnakes
    assert steelsnakes is not None


def test_import_base_sections():
    """Test that base sections module can be imported."""
    from steelsnakes.base.sections import BaseSection, SectionType
    assert BaseSection is not None
    assert SectionType is not None


def test_import_base_database():
    """Test that base database module can be imported."""
    from steelsnakes.base.database import SectionDatabase
    assert SectionDatabase is not None


def test_import_base_factory():
    """Test that base factory module can be imported."""
    from steelsnakes.base.factory import SectionFactory
    assert SectionFactory is not None


def test_import_uk_modules():
    """Test that UK modules can be imported."""
    try:
        from steelsnakes.UK.database import UKSectionDatabase
        from steelsnakes.UK.factory import UKSectionFactory
        assert UKSectionDatabase is not None
        assert UKSectionFactory is not None
    except ImportError as e:
        pytest.skip(f"UK modules not available: {e}")


def test_main_examples_run_and_print_eu_and_us_sections(capsys):
    """Smoke test the example runner so the documented demo stays valid."""
    from steelsnakes.main import main

    main()
    output = capsys.readouterr().out

    assert "steelsnakes classification examples" in output
    assert "EU examples" in output
    assert "US examples" in output
    assert "W-shape in minor-axis flexure" in output
    assert "case10" in output


def test_main_prints_every_numbered_example(capsys):
    """Test all twenty numbered examples run, in order, through to BS 5950."""
    import re
    from steelsnakes.main import main

    main()
    output = capsys.readouterr().out

    numbers = [int(number) for number in re.findall(r"^\s*(\d+)\. ", output, flags=re.MULTILINE)]
    assert sorted(set(numbers)) == list(range(1, 21))
    assert numbers == sorted(numbers)
    assert "BS 5950-1:2000 UB 457x191x67 S275" in output


def test_console_script_entry_point_resolves_to_main():
    """Test the [project.scripts] target in pyproject.toml imports and is callable."""
    import importlib
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        target = tomllib.load(f)["project"]["scripts"]["steelsnakes"]

    module_name, _, attribute = target.partition(":")
    entry_point = getattr(importlib.import_module(module_name), attribute)

    from steelsnakes.main import main
    assert entry_point is main


def test_combined_preset_without_alpha_raises():
    """Test the error path in main.py's __main__ block: 'combined' needs explicit elements."""
    from steelsnakes.UK import UB, classify_section
    from steelsnakes.UK.checks.classification import ElementStressDistribution

    with pytest.raises(NotImplementedError, match="custom_elements"):
        classify_section(section=UB("457x191x67"), fy_mpa=355.0, stress_pattern=ElementStressDistribution.COMBINED)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
