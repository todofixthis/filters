## Architecture

Composable validation pipeline library. Filters chain via `|`. Source in `src/filters/`, one module per category: base, simple, number, complex, string, extensions. The PyPI name is `phx-filters`; the import name is `filters`.

- Explicit imports with `__all__` throughout, no wildcard imports. `src/filters/__init__.py` orders its imports and `__all__` by module dependency, so ruff's import and `__all__` sorting is off for that file.
- A forward-reference annotation uses `typing.Optional` or `typing.Union`, never `X | None`: `"ClassName" | None` raises `TypeError` at runtime (`str.__or__`), which Sphinx can't recover from. Put `# Use \`Optional\` instead of \`|\` for Sphinx compat` on the line before the annotation; for a return type, on the line before `) ->`, splitting a one-line signature to make one. This is why ruff's `UP007` and `UP045` are ignored.
- A new `BaseFilter` subclass, or one whose `__init__` logic or signature changes, that stores a mutable container (`list`, `dict`, `set` …) must override `__copy__` to copy it (the container only, not what it holds), because `BaseFilter.__copy__` shares containers with the original. Child filters stay shared. Follow `FilterRepeater.__copy__`: a classmethod taking `the_filter: Self` and returning `Self`, with `# pyright: ignore[reportIncompatibleMethodOverride]` on its `def` line, chaining through `super().__copy__(the_filter)`, copying with `.copy()` or `dict(...)` for a `Mapping`. A container shared on purpose gets a comment saying why at its assignment in `__init__`, not an override. Add a copy test for each override, asserting that mutating the copy leaves the original unchanged (ADR 013).

In the template-owned `pyproject.toml`, this project's own content is `[project]`'s dependencies, keywords, classifiers, `pytest11` entry point and optional dependencies; `pyright`, `types-python-dateutil` and `types-pytz` in both the `dev` and `ci` groups; `[tool.mypy]`'s two disabled codes and its `regex` override; `[tool.pyright]`; and `[tool.ruff.lint]` with its per-file ignores. Edit them here and keep them through a template-update conflict.

## Type checking

mypy runs in strict mode on `src` and `test`, as the template's `type-check` job runs it. pyright runs in strict mode on `src/filters` and `test/typing`, in `.github/workflows/project.yml`'s `pyright` job (ADR 017). The pre-commit hook runs mypy but not pyright, so run `uv run pyright src/filters test/typing` before committing a change to either.

Fix a reported error where the fix is honest; otherwise suppress it on the line the checker reports, with a comment on the line above saying why. mypy's `return-value` and `no-any-return` and pyright's `reportReturnType` are disabled until #121, so nothing reports an `Any` returned where a type is declared. In a new `_apply`, or one whose logic you change, assign `_filter()`'s result to a new name and guard it with `if self._has_errors or result is None:`, as `CaseFold._apply` does: reassigning `value` leaves it `Any`, which leaves the rest of the body unchecked.

Each checker reads only its own form: `# type: ignore[code]` does not silence pyright, nor `# pyright: ignore[rule]` mypy, so a line both report needs both. `isinstance()` or `type()` on an `Any` value gives pyright a type with `Unknown` type arguments, which it reports and mypy does not: `cast` to supply the arguments, and where mypy rejects the cast as `redundant-cast`, suppress with `# pyright: ignore[rule]` instead. black re-wraps a line that overflows 88 columns only because of a `# pyright: ignore` comment, leaving the comment after the closing bracket, where pyright ignores it and reports it as unused. Keep the comment on the reported line by letting the call wrap and putting the comment on the reported argument's own line, or by aliasing a long callee to a short local, as `Type._apply` does; never `# fmt: skip`. black leaves a line carrying `# type: ignore` alone.

## Tests

One file per filter in `test/`, named `test_{filter_name}.py`, with a module docstring and functions named `test_{filter_name}_{scenario}`. Always `import filters as f`. `test/typing/` holds the `assert_type` cases both checkers must pass.

The `filters.pytest` plugin provides the `assert_filter_passes(filter_instance, value, expected)` and `assert_filter_errors(filter_instance, value, expected_codes)` fixtures. Always pass `assert_filter_passes` an explicit `expected`: many filters return a different type than the input (`Uuid` returns `UUID`, not `str`). `test/conftest.py` holds the helper classes `Lengthy`, `Bytesy` and `Unicody`; import them relatively (`from .conftest import Bytesy`).

Half the existing tests' docstrings predate `.agents/rules/testing.md` and run over several lines; write new ones to its one-line rule.
