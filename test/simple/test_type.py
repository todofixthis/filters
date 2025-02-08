import pytest

import filters as f

from filters.base import InvalidValue


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.Type(str).apply(None) is None


def test_pass_single_type() -> None:
    """
    The incoming value has the required type.
    """
    value = "Hello, world!"

    assert f.Type(str).apply(value) is value


def test_fail_single_type() -> None:
    """
    The incoming value does not have the required type.
    """
    value = b"Not a string, sorry."

    with pytest.raises(InvalidValue) as e:
        f.Type(str).apply(value)

    assert str(e.value) == "bytes is not valid (allowed types: str)."
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_pass_multiple_types() -> None:
    """
    The incoming value has one of the required types.
    """
    assert f.Type((str, int)).apply(42) == 42


def test_fail_multiple_types() -> None:
    """
    The incoming value doesn't match any of the required types.
    """
    with pytest.raises(InvalidValue) as e:
        f.Type((str, int)).apply(b"Still not a string, sorry")

    assert str(e.value) == "bytes is not valid (allowed types: str, int)."
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_pass_subclass() -> None:
    """
    The incoming value is a subclass of the required type.
    """
    # bool is a subclass of int
    assert f.Type(int).apply(True) is True


def test_fail_subclass_not_allowed() -> None:
    """
    The filter is configured explicitly to forbid subclasses.
    """
    with pytest.raises(InvalidValue) as e:
        f.Type(int, allow_subclass=False).apply(True)

    assert str(e.value) == "bool is not valid (allowed types: int)."
    assert e.value.code == f.Type.CODE_WRONG_TYPE


def test_fail_types_are_not_instances() -> None:
    """
    The incoming value must be an **instance** of the specified type(s).
    """
    with pytest.raises(InvalidValue) as e:
        f.Type(str).apply(str)

    assert str(e.value) == "type is not valid (allowed types: str)."
    assert e.value.code == f.Type.CODE_WRONG_TYPE
