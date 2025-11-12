# Python 3.14 Support Implementation Plan

## Context
Adding Python 3.14 support (released October 7, 2025) while maintaining compatibility with 3.13 and 3.12. Dropping support for Python 3.11 and below allows us to leverage Python 3.12 features.

## Key Python Version Changes

### Python 3.14 New Features (Cannot Use - Must Support 3.12/3.13)
- PEP 649: Deferred annotation evaluation
- PEP 750: Template strings (t-strings)
- PEP 779: Free-threaded Python (official support)
- New `annotationlib` module
- Zstandard compression module

### Python 3.12 Features (Will Use - Dropping 3.11)
- **PEP 695**: New type parameter syntax (`class Foo[T]:` instead of `TypeVar`)
- **PEP 695**: New type alias syntax (`type MyAlias = ...`)
- Improved generic class definitions with automatic variance inference
- Better typing ergonomics overall

### Critical Typing Changes
- `typing.Text`: Deprecated since 3.11, **must replace with `str`** (36 instances found)
- `typing.Pattern`: Should use `re.Pattern` instead (3 instances found)
- Modern type hint syntax available: `X | None` instead of `Optional[X]`, `list[X]` instead of `List[X]`

## Files to Modify

### 1. Configuration Files

**pyproject.toml** (3 changes):
- Line 10: `requires-python = ">=3.12, <4"` (already correct, no change)
- Lines 23-25: Fix classifiers - remove 3.10, 3.11; add 3.14
- Line 103: Update tox `env_list = ["py314", "py313", "py312"]`

**.github/workflows/build.yml**:
- Lines 16-17: Add `"3.14"` to test matrix: `python-version: ["3.14", "3.13", "3.12"]`

**.readthedocs.yaml**:
- Already uses `python: "latest"` (no change needed)

### 2. Documentation Files

**README.rst**:
- Lines 86-87: Add Python 3.14 to compatibility list

**docs/index.rst**:
- Lines 94-96: Fix inconsistency (currently lists 3.11 incorrectly), add 3.14

### 3. Source Code Files - Critical Changes

**Replace 36 instances of `typing.Text` → `str`**:
- `src/filters/string.py` (majority of instances)
- `src/filters/handlers.py`
- Other affected files

**Replace 3 instances of `typing.Pattern` → `re.Pattern`**:
- Add `import re` where needed
- Replace `typing.Pattern[str]` with `re.Pattern[str]`

### 4. Source Code Files - Modernisation Changes

**Apply PEP 695 syntax for generic classes**:
- `src/filters/base.py`:
  - `class BaseFilter[T]:` instead of `class BaseFilter(Generic[T]):`
  - `class FilterChain[T]:` instead of using TypeVar
  - Remove `TypeVar` imports where now unnecessary

**Apply modern type hint syntax (PEP 604/585)**:
- `typing.Optional[X]` → `X | None`
- `typing.Union[X, Y]` → `X | Y`
- `typing.List[X]` → `list[X]`
- `typing.Dict[K, V]` → `dict[K, V]`
- `typing.Tuple[X, ...]` → `tuple[X, ...]`
- `typing.Mapping[K, V]` → `collections.abc.Mapping[K, V]`
- `typing.MutableMapping[K, V]` → `collections.abc.MutableMapping[K, V]`
- `typing.Iterable[X]` → `collections.abc.Iterable[X]`
- `typing.Callable` → `collections.abc.Callable`

**Files affected**:
- `src/filters/base.py`
- `src/filters/simple.py`
- `src/filters/number.py`
- `src/filters/complex.py`
- `src/filters/string.py`
- `src/filters/handlers.py`
- `src/filters/extensions.py`
- `src/filters/test.py`

## Implementation Steps

1. **Update configuration files**:
   - pyproject.toml: classifiers, tox env_list
   - .github/workflows/build.yml: test matrix

2. **Update documentation**:
   - README.rst: Add 3.14 to compatibility list
   - docs/index.rst: Fix 3.11 inconsistency, add 3.14

3. **Critical code changes**:
   - Replace all 36 `typing.Text` → `str`
   - Replace all 3 `typing.Pattern` → `re.Pattern` (add imports)

4. **Modernisation - PEP 695**:
   - Update generic class definitions in base.py and other files
   - Use new `class Foo[T]:` syntax
   - Remove unnecessary TypeVar declarations

5. **Modernisation - PEP 604/585**:
   - Replace `Optional`, `Union`, `List`, `Dict`, `Tuple` with modern syntax
   - Update `Mapping`, `MutableMapping`, `Iterable`, `Callable` to use `collections.abc`

6. **Testing phase**:
   - Run `uv sync --group=dev` to update dependencies
   - Run `uv run pytest --collect-only` (verify still 401 tests)
   - Run `uv run pytest` on current Python version
   - Run `uv run tox -p` (all versions: 3.12, 3.13, 3.14)
   - Run `uv run ruff check` (linting)
   - Build docs: `uv run make clean && uv run make html`

## Verification Checklist

- [ ] All config files specify 3.12-3.14 support
- [ ] No `typing.Text` remains in codebase
- [ ] No `typing.Pattern` remains in codebase
- [ ] PEP 695 syntax used for generic classes
- [ ] Modern type hint syntax (PEP 604/585) applied throughout
- [ ] All tests pass on Python 3.12, 3.13, 3.14
- [ ] Test count remains 401
- [ ] Documentation builds without warnings
- [ ] Ruff linting passes
- [ ] CI/CD pipeline succeeds with all three versions

## Git Commit Strategy

Create a feature branch off `develop` with focused commits:
1. "Update Python version support to 3.12-3.14 in configs 🐍"
2. "Update documentation for Python 3.12-3.14 support 📚"
3. "Replace deprecated typing.Text with str 🔧"
4. "Replace typing.Pattern with re.Pattern 🔧"
5. "Modernise to PEP 695 type parameter syntax ✨"
6. "Adopt modern type hint syntax (PEP 604/585) ✨"

Each commit message ends with a relevant emoji as per project guidelines.
