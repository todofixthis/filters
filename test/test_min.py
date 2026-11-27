"""
Tests for the Min filter.
"""

from collections.abc import Callable
from typing import Any

import filters as f
from filters.handlers import FilterRunner


def test_min_pass_none(assert_filter_passes: Callable[..., FilterRunner[Any]]) -> None:
    """
    ``None`` always passes this Filter.

    Use ``Required | Min`` if you want to reject ``None``.
    """
    assert_filter_passes(f.Min(min_value=5), None)


def test_min_pass_greater_value(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is greater than the min value.
    """
    assert_filter_passes(f.Min(min_value=5), 8)


def test_min_pass_equal_value(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is equal to the min value.
    """
    assert_filter_passes(f.Min(min_value=5), 5)


def test_min_fail_equal_value_exclusive_comparison(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is equal to the min value, but the Filter is
    configured to use exclusive comparison.

    This is useful for infinite-precision floats and other cases
    where it is impossible to specify the min value exactly.
    """
    # The Filter is configured to allow any float value that is
    #   greater than - but not equal to - 5.0.
    assert_filter_errors(
        f.Min(min_value=5.0, exclusive=True),
        5.0,
        [f.Min.CODE_TOO_SMALL],
    )


def test_min_fail_lesser_value(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is less than the min value.
    """
    assert_filter_errors(
        f.Min(min_value=5),
        4,
        [f.Min.CODE_TOO_SMALL],
    )


def test_min_string_comparison_oddness(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    If the filter is being used on strings, the comparison is case
    sensitive.

    Note:  due to the way ASCII works, this may yield unexpected
    results (lowercase > uppercase).  Also, watch out for
    Unicode oddness!

    Basically what I'm trying to say is, don't use this filter on
    string values.
    """
    # ord('f') => 102
    # ord('F') => 70
    assert_filter_errors(
        f.Min(min_value="foo"),
        "Foo",
        [f.Min.CODE_TOO_SMALL],
    )
