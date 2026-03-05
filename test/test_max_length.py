"""
Tests for the MaxLength filter.
"""

import pytest

import filters as f
from .conftest import Lengthy


def test_max_length_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | MaxLength`` if you want to reject null values.
    """
    assert_filter_passes(
        f.MaxLength(max_length=0),
        None,
    )


def test_max_length_pass_short(assert_filter_passes):
    """
    The incoming value is shorter than the max length.
    """
    assert_filter_passes(
        f.MaxLength(max_length=6),
        "Hello",
    )


def test_max_length_pass_max_length(assert_filter_passes):
    """
    The incoming value has the max allowed length.
    """
    assert_filter_passes(
        f.MaxLength(max_length=5),
        "World",
    )


def test_max_length_fail_long(assert_filter_errors):
    """
    The incoming value is longer than the max length.
    """
    assert_filter_errors(
        f.MaxLength(max_length=5),
        "Goodbye",
        [f.MaxLength.CODE_TOO_LONG],
    )


def test_max_length_pass_truncated(assert_filter_passes):
    """
    The filter is configured to truncate values that are too long.
    """
    assert_filter_passes(
        f.MaxLength(max_length=3, truncate=True),
        ["foo", "bar", "baz", "luhrmann"],
        ["foo", "bar", "baz"],
    )


def test_max_length_multi_byte_characters(assert_filter_passes, assert_filter_errors):
    """
    Multibyte characters are treated differently depending on whether you
    pass in a unicode or a byte string.
    """
    # "Hello world" in Chinese:
    decoded_value = "\u4f60\u597d\u4e16\u754c"
    encoded_value = decoded_value.encode("utf-8")

    # The string version of the string contains 4 code points.
    assert_filter_passes(
        f.MaxLength(max_length=4),
        decoded_value,
    )

    # The bytes version of the string contains 12 bytes.
    assert_filter_errors(
        f.MaxLength(max_length=4),
        encoded_value,
        [f.MaxLength.CODE_TOO_LONG],
    )


@pytest.mark.parametrize(
    "max_length,value",
    [
        (4, ["foo", "bar", "baz", "luhrmann"]),
        (3, {"foo": "bar", "baz": "luhrmann"}),
        (4, Lengthy(4)),
        # etc.
    ],
)
def test_max_length_pass_short_collection(assert_filter_passes, max_length, value):
    """
    The incoming value is a collection with length less than or equal to
    the max length.
    """
    assert_filter_passes(f.MaxLength(max_length=max_length), value)


@pytest.mark.parametrize(
    "max_length,value",
    [
        (3, ["foo", "bar", "baz", "luhrmann"]),
        (1, {"foo": "bar", "baz": "luhrmann"}),
        (3, Lengthy(4)),
        # etc.
    ],
)
def test_max_length_fail_long_collection(assert_filter_errors, max_length, value):
    """
    The incoming value is a collection with length greater than the max
    length.
    """
    assert_filter_errors(
        f.MaxLength(max_length=max_length), value, [f.MaxLength.CODE_TOO_LONG]
    )
