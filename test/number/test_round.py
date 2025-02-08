from decimal import Decimal as DecimalType, ROUND_CEILING

import pytest

import filters as f
from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Round().apply(None) is None


def test_pass_round_integer_to_nearest_integer_multiple() -> None:
    """
    Rounding an integer value to the nearest multiple of a specified integer.
    """
    # Note: always specify ``to_nearest`` as a string to avoid floating point issues.
    assert f.Round(to_nearest="5").apply("42") == DecimalType("40")


def test_pass_round_integer_to_nearest_float_multiple() -> None:
    """
    Rounding an integer value to the nearest multiple of a specified float.
    """
    # Note: always specify ``to_nearest`` as a string to avoid floating point issues.
    assert f.Round(to_nearest="5.5").apply("42") == DecimalType("44")


def test_pass_round_float_to_nearest_integer_multiple() -> None:
    """
    Rounding a float value to the nearest multiple of a specified integer.
    """
    # Note: always specify ``to_nearest`` as a string to avoid floating point issues.
    assert f.Round(to_nearest="1").apply("3.5") == DecimalType("4")


def test_pass_round_float_to_nearest_float_multiple() -> None:
    """
    Rounding a float value to the nearest multiple of a specified float.
    """
    # Just to be tricky, use a float value that would normally result in some nasty
    # floating point artefacts.
    # :see: http://stackoverflow.com/a/4340355
    # Incidentally, that's why you should always specify ``to_nearest`` as a string (:
    assert f.Round(to_nearest="0.05").apply("1.368161685161") == DecimalType("1.35")


def test_pass_floating_point_precision_oddness() -> None:
    """
    If the incoming value is a float, you may encounter strange issues due to floating
    point precision.

    For safety, always use string or ``Decimal`` values where practical.

    :see: http://stackoverflow.com/q/22599883
    """
    value = 2.775

    # You would expect 2.775 to be rounded up to 2.78, but instead....
    assert f.Round(to_nearest="0.01").apply(value) == DecimalType("2.77")


def test_pass_floating_point_precision_oddness_workaround() -> None:
    """
    To avoid floating point precision issues as demonstrated in the previous test,
    always pass in string or ``Decimal`` values.

    :see: http://stackoverflow.com/q/22599883
    """
    # Note that we pass in a string value instead of a float.
    value = "2.775"

    # This time the rounding works exactly as you'd expect.
    assert f.Round(to_nearest="0.01").apply(value) == DecimalType("2.78")


def test_pass_round_negative_value() -> None:
    """
    Rounding negative values is supported.

    If you only want to work with positive values, stick a :py:class:`filters.Min` in
    front.
    """
    assert f.Round(to_nearest="0.1").apply("-2.775") == DecimalType("-2.8")


def test_pass_modify_rounding_mode() -> None:
    """
    If desired, you can customise the way the filter applies rounding.

    See https://docs.python.org/3/library/decimal.html#rounding-modes for available
    rounding modes.
    """
    assert f.Round(rounding=ROUND_CEILING).apply("0.00000000001") == DecimalType("1")


def test_fail_wrong_type() -> None:
    """
    The incoming value is not numeric.
    """
    with pytest.raises(InvalidValue) as e:
        f.Round().apply("three point five")

    assert str(e.value) == "Numeric value expected."
    assert e.value.code == f.Decimal.CODE_INVALID
