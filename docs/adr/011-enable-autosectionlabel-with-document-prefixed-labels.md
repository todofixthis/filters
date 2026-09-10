---
status: Accepted
date: 2026-09-10
scope: [docs/]
summary: Enable sphinx.ext.autosectionlabel with autosectionlabel_prefix_document = True, not its default unprefixed labels.
revisit-when: The section titles that currently collide with autosectionlabel's default unprefixed names (list in Context) are all renamed or removed, so prefixing no longer earns its verbosity.
---

# 011: Enable autosectionlabel with Document-Prefixed Labels

## Context

The docs already cross-reference sections by `:ref:`, but only because
[`simple_filters.rst`][], [`complex_filters.rst`][], [`getting_started.rst`][]
and [`upgrading_to_v4.rst`][] hand-place a `.. _label:` anchor above every
section a reader might want to link to — thirty-odd of them, per
[`010`][]'s own count of the docs' cross-reference load.
[`autosectionlabel`][] removes that step: it registers a label for every
section automatically, from the section's own title, so a new section needs
no anchor to become linkable.

Whether that label is the bare title or the title prefixed with the
document's name is a real choice, not a formality. Built with the bare
(default) form, the docs produce eleven `duplicate label` warnings —
measured, not assumed:

- `extensions`, [`index.rst`][]'s "Extensions" subsection against
  [`api.rst`][]'s "Extensions" heading.
- `filterception`, [`complex_filters.rst`][]'s own "Filterception" heading
  against its own hand-placed `.. _filterception:` anchor.
- `array`, `date`, `item`, `len`, `length`, `regex`, `required`, `round` and
  `unicode` — nine of [`simple_filters.rst`][]'s hand-placed anchors, each
  colliding with `autosectionlabel`'s own generated label for the section
  the anchor already sits above. All nine are single-word headings
  (`Array`, `Date`, `Unicode`, …); `autosectionlabel` lowercases a title but
  does not otherwise reshape it, so a single word matches its own anchor
  exactly, where a multi-word heading like `ByteString` does not collide
  with its `byte-string` anchor.

`.readthedocs.yaml` sets `fail_on_warning: true`, and `CLAUDE.md` states the
same policy for this project, so any one of these eleven warnings breaks
the published build.

## Options

### Option 1: Do nothing

**Pros:** No risk of introducing the warnings above.
**Cons:** Every section a future page wants to cross-reference still needs
its own hand-placed anchor, the way all thirty-odd existing ones do —
`autosectionlabel` exists precisely to remove that step.

### Option 2: Enable with default (unprefixed) labels

**Pros:** A label is just the section title, so an author who already knows
the heading can guess the `:ref:` target without checking.
**Cons:** Verified by building the docs with the extension enabled — this
breaks the build immediately on the eleven collisions described in
Context.
**Risks:** A future single-word heading collides with its own hand-placed
anchor the same way the nine in [`simple_filters.rst`][] already do, with
no warning until someone builds the docs.

### Option 3: Enable with `autosectionlabel_prefix_document = True` (Accepted)

**Pros:** Verified by building the docs with this setting — it resolves all
eleven collisions, since every `autosectionlabel`-generated label becomes
`<docname>:<Title>` (e.g. `simple_filters:Unicode`), which cannot match a
bare hand-placed anchor like `unicode`. None of the existing anchors or the
`:ref:` calls that cite them change, since prefixing only applies to labels
`autosectionlabel` generates.
**Cons:** A `:ref:` target for a section that has no hand-placed anchor now
needs the document name as well as the title, which is more to type and to
get right than a bare title. It also couples that target to the source
file's name, unlike a hand-placed anchor — renaming or splitting a `.rst`
file (`simple_filters.rst` is 1900-odd lines, a plausible future split)
invalidates every prefixed label pointing into it, caught by the same `-W`
build check rather than silently, but still a cost a hand-placed anchor
doesn't carry.
**Risks:** Prefixing disambiguates *across* documents, not within one, so a
future document repeating one of its own headings verbatim — the way
`complex_filters.rst`'s "Filterception" collides with its own anchor above
— still breaks the build; this needs the same before-and-after build check
as any docs change, not a one-off fix.

## Decision

Option 3. Prefixing is what keeps every hand-placed anchor working —
including the nine single-word ones already load-bearing throughout
[`simple_filters.rst`][] — while still letting `autosectionlabel` label
every other section for free. Option 2's bare labels collide with exactly
the anchors this project already relies on for its densest cross-reference
page.

## Consequences

- `docs/conf.py` gains `sphinx.ext.autosectionlabel` and
  `autosectionlabel_prefix_document = True`.
- A section with no hand-placed anchor is now reachable via
  `` :ref:`\<docname\>:\<Section Title\>` `` — e.g.
  `` :ref:`writing_filters:Macros` `` — while every existing bare `:ref:`
  target (`unicode`, `filter-mapper`, `upgrade-v4-siblings`, …) keeps
  resolving to its hand-placed anchor exactly as before.
- Two sections sharing an identical title *within the same document* still
  produce a `duplicate label` warning — prefixing does not reach that case,
  as `complex_filters.rst`'s "Filterception" heading and its own
  `.. _filterception:` anchor illustrate. A future docs change must still
  build clean before it ships, the same check this ADR ran to find the
  eleven collisions above.
- The docs now have two ways to make a section linkable. A hand-placed
  anchor stays the better choice for anything cited more than once, or
  cited from another project, since it's shorter and survives the file
  being renamed; the auto-generated `<docname>:<Title>` label is there for
  everything else, so a new section needs no anchor just to be reachable.

[`010`]: 010-document-the-package-to-resolve-cross-references.md
[`api.rst`]: ../api.rst
[`autosectionlabel`]: https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html
[`complex_filters.rst`]: ../complex_filters.rst
[`getting_started.rst`]: ../getting_started.rst
[`index.rst`]: ../index.rst
[`simple_filters.rst`]: ../simple_filters.rst
[`upgrading_to_v4.rst`]: ../upgrading_to_v4.rst
