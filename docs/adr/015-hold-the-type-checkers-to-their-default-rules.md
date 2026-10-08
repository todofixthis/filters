---
status: Accepted
date: 2026-10-08
scope: [pyproject.toml, .github/workflows/build.yml, src/filters/, test/typing/]
summary: Run mypy and pyright in CI on src and test/typing at each checker's default rules plus mypy's check_untyped_defs, disabling only return-value and reportReturnType until filters stop returning None to reject, rather than a per-code baseline or --strict and pyright strict mode; fix a new error, or suppress it inline with a comment saying why, never by disabling a code.
revisit-when: Filters stop returning None to reject a value (#121), so return-value and reportReturnType can be re-enabled; a consumer reports Any or Unknown from this package's annotations leaking into their own strict checking.
---

# 015: Hold the Type Checkers to Their Default Rules

## Context

[ADR 004][] wired mypy and pyright into CI but held both to the tree's error
set at the time: twelve mypy codes in `disable_error_code`, and the matching
twelve pyright rules set `false`. Its trigger was "Phase 6 ratchets both
checkers to full strictness and clears the disabled-code/rule lists this ADR
adds", and [#119][] is that phase.

Measured on `develop` before this change: `mypy src` (2.4.0) with every
code re-enabled reports 78 errors and `mypy --strict src` 211; `pyright
src/filters` (1.1.411) reports about 115, and about 555 in strict mode.
pyright's counts shift by a few with the config it runs under, so treat them
as approximate. Most of the strict-only surplus is `no-untyped-def`,
`no-any-return` and `type-arg` from mypy and `reportUnknown*` from pyright —
unannotated helpers, `__str__` methods and bare `Mapping`/`Iterable`
parameters rather than wrong types.

One code cannot be cleared by fixing code. A filter rejects a value by
returning `None` from an `_apply` declared to return `T_out`, mostly as
`if self._has_errors: return None` after a `_filter` call. That is 18 of the
22 `return-value` errors left once everything else is fixed; the other 4 are
the same mechanism one step removed: `apply()`'s `Optional` result read back
as non-`Optional`, or a value returned unconverted on the error path.
Replacing the mechanism is [#121][], still open.

## Options

### Option 1: Do nothing

Keep ADR 004's twelve-code baseline.

**Pros:** No churn.
**Cons:** The baseline pins categories, not counts: it grew from 37 hidden
mypy errors under ADR 004 (mypy 1.20.2) to 78 now (2.4.0), and a new bug in
any of the twelve categories ships unflagged.
**Risks:** Real defects stay hidden; clearing the lists found three (below).

### Option 2: Default rules plus `check_untyped_defs`, one code disabled (Accepted)

Clear both lists except `return-value`/`reportReturnType`, turn on mypy's
`check_untyped_defs`, and fix or suppress whatever surfaces.

**Pros:** Every category but one is enforced, and `check_untyped_defs`
removes ADR 004's `annotation-unchecked` notes by checking those bodies.
**Cons:** Not the "full strictness" ADR 004's trigger names.
**Risks:** A wrong `return` value type ships unflagged until #121.

### Option 3: Full strictness now

`mypy --strict` and pyright strict mode on top of Option 2.

**Pros:** Meets ADR 004's trigger as written.
**Cons:** Once Option 2's fixes land, 123 mypy errors and some 340 pyright
ones remain, nearly all
annotation coverage rather than type mismatches; the diff would touch every
filter for little defect-finding return. `return-value` stays blocked on #121
either way.
**Risks:** Volume invites bulk `Any` annotations and suppressions, which
satisfy strict mode while hiding exactly what it exists to surface.

## Decision

Option 2. The twelve disabled categories are where wrong types hide, and
clearing them found real bugs; strict mode's extra rules mostly measure
annotation coverage, and can land separately when worth the diff
([#146][]).

A newly surfaced error is fixed where the fix is local and honest, and
otherwise suppressed inline, on the line the checker reports, with a comment
saying why the checker is wrong or the code is deliberate. Never by adding a
code to `disable_error_code` or a `false` rule to `[tool.pyright]`: that hides
every future instance, which is how ADR 004's baseline doubled.

`return-value` and `reportReturnType` stay disabled globally, not suppressed
at each of the 22 rejection paths. Per-path ignores would make the build fail
as #121 removes each one; global disabling relies instead on the comment
beside each setting in `pyproject.toml` and this ADR's `revisit-when`, which
#121 has to answer since it rewrites every rejection path anyway.

The rest of ADR 004 still holds, restated here since this ADR supersedes it:

- Both checkers, on `src` and `test/typing`. mypy is what consumers run;
  pyright catches constructs mypy reads differently (`Type(Mapping)` resolves
  to `Type[Any]` under mypy and `Type[Mapping[...]]` under pyright), so
  dropping either leaves its blind spots unguarded.
- The `test/typing/` `assert_type` harness, checked by both: a runtime test
  cannot see a chain type collapse to `Any`.
- Checkers pinned below the next minor release (`mypy>=2.4,<2.5`,
  `pyright>=1.1.411,<1.2`): a checker can add diagnostics in a minor
  release, which would fail CI with no code change. pyright ships every
  release as 1.1.x, so for it `uv.lock` is what actually holds the version.
- `warn_unused_ignores` and `reportUnnecessaryTypeIgnoreComment`, so a
  suppression that stops being needed fails the build instead of decaying;
  `enableTypeIgnoreComments = false` keeps each checker reading only its own
  suppressions. AGENTS.md keeps both suppression forms trailing for the same
  reason.
- `ignore_missing_imports`, since `regex` ships no stubs; and the
  autohooks mypy plugin scoped to `src` and `test/typing` to match CI.
- `py.typed` in the wheel, and `typing_extensions` as a runtime dependency
  for PEP 696 `TypeVar` defaults on Python 3.12.

## Consequences

- This change adds seven suppressions:
  - mypy `override` on `FilterMeta.__or__`, which returns a `FilterChain`
    rather than `type.__or__`'s `UnionType` by design.
  - pyright `reportIncompatibleMethodOverride` on `FilterChain.__or__`:
    its overloads repeat `BaseFilter`'s verbatim, but pyright reports them
    out of order. Reproduced in a standalone two-class file; dropping the
    first or fourth overload from both sets silences it. mypy's `override`
    check still guards the set against drift.
  - pyright `reportIncompatibleMethodOverride` on each `__copy__` override,
    now typed `the_filter: Self`. [ADR 013][]'s classmethod form takes the
    instance as a parameter, so narrowing it is genuinely unsound in theory;
    `copy()` only ever passes an instance of `cls`. A new override per ADR 013
    carries the same suppression.
  - mypy `assignment` on `Round`'s and `Optional`'s defaults for parameters
    typed with a TypeVar, which mypy rejects even when they match the
    TypeVar's PEP 696 default.
- Clearing the lists fixed three bugs, each with a regression test:
  `str(Strip(leading=""))` raised `AttributeError`; `Item` reported a missing
  non-`str` mapping key as an exception rather than `missing`, because the
  key reached `str.join`; `FilterRunner(None)` failed on first use with
  `AttributeError` and now raises `TypeError` at construction.
- Where a body narrows `_filter`'s `Optional` result before using it, it
  guards with `if self._has_errors or result is None` rather than a `cast`.
  The `is None` half is redundant at runtime and goes with #121.
- `value: str = self._filter(value, ...)` annotations re-declaring the
  `value: Any` parameter are gone (mypy `no-redef`). Both checkers keep a
  re-assigned `Any` parameter as `Any`, so the annotations never typed the
  body; #121 will not restore that either, since `value` stays `Any`.
- The negative cases in `test/typing/test_chain_inference.py` now suppress
  `operator`/`reportOperatorIssue` on the chaining expression instead of an
  `assert_type` mismatch, so they assert the rejection itself. The class form
  must be an annotated assignment: mypy reads an unannotated
  `x = SomeFilter | None` as a PEP 604 type alias and never checks `|`.
  Replaces the guard [ADR 009][] describes.
- Smaller behaviour changes from the fixes:
  - `T_next`, the `|` overloads' type variable for the right-hand filter,
    gains `default=Any`: PEP 696 forbids a TypeVar without a default after
    `FilterMeta.__or__`'s `T_out`, which has one. Every overload solves it
    from the operand, so inference is unchanged.
  - `Round`'s `result_type` is typed `Callable[[Decimal], T_result]` rather
    than `type[T_result]`, so a converter function now type-checks too.
  - `Item` reports a missing mapping key under its `str()` form, so key `0`
    now appears as `"0"` rather than dropping out of the error key.
  - `_invalid_value` no longer mutates the caller's `template_vars`.
  - `MemoryHandler.exc_info` entries are built from the exception passed
    to `handle_exception` rather than `sys.exc_info()`. That is identical
    when it is the exception being handled, as at every call site in `src`,
    and is typed `tuple[type[Exception], Exception, Optional[TracebackType]]`.

[#119]: https://github.com/todofixthis/filters/issues/119
[#121]: https://github.com/todofixthis/filters/issues/121
[#146]: https://github.com/todofixthis/filters/issues/146
[ADR 004]: 004-type-checking-in-ci.md
[ADR 009]: 009-drop-none-as-an-operand-of-the-chaining-operator.md
[ADR 013]: 013-copy-a-filters-own-mutable-containers-in-copy.md
