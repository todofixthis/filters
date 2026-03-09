---
name: writing-adrs
description: Use when making significant architectural, tooling, or design decisions that would benefit from documented rationale — before implementing the decision
---

# Writing Architecture Decision Records

ADRs record _why_ things are the way they are, so future contributors don't relitigate settled decisions. Use one when choosing between libraries, patterns, or conventions, or any time "why didn't we just use X?" is a likely future question.

## Format

File: `docs/adr/NNN-<slug>.md` (zero-padded, kebab-case)

```markdown
# NNN: Title (Imperative Mood)

**Status:** Accepted | Superseded by [NNN] | Deprecated
**Date:** YYYY-MM-DD

## Context

Why is this a problem? Why now? What forces are at play?

## Options

### Option 1: Do nothing

_Establishes the stakes — what happens if we decide nothing._

**Pros:** ...
**Cons:** ...
**Risks:** ...

### Option 2: [Chosen option] (Accepted)

**Pros:** ...
**Cons:** ...
**Risks:** ...

### Option 3: [Rejected alternative]

**Pros:** ...
**Cons:** ...
**Risks:** ...

## Decision

State the decision and summarise the key reasons.

## Consequences

What follows — positive and negative.
```

## Conventions

- **Option 1 is always "Do nothing"** — sets the stakes
- **Option 2 is always the accepted option**
- **Options must be mutually exclusive** — each must represent a fundamentally different approach. Test: could any two options be combined without contradiction? If yes, they aren't mutually exclusive. Two failure modes:
  - _Implementation details as options_ — if two options share the same core approach but differ in implementation, the variant belongs as a sub-heading within the parent option, not a top-level option
  - _Multi-dimensional problems_ — if what looks like a list of options is actually two separate decisions, structure around the primary; handle the secondary as a sub-question in the Decision section or write a follow-up ADR
- **Number sequentially** — never reuse or renumber
- **Supersede, don't edit** — new ADR for changed decisions; mark the old one superseded
- **Keep it concise** — enough to reconstruct the reasoning, not a thesis
