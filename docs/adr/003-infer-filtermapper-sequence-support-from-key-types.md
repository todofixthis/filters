---
status: Accepted
date: 2026-08-30
scope: [src/filters/complex.py]
summary: FilterMapper accepts sequence input (returning a list) exactly when filter_map is non-empty and every key is a non-bool int; a FilterMapper with any other key keeps accepting Mapping input only.
revisit-when: A real use case needs FilterMapper's positional mode to accept a Sequence type other than list/tuple, or to accept str/bytes positionally, or to mix int and non-int keys in one positional FilterMapper.
---

# 003: Infer FilterMapper's Sequence Support from Filter-Map Key Types

## Context

`FilterMapper` validates a dict of named values against a `filter_map` of per-key
filters, but only accepts `Mapping` input ([#82][]). A common pipeline shape splits a
delimited string into a list (`f.Split(":")`) and then wants to validate each element
positionally — e.g. a path pair with an optional trailing mode flag. Nothing lets one
chain `Split` into per-position validation without a bespoke filter to turn the list
into a dict first.

`FilterRepeater` already solves an adjacent problem — applying one filter across every
item of an incoming iterable — by branching on `isinstance(value, Mapping)`: a dict is
walked by key, anything else by `enumerate()`, and the result comes back as
`mapping_result_type`/`sequence_result_type` (`dict`/`list`) to match. `FilterMapper`
needs the same input-shape flexibility, but with per-key filters rather than one filter
repeated, so the two classes can't share an implementation.

## Options

### Option 1: Do nothing

Callers who want positional validation on a list write a custom filter to convert it to
a dict before handing it to `FilterMapper`.

**Pros:** No change to a class every existing schema already depends on.
**Cons:** Leaves #82's exact use case unsupported; every caller re-solves the same
list-to-dict boilerplate.
**Risks:** None — this is the status quo.

### Option 2: Accept any Iterable, dispatch on the runtime value's type (Rejected)

Mirror `FilterRepeater` exactly: accept any `Iterable` regardless of `filter_map`'s key
types, walking a `Mapping` by key and anything else via `enumerate()`.

**Pros:** One `isinstance` check; no new state on the filter.
**Cons:** An existing string-keyed FilterMapper (e.g. `{"id": ..., "subject": ...}`)
handed a tuple by mistake — `test_filter_mapper_fail_non_mapping`'s exact scenario —
would silently switch to positional mode instead of failing with `CODE_WRONG_TYPE`:
string keys can never match a sequence index, so every value reports "missing" (or
"extra") instead of the caller learning their input has the wrong shape.
**Risks:** A caller relying on non-Mapping input raising one clear type error would
instead see a batch of confusing missing/extra-key errors.

### Option 3: Infer sequence support from `filter_map`'s key types (Accepted)

At `__init__`, note whether `filter_map` is non-empty and every key is an `int` (and not
a `bool` — `bool` is an `int` subclass, but `{True: ..., False: ...}` is never someone
declaring a positional filter). Only such a FilterMapper also accepts `list`/`tuple`
input, applying each filter by index and returning a `list`; a FilterMapper with any
other key, or no keys at all, keeps accepting `Mapping` only, exactly as today.

**Pros:** `test_filter_mapper_fail_non_mapping` and every other existing FilterMapper
keeps behaving identically, since their keys are never all non-bool `int`. #82's example
needs no extra constructor argument — an int-keyed `filter_map` already declares "this is
positional".
**Cons:** A FilterMapper's accepted input shape is implicit in its `filter_map`'s key
types rather than stated at the call site.
**Risks:** None distinct from the Cons above — a reader has to know the key-type rule
rather than see the mode in the constructor signature.

### Option 4: Require an explicit constructor flag (Rejected)

Add e.g. `FilterMapper(filter_map, sequence=True)` (or a separate
`FilterSequenceMapper` class) to opt in explicitly.

**Pros:** No implicit dispatch on key types; the signature states the mode directly.
**Cons:** #82's own acceptance example passes no such flag, so satisfying it would mean
deviating from the spec the issue gives; a separate class would duplicate most of
FilterMapper's logic for no behavioural gain over Option 3.
**Risks:** None beyond the added API surface.

## Decision

Option 3. It satisfies #82 exactly as specified — no flag, just an int-keyed
`filter_map` — while Option 2's blanket dispatch would quietly change what today's
string-keyed FilterMappers do with malformed input, and Option 4 contradicts the
issue's own example for no offsetting benefit.

`FilterMapper._apply` now checks `Type((Mapping, list, tuple))` when `filter_map` is
int-keyed, `Type(Mapping)` otherwise (unchanged). It checks concrete `list`/`tuple`
rather than `FilterRepeater`'s `Iterable`, or the broader `collections.abc.Sequence`:
per-position lookup needs random access and a length (`enumerate()`, `FilterRepeater`'s
mechanism, gives neither), and `Sequence` would admit `str`/`bytes` — technically
Sequences, but positional character/byte-level splitting is not a real use case here —
along with any other non-`list`/`tuple` Sequence, which nothing here has a proven need
to support.

The per-position logic mirrors the existing per-key logic: `allow_missing_keys`/
`allow_extra_keys` behave the same, "missing" means the index is out of range rather
than absent from `.keys()`, and extra positions (indices beyond `filter_map` with no
filter) surface in index order rather than sorted key order — already equivalent to the
mapping case, since indices sort the same way keys would.

## Consequences

- `FilterMapper` gains `mapping_result_type`/`sequence_result_type` (`dict`/`list`),
  matching `FilterRepeater`'s existing convention, to pick the return type from the
  input's runtime shape.
- `_invalid_value`/`_filter`'s `sub_key` must be a non-empty string:
  `BaseFilter.resolve_filter` skips assigning a falsy `key`, and `_make_key` joins key
  parts with `str.join`. An `int` key is never a `str`, and `0` is additionally falsy, so
  today's code mishandles any int-keyed `FilterMapper` in two distinct ways, both
  reproduced against the pre-#82 code: `FilterMapper({0: f.Required | f.Int})` applied
  to `{0: "not-an-int"}` reports the correct `not_numeric` code but an empty (lost) key
  in its error context; `FilterMapper({1: f.Required | f.Int})` applied to
  `{1: "not-an-int"}` raises `TypeError` inside `_make_key`'s `str.join`, caught by
  `_filter`'s exception handler and reported as a generic `exception` code instead of
  `not_numeric` — no nesting required. `FilterMapper` now routes every
  `sub_key`/`resolve_filter(key=...)` call through the existing `unicodify_key` helper
  so index keys render correctly regardless of int-ness or falsiness.

[#82]: https://github.com/todofixthis/filters/issues/82
