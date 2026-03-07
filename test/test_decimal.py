"""
Tests for the Decimal filter.
"""

from decimal import Decimal

import pytest

import filters as f


def test_decimal_pass_none(assert_filter_passes):
    """
    `None` always passes this Filter.

    Use `Required | Decimal` if you want to reject `None`.
    """
    assert_filter_passes(f.Decimal(), None)


def test_decimal_pass_valid_decimal(assert_filter_passes):
    """
    The incoming value can be interpreted as a Decimal.
    """
    value = "3.1415926"
    assert_filter_passes(f.Decimal(), value, Decimal(value))


def test_decimal_pass_max_precision(assert_filter_passes):
    """
    You can limit the max precision of the resulting Decimal
    object.

    Note that a too-precise value is not considered invalid;
    instead, it gets rounded to the expected precision.
    """
    assert_filter_passes(f.Decimal(max_precision=3), "3.1415926", Decimal("3.142"))


def test_decimal_max_precision_quantised(assert_filter_passes):
    """
    ``max_precision`` can also be specified as a Decimal object.
    """
    assert_filter_passes(
        f.Decimal(max_precision=Decimal("0.001")), "3.1415926", Decimal("3.142")
    )


def test_decimal_pass_zero(assert_filter_passes):
    """
    0 is also considered a valid Decimal value.
    """
    value = "0"
    assert_filter_passes(f.Decimal(), value, Decimal(value))


def test_decimal_pass_scientific_notation(assert_filter_passes):
    """
    Scientific notation is considered valid, as in certain cases it
    may be the only way to represent a really large or small
    value.
    """
    value = "2.8E-12"
    assert_filter_passes(f.Decimal(), value, Decimal(value))


def test_decimal_pass_boolean(assert_filter_passes):
    """
    Booleans are technically ints, so they can be converted to
    Decimals.
    """
    value = True
    assert_filter_passes(f.Decimal(), value, Decimal(value))


def test_decimal_fail_invalid_value(assert_filter_errors):
    """
    The incoming value cannot be converted to a Decimal.
    """
    assert_filter_errors(
        f.Decimal(),
        "this is not a decimal",
        [f.Decimal.CODE_INVALID],
    )


@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "+Inf",
        "-Inf",
        # There are a few other possible non-finite values out there, but you get the idea.
    ],
)
def test_decimal_fail_non_finite_value(assert_filter_errors, value):
    """
    Non-finite values like 'NaN' and 'Inf' are considered invalid,
    even though they are technically parseable.
    """
    assert_filter_errors(f.Decimal(), value, [f.Decimal.CODE_NON_FINITE])


def test_decimal_pass_tuple(assert_filter_passes):
    """
    You may pass a 3-tuple for more control over how the resulting
    Decimal object is created.
    """
    value = (0, (4, 2), -1)
    assert_filter_passes(f.Decimal(), value, Decimal(value))


def test_decimal_fail_tuple_invalid(assert_filter_errors):
    """
    If you're going to use a tuple, you've got to make sure you get
    it right!
    """
    assert_filter_errors(f.Decimal(), ("1", "2", "3"), [f.Decimal.CODE_INVALID])


def test_decimal_fail_tuple_disallowed(assert_filter_errors):
    """
    The filter is configured to disallow tuple values.
    """
    assert_filter_errors(
        f.Decimal(allow_tuples=False),
        (0, (4, 2), -1),
        [f.Type.CODE_WRONG_TYPE],
    )


def test_decimal_fail_bytes(assert_filter_errors):
    """
    To ensure that the filter behaves the same in Python 2 and
    Python 3, bytes are not allowed.
    """
    assert_filter_errors(f.Decimal(), b"-12", [f.Type.CODE_WRONG_TYPE])


def test_decimal_fail_unsupported_type(assert_filter_errors):
    """
    The incoming value has an unsupported type.
    """
    assert_filter_errors(
        f.Decimal(),
        {0, (4, 2), -1},
        [f.Type.CODE_WRONG_TYPE],
    )
