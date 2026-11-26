"""
Tests that a filter instance keeps no state from one run to the next, so
filters shared between chains, mappers, repeaters and runners can't swap
errors or keys (issue #175, ADR 019).
"""

import copy
import threading
from collections.abc import Callable
from typing import Any, Optional

import pytest

import filters as f
from filters.base import ExceptionHandler

RUN_TIMEOUT = 2
"""Seconds a threaded test waits before it gives a run up as deadlocked."""


class Rendezvous(f.BaseFilter[str]):
    """Rejects an empty string, while a second run is part-way through
    this same filter.

    Each run waits for the other twice: before it checks its value, so
    both have been handed this filter by their own parents, and before it
    returns, so neither run finishes until both have reported.
    """

    CODE_EMPTY = "empty"

    templates = {
        CODE_EMPTY: "Empty value not allowed.",
    }

    def __init__(self) -> None:
        super().__init__()

        # Shared between runs on purpose: they are what make the runs meet.
        self.entered = threading.Barrier(2, timeout=RUN_TIMEOUT)
        self.reported = threading.Barrier(2, timeout=RUN_TIMEOUT)

    def _apply(self, value: str) -> str:
        self.entered.wait()

        try:
            if not value:
                return self._invalid_value(value, self.CODE_EMPTY)

            return value
        finally:
            self.reported.wait()


class Spy(f.BaseFilter[Any]):
    """Records where each run finds it."""

    def __init__(self) -> None:
        super().__init__()

        # Shared between runs on purpose: the tests read it afterwards.
        self.seen: list[tuple[Optional[f.BaseFilter[Any]], str]] = []

    def _apply(self, value: Any) -> Any:
        self.seen.append((self.parent, self.key))
        return value


def shared_text() -> f.FilterChain[str]:
    """Builds the chain every route below shares between two runs."""
    return f.Unicode | Rendezvous()


Route = tuple[f.BaseFilter[Any], f.BaseFilter[Any], Callable[[str], Any], str, str]
"""Two filters sharing a chain, how to wrap a value for them, and the key
each files that chain's errors under.
"""


def route_pipe_left() -> Route:
    """``|`` with the shared chain on the left, which copies its list."""
    shared = shared_text()
    return shared | f.MaxLength(5), shared | f.MaxLength(50), str, "", ""


def route_pipe_right() -> Route:
    """``|`` with the shared chain on the right, which nests it."""
    shared = shared_text()
    return f.NoOp | shared, f.Strip | shared, str, "", ""


def route_filter_mapper() -> Route:
    """Two ``FilterMapper`` instances holding the shared chain."""
    shared = shared_text()
    return (
        f.FilterMapper({"a": shared}),
        f.FilterMapper({"a": f.NoOp, "b": shared}),
        _both_keys,
        "a",
        "b",
    )


def route_filter_repeater() -> Route:
    """Two ``FilterRepeater`` instances holding the shared chain."""
    shared = shared_text()
    return f.FilterRepeater(shared), f.FilterRepeater(shared), _one_item, "0", "0"


def route_same_chain() -> Route:
    """One chain run by two ``FilterRunner`` instances."""
    chain = f.NoOp | shared_text()
    return chain, chain, str, "", ""


def route_same_mapper() -> Route:
    """One ``FilterMapper`` run by two ``FilterRunner`` instances."""
    mapper = f.FilterMapper({"a": shared_text()})
    return mapper, mapper, _both_keys, "a", "a"


def _both_keys(value: str) -> dict[str, str]:
    return {"a": value, "b": value}


def _one_item(value: str) -> list[str]:
    return [value]


ROUTES = [
    route_pipe_left,
    route_pipe_right,
    route_filter_mapper,
    route_filter_repeater,
    route_same_chain,
    route_same_mapper,
]


def run_together(
    runner_a: f.FilterRunner[Any],
    runner_b: f.FilterRunner[Any],
) -> None:
    """Runs both runners on their own threads, at the same time."""
    threads = [
        threading.Thread(target=runner.full_clean) for runner in (runner_a, runner_b)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(RUN_TIMEOUT)
        assert not thread.is_alive()


@pytest.mark.parametrize("route", ROUTES)
def test_per_run_state_threads_one_invalid(route: Callable[[], Route]) -> None:
    """An invalid run and a valid run sharing filters each get their own result."""
    filter_a, filter_b, wrap, key_a, _ = route()
    runner_a = f.FilterRunner(filter_a, wrap(""))
    runner_b = f.FilterRunner(filter_b, wrap("ok"))

    run_together(runner_a, runner_b)

    assert runner_a.error_codes == {key_a: [Rendezvous.CODE_EMPTY]}
    assert runner_b.error_codes == {}


@pytest.mark.parametrize("route", ROUTES)
def test_per_run_state_threads_both_invalid(route: Callable[[], Route]) -> None:
    """Two invalid runs sharing filters each file one error, under their own key."""
    filter_a, filter_b, wrap, key_a, key_b = route()
    runner_a = f.FilterRunner(filter_a, wrap(""))
    runner_b = f.FilterRunner(filter_b, wrap(""))

    run_together(runner_a, runner_b)

    assert runner_a.error_codes == {key_a: [Rendezvous.CODE_EMPTY]}
    assert runner_b.error_codes == {key_b: [Rendezvous.CODE_EMPTY]}


def test_per_run_state_nested_run_keeps_its_errors() -> None:
    """A run started and finished inside another, over the same filters, takes none of its errors."""

    class RunAgain(f.BaseFilter[str]):
        """Runs the chain holding it a second time, part-way through the first."""

        def _apply(self, value: str) -> str:
            if not inner_runners:
                inner_runners.append(f.FilterRunner(chain, "valid"))
                inner_runners[0].full_clean()

            return value

    inner_runners: list[f.FilterRunner[str]] = []
    chain = f.Unicode | RunAgain() | f.NotEmpty

    runner = f.FilterRunner(chain, "")

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}
    assert inner_runners[0].error_codes == {}
    assert inner_runners[0].cleaned_data == "valid"


@pytest.mark.parametrize("configured", [None, f.MemoryHandler()])
def test_per_run_state_runner_leaves_handler(
    configured: Optional[f.MemoryHandler],
) -> None:
    """A FilterRunner run leaves the filter's own handler as it found it."""
    chain = f.Unicode() | f.NotEmpty
    chain._handler = configured

    assert not f.FilterRunner(chain, "").is_valid()

    assert chain._handler is configured


def test_per_run_state_runner_leaves_shared_sub_filter_handler() -> None:
    """A FilterRunner on a filter another chain holds leaves its handler unset."""
    not_empty = f.NotEmpty()
    (f.Unicode | not_empty).set_handler(f.MemoryHandler())

    assert not f.FilterRunner(not_empty, "").is_valid()

    assert not_empty._handler is None


def test_per_run_state_runner_overrides_configured_handler() -> None:
    """A FilterRunner receives the errors of a chain that has its own handler."""
    configured = f.MemoryHandler()
    chain = (f.Unicode | f.NotEmpty).set_handler(configured)

    assert f.FilterRunner(chain, "").error_codes == {"": [f.NotEmpty.CODE_EMPTY]}
    assert configured.messages == {}


def held_by_mapper_then_built() -> f.BaseFilter[Any]:
    """A filter a ``FilterMapper`` holds but has not run."""
    not_empty = f.NotEmpty()
    f.FilterMapper({"a": not_empty})
    return not_empty


def held_by_mapper_then_run() -> f.BaseFilter[Any]:
    """A filter a ``FilterMapper`` holds and has run."""
    not_empty = f.NotEmpty()
    assert f.FilterRunner(f.FilterMapper({"a": not_empty}), {"a": "x"}).is_valid()
    return not_empty


def held_by_mapper_built_afterwards() -> f.BaseFilter[Any]:
    """A filter a chain holds, then a ``FilterMapper`` built later."""
    not_empty = f.NotEmpty()
    chain = f.Unicode | not_empty
    f.FilterMapper({"a": chain})
    return not_empty


STALE_KEY_SETUPS = [
    held_by_mapper_then_built,
    held_by_mapper_then_run,
    held_by_mapper_built_afterwards,
]


@pytest.mark.parametrize("setup", STALE_KEY_SETUPS)
def test_per_run_state_key_in_chain(setup: Callable[[], f.BaseFilter[Any]]) -> None:
    """A filter a mapper also holds files its errors under the chain's key, not the mapper's."""
    runner = f.FilterRunner(f.Unicode | setup(), "")

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}


@pytest.mark.parametrize("setup", STALE_KEY_SETUPS)
def test_per_run_state_key_run_directly(
    setup: Callable[[], f.BaseFilter[Any]],
) -> None:
    """A filter a mapper also holds files its errors under no key when a runner runs it."""
    runner = f.FilterRunner(setup(), "")

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}


@pytest.mark.parametrize("setup", STALE_KEY_SETUPS)
def test_per_run_state_key_plain_apply(
    setup: Callable[[], f.BaseFilter[Any]],
) -> None:
    """A filter a mapper also holds files its errors under no key when applied directly."""
    with pytest.raises(f.FilterError) as exc_info:
        setup().apply("")

    assert exc_info.value.context["key"] == ""


def test_per_run_state_parent_and_key_follow_the_run() -> None:
    """A shared filter's parent and key are those of the run applying it."""
    spy = Spy()
    mapper = f.FilterMapper({"a": f.FilterRepeater(spy)})
    chain = f.NoOp | spy

    mapper.apply({"a": ["x"]})
    chain.apply("x")
    spy.apply("x")

    assert [key for _, key in spy.seen] == ["a.0", "", ""]
    assert isinstance(spy.seen[0][0], f.FilterRepeater)
    assert spy.seen[1][0] is chain
    assert spy.seen[2][0] is None


def test_per_run_state_parent_and_key_outside_a_run() -> None:
    """Outside apply(), a filter has no parent, key or error flag, whatever holds it."""
    not_empty = f.NotEmpty()
    mapper = f.FilterMapper({"a": not_empty})
    assert not f.FilterRunner(mapper, {"a": ""}).is_valid()

    assert not_empty.parent is None
    assert not_empty.key == ""
    assert not not_empty._has_errors
    assert not mapper._has_errors


def test_per_run_state_parent_and_key_are_read_only() -> None:
    """Assigning a parent or key raises, because neither is the filter's to keep."""
    not_empty = f.NotEmpty()

    with pytest.raises(AttributeError):
        not_empty.parent = f.NoOp()  # type: ignore[misc]

    with pytest.raises(AttributeError):
        not_empty.key = "a"  # type: ignore[misc]


def test_per_run_state_recursive_filter() -> None:
    """A filter that applies itself keeps a separate key and error flag at each depth."""

    class Tree(f.BaseFilter[Any]):
        """A node: a non-empty ``name`` and a list of child nodes."""

        def _apply(self, value: Any) -> Any:
            return self._filter(
                value,
                f.FilterMapper(
                    {
                        "children": f.FilterRepeater(self),
                        "name": f.Required | f.Unicode | f.NotEmpty,
                    }
                ),
            )

    tree = {
        "children": [
            {"children": [], "name": "ok"},
            {"children": [{"children": [], "name": ""}], "name": "ok"},
        ],
        "name": "",
    }

    assert f.FilterRunner(Tree(), tree).error_codes == {
        "children.1.children.0.name": [f.NotEmpty.CODE_EMPTY],
        "name": [f.NotEmpty.CODE_EMPTY],
    }


def test_per_run_state_direct_apply_starts_its_own_run() -> None:
    """A filter applied with apply() inside another's _apply takes no key or handler from it."""

    class Direct(f.BaseFilter[Any]):
        """Applies ``NotEmpty`` without going through ``_filter``."""

        def _apply(self, value: Any) -> Any:
            try:
                return f.NotEmpty().apply(value)
            except f.FilterError as e:
                contexts.append(dict(e.context))
                raise

    contexts: list[dict[str, Any]] = []
    runner = f.FilterRunner(f.FilterMapper({"a": Direct()}), {"a": ""})

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}
    assert contexts[0]["key"] == ""


def test_per_run_state_overridden_apply_joins_the_run() -> None:
    """A filter that overrides apply() still reports under its parent's key and handler."""

    class Loud(f.Unicode):
        """Overrides ``apply``, as a filter that wraps every call might."""

        def apply(self, value: Any) -> Optional[str]:
            return super().apply(value)

    runner = f.FilterRunner(f.FilterMapper({"a": Loud() | f.NotEmpty}), {"a": b"\xff"})

    assert runner.error_codes == {"a": [f.Unicode.CODE_DECODE_ERROR]}


def test_per_run_state_iter_outside_apply_uses_configured_handler() -> None:
    """FilterRepeater.iter() called directly sends item errors to the repeater's own handler."""
    handler = f.MemoryHandler()
    repeater = f.FilterRepeater(f.NotEmpty).set_handler(handler)
    assert isinstance(repeater, f.FilterRepeater)

    assert list(repeater.iter(["x", ""])) == ["x", None]
    assert {key: [m.code for m in msgs] for key, msgs in handler.messages.items()} == {
        "1": [f.NotEmpty.CODE_EMPTY],
    }


def test_per_run_state_apply_with_handler() -> None:
    """apply_with_handler() sends one call's errors to its handler and leaves the filter alone."""
    configured = f.MemoryHandler()
    handler = f.MemoryHandler()
    chain = (f.Unicode | f.NotEmpty).set_handler(configured)

    assert chain.apply_with_handler("", handler) is None

    assert list(handler.messages) == [""]
    assert configured.messages == {}
    assert chain._handler is configured


def test_per_run_state_apply_with_handler_nested_handler_wins() -> None:
    """A nested filter with its own handler keeps it under apply_with_handler()."""
    nested = f.MemoryHandler()
    handler = f.MemoryHandler()
    chain = f.Unicode | f.NotEmpty().set_handler(nested)

    assert chain.apply_with_handler("", handler) is None

    assert list(nested.messages) == [""]
    assert handler.messages == {}


def test_per_run_state_handler_outside_a_run() -> None:
    """Outside apply(), a filter's handler is its own or the default, never a holder's."""
    not_empty = f.NotEmpty()
    chain = (f.Unicode | not_empty).set_handler(f.MemoryHandler())

    assert isinstance(not_empty.handler, ExceptionHandler)
    assert chain.handler is chain._handler


def test_per_run_state_copy_keeps_handler() -> None:
    """Copying a filter keeps its configured handler, the only state BaseFilter stores."""
    handler = f.MemoryHandler()
    not_empty = f.NotEmpty().set_handler(handler)

    copied = copy.copy(not_empty)

    assert vars(copied) == vars(not_empty)
    assert copied.handler is handler
