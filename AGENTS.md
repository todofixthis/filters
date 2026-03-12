## Getting Started

Before writing code, check:

- `docs/plans/` — current implementation plan
- `docs/adr/INDEX.md` — prior decisions (don't re-litigate)
- `docs/future/` — deferred features (don't re-discuss)

## Architecture Decision Records

When making significant decisions — choosing between libraries, patterns, tools, or conventions — you **must** write an ADR before implementing the decision. Use the `writing-adrs` skill for the format and conventions. ADRs live in `docs/adr/`. Before writing, run `ls docs/adr/` to find the highest existing number and increment it.

If you find yourself about to establish a new cross-cutting pattern (something that will affect multiple domains or files, e.g. a testing convention, a shared utility, an error-handling approach), stop and write an ADR first even if the immediate task feels local. A pattern adopted once becomes the template for everything that follows.

## Commands

- **Test (current Python)**: `uv run pytest`
- **Test (all versions)**: `uv run tox -p`
- **Verify test count**: `uv run pytest --collect-only` — note count at start of mahi; verify it increases appropriately when done
- **Lint**: `uv run ruff check`
- **Build docs**: `uv run make -C docs clean && uv run make -C docs html`
- **Sync deps**: `uv sync --group=dev` (run after pulling)
- **Commit**: always `uv run git commit` — autohooks requires the uv venv

## Architecture

Composable validation pipeline library. Filters chain via `|`. Source in `src/filters/`; modules for each category: base, simple, number, complex, string, extensions.

- Explicit imports with `__all__` throughout — no wildcard imports
- Forward-reference type hints must use `typing.Optional`/`typing.Union` (not `X | None`) to avoid Sphinx autodoc failures — add `# Use Optional for Sphinx compat` inline
- Import collection ABCs from `collections.abc`; keep `Any` and `Hashable` from `typing`

## Tests

One file per filter in `test/`, named `test_{filter_name}.py`. Always `import filters as f`.

**Custom fixtures** (`test/conftest.py`):
- `assert_filter_passes(filter_instance, value, expected)` — always pass an explicit `expected`; many filters return a different type than the input (e.g. `Uuid` returns `UUID`, not `str`)
- `assert_filter_errors(filter_instance, value, expected_codes)`
- Helper classes: `Lengthy`, `Bytesy`, `Unicody`

Test functions: `test_{filter_name}_{scenario}`. Each test file needs a module-level docstring.

## Docstrings

Google/Napoleon format (`Args:`, `Returns:`, `Note:`) — not Sphinx `:param:` style. Max 80 chars per line. Escape backslashes (e.g. `'\\n'` not `'\n'`). Blank line before lists inside `Args:` sections to avoid Sphinx indentation warnings. ReadTheDocs treats all Sphinx warnings as errors — resolve them before pushing.

## Code Comments

Place comments on the line preceding the code they document, not as trailing comments.

## Language and Style

- NZ English; incorporate Te Reo Māori where natural (e.g. "mahi", "kaupapa")
- Use "Initialises" not "Initializes"

## Branches

- `main` — releases only; merge from `develop` via PR
- `develop` — main development branch
- Feature branches off `develop` for all new work

## Git Worktrees

Use `.worktrees/` for isolated workspaces (project-local, gitignored).

After switching to a worktree, run `uv run autohooks activate --mode=pythonpath` to install the pre-commit hook for that worktree.

## Package

Package name is `phx-filters` (distinct from the `filters` import name).

## Troubleshooting

**conftest import errors**: use relative imports (`from .conftest import Bytesy`).

**Sphinx forward reference warnings** (`unsupported operand type(s) for |`): use `typing.Optional["ClassName"]` not `"ClassName" | None` — see Architecture above.
