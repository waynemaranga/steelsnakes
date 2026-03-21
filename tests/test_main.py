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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
