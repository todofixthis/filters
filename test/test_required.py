"""
Tests for the Required filter.
"""

import pytest

import filters as f
from .conftest import Lengthy


def test_required_fail_none(assert_filter_errors):
    """
    :py:class:`f.Required` is the only filter that does not allow null
    values.
    """
    assert_filter_errors(f.Required(), None, [f.Required.CODE_EMPTY])


def test_required_pass_non_empty_string(assert_filter_passes):
    """
    The incoming value is a non-empty string.
    """
    assert_filter_passes(f.Required(), "Hello, world!")


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
def test_required_pass_non_empty_collection(assert_filter_passes, value):
    """
    The incoming value is a collection with length > 0.
    """
    assert_filter_passes(f.Required(), value)


def test_required_pass_non_collection(assert_filter_passes):
    """
    Any value that does not have a length is assumed to be not empty.
    """
    assert_filter_passes(f.Required(), object())


def test_required_fail_empty_string(assert_filter_errors):
    """
    The incoming value is an empty string.
    """
    assert_filter_errors(f.Required(), "", [f.Required.CODE_EMPTY])


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        Lengthy(0),
        # etc.
    ],
)
def test_required_fail_empty_collection(assert_filter_errors, value):
    """
    The incoming value is a collection with length < 1.
    """
    assert_filter_errors(f.Required(), value, [f.Required.CODE_EMPTY])


def test_required_zero_is_not_empty(assert_filter_passes):
    """
    PHP developers take note!
    """
    assert_filter_passes(f.Required(), 0)


def test_required_false_is_not_empty(assert_filter_passes):
    """
    The boolean value ``False`` is NOT considered empty because it
    represents SOME kind of value.
    """
    assert_filter_passes(f.Required(), False)
