"""
Tests for the Int filter.
"""

import filters as f


def test_int_pass_none(assert_filter_passes):
    """
    `None` always passes this Filter.

    Use `Required | Int` if you want to reject `None`.
    """
    assert_filter_passes(f.Int(), None)


def test_int_pass_valid_int(assert_filter_passes):
    """
    The incoming value can be interpreted as an int.
    """
    assert_filter_passes(f.Int(), "42", 42)


def test_int_pass_zero(assert_filter_passes):
    """
    The incoming value is zero.
    """
    assert_filter_passes(f.Int(), "0", 0)


def test_int_pass_negative(assert_filter_passes):
    """
    The incoming value is a negative int.
    """
    assert_filter_passes(f.Int(), "-314", -314)


def test_int_pass_boolean(assert_filter_passes):
    """
    Booleans are technically ints.
    """
    assert_filter_passes(f.Int(), True, 1)


def test_int_fail_invalid_value(assert_filter_errors):
    """
    The incoming value cannot be interpreted as a number, let alone
    an integer.
    """
    assert_filter_errors(
        f.Int(),
        "this is not an int",
        [f.Decimal.CODE_INVALID],
    )


def test_int_fail_bytes(assert_filter_errors):
    """
    To ensure that the filter behaves the same in Python 2 and
    Python 3, bytes are not allowed.
    """
    assert_filter_errors(f.Int(), b"-12", [f.Type.CODE_WRONG_TYPE])


def test_int_fail_float_value(assert_filter_errors):
    """
    The incoming value contains significant digits after the
    decimal point.
    """
    assert_filter_errors(
        f.Int(),
        "42.01",
        [f.Int.CODE_DECIMAL],
    )


def test_int_pass_int_point_zero(assert_filter_passes):
    """
    The incoming value contains only insignificant digits after the
    decimal point.
    """
    assert_filter_passes(f.Int(), "42.0000000000000", 42)


def test_int_pass_scientific_notation(assert_filter_passes):
    """
    The incoming value is expressed in scientific notation.
    """
    assert_filter_passes(f.Int(), "2.6E4", 26000)


def test_int_fail_non_finite_value(assert_filter_errors):
    """
    The incoming value is a non-finite value.
    """
    assert_filter_errors(f.Int(), "NaN", [f.Decimal.CODE_NON_FINITE])
    assert_filter_errors(f.Int(), "+Inf", [f.Decimal.CODE_NON_FINITE])
    assert_filter_errors(f.Int(), "-Inf", [f.Decimal.CODE_NON_FINITE])
    # There are a few other possible non-finite values out there,
    # but you get the idea.


def test_int_pass_int(assert_filter_passes):
    """
    The incoming value is already an int object.
    """
    assert_filter_passes(f.Int(), 777)
