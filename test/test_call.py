"""
Tests for the Call filter.
"""

import filters as f


def test_call_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Call`` if you want to reject null values.
    """

    def always_fail(value):
        raise ValueError("{value} is not valid!".format(value=value))

    assert_filter_passes(f.Call(always_fail), None)


def test_call_pass_successful_execution(assert_filter_passes):
    """
    The callable runs successfully.
    """

    def is_odd(value):
        return value % 2

    assert_filter_passes(
        f.Call(is_odd),
        6,
        # Note that ANY value returned by the callable is considered valid;
        # if you want custom handling of some values, you're better off
        # creating a custom filter type (it's super easy!).
        False,
    )


def test_call_fail_filter_error(assert_filter_errors):
    """
    The callable raises a :py:class:`FilterError`.
    """

    def even_only(value):
        if value % 2:
            raise f.FilterError("value is not even!")
        return value

    assert_filter_errors(f.Call(even_only), 5, ["value is not even!"])


def test_call_fail_filter_error_custom_code(assert_filter_errors):
    """
    The callable raises a :py:class:`FilterError` with a custom error code.
    """

    def even_only(value):
        if value % 2:
            # If you find yourself doing this, you would probably be better
            # served by creating a custom filter instead.
            error = f.FilterError("value is not even!")
            error.context = {"code": "not_even"}
            raise error
        return value

    assert_filter_errors(
        f.Call(even_only),
        5,
        ["not_even"],
    )


def test_call_error_exception():
    """
    The callable raises an exception other than a :py:class:`FilterError`.
    """

    def even_only(value):
        if value % 2:
            raise ValueError("{value} is not even!")
        return value

    filter_runner = f.FilterRunner(f.Call(even_only), 5)

    # :py:class:`Call` assumes that any exception other than a
    # :py:class:`FilterError` represents an error in the code.
    assert filter_runner.has_exceptions
