---
status: Accepted
date: 2026-11-25
scope: [.agents/rules/project.md, .agents/rules/template-owned.md, .copier-answers.yml, .github/workflows/, AGENTS.md, pyproject.toml, src/filters/, test/]
summary: Filters follows the copier template todofixthis/cookiecutter-py, which writes and owns the files .agents/rules/template-owned.md lists, and defers to its decisions in them; cookiecutter-py ADR 019 replaces ADR 014 (ADR tooling), its ADRs 006 and 020 replace the archived ADRs 011 and 012 (prefixed autosectionlabel, strict docs builds in the hook and CI), and this ADR restates ADR 016 with mypy strict over src and all of test through the template's hook and type-check job at the template's major-range pin, pyright strict over src/filters and test/typing as a pyright job in .github/workflows/project.yml at a patch-level pin, and a mypy override for regex alone rather than a global ignore_missing_imports; diverging from a template decision on purpose needs an ADR here naming the cookiecutter-py ADR it departs from.
revisit-when: Filters stops taking template updates; the template supersedes or renumbers one of the ADRs named here; ADRs here are routinely authored in a harness other than Claude Code; filters stops returning None to reject a value (#121), so return-value, no-any-return and reportReturnType can be re-enabled; a consumer reports Any or Unknown from this package's annotations although both checkers pass in strict mode; src holds more than 30 pyright suppressions; another generated project with a consumer-facing generic API wants pyright, so it becomes a template question.
---

# 017: Defer to cookiecutter-py's Template Decisions

## Context

Filters now takes its tooling from [cookiecutter-py's copier template][] at
release 1.6.0, recorded in `.copier-answers.yml`; each later release arrives
as a Renovate PR running `copier update` ([cookiecutter-py ADR 015][]). The
files copier writes are template-owned: [`.agents/rules/template-owned.md`][]
lists them and says how to change one.

Four of filters' ADRs decide what the template now decides, or bind files it
now writes:

- [ADR 014][] relies on the phx plugin for ADR tooling, never a repo-local
  generator, pre-commit hook or vendored copy. [cookiecutter-py ADR 019][]
  decides the same, and the template pins `phx-adr` at 9.1.0 where filters
  pinned 8.1.0.
- [ADR 011][] (document-prefixed `autosectionlabel`) and [ADR 012][] (a
  strict, full-reread docs build in the pre-commit hook) are archived on
  comments in `docs/conf.py`, `.autohooks/docs_build.py`, `pyproject.toml`
  and `.readthedocs.yaml`. The template rewrites all four, citing
  [cookiecutter-py ADR 006][] and [ADR 020][cookiecutter-py ADR 020], which
  decide the same; 020 adds `-W` to the CI docs job and drops
  `--keep-going`.
- [ADR 016][] runs mypy and pyright strict on `src` and `test/typing`,
  pinned below each checker's next minor release, with mypy's
  `ignore_missing_imports` because `regex` ships no type information. The
  template runs strict mypy on `src` and all of `test`, in its pre-commit
  hook and `type-check` job, pins mypy to a major range, and has no
  pyright. todofixthis/filters#176 typed the rest of `test/` for this, and
  todofixthis/filters#179 met the template's ruff 0.17 rules.

## Options

### Option 1: Do nothing

Keep ADRs 011, 012, 014 and 016 beside the template's files.

**Cons:** Four records of decisions the template now owns. ADRs 011 and 012
are archived on comments the template has replaced, so nothing defends
them. ADR 016's checker scope and pins contradict the configuration the
template writes.

### Option 2: Defer to the template, restating ADR 016's own parts (Accepted)

Supersede ADRs 011, 012, 014 and 016. Restate here what ADR 016 decided
that is filters' own: pyright, its strict mode and suppression rules, and
the three disabled return codes.

**Cons:** A reader follows a link to another repository for the reasoning,
and the revisit triggers of the template's ADRs sit in its index. This ADR
names template ADRs by number, which goes stale if the template supersedes
or renumbers one; the links pin the 1.6.0 tag. mypy, at the template's
`>=2,<3`, can take a minor release with new diagnostics in a weekly lock
refresh, where ADR 016 held it below the next minor.

### Option 3: Option 2, but keep mypy pinned below the next minor

**Cons:** The pin sits in the template-owned dependency groups, so every
template update touching them conflicts. The template's weekly lock refresh
already stops a mypy minor with new diagnostics, since its PR fails `gate`
and isn't merged until fixed.

## Decision

Option 2. The template owns these files, so it owns the decisions about
them, and a second copy here can only fall behind. Option 3's pin buys
little over the lock refresh failing visibly.

Pyright stays filters' own, in a `pyright` job in
`.github/workflows/project.yml` that `gate` requires, rather than in the
template: most users' editors run pyright, which reads some of filters'
generics differently from mypy, as ADR 004 recorded, and a library whose
types are its interface needs both readings checked. No other generated
project has that need yet, so adding pyright to every project would charge
all of them for a benefit only filters has. pyright keeps ADR 016's
patch-level pin: it ships every release as 1.1.x, so `uv.lock` is what
holds its version.

What ADR 016 decided otherwise stands, restated here:

- Both checkers in strict mode, with mypy's `return-value` and
  `no-any-return` and pyright's `reportReturnType` disabled until #121
  makes rejection raise. A new error is fixed where the fix is honest, and
  otherwise suppressed on the reported line with a comment saying why;
  never by disabling a code, and never by annotating `Any` where a narrower
  type is true.
- The `test/typing/` `assert_type` harness, checked by both.
- `reportUnnecessaryTypeIgnoreComment`, and mypy's `warn_unused_ignores`
  through `strict`, so a suppression that stops being needed fails the
  build; `enableTypeIgnoreComments = false` keeps each checker reading only
  its own suppressions.
- `typing_extensions` as a runtime dependency, for PEP 696 `TypeVar`
  defaults on Python 3.12.

mypy's `ignore_missing_imports` narrows to an override for `regex`: a global
setting would also hide a missing stub for any dependency added later.
typeshed's `types-regex` is not the fix, since it types `Regex` and
`Split`'s `pattern` against `re.Pattern` alone, rejecting the
`regex.Pattern` they accept at runtime.

## Consequences

- `.agents/rules/template-owned.md` decides whether a change to a
  template-owned file is made here or proposed to cookiecutter-py; that
  rule, not this ADR's `scope`, lists the files. Filters' own content in
  them is listed in `.agents/rules/project.md`.
- Diverging from a template decision on purpose needs its own ADR here,
  naming the template ADR it departs from.
- The pre-commit hook runs mypy over every staged Python file, `test/`
  included, and still not pyright; `project.md` gives the pyright command.
- The `develop` and `main` rulesets must require the template's `gate`
  job. Filters' CI had no `gate`, so a ruleset requiring checks named them
  one by one; `typecheck`, which the template renames `type-check`, would
  then never report and block every PR. Make the switch before or with this
  adoption's merge.
- `Regex` and `Split`'s `pattern` annotation omits `regex.Pattern`, which
  they accept; typing it fully is a public-typing change for its own PR.

[ADR 011]: 011-enable-autosectionlabel-with-document-prefixed-labels.md
[ADR 012]: 012-check-the-docs-build-in-the-pre-commit-hook.md
[ADR 014]: 014-rely-on-the-phx-plugin-for-adr-tooling.md
[ADR 016]: 016-run-the-type-checkers-in-strict-mode.md
[`.agents/rules/template-owned.md`]: ../../.agents/rules/template-owned.md
[cookiecutter-py ADR 006]: https://github.com/todofixthis/cookiecutter-py/blob/1.6.0/docs/adr/006-enable-autosectionlabel-with-document-prefixed-labels.md
[cookiecutter-py ADR 015]: https://github.com/todofixthis/cookiecutter-py/blob/1.6.0/docs/adr/015-propagate-template-changes-with-copier-and-rotate-python-from-agent-sessions.md
[cookiecutter-py ADR 019]: https://github.com/todofixthis/cookiecutter-py/blob/1.6.0/docs/adr/019-rely-on-the-phx-plugin-for-adr-tooling.md
[cookiecutter-py ADR 020]: https://github.com/todofixthis/cookiecutter-py/blob/1.6.0/docs/adr/020-fail-generated-docs-builds-on-sphinx-warnings-in-ci-and-before-commit.md
[cookiecutter-py's copier template]: https://github.com/todofixthis/cookiecutter-py
