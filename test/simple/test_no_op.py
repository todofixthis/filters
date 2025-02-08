import filters as f


def test_none() -> None:
    """
    Passing ``None`` to this filter is a no-op.
    """
    assert f.NoOp().apply(None) is None


def test_happy_path() -> None:
    """
    Does what it says on the tin.
    """
    value = "supercalafragalisticexpialadoshus"
    assert f.NoOp().apply(value) is value
