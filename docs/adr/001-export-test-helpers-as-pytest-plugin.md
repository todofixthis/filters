---
status: Accepted
date: 2026-03-10
tags: [pytest, testing, fixtures, plugin]
summary: Test helper fixtures are exported as an auto-registered pytest plugin via the `pytest11` entry point.
---

# 001: Export Test Helpers as a pytest Plugin

## Context

`phx-filters` ships `filters.test.BaseFilterTestCase` for downstream libraries that use
unittest. Projects using pytest have no equivalent — they must re-implement assertion
helpers for filter pass/fail behaviour themselves.

The helpers in `test/conftest.py` (`assert_filter_passes`, `assert_filter_errors`,
`unmodified`, `skip_value_check`) solve this problem, but are internal to this project
and not importable by downstream libraries.

## Options

### Option 1: Do nothing

Leave the helpers in `test/conftest.py` as internal-only fixtures.

**Pros:** No new surface area; no pytest coupling in the package.
**Cons:** Downstream projects must re-implement (or copy) the same assertions.
**Risks:** Divergent implementations across dependent projects.

### Option 2: Auto-registered pytest plugin (Accepted)

Create `src/filters/pytest_plugin.py` with `@pytest.fixture`-decorated helpers.
Register it via a `pytest11` entry point in `pyproject.toml` so pytest discovers it
automatically when `phx-filters` is installed.

Export: `assert_filter_passes`, `assert_filter_errors`, `unmodified`, `skip_value_check`.

**Pros:** True pytest fixtures — injected by name with no downstream config required.
Consistent with established ecosystem patterns (pytest-django, pytest-asyncio, etc.).
**Cons:** pytest is implicitly required at test time; plugin loads for every project that
installs `phx-filters`, even those not testing filters directly.
**Risks:** Fixture name collision is unlikely given the distinctive names, but possible.

### Option 3: Plain callable module

Create `src/filters/testing.py` exporting the helpers as regular functions.
Downstream projects call them directly or wrap them as fixtures in their own conftest.

**Pros:** No pytest coupling in the package; helpers usable outside pytest.
**Cons:** Not injectable as fixtures without additional downstream boilerplate.
**Risks:** Friction discourages adoption; wrapping is error-prone.

## Decision

Adopt Option 2. The `pytest11` entry point is the idiomatic mechanism for distributing
reusable fixtures, and the fixture names are distinctive enough to avoid collisions.
pytest is already a de-facto test-time dependency for any project using these helpers.

`test/conftest.py` is updated to remove the exported symbols (auto-registered plugin
makes them available) and retain only internal helpers (`Lengthy`, `Bytesy`, `Unicody`).

## Consequences

- Downstream projects get `assert_filter_passes` and `assert_filter_errors` as injected
  fixtures with zero configuration.
- `unmodified` and `skip_value_check` are importable from `filters.pytest_plugin`.
- pytest becomes an implicit test-time dependency of any project using the plugin.
- Future changes to the fixture signatures are a breaking change for downstream consumers.
