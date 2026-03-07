"""
Tests for the Round filter.
"""

from decimal import Decimal, ROUND_CEILING

import filters as f


def test_round_pass_none(assert_filter_passes):
    """
    `None` always passes this filter.

    Use `Required | Round` to reject incoming `None`.
    """
    assert_filter_passes(f.Round(), None)


def test_round_pass_round_integer_to_nearest_integer(assert_filter_passes):
    """
    Rounds an integer to the nearest integer value.
    """
    # You should always specify `to_nearest` as a string, to
    # avoid floating point issues.
    assert_filter_passes(
        f.Round(to_nearest="5"),
        42,
        # The result is always a Decimal object.
        Decimal("40.0"),
    )


def test_round_pass_round_integer_to_nearest_float(assert_filter_passes):
    """
    Rounds an integer to the nearest float value.
    """
    assert_filter_passes(
        f.Round(to_nearest="5.5"),
        42,
        Decimal("44.0"),
    )


def test_round_pass_round_float_to_nearest_integer(assert_filter_passes):
    """
    Rounds a float to the nearest integer value.
    """
    assert_filter_passes(
        f.Round(to_nearest="1"),
        3.5,
        Decimal("4.0"),
    )


def test_round_pass_round_float_to_nearest_float(assert_filter_passes):
    """
    Rounds a float to the nearest float value.
    """
    # Just to be tricky, use a float value that would normally
    # result in some nasty floating point artifacts.
    # http://stackoverflow.com/a/4340355
    assert_filter_passes(
        f.Round(to_nearest="0.05"),
        1.368161685161,
        Decimal("1.35"),
    )


def test_round_pass_round_string_float(assert_filter_passes):
    """
    Rounds a float represented as a string to avoid floating point
    issues.
    """
    # http://stackoverflow.com/q/22599883
    assert_filter_passes(
        f.Round(to_nearest="0.1"),
        "2.775",
        Decimal("2.8"),
    )


def test_round_pass_round_to_big_value(assert_filter_passes):
    """
    Rounds something to a value greater than 1.
    """
    assert_filter_passes(
        f.Round(to_nearest="20"),
        "386.428",
        Decimal("380"),
    )


def test_round_pass_round_negative_value(assert_filter_passes):
    """
    Rounds a negative value.
    """
    assert_filter_passes(
        f.Round(to_nearest="0.1"),
        "-2.775",
        Decimal("-2.8"),
    )


def test_round_pass_modify_rounding(assert_filter_passes):
    """
    By default, the filter will round up any value that is halfway
    to the nearest `to_nearest` value, but this behaviour can be
    customized.
    """
    assert_filter_passes(
        f.Round(rounding=ROUND_CEILING),
        "0.00000000001",
        Decimal("1"),
    )


def test_round_pass_custom_result_type(assert_filter_passes):
    """
    You can customize the return type of the filter.
    """
    assert_filter_passes(
        f.Round(result_type=int),
        "2.775",
        3,
    )


def test_round_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not numeric.
    """
    assert_filter_errors(f.Round(), "three", [f.Decimal.CODE_INVALID])
