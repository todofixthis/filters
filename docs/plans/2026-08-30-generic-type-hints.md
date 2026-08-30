# Plan: Generic Type Hints for Filters (issue #34)

**Issue:** [#34 — Add generic type hints](https://github.com/todofixthis/filters/issues/34)
**Branch:** `claude/issue-34-planning-ma47i5`
**Status:** Awaiting review — no code changes made yet.

## Goal

Parameterise the filter hierarchy so a type checker can infer a chain's output
type, making `FilterRunner(...).cleaned_data` and `FilterChain.apply()` return
something better than `Any`.

Note the issue text says `FilterRunner(...).apply()`. That method returns
`None` — it only resets cached state. The inference target is
`FilterRunner.cleaned_data` (and `BaseFilter.apply` on a chain).

## Evidence

Every claim below was tested against mypy 1.19.1 and pyright 1.1.408. Findings
that contradict the issue's assumptions are marked ⚠.

| Question | Result |
|---|---|
| Can a type checker see `FilterMeta.__or__`? | **No.** Both checkers evaluate `Unicode \| NotEmpty` as a PEP 604 union and report `types.UnionType`. Neither raises a diagnostic. The metaclass operator is invisible to typing, however it is annotated. |
| Does a `cls: type[BaseFilter[...]]` self-type on the metaclass rescue it? | **No.** pyright rejects it outright (`Type of parameter "cls" must be a supertype of its class`); mypy warns and only handles the mixed `Class \| instance()` form. |
| ⚠ Must `Type.__init__` require a tuple? | **No.** Overloads resolve `Type(str)` → `Type[str]` and `Type((str, int))` → `Type[str \| int]` on both checkers. This breaking change is not forced. |
| Do the `Type` overloads cope with abstract arguments? | **Only with a bare-`type` fallback overload.** `type[T]` alone makes `Type(Iterable)` a mypy `type-abstract` error and a pyright "no overloads match" error — and the library itself calls `Type(Iterable)`, `Type(Sized)` and `Type(Mapping)` five times. Adding `type` and `tuple[type, ...]` fallbacks clears both. |
| Does a bare class on the *right* of `\|` still infer? | **Yes.** `Unicode() \| NotEmpty` works via a `type[BaseFilter[...]]` overload. Only the left-hand position is lost. |
| Does `BaseFilter[T, T]` express a pass-through filter? | **Not portably.** mypy solves `T` from call context; pyright leaves it `Unknown`. A non-generic marker base works on both. |
| Can `ByteString(Unicode)` and `Date(Datetime)` keep their base classes? | **No.** Both invert the output type (`bytes` is not a `str`; `date` is not a `datetime`). Both checkers reject the re-parameterisation as mutually incompatible bases. |
| Does `Generic` break the Sphinx build? | **No.** A spike adding `Generic[T_in, T_out]`, `@overload`ed `__or__` and a parameterised `Type` to `base.py` built clean (1 pre-existing intersphinx warning) and passed all 551 tests. |
| PEP 695 (`class BaseFilter[T_in, T_out]`) or classic `TypeVar`? | **Classic.** mypy parses PEP 695 with the host interpreter's parser, so a consumer running mypy on Python < 3.12 cannot even parse our source. |

## Prerequisites (none of this reaches a consumer without them)

1. **`src/filters/py.typed`.** The package ships no marker, so every annotation
   we add is invisible downstream today. `filters-pydantic` carries
   `# type: ignore[misc]` on `class PydanticModel(BaseFilter)` for exactly this
   reason. Needs the file plus a `[tool.hatch.build]` include.
2. **A type checker in CI.** mypy is commented out of `[dependency-groups]`,
   `[tool.autohooks]`, `[tool.mypy]` and `[tool.tox]`. Generic inference that
   nothing verifies will rot within a release.
3. **An inference test harness.** Runtime tests cannot catch a regression from
   `FilterChain[Any, str]` to `FilterChain[Any, Any]`. See "Testing inference".

## Type model

```python
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")

class BaseFilter(Generic[T_in, T_out], metaclass=FilterMeta): ...
class FilterChain(BaseFilter[T_in, T_out]): ...
```

Two parameters, both invariant. `T_in` earns its place because pass-through
filters must express "output type equals input type"; with a single output
parameter, `f.Unicode | f.NotEmpty` collapses to `Any` — and that is paddock's
single most common chain shape.

Filters fall into three categories, distinguished by a base class so that
`__or__` can be overloaded on them:

| Category | Base | Members | Chain effect |
|---|---|---|---|
| Transforming | `BaseFilter[Any, T]` | `Unicode`, `Int`, `Uuid`, `Split`, `NamedTuple`, … | Output becomes `T` |
| Pass-through | `PassThroughFilter` | `NotEmpty`, `Required`, `Min`, `Max`, `MinLength`, `MaxLength`, `Len`, `Length`, `NoOp`, `Empty`, `Choice` | Output unchanged |
| Widening | `WideningFilter[D]` | `Optional` | Output becomes `T_out \| D` |

`BaseFilter.__or__` gets one overload pair (instance, class) per category — six
in total, plus the runtime implementation.

## Breaking changes

### 1. Bare-class chaining: `f.Unicode | f.Strip`

This is the only change the typing goal genuinely forces. It is also the most
widely used idiom: 176 chain heads across this repo's tests, docs and README,
and every schema entry in paddock.

An important wrinkle: `FilterMeta.__or__` cannot simply be deleted.
`Unicode | Strip` with no metaclass operator falls through to `type.__or__` and
returns a **`types.UnionType`, silently**. The failure surfaces much later, deep
in `resolve_filter`, as `TypeError: UnionType ... is not compatible with ...`.
The mixed form `Unicode | Strip()` fails immediately but with the generic
`unsupported operand type(s)` message.

**Options**

| Option | Pros | Cons |
|---|---|---|
| **A. Delete `FilterMeta.__or__`** | Simplest diff | Silent `UnionType` at the definition site; cryptic failure far away |
| **B. Keep it working, annotate as `FilterChain[Any, Any]`** | Nothing breaks | Chains starting with a bare class type as `UnionType`, so consumers get a type error at every use site on code that runs fine — the worst of both |
| **C. Guarded raise** (recommended mechanism) | Fails loudly at the definition site with a message naming the fix; `Unicode \| None` and other genuine PEP 604 unions still work, because a non-filter right-hand operand returns `NotImplemented` | Still a hard break |
| **D. Deprecate, then C** (recommended timing) | Gives PyPI consumers a runtime signal before the break | One extra release |

```python
def __or__(cls, next_filter):
    if isinstance(next_filter, (BaseFilter, FilterMeta)):
        raise TypeError(
            f"Cannot chain filter classes with `|`. Instantiate them first: "
            f"{cls.__name__}() | ..."
        )
    # Not a filter — let Python build an ordinary PEP 604 union.
    return NotImplemented
```

**Recommendation: D → C.** Ship v3.8.0 as a pure-deprecation release where
`FilterMeta.__or__` still returns a chain but emits a `DeprecationWarning`, then
the guarded raise in v4.0.0. The deprecation costs roughly fifteen lines and one
release; the sugar is idiomatic enough (248 bare-class pipe operands in this repo alone)
that unknown downstream users deserve the warning. Collapse D into C if you'd
rather not spend the release.

Note what is *not* lost: `f.Unicode() | f.Strip` still works and still infers.
Only the leftmost operand must be instantiated.

### 2. `Type.__init__` requiring a tuple

⚠ **Recommendation: don't do this.** Overloads handle the scalar form on both
checkers, so `f.Type(bool)` and `f.Type(dict)` can stay:

```python
@overload
def __init__(self: "Type[T1]", allowed_types: type[T1]) -> None: ...
@overload
def __init__(self: "Type[T1]", allowed_types: tuple[type[T1]]) -> None: ...
# ... arities 2 and 3 ...
# Fallbacks: abstract classes and longer tuples degrade to Type[Any]
# rather than erroring.
@overload
def __init__(self: "Type[Any]", allowed_types: type) -> None: ...
@overload
def __init__(self: "Type[Any]", allowed_types: tuple[type, ...]) -> None: ...
```

The two fallback overloads are load-bearing, not defensive. Without the bare
`type` one, `Type(Iterable)` is a mypy `type-abstract` error and a pyright
"no overloads match" error — and the library itself passes abstract classes to
`Type` five times (`simple.py:170,518,575`, `complex.py:80,270`), as do the
public docs (`f.Type(Sequence)`). With both fallbacks, mypy reports no errors at
all and pyright reports only a declaration-site `reportOverlappingOverload`,
suppressible in our source and invisible to consumers.

Degradations, both silent and both preferable to a break: a tuple longer than
the enumerated arities resolves to `Type[Any]`, and abstract arguments resolve
to `Type[Any]` under mypy but to the ABC itself under pyright. The inference
tests must not assert on abstract arguments, since the checkers disagree.

### 3. `ByteString(Unicode)` and `Date(Datetime)`

Not mentioned in the issue, and forced. `Unicode` outputs `str` but `ByteString`
outputs `bytes`; `Datetime` outputs `datetime` but `Date` outputs `date`. Each
subclass therefore inverts its parent's output type, which no variance
annotation can express — both checkers reject it.

**Options**

| Option | Pros | Cons |
|---|---|---|
| **A. Extract a shared private base** (`_BaseDecoder`, `_BaseDatetime`) and have both siblings inherit from it | Type-correct; keeps the shared `__init__` and helper logic in one place | `issubclass(f.ByteString, f.Unicode)` becomes `False` — a silent behavioural break for anyone dispatching on it |
| **B. Duplicate the shared logic** | Same as A for typing | Also breaks `issubclass`, and duplicates code |
| **C. `# type: ignore` the override** | No API change | Both checkers reject it as *mutually incompatible bases*, not a suppressible override error — this does not actually work |

**Recommendation: A.** C is not available, and A keeps the code in one place.
Call out the `issubclass` change in the v4.0.0 release notes; it is unlikely but
not impossible that someone depends on it.

`Array(Type)` is fine — `Array` narrows to `Sequence`, which is a legitimate
covariant narrowing.

### 4. `_filter()`'s return type

`BaseFilter._filter` returns `Any` today, and paddock's phx-filters skill
documents `cast()`-ing every call site. Once the chain argument is typed we can
return `T | None` — the `None` is real, since `_invalid_value` returns the
replacement value (usually `None`) on failure.

**Recommendation: `T | None`.** Honest, and it lets custom-filter authors drop
the `cast` import in favour of a narrowing check they should be doing anyway.
The alternative — returning `T` because `_has_errors` is checked immediately
after — reads better at the call site but lies on the error path, and the lie is
invisible.

This changes paddock's documented idiom, so its skill needs updating in step.

### 5. `FilterRunner.cleaned_data`

`FilterRunner` becomes `FilterRunner[T_out]`, resolved from `starting_filter`
via overloads (instance / class / zero-arg callable / `None` → `Any`). Verified
working on both checkers.

The remaining choice is whether `cleaned_data` returns `T_out` or
`T_out | None`. `T_out` matches the documented usage (check `is_valid()` first,
then read); `T_out | None` is honest but forces a narrow at every call site
including the guarded ones. **Recommendation: `T_out`**, since the guard is
already the documented contract and the property is the whole point of the
issue. Flagging it as a decision because it is the inverse of the call made for
`_filter` above — the difference is that `is_valid()` is a public, documented
gate whereas `_has_errors` is internal.

## Non-breaking friction

- **`filters.Optional` shadows `typing.Optional`.** `simple.py` currently
  imports neither, but annotating that module means using `X | None` there while
  the repo's Sphinx rule mandates `typing.Optional` for string forward
  references. Resolve with `import typing` and a qualified `typing.Optional`
  where a forward reference is involved.
- **`filter_macro` is opaque to type checkers.** It builds a class inside a
  function via a metaclass that overrides `__call__`. Nothing static can follow
  it. Macros will resolve to `Any`. Leave as-is and document the limitation.
- **`ext` registry.** `FilterExtensionRegistry.__getattr__` is inherently
  dynamic; `f.ext.Country` stays `type[BaseFilter[Any, Any]]`. Acceptable.
- **`BaseFilter.__copy__` is a `classmethod`** taking the filter as an argument,
  with an existing `# noinspection PyTypeChecker` in `FilterChain.__copy__`.
  It will fight `Self` typing. Expect to rework it into a conventional
  `def __copy__(self) -> Self`.
- **`test.py:51` — `filter_type: Callable[[...], BaseFilter]`.** `[...]` is not
  valid typing syntax; a checker will reject it on day one. Should be
  `Callable[..., BaseFilter[Any, Any]]`.
- **`FilterRepeater`'s output is `list` or `dict`** depending on the input.
  Best available is `list[T] | dict[Any, T]`. `FilterMapper` resolves to
  `dict[str, Any]`; precise per-key inference would need PEP 728 and is not
  worth chasing.

## Testing inference

Runtime tests cannot see a type regression, so this needs its own harness — a
new cross-cutting convention, and therefore an ADR.

Proposal: a `test/typing/` directory of modules using `typing.assert_type`,
checked in CI by **both** mypy (matching what consumers run) and pyright (which
diverges from mypy on exactly the constructs this design depends on). The
modules import cleanly at runtime, so pytest collects them for free.

Negative cases matter as much as positive ones: assert that `f.Int() | f.Unicode`
is rejected where it should be, using `# type: ignore[...]` under
`--warn-unused-ignores`, so a rule that silently stops firing fails the build
rather than passing quietly.

## ADRs required

Per `AGENTS.md`, each of these must be written before the change it governs.

1. Generic type parameter model — two parameters, invariant, classic `TypeVar`
   over PEP 695, with the mypy-parser rationale.
2. Filter categories and the pass-through / widening marker bases.
3. Retiring bare-class `|` chaining, including the guarded-raise mechanism and
   the deprecation release.
4. Type checking in CI — mypy plus pyright, strictness, and the `assert_type`
   harness.
5. Splitting the `ByteString` / `Date` inheritance chains.

## Phases

Sizes are relative, not estimates.

| Phase | Scope | Breaking | Size |
|---|---|---|---|
| **0** | `py.typed`; re-enable mypy; add pyright; `test/typing/` harness; fix `test.py:51`. Ships as **v3.8.0** with the `FilterMeta.__or__` deprecation warning. | No | M |
| **1** | `base.py`: `Generic` bases, category markers, `__or__` overloads, `Type` overloads, `FilterCompatible`, `resolve_filter`, `_filter`, `__copy__`. | Yes | L |
| **2** | `number.py`, `string.py`, `simple.py` — annotate each filter into its category. | No | L |
| **3** | Split `ByteString` / `Date` from their parents. | Yes | S |
| **4** | `complex.py` — `FilterMapper`, `FilterRepeater`, `FilterSwitch`, `NamedTuple`. | No | M |
| **5** | `handlers.py` — generic `FilterRunner`. **This is the phase that closes the issue.** | No | S |
| **6** | `macros.py`, `extensions.py`, `test.py`, `pytest.py`. | No | S |
| **7** | Migrate 176 chain heads in tests, docs and README; write the v4 upgrade guide. | — | L |
| **8** | Downstream: paddock and `filters-pydantic` — code, and their `phx-filters` skills. | — | M |

Phase 1 lands the whole type model at once because `__or__`'s overloads,
the category markers and `FilterChain` are mutually dependent; splitting them
leaves the tree unbuildable.

Phases 1–7 ship together as **v4.0.0**.

## Consumer impact

**paddock** — every entry in `_config_schema`, `_build_schema` and `_env_schema`
starts with a bare class, so each needs `()` added. `f.Type(dict)` and
`f.Type((str, Path))` both survive under the recommendation. The `cast()` calls
in `config/filters.py` can go once `_filter` is typed. Its `phx-filters` skill
documents bare-class chaining as correct and must be rewritten.

**filters-pydantic** — can drop `# type: ignore[misc]` from `PydanticModel` once
`py.typed` ships. `FilterField` becomes a candidate for
`FilterField[T]`, closing the gap its own docstring apologises for
("`phx-filters` chains have no generic typing"). Its skill's example
`FilterField(f.Required | f.Unicode | f.NotEmpty)` breaks.

**`phx-filters-django` / `phx-filters-iso`** — checked both: every filter is an
unparameterised `BaseFilter` subclass, which stays valid as implicit `Any`, and
neither chains a bare class in code. `filters-iso` has three docstrings reading
``Required | Locale`` and the like, which want tidying but break nothing.
Follow-up work, not blocking.

## Decisions for review

1. **Deprecation release?** D (v3.8.0 warning, then v4.0.0 raise) or straight
   to C.
2. **Keep `Type`'s scalar sugar?** The recommendation contradicts the issue.
3. **`cleaned_data: T_out` or `T_out | None`?**
4. **`_filter() -> T | None`** — confirmed, given it changes paddock's idiom.
5. **`issubclass(f.ByteString, f.Unicode)` becoming `False`** — acceptable?
6. **pyright in CI alongside mypy**, or mypy alone? The design leans on
   constructs where the two diverge.
