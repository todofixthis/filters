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
            "request payload:\\n\\n{tracebacks}\\n\\n"
            "Filter Messages:\\n\\n{messages}".format(
                messages=pformat(dict(runner.filter_messages)),
                tracebacks=pformat(list(starmap(format_exception, runner.exc_info))),
            )
        )

    if isinstance(expected_codes, list):
        expected_codes = {"": expected_codes}

    if runner.error_codes != expected_codes:
        pytest.fail(
            "Filter generated unexpected error codes (expected "
            "{expected}):\\n\\n{messages}".format(
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
