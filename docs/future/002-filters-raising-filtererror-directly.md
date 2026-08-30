# 002: Filters Raising `FilterError` Directly

Deferred, not rejected, during [#34][]'s review.

## Current pattern

A filter that rejects a value calls `self._invalid_value(...)` and returns
its result — `None` by default — leaving the caller to notice the rejection
by checking `self._has_errors` afterwards. `BaseFilter.apply()`'s docstring
records this as the reason its return type is `Optional[T_out]` rather than
`T_out`: every rejection path runs through `_invalid_value`, which returns a
replacement value instead of signalling failure through control flow.

## Proposed alternative

Filters would raise `filters.base.FilterError` directly instead of calling
`_invalid_value` and relying on the caller to check `_has_errors`.
`FilterError` already exists (a `ValueError` subclass) and `_invalid_value`
already special-cases it — this would make that path the default, not a
special case.

## Why it wasn't done here

Recorded in [#34][]'s review as future work: "#34 is pretty big as it is."
Changing the rejection mechanism itself is a larger, riskier change than
parameterising the existing one on its output type, and orthogonal to
generic typing.

## What it would unlock

With rejection routed through an exception, `apply()` and `_filter()` could
drop the `| None` from their return types entirely — `T_out` and
`T_filtered` in place of `Optional[T_out]` and `Optional[T_filtered]` — since
a filter that returns would always have succeeded. This is also what
[001: A Narrowing Filter Category][001] is waiting on.

[#34]: https://github.com/todofixthis/filters/issues/34
[001]: 001-a-narrowing-filter-category.md
