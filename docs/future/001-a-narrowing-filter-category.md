# 001: A Narrowing Filter Category

Deferred, not rejected, during [#34][]'s review.

## What it would do

Add a sixth chain-effect category alongside the five that [ADR 006][]
defines: a narrowing marker taking `T | None` to `T`. `Required` and
`NotEmpty(allow_none=False)` are the two candidates — both already reject
`None` at runtime, so a static narrowing category would let a type checker
drop `None` from the chain's inferred type at the point either one appears,
rather than carrying `| None` through every filter downstream of it. This
has real value: `Required` heads nearly every schema entry in downstream
projects (e.g. `paddock`), so today's chains keep inferring `| None` long
after `Required` has already ruled it out.

## Why it wasn't done here

It depends on resolving how `apply()`/`_filter()` type their `None` handling
(see [002][]) — until that lands, a narrowing overload has nothing stable to
narrow *from*. [#34][]'s review flagged this explicitly as its own follow-up
rather than something to fold into an already-large change.

## Depends on

[002: Filters Raising `FilterError` Directly][002] — or whatever else settles
`apply()`/`_filter()`'s `T_out | None` return type.

[#34]: https://github.com/todofixthis/filters/issues/34
[ADR 006]: ../adr/006-distinguish-filter-categories-by-marker-base-class.md
[002]: 002-filters-raising-filtererror-directly.md
