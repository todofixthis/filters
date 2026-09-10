---
status: Accepted
date: 2026-09-05
scope: [docs/, src/filters/]
summary: Document the `filters` package itself in `api.rst`, so autodoc registers objects under the public path the prose cites, rather than citing submodule paths or resolving them with a `conf.py` hook.
revisit-when: A name worth documenting stops being re-exported from `filters/__init__.py`, which would drop it from the API page; or an unqualified cross-reference such as `` :py:class:`NotEmpty` `` needs to resolve, which registering the public path does not fix.
---

# 010: Document the Package to Resolve Cross-References

## Context

The prose cites filters by the name callers import: `` :py:class:`filters.Unicode` ``.
[`api.rst`][] documented each submodule, so autodoc registered that class as
`filters.string.Unicode`, and the two never met. Sphinx does not error on an
unresolved Python cross-reference unless `nitpicky` is set, which this project
does not set, so the role rendered as plain text and the build stayed green.

Measured across the built HTML, excluding the module index, which carries
generated rows rather than prose: 47 of 82 cross-references resolved to
nothing. Each one rendered fully qualified and unclickable, so the output
announced the failure no more than the build did. The proportion is what makes
this structural rather than a scatter of typos — the prose cites the public
name because that is the name a reader types, and the public name was the one
path autodoc never registered.

Docstrings under `src/filters/` carry these roles too, and autodoc pulls them
into the API page, so the citation style is decided in both trees.

## Options

Options 2, 3 and 4 all resolve the same 38 references, so none is
distinguished by how many it fixes.

### Option 1: Do nothing

**Pros:** Nothing to maintain, and no risk of a citation resolving to the
wrong object.
**Cons:** Leaves 47 dead cross-references, and every future one joins them.
The reference-heavy pages are worst hit — the v4 upgrade guide, where a reader
most needs to reach `ByteString` and `Datetime`, had 15 of its 32 dead.
**Risks:** The failure is invisible from both sides: the build reports
nothing, and the page renders text that reads as deliberate.

### Option 2: Document the package (Accepted)

`api.rst` documents `filters` itself, plus `filters.extensions` and
`filters.test` — the two modules the package does not re-export. Autodoc then
registers `filters.Unicode`, the path the prose already cites.

**Pros:** No configuration and no custom code. The public path is where the
object is registered rather than an alias resolved after the fact, so a class
moving between submodules changes nothing. Builds clean under `-W`.
**Cons:** Drops the `T_out` type variable, the one documented name that is
neither re-exported nor in the two extra modules.
**Risks:** A name dropped from [`filters/__init__.py`][]'s re-exports silently
leaves the API page, taking any citation of it down as well.

### Option 3: Cite the submodule path in the prose

Write `` :py:class:`~filters.string.Unicode` `` throughout, with `~` so the
rendered text stays short.

**Pros:** Each citation names exactly what it points at, by the mechanism
Sphinx already has.
**Cons:** Couples every citation to the module layout, so moving a class
between submodules breaks each one — silently, the build being green either
way. It also asks the prose to name a path callers never type.
**Risks:** The coupling stays invisible until a refactor, which is precisely
when nobody is reading the docs.

### Option 4: A `missing-reference` hook in `conf.py`

Handle Sphinx's `missing-reference` event: where an unresolved target begins
`filters.`, search the Python domain for an object whose path ends in the same
name and resolve to it.

**Pros:** No `.rst` file changes, and the citation survives a class moving
between submodules.
**Cons:** Thirty-odd lines of custom Sphinx code and a `setup()` in `conf.py`,
for an outcome Option 2 reaches with none. Resolution is implicit — nothing in
the prose says `filters.Unicode` is not the registered path.
**Risks:** Resolution is by first match on the trailing name, in `api.rst`
directive order. No two submodules export the same leaf name today, so nothing
is ambiguous; if two ever did, the hook would silently pick one, and
reordering `api.rst` would change which.

## Decision

Option 2. Measured against the same tree, Options 2 and 4 leave an identical
nine references dead, so the hook buys nothing Option 2 does not give free —
and it charges custom code, an implicit resolution step, and a latent
first-match ambiguity for it. Registering the public path is also the more
honest description of the situation: `filters.Unicode` is what the package
exports, so it is what the inventory should say, rather than a name patched in
after resolution has already failed.

Option 3 buys the same correctness by making every citation a hostage to the
module layout, which is the coupling Option 2 removes.

Losing `T_out` is accepted rather than worked around. No page cites it, and
adding `filters.base` back to reach it would re-register every class under its
submodule path as well, restoring the ambiguity Option 2 exists to remove.

`nitpicky` stays off. Turning it on would make these fail loudly, which is the
right instinct, but it reports every unresolved reference — including the
third-party types in [`extension_filters.rst`][] that have no inventory to
resolve against — and [`.readthedocs.yaml`][] sets `fail_on_warning: true`, so
switching it on without first supplying or suppressing those inventories
breaks the published build. That is its own decision, and this one does not
take it.

## Consequences

- Nine cross-references still resolve to nothing, and the build stays silent
  about them. Three name third-party types with no intersphinx inventory
  (`iso3166.Country`, `moneyed.Currency`, `language_tags.Tag.Tag`); three name
  members autodoc does not emit (`_invalid_value`, `FilterMeta.__or__`,
  `filters.ext`); and three are cited without the `filters.` prefix that would
  reach them — `` :py:meth:`apply` `` twice in [`complex.py`][] and
  `` :py:class:`NotEmpty` `` in [`simple_filters.rst`][]. That last group is
  the one this decision does not address, and the one a future author is
  likeliest to add to, the unqualified form being the natural way to write it.
  Counting them means parsing the built HTML, as this ADR did; nothing reports
  them.
- `typing.Any` and `typing.Optional` resolve only through `:py:obj:`, CPython's
  inventory registering both as `py:data`. `typing.Union` is a `py:class`
  there, so the rule is not uniform across `typing` and cannot be generalised
  from those two.
- The API page now lists every re-exported name in one sequence rather than
  grouped by defining module. The previous grouping was invisible in the
  rendered page — the old `api.rst` carried no headings, only anchors — so
  what a reader loses is member order, not structure. The new file adds two
  headings of its own, `Extensions` and `Test Helpers`, so the page gains two
  visible sections where it had none. The module index shrinks with it, from
  nine rows to three.
- A citation written in a `src/filters/` docstring is subject to this decision
  the same as one in `docs/`, autodoc pulling both into the same page.

[`.readthedocs.yaml`]: ../../.readthedocs.yaml
[`api.rst`]: ../api.rst
[`complex.py`]: ../../src/filters/complex.py
[`extension_filters.rst`]: ../extension_filters.rst
[`filters/__init__.py`]: ../../src/filters/__init__.py
[`simple_filters.rst`]: ../simple_filters.rst
