# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing and Quality Assurance
- **Run tests**: `uv run pytest` (current environment) or `uv run tox -p` (all supported Python versions)
- **Run specific filter tests**: `uv run pytest test/test_decimal.py test/test_uuid.py`
- **Run filter category tests**: `uv run pytest test/test_filter_*.py` (complex filters)
- **Run pattern-based tests**: `uv run pytest -k "decimal or uuid"` (tests containing keywords)
- **Check test collection**: `uv run pytest --collect-only` (verify test count: should be 401 total)
- **Linting**: `uv run ruff check` (code quality and imports)
- **Build package**: `uv build`
- **Install dev dependencies**: `uv sync --group=dev`

### Test Architecture
The test suite uses **pytest-style function-based tests** with a **modular file structure**:

**Test Organisation**: Each filter has its own test file (e.g., `test_decimal.py`, `test_uuid.py`, `test_filter_mapper.py`). This modular approach provides:
- Easy location of filter-specific tests
- Ability to run individual filter test suites
- Clear separation of concerns
- Better maintainability and navigation

**Custom Fixtures** (`test/conftest.py`):
- **`assert_filter_passes(filter_instance, test_value, expected_value)`**: Verifies successful filter processing
- **`assert_filter_errors(filter_instance, test_value, expected_codes)`**: Verifies filter validation errors
- **Helper classes**: `Lengthy`, `Bytesy`, `Unicody` available from conftest for object-like testing

**Naming Conventions**:
- **File naming**: `test_{filter_name}.py` (e.g., `test_decimal.py`, `test_filter_chain.py`)
- **Function naming**: `test_{filter_name}_{scenario}` (e.g., `test_decimal_pass_none`)
- **Filter import**: Always use `import filters as f`

**Documentation Standards**:
- **Module docstrings**: Each test file must have a module-level docstring at the very top:
  ```python
  """
  Tests for the [FilterName] filter.
  """
  ```
- **Multi-line format**: Use multi-line docstrings with opening and closing `"""` on separate lines
- **Consistent naming**: Use proper capitalisation in docstrings (e.g., "FilterChain", "Base64Decode", "Extensions system")

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

### Test-Specific Troubleshooting

**Test Import Errors**: If tests fail importing helper classes like `Bytesy` or `Unicody`, use relative imports:
```python
from .conftest import Bytesy, Unicody
```

**Expected Value Mismatches**: When filter output types differ from input (e.g., UUID filter returns UUID objects, not strings), specify the actual expected object type rather than using `unmodified`.

**Test Count Verification**: After test modifications, always verify the total remains 401 tests using `uv run pytest --collect-only`.

### Test Development Best Practices

**Writing New Tests**: When creating tests, always specify explicit expected values:
```python
# Good: Explicit expected value
assert_filter_passes(f.Uuid(), "3466c56a-2ebc-449d-97d2-9b119721ff0f", UUID("3466c56a-2ebc-449d-97d2-9b119721ff0f"))

# Avoid: Using unmodified when filter transforms the value
assert_filter_passes(f.Uuid(), "3466c56a-2ebc-449d-97d2-9b119721ff0f")  # Wrong - returns UUID object, not string
```

**Test Organisation Principles**: When working with the test suite:
- Each filter has its own dedicated test file for better organisation and maintainability
- Run specific filter tests: `uv run pytest test/test_decimal.py`
- Run filter category tests: `uv run pytest test/test_*decimal*.py test/test_*int*.py` (number filters)
- The modular structure makes it easy to locate, run, and maintain tests for specific functionality

### Development Workflows

**Large-Scale Refactoring**: For complex multi-step tasks involving many files (e.g., test reorganisation, mass refactoring):
- Use the **Task tool with general-purpose agent** for systematic file operations
- The agent can handle bulk file creation, splitting, and organisation tasks efficiently
- Always verify test counts before and after major structural changes: `uv run pytest --collect-only`

**Code Formatting Tasks**: For systematic formatting changes across multiple files:
- **Task tool for bulk operations**: Use the general-purpose agent for tasks affecting 10+ files (e.g., docstring formatting, import standardisation)
- **Direct tools for small changes**: Use Edit/MultiEdit for 1-5 files
- **Pattern-based changes**: The Task tool excels at applying consistent patterns across the codebase

**File Organisation**: When working with large codebases:
- Individual test files per filter improve maintainability and navigation
- Use consistent naming patterns: `test_{filter_name}.py`
- Group related functionality logically (complex, simple, number, string filter categories)

### Development Environment
- Always run `uv sync --group=dev` after pulling changes to ensure dependencies are up to date
- Use `uv run` prefix for all development commands to ensure proper virtual environment activation

## Language and Style Guidelines

- Use New Zealand English spelling and incorporate commonly-used Te Reo Māori terms where appropriate (e.g. "mahi", "kaupapa", "whānau", etc.)
- Add a relevant emoji to the end of the title of every git commit