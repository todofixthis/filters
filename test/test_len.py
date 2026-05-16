"""
Tests for the Len filter.
"""

import pytest

import filters as f
from .conftest import Lengthy

# ---------------------------------------------------------------------------
# None passthrough
# ---------------------------------------------------------------------------


def test_len_pass_none(assert_filter_passes):
    """None always passes — use ``Required | Len(...)`` to reject null values."""
    assert_filter_passes(f.Len(4), None)


# ---------------------------------------------------------------------------
# Exact mode  [Len(n)]
# ---------------------------------------------------------------------------


def test_len_exact_pass(assert_filter_passes):
    """Value length matches the exact constraint."""
    assert_filter_passes(f.Len(3), "foo")


def test_len_exact_fail_too_long(assert_filter_errors):
    """Value is longer than the exact constraint."""
    assert_filter_errors(f.Len(3), "foobar", [f.Len.CODE_TOO_LONG])


def test_len_exact_fail_too_short(assert_filter_errors):
    """Value is shorter than the exact constraint."""
    assert_filter_errors(f.Len(3), "hi", [f.Len.CODE_TOO_SHORT])


def test_len_exact_zero(assert_filter_passes):
    """Len(0) passes an empty value."""
    assert_filter_passes(f.Len(0), "")


# ---------------------------------------------------------------------------
# Min-only mode  [Len(min=n)]
# ---------------------------------------------------------------------------


def test_len_min_pass(assert_filter_passes):
    """Value length is equal to the minimum."""
    assert_filter_passes(f.Len(min=3), "foo")


def test_len_min_pass_longer(assert_filter_passes):
    """Value length exceeds the minimum."""
    assert_filter_passes(f.Len(min=3), "foobar")


def test_len_min_fail_too_short(assert_filter_errors):
    """Value is shorter than the minimum."""
    assert_filter_errors(f.Len(min=5), "hi", [f.Len.CODE_TOO_SHORT])


# ---------------------------------------------------------------------------
# Max-only mode  [Len(max=n)]
# ---------------------------------------------------------------------------


def test_len_max_pass(assert_filter_passes):
    """Value length is equal to the maximum."""
    assert_filter_passes(f.Len(max=3), "foo")


def test_len_max_pass_shorter(assert_filter_passes):
    """Value length is below the maximum."""
    assert_filter_passes(f.Len(max=5), "hi")


def test_len_max_fail_too_long(assert_filter_errors):
    """Value exceeds the maximum length."""
    assert_filter_errors(f.Len(max=3), "foobar", [f.Len.CODE_TOO_LONG])


def test_len_max_zero(assert_filter_passes):
    """Len(max=0) passes an empty value."""
    assert_filter_passes(f.Len(max=0), "")


# ---------------------------------------------------------------------------
# Range mode  [Len(min=m, max=n)]
# ---------------------------------------------------------------------------


def test_len_range_pass(assert_filter_passes):
    """Value length is within the range."""
    assert_filter_passes(f.Len(min=2, max=4), "foo")


def test_len_range_pass_at_min(assert_filter_passes):
    """Value length equals the minimum of the range."""
    assert_filter_passes(f.Len(min=2, max=4), "hi")


def test_len_range_pass_at_max(assert_filter_passes):
    """Value length equals the maximum of the range."""
    assert_filter_passes(f.Len(min=2, max=4), "foob")


def test_len_range_fail_too_long(assert_filter_errors):
    """Value is longer than the range maximum."""
    assert_filter_errors(f.Len(min=2, max=4), "foobar", [f.Len.CODE_TOO_LONG])


def test_len_range_fail_too_short(assert_filter_errors):
    """Value is shorter than the range minimum."""
    assert_filter_errors(f.Len(min=2, max=4), "x", [f.Len.CODE_TOO_SHORT])


def test_len_range_equal_bounds(assert_filter_passes):
    """min == max is a valid range (equivalent to exact mode)."""
    assert_filter_passes(f.Len(min=3, max=3), "foo")


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        ["foo", "bar", "baz"],
        {"a": 1, "b": 2, "c": 3},
        Lengthy(3),
    ],
)
def test_len_exact_pass_collections(assert_filter_passes, value):
    """Exact mode works on lists, dicts, and Sized objects."""
    assert_filter_passes(f.Len(3), value)


@pytest.mark.parametrize(
    "value",
    [
        ["foo", "bar", "baz"],
        {"a": 1, "b": 2, "c": 3},
        Lengthy(3),
    ],
)
def test_len_min_pass_collections(assert_filter_passes, value):
    """Min-only mode works on lists, dicts, and Sized objects."""
    assert_filter_passes(f.Len(min=2), value)


@pytest.mark.parametrize(
    "value",
    [
        ["foo", "bar", "baz"],
        {"a": 1, "b": 2, "c": 3},
        Lengthy(3),
    ],
)
def test_len_max_pass_collections(assert_filter_passes, value):
    """Max-only mode works on lists, dicts, and Sized objects."""
    assert_filter_passes(f.Len(max=4), value)


# ---------------------------------------------------------------------------
# Invalid configuration — all must raise ValueError at init time
# ---------------------------------------------------------------------------


def test_len_invalid_exact_with_min():
    """Mixing positional exact with min is not allowed."""
    with pytest.raises(ValueError):
        f.Len(4, min=2)


def test_len_invalid_exact_with_max():
    """Mixing positional exact with max is not allowed."""
    with pytest.raises(ValueError):
        f.Len(4, max=4)


def test_len_invalid_exact_with_min_and_max():
    """Mixing positional exact with both min and max is not allowed."""
    with pytest.raises(ValueError):
        f.Len(4, min=2, max=4)


def test_len_invalid_negative_exact():
    """Negative exact length is not allowed."""
    with pytest.raises(ValueError):
        f.Len(-1)


def test_len_invalid_negative_min():
    """Negative min is not allowed."""
    with pytest.raises(ValueError):
        f.Len(min=-1)


def test_len_invalid_negative_max():
    """Negative max is not allowed."""
    with pytest.raises(ValueError):
        f.Len(max=-1)


def test_len_invalid_min_greater_than_max():
    """min > max is not allowed."""
    with pytest.raises(ValueError):
        f.Len(min=4, max=2)


def test_len_invalid_no_args():
    """Calling Len() with no arguments is not allowed."""
    with pytest.raises(ValueError):
        f.Len()
