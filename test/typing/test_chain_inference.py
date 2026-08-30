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
