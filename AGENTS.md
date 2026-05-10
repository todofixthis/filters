> `CLAUDE.md` is a symlink to this file — edit `AGENTS.md` only.

## Getting Started

Before writing code, check:

- `docs/plans/` — current implementation plan
- `docs/adr/INDEX.md` — prior decisions (don't re-litigate)
- `docs/future/` — deferred features (don't re-discuss)

## Architecture Decision Records

When making significant decisions — choosing between libraries, patterns, tools, or conventions — you **must** write an ADR before implementing the decision. Use the `writing-adrs` skill for the format and conventions. ADRs live in `docs/adr/`. Before writing, run `ls docs/adr/` to find the highest existing number and increment it.

If you find yourself about to establish a new cross-cutting pattern (something that will affect multiple domains or files, e.g. a testing convention, a shared utility, an error-handling approach), stop and write an ADR first even if the immediate task feels local. A pattern adopted once becomes the template for everything that follows.

## Commands

```bash
uv run autohooks activate --mode=pythonpath            # install pre-commit hook (once per clone)
uv run git commit                                      # always use instead of git commit (runs autohooks)
uv add --bounds major <package>                        # add a runtime dependency at latest version
uv add --bounds major --group dev <package>            # add a dev dependency at latest version
uv sync --group=dev                                    # sync deps after pulling
uv run pytest                                          # run tests (current Python)
uv run tox -p                                          # run tests (all supported versions)
uv run pytest --collect-only                           # verify test count (note at start of mahi; confirm it increases when done)
uv run ruff check                                      # lint
uv run make -C docs clean && uv run make -C docs html  # build docs
```

## Architecture

Composable validation pipeline library. Filters chain via `|`. Source in `src/filters/`; modules for each category: base, simple, number, complex, string, extensions.

- Explicit imports with `__all__` throughout — no wildcard imports
- Forward-reference type hints must use `typing.Optional`/`typing.Union` (not `X | None`) — `"ClassName" | None` raises a Python runtime `TypeError` (`str.__or__` unsupported) that Sphinx cannot recover from; this is not fixed in Sphinx 9 — add `# Use Optional for Sphinx compat` inline
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

### Writing for coding agents

- Do not document information that already exists in the coding agent's training data or could be easily discovered by reading the code.
- Do not list individual files; list high-level directories so the agent knows where to look.
- Aim for concise style that optimises token count without sacrificing clarity.

## Branches

- `main` — releases only; merge from `develop` via PR
- `develop` — main development branch
- Feature branches off `develop` for all new work

## Git Worktrees

Use `.worktrees/` for isolated workspaces (project-local, gitignored).

After switching to a worktree, run the autohooks activate command (see Commands) to install the pre-commit hook for that worktree.

## Package

Package name is `phx-filters` (distinct from the `filters` import name).

## Troubleshooting

**conftest import errors**: use relative imports (`from .conftest import Bytesy`).

**Sphinx forward reference errors** (`TypeError: unsupported operand type(s) for |`): `"ClassName" | None` fails at Python runtime because `str.__or__` is not supported — not a Sphinx bug, and not fixed in Sphinx 9. Use `typing.Optional["ClassName"]` — see Architecture above.
