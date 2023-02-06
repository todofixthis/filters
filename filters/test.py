import json
import typing
from itertools import starmap
from pprint import pformat
from traceback import format_exception
from unittest import TestCase

from filters.base import BaseFilter
from filters.handlers import FilterRunner

__all__ = [
    'BaseFilterTestCase',
]


def sorted_dict(value: typing.Mapping) -> typing.Any:
    """
    Sorts a dict's keys, to make it easier to compare filter messages from
    test failures.
    """
    if isinstance(value, typing.Mapping):
        # Note: ``dict`` preserves key insertion order since Python 3.6.
        # https://docs.python.org/3/library/stdtypes.html#dict
        return dict(
            (key, sorted_dict(value[key]))
                for key in sorted(value.keys())
        )

    elif isinstance(value, typing.Sequence) and not isinstance(value, str):
        return list(map(sorted_dict, value))

    else:
        return value


class BaseFilterTestCase(TestCase):
    """
    Base functionality for request filter unit tests.

    Prevents typos from causing invalid test passes/failures by abstracting the
    Filter type out of filtering ops; just set ``filter_type`` at the top of
    your test case, and then use ``assertFilterPasses`` and
    ``assertFilterErrors`` to check use cases.
    """
    filter_type: typing.Callable[[...], BaseFilter] = None

    class unmodified(object):
        """
        Used by ``assertFilterPasses`` so that you can omit the
        ``expected_value`` parameter.
        """
        pass

    class skip_value_check(object):
        """
        Sentinal value; used by ``assertFilterPasses`` to skip checking the
        filtered value.  This is useful for tests where a simple equality check
        is not practical.

        Note:  If you use ``skip_value_check``, you should add extra assertions
        to your test to make sure the filtered value conforms to expectations.
        """
        pass

    def assertFilterPasses(self,
            runner: typing.Any,
            expected_value: typing.Any = unmodified,
    ) -> FilterRunner:
        """
        Asserts that the FilterRunner returns the specified value, without
        errors.

        :param runner:
            Usually a FilterRunner instance, but you can pass in the test value
            itself if you want (it will automatically be run through
            ``_filter``).

        :param expected_value:
            The expected value for ``runner.cleaned_data``.

            If omitted, the assertion will check that the incoming value is
            returned unmodified.
        """
        return self.assertFilterErrors(runner, {}, expected_value)

    def assertFilterErrors(self,
            runner: typing.Any,
            expected_codes: typing.Union[
                typing.Mapping[str, typing.Sequence[str]],
                typing.Sequence[str],
            ],
            expected_value: typing.Any = None,
    ) -> FilterRunner:
        """
        Asserts that the FilterRunner generates the specified error codes.

        :param runner:
            Usually a FilterRunner instance, but you can pass in the test value
            itself if you want (it will automatically be run through
            `_filter`).

        :param expected_codes:
            Expected error codes.

        :param expected_value:
            Expected value for ``runner.cleaned_data`` (usually ``None``).
        """
        if not isinstance(runner, FilterRunner):
            runner: FilterRunner = self._filter(runner)

        # First check to make sure no unhandled exceptions occurred.
        if runner.has_exceptions:
            # noinspection PyTypeChecker
            self.fail(
                'Unhandled exceptions occurred while filtering the '
                'request payload:\n\n{tracebacks}\n\n'
                'Filter Messages:\n\n{messages}'.format(
                    messages=pformat(dict(runner.filter_messages)),

                    tracebacks=pformat(
                        list(starmap(format_exception, runner.exc_info))
                    ),
                )
            )

        if isinstance(expected_codes, list):
            expected_codes = {'': expected_codes}

        if runner.error_codes != expected_codes:
            self.fail(
                'Filter generated unexpected error codes (expected '
                '{expected}):\n\n{messages}'.format(
                    expected=json.dumps(sorted_dict(expected_codes)),
                    messages=pformat(dict(runner.filter_messages)),
                ),
            )

        check_value = (
                (self.skip_value_check is not True)
                and (expected_value is not self.skip_value_check)
        )

        if check_value:
            self._check_filter_value(
                runner.cleaned_data,
                runner.data
                if expected_value is self.unmodified
                else expected_value
            )

        # Return the ``FilterRunner`` instance, so that we can do some
        # additional checks if needed.
        return runner

    def _filter(self, *args, **kwargs) -> FilterRunner:
        """
        Applies the Filter to the specified value.

        Generally, you don't have to use this method in your test case, unless
        you want to specify Filter options.

        Example::

            self.filter_type = Min

            # Min().apply(42)
            self.assertFilterPasses(42)

            # Min(min_val=40).apply(42)
            self.assertFilterPasses(self._filter(42, min_val=40))

        :param args:
            Positional params to pass to the Filter's initializer.

        :param kwargs:
            Keyword params to pass to the Filter's initializer.
        """
        if not callable(self.filter_type):
            self.fail('{cls}.filter_type is not callable.'.format(
                cls=type(self).__name__,
            ))

        if not args:
            self.fail(
                'First argument to {cls}._filter '
                'must be the filtered value.'.format(
                    cls=type(self).__name__,
                ),
            )

        return FilterRunner(
            starting_filter=self.filter_type(*args[1:], **kwargs),
            incoming_data=args[0],
            capture_exc_info=True,
        )

    def _check_filter_value(self, cleaned_data, expected):
        """
        Checks the value returned by the Filter, used by
        ``assertFilterPasses``.

        In certain cases, it may be useful to override this method in your test
        case subclass.

        :param cleaned_data:
            ``cleaned_data`` from the FilterRunner.
        """
        self.assertEqual(cleaned_data, expected)
