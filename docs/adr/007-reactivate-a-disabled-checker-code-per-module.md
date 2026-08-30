---
status: Accepted
date: 2026-08-30
scope: [src/filters/]
summary: Re-enable mypy's globally disabled `override` code with a file-level directive in each module carrying an interim override suppression, rather than adding `unused-ignore` to the suppression comment, which forfeits decay detection.
revisit-when: A module that needs this interim suppression also carries an unrelated `override` violation, which the module-wide directive would turn into a hard failure.
---

# 007: Reactivate a Disabled Checker Code per Module for an Interim Override Suppression

## Context

Phase 2 of [#34][] parameterises every filter on its output type, and two
inheritance pairs contradict that: [`ByteString`][] extends [`Unicode`][] but
returns `bytes` where its parent returns `str`, and [`Date`][] extends
[`Datetime`][] but returns `date` where its parent returns `datetime`. Each
subclass overrides `apply`/`_apply` to report the type it actually produces,
and each override is a genuine Liskov violation — one that predates this work
and is visible today only if mypy's `override` code is on.

It is not. [ADR 004][] holds both checkers to the tree's error set at the
time, which puts `override` in `disable_error_code` in `pyproject.toml` and
`reportIncompatibleMethodOverride = false` in `[tool.pyright]`. Phase 5 splits
each pair into siblings under a shared private base, removing the inheritance
and the contradiction together; [the plan][] records that as a chosen
breaking change. Both overrides are therefore deliberate, reviewed interim
states with a scheduled end, not bugs to fix now.

The complication is the pairing of `disable_error_code` with
`warn_unused_ignores = true`, from the same ADR. With `override` disabled
project-wide, mypy generates no diagnostic for a `# type: ignore[override]` to
match, so it reports the comment itself as an unused ignore — failing the
"both checkers exit 0" bar the same ADR sets. The plan already names this
exact bind: "Under `--warn-unused-ignores` the interim suppressions must be
added in Phase 1 or 2 and removed in the same commit as Phase 5, or the build
breaks on one side or the other."

Pyright is not part of this only as long as `reportIncompatibleMethodOverride`
stays `false` in `[tool.pyright]`: `enableTypeIgnoreComments = false` makes it
skip `# type: ignore` comments entirely, so today neither the violation nor
its suppression reaches it. Re-enabling that rule before Phase 5 splits the
classes would need a `# pyright: ignore[reportIncompatibleMethodOverride]`
beside each `# type: ignore[override]` — neither file carries one. What
follows is a mypy-only question, contingent on that ordering.

Each override fixes only the *direct* call, independent of which suppression
mechanism this ADR picks: `ByteString().apply(x)` reports `bytes` and
`Date().apply(x)` reports `date`, but a chain through either filter still
infers the parent's type, since `|`'s overloads dispatch on the class
parameter the subclass inherits rather than on the overridden method.
`test/typing/test_string.py` and `test/typing/test_simple.py` pin that wrong
inference, so whoever removes the override in Phase 5 has to update the
assertions deliberately.

## Options

Options 2 and 3 both leave per-line comments in two files for Phase 5 to
remove; that obligation is identical and does not rank them — enforcement is
where they differ.

### Option 1: Do nothing — keep the overrides, add no suppression

Annotate `apply`/`_apply` on both subclasses and write no ignore comment,
leaving `disable_error_code` to swallow the resulting error.

**Pros:** Nothing to remove in Phase 5 beyond the overrides themselves; no
module-wide scope change; smallest diff.
**Cons:** Verified against a fixture reproducing the project's mypy settings:
mypy reports nothing at all, so the tree carries two known Liskov violations
with no in-source marker. `mypy --enable-error-code override
src/filters/string.py` — the command that reveals what the disabled code
hides — then reports errors with no way to tell an accepted one from a new
one.
**Risks:** When Phase 6 clears the disabled-code list, both errors surface at
once with nothing in the source saying they were expected; the cheapest way to
green is to revert the return annotations to the parent's type, silently
undoing what Phase 2 added them for.

### Option 2: A file-level `# mypy: enable-error-code="override"` directive plus `# type: ignore[override]` (Accepted)

Re-enable the code for the one module, so the plain ignore has a real
diagnostic to consume.

**Pros:** Confirmed on the same fixtures: the ignore registers as used while
the contradiction stands, and mypy reports `Unused "type: ignore" comment`
the moment the contradiction goes away.
**Cons:** Widens `override` enforcement to the whole module rather than the
two suppressed lines, and couples both files to `base.py`'s signatures — see
Consequences.
**Risks:** None distinct from the Cons.

### Option 3: `# type: ignore[override, unused-ignore]` with no directive

Suppress the override error and, in the same comment, the unused-ignore
complaint that the disabled code provokes.

**Pros:** One comment, one line, no module-wide scope change, and nothing to
remember to remove beyond the comment itself.
**Cons:** Measured against the fixture where the contradiction is removed and
the comment left behind: mypy reports nothing, exactly as it does while the
comment is needed. The two states are indistinguishable.
**Risks:** `unused-ignore` is the mechanism `warn_unused_ignores` uses to
report decay, so suppressing it disables decay detection for that line
permanently — and does so invisibly, since a stale comment and a live one
produce identical output.

## Decision

Option 2. Option 3 reads as the smaller change and is the one to reach for
instinctively, but it trades away the single property the interim state
depends on: Phase 5 removes the contradiction in a commit that also has to
find and delete these comments, and only Option 2 fails if it does not. Option
1 keeps the violation entirely unrecorded, which is worse than either — the
tree already hides it once via `disable_error_code`, and hiding it a second
time leaves the deliberate overrides indistinguishable from accidental ones.

A third module needing this technique is not by itself a reason to reopen
this: the pattern is cheap to repeat, and centralising it means removing
`override` from the disabled list, which is Phase 6's job under ADR 004's own
revisit trigger. What would reopen it is a module that needs the suppression
*and* carries an unrelated `override` violation: the directive still works
there too — a second `# type: ignore[override]` records the unrelated
violation rather than hiding it, arguably an improvement on today's silence —
but doing so repeats the trade ADR 004's Option 4 rejected: fixing or
suppressing code the phase has no reason to touch. Unrelated `override`
violations are not hypothetical: with `override` forced on, `base.py`
reports two such errors (`__or__`, `__copy__`), confirmed as of `b6cf12a`.
`complex.py` carries a comparable violation today (`FilterRepeater.__copy__`,
two diagnostics), though Phase 2 hasn't yet annotated that file, so the
count there may change once it does.

## Consequences

- Phase 5 must delete the directive and the `# type: ignore[override]`
  comments from each file in the same commit that splits the classes.
  Each file's interim comment on `apply` already says the suppression goes
  with the split; the directive's own comment now says the same of itself.
  Only the suppression's removal makes the build fail if Phase 5 forgets,
  since the ignore goes stale the moment the contradiction does — the
  directive's removal is unenforced, per the point below.
- `string.py` and `simple.py` are held to a stricter `override` standard than
  the rest of `src/filters/` until Phase 6 levels them up, so a Liskov
  violation introduced in either fails CI while the same mistake elsewhere
  does not.
- The directive also couples both files to `base.py`'s (and `Unicode`'s and
  `Datetime`'s) method signatures: mypy attributes an override incompatibility
  to the *subclass*'s file, so a base-class signature change made in a later
  phase — Phases 2-6 still touch `base.py` — can newly fail the build in
  exactly `string.py`/`simple.py` while sibling modules, still shielded by
  `disable_error_code`, stay green.
- A directive left behind after its last suppression is removed goes
  unreported: mypy has no "unused `enable-error-code`" check, confirmed by
  testing a directive with no remaining suppression. The failure is benign —
  the module is checked slightly more strictly than its siblings, not
  silently broken — so it is worth removing when noticed, not worth a check
  of its own.

[ADR 008][] removes the directive and both suppressions this section
describes; the module-wide widening and the `base.py` coupling above no longer
apply as of that change.

[#34]: https://github.com/todofixthis/filters/issues/34
[ADR 004]: 004-type-checking-in-ci.md
[ADR 008]: 008-split-bytestring-and-date-into-siblings.md
[`ByteString`]: ../../src/filters/string.py
[`Date`]: ../../src/filters/simple.py
[`Datetime`]: ../../src/filters/simple.py
[the plan]: https://github.com/todofixthis/filters/pull/116
[`Unicode`]: ../../src/filters/string.py
