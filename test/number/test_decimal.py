from decimal import Decimal as DecimalType

import pytest

import filters as f
from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Decimal().apply(None) is None


def test_pass_valid_decimal() -> None:
    """
    The incoming value can be interpreted as a Decimal.
    """
    assert f.Decimal().apply("3.1415926") == DecimalType("3.1415926")


def test_pass_max_precision() -> None:
    """
    You can limit the max precision of the resulting Decimal object.

    Note that a too-precise value is not considered invalid; instead, it gets rounded to
    the expected precision.
    """
    assert f.Decimal(max_precision=3).apply("3.1415926") == DecimalType("3.142")


def test_max_precision_quantized() -> None:
    """
    ``max_precision`` can also be specified as a Decimal object.
    """
    actual = f.Decimal(max_precision=DecimalType("0.001")).apply("3.1415926")
    assert actual == DecimalType("3.142")


def test_pass_zero() -> None:
    """
    0 is also considered a valid Decimal value.
    """
    assert f.Decimal().apply("0") == DecimalType("0")


def test_pass_scientific_notation() -> None:
    """
    Scientific notation is considered valid, as in certain cases it may be the only way
    to represent super large or small values.
    """
    # Probably not as exciting as you were expecting, but that's because Python's
    # ``Decimal`` type is doing all the heavy lifting for us (:
    assert f.Decimal().apply("2.8E-12") == DecimalType("2.8E-12")


def test_pass_boolean() -> None:
    """
    Booleans are technically ints, so they can be converted to Decimal.

    If you explicitly want to reject boolean values, put a :py:class:`filters.Type` in
    front.
    """
    assert f.Decimal().apply(True) == DecimalType(True)


def test_fail_invalid_value() -> None:
    """
    The incoming value cannot be converted to a Decimal.
    """
    value = "ce n'est pas un décimal"

    with pytest.raises(InvalidValue) as e:
        f.Decimal().apply(value)

    assert str(e.value) == "Numeric value expected."
    assert e.value.code == f.Decimal.CODE_INVALID


@pytest.mark.parametrize("value", ("NaN", "+Inf", "-Inf"))
def test_fail_non_finite_value(value: str) -> None:
    """
    Non-finite values like 'NaN' and 'Inf' are considered invalid, even though they are
    technically parseable.
    """
    with pytest.raises(InvalidValue) as e:
        f.Decimal().apply(value)

    assert str(e.value) == "Finite value expected."
    assert e.value.code == f.Decimal.CODE_NON_FINITE


def test_pass_tuple() -> None:
    """
    You may pass a three-part tuple for more control over how the resulting Decimal
    object is created.

    From `Python docs`_:
    If value is a tuple, it should have three components, a sign (0 for positive or 1
    for negative), a tuple of digits, and an integer exponent. For example,
    ``Decimal((0, (1, 4, 1, 4), -3))`` returns ``Decimal('1.414')``.

    .. _`Python docs`: https://docs.python.org/3/library/decimal.html#decimal.Decimal
    """
    value = (0, (4, 2), -1)
    assert f.Decimal().apply(value) == DecimalType(value)


def test_fail_tuple_invalid() -> None:
    """
    If you're going to pass a tuple, it had better be valid (:
    """
    with pytest.raises(InvalidValue) as e:
        f.Decimal().apply(("1", "2", "3"))

    assert str(e.value) == "Numeric value expected."
    assert e.value.code == f.Decimal.CODE_INVALID


def test_fail_tuple_disallowed() -> None:
    """
    If desired, you can configure the filter to disallow tuple inputs.
    """
    with pytest.raises(InvalidValue) as e:
        f.Decimal(allow_tuples=False).apply((0, (4, 2), -1))

    assert (
        str(e.value) == "tuple is not valid (allowed types: str, int, float, Decimal)."
    )
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_fail_bytes() -> None:
    """
    For historical reasons, ``bytes`` input is not allowed.

    This was done in earlier versions of phx-filters so that the code would have the
    same behaviour in Python 2 and Python 3.
    """
    with pytest.raises(InvalidValue) as e:
        f.Decimal().apply(b"-12")

    assert (
        str(e.value)
        == "bytes is not valid (allowed types: str, int, float, Decimal, list, tuple)."
    )
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_fail_unsupported_type() -> None:
    """
    The incoming value has an unsupported type.
    """
    with pytest.raises(InvalidValue) as e:
        f.Decimal().apply({0, (4, 2), -1})

    assert (
        str(e.value)
        == "set is not valid (allowed types: str, int, float, Decimal, list, tuple)."
    )
    assert e.value.code == f.Type.CODE_WRONG_TYPE
