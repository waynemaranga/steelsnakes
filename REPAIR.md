# Test Suite Repair Plan

## Snapshot (2026-03-21)

Command run:
- c:/Users/wayne.Maranga/Documents/steelsnakes/.venv/Scripts/python.exe -m pytest -v

Observed:
- Collected tests: 3
- Passed: 3
- Failed: 0
- Error: 0
- Skipped: 0

Tests that currently run:
- tests/test_sections.py::TestInheritance::test_inheritance_chain
- tests/test_sections.py::TestInheritance::test_method_resolution_order
- tests/test_sections.py::TestInheritance::test_abstract_base_class_registration

## What Is Broken (Practical View)

1. Effective test coverage is very low.
- Most tests in tests/test_database.py, tests/test_factory.py, tests/test_fuzzy_matching.py, and tests/test_UK_module.py are commented out.
- Large parts of tests/test_sections.py are also commented out.

2. tests/test_main.py is not a real test module yet.
- Current content is only: assert 1
- This does not create any test function for pytest collection.

3. Pytest configuration likely not being applied as intended.
- pytest.ini currently uses [tool:pytest].
- For pytest.ini files, the expected section is [pytest].
- The run output did not show configured coverage reporting, suggesting addopts may not be active.

## Repair Backlog (Priority Order)

### P0: Restore config enforcement and visibility
- Change pytest.ini section header from [tool:pytest] to [pytest].
- Re-run pytest and verify:
  - Coverage summary appears.
  - cov-fail-under=80 is enforced.
  - strict-config and strict-markers are active.

Done when:
- Pytest output explicitly includes coverage report and threshold behavior.

### P1: Bring back a minimal, stable smoke set
- Un-comment a small subset first:
  - 5 to 10 tests from tests/test_database.py
  - 5 to 10 tests from tests/test_factory.py
  - 3 to 5 tests from tests/test_UK_module.py
- Keep fixtures lightweight and deterministic.

Done when:
- At least 20 tests collected and all passing locally.

### P2: Convert disabled tests to maintainable parameterized tests
- Replace repeated commented tests with pytest.mark.parametrize where possible.
- Remove stale/duplicate commented blocks that are no longer needed.

Done when:
- No large commented test blocks remain in active test files.

### P3: Add real tests for main entry points
- Replace tests/test_main.py placeholder with meaningful tests around:
  - startup path
  - expected output or side effects
  - error path behavior

Done when:
- tests/test_main.py contributes at least 2 to 4 meaningful tests.

### P4: Stage-by-stage quality gate
- After each file family is restored, run:
  - full pytest
  - targeted module run for changed tests
- Keep each repair PR/commit small and reviewable.

Done when:
- Full suite is green and coverage gate is consistently enforced.

## Suggested Execution Sequence

1. Fix pytest.ini header.
2. Re-run pytest and confirm config behavior.
3. Reactivate tests/test_database.py smoke subset.
4. Reactivate tests/test_factory.py smoke subset.
5. Reactivate tests/test_UK_module.py smoke subset.
6. Expand tests/test_sections.py from inheritance-only to full base behavior.
7. Implement real tests in tests/test_main.py.

## Current Risk

Current CI confidence is low because most intended tests are inactive, even though the active subset passes.