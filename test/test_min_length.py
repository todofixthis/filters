"""
Tests for the MinLength filter.
"""

import filters as f
from .conftest import Lengthy


def test_min_length_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use `Required | MinLength` if you want to reject null values.
    """
    assert_filter_passes(
        f.MinLength(min_length=5),
        None,
    )


def test_min_length_pass_long(assert_filter_passes):
    """
    The incoming value has length greater than the minimum value.
    """
    assert_filter_passes(
        f.MinLength(min_length=2),
        "Hello",
    )


def test_min_length_pass_min_length(assert_filter_passes):
    """
    The incoming value has length equal to the minimum value.
    """
    assert_filter_passes(
        f.MinLength(min_length=5),
        "World",
    )


def test_min_length_fail_short(assert_filter_errors):
    """
    The incoming value has length less than the minimum value.
    """
    assert_filter_errors(
        f.MinLength(min_length=10),
        "Goodbye",
        [f.MinLength.CODE_TOO_SHORT],
    )


def test_min_length_multi_byte_characters(assert_filter_passes, assert_filter_errors):
    """
    Multibyte characters are treated differently depending on whether you
    pass in a unicode or a byte string.
    """
    # "Hello world" in Chinese:
    decoded_value = "\u4f60\u597d\u4e16\u754c"
    encoded_value = decoded_value.encode("utf-8")

    # The string version of the string contains 4 code points.
    assert_filter_errors(
        f.MinLength(min_length=12),
        decoded_value,
        [f.MinLength.CODE_TOO_SHORT],
    )

    # The bytes version of the string contains 12 bytes.
    assert_filter_passes(
        f.MinLength(min_length=12),
        encoded_value,
    )


def test_min_length_pass_long_collection(assert_filter_passes):
    """
    The incoming value is a collection with length greater than or equal to
    the minimum value.
    """
    assert_filter_passes(
        f.MinLength(min_length=3),
        ["foo", "bar", "baz", "luhrmann"],
    )

    assert_filter_passes(
        f.MinLength(min_length=1),
        {"foo": "bar", "baz": "luhrmann"},
    )

    assert_filter_passes(
        f.MinLength(min_length=5),
        Lengthy(6),
    )

    # etc.


def test_min_length_fail_short_collection(assert_filter_errors):
    """
    The incoming value is a collection with length less than the minimum
    value.
    """
    assert_filter_errors(
        f.MinLength(min_length=5),
        ["foo", "bar", "baz", "luhrmann"],
        [f.MinLength.CODE_TOO_SHORT],
    )

    assert_filter_errors(
        f.MinLength(min_length=3),
        {"foo": "bar", "baz": "luhrmann"},
        [f.MinLength.CODE_TOO_SHORT],
    )

    assert_filter_errors(
        f.MinLength(min_length=7),
        Lengthy(6),
        [f.MinLength.CODE_TOO_SHORT],
    )

    # etc.
