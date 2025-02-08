import pytest

import filters as f
from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Int().apply(None) is None


def test_pass_valid_int() -> None:
    """
    The incoming value is already an int.
    """
    assert f.Int().apply(42) == 42


def test_pass_valid_compatible_type() -> None:
    """
    The incoming value can be cast as an int.
    """
    assert f.Int().apply("42") == 42


def test_pass_zero() -> None:
    """
    The filter accepts 0 as a valid int.
    """
    assert f.Int().apply("0") == 0


def test_pass_negative() -> None:
    """
    The filter accepts negative values.

    If you only want to accept positive values, chain the filter with
    :py:class:`filters.Min`.
    """
    assert f.Int().apply("-314") == -314


def test_pass_boolean() -> None:
    """
    Booleans are technically ints.

    If you explicitly want to reject boolean values, put a :py:class:`filters.Type` in
    front.
    """
    assert f.Int().apply(True) == 1


def test_fail_bytes() -> None:
    """
    For historical reasons, ``bytes`` input is not allowed.

    This was done in earlier versions of phx-filters so that the code would have the
    same behaviour in Python 2 and Python 3.
    """
    with pytest.raises(InvalidValue) as e:
        f.Int().apply(b"42.01")

    assert (
        str(e.value)
        == "bytes is not valid (allowed types: str, int, float, Decimal, list, tuple)."
    )
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_fail_float_non_empty_fpart() -> None:
    """
    The incoming value contains significant digits after the decimal point.

    If you want to accept float values with non-empty fparts, pass the value through
    :py:class:`filters.Round` first.
    """
    with pytest.raises(InvalidValue) as e:
        f.Int().apply("42.01")

    assert str(e.value) == "Integer value expected."
    assert e.value.code == f.Int.CODE_DECIMAL


def test_pass_float_empty_fpart() -> None:
    """
    The incoming value does not contain any significant digits after the decimal point.
    """
    assert f.Int().apply("42.0000000000000") == 42


def test_pass_scientific_notation() -> None:
    """
    Scientific notation is considered valid, as in certain cases it may be the only way
    to represent super large or small values.
    """
    assert f.Int().apply("2.6E4") == 26_000


@pytest.mark.parametrize("value", ("NaN", "+Inf", "-Inf"))
def test_fail_non_finite_value(value: str) -> None:
    """
    Non-finite values like 'NaN' and 'Inf' are considered invalid, even though they are
    technically parseable.
    """
    with pytest.raises(InvalidValue) as e:
        f.Int().apply(value)

    assert str(e.value) == "Finite value expected."
    assert e.value.code == f.Decimal.CODE_NON_FINITE


def test_fail_invalid_value() -> None:
    """
    The incoming value cannot be interpreted as a number, let alone an integer.
    """
    with pytest.raises(InvalidValue) as e:
        f.Int().apply("ce n'est pas un int")

    assert str(e.value) == "Numeric value expected."
    assert e.value.code == f.Decimal.CODE_INVALID
