---
status: Accepted
date: 2026-11-22
scope: [pyproject.toml, .github/workflows/build.yml, src/filters/, test/typing/]
summary: Run mypy --strict and pyright strict mode in CI on src and test/typing, disabling only return-value, no-any-return and reportReturnType until filters stop returning None to reject, rather than each checker's default rules, a hand-picked subset of strict rules, or an inline suppression at each rejection path; fix a new error, or suppress it inline with a comment saying why, never by disabling a code.
revisit-when: Filters stop returning None to reject a value (#121), so return-value, no-any-return and reportReturnType can be re-enabled.
---

# 016: Run the Type Checkers in Strict Mode

## Context

[ADR 015][] held mypy and pyright to their default rules plus mypy's
`check_untyped_defs`, and left strict mode to [#146][]: the backlog was
annotation coverage rather than wrong types, and its volume invited bulk
`Any` annotations and suppressions.

Filters 4.0.0 is the first release to ship `py.typed`, so from then on a
consumer's checker reads this package's annotations. An unannotated
parameter or a bare `Mapping` reaches a consumer who runs strict mode as an
implicit `Any` or `Unknown`, which their checker reports in their code. That
is ADR 015's second revisit condition, "a consumer reports Any or Unknown
from this package's annotations leaking into their own strict checking", and
4.0.0 is the last point at which it can be met before a consumer does.

Measured on `develop` on 2026-11-22, with mypy 2.4.0 and pyright 1.1.411:

- `mypy --strict src` reports 123 errors: 48 `no-untyped-def`, 38
  `no-any-return`, 33 `type-arg` and 4 others.
- pyright strict mode reports 338 on `src/filters`. Of those, 263 are
  `reportUnknown*`, and nearly all of them follow from 67 missing parameter
  annotations and type arguments.
- `test/typing` adds 6 from each checker.

One strict rule cannot be cleared by fixing code. `_invalid_value` returns
`Any`, and `return self._invalid_value(...)` is how a filter rejects a value,
here and in every consumer's filter, as `docs/writing_filters.rst` teaches.
mypy reports `no-any-return` on each such line: 21 of the 38. Typing `_invalid_value` to return its `replacement`
would move those errors to `return-value` in this package, where ADR 015
already disables them, but would also report `return-value` on the same line
in every consumer's filter. Replacing the mechanism is [#121][], still open.

## Options

### Option 1: Do nothing

Keep ADR 015's default rules.

**Pros:** No diff, and no new suppressions.
**Cons:** A consumer in strict mode meets `Unknown` from this package's
public signatures, with no fix available to them short of a suppression.
**Risks:** The first report arrives after 4.0.0, when an annotation fix needs
a patch release.

### Option 2: Strict mode in both checkers, three rules disabled (Accepted)

Set `strict = true` and `typeCheckingMode = "strict"` once, over `src` and
`test/typing`. Disable `no-any-return` beside `return-value` and
`reportReturnType` until #121.

**Pros:** One setting per checker, with no list of rules to maintain. The
three exemptions share one cause and one issue that removes them.
**Cons:** With `no-any-return` off, a function that returns `Any` where it
declares a type goes unreported, in new code as well as on rejection paths.
**Risks:** pyright adds a strict rule in a release, which fails CI with no
code change. The patch-level pins ADR 015 set contain that.

### Option 3: Strict mode, with each rejection path suppressed inline

As Option 2, but keep `no-any-return` enabled and put
`# type: ignore[no-any-return]` on each `return self._invalid_value(...)`.

**Pros:** A new `Any` return outside a rejection path is reported.
**Cons:** 21 suppressions now, and one more with each rejection path a new
filter adds, each needing its reason stated. `filters-django` and
`filters-iso` already disable `no-any-return` and `return-value` together
for this mechanism, so this package would differ from the configuration the
upgrade guide tells a filter author to copy.
**Risks:** The suppressions become noise that reviewers stop reading.

### Option 4: A hand-picked subset of strict rules

Enable the rules that annotate public signatures, such as
`disallow_untyped_defs` and `reportMissingParameterType`, and leave the rest.

**Pros:** A smaller diff.
**Cons:** About 70 unannotated sites cause most of both checkers' errors, so
a subset saves little work and leaves a list of exemptions to justify.
**Risks:** The list drifts, as ADR 004's baseline did.

## Decision

Option 2. Strict mode is what makes this package's annotations safe to
consume, and the work was annotation coverage, as ADR 015 predicted: the
backlog cleared with 13 suppressions in `src`, each a checker limitation
rather than a hidden defect.

`no-any-return` joins the two disabled rules because it reports the same
mechanism, and ADR 015's reasoning for disabling `return-value` globally
applies to it unchanged. The cost is real. Two of the other 17
`no-any-return` errors were annotation gaps, now fixed, and 15 stay hidden: each returns a value that the filter has validated at
runtime but that the checker still sees as the `Any` parameter it came from.
#121 rewrites every `_apply` body that has one, and has to clear them to
re-enable the rule.

A new error is still fixed where the fix is local and honest, and otherwise
suppressed on the line the checker reports, with a comment saying why. Never
by disabling a code or rule, and not with an annotation of `Any` where a
narrower type is true. `Any` is correct where the value really is arbitrary:
a filter's input, a mapping's keys, arguments forwarded to another callable.

The rest of ADR 015 still holds, restated here since this ADR supersedes it:

- Both checkers, on `src` and `test/typing`. mypy is what consumers run;
  pyright catches constructs mypy reads differently, so dropping either
  leaves its blind spots unguarded.
- The `test/typing/` `assert_type` harness, checked by both: a runtime test
  cannot see a chain type collapse to `Any`.
- Checkers pinned below the next minor release (`mypy>=2.4,<2.5`,
  `pyright>=1.1.411,<1.2`). pyright ships every release as 1.1.x, so for it
  `uv.lock` is what holds the version.
- `reportUnnecessaryTypeIgnoreComment`, and mypy's `warn_unused_ignores`,
  which `strict` now sets, so a suppression that stops being needed fails the
  build. `enableTypeIgnoreComments = false` keeps each checker reading only
  its own suppressions.
- `ignore_missing_imports`, since `regex` ships no stubs; and the autohooks
  mypy plugin scoped to `src` and `test/typing` to match CI.
- `py.typed` in the wheel, and `typing_extensions` as a runtime dependency
  for PEP 696 `TypeVar` defaults on Python 3.12.
- The suppressions ADR 015 lists, including
  `reportIncompatibleMethodOverride` on each `__copy__` override.

## Consequences

- A consumer who runs `mypy --strict` on their own filters gets
  `no-any-return` on each `return self._invalid_value(...)`. The upgrade
  guide's Known Limitations says so, and tells them to disable it with
  `return-value`, as this package does.
- pyright narrows a value through `isinstance()`, or reads `type()` of an
  `Any` value, as a type with `Unknown` type arguments; mypy reads `Any`. A
  `cast` that supplies the arguments satisfies pyright and fails mypy's
  `redundant-cast`, so 11 of the 13 suppressions in `src` are
  `# pyright: ignore` on such a line. The other
  2 are `reportPrivateUsage` where the chaining operators call
  `FilterChain._add`. AGENTS.md carries the rule for new code.
- black re-wraps a line that overflows only because of a `# pyright: ignore`
  comment, which moves the comment off the line pyright reports. A few
  statements are split in two to keep the line short, and one site in
  `string.py` uses a `cast` that mypy accepts instead.
- Signature changes that a caller can observe:
  - `FilterError.__init__` drops `**kwargs`. `ValueError` rejects keyword
    arguments, so passing one raised `TypeError` before and still does.
  - `FilterMeta.__init__` takes its three arguments positionally only, as
    `type.__new__` passes them.
  - `Omit`, `Pick`, `FilterRepeater` and `FilterMapper` type their key
    collections as `Iterable[Any]`, not `Iterable[Hashable]`: the same keys
    index sequences and sort, which `Hashable` does not allow.
  - The `filters.pytest` fixtures return `Callable[..., FilterRunner[Any]]`.
- `FilterRepeater` and `FilterMapper` create their result generator before
  the `isinstance` check that picks the result type. Nothing runs until the
  result type consumes it, so behaviour is unchanged.
- In `test/typing`, the four negative cases also suppress
  `reportUnknownVariableType`, since the rejected expression has no type.

[#121]: https://github.com/todofixthis/filters/issues/121
[#146]: https://github.com/todofixthis/filters/issues/146
[ADR 015]: 015-hold-the-type-checkers-to-their-default-rules.md
