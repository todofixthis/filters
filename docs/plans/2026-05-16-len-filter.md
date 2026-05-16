# `Len` Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Len` filter that unifies `Length`, `MinLength`, and `MaxLength` into one composable filter with exact, min-only, max-only, and range modes.

**Architecture:** `Len` is a single `BaseFilter` subclass in `src/filters/simple.py`. Configuration mode (exact vs min/max) is resolved in `__init__` with eager `ValueError` for invalid combos. `_apply` delegates to whichever bounds are active.

**Worktree:** `/Users/phx/Documents/filters/.claude/worktrees/feature+len-filter` (branch: `worktree-feature+len-filter`)

**Tech Stack:** Python, pytest, Sphinx/RST docs.

---

## File Map

| Action | Path |
|--------|------|
| Modify | `src/filters/simple.py` — add `Len` class (before `Length`) and `"Len"` to `__all__` (between `"Item"` and `"Length"`) |
| Modify | `src/filters/__init__.py` — add `"Len"` to `__all__` and `Len` to the `from .simple import …` block |
| Create | `test/test_len.py` |
| Modify | `docs/simple_filters.rst` — add `Len` section before `Length` (alphabetically `Len < Length`) |

---

## Task 1: Implement and export `Len` ✅

`Len` is implemented as a `BaseFilter` subclass in `src/filters/simple.py`, inserted alphabetically before `Length`. It supports four modes — exact (`Len(n)`), min-only (`Len(min=n)`), max-only (`Len(max=n)`), and range (`Len(min=m, max=n)`) — resolved in `__init__` with eager `ValueError` for invalid combos (mixed exact+range, negatives, `min > max`, no args). `__init__` parameters use `int | None` (not `typing.Optional`) to avoid shadowing the `Optional` filter class. The filter is exported from `src/filters/__init__.py` and accessible as `f.Len`. 35 tests in `test/test_len.py` cover all modes, collection types (`list`, `dict`, `Sized`), and every invalid-configuration guard; total suite grew from 441 to 476.

---

## Task 2: Documentation

**Files:**
- Modify: `docs/simple_filters.rst`

- [ ] **Step 1: Add `Len` section to `simple_filters.rst`**

The filters are documented in alphabetical order. `Len` sorts before `Length` (4th character: `\0` < `g`), so insert the `Len` section immediately before the `.. _length:` label (around line 614). Insert:

```rst
.. _len:

Len
---
A unified length-constraint filter that replaces :ref:`length`,
:ref:`min-length`, and :ref:`max-length`.

.. code-block:: python

   import filters as f

   # Exact length — equivalent to Length(3)
   runner = f.FilterRunner(f.Len(3), ['foo', 'bar', 'baz'])
   assert runner.is_valid() is True

   runner = f.FilterRunner(f.Len(3), ['foo', 'bar'])
   assert runner.is_valid() is False

   # Minimum length only — equivalent to MinLength(3)
   runner = f.FilterRunner(f.Len(min=3), 'Hello')
   assert runner.is_valid() is True

   # Maximum length only — equivalent to MaxLength(5)
   runner = f.FilterRunner(f.Len(max=5), 'Hi')
   assert runner.is_valid() is True

   # Length within a range — equivalent to MinLength(2) | MaxLength(5)
   runner = f.FilterRunner(f.Len(min=2, max=5), 'kia')
   assert runner.is_valid() is True

   runner = f.FilterRunner(f.Len(min=2, max=5), 'x')
   assert runner.is_valid() is False

The filter accepts any ``Sized`` value (strings, lists, dicts, bytes, etc.).

.. note::

   ``Len(n)`` requires *exactly* the specified length.
   ``Len(min=m, max=n)`` with ``m == n`` is equivalent to ``Len(m)``.

.. caution::

   You cannot mix the positional ``exact`` argument with ``min`` or ``max``
   keyword arguments — ``Len(4, min=2)`` raises ``ValueError`` at
   initialisation time.

   All length values must be ``>= 0``, and when using range mode,
   ``min`` must not exceed ``max``.

```

Also update the `.. note::` in the `Length` section (which will have shifted down a few lines after the `Len` insertion) to reference `Len`:

```rst
.. note::

   :py:class:`filters.Length` requires the incoming value to have *exactly*
   the specified length; if you want to check that the incoming value has a
   minimum or maximum length, use :ref:`min-length` or :ref:`max-length`,
   respectively — or use the unified :ref:`len` filter.
```

- [ ] **Step 2: Build docs and verify**

Run: `uv run make -C docs clean && uv run make -C docs html 2>&1 | tail -20`

Expected: `build succeeded` with zero warnings.

- [ ] **Step 3: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

- [ ] **Step 4: Compress this task in the plan**

Use the `compress-plan-task` skill.

---

## Task 3: GitHub deprecation issue

**Files:** none (GitHub only)

- [ ] **Step 1: Create the GitHub issue**

Run:

```bash
gh issue create \
  --title "Deprecate Length, MinLength, MaxLength in favour of Len" \
  --label "enhancement" \
  --body "$(cat <<'EOF'
## Context

PR #NNN introduced the unified `Len` filter as a drop-in replacement for
`Length`, `MinLength`, and `MaxLength`.

## Tasks for next major release

- [ ] Deprecate `Length` — emit `DeprecationWarning` and point users to `Len(n)`
- [ ] Deprecate `MinLength` — emit `DeprecationWarning` and point users to `Len(min=n)`
- [ ] Deprecate `MaxLength` — emit `DeprecationWarning` and point users to `Len(max=n)`
- [ ] Update docs to mark the three filters as deprecated
- [ ] Remove the three deprecated filters in the release after that

## Notes

- `MaxLength` has a `truncate` option that `Len` does not support — decide
  whether to add truncation to `Len` or keep `MaxLength` for that use case.
EOF
)"
```

Replace `#NNN` with the actual PR number before running.

- [ ] **Step 2: Note the issue number**

Copy the issue URL from the output and note the number for future reference.

- [ ] **Step 3: Compress this task in the plan**

Use the `compress-plan-task` skill.

---

## Self-Review Checklist

- [ ] Does every commit step remind the agent to run `git status` first?
- [ ] Does every task end with a compression step?
- [ ] Does the plan header include a `**Worktree:**` field? *(fill in at execution time)*
- [ ] Are all `Len(...)` configurations from the spec covered by tests?
  - `Len(4)` ✅ exact pass
  - `Len(min=4)` ✅ min-only pass/fail
  - `Len(max=4)` ✅ max-only pass/fail
  - `Len(min=2, max=4)` ✅ range pass/fail
  - `Len(4, min=2)` ✅ ValueError
  - `Len(4, max=4)` ✅ ValueError
  - `Len(4, min=2, max=4)` ✅ ValueError
  - `Len(0)` ✅ zero exact
  - `Len(max=0)` ✅ zero max
  - `Len(-1)` ✅ ValueError
  - `Len(min=-1)` ✅ ValueError
  - `Len(max=-1)` ✅ ValueError
  - `Len(min=4, max=2)` ✅ ValueError
  - `Len()` ✅ ValueError (no args)
- [ ] Do type signatures in tests match the implementation? (`f.Len.CODE_TOO_LONG`, `f.Len.CODE_TOO_SHORT`) ✅
- [ ] Do the `__init__` parameters use `int | None` (not `typing.Optional`) to avoid shadowing the `Optional` filter class? ✅
