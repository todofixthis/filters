---
status: Accepted
date: 2026-10-02
scope: [src/filters/, test/]
summary: Keep BaseFilter.__copy__ a shallow __dict__ copy and require a new filter, or one whose __init__ changes, that owns a mutable container to override __copy__ to copy it, rather than deep-copying or having the base class copy every container.
revisit-when: A bug report or review shows a filter shipped after this ADR without an override it needed, so the convention does not hold without enforcement.
---

# 013: Copy a Filter's Own Mutable Containers in __copy__

## Context

[`BaseFilter.__copy__`][] builds the copy with `object.__new__` and copies the instance `__dict__`, so a filter whose constructor takes arguments can be copied ([#118][], [#133][]). The copy shares every mutable container the original holds, so changing a copy's configuration changes the original's.

Three filters already copy a container, so the convention exists but is unwritten: `FilterChain` copies its list of child filters, [`FilterRepeater`][] copies its `restrict_keys` set, and `FilterMapper` copies its `_filters` dict and its `allow_missing_keys` and `allow_extra_keys` sets. Other filters share theirs: `Omit` (`keys`), `Pick` (`keys`, `allow_missing_keys`), `Split` (`keys`), `FilterSwitch` (`cases`), `Choice` (`choice_map`), `Call` (`extra_kwargs`) and `Type` (`aliases`, which `Array` passes through). Nothing tells an author adding a filter which containers need copying, and the first filter to do so becomes the template for the rest.

## Options

### Option 1: Do nothing

**Pros:** No per-filter code; `__copy__` stays the one base-class method.
**Cons:** The existing overrides stay a habit rather than a rule, so new and existing filters keep leaking configuration between copies until someone mutates a copy.

### Option 2: Copy each filter's own containers in `__copy__` (Accepted)

**Cons:** The base class does not enforce it, so a missed override passes silently.

### Option 3: Have `BaseFilter.__copy__` copy containers itself

The base class copies every `list`, `dict` and `set` in `__dict__`, optionally with a per-class opt-out listing attributes to share.

**Pros:** Closes the gap for every filter, existing and future, with no override to remember. No filter in the library is known to share a container on purpose, so nothing is known to break.
**Cons:** Copy behaviour becomes implicit and depends on attribute types, so a later attribute change alters it with no edit to `__copy__`. An opt-out list only moves the per-filter burden to the filters that share.
**Risks:** A filter that stores a large or deliberately shared container pays for a copy it does not want.

## Decision

Keep `BaseFilter.__copy__` a plain `__dict__` copy, and have each filter that stores a mutable container in `__init__` override `__copy__` to copy it, leaving child filters shared. A container is the filter's own when `__init__` creates or stores it, including one the caller passed in; whether `__init__` should copy a caller's object is a separate question this ADR does not settle. The copy goes one level deep, so the container is new but what it holds is not. A filter that shares a container on purpose leaves it uncopied and says why in a comment. Each filter with an override gets a copy test asserting that mutating the copy leaves the original unchanged.

The rule binds new filters, and existing filters when their `__init__` changes. Retrofitting the rest is a separate change per filter, so this ADR stays small.

Option 3 may well be the better design, since it removes the failure mode instead of documenting it. It loses on a judgement about the future, that implicit behaviour will cost more than the overrides do, rather than on anything in the library today. The revisit trigger is where that judgement gets checked.

## Consequences

- Filters that share containers today (`Omit`, `Pick`, `Split`, `FilterSwitch`, `Choice`, `Call`, `Type`) do not conform until each is retrofitted.
- Child filters stay shared across copies, along with everything reachable only through them: a copied repeater shares its chain's own container, and a copied `NamedTuple` shares its `FilterMapper`. Shared children also share runtime state, since their `_has_errors`, `_key` and `_parent` are common to all copies and re-pointed at whichever copy is applying. Handlers and error key paths are unaffected when copies apply one after another, but two copies applied concurrently are not isolated.

[#118]: https://github.com/todofixthis/filters/issues/118
[#133]: https://github.com/todofixthis/filters/pull/133
[`BaseFilter.__copy__`]: ../../src/filters/base.py
[`FilterRepeater`]: ../../src/filters/complex.py
