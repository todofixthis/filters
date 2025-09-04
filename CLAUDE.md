# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing and Quality Assurance
- **Run tests**: `uv run pytest` (current environment) or `uv run tox -p` (all supported Python versions)
- **Type checking**: `uv run mypyc src test`
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
- **Simple filters** (`src/filters/simple.py`): Date, Datetime, Optional, Call
- **Number filters** (`src/filters/number.py`): Int, Decimal, Min, Max, Round  
- **Collection filters** (`src/filters/collections.py`): Array, Length, Required, etc.
- **Legacy filters**: String, complex filters are commented out in `__init__.py` (being refactored)

### Key Design Patterns

**Filter Chaining**: Filters implement `__or__` to enable syntax like:
```python
f.Required | f.Decimal | f.Min(Decimal(-90)) | f.Max(Decimal(90))
```

**Parent-Child Relationships**: Filters maintain weak references to parent filters for context and key generation.

**Error Handling**: Two-tier error system distinguishing validation failures (`InvalidValue`) from code bugs (`UncaughtException`).

**Type Safety**: Modern Python typing with generics throughout the codebase.

## Project Status

This is an active refactor of a legacy codebase. Many string and complex filters are currently disabled (see commented imports in `__init__.py`) as they're being modernised with the new type system.

## Package Information

- Package name: `phx-filters` 
- Python versions: 3.12+ (3.13, 3.12 tested via tox)
- Built with: hatchling build backend
- Uses `uv` for dependency management and virtual environments

## Language and Style Guidelines

- Use New Zealand English spelling and incorporate commonly-used Te Reo Māori terms where appropriate (e.g. "mahi", "kaupapa", "whānau", etc.)
- Add a relevant emoji to the end of the title of every git commit