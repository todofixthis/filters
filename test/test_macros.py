"""
Unit tests for :py:func:`filter_macro`.
"""

from datetime import datetime

from pytz import utc

import filters as f
from filters.macros import FilterMacroType, filter_macro


def test_filter_macro_decorator(assert_filter_passes, assert_filter_errors):
    """
    A common use case for Filter macros is to use them as
    decorators for functions.
    """

    @filter_macro
    def MyFilter():
        return f.Unicode | f.Strip | f.MinLength(12)

    # You can use :py:class:`FilterMacroType` to detect a filter
    # macro.
    assert issubclass(MyFilter, FilterMacroType)

    # As you would expect, invoking the macro returns a
    # FilterChain.
    the_filter = MyFilter()

    assert not isinstance(the_filter, FilterMacroType)
    assert isinstance(the_filter, f.FilterChain)

    assert_filter_passes(the_filter, "  Hello, world!  ", "Hello, world!")
    assert_filter_errors(the_filter, "Hi there!", [f.MinLength.CODE_TOO_SHORT])


def test_filter_macro_chain(assert_filter_passes, assert_filter_errors):
    """
    You can chain Filter macros with other Filters, the same as you
    would with any other Filter.
    """

    @filter_macro
    def MyFilter():
        return f.Unicode | f.Strip | f.MinLength(12)

    # Note that you don't have to invoke the macro to include it in
    # a chain.
    # If you don't believe me, try removing the decorator from
    # ``MyFilter``, and watch this test explode.
    filter_chain = MyFilter | f.Split(r"\s+")

    assert_filter_passes(filter_chain, "Hello, world!", ["Hello,", "world!"])
    assert_filter_errors(filter_chain, "Hi there!", [f.MinLength.CODE_TOO_SHORT])


def test_filter_macro_chain_macros(assert_filter_passes, assert_filter_errors):
    """
    Yup, you can chain Filter macros together, too.
    """

    @filter_macro
    def Filter1():
        return f.Unicode | f.Strip

    @filter_macro
    def Filter2():
        return f.Split(r"\s+") | f.MinLength(2)

    filter_chain = Filter1 | Filter2

    assert_filter_passes(filter_chain, "  Hello, world!  ", ["Hello,", "world!"])
    assert_filter_errors(filter_chain, "whazzup!", [f.MinLength.CODE_TOO_SHORT])


def test_filter_macro_optional_parameters(assert_filter_passes, assert_filter_errors):
    """
    A filter macro may accept optional parameters.
    """

    @filter_macro
    def MyFilter(min_length=12):
        return f.Unicode | f.MinLength(min_length)

    # `MyFilter` is configured to require 12 chars by default.
    filter_chain = f.Required | MyFilter

    assert_filter_passes(filter_chain, "Hello, world!", "Hello, world!")
    assert_filter_errors(filter_chain, "Hi there!", [f.MinLength.CODE_TOO_SHORT])


def test_filter_macro_partial(assert_filter_passes):
    """
    You can use Filter macros to create partials from other Filter
    types.
    """
    MyDatetime = filter_macro(f.Datetime, timezone=12)

    # By default, MyDatetime assumes a timezone of UTC+12...
    assert_filter_passes(
        MyDatetime(),
        "2015-10-13 15:22:18",
        datetime(2015, 10, 13, 3, 22, 18, tzinfo=utc),
    )
    # ... however, we can override it — note the hour is 09:00 UTC
    # (not 03:00), reflecting the smaller UTC+6 offset.
    assert_filter_passes(
        MyDatetime(timezone=6),
        "2015-10-13 15:22:18",
        datetime(2015, 10, 13, 9, 22, 18, tzinfo=utc),
    )
