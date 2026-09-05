---
status: Archived
date: 2026-08-29
archived-because: phx:writing-adrs is read before any new ADR is drafted (AGENTS.md requires it), met while the work is still being planned, defending the scope-not-tags convention this ADR adopts.
scope: [docs/adr/, scripts/adr/generate_index.py, .autohooks/adr_index.py, .github/workflows/build.yml]
summary: Replace ADR frontmatter's tags field with scope — the exact paths and directory prefixes a decision binds — validated by the index generator.
---

# 002: Scope ADR Frontmatter by the Paths a Decision Binds

## Context

ADR 001 carries a `tags` field: free-text keywords such as `pytest`, `testing`,
`fixtures`. `tags` helps a reader who already suspects a decision exists search for
it, but gives no way to go the other direction — from a file someone is editing back
to the decisions governing it — since keywords don't name locations.

[`phx:writing-adrs`][], this project's ADR skill (see `AGENTS.md`), now specifies a
`scope` field instead: the exact files and directory prefixes where a breach of the
decision would be authored. It also specifies frontmatter rules `scripts/adr/generate_index.py`
did not yet enforce: `Archived` and `Superseded` each require a field naming why
(`archived-because`, `superseded-by`), and a `revisit-when` trigger can be marked
spent via `revisit-discharged-by`.

`todofixthis/class-registry` carried out this same migration first; its
`scripts/adr/generate_index.py` (and the reasoning in its own now-archived migration
ADR) is the template this ADR ports.

## Options

### Option 1: Do nothing — keep `tags`

Leave the existing ADR and the generator as they are.

**Pros:** No migration effort.
**Cons:** Diverges from `phx:writing-adrs`; keyword search is the only way to find a
decision, so a directory rename or file move can silently orphan an ADR's frontmatter.
**Risks:** The gap between skill and repo widens with every ADR added under the old
convention.

### Option 2: Rename `tags` to `scope`, without path or status validation

Migrate the field name and its values to paths, but skip the generator checks that a
scope entry still exists on disk, that `Archived`/`Superseded` carry their required
field, and that a `revisit-discharged-by` names a live `revisit-when`.

**Pros:** Smaller diff to the generator than Option 3.
**Cons:** An unchecked `scope` rots the same way `tags` did; a status changed without
its paired field passes silently.
**Risks:** The field reads as validated, because the sibling fields are, and that
impression is false.

### Option 3: Rename `tags` to `scope`, with full validation (Accepted)

Migrate the field and port the validation `class-registry` already ported from the
`phx:writing-adrs` canonical generator: `scope` is required (or explicitly `[]`), its
entries must resolve to real paths (no globs, directories need a trailing `/`),
`Archived`/`Superseded` require their paired field and no other status may carry it,
and `revisit-discharged-by` requires a `revisit-when` to spend. Add the `--for` lookup
mode and a CI job that fails on a stale index.

**Pros:** Matches `phx:writing-adrs` exactly; a stale scope entry or an orphaned
status field fails the pre-commit hook and CI alike, instead of rotting unnoticed;
`--for` answers "what governs this file?" for an agent who never thought to check
`INDEX.md`.
**Cons:** Larger change to `scripts/adr/generate_index.py` than Option 2.
**Risks:** An authored `scope` is a judgement call, not a lookup — too narrow leaves
the decision unreachable from files it governs; too wide, and it stops meaning
anything.

## Decision

Option 3. `phx:writing-adrs` is this project's standing convention for ADR
frontmatter (`AGENTS.md`), so Option 1 leaves the project non-compliant with its own
tooling, and Option 2 keeps exactly the silent-drift problem the skill's validation
exists to catch.

`scripts/adr/generate_index.py` keeps parsing frontmatter with PyYAML (already a dev
dependency here) rather than the canonical script's hand-rolled, stdlib-only line
parser — that parser exists because the skill's own repository has no Python project
root and cannot take a PyYAML dependency, a constraint that doesn't apply here.

`scope` for ADR 001 was authored by reading what it actually binds: `pyproject.toml`,
where the `pytest11` entry point registers the plugin, and `src/filters/pytest.py`,
the plugin implementation itself.

## Consequences

- A new ADR must declare `scope` (or `scope: []`); the pre-commit hook and a CI job
  that regenerates `INDEX.md` and diffs it against the committed copy now reject one
  that still uses `tags`, is missing `scope`, or pairs a status with the wrong field.
- `uv run python -m scripts.adr.generate_index --for <path>` reports which ADRs bind
  a given file.
- `docs/adr/INDEX.md` gains a Scope column and drops Tags; a Revisit column surfaces
  any live `revisit-when` trigger.
- Archiving removes this ADR from `INDEX.md`, but `archived-because` only defends the
  scope-not-tags convention. The CI-enforcement decision (over the rejected
  unvalidated-rename option) and the PyYAML-over-stdlib-parser choice have no
  comparable defence and could regress unnoticed; accepted, since neither is a
  decision someone reverts by accident.

[`phx:writing-adrs`]: https://github.com/todofixthis/phx-claude-siat/blob/develop/skills/writing-adrs/SKILL.md
