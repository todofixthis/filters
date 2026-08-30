"""
Pins the chain-type inference the Phase 1 generic core provides (issue #34).

The concrete filters are not annotated yet, so these assertions run against
stand-ins defined here — one per category from
docs/adr/006-distinguish-filter-categories-by-marker-base-class.md — which
carry the same shapes ``Unicode``, ``NotEmpty``, ``Int`` and ``Optional``
take on once they are annotated. Every stand-in is a working filter at
runtime, because pytest collects this module like any other.

Nothing here asserts the parameter ``Type`` infers for an abstract argument:
mypy and pyright disagree on that (``Type[Any]`` versus the parameterised
ABC), so an assertion either way fails one of them.
"""

from copy import copy
from typing import Any, Optional, Union, assert_type

import pytest

import filters as f


class _StubTransform(f.BaseFilter[str]):
    """Stands in for a transforming filter, e.g. ``Unicode``."""

    def _apply(self, value: Any) -> str:
        return str(value)


class _StubTransformInt(f.BaseFilter[int]):
    """Stands in for a second, differently typed transforming filter."""

    def _apply(self, value: Any) -> int:
        return int(value)


class _StubPassThrough(f.PassThrough):
    """Stands in for a pass-through filter, e.g. ``NotEmpty``."""

    def _apply(self, value: Any) -> Any:
        return value


class _StubWidening(f.Widening[None]):
    """Stands in for a widening filter, i.e. ``Optional``."""

    def _apply(self, value: Any) -> Any:
        return value


class _StubUnparameterised(f.BaseFilter):
    """Stands in for a subclass written without a type argument."""

    def _apply(self, value: Any) -> Any:
        return value


def _make_stub_transform_int() -> _StubTransformInt:
    """Stands in for a filter supplied as a zero-argument callable."""
    return _StubTransformInt()


def test_chain_inference_pass_through_preserves_output_type() -> None:
    """A pass-through filter leaves the chain's output type alone."""
    assert_type(_StubTransform | _StubPassThrough, f.FilterChain[str])
    assert_type(_StubTransform() | _StubPassThrough(), f.FilterChain[str])


def test_chain_inference_survives_three_filters() -> None:
    """``FilterChain.__or__`` carries its own overloads.

    Without them every ``|`` after the first degrades the chain to
    ``FilterChain[Any]`` on both checkers.
    """
    assert_type(
        _StubTransform | _StubPassThrough | _StubTransformInt,
        f.FilterChain[int],
    )
    assert_type(
        _StubTransform | _StubPassThrough | _StubPassThrough,
        f.FilterChain[str],
    )


def test_chain_inference_none_leaves_the_chain_alone() -> None:
    """``None`` on the right of ``|`` is a no-op, as it is at runtime.

    Dropping this arm is a breaking change that #34 schedules for phase 5;
    until then ``resolve_filter`` no-ops on ``None`` and the type has to
    say so.
    """
    assert_type(_StubTransform | None, f.FilterChain[str])
    assert_type(_StubTransform() | None, f.FilterChain[str])
    assert_type((_StubTransform | _StubPassThrough) | None, f.FilterChain[str])

    # The runtime half of the same claim: nothing was appended.
    assert len((_StubTransform | None)._filters) == 1


def test_chain_inference_callable_reports_what_it_returns() -> None:
    """A zero-argument callable is resolved to the filter it returns, so
    the chain takes that filter's output type.
    """
    assert_type(_StubTransform | _make_stub_transform_int, f.FilterChain[int])
    assert_type(_StubTransform() | _make_stub_transform_int, f.FilterChain[int])
    assert_type(
        (_StubTransform | _StubPassThrough) | _make_stub_transform_int,
        f.FilterChain[int],
    )
    assert_type(_StubTransform | (lambda: _StubTransformInt()), f.FilterChain[int])


def test_chain_inference_rejects_a_non_filter_operand() -> None:
    """Negative case: widening the overloads to swallow anything is the
    failure mode this file exists to catch.

    Both suppressions are load-bearing — remove either and the checker it
    speaks for reports the mismatch, because a rejected operand leaves the
    expression ``Any`` (mypy) or ``Unknown`` (pyright) rather than
    ``FilterChain[str]``. Kept inside ``pytest.raises`` because this module
    is collected and run like any other, and ``resolve_filter`` raises on an
    operand it cannot resolve.
    """
    with pytest.raises(TypeError):
        assert_type(  # type: ignore[assert-type]
            _StubTransform() | 42,  # pyright: ignore[reportAssertTypeFailure]
            f.FilterChain[str],
        )


def test_chain_inference_widening_adds_to_output_type() -> None:
    """A widening filter unions its type with the chain's."""
    assert_type(_StubTransform | _StubWidening, f.FilterChain[Optional[str]])
    assert_type(_StubTransform | _StubWidening(), f.FilterChain[Optional[str]])


def test_chain_inference_reaches_apply() -> None:
    """``apply`` reports the chain's output type, plus the ``None`` every
    rejection path returns.
    """
    assert_type((_StubTransform | _StubPassThrough).apply("x"), Optional[str])


def test_chain_inference_unparameterised_subclass_defaults_to_any() -> None:
    """``default=Any`` keeps a subclass written without a type argument
    valid, at the cost of opting it out of inference.
    """
    assert_type(_StubUnparameterised().apply("x"), Optional[Any])
    assert_type(_StubUnparameterised | _StubPassThrough, f.FilterChain[Any])


def test_chain_inference_copy_preserves_the_subclass() -> None:
    """The ``TypeVar`` on ``__copy__`` carries the subclass through
    ``copy()``.
    """
    assert_type(copy(_StubTransform()), _StubTransform)
    assert_type(copy(_StubTransform | _StubPassThrough), f.FilterChain[str])


def test_chain_inference_filter_reports_its_argument_type() -> None:
    """``_filter`` is parameterised on the filter it is handed, not on the
    filter calling it.
    """
    assert_type(
        _StubTransform()._filter("42", _StubTransformInt),
        Optional[int],
    )


def test_chain_inference_type_binds_from_its_argument() -> None:
    """``Type``'s overloads bind the output type from ``allowed_types``."""
    assert_type(f.Type(str), f.Type[str])
    assert_type(f.Type((str, int)), f.Type[Union[str, int]])
    # Tuples stop at two; a longer one degrades rather than erroring.
    assert_type(f.Type((str, int, float)), f.Type[Any])
