# Plan: Generic Type Hints for Filters (issue #34)

**Issue:** [#34 — Add generic type hints](https://github.com/todofixthis/filters/issues/34)
**Branch:** `claude/issue-34-planning-ma47i5`
**Status:** Awaiting review — no library code changed.

## Goal

Parameterise the filter hierarchy so a type checker can infer a chain's output
type, making `FilterRunner(...).cleaned_data` and `BaseFilter.apply()` return
something better than `Any`.

The issue text says `FilterRunner(...).apply()`. That method returns `None` — it
only resets cached state. The inference targets are `FilterRunner.cleaned_data`
and `apply()` on the chain itself.

## Headline

**Neither breaking change proposed on the issue is necessary.** Both were tested
and both turned out to be avoidable. The design below keeps `f.Unicode | f.Strip`
*and* infers through it, and keeps `f.Type(bool)`.

What is left is a much smaller question: whether to fix two genuine Liskov
violations (a v4.0.0) or suppress them (a v3.8.0).

## Evidence

Everything below was run against mypy 1.19.1 and pyright 1.1.408. The complete
design was validated end to end in a single spike: both checkers clean apart
from one suppressible pyright lint, with `--warn-unused-ignores` confirming
every suppression is load-bearing, and a deliberately wrong `assert_type`
confirmed to fail on both.

| Question | Result |
|---|---|
| ⚠ Must `FilterMeta.__or__` go? | **No.** Annotated as `@overload`s with a `cls: "type[BaseFilter[T_out]]"` self-type, both checkers infer `Unicode \| NotEmpty` → `FilterChain[str]` and `Unicode \| NotEmpty \| Int` → `FilterChain[int]`. A *plain* (non-overloaded) method does fail — pyright rejects the self-type and mypy falls back to `types.UnionType` — which is what makes this look impossible on a first pass. |
| ⚠ Must `Type.__init__` require a tuple? | **No.** Overloads resolve `Type(str)` → `Type[str]` and `Type((str, int))` → `Type[str \| int]`. |
| Do the `Type` overloads cope with abstract arguments? | **Only with bare-`type` fallbacks.** `type[T]` alone makes `Type(Iterable)` a mypy `type-abstract` error and a pyright "no overloads match" — and the library passes ABCs to `Type` at nine call sites (`simple.py:128,170,412,518,575,758,915`, `complex.py:80,526`). Adding `type` and `tuple[type, ...]` fallbacks clears both. |
| One type parameter or two? | **One.** With a pass-through marker doing the identity work, nothing in the design ever produces a `T_in` other than `Any`; a second parameter costs every subclass, downstream ones included, and buys nothing. |
| Does a generic base break unparameterised subclasses? | **Under `mypy --strict`, yes** (`disallow_any_generics`): `class Country(BaseFilter)` errors. pyright does not flag it. A PEP 696 default (`TypeVar("T_out", default=Any)`) fixes it on both. |
| Can `ByteString(Unicode)` and `Date(Datetime)` keep their bases? | **Only by suppression.** Re-listing bases fails pyright (mypy passes it and silently infers `str` for `ByteString`). Overriding `apply` with `# type: ignore[override]` works on both — so this is suppressible, unlike the parameterised-base form. |
| Does `Generic` break the Sphinx build? | **No.** `base.py` was patched to make `BaseFilter`, `FilterChain` and `Type` generic with an overloaded `__or__`, then `uv run make -C docs clean && uv run make -C docs html`: build succeeded, one pre-existing intersphinx warning, and `uv run pytest` passed all 551 tests. Patch reverted. |
| PEP 695 or classic `TypeVar`? | **Classic.** PEP 695 infers variance rather than letting it be declared, and this design wants `T_out` declared. (The "consumers on old mypy can't parse it" argument is weak — `requires-python` is already `>=3.12`.) |

## Type model

```python
# `default=Any` keeps `class Country(BaseFilter)` valid under mypy --strict.
T_out = TypeVar("T_out", default=Any)

class BaseFilter(Generic[T_out], metaclass=FilterMeta): ...
class FilterChain(BaseFilter[T_out]): ...
```

Filters fall into categories distinguished by a base class, so that `__or__` can
overload on them. `BaseFilter.__or__` and `FilterMeta.__or__` each carry the same
five overloads (pass-through as class and as instance, widening, transforming as
class and as instance).

| Category | Base | Chain effect | Members |
|---|---|---|---|
| Transforming | `BaseFilter[T]` | Output becomes `T` | `Unicode`, `ByteString`, `ByteArray`, `Int`, `Decimal`, `Uuid`, `Split`, `Regex`, `Base64Decode`, `CaseFold`, `Strip`, `IpAddress`, `Date`, `Datetime`, `JsonDecode`, `TomlDecode`, `NamedTuple`, `FilterMapper`, `Empty` |
| Pass-through | `PassThrough` | Output unchanged | `NotEmpty`, `Required`, `Min`, `Max`, `MinLength`, `MaxLength`, `MaxBytes`, `MaxChars`, `Len`, `Length`, `NoOp` |
| Widening | `Widening[D]` | Output becomes `T_out \| D` | `Optional` |
| Ctor-typed | `BaseFilter[T]`, `T` from an `__init__` argument | Output becomes `T` | `Type`, `Choice`, `Call`, `Round`, `NamedTuple` |
| Untyped | `BaseFilter[Any]` | Output becomes `Any` | `Item`, `Omit`, `Pick`, `Array`, `FilterSwitch`, `FilterRepeater` |

Notes on the awkward members, each of which needs the classification stated
rather than left to the implementer:

- **`Choice` is transforming, not pass-through.** `_apply` returns
  `self.choice_map[value]` — the canonical choice, not the input. With
  `case_sensitive=False`, `Choice(['RO']).apply('ro')` returns `'RO'`.
  `Choice[T]` from `choices: Iterable[T]`.
- **`Call`** takes `T` from the callable's return type; **`Round`** from
  `result_type: type[T]`.
- **`Array`** parameterises to `Sequence[Any]` via `Type`, but `_apply` rejects
  `str` and `bytes`, which *are* Sequences — the parameter overstates the
  contract. `BaseFilter[Any]` is honest; `Sequence[Any]` is not.
- **`Omit` / `Pick`** degrade to `dict`/`list` through `selective_copy_*`, so
  neither pass-through nor a fixed `T` fits.
- **`FilterSwitch`** would be the union of its cases' outputs; not worth the
  overload machinery, so `Any`.
- **`FilterRepeater`** returns `mapping_result_type` or `sequence_result_type`,
  both *overridable class attributes*, so even `list[T] | dict[Any, T]` would be
  a guess.
- **A narrowing category was considered and rejected for now.** `Required` and
  `NotEmpty(allow_none=False)` could take `T | None` → `T`, which is worth real
  money given `Required` heads nearly every paddock schema entry. It needs
  `apply()`'s `| None` question (below) settled first; deferred to a follow-up
  issue rather than smuggled into this one.

### `apply()`'s return type

`_apply_none()` returns `None` in every filter, so `apply(None)` is `None`
whatever `T_out` is. `apply` must therefore be `T_out | None`, and so must
`_filter`. That resolves what would otherwise be an awkward asymmetry with
`cleaned_data`, which stays `T_out` because `is_valid()` is a public, documented
gate — the whole point of the issue is that reading `cleaned_data` after that
gate should give you a real type.

### Names whose fate must be decided in Phase 1

- **`FilterCompatible`** is public and in `__all__`. Both `_filter` and
  `FilterRunner`'s overloads need a generic `FilterCompatible[T]`, and
  `filters-pydantic` annotates against it (`FilterField.__init__`).
- **`resolve_filter`** is declared `Optional["FilterChain"]` but returns the
  resolved `BaseFilter` — mypy already flags it today. Its corrected return type
  propagates to `FilterRunner.filter_chain`.

## Breaking changes

Only two remain, and both are optional.

### 1. `ByteString(Unicode)` and `Date(Datetime)`

`Unicode` outputs `str` but `ByteString` outputs `bytes`; `Datetime` outputs
`datetime` but `Date` outputs `date`. Each subclass contradicts its parent's
output type.

| Option | Pros | Cons |
|---|---|---|
| **A. Extract a shared private base** (`_BaseDecoder`, `_BaseDatetime`) | Fixes a real unsoundness: today `def f(x: Unicode) -> str: return x.apply(v)` silently returns `bytes` when handed a `ByteString` | `issubclass(f.ByteString, f.Unicode)` becomes `False` — a silent behavioural break |
| **B. Duplicate the shared logic** | Same typing outcome | Same `issubclass` break, plus duplication |
| **C. Override `apply` with `# type: ignore[override]`** | Non-breaking; verified working on both checkers | Keeps a Liskov violation, deliberately, in the type model this whole exercise exists to make trustworthy |

**Recommendation: A.** C is genuinely available — an earlier draft of this plan
wrongly said it was not — so this is a judgement call, not a forced move. A is
right because the violation is real: the unsoundness it papers over is exactly
the class of bug generic hints are meant to catch.

### 2. `BaseFilter.__copy__`

It is a `classmethod` taking the filter as an argument, and `FilterChain` and
`FilterRepeater` override it in that shape (mypy already flags both as Liskov
violations). Reworking to `def __copy__(self) -> Self` breaks every third-party
subclass that overrides it. This is a release-note item, not incidental
tidy-up — an earlier draft filed it as friction.

## Release shape

The two items above are the only things forcing a major.

- **v3.8.0 (non-breaking):** everything else, with option C for `ByteString`/
  `Date` and `__copy__` annotated around rather than reworked.
- **v4.0.0:** the same, plus option A and the `__copy__` rework.

**Recommendation: v4.0.0.** Both fixes are small, both are real soundness bugs,
and a major that breaks almost nothing is a cheap place to spend them. The
question is worth putting to review precisely because the answer is no longer
forced.

## Prerequisites

1. **`src/filters/py.typed`.** The package ships no marker, so every annotation
   is invisible downstream today — `filters-pydantic` carries
   `# type: ignore[misc]` on `class PydanticModel(BaseFilter)` for this reason.
   Needs the file plus a hatch build include.
2. **A type checker in CI.** mypy is commented out of `[dependency-groups]`,
   `[tool.autohooks]`, `[tool.mypy]` and `[tool.tox]`.
3. **`typing_extensions`**, or a floor bump to Python 3.13. `TypeVar(default=)`
   is native from 3.13; `requires-python` is currently `>=3.12`.

### The Phase 0 error budget

Measured on the tree as it stands, so Phase 0 is not the tidy-up it looks like:

| check | errors |
|---|---|
| `mypy --ignore-missing-imports src` | 47 |
| `mypy --strict --ignore-missing-imports src` | 278 |
| `mypy --strict --ignore-missing-imports src test` | 882 |
| `pyright src` | 78 |

Phase 0 must pick one of: fix all 278, adopt a baseline and ratchet, or stage
strictness flag by flag. Left undecided, it blocks every later phase.

## Testing inference

Runtime tests cannot see a regression from `FilterChain[str]` to
`FilterChain[Any]`, so this needs its own harness — a new cross-cutting
convention, hence an ADR.

A `test/typing/` directory of modules using `typing.assert_type`, checked by
**both** mypy (what consumers run) and pyright (which diverges from mypy on
several constructs this design leans on). The modules import cleanly, so pytest
collects them for free.

Three things the harness must get right:

- **Negative cases.** A wrong `assert_type` was confirmed to fail on both
  checkers, so the harness can fail. Assertions that a construct is *rejected*
  need `# type: ignore[...]` under `--warn-unused-ignores`, so a rule that
  silently stops firing fails the build.
- **Both comment dialects.** pyright ignores mypy error codes and vice versa, so
  shared modules need both. pyright's analogue of `--warn-unused-ignores` is
  `reportUnnecessaryTypeIgnoreComment`, **off by default even in strict** — not
  enabling it leaves the negative cases unguarded on the pyright side, which is
  the exact failure this section exists to prevent.
- **No assertions on abstract `Type` arguments.** The checkers disagree:
  `Type(Mapping)` is `Type[Any]` under mypy and `Type[Mapping[...]]` under
  pyright. Neither errors; asserting either would fail the other.

## ADRs required

Per `AGENTS.md`, written before the change each governs.

1. Type parameter model — one parameter, `default=Any`, classic `TypeVar` over
   PEP 695, with the variance rationale.
2. Filter categories and the marker base classes.
3. Type checking in CI — mypy plus pyright, the strictness ramp, and the
   `assert_type` harness.
4. Splitting the `ByteString` / `Date` inheritance chains (only if option A).

## Phases

| Phase | Scope | Breaking | Size |
|---|---|---|---|
| **0** | `py.typed`; mypy and pyright in CI plus the strictness decision; `test/typing/` harness; fix `test.py:51`'s invalid `Callable[[...], ...]`; correct `resolve_filter`'s return type. | No | L |
| **1** | `base.py`: generic `BaseFilter`/`FilterChain`, category markers, both `__or__` overload sets, `Type`'s overloads, `FilterCompatible[T]`, `_filter`, `apply`. | No | L |
| **2** | `number.py`, `string.py`, `simple.py`, `complex.py` — annotate every filter into its category. | No | L |
| **3** | `handlers.py` — generic `FilterRunner`. **Closes the issue.** | No | S |
| **4** | `macros.py`, `extensions.py`, `test.py`, `pytest.py`. | No | S |
| **5** | Liskov repairs: split `ByteString`/`Date`, rework `__copy__`. | Yes | S |
| **6** | Docs, README and the upgrade note. | No | M |
| **7** | Downstream: paddock and `filters-pydantic` — code and skills. | — | M |

Phases 1 and 2 are one atomic change under `mypy --strict`: once `BaseFilter` is
generic, `disallow_any_generics` rejects every unparameterised subclass in the
package. Either they land together or Phase 0's strictness decision defers that
flag. **This is the constraint most likely to derail execution, so settle it in
Phase 0.**

## Consumer impact

Far smaller than the issue anticipated, because the chaining idiom survives.

**paddock** — no source changes forced. The `cast()` calls in
`config/filters.py` can go once `_filter` is typed, and the skill's section on
narrowing `self._filter` needs rewriting to match `T | None`. `f.Type(dict)` and
`f.Type((str, Path))` both keep working.

**filters-pydantic** — can drop `# type: ignore[misc]` from `PydanticModel`
once `py.typed` ships. `FilterField` becomes a candidate for `FilterField[T]`,
closing the gap its own docstring apologises for ("`phx-filters` chains have no
generic typing"). Its documented example `FilterField(f.Required | f.Unicode |
f.NotEmpty)` keeps working unchanged.

**`phx-filters-django` / `phx-filters-iso`** — checked both: every filter is an
unparameterised `BaseFilter` subclass and neither chains a bare class in code.
They stay valid at runtime, and the `default=Any` typevar keeps them valid under
`mypy --strict` too. `filters-iso` has three docstrings reading
``Required | Locale``, which now remain correct.

**`filters.ext` and `filter_macro`** — both depend on `FilterMeta.__or__`
(`create_instance` returns the class specifically so `filters.ext.MyFilter |
Other` works, and its docstring cites the metaclass by name; `macros.py:43`
returns `Unicode | Strip | NotEmpty`). Keeping the operator keeps both intact.
Macros stay opaque to type checkers and resolve to `Any` — a documented
limitation, not a regression.

## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*

- **`FilterRepeater`, `FilterSwitch`, `Item`, `Omit`, `Pick`, `Array` stay
  `BaseFilter[Any]`.** Precise types for them depend on runtime values or
  overridable class attributes. Accepted as a limitation rather than chased.
- **`FilterMapper` resolves to `dict[str, Any]`.** Per-key inference needs
  PEP 728 `TypedDict` support; out of scope.
- **A narrowing category for `Required` is deferred**, not rejected.

## Decisions for review

1. **v3.8.0 or v4.0.0** — i.e. fix the two Liskov violations, or suppress them?
2. **Phase 0's strictness stance:** fix 278 errors, ratchet from a baseline, or
   stage the flags? This gates whether phases 1 and 2 can be separate commits.
3. **`typing_extensions` dependency, or bump the floor to Python 3.13?**
4. **pyright in CI alongside mypy** — the design leans on constructs where the
   two diverge, and the negative-test guarding differs between them.
5. **`apply() -> T_out | None`** — confirmed forced by `_apply_none`, but it
   makes every call site narrow. Worth confirming you want that over a
   convenient lie.
6. **`issubclass(f.ByteString, f.Unicode)` becoming `False`** (only if v4.0.0).
