"""
Smoke test for the static type-checking harness (issue #34).

Modules here use ``typing.assert_type`` to pin the exact type mypy and
pyright infer for a filter or chain -- a regression here (e.g.
``FilterChain[str]`` silently degrading to ``FilterChain[Any]``) is invisible
to a runtime test. Both checkers run against this directory in CI, under
``--warn-unused-ignores``/``reportUnnecessaryTypeIgnoreComment`` (see
docs/adr/004-type-checking-in-ci.md), so an ignore that stops being needed
fails the build rather than silently going stale.

Rule for negative cases (asserting a construct is *rejected*): guard the
rejected line with ``# type: ignore[code]`` and, where the two checkers
disagree on the code, its ``# pyright: ignore[code]`` twin -- never with a
construct that is also invalid at runtime. pytest collects every module in
this directory as an ordinary test module, so a case that raises on import
(instead of merely failing a type checker) crashes collection for the whole
file rather than reporting one failing assertion.
"""

from typing import Optional, assert_type

import filters as f


def test_smoke_set_handler_return_type_is_base_filter() -> None:
    """``BaseFilter.set_handler`` is explicitly annotated, pre-Phase-1.

    Proves the harness and its CI wiring work end to end against a
    construct where mypy and pyright already agree, before Phase 1 makes
    the interesting cases (chain inference) possible to write.
    """
    assert_type(
        f.Unicode().set_handler(f.ExceptionHandler()),
        f.BaseFilter,
    )


def test_smoke_resolve_filter_return_type_is_optional_base_filter() -> None:
    """``BaseFilter.resolve_filter`` returns the resolved filter, not a chain.

    Regression check for the Phase 0 fix to its declared return type
    (previously ``Optional[FilterChain]``, which mypy flagged as wrong).
    """
    assert_type(
        f.BaseFilter.resolve_filter(f.Unicode()),
        Optional[f.BaseFilter],
    )
