---
status: Accepted
date: 2026-08-30
scope: [src/filters/simple.py, src/filters/string.py]
summary: Rebase `ByteString` and `Date` as siblings of `Unicode` and `Datetime` under a private generic base that holds the shared logic under a name of its own, rather than under `_apply`, and do not register the split pairs back together as virtual subclasses.
revisit-when: A consumer turns up that depends on `issubclass(f.ByteString, f.Unicode)` or `issubclass(f.Date, f.Datetime)`; or a filter outside either pair needs the shared decode or parse logic, which would put the private base on the public surface.
---

# 008: Split `ByteString` and `Date` into Siblings of `Unicode` and `Datetime`

## Context

[`ByteString`][] extends [`Unicode`][] and returns `bytes` where its parent
returns `str`; [`Date`][] extends [`Datetime`][] and returns `date` where its
parent returns `datetime`. Neither is an "is-a" relationship. Each subclass
inherits its parent's initialiser and one method's worth of decoding or
parsing, then contradicts everything else about it — a convenience predating
[#34][] that nothing in the library depends on.

Phase 2 of #34 made the contradiction a type error by parameterising every
filter on its output type: `ByteString` inherits `BaseFilter[str]` through
`Unicode`, so `apply` reports `str` for a filter that returns `bytes`.
[ADR 007][] patched that with an interim `apply`/`_apply` override on each
subclass, a `# type: ignore[override]` on each, and a per-module
`# mypy: enable-error-code="override"` directive to keep the suppressions
honest — recording, in its Consequences, that the phase splitting the classes
must delete all of it in the same commit.

The patch is partial by construction. `|`'s overloads dispatch on the class
parameter the subclass inherits, not on the overridden method, so
`Unicode() | ByteString()` still infers `FilterChain[str]` and `Date() |
NoOp()` still infers `FilterChain[datetime]` — a caller reaching for `.hour`
on the latter type-checks and then fails at runtime. `test/typing/`'s
assertions pin both wrong answers so that whoever removes the inheritance has
to change them deliberately.

## Options

Options 2 and 4 both flip `issubclass(f.ByteString, f.Unicode)` and
`issubclass(f.Date, f.Datetime)` from `True` to `False`, a breaking change for
the `v4.0.0` this work targets. The cost is identical either way and does not
rank them.

### Option 1: Do nothing — keep the inheritance and the interim overrides

Leave both pairs as they are, and with them the two suppressions and two
module-wide directives ADR 007 added.

**Pros:** No breaking change, and no diff at all.
**Cons:** Leaves the chain inference wrong — the half of the contradiction the
override cannot reach, and the reason #34 scheduled the split. The
`test/typing/` assertions go on pinning an answer known to be false.
**Risks:** The interim suppressions are honest only while something is
scheduled to remove them. Kept indefinitely, they make ADR 007's decay
detection guard a permanent state, and the next reader cannot tell a
deliberate override from a mistake.

### Option 2: Siblings under a shared private generic base (Accepted)

`_BaseDecoder(BaseFilter[T_out])` holds the initialiser, `__str__` and the
decode logic common to `Unicode` and `ByteString`; each becomes
`_BaseDecoder[str]` / `_BaseDecoder[bytes]` and declares its own `_apply`.
`_BaseDatetime` does the same for `Datetime` and `Date`.

**Pros:** Each class's parameter now matches what its `_apply` returns, so the
overloads infer chains correctly without any per-method override.
**Cons:** Adds a class to each module that exists only to be inherited from.
**Risks:** None distinct from the shared cost above.

#### Where the shared logic lives

Naming the shared method `_apply` — the obvious first pass — recreates the
Liskov violation one level up: the base's `_apply` returns a fixed `str`,
contradicting `BaseFilter[T_out]`'s own `_apply`, and then contradicting
`ByteString`'s when it binds `T_out` to `bytes`. Measured on a fixture in this
repository's environment, `mypy --enable-error-code override` reports exactly
two errors: `Return type "str" of "_apply" incompatible with return type
"T_spike" in supertype "filters.base.BaseFilter"` and `Return type "bytes" of
"_apply" incompatible with return type "str" in supertype
"_NaiveBaseDecoder"`. Under this ADR's `_decode`/`_parse` naming the same
command reports nothing, and both checkers infer `SoundUnicode() |
SoundByteString()` as `FilterChain[bytes]`. Pyright is silent on both
fixtures, because [ADR 004][]'s baseline sets
`reportIncompatibleMethodOverride = false`.

### Option 3: Keep the inheritance and make `Unicode` and `Datetime` generic

`class Unicode(BaseFilter[T_out])` with `class ByteString(Unicode[bytes])`,
so the subclass rebinds the parameter rather than inheriting a wrong one.

**Pros:** Preserves both `issubclass` relationships, so nothing breaks
downstream.
**Cons:** Gives `Unicode` a type parameter it cannot honour — its `_apply`
returns `str` unconditionally. Measured on a fixture: both checkers accept
`GenericUnicode[int]().apply("x")` as `int | None`. The parameter is public
API under [ADR 005][]'s scheme, where every other filter's parameter names
what that filter actually produces.
**Risks:** This is the naive shape again, one class further out. On the same
fixture `mypy --enable-error-code override` reports the identical pair of
errors: `Unicode._apply` contradicts `BaseFilter`'s `T_out`, and
`ByteString._apply` contradicts `Unicode`'s `str`. The `override` violation
survives the change meant to remove it.

### Option 4: Siblings sharing a plain mixin outside the filter hierarchy

`class _DecoderMixin` (not a `BaseFilter`), with `class Unicode(_DecoderMixin,
BaseFilter[str])` and `class ByteString(_DecoderMixin, BaseFilter[bytes])`.

**Pros:** Same corrected inference as Option 2, and the shared code is
unambiguously not a filter.
**Cons:** The shared code is not filter-independent: `_decode` calls
`self._invalid_value` and `_parse` reads `self.CODE_INVALID`, both from
`BaseFilter`. A mixin using them either declares those members itself,
duplicating `BaseFilter`'s surface, or type-checks only by accident.
**Risks:** `FilterMeta.__init__` merges `templates` only from bases that are
themselves `FilterMeta` instances, so a plain mixin's entries reach a subclass
by ordinary MRO lookup alone — and only while the mixin is listed first.
Measured: `class Uses(Mixin, BaseFilter[str])` carries the mixin's template,
and `class Uses(BaseFilter[str], Mixin)` silently drops it.

## Decision

Option 2, with the shared logic under `_decode` and `_parse` rather than
`_apply`. Option 3 looks least disruptive and is the trap: it keeps the
runtime relationship by making `Unicode`'s type parameter meaningless, and
still leaves `ByteString` overriding a method whose signature it cannot
satisfy. Option 4 buys separation the shared code cannot use, both helpers
depending on `BaseFilter`'s error-reporting members.

`Unicode.register(ByteString)` — and its `Datetime`/`Date` twin — is rejected
rather than deferred. Registering restores the `issubclass` answer by
asserting the exact "is-a" claim the split exists to deny, leaving the library
to say one thing to a type checker and the opposite to `issubclass`. Nothing
depends on that answer today. Verified by `rg` over this repository's `test/`
and `src/` — the only `issubclass` calls are `FilterMacroType` and
`extensions.py`'s registry guard — and over shallow clones of the three known
downstream consumers at `todofixthis/paddock` (`0f91e67`),
`todofixthis/filters-pydantic` (`fe0b367`) and `todofixthis/filters-iso`
(`85de405`): none mentions `ByteString` or `Date`, and `paddock`'s single use
of `Datetime` is a direct `f.Datetime()` call this ADR does not touch.

That verification is narrower than it sounds, and deliberately so. [The
plan][] scopes the whole release's breaking surface to "one `issubclass`
result and one no-op operator", reaching none of the three repositories above
— a scope covering the downstream consumers but not this repository's own
`docs/`, where an `rg` sweep found a worked example the operator half of that
sentence breaks (see [ADR 009][]). The clones are a point-in-time check of
three repositories, not a claim about every consumer.

## Consequences

- `issubclass(f.ByteString, f.Unicode)` and `issubclass(f.Date, f.Datetime)`
  become `False`, as do the corresponding `isinstance` checks. This is the
  breaking change `v4.0.0` carries. A runtime assertion in
  `test/test_byte_string.py` and `test/test_date.py` records it, so a later
  change restoring either relationship fails rather than passing quietly.
- `Date.templates` loses its inherited `not_datetime` entry and keeps
  `not_date`. `FilterMeta` merges templates along the MRO, so the entry was
  only ever reachable through the inheritance, and `Date` never emitted it:
  `_parse` resolves `self.CODE_INVALID` polymorphically.
- ADR 007's scaffolding goes in the same commit — both suppressions, both
  `apply`/`_apply` overrides that carried them, and both module-wide
  `override` directives. `string.py` and `simple.py` return to the same
  `override` standard as their siblings, until Phase 6 levels the whole
  package up under ADR 004's trigger.
- `test/typing/test_string.py` and `test/typing/test_simple.py` stop pinning
  the wrong chain inference and pin `FilterChain[bytes]` and
  `FilterChain[date]` instead.
- `_BaseDecoder` and `_BaseDatetime` are private and stay out of `__all__`, so
  neither reaches the rendered API docs. A downstream filter wanting the
  shared decode or parse logic has no supported way to get at it.

[#34]: https://github.com/todofixthis/filters/issues/34
[ADR 004]: 004-type-checking-in-ci.md
[ADR 005]: 005-parameterise-filters-on-one-output-type.md
[ADR 007]: 007-reactivate-a-disabled-checker-code-per-module.md
[ADR 009]: 009-drop-none-as-an-operand-of-the-chaining-operator.md
[`ByteString`]: ../../src/filters/string.py
[`Date`]: ../../src/filters/simple.py
[`Datetime`]: ../../src/filters/simple.py
[the plan]: https://github.com/todofixthis/filters/pull/116
[`Unicode`]: ../../src/filters/string.py
