---
status: Accepted
date: 2026-11-25
scope: [.agents/rules/project.md, pyproject.toml, renovate.json, src/filters/string.py, test/typing/test_string.py]
summary: Type-check regex through typeshed's types-regex in the dev and ci groups, capped below 2026.11.19.20261122, rather than a mypy override that ignores its missing imports; Regex and Split accept a regex.Pattern and Strip stores optional patterns.
revisit-when: The pyright in uv.lock bundles _typeshed.FloatInt; filters needs a types-regex release above the cap.
---

# 018: Type regex with typeshed's stubs

## Context

[ADR 017][] narrowed mypy's `ignore_missing_imports` to an override for
`regex`, which ships no type information, and named the condition for
replacing it: "Regex and Split's pattern annotation accepts regex.Pattern, so
types-regex can replace the regex override". Under the override, mypy reads
every `regex` call as `Any`, so it checks nothing filters does with a
pattern; and a consumer who installs `types-regex` meets the errors filters'
own checks never see, such as `Regex(regex.compile(...))` failing to type.

The current `types-regex`, 2026.11.19.20261122, changes only one thing from
the release before it: it annotates `timeout` with `_typeshed.FloatInt`
rather than `float`. mypy 2.4's bundled typeshed has `FloatInt`; pyright's
does not, in any release from 1.1.411 to 1.1.414, the newest (all four bundle
the same typeshed commit, and 1.1.414 is 11 weeks old). pyright resolves it
as `Unknown`, and strict mode reports the seven calls in
`src/filters/string.py` whose signature takes `timeout`.

## Options

### Option 1: Do nothing

Keep the override.

**Cons:** `regex` stays unchecked in filters, while consumers with the stubs
see errors filters can't.

### Option 2: Adopt types-regex below the release that needs FloatInt (Accepted)

Add `types-regex>=2026,<2026.11.19.20261122` to the `dev` and `ci` groups,
drop the override, and fix the annotations the stubs expose.

**Cons:** the cap holds back every later `types-regex` release, including
stubs for newer `regex` runtimes, for as long as pyright's typeshed lags,
which on its recent cadence may be months. Nothing announces when pyright
catches up: the lock refresh brings the new pyright, and the build stays
green either way.

### Option 3: Adopt the newest types-regex and suppress pyright at each call

**Cons:** seven `# pyright: ignore[reportUnknownMemberType]` comments for a
gap between the stubs and the checker, not an error in filters, where ADRs
016 and 017 allow a suppression only where no honest fix exists. Their one
merit is an alarm: `reportUnnecessaryTypeIgnoreComment` fails the build once
pyright catches up.

## Decision

Option 2. The cap is one line in each group with its reason beside it, where
Option 3 spreads the workaround across the code it is meant to check. The
release it excludes adds nothing filters needs. Without Option 3's alarm, the
check is manual: Consequences says how to run it.

## Consequences

- `Regex` and `Split` take `pattern: str | re.Pattern[str] |
  regex.Pattern[str]`, and `Strip` declares `leading` and `trailing` as
  `regex.Pattern[str] | None`. `test/typing/test_string.py` checks both
  public types; against the old annotations both checkers fail the
  `pattern` cases and mypy fails the `Strip` ones.
- `.agents/rules/project.md` lists `types-regex` among filters' own content
  in the template-owned `pyproject.toml`, in place of the override.
- The stubs track `regex`'s newest release while `uv.lock` holds an older
  runtime, so mypy can accept a call the locked `regex` lacks. The cap
  widens that gap as the runtime moves on.
- Renovate's `pep621` manager raises an upper bound to admit a new release,
  so a package rule in `renovate.json` disables it for `types-regex`; the
  weekly lock refresh still moves the stubs within the cap.
- To check whether the cap can lift, remove it from both groups, run `uv lock
  --upgrade-package types-regex && uv sync --group dev` (plain `uv lock` keeps
  the capped release, so the check would pass regardless; leave pyright where
  the lock has it), then `uv run pyright src/filters test/typing`. Zero errors
  means the locked pyright bundles `FloatInt`: commit the change with the
  `renovate.json` rule removed and the cap's mentions in
  `.agents/rules/project.md` dropped; otherwise restore `pyproject.toml` and
  `uv.lock` and re-sync. `uv.lock` records only pyright's version, so nothing
  in it shows this.

[ADR 017]: 017-defer-to-cookiecutter-py-s-template-decisions.md
