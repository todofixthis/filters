"""
Tests for the Empty filter.
"""

from collections.abc import Callable
from typing import Any

import pytest

import filters as f
from filters.handlers import FilterRunner

from .conftest import Lengthy


def test_empty_pass_none(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    ``None`` shall pass.

    What?

    ``None`` shall pass!
    """
    assert_filter_passes(f.Empty(), None)


def test_empty_pass_empty_string(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is an empty string.
    """
    assert_filter_passes(f.Empty(), "")


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        Lengthy(0),
        # etc.
    ],
)
def test_empty_pass_empty_collection(
    assert_filter_passes: Callable[..., FilterRunner[Any]], value: Any
) -> None:
    """
    The incoming value is a collection with length < 1.
    """
    assert_filter_passes(f.Empty(), value)


def test_empty_fail_non_empty_string(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is a non-empty string.
    """
    assert_filter_errors(
        f.Empty(),
        "Goodbye world!",
        [f.Empty.CODE_NOT_EMPTY],
    )


@pytest.mark.parametrize(
    "value",
    [
        # The values inside the collection may be empty, but the collection
        # itself is not.
        ["", "", ""],
        {"": ""},
        Lengthy(1),
        # etc.
    ],
)
def test_empty_fail_non_empty_collection(
    assert_filter_errors: Callable[..., FilterRunner[Any]], value: Any
) -> None:
    """
    The incoming value is a collection with length > 0.
    """
    assert_filter_errors(f.Empty(), value, [f.Empty.CODE_NOT_EMPTY])


def test_empty_fail_non_collection(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value does not have a length.
    """
    # The filter can't determine the length of this object, so it assumes
    # that it is not empty.
    assert_filter_errors(f.Empty(), object(), [f.Empty.CODE_NOT_EMPTY])


def test_empty_zero_is_not_empty(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    PHP developers take note!
    """
    assert_filter_errors(f.Empty(), 0, [f.Empty.CODE_NOT_EMPTY])


def test_empty_false_is_not_empty(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The boolean value ``False`` is NOT considered empty because it
    represents SOME kind of value.
    """
    assert_filter_errors(f.Empty(), False, [f.Empty.CODE_NOT_EMPTY])
