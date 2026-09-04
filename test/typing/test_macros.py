"""
Pins the type-checker inference for ``filter_macro``-produced types.

``filter_macro`` erases the wrapped function's real signature down to
``type[FilterMacroType[T_out]]``, so a checker has no way to know which
keyword arguments a given macro accepts. ``FilterMacroType.__init__`` is
typed permissively (``*args: Any, **kwargs: Any``) specifically to keep
macro construction call-arg-checkable-but-permissive rather than rejecting
every keyword argument outright -- found via a downstream project (paddock)
whose stricter mypy config (``check_untyped_defs = true``) flagged
constructor calls like ``Volume(home_dir=...)`` that phx-filters' own
default config does not check.

``T_out`` itself defaults to ``Any``, so an unannotated macro function stays
usable without a checker narrowing its output -- mypy only reads an explicit
return annotation on the wrapped function; pyright also infers unannotated
bodies, so it narrows some macros mypy still sees as ``Any``. Where the two
disagree, the assertion below pins pyright's (stronger, correct) inference
and carries a ``# type: ignore[assert-type]`` for mypy's weaker one, per the
rule in ``test_smoke``.
"""

from typing import Any, assert_type

import filters as f
from filters.macros import FilterMacroType, filter_macro


def test_macro_decorator_accepts_wrapped_functions_keyword_argument() -> None:
    """A macro built with ``@filter_macro`` must still accept, at the type
    level, whatever keyword arguments its wrapped function declares.

    ``WithMinLength`` has no return annotation, so mypy infers ``Any`` for
    its output type; pyright infers the real ``str`` from the body.
    """

    @filter_macro
    def WithMinLength(min_length: int = 12):
        return f.Unicode | f.MinLength(min_length)

    assert_type(WithMinLength(min_length=6), FilterMacroType[str])  # type: ignore[assert-type]


def test_macro_decorator_with_return_annotation_narrows_output_type() -> None:
    """Giving the wrapped function an explicit return annotation lets both
    checkers narrow the macro's output type -- the escape hatch for a macro
    author who wants more than ``Any``.
    """

    @filter_macro
    def AnnotatedString() -> f.BaseFilter[str]:
        return f.Unicode() | f.Strip() | f.NotEmpty()

    assert_type(AnnotatedString(), FilterMacroType[str])


def test_macro_partial_accepts_override_keyword_argument() -> None:
    """A macro built by presetting kwargs via ``filter_macro(...)`` directly
    must still accept an overriding keyword argument at call time.

    ``Max`` is a ``PassThrough`` filter (see ``docs/adr/006``), so its own
    output type is ``Any`` on both checkers -- no divergence here.
    """
    Minor = filter_macro(f.Max, max_value=18, exclusive=False)

    assert_type(Minor(exclusive=True), FilterMacroType[Any])
