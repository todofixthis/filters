---
status: Accepted
date: 2026-08-30
scope: [pyproject.toml, .github/workflows/build.yml, test/typing/]
summary: Run both mypy and pyright in CI, held to today's error set via disabled codes/rules rather than --strict, plus a test/typing/ assert_type harness checked by both.
revisit-when: Phase 6 ratchets both checkers to full strictness and clears the disabled-code/rule lists this ADR adds.
---

# 004: Type Checking in CI

## Context

[#34][] asks for generic type hints across the filter hierarchy, so a type
checker can infer a chain's output type. Before any of that lands, three
things need to exist: a marker so the package's own annotations are visible
to consumers, at least one checker running in CI so a regression is caught
automatically, and a harness that can assert an inferred type rather than
merely a runtime value — `FilterChain[str]` silently degrading to
`FilterChain[Any]` produces no failing assertion in the existing suite.

Neither checker was wired up before this: mypy is commented out of
`[dependency-groups]`, `[tool.autohooks]` and `[tool.tox]`, and pyright is
entirely absent. The tree also isn't clean under either checker today, for
reasons unrelated to #34 — pre-existing bugs the generics work neither
causes nor needs to fix to proceed.

## Options

### Option 1: Do nothing

Leave both checkers unwired until the generics work lands, then adopt
checking and strictness together as one change.

**Pros:** No baseline-vs-strict distinction to design or explain.
**Cons:** Nothing catches a chain-type regression during the eight phases
that follow — the type model, the category markers, and every filter's
annotation are added without a checker running, so a mistake in phase 1
surfaces only once phase 6 turns strictness on, several phases and commits
later.
**Risks:** A regression found that late is expensive to bisect: any of the
five intervening phases could be the cause.

### Option 2: mypy and pyright in CI now, held to today's baseline; `test/typing/` harness (Accepted)

Wire up both checkers immediately, but hold each to a permissiveness level
that passes today's tree outright, and add the `assert_type` harness the
rest of the plan depends on.

**Pros:** Every phase from 1 onward runs against a working checker from
its first commit — a chain-type regression fails CI in the phase that
introduces it, not three phases later. `test/typing/` gives runtime tests a
counterpart that can see an inferred type, which is the one thing they
cannot.
**Cons:** The permissive baseline is itself a maintenance surface —
disabled codes/rules that must be tracked and eventually removed (Phase 6),
and until then a genuinely new bug in a disabled category ships unflagged.
**Risks:** A future contributor could read the disabled lists as "these
rules are unwanted" rather than "this is where the ratchet starts."

### Option 3: One checker only (mypy or pyright)

**Pros:** One toolchain, one config surface, one set of ignore comments.
**Cons:** The two disagree on several constructs this design leans on —
e.g. `Type(Mapping)` resolves to `Type[Any]` under mypy and
`Type[Mapping[_KT, _VT_co]]` under pyright — and mypy is what filters'
consumers run, so it can't be dropped, while pyright is what would catch
mypy's blind spots (and vice versa). Running only one leaves the other
checker's failure modes unguarded for the rest of the plan.
**Risks:** A construct that satisfies the one checker run in CI but breaks
the other ships unnoticed, discovered only when a consumer runs the other
checker themselves.

### Option 4: `--strict` (or `disallow_any_generics`/`reportMissingTypeArgument`) from the start

**Pros:** No baseline-then-ratchet distinction; one configuration for the
life of the project.
**Cons:** Measured on this tree: `mypy --strict --ignore-missing-imports
src` reports 205 errors, `pyright src/filters` in strict mode 680 —
overwhelmingly pre-existing issues unrelated to #34, that phases 1-5 would
either have to fix as a prerequisite (blocking the actual issue) or
suppress inline (spreading `# type: ignore` across files phases 1-5 don't
otherwise touch). `disallow_any_generics`/`reportMissingTypeArgument`
additionally reject every unparameterised `BaseFilter` subclass — which is
every filter until phase 2 annotates it — making phases 1 and 2 unable to
land as separate commits, the exact atomicity trap `TypeVar(...,
default=Any)` (PEP 696) exists to avoid.
**Risks:** None distinct from the Cons — this option's cost is why it is
rejected, not a separate risk.

## Decision

Option 2. Both checkers, wired up now, at whatever permissiveness makes
today's tree pass outright — not Option 4's `--strict`, and not
`disallow_any_generics`/`reportMissingTypeArgument` on their own, since
either rejects every unparameterised subclass and reintroduces the
phase-1/2 atomicity trap `default=Any` is meant to have already solved.
Only mypy (what consumers run) or only pyright (Option 3) each leave the
other's blind spots unguarded for the eight phases still to come, which is
the risk this ADR exists to close early rather than at phase 6.

Measured on this tree with `ignore_missing_imports = true` (mypy) and
default rule settings (pyright), after the two source fixes below:

| checker | invocation | errors | files |
|---|---|---|---|
| mypy 1.20.2 | `mypy src` | 37 | 5 |
| pyright 1.1.411 | `pyright src/filters` | 71 | 8 |

No single flag reaches zero without also reaching `--strict`, so the
baseline instead disables the specific codes/rules today's 37 and 71 errors
fall under — `disable_error_code` in `[tool.mypy]`
(`arg-type`, `assignment`, `attr-defined`, `call-arg`, `call-overload`,
`no-redef`, `operator`, `override`, `return`, `return-value`, `union-attr`,
`var-annotated`) and the matching rules in `[tool.pyright]`
(`reportArgumentType`, `reportAssignmentType`, `reportAttributeAccessIssue`,
`reportCallIssue`, `reportGeneralTypeIssues`,
`reportIncompatibleMethodOverride`, `reportOperatorIssue`,
`reportOptionalCall`, `reportOptionalIterable`, `reportOptionalMemberAccess`,
`reportRedeclaration`, `reportReturnType`, all set `false`). Both checkers
then pass at exit 0 against `src`, and `disable_error_code`/the `false`
rules are exactly what Phase 6 ratchets away as it clears the backlog each
one currently hides.

Two source fixes landed as part of this baseline, ahead of any generics
work, because each was independently wrong and each is a prerequisite the
plan's own strictness table assumes: `test.py:51`'s `filter_type:
Callable[[...], BaseFilter]` used `[...]` where `Callable` takes either a
parameter-type list or the bare `...`, corrected to `Callable[...,
BaseFilter]`; `BaseFilter.resolve_filter`'s declared `Optional["FilterChain"]`
return type didn't match its body, which returns the resolved `BaseFilter`
of whichever subclass was passed in — corrected to `Optional["BaseFilter"]`.
Both were mypy errors independent of the disabled-code list above (`misc`
and one instance of `return-value`, respectively) and neither changes
behaviour, so fixing them isn't part of the baseline-vs-strict trade-off
this ADR is otherwise about.

`test/typing/` holds `assert_type`-based modules, checked by both mypy and
pyright as a run distinct from the `src` baseline above (`mypy test/typing`,
`pyright test/typing`) — this is the harness runtime tests cannot
substitute for, since a value can be correct at runtime while its static
type has already collapsed to `Any`. A wrong `assert_type` was confirmed to
fail on both checkers during this work. The one starter module,
`test_smoke`, asserts against today's already-explicit annotations
(`BaseFilter.set_handler`, and the corrected `resolve_filter` above) rather
than against `apply()`'s inferred type, which pyright and mypy already
disagree on pre-Phase-1 (pyright's call-site inference over `apply`'s
unannotated body reports `Unknown | Any | None`; mypy, which does not infer
untyped bodies by default, reports plain `Any`) — the same class of
divergence `test/typing/`'s own docstring rule warns against for `Type`'s
abstract-argument overloads.

## Consequences

- CI gains a `typecheck` job running four steps: `mypy src`, `mypy
  test/typing`, `pyright src/filters`, `pyright test/typing`. The
  `autohooks.plugins.mypy` pre-commit hook is scoped to `src/*.py` and
  `test/typing/*.py` to match, via `[tool.autohooks.plugins.mypy].include`
  — otherwise its default `*.py` include would run mypy against any staged
  file, including ones outside this ADR's scope (e.g. `scripts/`) that
  still fail even under `ignore_missing_imports` (a known-stub-package hint
  such as `types-PyYAML`, which that flag does not suppress).
- `pyright` and `mypy` join `[dependency-groups]` dev and ci, pinned exact
  (`mypy==1.20.2`, `pyright==1.1.411` — both newer patch/minor releases of
  the versions #34's design was validated against, 1.19.1 and 1.1.408, in
  the same major line) so a new release can't silently change which of
  today's errors are and aren't caught. `autohooks-plugin-mypy` has no
  pyright counterpart on PyPI, confirmed by search — pyright runs as a
  plain tox command and CI step instead of through autohooks.
- `typing_extensions` becomes a runtime dependency (`uv add --bounds major
  typing_extensions`): `TypeVar(..., default=)` (PEP 696), which the type
  model in #34 depends on, is native only from Python 3.13, and
  `requires-python` here stays `>=3.12`.
- `src/filters/py.typed` ships in the wheel with no `pyproject.toml` build
  change beyond adding the file — confirmed by building the wheel and
  inspecting its contents; hatchling's existing `include = ["src/filters"]`
  already covers non-`.py` files under that path. Downstream, this is also
  what let `test/typing/` see real types from `import filters` at all: `uv
  run mypy` treated every `filters` symbol as `Any` (via
  `ignore_missing_imports`) until the marker existed, the same way it would
  for any third-party package without one.
- `AGENTS.md`'s "Place comments on the preceding line" rule gets an
  exception for `# type: ignore[...]`/`# pyright: ignore[...]`: both only
  suppress the exact line they trail, so a leading comment (e.g. on an
  `@overload`) leaves the error reported against the `def` below it, and
  `reportUnnecessaryTypeIgnoreComment` is off by default — a misplaced
  ignore then fails silently rather than erroring. Both are now on
  (`warn_unused_ignores` in `[tool.mypy]`,
  `reportUnnecessaryTypeIgnoreComment` in `[tool.pyright]`), closing that
  gap for `src` and `test/typing`.
- `reportGeneralTypeIssues` is the broadest-sounding rule in the disabled
  pyright list, but its footprint here is narrow: run under a bare
  `pyrightconfig.json` (no `[tool.pyright]` overrides), it fires on exactly
  2 pre-existing errors in `src` — `base.py:78` (a `UnionType` used where a
  class is expected) and `macros.py:76` (a zero-argument `super()` call
  inside a `@staticmethod`) — both unrelated to [#34][].
- `mypy src` also prints `annotation-unchecked` notes on every run (e.g.
  `complex.py:93: note: By default the bodies of untyped functions are not
  checked, consider using --check-untyped-defs`). These are notes, not
  errors, so the exit code is unaffected: mypy skips checking variable
  annotations inside untyped function bodies unless `--check-untyped-defs`
  is set, which this baseline leaves unset. Expected, non-blocking noise —
  Phase 6 is the natural place to revisit `check_untyped_defs`. 21 when
  this ADR was written, 2 at the tip of #34's branch: annotating a function
  body is what stops it triggering the note.
- Re-measured at that same tip, the backlog the disabled codes hide has
  roughly doubled rather than shrunk: `mypy src` with all twelve codes
  re-enabled reports 77 errors against the 37 above. Two codes supply 32 of
  the 40 new ones — `return-value` (2 then, 22 now) and `no-redef` (1 then,
  13 now) — both a direct consequence of Phase 2 giving every `_apply` a
  declared return type for mypy to check each rejection path against.
  Pyright rises the same way, 76 to 114 under a bare `pyrightconfig.json`
  at both points — a different invocation from the table's 71, so compare
  the pair, not either figure to it. The disabled list is therefore not the
  frozen pre-#34 snapshot the Decision above describes: pinning a baseline
  by code fixes which categories are ignored, not how many errors they
  hide.
- `return-value` cannot be cleared by tidying. Nearly every instance is
  `Incompatible return value type (got "None", expected ...)` where a
  filter returns `self._invalid_value(...)`, and replacing that rejection
  mechanism with a raised `FilterError` is what [future work 002][]
  proposes and defers. Until that lands, Phase 6 can only leave this code
  disabled or suppress it at every rejection path — so `revisit-when` is
  gated on a decision this ADR does not own.
- Every disabled mypy code and `false` pyright rule above is a debt Phase 6
  must clear, not a permanent configuration — the point at which
  `revisit-when` fires.

[#34]: https://github.com/todofixthis/filters/issues/34
[future work 002]: ../future/002-filters-raising-filtererror-directly.md
