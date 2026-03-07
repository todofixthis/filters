import json
from collections.abc import Callable, Mapping, Sequence
from itertools import starmap
from pprint import pformat
from traceback import format_exception
from typing import Any
from unittest import TestCase

from filters.base import BaseFilter
from filters.handlers import FilterRunner

__all__ = [
    "BaseFilterTestCase",
]


def sorted_dict(value: Mapping) -> Any:
    """Sorts a dict's keys for easier comparison.

    Sorts a dict's keys, to make it easier to compare filter messages
    from test failures.

    Args:
        value: The value to sort (can be dict, list, or other).

    Returns:
        The value with sorted dict keys at all levels.
    """
    if isinstance(value, Mapping):
        # Note: ``dict`` preserves key insertion order since Python 3.6.
        # https://docs.python.org/3/library/stdtypes.html#dict
        return dict((key, sorted_dict(value[key])) for key in sorted(value.keys()))

    elif isinstance(value, Sequence) and not isinstance(value, str):
        return list(map(sorted_dict, value))

    else:
        return value


class BaseFilterTestCase(TestCase):
    """Base functionality for request filter unit tests.

    Prevents typos from causing invalid test passes/failures by
    abstracting the Filter type out of filtering ops; just set
    ``filter_type`` at the top of your test case, and then use
    ``assertFilterPasses`` and ``assertFilterErrors`` to check use
    cases.
    """

    filter_type: Callable[[...], BaseFilter] = None

    class unmodified(object):
        """Used by assertFilterPasses to omit expected_value parameter.

        Used by ``assertFilterPasses`` so that you can omit the
        ``expected_value`` parameter.
        """

        pass

    class skip_value_check(object):
        """Sentinel value to skip checking the filtered value.

        Sentinel value; used by ``assertFilterPasses`` to skip
        checking the filtered value. This is useful for tests where a
        simple equality check is not practical.

        Note:
            If you use ``skip_value_check``, you should add extra
            assertions to your test to make sure the filtered value
            conforms to expectations.
        """

        pass

    def assertFilterPasses(
        self,
        runner: Any,
        expected_value: Any = unmodified,
    ) -> FilterRunner:
        """Asserts that the FilterRunner returns the value without errors.

        Args:
            runner: Usually a FilterRunner instance, but you can pass
                in the test value itself if you want (it will
                automatically be run through ``_filter``).
            expected_value: The expected value for
                ``runner.cleaned_data``.

                If omitted, the assertion will check that the incoming
                value is returned unmodified.

        Returns:
            The FilterRunner instance for further assertions.
        """
        return self.assertFilterErrors(runner, {}, expected_value)

    def assertFilterErrors(
        self,
        runner: Any,
        expected_codes: Mapping[str, Sequence[str]] | Sequence[str],
        expected_value: Any = None,
    ) -> FilterRunner:
        """Asserts that the FilterRunner generates the specified errors.

        Args:
            runner: Usually a FilterRunner instance, but you can pass
                in the test value itself if you want (it will
                automatically be run through `_filter`).
            expected_codes: Expected error codes.
            expected_value: Expected value for ``runner.cleaned_data``
                (usually ``None``).

        Returns:
            The FilterRunner instance for further assertions.
        """
        if not isinstance(runner, FilterRunner):
            runner: FilterRunner = self._filter(runner)

        # First check to make sure no unhandled exceptions occurred.
        if runner.has_exceptions:
            # noinspection PyTypeChecker
            self.fail(
                f"Unhandled exceptions occurred while filtering the "
                f"request payload:\n\n"
                f"{pformat(list(starmap(format_exception, runner.exc_info)))}\n\n"
                f"Filter Messages:\n\n{pformat(dict(runner.filter_messages))}"
            )

        if isinstance(expected_codes, list):
            expected_codes = {"": expected_codes}

        if runner.error_codes != expected_codes:
            self.fail(
                f"Filter generated unexpected error codes (expected "
                f"{json.dumps(sorted_dict(expected_codes))}):\n\n"
                f"{pformat(dict(runner.filter_messages))}",
            )

        check_value = (self.skip_value_check is not True) and (
            expected_value is not self.skip_value_check
        )

        if check_value:
            self._check_filter_value(
                runner.cleaned_data,
                runner.data if expected_value is self.unmodified else expected_value,
            )

        # Return the ``FilterRunner`` instance, so that we can do some
        # additional checks if needed.
        return runner

    def _filter(self, *args, **kwargs) -> FilterRunner:
        """Applies the Filter to the specified value.

        Generally, you don't have to use this method in your test
        case, unless you want to specify Filter options.

        Example::

            self.filter_type = Min

            # Min().apply(42)
            self.assertFilterPasses(42)

            # Min(min_val=40).apply(42)
            self.assertFilterPasses(self._filter(42, min_val=40))

        Args:
            *args: Positional params to pass to the Filter's
                initialiser.
            **kwargs: Keyword params to pass to the Filter's
                initialiser.

        Returns:
            FilterRunner instance with the filter applied to the value.
        """
        if not callable(self.filter_type):
            self.fail(f"{type(self).__name__}.filter_type is not callable.")

        if not args:
            self.fail(
                f"First argument to {type(self).__name__}._filter "
                "must be the filtered value.",
            )

        return FilterRunner(
            starting_filter=self.filter_type(*args[1:], **kwargs),
            incoming_data=args[0],
            capture_exc_info=True,
        )

    def _check_filter_value(self, cleaned_data, expected):
        """Checks the value returned by the Filter.

        Used by ``assertFilterPasses``.

        In certain cases, it may be useful to override this method in
        your test case subclass.

        Args:
            cleaned_data: ``cleaned_data`` from the FilterRunner.
            expected: The expected value.
        """
        self.assertEqual(cleaned_data, expected)
