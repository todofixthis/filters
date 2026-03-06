"""
Tests for the NotEmpty filter.
"""

import pytest

import filters as f
from .conftest import Lengthy


def test_not_empty_pass_none(assert_filter_passes):
    """
    By default, :py:class:`f.NotEmpty` will treat ``None`` as valid, just
    like every other filter.

    Unlike every other filter, however, the strategy for rejecting null
    values is a wee bit different, as we'll see in the next test.
    """
    assert_filter_passes(
        f.NotEmpty(),
        None,
    )


def test_not_empty_fail_none(assert_filter_errors):
    """
    You can configure the filter to reject null values.
    """
    assert_filter_errors(
        f.NotEmpty(allow_none=False),
        None,
        [f.NotEmpty.CODE_EMPTY],
    )


def test_not_empty_pass_non_empty_string(assert_filter_passes):
    """
    The incoming value is a non-empty string.
    """
    assert_filter_passes(
        f.NotEmpty(),
        "Hello, world!",
    )


@pytest.mark.parametrize(
    "value",
    [
        # The values in the collection may be empty, but the collection itself
        # is not.
        ["", "", ""],
        {"": ""},
        Lengthy(1),
        # etc.
    ],
)
def test_not_empty_pass_non_empty_collection(assert_filter_passes, value):
    """
    The incoming value is a collection with length > 0.
    """
    assert_filter_passes(
        f.NotEmpty(),
        value,
    )


def test_not_empty_pass_non_collection(assert_filter_passes):
    """
    The incoming value does not have a length.
    """
    assert_filter_passes(
        f.NotEmpty(),
        object(),
    )


def test_not_empty_fail_empty_string(assert_filter_errors):
    """
    The incoming value is an empty string.
    """
    assert_filter_errors(
        f.NotEmpty(),
        "",
        [f.NotEmpty.CODE_EMPTY],
    )


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        Lengthy(0),
        # etc.
    ],
)
def test_not_empty_fail_empty_collection(assert_filter_errors, value):
    """
    The incoming value is a collection with length < 1.
    """
    assert_filter_errors(
        f.NotEmpty(),
        value,
        [f.NotEmpty.CODE_EMPTY],
    )


def test_not_empty_zero_is_not_empty(assert_filter_passes):
    """
    PHP developers take note!
    """
    assert_filter_passes(
        f.NotEmpty(),
        0,
    )


def test_not_empty_false_is_not_empty(assert_filter_passes):
    """
    The boolean value ``False`` is NOT considered empty because it
    represents SOME kind of value.
    """
    assert_filter_passes(
        f.NotEmpty(),
        False,
    )
