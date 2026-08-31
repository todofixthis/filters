"""
Tests for the FilterCompatible type alias.
"""

from typing import get_type_hints

import filters as f


def test_filter_compatible_is_subscriptable():
    """
    ``FilterCompatible`` is genuinely generic at runtime, not just for a
    type checker.

    A plain ``Optional[Union["BaseFilter[T_out]", ...]]`` built from
    string forward references carries no ``__parameters__`` of its own,
    since a ``ForwardRef`` is opaque until evaluated — so subscripting it
    used to raise ``TypeError: ... is not a generic class``.
    """
    assert repr(f.FilterCompatible[int]) == "FilterCompatible[int]"


def test_filter_compatible_resolves_under_get_type_hints():
    """
    Signatures naming ``FilterCompatible`` survive runtime introspection.

    Anything that resolves annotations at runtime — pydantic, FastAPI,
    ``inspect.signature(eval_str=True)`` — calls ``get_type_hints()``,
    which used to raise ``TypeError: ... is not a generic class`` on
    every one of these for the same reason as above.
    """
    hints = get_type_hints(f.BaseFilter.resolve_filter)
    assert hints["the_filter"].__origin__ is f.FilterCompatible
