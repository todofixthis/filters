# Pytest Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Export `assert_filter_passes`, `assert_filter_errors`, `unmodified`, and
`skip_value_check` as a distributable pytest plugin so downstream libraries can use
them as proper injected fixtures.

**Architecture:** Create `src/filters/pytest_plugin.py` containing the exported symbols,
register it as a pytest plugin via the `pytest11` entry point in `pyproject.toml`, then
slim `test/conftest.py` down to internal-only helpers. The existing 401-test suite serves
as the integration test — if it passes after the refactor, the plugin works correctly.

**Tech Stack:** Python, pytest fixtures, `pytest11` entry points (hatchling build system)

---

### Task 1: Write the failing test

**Files:**
- Create: `test/test_pytest_plugin.py`

**Step 1: Create the test file**

```python
"""Tests for the filters pytest plugin."""

import filters as f
import filters.pytest_plugin as plugin


def test_module_exports():
    """Plugin __all__ contains the expected public symbols."""
    assert "assert_filter_errors" in plugin.__all__
    assert "assert_filter_passes" in plugin.__all__
    assert "skip_value_check" in plugin.__all__
    assert "unmodified" in plugin.__all__


def test_unmodified_is_sentinel():
    """unmodified is a class, not an instance."""
    assert isinstance(plugin.unmodified, type)


def test_skip_value_check_is_sentinel():
    """skip_value_check is a class, not an instance."""
    assert isinstance(plugin.skip_value_check, type)


def test_assert_filter_passes_fixture(assert_filter_passes):
    """assert_filter_passes fixture is injected and functional."""
    assert_filter_passes(f.Int(), "42", 42)


def test_assert_filter_errors_fixture(assert_filter_errors):
    """assert_filter_errors fixture is injected and functional."""
    assert_filter_errors(f.Int(), "not-an-int", [f.Int.CODE_INVALID_VALUE])
```

**Step 2: Run to verify it fails**

```
uv run pytest test/test_pytest_plugin.py -v
```

Expected: `ModuleNotFoundError: No module named 'filters.pytest_plugin'`

---

### Task 2: Create `src/filters/pytest_plugin.py`

**Files:**
- Create: `src/filters/pytest_plugin.py`

**Step 1: Create the module**

Move the exported symbols out of `test/conftest.py` into this new file. The content is
identical to the corresponding sections in conftest.py — just relocated.

```python
"""
Pytest plugin for testing filters.

Provides fixtures and sentinel classes for writing filter tests. Registered
automatically via the ``pytest11`` entry point — no configuration required.

Import sentinels directly::

    from filters.pytest_plugin import unmodified, skip_value_check

Fixtures (``assert_filter_passes``, ``assert_filter_errors``) are injected by
pytest automatically.
"""

import json
from itertools import starmap
from pprint import pformat
from traceback import format_exception

import pytest

from filters.handlers import FilterRunner

__all__ = [
    "assert_filter_errors",
    "assert_filter_passes",
    "skip_value_check",
    "unmodified",
]


class unmodified:
    """
    Used by ``assert_filter_passes`` so that you can omit the
    ``expected_value`` parameter.
    """

    pass


class skip_value_check:
    """
    Sentinel value; used by ``assert_filter_passes`` to skip checking the
    filtered value. This is useful for tests where a simple equality check
    is not practical.

    Note: If you use ``skip_value_check``, you should add extra assertions
    to your test to make sure the filtered value conforms to expectations.
    """

    pass


def _run_filter_assertion(filter_instance, test_value, expected_codes, expected_value):
    """
    Core assertion logic for filter testing.

    Args:
        filter_instance: The filter instance to test.
        test_value: The value to filter.
        expected_codes: Expected error codes.
        expected_value: Expected value for cleaned_data.
    """
    runner = FilterRunner(
        starting_filter=filter_instance,
        incoming_data=test_value,
        capture_exc_info=True,
    )

    # Fail immediately if unhandled exceptions occurred.
    if runner.has_exceptions:
        pytest.fail(
            "Unhandled exceptions occurred while filtering the "
            "request payload:\n\n{tracebacks}\n\n"
            "Filter Messages:\n\n{messages}".format(
                messages=pformat(dict(runner.filter_messages)),
                tracebacks=pformat(list(starmap(format_exception, runner.exc_info))),
            )
        )

    if isinstance(expected_codes, list):
        expected_codes = {"": expected_codes}

    if runner.error_codes != expected_codes:
        pytest.fail(
            "Filter generated unexpected error codes (expected "
            "{expected}):\n\n{messages}".format(
                expected=json.dumps(expected_codes),
                messages=pformat(dict(runner.filter_messages)),
            ),
        )

    if expected_value is not skip_value_check:
        cleaned_data = runner.cleaned_data
        expected = test_value if expected_value is unmodified else expected_value
        assert cleaned_data == expected

    return runner


@pytest.fixture
def assert_filter_passes():
    """
    Assertion fixture for testing that a filter passes without errors.

    Returns a callable that asserts the filter returns the specified value
    without errors.

    Args:
        filter_instance: The filter instance to test.
        test_value: The value to filter.
        expected_value: Expected filtered value (default: ``unmodified``).
    """

    def _assert_passes(filter_instance, test_value, expected_value=unmodified):
        return _run_filter_assertion(filter_instance, test_value, {}, expected_value)

    return _assert_passes


@pytest.fixture
def assert_filter_errors():
    """
    Assertion fixture for testing that a filter generates expected errors.

    Returns a callable that asserts the filter generates the specified error
    codes.

    Args:
        filter_instance: The filter instance to test.
        test_value: The value to filter.
        expected_codes: Expected error codes (list or dict).
        expected_value: Expected cleaned_data value (default: ``None``).
    """

    def _assert_errors(
        filter_instance, test_value, expected_codes, expected_value=None
    ):
        return _run_filter_assertion(
            filter_instance, test_value, expected_codes, expected_value
        )

    return _assert_errors
```

**Step 2: Run the new tests**

```
uv run pytest test/test_pytest_plugin.py -v
```

Expected: `test_module_exports` and sentinel tests pass; fixture tests **fail** because
the entry point is not registered yet (fixtures not injected).

---

### Task 3: Register the pytest11 entry point

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add the entry point**

In `pyproject.toml`, add after `[project.urls]`:

```toml
[project.entry-points."pytest11"]
filters = "filters.pytest_plugin"
```

**Step 2: Reinstall the package so the entry point is picked up**

```
uv sync --group=dev
```

**Step 3: Run the new tests again**

```
uv run pytest test/test_pytest_plugin.py -v
```

Expected: All 5 tests pass.

---

### Task 4: Slim down `test/conftest.py`

**Files:**
- Modify: `test/conftest.py`

**Step 1: Replace conftest.py contents**

Remove everything that moved to `pytest_plugin.py`. Keep only `Lengthy`, `Bytesy`, and
`Unicody`, plus a short updated module docstring. Remove the imports that are no longer
needed (`json`, `starmap`, `pformat`, `format_exception`, `pytest`).

```python
"""
Internal test helpers for the phx-filters test suite.

Fixtures (``assert_filter_passes``, ``assert_filter_errors``) and sentinels
(``unmodified``, ``skip_value_check``) are provided by the ``filters``
pytest plugin — no import needed.
"""

import typing


# Test helper classes for filters that need custom types
class Lengthy(typing.Sized):
    """
    A class that defines ``__len__``, used to test filters that check for
    object length.
    """

    def __init__(self, length):
        super().__init__()
        self.length = length

    def __len__(self):
        return self.length


class Bytesy:
    """
    A class that defines ``__bytes__``, used to test filters that convert
    values into byte strings.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __bytes__(self):
        return bytes(self.value)


class Unicody:
    """
    A class that defines ``__str__``, used to test filters that convert values
    into unicodes.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return str(self.value)
```

**Step 2: Run the full test suite**

```
uv run pytest
```

Expected: all tests pass (401 + 5 new = 406 total).

**Step 3: Verify test count**

```
uv run pytest --collect-only 2>&1 | tail -5
```

Expected: 406 tests collected.

---

### Task 5: Commit

```
uv run git add src/filters/pytest_plugin.py test/conftest.py test/test_pytest_plugin.py pyproject.toml
uv run git commit
```

Use the `creative-commits` skill for the commit message.
