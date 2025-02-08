import pytest

import filters as f
from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Min(42).apply(None) is None


def test_pass_greater_value() -> None:
    """
    The incoming value is larger than the min value.
    """
    assert f.Min(42).apply(43) == 43


def test_pass_equal_value() -> None:
    """
    By default, the filter also accepts an incoming value equal to the min value.
    """
    assert f.Min(42).apply(42) == 42


def test_fail_equal_value_disallowed() -> None:
    """
    The incoming value is equal to the min value, but the Filter is configured to use an
    exclusive comparison.

    This is useful for infinite-precision floats and other cases where it is impossible
    to specify the min value exactly.
    """
    with pytest.raises(InvalidValue) as e:
        f.Min(42, exclusive=True).apply(42)

    assert str(e.value) == "Value is too small (must be > 42)."
    assert e.value.code == f.Min.CODE_TOO_SMALL


def test_fail_lesser_value() -> None:
    """
    The incoming value is smaller than the min value.
    """
    with pytest.raises(InvalidValue) as e:
        f.Min(42).apply(41)

    assert str(e.value) == "Value is too small (must be >= 42)."
    assert e.value.code == f.Min.CODE_TOO_SMALL


def test_fail_string_comparison_oddness() -> None:
    """
    If the filter is being used on strings, the comparison may produce unexpected
    results (technically, it compares code point values).
    """
    with pytest.raises(InvalidValue) as e:
        # ord('f') => 102
        # ord('F') => 70
        f.Min("foo").apply("Foo")

    assert str(e.value) == "Value is too small (must be >= foo)."
    assert e.value.code == f.Min.CODE_TOO_SMALL
