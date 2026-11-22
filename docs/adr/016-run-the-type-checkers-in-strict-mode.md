---
status: Accepted
date: 2026-11-22
scope: [pyproject.toml, .github/workflows/build.yml, src/filters/, test/typing/]
summary: Run mypy --strict and pyright strict mode in CI on src and test/typing, disabling only return-value, no-any-return and reportReturnType until filters stop returning None to reject, rather than each checker's default rules, a hand-picked subset of strict rules, retyping _invalid_value, or an inline suppression at each rejection path; fix a new error, or suppress it inline with a comment saying why, never by disabling a code or by annotating Any where a narrower type is true.
revisit-when: Filters stop returning None to reject a value (#121), so return-value, no-any-return and reportReturnType can be re-enabled; a consumer reports Any or Unknown from this package's annotations although both checkers pass in strict mode; the suppressions for checker limitations in src grow well past the 13 this ADR records.
---

# 016: Run the Type Checkers in Strict Mode

## Context

[ADR 015][] held mypy and pyright to their default rules plus mypy's
`check_untyped_defs`, and left strict mode to [#146][]: the backlog was
annotation coverage rather than wrong types, and its volume invited bulk
`Any` annotations and suppressions.

`py.typed` first shipped in `4.0.0a1`, so a consumer's checker now reads this
package's annotations. To a consumer who runs strict mode, an unannotated
`__init__` is a `no-untyped-call` error under mypy, and a bare `Mapping`
parameter is `Unknown` under pyright, each reported in their code. That is
ADR 015's second revisit condition, "a consumer reports Any or Unknown from
this package's annotations leaking into their own strict checking". No
consumer has reported it against either alpha; 4.0.0 is the last release
before 3.x users at large can.

Measured on `develop` on 2026-11-22, with mypy 2.4.0 and pyright 1.1.411:

- `mypy --strict src` reports 123 errors: 48 `no-untyped-def`, 38
  `no-any-return`, 33 `type-arg` and 4 others.
- pyright strict mode reports 338 on `src/filters`. Of those, 263 are
  `reportUnknown*`, and nearly all of them follow from 67 missing parameter
  annotations and type arguments.
- `test/typing` adds 6 from pyright and 4 from mypy, 3 of the 4 in
  `test/__init__.py`, which it imports.

`_invalid_value` returns `Any`, and `return self._invalid_value(...)` is how
a filter rejects a value, here and in every consumer's filter, as
`docs/writing_filters.rst` teaches. mypy reports `no-any-return` on each such
line: 21 of the 38. The other 17 return a value the checker sees as `Any`
for some other reason, most often `return value` after
`value = self._filter(value, ...)`, where `value` is still the `Any`
parameter. Replacing the rejection mechanism is [#121][], still open.

## Options

### Option 1: Do nothing

Keep ADR 015's default rules.

**Pros:** No diff, and no new suppressions.
**Cons:** A consumer in strict mode gets errors in their own code from this
package's signatures, with no fix available to them short of a suppression.
**Risks:** The first report arrives after 4.0.0, when an annotation fix needs
a patch release.

### Option 2: Strict mode in both checkers, three rules disabled (Accepted)

Set `strict = true` and `typeCheckingMode = "strict"` once, over `src` and
`test/typing`. Disable `no-any-return` beside `return-value` and
`reportReturnType` until #121. `filters-django` and `filters-iso` already
disable the two mypy rules together for this mechanism.

**Pros:** One setting per checker, with no list of rules to maintain. No
annotation a consumer already checks against changes its meaning.
**Cons:** With `no-any-return` off, a function that returns `Any` where it
declares a type goes unreported, in new code as well as on rejection paths.
A consumer under `mypy --strict` has to disable the rule too, or suppress
each rejection path.
**Risks:** #121 clears the 21 rejection paths but not every other
`no-any-return` error, so the rule may stay off after it lands.

### Option 3: Strict mode, with `_invalid_value` retyped

Keep `no-any-return` enabled, and change `_invalid_value`'s return
annotation so that `return self._invalid_value(...)` type-checks. Two
annotations were tried:

- **`T_out`, the filter's output type.** Clean in `_apply` under
  `mypy --strict`, here and in a consumer's parameterised filter.
- **A type variable used nowhere else in the signature**, so that each call
  takes the type its context expects. Clean in every return position under
  mypy, default and strict, and under pyright's default rules.

**Pros:** `no-any-return` stays on, and the documented rejection needs no
suppression from a consumer.
**Cons:** With `T_out`, `return self._invalid_value(...)` from a helper
whose return type differs, such as `-> int`, reports `return-value` and
`reportReturnType` at each checker's default rules, where 4.0.0a2 reported
nothing. An unparameterised subclass still reports `no-any-return`. With the
lone type variable, pyright strict mode reports the result as `Unknown`
wherever the context is `Any`, and both checkers report the definition
itself as a misuse.
**Risks:** Consumers who upgrade from an alpha meet new errors with no code
change, at settings where this package promised none.

### Option 4: Strict mode, with each rejection path suppressed inline

As Option 2, but keep `no-any-return` enabled and put
`# type: ignore[no-any-return]` on each `return self._invalid_value(...)`.

**Pros:** A new `Any` return outside a rejection path is reported.
**Cons:** 21 suppressions, and one more with each rejection path a new
filter adds. A consumer still has to add their own.
**Risks:** The suppressions become noise that reviewers stop reading.

### Option 5: A hand-picked subset of strict rules

Enable the rules that annotate public signatures, such as
`disallow_untyped_defs` and `reportMissingParameterType`, and leave the rest.

**Pros:** A smaller diff.
**Cons:** About 70 unannotated sites cause most of both checkers' errors, so
a subset saves little work and leaves a list of exemptions to justify.
**Risks:** The list drifts, as ADR 004's baseline did.

## Decision

Option 2. Strict mode removes implicit `Any` and `Unknown` from this
package's signatures, and the work was annotation coverage, as ADR 015
predicted: the backlog cleared with 13 suppressions in `src`, each a checker
limitation rather than a hidden defect. Nothing checks the consumer's view
directly: `pyright --verifytypes filters` still counts unannotated attributes
and class constants as ambiguous, and CI runs no consumer-side strict check.

`no-any-return` joins the two disabled rules because 21 of its 38 errors are
the rejection mechanism, and ADR 015's reasoning for disabling `return-value`
globally applies to those unchanged. Option 3 was implemented with `T_out`
and withdrawn: it trades an error that only strict mode reports for one that
default settings report. Of the other 17 errors, 9 are fixed: two annotation
gaps, and five string filters and `Decimal` that returned the `Any`
parameter. The remaining 8 stay hidden. Each returns a value whose type is a
runtime fact a checker cannot follow, such as `Type._apply` returning the
value it has just checked, and each needs a suppression when the rule comes
back on.

A new error is fixed where the fix is local and honest, and otherwise
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
- The return rules disabled globally rather than at each rejection path, on
  the comment beside each setting in `pyproject.toml`.
- Checkers pinned below the next minor release (`mypy>=2.4,<2.5`,
  `pyright>=1.1.411,<1.2`). pyright ships every release as 1.1.x, so for it
  `uv.lock` is what holds the version, including against a release that adds
  a strict rule.
- `reportUnnecessaryTypeIgnoreComment`, and mypy's `warn_unused_ignores`,
  which `strict` sets, so a suppression that stops being needed fails the
  build. `enableTypeIgnoreComments = false` keeps each checker reading only
  its own suppressions.
- `ignore_missing_imports`, since `regex` ships no stubs; and the autohooks
  mypy plugin scoped to `src` and `test/typing` to match CI.
- `py.typed` in the wheel, and `typing_extensions` as a runtime dependency
  for PEP 696 `TypeVar` defaults on Python 3.12.
- The suppressions ADR 015 lists. One of them AGENTS.md asks for in new
  code: pyright's `reportIncompatibleMethodOverride` on each `__copy__`
  override, whose `the_filter: Self` parameter narrows the base class's.

## Consequences

- A consumer who runs `mypy --strict` on their own filters gets
  `no-any-return` on each `return self._invalid_value(...)`, and on
  `return value` after `value = self._filter(value, ...)`. The upgrade
  guide's Known Limitations covers both.
- #121 is necessary to re-enable `no-any-return` but not sufficient: it has
  to suppress or restructure the 8 other sites as well.
- `src` gains 13 `# pyright: ignore` suppressions. Each new `isinstance()` on
  an `Any` value is likely to need another, which is a standing cost to
  contributors.
- pyright narrows a value through `isinstance()`, or reads `type()` of an
  `Any` value, as a type with `Unknown` type arguments; mypy reads `Any`. A
  `cast` to the same type with `Any` arguments satisfies pyright and fails
  mypy's `redundant-cast`, so 11 of the 13 suppressions sit on such a line.
  The other 2 are `reportPrivateUsage` where the chaining operators call
  `FilterChain._add`.
- black re-wraps a line that overflows only because of a `# pyright: ignore`
  comment, which moves the comment off the line pyright reports. A few
  statements are split in two to keep the line short, and one site in
  `string.py` casts to `Element[str]`, which mypy accepts because it differs
  from the type mypy inferred.
- The pre-commit hook runs mypy and not pyright, so a pyright error first
  appears in CI or tox unless the author runs pyright. AGENTS.md lists the
  command and the rules above.
- Annotation changes a caller's checker can observe:
  - `FilterError.__init__` drops `**kwargs`. `ValueError` rejects keyword
    arguments, so passing one raised `TypeError` before and still does.
  - `FilterMeta.__init__` takes its three arguments positionally only, as
    `type.__call__` passes them.
  - `JsonDecode`'s `decoder` is `Callable[[str], Any]`, and the `pattern` of
    `Regex` and `Split` is `str | re.Pattern[str]`. Each was a bare generic.
    A decoder that needs a second argument, or a bytes pattern, is a type
    error; both already failed at runtime.
  - Newly annotated, with no call rejected that passed before: the
    `filters.pytest` fixtures, `FilterMessage.code` and `as_dict`,
    `BaseFilterTestCase`'s assertions, and the `mapping_result_type` and
    `sequence_result_type` attributes.
- The key collections of `Omit`, `Pick` and `FilterRepeater` are
  `Iterable[Any]`, where they were bare `Iterable`. `Iterable[Hashable]`
  would be wrong: the same keys index sequences and are sorted, which
  `Hashable` does not allow.
- `FilterRepeater` and `FilterMapper` create their result generator before
  the `isinstance` check that picks the result type. Nothing runs until the
  result type consumes it, so behaviour is unchanged.
- `CaseFold`, `IpAddress`, `MaxBytes`, `MaxChars` and `Strip` hold the
  result of `_filter()` in a typed local, guarded with
  `if self._has_errors or text is None`. `Decimal._apply` returns `None`
  where it returned the rejected value from its type check, which was `None`
  already.
- In `test/typing`, the four negative cases also suppress
  `reportUnknownVariableType`, since the rejected expression has no type.
  Three more suppressions are new: `reportPrivateUsage` on a `_filter` call,
  `reportUntypedNamedTuple`, and `no-untyped-def` on a macro left
  unannotated on purpose.

[#121]: https://github.com/todofixthis/filters/issues/121
[#146]: https://github.com/todofixthis/filters/issues/146
[ADR 015]: 015-hold-the-type-checkers-to-their-default-rules.md
