# Test Suite Repair Plan

## Snapshot (2026-09-27)

Command run:
- .venv/Scripts/python.exe -m pytest

Observed:
- Collected tests: 546
- Passed: 546
- Failed: 0
- Error: 0
- Skipped: 0
- Coverage: 82.27%, gate of 80% enforced

## Previous Snapshot (2026-03-21)

Command run:
- c:/Users/wayne.Maranga/Documents/steelsnakes/.venv/Scripts/python.exe -m pytest -v

Observed:
- Collected tests: 3
- Passed: 3
- Failed: 0
- Error: 0
- Skipped: 0

Tests that ran:
- tests/test_sections.py::TestInheritance::test_inheritance_chain
- tests/test_sections.py::TestInheritance::test_method_resolution_order
- tests/test_sections.py::TestInheritance::test_abstract_base_class_registration

## What Was Broken (Practical View)

1. Effective test coverage was very low.
- Most tests in tests/test_database.py, tests/test_factory.py, tests/test_fuzzy_matching.py, and tests/test_UK_module.py were commented out.
- Large parts of tests/test_sections.py were also commented out.

2. tests/test_main.py was not a real test module.
- Content was only: assert 1
- This did not create any test function for pytest collection.

3. Pytest configuration was not being applied.
- pytest.ini used [tool:pytest]; pytest.ini files need [pytest].
- addopts (coverage, cov-fail-under=80, strict-config, strict-markers) were silently ignored.

## Repair Backlog (Priority Order)

### P0: Restore config enforcement and visibility
- Change pytest.ini section header from [tool:pytest] to [pytest].
- Re-run pytest and verify:
  - Coverage summary appears.
  - cov-fail-under=80 is enforced.
  - strict-config and strict-markers are active.

Done when:
- Pytest output explicitly includes coverage report and threshold behavior.

Status: done. With the header fixed the suite first failed the gate at 71.72%; it now passes at 82.27% without omitting
any source from coverage.

### P1: Bring back a minimal, stable smoke set
- Un-comment a small subset first:
  - 5 to 10 tests from tests/test_database.py
  - 5 to 10 tests from tests/test_factory.py
  - 3 to 5 tests from tests/test_UK_module.py
- Keep fixtures lightweight and deterministic.

Done when:
- At least 20 tests collected and all passing locally.

Status: done. tests/test_database.py 13, tests/test_factory.py 78 (69 of them build every packaged section, one per
region and section type), tests/test_UK_module.py 96, tests/test_fuzzy_matching.py 22, tests/test_US_Metric_module.py
43. Fixtures write JSON to tmp_path, or read the packaged data.

### P2: Convert disabled tests to maintainable parameterized tests
- Replace repeated commented tests with pytest.mark.parametrize where possible.
- Remove stale/duplicate commented blocks that are no longer needed.

Done when:
- No large commented test blocks remain in active test files.

Status: done. tests/test_UK_module.py and tests/test_fuzzy_matching.py are rewritten against the current API, with the
per-type and per-constructor tests parameterized. Mocks of the old `steelsnakes.UK.universal` module paths are replaced
by real data directories. The bolt and weld blocks stay commented, as their section classes are.

Restoring the fuzzy tests showed that `create_section("254x146x30")`, with no type, silently returned 254x146x37:
difflib scored 254x146x31 and 254x146x37 equally and took one. `find_section()` now only resolves an unambiguous
match; a tie raises `SectionNotFoundError` with both as suggestions.

### P3: Add real tests for main entry points
- Replace tests/test_main.py placeholder with meaningful tests around:
  - startup path
  - expected output or side effects
  - error path behavior

Done when:
- tests/test_main.py contributes at least 2 to 4 meaningful tests.

Status: done. 9 tests: imports, `main()` output for all twenty numbered examples, the `[project.scripts]` target in
pyproject.toml resolving to `steelsnakes.main:main`, and the `combined` preset error path from main.py's `__main__`
block.

### P4: Stage-by-stage quality gate
- After each file family is restored, run:
  - full pytest
  - targeted module run for changed tests
- Keep each repair PR/commit small and reviewable.

Done when:
- Full suite is green and coverage gate is consistently enforced.

Status: done locally. CI (.github/workflows) runs a bare `pytest` on ubuntu-latest, which now picks up pytest.ini and
enforces the gate.

## Suggested Execution Sequence

1. ~~Fix pytest.ini header.~~
2. ~~Re-run pytest and confirm config behavior.~~
3. ~~Reactivate tests/test_database.py smoke subset.~~
4. ~~Reactivate tests/test_factory.py smoke subset.~~
5. ~~Reactivate tests/test_UK_module.py smoke subset.~~
6. ~~Expand tests/test_sections.py from inheritance-only to full base behavior.~~
7. ~~Implement real tests in tests/test_main.py.~~

## Current Risk

- Coverage sits 2.27 points above the gate. The largest untested modules are base/sqlite3db.py (13%), cli.py (0%), the
  legacy US/checks/lrfd.py and UK/checks/uls.py prototypes (0%), and the IN and AU sections, which have no data yet.
- The local .venv still carries the old `steelsnakes = steelsnakes:main` console script; `uv pip install -e .` refreshes
  it. pyproject.toml is correct and tested.
