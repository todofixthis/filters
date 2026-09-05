---
status: Accepted
date: 2026-08-30
scope: [docs/simple_filters.rst, src/filters/base.py, test/test_filter_chain.py, test/typing/test_chain_inference.py]
summary: Make `some_filter | None` raise `TypeError` and drop the `None` arm from all three `__or__` overload sets, while leaving `FilterCompatible`, `resolve_filter` and `FilterChain._add` accepting `None` as before.
revisit-when: Requiring `NoOp` proves onerous in practice — a caller assembling a chain from parts that may legitimately be absent, where threading `NoOp` through each one obscures the code more than the silent no-op did.
---

# 009: Drop `None` as an Operand of the Chaining Operator

## Context

`some_filter | None` is a silent no-op today. `BaseFilter.__or__` and
[`FilterChain.__or__`][] both call `resolve_filter`, treat its `None` result
as "nothing to add", and hand back the left operand unchanged.
`FilterMeta.__or__` inherits the behaviour by delegating to
`FilterChain(cls) | next_filter`.

The result is an operator that accepts an operand it cannot do anything with.
`f.Unicode | None | f.NotEmpty` and `f.Unicode | f.NotEmpty` are the same
chain, so a `None` that arrived by accident — an unset variable, a lookup that
missed — builds a shorter chain than the author meant and reports no error.
[#34][] parameterises `|` on its operand's output type, which makes the arm
worth pricing rather than inheriting: [ADR 006][] had to carry a `None`
overload in each of the three sets purely to keep the existing behaviour
type-checking, and recorded that dropping it "is a break #34 schedules for
phase 5 rather than one this ADR takes".

`None` is load-bearing elsewhere in the same union. A `None` entry in
`FilterMapper`'s `filter_map` declares a key without filtering its value, and
`FilterSwitch` reads `default=None` as "no default"; both reach
`resolve_filter` through `_filter` or `FilterChain._add`, not through `|`.

## Options

### Option 1: Do nothing — keep `filter | None` as a no-op

**Pros:** No breaking change, and every arm of `FilterCompatible` is accepted
wherever the alias appears.
**Cons:** Keeps an operand that cannot fail, so a mistake the overloads could
catch for free goes on being absorbed silently. Each of the three overload
sets carries an arm whose only job is to describe a no-op.
**Risks:** Every release it stands, more callers and more documentation come
to rely on it, widening the eventual break.

### Option 2: Raise on a `None` operand, and drop the overload arm (Accepted)

Replace each `__or__`'s no-op branch with a `TypeError`, and remove the `None`
arm from `FilterMeta.__or__`, `BaseFilter.__or__` and `FilterChain.__or__`.
`FilterCompatible`, `resolve_filter` and `_add` are untouched.

**Pros:** Every form raises at runtime, getting the same rejection
`resolve_filter` already gives any operand it cannot use, where the no-op
absorbed the mistake silently. Statically the benefit waits on Phase 6 — see
Consequences.
**Cons:** Breaking, for callers relying on the no-op.
**Risks:** None distinct from the Cons.

### Option 3: Remove `None` from `FilterCompatible` as well

Take the arm out of the alias, so nothing in the library advertises a `None`
filter.

**Pros:** One definition to read instead of an alias with a caveat.
**Cons:** Breaks `FilterMapper`'s unfiltered-key entry and `FilterSwitch`'s
`default=None`, neither of which has a replacement short of substituting
`NoOp` and changing what those classes mean.
**Risks:** Conflates two questions — what a filter-shaped argument may be, and
what `|` may be given — that happen to share an alias.

## Decision

Option 2. The change is narrower than it looks: `|` is the only place a `None`
operand has nothing to do, being the only place that exists to extend a chain.
Everywhere else `None` carries meaning the caller chose, which is why Option 3
is a different decision wearing the same word.

Option 1's cost is not the code it keeps but the documentation it has already
produced. `docs/simple_filters.rst` carries a `.. tip::` under `NoOp` built on
the claim that `None` can safely be substituted for `filters.NoOp`, with a
worked, runnable example — `f.FilterRunner(f.Unicode | None | f.NotEmpty,
...)`. [The plan][] scopes this change to "one no-op operator" reaching none of
the downstream repositories — true of `src/` and of those repositories, and
silent about `docs/`. Sweeping the paths it leaves out, `rg '\| None\b'` over
`docs/` and over `test/`, turned up that tip plus a second typing test,
`test/typing/test_chain_inference.py`, alongside the
`test/test_filter_chain.py` case.

## Consequences

- `some_filter | None` raises `TypeError` where it previously returned the
  left operand wrapped in a `FilterChain`. Callers substitute `f.NoOp`, which
  is what the operand meant.
- `FilterCompatible` keeps its `None` arm, so it now describes a value
  accepted by every consumer except `|`. `resolve_filter`, `_filter` and
  `FilterChain._add` — including the `FilterChain(None)` its own initialiser
  performs — are unchanged.
- Statically, nothing changes until Phase 6. [ADR 004][]'s baseline disables
  mypy's `operator` code and pyright's `reportOperatorIssue`, so on this tree
  `f.Unicode() | None` draws no diagnostic from either checker and resolves to
  `Any` (mypy) or `Unknown` (pyright); measured with a `reveal_type` probe.
  With both codes forced on, each checker rejects all three forms. mypy
  reaches the class form only because
  `FilterMeta` defines `__or__`: for a class whose metaclass does not,
  `X | None` is a PEP 604 union expression with nothing to reject, measured
  both ways.
- The `.. tip::` block in `docs/simple_filters.rst` goes; the paragraph it
  contained about a filter macro needing `NoOp` stays, since a macro body
  still cannot usefully write `None | f.Decimal`. That expression does not
  raise: `None` has no applicable `__or__`, so Python falls back to the right
  operand's `__ror__`, which `FilterMeta` inherits from `type`, and the result
  is quietly the union `None | Decimal` rather than a chain, which goes on
  absorbing `|` operands as a union. The failure surfaces one step later,
  where the macro is chained: `resolve_filter` reports `Union None |
  filters.number.Decimal is not compatible with FilterChain` — less legible
  than the instance form, `None | f.Decimal()`, which raises `TypeError` on
  the spot.
- Two tests change: `test_filter_chain_implicit_chain_null` becomes
  `test_filter_chain_rejects_none` and asserts the raise, and
  `test_chain_inference_none_leaves_the_chain_alone` in `test/typing/` becomes
  a negative case, guarded per that module's own rule with a
  `# type: ignore[assert-type]` and its `# pyright: ignore` twin on each
  pinned form. Each suppression polices one checker only —
  ADR 004's `warn_unused_ignores` the mypy comment,
  `reportUnnecessaryTypeIgnoreComment` the pyright one — and neither
  cross-checks the other. Both are load-bearing because a rejected operand
  leaves the expression `Any`/`Unknown`, so each pinned `assert_type` fails.
  That is the guard: re-adding a `None` arm returning `FilterChain[T_out]`
  would make the assertion pass again, and each checker would then report its
  own suppression as unused and fail the build.
- The class form's `TypeError` now names the operand's own class rather than
  the `FilterChain` wrapper `FilterMeta.__or__` builds internally: `f.Int |
  None` says `None is not compatible with Int in a filter chain`, matching
  the instance and chain forms. Fixed by checking `cls.__name__` directly in
  `FilterMeta.__or__`, ahead of its existing delegation to `FilterChain(cls)
  | next_filter`. That guard doesn't replace `FilterChain.__or__`'s own
  check, only runs ahead of it, so the class form now costs the third
  `resolve_filter` call on the same operand this bullet originally declined
  to pay for a better noun.
- The same message also reaches a reader `FilterMeta.__or__` was never
  written for: a PEP 604 annotation like `def g(x: f.Unicode | None)` hits
  the same operator. `develop` didn't raise there either — it silently built
  a `FilterChain` where a type belonged — so v4.0.0 turning that into a loud
  error is this ADR's own rationale reaching a case it didn't enumerate, not
  a regression. "use NoOp instead" only serves the chain reader, so the
  message now names both remedies — `NoOp` for a chain, `Optional[...]` for
  an annotation — since quoting the annotation doesn't dodge the error: on
  3.12 `from __future__ import annotations` and on 3.14 PEP 649 both only
  defer the identical `TypeError` to `get_type_hints`.

[#34]: https://github.com/todofixthis/filters/issues/34
[ADR 004]: 004-type-checking-in-ci.md
[ADR 006]: 006-distinguish-filter-categories-by-marker-base-class.md
[`FilterChain.__or__`]: ../../src/filters/base.py
[the plan]: https://github.com/todofixthis/filters/pull/116
