import pytest

import filters as f
from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Max(42).apply(None) is None


def test_pass_lesser_value() -> None:
    """
    The incoming value is smaller than the max value.
    """
    assert f.Max(42).apply(41) == 41


def test_pass_equal_value() -> None:
    """
    By default, the filter also accepts an incoming value equal to the max value.
    """
    assert f.Max(42).apply(42) == 42


def test_fail_equal_value_disallowed() -> None:
    """
    The incoming value is equal to the max value, but the Filter is configured to use an
    exclusive comparison.

    This is useful for infinite-precision floats and other cases where it is impossible
    to specify the max value exactly.
    """
    with pytest.raises(InvalidValue) as e:
        f.Max(42, exclusive=True).apply(42)

    assert str(e.value) == "Value is too large (must be < 42)."
    assert e.value.code == f.Max.CODE_TOO_BIG


def test_fail_greater_value() -> None:
    """
    The incoming value is greater than the max value.
    """
    with pytest.raises(InvalidValue) as e:
        f.Max(42).apply(43)

    assert str(e.value) == "Value is too large (must be <= 42)."
    assert e.value.code == f.Max.CODE_TOO_BIG


def test_fail_string_comparison_oddness() -> None:
    """
    If the filter is being used on strings, the comparison may produce unexpected
    results (technically, it compares code point values).
    """
    with pytest.raises(InvalidValue) as e:
        # ord('F') => 70
        # ord('f') => 102
        f.Max("Foo").apply("foo")

    assert str(e.value) == "Value is too large (must be <= Foo)."
    assert e.value.code == f.Max.CODE_TOO_BIG
