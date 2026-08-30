# Plan: Generic Type Hints for Filters (issue #34)

**Issue:** [#34 — Add generic type hints](https://github.com/todofixthis/filters/issues/34)
**Branch:** `claude/issue-34-planning-ma47i5`
**Status:** Awaiting review — no library code changed.

## Goal

Parameterise the filter hierarchy so a type checker can infer a chain's output
type, making `FilterRunner(...).cleaned_data` and `BaseFilter.apply()` return
something better than `Any`.

The issue says `FilterRunner(...).apply()`. That method returns `None` — it only
resets cached state. The inference targets are `FilterRunner.cleaned_data` and
`apply()` on the chain.

## Headline

**Nothing has to break.** Both breaking changes proposed on the issue turned out
to be avoidable, and so did the two Liskov repairs that replaced them:

- `f.Unicode | f.Strip` survives and infers, via an overloaded metaclass
  operator.
- `f.Type(bool)` survives, via overloads with bare-`type` fallbacks.
- `__copy__` keeps its classmethod shape, parameterised with a bound `TypeVar`.
- `issubclass(f.ByteString, f.Unicode)` survives a hierarchy split, via
  `Unicode.register(ByteString)` — `FilterMeta` already subclasses `ABCMeta`.

This can ship as **v3.8.0**. The remaining question is how strict the checkers
run, not what to break.

## Evidence

Run against mypy 1.19.1 and pyright 1.1.408. The design was validated end to end
in a spike: both checkers clean, `--warn-unused-ignores` confirming every
suppression is load-bearing, and a wrong `assert_type` confirmed to fail on both.

| Question | Result |
|---|---|
| Must `FilterMeta.__or__` go? | **No.** As `@overload`s with a `cls: "type[BaseFilter[T_out]]"` self-type, both checkers infer `Unicode \| NotEmpty` → `FilterChain[str]`. A *plain* method does fail — pyright rejects the self-type, mypy falls back to `types.UnionType` — which is what makes this look impossible on a first pass. |
| How many `__or__` overload sets are needed? | **Three.** `FilterChain.__or__` (`base.py:427`) overrides the base, so every `\|` after the first dispatches to it. Left inheriting, `Unicode \| NotEmpty \| Int` degrades to `FilterChain[Any]` on both checkers. |
| Must `Type.__init__` require a tuple? | **No.** Overloads give `Type(str)` → `Type[str]`, `Type((str, int))` → `Type[str \| int]`. |
| Do those overloads cope with abstract arguments? | **Only with bare-`type` fallbacks.** `type[T]` alone makes `Type(Iterable)` a mypy `type-abstract` error and a pyright "no overloads match" — and the library passes ABCs to `Type` at nine sites (`simple.py:128,170,412,518,575,758,915`, `complex.py:80,526`). |
| One type parameter or two? | **One.** With a pass-through marker doing the identity work, nothing produces a `T_in` other than `Any`; a second parameter taxes every subclass, downstream ones included. |
| Does a generic base break unparameterised subclasses? | **Yes, on both checkers at full strictness** — mypy's `disallow_any_generics` and pyright's `reportMissingTypeArgument`. A PEP 696 default (`TypeVar("T_out", default=Any)`) clears both. |
| Must `__copy__` be reworked to `(self) -> Self`? | **No.** Keeping `@classmethod def __copy__(cls, the_filter: TF) -> TF` with `TF = TypeVar("TF", bound="BaseFilter")` type-checks clean on both, infers the subclass through `copy()`, and clears the two Liskov errors mypy flags today (`base.py:447`, `complex.py:65`). No API change. |
| Can `ByteString(Unicode)` / `Date(Datetime)` keep their bases? | **Only by suppression** — re-listing bases fails pyright (mypy passes it and silently infers `str` for `ByteString`); overriding `apply` with `# type: ignore[override]` works on both. Splitting them is optional, and `Unicode.register(ByteString)` keeps `issubclass` and `isinstance` both `True`. |
| Does `Generic` break the Sphinx build? | **No.** `base.py` was patched to make `BaseFilter`, `FilterChain` and `Type` generic with an overloaded `__or__`, then `uv run make -C docs clean && uv run make -C docs html`: build succeeded, one pre-existing intersphinx warning, and `uv run pytest` passed all 551 tests. Patch reverted. |
| PEP 695 or classic `TypeVar`? | **Classic.** PEP 695 infers variance rather than letting it be declared. |

## Type model

```python
# `default=Any` keeps `class Country(BaseFilter)` valid at full strictness.
T_out = TypeVar("T_out", default=Any)

class BaseFilter(Generic[T_out], metaclass=FilterMeta): ...
class FilterChain(BaseFilter[T_out]): ...
```

Categories are distinguished by a base class so `__or__` can overload on them.
The same five overloads (pass-through as class and as instance, widening,
transforming as class and as instance) appear in **three** places:
`FilterMeta.__or__`, `BaseFilter.__or__` and `FilterChain.__or__`.

| Category | Base | Chain effect | Members |
|---|---|---|---|
| Transforming | `BaseFilter[T]` | Output becomes `T` | `Unicode`→`str`, `ByteString`→`bytes`, `ByteArray`→`bytearray`, `CaseFold`→`str`, `Strip`→`str`, `MaxChars`→`str`, `MaxBytes`→`bytes`, `Base64Decode`→`bytes`, `IpAddress`→`str`, `Regex`→`list[str]`, `Int`→`int`, `Decimal`→`Decimal`, `Uuid`→`UUID`, `Date`→`date`, `Datetime`→`datetime`, `TomlDecode`→`dict[str, Any]` |
| Pass-through | `PassThrough` | Output unchanged | `NotEmpty`, `Required`, `Empty`, `Min`, `Max`, `MinLength`, `MaxLength`, `Len`, `Length`, `NoOp` |
| Widening | `Widening[D]` | Output becomes `T_out \| D` | `Optional` |
| Ctor-typed | `BaseFilter[T]`, `T` bound from `__init__` | Output becomes `T` | `Type`, `Choice`, `Call`, `Round`, `NamedTuple`, `Split` |
| Untyped | `BaseFilter[Any]` | Output becomes `Any` | `Item`, `Omit`, `Pick`, `Array`, `JsonDecode`, `FilterSwitch`, `FilterRepeater`, `FilterMapper` |

Every filter exported from `__init__.py` appears exactly once. The awkward ones,
so the implementer need not rule on them:

- **`MaxBytes` transforms.** `_apply` encodes and returns `bytes` on every path
  (`f.MaxBytes(10).apply('hello')` → `b'hello'`). Filed as pass-through, it would
  have made `f.Unicode | f.MaxBytes(10)` infer `str` for a chain returning
  `bytes` — the exact unsoundness this exercise exists to catch.
- **`Empty` passes through.** It returns the input untouched; there is no `T`.
- **`Choice` is ctor-typed, not pass-through.** `_apply` returns
  `self.choice_map[value]` — the canonical choice, not the input. With
  `case_sensitive=False`, `Choice(['RO']).apply('ro')` returns `'RO'`.
  `Choice[T]` binds from `choices: Iterable[T]`.
- **`Split` is ctor-typed on `keys`**: `dict[str, str]` when `keys` is set,
  `list[str]` otherwise. Needs `Type`-style overloads.
- **`Call`** binds `T` from the callable's return type; **`Round`** from
  `result_type: type[T]`; **`NamedTuple`** from `type_: type[T]`.
- **`JsonDecode`** has no `T` to bind — `decoder: Callable = json.loads` returns
  `Any`. Ctor-typing it off `decoder: Callable[..., T]` is pointless while the default is
  `json.loads`.
- **`Array`** would parameterise to `Sequence[Any]` through `Type`, but `_apply`
  rejects `str` and `bytes`, which *are* Sequences — the parameter would
  overstate the contract.
- **`FilterMapper` and `FilterRepeater`** both pick their result type from the
  *input value* (`Mapping` → dict, otherwise list), and both expose
  `mapping_result_type` / `sequence_result_type` as overridable class
  attributes. No static type is honest.
- **A narrowing category was considered and deferred.** `Required` and
  `NotEmpty(allow_none=False)` could take `T | None` → `T`, worth real money
  given `Required` heads nearly every paddock schema entry. It depends on the `| None` question below;
  follow-up issue, not smuggled in here.

### `apply()`'s return type

`apply` and `_filter` should be `T_out | None`, because `_invalid_value` returns
its `replacement` — `None` by default — on every rejection path where the
handler does not raise. That is the real reason; `_apply_none` is *not*, since
`Optional._apply_none` returns its default and `FilterChain._apply_none`
delegates.

This does collide with `Widening`: `Optional` exists to make `None` go away, and
`T_out | D | None` hands it back. Worth deciding whether `Optional` gets a
narrowing overload rather than inheriting the `| None`.

`cleaned_data` stays `T_out`. That is a **knowing choice, not a derivation** —
`handlers.py:206` returns `self._cleaned_data`, which is `None` when the filter
rejects, and nothing forces `is_valid()` first. It is typed optimistically
because reading it after the documented gate is the whole point of the issue.

### Names to decide in Phase 1

- **`FilterCompatible`** is public, in `__all__`, and includes `None`
  (`base.py:21`). None of the five overloads accept `None`, so whether
  `f.Unicode | None` stays legal is undecided. A generic `FilterCompatible[T]`
  is needed by `_filter` and `FilterRunner`, and `filters-pydantic` annotates
  against it (`FilterField.__init__`).
- **`resolve_filter`** is declared `Optional["FilterChain"]` but returns the
  resolved `BaseFilter` — mypy flags it today. Its corrected type propagates to
  `FilterRunner.filter_chain`.

## Optional changes

Neither is required; both are soundness fixes.

### Split `ByteString` from `Unicode`, `Date` from `Datetime`

`Unicode` outputs `str` but `ByteString` outputs `bytes`; `Datetime` outputs
`datetime` but `Date` outputs `date`. Each subclass contradicts its parent.
Today `def f(x: Unicode) -> str: return x.apply(v)` silently returns `bytes` for
a `ByteString`.

| Option | Pros | Cons |
|---|---|---|
| **A. Extract a shared private base** (`_BaseDecoder`, `_BaseDatetime`) | Fixes the unsoundness. `issubclass`/`isinstance` are restorable with `Unicode.register(ByteString)`, verified | Real refactor: both subclasses call `super()._apply`, and `Date` reuses `Datetime.__init__` |
| **B. Override `apply` with `# type: ignore[override]`** | One line, no refactor | Keeps a deliberate Liskov violation in the model this exercise exists to make trustworthy |

**Recommendation: A**, but B is defensible if v3.8.0's non-breaking shape is the
priority. With `register()` the `issubclass` objection dissolves, so A is no
longer a breaking change — only a larger one.

### Strictness

This is the decision that actually shapes the work. Measured on `a872e72` with
fresh caches:

| check | errors |
|---|---|
| `mypy --ignore-missing-imports src` | 47 |
| `mypy --strict --ignore-missing-imports src` | 278 |
| `mypy --strict --ignore-missing-imports src test` | 882 |
| `pyright src/filters` (standard) | 73 |
| `pyright src/filters` (strict) | 686 |

Both checkers are ~10× worse at full strictness, and the choice is not cosmetic:
`default=Any`'s justification only bites at strict, and the
`reportUnnecessaryTypeIgnoreComment` requirement below presumes a mode. Phase 0
must pick, per checker: fix everything, baseline and ratchet, or stage the flags.

## Prerequisites

1. **`src/filters/py.typed`.** No marker ships today, so every annotation is
   invisible downstream — `filters-pydantic` carries `# type: ignore[misc]` on
   `class PydanticModel(BaseFilter)` for this reason. Needs the file plus a hatch
   build include.
2. **A type checker in CI.** mypy is commented out of `[dependency-groups]`,
   `[tool.autohooks]`, `[tool.mypy]` and `[tool.tox]`.
3. **`typing_extensions`.** `TypeVar(default=)` is native from 3.13;
   `requires-python` is `>=3.12`. Bumping the floor instead is itself a breaking
   change, so it cannot ride in the v3.8.0 shape.
4. **A comment-placement carve-out in `AGENTS.md`.** The repo mandates comments on
   the preceding line, but `# type: ignore` and `# pyright: ignore` only work on
   the error line. The spike proved the failure mode: an ignore on the
   `@overload` decorator leaves the error reported on the `def` below it — and
   with `reportUnnecessaryTypeIgnoreComment` off by default, a misplaced ignore
   is silent.

## Testing inference

Runtime tests cannot see a regression from `FilterChain[str]` to
`FilterChain[Any]`, so this needs its own harness — a cross-cutting convention,
hence an ADR.

A `test/typing/` directory of modules using `typing.assert_type`, checked by
**both** mypy (what consumers run) and pyright (which diverges from mypy on
several constructs this design leans on). Four things it must get right:

- **Negative cases.** A wrong `assert_type` was confirmed to fail on both
  checkers. Assertions that a construct is *rejected* need `# type: ignore[...]`
  under `--warn-unused-ignores`, so a rule that silently stops firing fails the
  build.
- **Both comment dialects.** pyright ignores mypy error codes and vice versa.
  pyright's analogue of `--warn-unused-ignores` is
  `reportUnnecessaryTypeIgnoreComment`, **off by default even in strict** — not
  enabling it leaves the negative cases unguarded, the exact failure this
  section exists to prevent.
- **Runtime-safe negative cases.** The modules are collected by pytest, so a
  negative case that is also invalid at runtime crashes collection. Needs a
  stated rule.
- **No assertions on abstract `Type` arguments.** The checkers disagree:
  `Type(Mapping)` is `Type[Any]` under mypy and `Type[Mapping[_KT, _VT_co]]`
  under pyright. Neither errors, but asserting either fails the other — and the
  library has seven such internal call sites, so the resulting chain types
  differ between checkers.

## ADRs required

Per `AGENTS.md`, written before the change each governs.

1. Type parameter model — one parameter, `default=Any`, classic `TypeVar` over
   PEP 695, with the variance rationale.
2. Filter categories and the marker base classes.
3. Type checking in CI — mypy plus pyright, the strictness stance per checker,
   and the `assert_type` harness.

## Phases

| Phase | Scope | Size |
|---|---|---|
| **0** | `py.typed`; mypy and pyright in CI plus the strictness decision; `typing_extensions`; the `AGENTS.md` carve-out; `test/typing/` harness; fix `test.py:51`'s invalid `Callable[[...], ...]` and `resolve_filter`'s return type. | L |
| **1** | `base.py`: generic `BaseFilter`/`FilterChain`, category markers, **three** `__or__` overload sets, `Type`'s overloads, `FilterCompatible[T]`, `_filter`, `apply`, parameterised `__copy__`. | L |
| **2** | `number.py`, `string.py`, `simple.py`, `complex.py` — annotate every filter into its category. | L |
| **3** | `handlers.py` — generic `FilterRunner`. **Closes the issue.** | S |
| **4** | `macros.py`, `extensions.py`, `test.py`, `pytest.py`. | S |
| **5** | Optional: split `ByteString`/`Date` with `register()` to preserve `issubclass`. | S |
| **6** | Docs and README. | M |
| **7** | Downstream: paddock and `filters-pydantic` — code and skills. | M |

Two phase-boundary traps, both of which will otherwise red-line CI:

1. **Phases 1 and 2 are atomic under full strictness.** Once `BaseFilter` is
   generic, `disallow_any_generics` / `reportMissingTypeArgument` reject every
   unparameterised subclass in the package. Either they land in one commit, or
   Phase 0's strictness decision defers those flags.
2. **If Phase 5 is taken, phases 1–4 need interim suppressions that Phase 5
   deletes.** `ByteString` and `Date` fail the checkers as soon as the base is
   generic. Under `--warn-unused-ignores` the ignores must be added and removed
   in the right commits or the build breaks either side.

## Consumer impact

**paddock** — no source changes forced. The `cast()` calls in
`config/filters.py` can go once `_filter` is typed, and the skill's section on
narrowing `self._filter` needs rewriting to match `T | None`. `f.Type(dict)`,
`f.Type((str, Path))` and every bare-class chain keep working.

**filters-pydantic** — can drop `# type: ignore[misc]` from `PydanticModel` once
`py.typed` ships. `FilterField` becomes a candidate for `FilterField[T]`,
closing the gap its own docstring apologises for ("`phx-filters` chains have no
generic typing"). Its documented example
`FilterField(f.Required | f.Unicode | f.NotEmpty)` keeps working unchanged.

**`phx-filters-django` / `phx-filters-iso`** — checked both: every filter is an
unparameterised `BaseFilter` subclass and neither chains a bare class in code.
The `default=Any` typevar keeps them valid even for strict-mode consumers.
`filters-iso`'s three ``Required | Locale`` docstrings remain correct.

**`filters.ext` and `filter_macro`** — both depend on `FilterMeta.__or__`
(`create_instance` returns the class specifically so `filters.ext.MyFilter |
Other` works, and its docstring cites the metaclass by name; `macros.py:43`
returns `Unicode | Strip | NotEmpty`). Keeping the operator keeps both intact.
Macros stay opaque to type checkers and resolve to `Any` — a documented
limitation, not a regression.

## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*

- **`FilterMapper`, `FilterRepeater`, `FilterSwitch`, `Item`, `Omit`, `Pick`,
  `Array`, `JsonDecode` stay `BaseFilter[Any]`.** Their result types depend on
  runtime values or overridable class attributes. Accepted, not chased.
- **A narrowing category for `Required` is deferred**, not rejected.
- **`Type`'s overloads stop at 2-tuples.** `Type((str, int, float))` degrades to
  `Type[Any]` on both checkers; no 3-tuples exist in `src/` or `test/` today, so
  the arity is a "how many to write" call, not a defect.
- **`cleaned_data: T_out`** is typed optimistically on purpose; see above.

## Decisions for review

1. **Strictness, per checker** — fix everything, ratchet from a baseline, or
   stage the flags? This gates whether phases 1 and 2 can be separate commits,
   and it is now the largest single cost in the plan.
2. **Split `ByteString`/`Date` (A), or suppress (B)?** No longer a breaking
   change either way.
3. **`apply() -> T_out | None`** — forced by `_invalid_value`'s replacement path,
   but it makes every call site narrow. Should `Optional` get a narrowing
   overload so `Widening` doesn't hand `None` straight back?
4. **Does `f.Unicode | None` stay legal?** `FilterCompatible` allows it today;
   none of the proposed overloads do.
5. **`typing_extensions` as a runtime dependency** — the alternative, a 3.13
   floor, is itself breaking.
