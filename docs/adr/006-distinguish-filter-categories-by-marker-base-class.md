---
status: Accepted
date: 2026-08-30
scope: [src/filters/]
summary: Sort every filter into one of five chain-effect categories, two of which (pass-through and widening) are marker base classes in base.py that the overloads on `|` dispatch on.
revisit-when: A filter's effect on a chain's output type fits none of the five categories — most likely the deferred narrowing category, where `Required` and `NotEmpty(allow_none=False)` would take `T | None` to `T`.
---

# 006: Distinguish Filter Categories by Marker Base Class

## Context

[005: Parameterise Filters on One Output Type][] gives every filter an
output parameter, which settles what a *single* filter produces. It does
not settle what a *chain* produces, and chaining is what [#34][] is about.

The obvious rule — a chain's output is its last filter's output — is wrong
for a sizeable minority of this package. `f.Unicode | f.NotEmpty` produces `str`, but
`NotEmpty` has no output type of its own: it returns whatever it was given.
Ten filters behave that way (`NotEmpty`, `Required`, `Empty`, `Min`, `Max`,
`MinLength`, `MaxLength`, `Len`, `Length`, `NoOp`) — a quarter of the filters
this package exports — and a validation chain that checks nothing is unusual, so
getting them wrong collapses the common chain to `Any` and takes the issue's
headline case with it.

`Optional` is wrong under that rule in a second way: it produces its input
type *or* its default, so it widens rather than replaces.

Whatever distinguishes these has to be visible to a type checker at the
point `|` is resolved, and it has to be declared by the filter rather than
by each chain's author — `f.Unicode | f.NotEmpty` names no types at all.

## Options

Options 2, 3 and 4 all require phase 2 to visit every filter class in
`number.py`, `string.py`, `simple.py` and `complex.py` and say something
about it. That cost is common to all three and does not rank them.

### Option 1: Do nothing — a chain adopts its right operand's parameter

**Pros:** One overload instead of five, in each of the three places `|` is
defined. Nothing new in `base.py`, and no category to assign.
**Cons:** Every pass-through filter is `BaseFilter[Any]`, so `f.Unicode |
f.NotEmpty` infers `FilterChain[Any]` — as does anything ending in
`Required`. `f.Optional` reports its default's type and loses the input's.
**Risks:** The result is worse than no typing at all, because
`FilterChain[Any]` looks like a successful inference. The chains that
degrade are the most common ones, so the failure is widespread and quiet.

### Option 2: Marker base classes, dispatched by overloads on `|` (Accepted)

`base.py` gains `PassThrough` and `Widening[T_widened]`, both `BaseFilter`
subclasses that add no runtime behaviour, and each of the three places `|`
is defined carries a set of overloads that dispatches on them. A filter
joins a category by its base class.

**Pros:** The category is declared once, on the filter, and a chain infers
correctly without naming a type — including `f.Unicode | f.NotEmpty`
written entirely in bare classes. A downstream package gets the same
treatment by subclassing the marker.
**Cons:** Two new public names in `base.py` that exist only for the type
checker, and seven overloads repeated in three places — one for `None`, two
for `PassThrough` (class and instance), one for `Widening`, two generic
`BaseFilter[T]` arms covering the transforming, ctor-typed and untyped
categories, and one for the zero-argument-callable arm `FilterCompatible`
still carries — so twenty-one signatures whose bodies are all one
implementation. [009: Drop `None` as an Operand of the Chaining Operator][]
has since removed the `None` arm, leaving six and eighteen.
**Risks:** A filter filed in the wrong category produces a confidently
wrong chain type. `MaxBytes` is the live example: it reads as a length
check but `_apply` encodes, and returns `bytes` on every path that isn't an
error, so filing it pass-through would type `f.Unicode | f.MaxBytes(10)` as
`str` for a chain returning `bytes`.

### Option 3: A class attribute naming the effect

Give each filter something like `chain_effect: Literal["pass", "widen",
"transform"]` and have `|` read it.

**Pros:** No new base classes, no marker in the MRO, and the category is
introspectable at runtime — which the base-class form is not.
**Cons:** Overload resolution matches on a parameter's *type*, not on the
value of an attribute the parameter happens to carry, so neither checker
can dispatch on this. It would have to be paired with an overload set that
discriminates some other way, at which point the attribute is documentation
rather than mechanism.
**Risks:** It reads as though it works, and produces no error when it
doesn't — the attribute is simply never consulted.

### Option 4: Each filter declares its own `__or__` overloads

**Pros:** Fully general — a filter can describe any relationship between
its input and output types, including ones no fixed set of categories
anticipates.
**Cons:** The same overload block copied into every pass-through filter,
and again into every downstream one. `phx-filters-django` and
`phx-filters-iso` would each have to write it to keep chaining, turning a
transparent upgrade into a coordinated one.
**Risks:** Two filters in the same category drifting apart, with nothing
to compare them against.

## Decision

Option 2. Option 3 cannot dispatch, which leaves Option 4 as the only real
rival, and its generality is not worth what it costs: the categories below
cover every filter this package exports, and Option 4 charges every
downstream author for a flexibility none of them has asked for. A marker
base class is also the one signal that survives being written as a bare
class — `f.Unicode | f.NotEmpty` passes the *class* `NotEmpty`, not an
instance, and `type[PassThrough]` is still matchable where a per-instance
attribute is not.

Five categories, only two of which need a marker:

| Category | Base | Effect on the chain |
|---|---|---|
| Transforming | `BaseFilter[T]` | Output becomes `T` |
| Pass-through | `PassThrough` | Output unchanged |
| Widening | `Widening[T_widened]` | Output becomes `T \| T_widened` |
| Ctor-typed | `BaseFilter[T]`, `T` bound in `__init__` | Output becomes `T` |
| Untyped | `BaseFilter[Any]` | Output becomes `Any` |

Transforming, ctor-typed and untyped are all `BaseFilter[T]` — they differ
in where `T` comes from, not in how `|` treats them, so they need no marker
and no overload of their own. Only pass-through and widening change what
`|` does, and so only those two become classes.

Nothing does an `isinstance` check against either marker, and nothing
should: their whole job is to be visible in an overload signature.

`Widening[T_widened]` widens to `T_out | T_widened` and stops there, even
though `Optional` — its only member — exists to remove `None` and
`apply()` returns `T_out | None` regardless. Resolving that means giving
`Optional` a narrowing override, which #34 defers.

## Consequences

- `PassThrough` and `Widening` are public API in `base.py` and in
  `__all__`. Downstream packages join a category the same way this one
  does, by subclassing.
- The overloads are duplicated across `FilterMeta.__or__`,
  `BaseFilter.__or__` and `FilterChain.__or__`. `FilterChain` cannot simply
  inherit them: it overrides `__or__` for a runtime reason — chaining onto
  a chain copies rather than mutating — and every `|` after the first
  dispatches to that override. Measured on a spike, an override written
  without its own overloads degrades a three-filter chain to
  `FilterChain[Any]` on both checkers, while deleting the override
  altogether infers correctly; keeping the runtime behaviour is what
  obliges the third copy.
- Every set has to cover the whole of `FilterCompatible`, not just the
  categories. `None` and a zero-argument callable are both accepted by
  `resolve_filter`, so each set carries an arm for them; omitting either
  makes `f.Unicode | None` a type error, which is a break #34 schedules for
  phase 5 rather than one this ADR takes. 009 took that break: the `None`
  arm is gone from all three sets, and `base.py` records its absence where
  the arm used to sit.
- Overload order is load-bearing, in both directions. `PassThrough` and
  `Widening` are `BaseFilter` subclasses, so the general `BaseFilter[T]`
  overloads match them too and the marker overloads must come first or the
  markers never fire. The callable arm is the mirror image: a filter
  *class* is itself a zero-argument callable returning a filter, so it must
  come last or it swallows every `type[...]` arm above it. Measured —
  putting the callable arm first degrades `f.Unicode | f.NotEmpty` to
  `FilterChain[Any]` on both checkers.
- Assigning a category is a hierarchy change, not an annotation. A marker
  is a real base class, so rebasing `NotEmpty` onto `PassThrough` in phase
  2 adds an MRO entry and flips `issubclass(f.NotEmpty, f.PassThrough)`
  from `False` to `True`. #34 treats that class of change as breaking for
  the `ByteString`/`Unicode` split; this one runs the other way — it only
  adds a base nothing downstream can have been testing for, the marker not
  having existed — so it is additive, and `issubclass`-visible all the
  same.
- A filter is pass-through **or** typed, never both. `PassThrough` is
  `BaseFilter[Any]`, and the marker overloads run first, so a filter that
  lists both — `class Foo(PassThrough, BaseFilter[str])` — has its `str`
  silently ignored: both checkers accept the class and then chain it as a
  pass-through. Phase 2 has to pick one per filter.
- Phase 2 assigns every filter a category, and a wrong assignment is not
  something either checker can catch — the filter's `_apply` is the only
  evidence. `MaxBytes` is the one already known to read against its
  category.
- The marker overloads fire wherever mypy evaluates `|` as an expression,
  which is not everywhere. Against an assignment target mypy reads `X | Y`
  between two *classes* as an implicit [PEP 604][] type alias and never
  consults `__or__`, so `chain = f.Unicode | f.NotEmpty` binds
  `types.UnionType` and anything drawn from it degrades to `Any`, with no
  error raised. At runtime the expression is a real `FilterChain` —
  `FilterMeta.__or__` runs regardless — so this is mypy asserting a type the
  object does not have, not merely losing one. Annotating the target, or
  instantiating any one of the operands, restores it; pyright is unaffected.
  This is a rule about assignment statements rather than about overloads, so
  Option 4 measures identically and no category scheme avoids it.
- The `test/typing/` harness is where a category assignment is pinned:
  `assert_type` on a chain is the only thing that fails when a filter is
  refiled or a marker stops matching. It cannot catch the assignment case
  above, `assert_type` taking the chain as an argument — the one position
  that works.

[#34]: https://github.com/todofixthis/filters/issues/34
[005: Parameterise Filters on One Output Type]: 005-parameterise-filters-on-one-output-type.md
[009: Drop `None` as an Operand of the Chaining Operator]: 009-drop-none-as-an-operand-of-the-chaining-operator.md
[PEP 604]: https://peps.python.org/pep-0604/
