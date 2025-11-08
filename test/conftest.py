"""
Pytest configuration and fixtures for the filters test suite.

This module provides shared fixtures and utilities that replace the functionality
of BaseFilterTestCase for modern pytest-based testing.
"""

import json
import typing
from itertools import starmap
from pprint import pformat
from traceback import format_exception

import pytest

from filters.handlers import FilterRunner


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

    :param filter_instance: The filter instance to test
    :param test_value: The value to filter
    :param expected_codes: Expected error codes
    :param expected_value: Expected value for cleaned_data
    """
    runner = FilterRunner(
        starting_filter=filter_instance,
        incoming_data=test_value,
        capture_exc_info=True,
    )

    # First check to make sure no unhandled exceptions occurred.
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

    # Return the FilterRunner instance for additional checks if needed
    return runner


@pytest.fixture
def assert_filter_passes():
    """
    Assertion fixture for testing that a filter passes without errors.

    Returns a function that asserts the filter returns the specified value
    without errors.
    """

    def _assert_passes(filter_instance, test_value, expected_value=unmodified):
        """
        Asserts that the filter passes with the expected value.

        :param filter_instance: The filter instance to test
        :param test_value: The value to filter
        :param expected_value: The expected filtered value (defaults to unmodified)
        """
        return _run_filter_assertion(filter_instance, test_value, {}, expected_value)

    return _assert_passes


@pytest.fixture
def assert_filter_errors():
    """
    Assertion fixture for testing that a filter generates expected errors.

    Returns a function that asserts the filter generates the specified error codes.
    """

    def _assert_errors(
        filter_instance, test_value, expected_codes, expected_value=None
    ):
        """
        Asserts that the filter generates the specified error codes.

        :param filter_instance: The filter instance to test
        :param test_value: The value to filter
        :param expected_codes: Expected error codes
        :param expected_value: Expected value for cleaned_data (usually None)
        """
        return _run_filter_assertion(
            filter_instance, test_value, expected_codes, expected_value
        )

    return _assert_errors


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
