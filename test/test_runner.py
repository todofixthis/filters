import typing

import filters as f
from filters.base import BaseFilter, T
from filters.runner import FilterRunner


def test_happy_path_filter_passes() -> None:
    """
    Using a filter runner to check a valid value.
    """
    value = "Hello, world!"

    runner = FilterRunner(f.NoOp())
    runner.apply(value)

    assert runner.is_valid() is True
    assert runner.cleaned_data is value
    assert runner.errors == {}

def test_happy_path_filter_fails() -> None:
    """
    Using a filter runner to check an invalid value.
    """
    runner = FilterRunner(f.Type(str))
    runner.apply(42)

    assert runner.is_valid() is False
    assert runner.cleaned_data is None
    assert runner.errors == {'': [{
        "code": f.Type.CODE_WRONG_TYPE,
        "message": "int is not valid (allowed types: str).",
    }]}

def test_filter_asplodes() -> None:
    """
    The filter raises an unexpected exception.
    """
    class Asplode(BaseFilter[None]):
        """
        We do so love our references.
        """
        def _apply(self, value: typing.Any) -> T:
            raise RuntimeError("Well, my head asplode.")

    runner = FilterRunner(Asplode())
    runner.apply(42)

    assert runner.is_valid() is False
    assert runner.cleaned_data is None
    assert runner.errors == {'': [{
        "code": BaseFilter.CODE_EXCEPTION,
        "message": "An error occurred while processing this value.",
    }]}

