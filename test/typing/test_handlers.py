"""
Pins the ``FilterRunner`` inference that closes issue #34.

Issue #34's own text: "Annotate each filter class with a generic type hint,
so that clever IDEs can infer the return type from
``FilterRunner(...).apply()``". ``apply()`` itself returns ``None`` -- see
``handlers.py``'s docstring on it -- so the inference target the issue was
actually after is ``FilterRunner.cleaned_data``, read after the ``apply()``
call that ``full_clean()`` makes internally.
"""

from typing import assert_type

import filters as f


def test_handlers_filter_runner_infers_from_a_single_filter() -> None:
    """A bare filter solves ``FilterRunner``'s type parameter directly."""
    assert_type(f.FilterRunner(f.Int()), f.FilterRunner[int])
    assert_type(f.FilterRunner(f.Int()).cleaned_data, int)


def test_handlers_filter_runner_infers_from_a_chain() -> None:
    """A chain resolves to ``FilterChain[T]`` first (Phase 1/2), and that
    ``T`` is what ``FilterRunner`` then infers.
    """
    assert_type(f.FilterRunner(f.Int() | f.Max(10)), f.FilterRunner[int])
    assert_type(f.FilterRunner(f.Int() | f.Max(10)).cleaned_data, int)


def test_handlers_filter_runner_cleaned_data_matches_the_issue() -> None:
    """The issue's own motivating case: reading a value out of
    ``FilterRunner`` without an explicit cast or ``Any`` in sight.
    """
    runner = f.FilterRunner(f.Int())
    runner.apply("42")

    if runner.is_valid():
        assert_type(runner.cleaned_data, int)
