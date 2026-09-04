"""
Pins the type-checker inference for ``filter_macro``-produced types.

``filter_macro`` erases the wrapped function's real signature down to
``type[FilterMacroType]``, so a checker has no way to know which keyword
arguments a given macro accepts. ``FilterMacroType.__init__`` is typed
permissively (``*args: Any, **kwargs: Any``) specifically to keep macro
construction call-arg-checkable-but-permissive rather than rejecting every
keyword argument outright -- found via a downstream project (paddock) whose
stricter mypy config (``check_untyped_defs = true``) flagged constructor
calls like ``Volume(home_dir=...)`` that phx-filters' own default config
does not check.
"""

from typing import assert_type

import filters as f
from filters.macros import FilterMacroType, filter_macro


def test_macro_decorator_accepts_wrapped_functions_keyword_argument() -> None:
    """A macro built with ``@filter_macro`` must still accept, at the type
    level, whatever keyword arguments its wrapped function declares.
    """

    @filter_macro
    def WithMinLength(min_length: int = 12):
        return f.Unicode | f.MinLength(min_length)

    assert_type(WithMinLength(min_length=6), FilterMacroType)


def test_macro_partial_accepts_override_keyword_argument() -> None:
    """A macro built by presetting kwargs via ``filter_macro(...)`` directly
    must still accept an overriding keyword argument at call time.
    """
    Minor = filter_macro(f.Max, max_value=18, exclusive=False)

    assert_type(Minor(exclusive=True), FilterMacroType)
