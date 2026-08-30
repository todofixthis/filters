---
status: Accepted
date: 2026-08-30
scope: [src/filters/]
summary: Parameterise BaseFilter on a single invariant output type variable, declared with typing_extensions.TypeVar(default=Any) rather than PEP 695 syntax or a second input parameter.
revisit-when: A filter needs to constrain its input type as well as its output; or PEP 695 syntax gains a way to declare variance rather than infer it; or requires-python reaches 3.13, making typing_extensions.TypeVar redundant.
---

# 005: Parameterise Filters on One Output Type

## Context

[#34][] asks that a type checker be able to infer what a filter chain
produces, so `f.Unicode | f.Strip` is something better than `Any`. Every
shape decision that follows — how many parameters, how they are declared,
what happens to a subclass that supplies none — is taken once here and paid
for by every filter in this package and by every downstream one — the
`phx-filters-django` and `phx-filters-iso` extras this package declares,
and any private subclass — because all of them subclass [`BaseFilter`][].

Two forces pull against each other. The parameter has to carry enough
information for `apply()` and a chain's result to be useful, and it has to
cost a subclass author nothing when they don't want it: `class
Country(BaseFilter)`, with no type argument, is the shape every filter here
is written in today, and it must keep type-checking after this lands.

The work is also phased: phase 1 makes the base generic, phase 2 annotates
the concrete filters, phase 6 ratchets both checkers to full strictness (see
[004: Type Checking in CI][]). Between phases 1 and 2 the tree is full of
unparameterised subclasses, which mypy's `disallow_any_generics` and
pyright's `reportMissingTypeArgument` — both on at full strictness — reject.
What is decided here therefore also decides whether those phases can land as
separate commits.

## Options

Options 2 and 3 both parameterise `BaseFilter`, so both carry the same
migration: every filter in this package gets a parameter in phase 2, and
`FilterChain`, `Type` and the `|` operator all become generic. That cost is
identical and does not rank them.

### Option 1: Do nothing

Leave `BaseFilter` unparameterised and let `apply()` keep returning an
implicit `Any`.

**Pros:** No migration, no new dependency, no strictness interaction, and
every downstream subclass keeps working untouched.
**Cons:** The issue stays open — `FilterRunner(...).cleaned_data` and
`apply()` remain `Any`, so consumers keep casting at every boundary, and a
chain that transforms `str` to `bytes` is indistinguishable from one that
doesn't.
**Risks:** `Any` propagates: a wrong type flowing out of a filter is
invisible at every call site downstream of it, which is the class of bug a
validation library is least able to afford.

### Option 2: One invariant output parameter, `TypeVar("T_out", default=Any)` (Accepted)

`class BaseFilter(Generic[T_out], metaclass=FilterMeta)`, with `T_out`
imported from `typing_extensions` so PEP 696's `default=` is available on
Python 3.12, and variance left invariant.

**Pros:** `class Country(BaseFilter)` keeps checking, because the default
supplies `Any` where no argument is given — verified against `mypy
--strict` and pyright in `strict` mode, the bar phase 6 ratchets to.
**Cons:** `typing_extensions` has to be a runtime dependency, not a
dev-only one, because the `TypeVar` call executes at import time.
**Risks:** `default=Any` is also what makes a *missing* parameter silent —
a phase 2 filter that nobody annotates degrades a chain to `Any` and
nothing reports it.

### Option 3: Two parameters, input and output

`class BaseFilter(Generic[T_in, T_out])`, so a filter can constrain what it
accepts as well as what it produces.

**Pros:** Expresses a filter that genuinely rejects a type — `f.MaxChars`
takes only `str` — and would let a chain be checked end to end rather than
only at its tail.
**Cons:** Nothing in this package produces a `T_in` other than `Any`.
Filters are written to accept whatever arrives and reject it through
`_invalid_value`, so `T_in` would be `Any` on almost every filter while
still having to be spelled out by every subclass author, downstream ones
included. It also doubles the surface of the `|` overloads, which already
appear five times over in three places.
**Risks:** A parameter that is `Any` almost everywhere trains readers to
write `Any` in the one place it would have mattered.

### Option 4: PEP 695 syntax (`class BaseFilter[T_out]`)

**Pros:** No `TypeVar` call, no `Generic` base, no import — and PEP 695 has
native `= Any` defaults, so no `typing_extensions` dependency.
**Cons:** PEP 695 infers variance from usage rather than letting it be
declared. Today `T_out` is output-only, so both checkers would infer
covariance; the narrowing category deferred in
[006: Distinguish Filter Categories by Marker Base Class][] would put it in
an input position and flip that inference, changing the variance of a
public generic class as a side effect of an unrelated change.
**Risks:** Variance that moves on its own is a breaking change for
consumers that nothing in this repository would flag.

## Decision

Option 2. Option 3's second parameter is charged to every subclass author
in this package and downstream, and buys a parameter that is `Any` wherever
it would have to be written. Option 4 is rejected on variance alone: this
is a public generic base subclassed outside this repository, and the one
property a public generic owes those subclasses is that its variance does
not change without someone deciding it should.

Invariant, and deliberately so. Covariance would be sound today — `T_out`
appears only in `apply`, `_apply` and `_apply_none` return positions, and
both checkers accept `covariant=True` on a spike of this hierarchy — but
loosening later is backwards-compatible where tightening is not, and the
narrowing category deferred out of #34 would take `T | None` to `T`,
putting `T_out` in an input position. Invariance costs only the rare
assignment of a `BaseFilter[str]` to a `BaseFilter[object]`, which
`BaseFilter[Any]` already serves.

## Consequences

- Phases 1 and 2 can land as separate commits at any strictness —
  `default=Any`'s second job, and why #34's phasing survives the phase 6
  ratchet rather than collapsing into one change.
- `typing_extensions` is imported at runtime by `base.py`. It is already a
  declared runtime dependency for exactly this reason.
- A downstream subclass written as `class Country(BaseFilter)` means
  `BaseFilter[Any]`, and so silently opts out of chain inference. That is
  the intended migration path, but it means the absence of a parameter is
  never an error — only a chain that infers `Any` reveals it, which is what
  the `test/typing/` harness exists to catch.
- Variance is a decision this ADR now owns. A later change that puts
  `T_out` in an input position needs no variance edit; one that wants
  `covariant=True` supersedes this ADR rather than editing the `TypeVar`.

[#34]: https://github.com/todofixthis/filters/issues/34
[004: Type Checking in CI]: 004-type-checking-in-ci.md
[006: Distinguish Filter Categories by Marker Base Class]: 006-distinguish-filter-categories-by-marker-base-class.md
[`BaseFilter`]: ../../src/filters/base.py
