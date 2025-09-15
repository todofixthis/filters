# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing and Quality Assurance
- **Run tests**: `uv run pytest` (current environment) or `uv run tox -p` (all supported Python versions)
- **Linting**: `uv run ruff check` (code quality and imports)
- **Build package**: `uv build`
- **Install dev dependencies**: `uv sync --group=dev`

### Pre-commit Setup
- **Activate pre-commit hooks**: `uv run autohooks activate --mode=pythonpath`
- Pre-commit runs: black, mypy, pytest, ruff

### Documentation
- **Build docs**: `cd docs && uv run make html`

## Architecture Overview

This is a Python data validation and processing pipeline library called "Filters". The architecture follows a composable filter pattern where filters can be chained together using the `|` operator.

### Core Architecture Components

**Base Filter System** (`src/filters/base.py`):
- `BaseFilter[T]`: Abstract base class for all filters with generic type support
- `FilterChain[T]`: Allows chaining multiple filters using `|` operator
- `InvalidValue`: Exception for validation failures
- `UncaughtException`: Exception wrapper for unexpected errors
- `FilterHarness`: Context manager for error handling

**Filter Categories**:
- **Simple filters** (`src/filters/simple.py`): Date, Datetime, Optional, Call, Array, Length, Required, etc.
- **Number filters** (`src/filters/number.py`): Int, Decimal, Min, Max, Round
- **Complex filters** (`src/filters/complex.py`): FilterMapper, FilterRepeater, FilterSwitch, NamedTuple
- **String filters** (`src/filters/string.py`): Base64Decode, ByteString, CaseFold, Choice, IpAddress, etc.
- **Extension system** (`src/filters/extensions.py`): FilterExtensionRegistry for loading third-party filters

### Key Design Patterns

**Filter Chaining**: Filters implement `__or__` to enable syntax like:
```python
f.Required | f.Decimal | f.Min(Decimal(-90)) | f.Max(Decimal(90))
```

**Parent-Child Relationships**: Filters maintain weak references to parent filters for context and key generation.

**Error Handling**: Two-tier error system distinguishing validation failures (`InvalidValue`) from code bugs (`UncaughtException`).

**Type Safety**: Modern Python typing with generics throughout the codebase.

**Import Strategy**: The `__init__.py` uses explicit imports with `__all__` declarations rather than wildcard imports to satisfy static analysis tools like ruff and improve IDE support.

## Project Status

This project has undergone significant modernisation. The filters now use explicit imports and proper `__all__` declarations for better static analysis support. All major filter categories (base, simple, number, complex, string) are active and available.

### Git Branch Structure
- **Release branch**: `main` (for stable releases only)
- **Development branch**: `develop` (main development branch)
- **Feature development**: Create feature branches off `develop` for all new work
- Always create feature branches for new development rather than working directly on `develop`

## Package Information

- Package name: `phx-filters` 
- Python versions: 3.12+ (3.13, 3.12 tested via tox)
- Built with: hatchling build backend
- Uses `uv` for dependency management and virtual environments

## Troubleshooting

### Common Import Issues

**phx-class-registry v5 Breaking Changes**: If you encounter `ImportError: cannot import name 'EntryPointClassRegistry'`, update the import in `src/filters/extensions.py`:
```python
# Old (v4): from class_registry import EntryPointClassRegistry
# New (v5): from class_registry.entry_points import EntryPointClassRegistry
```

**Ruff Linting F403 Errors**: Use explicit imports with `__all__` declarations instead of wildcard imports (`from module import *`) to satisfy static analysis tools.

**Missing Modules**: If tests fail with `ModuleNotFoundError` for modules like `filters.collections`, check that the package structure matches expectations and that all required modules exist in `src/filters/`.

### Development Environment
- Always run `uv sync --group=dev` after pulling changes to ensure dependencies are up to date
- Use `uv run` prefix for all development commands to ensure proper virtual environment activation

## Language and Style Guidelines

- Use New Zealand English spelling and incorporate commonly-used Te Reo Māori terms where appropriate (e.g. "mahi", "kaupapa", "whānau", etc.)
- Add a relevant emoji to the end of the title of every git commit