---
status: Accepted
date: 2026-11-26
scope: [src/filters/]
summary: A filter instance holds configuration only; BaseFilter keeps each run's parent, key, error flag and injected handler in a per-apply frame held in a ContextVar, rather than on the instance or by copying child filters when chains combine, so parent and key are read-only, resolve_filter takes no parent or key, a filter applies a child with self._filter() rather than child.apply() to keep it in the run, and FilterRunner injects its handler with apply_with_handler.
revisit-when: A filter needs its run state in a thread or task that cannot run in a copy of the run's context; or a consumer's profile shows the per-apply frame as a bottleneck that optimising the frame cannot remove.
---

# 019: Keep Per-Run State off Filter Instances

## Context

A filter instance is shared more often than its author sees. `|` copies a chain's list but not the filters in it, and nesting a filter in a chain, a [`FilterMapper`][] or a `FilterRepeater` stores the instance itself ([ADR 013][] keeps child filters shared across copies on purpose). A module-level chain run by two [`FilterRunner`][]s shares everything.

[`BaseFilter`][] also kept the state of a run on the instance. `_filter` assigned `parent` and `key` to a child each time it applied it, `handler` and `key` walked `parent` to find where an error goes and what it is filed under, `apply` reset `_has_errors`, and `FilterRunner` set the top filter's `handler` for its run and restored it afterwards.

[#175][] sets out what follows from the two together:

- Two threads that run filters sharing an instance can swap errors. One run accepts an invalid value because its error lands in the other run's handler, and the other run rejects a valid value.
- `FilterRunner` saved the handler through the `handler` getter and restored it to `_handler`, so a single run on one thread left the filter with an `ExceptionHandler` set where it had none, and overlapping runners could leave it holding a finished run's handler for good.
- `key` went stale on one thread. Constructing a `FilterMapper` around a filter filed that filter's errors under the mapper's key wherever else the filter ran.

Synchronous validation on a thread pool is what most web frameworks do, so this is the ordinary case. phx-filters-pydantic works around part of it with a lock per field ([its ADR 005][]), which cannot cover an instance that two fields share.

A fix can break a custom filter, so it belongs in 4.0.0, which is still in alpha.

## Options

### Option 1: Do nothing

Document that a filter instance must stay on one thread at a time.

**Pros:** No change to any filter or to custom filters.
**Cons:** The stale key and the handler a runner leaves behind are wrong on one thread, where no rule about threads helps. The rule itself is hard to follow, because `|` and nesting share instances without saying so.
**Risks:** An invalid value accepted under load, in the deployments the library is used for, with every single-threaded test passing.

### Option 2: Keep per-run state in a frame per `apply()` call (Accepted)

Each `apply()` call gets a frame holding the filter, the frame of the filter that applied it, the sub-key it was applied under, its error flag and, for the call a run starts with, a handler injected for that run. The current frame lives in a `contextvars.ContextVar`. `_filter` creates the child's frame and `apply()` claims it. `parent`, `key`, `handler` and `_has_errors` become properties that read the filter's nearest frame in the run, and the instance keeps only `_handler`, the handler set with `set_handler`.

**Pros:** `_apply`, `_filter`, `_invalid_value` and `self._has_errors` keep their signatures and meaning, so the filters in this package, phx-filters-django, phx-filters-iso, phx-filters-pydantic and paddock run unchanged.
**Cons:** Each `apply()` allocates a frame and sets and resets the context variable. `parent` and `key` lose their setters, and `resolve_filter` loses its `parent` and `key` arguments, which breaks a custom filter that uses them.
**Risks:** A frame is found through the context, so a filter that applies a child from a thread it starts itself finds no frame there, unless the interpreter gives a new thread its parent's context. The child then reports to the filter's own handler, or raises in that thread where the filter has none, and the run that started the thread can accept an invalid value. Running the thread's work with `contextvars.copy_context().run` gives it the frame.

The frame could instead be an argument to `apply` and `_apply`. That needs no context variable, and it changes the signature of every `_apply` ever written, so it is not a separate option worth the break.

### Option 3: Copy child filters when chains combine or nest

`__or__`, `_add` and the `FilterMapper` and `FilterRepeater` constructors deep-copy what they are given.

**Pros:** No change to how a run finds its handler or key.
**Cons:** It leaves open one chain run by two runners, and an instance held by `FilterSwitch` cases, `NamedTuple`'s mapper, or a custom filter that stores a child in `__init__`. It copies state a filter means to share, such as a connection or a cache, and reverses ADR 013, which leaves child filters shared. It needs a `__deepcopy__` on every filter that copies downward only, because `copy.deepcopy` follows the `parent` reference into the enclosing chain.
**Risks:** The routes it leaves open fail the same silent way, with less to point a reader at them.

### Option 4: Serialise runs with a lock

`apply()` takes a lock for the top-level filter, or one lock for the package.

**Pros:** No change to where state lives.
**Cons:** A lock per top-level filter does not cover an instance two chains share, which is the limit phx-filters-pydantic's ADR 005 already reached. One lock for the package serialises all validation in the process. Neither fixes the stale key or the handler a runner leaves behind.
**Risks:** Lock ordering between filters that validate into each other.

## Decision

Keep per-run state in a frame per `apply()` call. It removes the cause, where copying and locking each close some routes and leave the rest to fail silently. It is also the only option that fixes the single-threaded faults without a second mechanism.

A `ContextVar` holds the current frame because it is per thread and per asyncio task with no work from the caller, and because it leaves `_apply`'s signature alone.

The rules that follow from it:

- A filter instance holds configuration. `BaseFilter` stores `_handler` on it and nothing else, and a filter must not write per-run state to `self` in `_apply`.
- A filter's run state is that of its nearest frame in the run, so it holds while a child the filter applied is running. The child can read `self.parent.key`, and a callback the child runs can report through the filter that passed it.
- `parent` and `key` are read-only. For a filter with no frame in the run they are `None` and `""`, and its `_has_errors` reads `False` and ignores assignment. A filter held by a chain has no parent until that chain applies it.
- `handler` is the nearest of: the handler set on the filter, the handler set on each filter applying it in turn, and the handler injected for the run. The injected handler replaces the one set on the run's first filter, as `FilterRunner` always did, and a nested filter's own handler still wins over it. For a filter with no frame it is the filter's own handler or a new `ExceptionHandler`, never a holder's.
- A filter applies a child with `_filter`. A child applied with `apply()` from inside `_apply` starts a run of its own, with no key and no handler but its own, because `unicodify_key` and code like it rely on `Unicode().apply()` raising there. A filter that calls its own `apply()`, to recurse into a nested value, is the exception: it has a frame in the run already and carries on under that frame's key and handler.
- `_filter` called by a filter with no frame, as `FilterRepeater.iter()` allows, gives that filter a frame for the call, under the frame of whichever filter is being applied. Its children find a handler set on it and the key of the run around it.
- `apply_with_handler(value, handler)` injects a handler for one call and is public, so a caller with its own runner has a route that does not write to the filter. `FilterRunner` uses it.
- `resolve_filter` takes no `parent` or `key`. Passing either raises `TypeError`, which is a louder failure than accepting and ignoring them.

## Consequences

- Every route #175 lists is closed, along with a plain `apply()`. `test/test_per_run_state.py` holds two runs inside a shared filter at once for `|` on either side, `FilterMapper`, `FilterRepeater`, `FilterSwitch`, `NamedTuple`, a custom filter that stores a child, and one chain or mapper under two runners. Every one of those cases fails against the code this ADR replaces.
- What stays the caller's to keep to one thread is state that was never the run's. A `FilterRunner` object caches its own result. A handler set with `set_handler` receives the errors of every run that reaches it, so a `MemoryHandler` set on a shared filter mixes them. Changing a filter's configuration while another thread applies it is a race. A custom filter that writes to `self` in `_apply` shares that write with every run.
- phx-filters-pydantic can drop its per-field lock and its warnings about shared filters, once it requires a phx-filters release that carries this change.
- Breaking, for custom filters:
  - Assigning `parent` or `key` raises `AttributeError`, and `resolve_filter(..., parent=..., key=...)` raises `TypeError`. In `__init__` the filter fails to construct. In `_apply` the exception is caught like any other, so every value fails with the code `exception`.
  - A child that a filter stored with `resolve_filter(child, parent=self)` and applies with `child.apply()` reported under the filter's key and handler. It now runs on its own. Apply it with `_filter`.
  - A filter applied directly reported to the handler of a chain that also held it, while that chain was alive. It now reports to its own handler.
  - `parent`, `key`, `handler` and `_has_errors` read outside a run no longer reflect the filters that hold the instance.
  - Calling another instance's `_apply` directly, in place of `apply()`, gives that instance no frame, so its `_has_errors` checks never trip.

  `docs/upgrading_to_v4.rst` covers each.
- A four-filter chain took about 9 microseconds to apply against about 6 before, and a mapper over a nested schema took about a quarter longer, measured with `timeit` on CPython 3.14 when this ADR was written.
- ADR 013's note that two copies applied at once are not isolated no longer holds for the state `BaseFilter` keeps. Its rule on copying containers is unchanged.
- `__copy__` copies `_handler` and the subclass's own attributes. There is no run state left for a copy to inherit.

[#175]: https://github.com/todofixthis/filters/issues/175
[ADR 013]: 013-copy-a-filters-own-mutable-containers-in-copy.md
[`BaseFilter`]: ../../src/filters/base.py
[`FilterMapper`]: ../../src/filters/complex.py
[`FilterRunner`]: ../../src/filters/handlers.py
[its ADR 005]: https://github.com/todofixthis/filters-pydantic/blob/main/docs/adr/005-serialise-shared-filter-chains.md
