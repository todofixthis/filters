"""
Tests that a filter instance keeps no state from one run to the next, so
filters shared between chains, mappers, repeaters and runners can't swap
errors or keys (issue #175, ADR 019).
"""

import contextvars
import copy
import threading
import typing
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


class Holder(f.BaseFilter[Any]):
    """Stores a child filter and applies it under the key ``held``."""

    def __init__(self, child: f.FilterCompatible[Any]) -> None:
        super().__init__()

        self.child = self.resolve_filter(child)

    def _apply(self, value: Any) -> Any:
        return self._filter(value, self.child, sub_key="held")


class OneField(typing.NamedTuple):
    """The namedtuple type the ``NamedTuple`` route builds."""

    a: str


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


def route_filter_switch() -> Route:
    """Two ``FilterSwitch`` instances with the shared chain as a case."""
    shared = shared_text()
    return (
        f.FilterSwitch(len, {0: shared, 2: shared}),
        f.FilterSwitch(len, {}, default=shared),
        str,
        "",
        "",
    )


def route_named_tuple() -> Route:
    """Two ``NamedTuple`` instances whose mappers hold the shared chain."""
    shared = shared_text()
    return (
        f.NamedTuple(OneField, {"a": shared}),
        f.NamedTuple(OneField, {"a": shared}),
        _one_item,
        "a",
        "a",
    )


def route_stored_child() -> Route:
    """Two custom filters that each store the shared chain as a child."""
    shared = shared_text()
    return Holder(shared), Holder(shared), str, "held", "held"


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
    route_filter_switch,
    route_named_tuple,
    route_stored_child,
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
    """An invalid and a valid run sharing filters each get their own result."""
    filter_a, filter_b, wrap, key_a, _ = route()
    runner_a = f.FilterRunner(filter_a, wrap(""))
    runner_b = f.FilterRunner(filter_b, wrap("ok"))

    run_together(runner_a, runner_b)

    assert runner_a.error_codes == {key_a: [Rendezvous.CODE_EMPTY]}
    assert runner_b.error_codes == {}


@pytest.mark.parametrize("route", ROUTES)
def test_per_run_state_threads_both_invalid(route: Callable[[], Route]) -> None:
    """Two invalid runs sharing filters each file one error, under its key."""
    filter_a, filter_b, wrap, key_a, key_b = route()
    runner_a = f.FilterRunner(filter_a, wrap(""))
    runner_b = f.FilterRunner(filter_b, wrap(""))

    run_together(runner_a, runner_b)

    assert runner_a.error_codes == {key_a: [Rendezvous.CODE_EMPTY]}
    assert runner_b.error_codes == {key_b: [Rendezvous.CODE_EMPTY]}


def test_per_run_state_nested_run_keeps_its_errors() -> None:
    """A run nested in another over the same filters takes no errors from it."""

    class RunAgain(f.BaseFilter[str]):
        """Runs the chain that holds it again, part-way through a run."""

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
    """A runner on a filter another chain holds leaves its handler unset."""
    not_empty = f.NotEmpty()
    (f.Unicode | not_empty).set_handler(f.MemoryHandler())

    assert not f.FilterRunner(not_empty, "").is_valid()

    assert not_empty._handler is None


def test_per_run_state_runner_overrides_configured_handler() -> None:
    """A runner receives the errors of a chain that has its own handler."""
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
    """A filter a mapper also holds reports under the chain's key."""
    runner = f.FilterRunner(f.Unicode | setup(), "")

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}


@pytest.mark.parametrize("setup", STALE_KEY_SETUPS)
def test_per_run_state_key_run_directly(
    setup: Callable[[], f.BaseFilter[Any]],
) -> None:
    """A filter a mapper also holds reports under no key under a runner."""
    runner = f.FilterRunner(setup(), "")

    assert runner.error_codes == {"": [f.NotEmpty.CODE_EMPTY]}


@pytest.mark.parametrize("setup", STALE_KEY_SETUPS)
def test_per_run_state_key_plain_apply(
    setup: Callable[[], f.BaseFilter[Any]],
) -> None:
    """A filter a mapper also holds reports under no key on a plain apply()."""
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
    """Outside apply(), a filter has no parent, key or error flag."""
    not_empty = f.NotEmpty()
    mapper = f.FilterMapper({"a": not_empty})
    assert not f.FilterRunner(mapper, {"a": ""}).is_valid()

    assert not_empty.parent is None
    assert not_empty.key == ""
    assert not not_empty._has_errors
    assert not mapper._has_errors


def test_per_run_state_parent_and_key_are_read_only() -> None:
    """Assigning a parent or key raises: neither is the filter's to keep."""
    not_empty = f.NotEmpty()

    with pytest.raises(AttributeError):
        # mypy rejects the assignment this test makes on purpose.
        not_empty.parent = f.NoOp()  # type: ignore[misc]

    with pytest.raises(AttributeError):
        # mypy rejects the assignment this test makes on purpose.
        not_empty.key = "a"  # type: ignore[misc]


def test_per_run_state_recursive_filter() -> None:
    """A filter that applies itself keeps its own key at each depth."""

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
    """apply() inside another filter's _apply takes no key or handler."""

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
    """A filter that overrides apply() still reports under its parent's key."""

    class Loud(f.Unicode):
        """Overrides ``apply``, as a filter that wraps every call might."""

        def apply(self, value: Any) -> Optional[str]:
            return super().apply(value)

    runner = f.FilterRunner(f.FilterMapper({"a": Loud() | f.NotEmpty}), {"a": b"\xff"})

    assert runner.error_codes == {"a": [f.Unicode.CODE_DECODE_ERROR]}


def test_per_run_state_iter_outside_apply_uses_configured_handler() -> None:
    """iter() called directly reports to the repeater's own handler."""
    handler = f.MemoryHandler()
    repeater = f.FilterRepeater(f.NotEmpty).set_handler(handler)
    assert isinstance(repeater, f.FilterRepeater)

    assert list(repeater.iter(["x", ""])) == ["x", None]
    assert {key: [m.code for m in msgs] for key, msgs in handler.messages.items()} == {
        "1": [f.NotEmpty.CODE_EMPTY],
    }


def test_per_run_state_apply_with_handler() -> None:
    """apply_with_handler() takes one call's errors and leaves the filter be."""
    configured = f.MemoryHandler()
    handler = f.MemoryHandler()
    chain = (f.Unicode | f.NotEmpty).set_handler(configured)

    assert chain.apply_with_handler("", handler) is None

    assert list(handler.messages) == [""]
    assert configured.messages == {}
    assert chain._handler is configured


def test_per_run_state_apply_with_handler_nested_handler_wins() -> None:
    """A nested filter's own handler wins under apply_with_handler()."""
    nested = f.MemoryHandler()
    handler = f.MemoryHandler()
    chain = f.Unicode | f.NotEmpty().set_handler(nested)

    assert chain.apply_with_handler("", handler) is None

    assert list(nested.messages) == [""]
    assert handler.messages == {}


def test_per_run_state_handler_outside_a_run() -> None:
    """Outside apply(), a filter's handler is its own, never a holder's."""
    not_empty = f.NotEmpty()
    chain = (f.Unicode | not_empty).set_handler(f.MemoryHandler())

    assert isinstance(not_empty.handler, ExceptionHandler)
    assert chain.handler is chain._handler


def test_per_run_state_copy_keeps_handler() -> None:
    """Copying a filter keeps its handler, all the state BaseFilter stores."""
    handler = f.MemoryHandler()
    not_empty = f.NotEmpty().set_handler(handler)

    copied = copy.copy(not_empty)

    assert vars(copied) == vars(not_empty)
    assert copied.handler is handler


def test_per_run_state_ancestor_state_while_child_runs() -> None:
    """A filter keeps its key and handler while a child it applies runs."""

    class ReadsParent(f.BaseFilter[Any]):
        """Records what its parent reports while this filter runs."""

        def _apply(self, value: Any) -> Any:
            parent = self.parent
            assert parent is not None
            seen.append((parent.key, parent.handler))
            return value

    seen: list[tuple[str, f.BaseInvalidValueHandler]] = []
    handler = f.MemoryHandler()

    f.FilterMapper({"a": f.FilterRepeater(ReadsParent())}).apply_with_handler(
        {"a": ["x"]},
        handler,
    )

    assert seen == [("a", handler)]


def test_per_run_state_callback_into_ancestor() -> None:
    """A callback a child runs reports under the key of the filter it is on."""

    class Checks(f.BaseFilter[Any]):
        """Hands a child a bound method that calls back into this filter."""

        CODE_ODD = "odd"

        templates = {
            CODE_ODD: "Odd.",
        }

        def _apply(self, value: Any) -> Any:
            result = self._filter(value, f.Call(self._check))
            flags.append(self._has_errors)
            return result

        def _check(self, value: Any) -> Any:
            return self._invalid_value(value, self.CODE_ODD)

    flags: list[bool] = []
    runner = f.FilterRunner(f.FilterMapper({"a": Checks()}), {"a": 1})

    assert runner.error_codes == {"a": [Checks.CODE_ODD]}
    assert flags == [True]


def test_per_run_state_iter_inside_another_filter() -> None:
    """iter() inside another filter's _apply reports under that filter's key."""

    class Iterates(f.BaseFilter[Any]):
        """Consumes a mapper through ``iter()`` instead of ``_filter``."""

        def _apply(self, value: Any) -> Any:
            return dict(f.FilterMapper({"x": f.NotEmpty}).iter(value))

    runner = f.FilterRunner(f.FilterMapper({"a": Iterates()}), {"a": {"x": ""}})

    assert runner.error_codes == {"a.x": [f.NotEmpty.CODE_EMPTY]}
    assert runner.cleaned_data == {"a": {"x": None}}


def test_per_run_state_filter_applies_itself() -> None:
    """A filter that calls its own apply() keeps the run's key and handler."""

    class Nested(f.BaseFilter[Any]):
        """Rejects an empty string, at any depth of nested lists."""

        CODE_BAD = "bad"

        templates = {
            CODE_BAD: "Bad.",
        }

        def _apply(self, value: Any) -> Any:
            if isinstance(value, list):
                return [self.apply(item) for item in value]

            return value if value else self._invalid_value(value, self.CODE_BAD)

    runner = f.FilterRunner(f.FilterMapper({"a": Nested()}), {"a": ["x", "", ["y"]]})

    assert runner.error_codes == {"a": [Nested.CODE_BAD]}
    assert runner.cleaned_data == {"a": ["x", None, ["y"]]}


def test_per_run_state_overridden_apply_called_twice() -> None:
    """An apply() that calls the base twice reports both calls under its key."""

    class Twice(f.NotEmpty):
        """Applies the base filter to each half of a pair."""

        def apply(self, value: Any) -> Any:
            return [super().apply(value[0]), super().apply(value[1])]

    runner = f.FilterRunner(f.FilterMapper({"a": Twice()}), {"a": ["", ""]})

    assert runner.error_codes == {"a": [f.NotEmpty.CODE_EMPTY] * 2}


def run_on_thread(func: Callable[[], Any]) -> list[Any]:
    """Calls ``func`` on another thread, returning its result or exception."""

    def target() -> None:
        try:
            outcome.append(func())
        # Handed back for the test to assert on.
        except Exception as e:  # noqa: BLE001
            outcome.append(e)

    outcome: list[Any] = []
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(RUN_TIMEOUT)
    return outcome


def test_per_run_state_child_thread_bound_to_run() -> None:
    """A child applied on a thread through _bind_to_run() reports to the run."""

    class Threaded(f.BaseFilter[Any]):
        """Applies ``NotEmpty`` to its value on another thread."""

        def _apply(self, value: Any) -> Any:
            bound = self._bind_to_run(self._filter)
            run_on_thread(lambda: bound(value, f.NotEmpty, "t"))
            flags.append(self._has_errors)
            return value

    flags: list[bool] = []
    runner = f.FilterRunner(f.FilterMapper({"a": Threaded()}), {"a": ""})

    assert runner.error_codes == {"a.t": [f.NotEmpty.CODE_EMPTY]}
    assert flags == [True]


def test_per_run_state_thread_with_run_context_is_not_in_the_run() -> None:
    """A thread holding a live run's context takes no part in that run."""

    class Threaded(f.BaseFilter[Any]):
        """Calls itself on another thread, in a copy of the run's context."""

        def _apply(self, value: Any) -> Any:
            context = contextvars.copy_context()
            outcomes.extend(
                run_on_thread(
                    lambda: context.run(self._filter, "", f.NotEmpty, "t"),
                )
            )
            outcomes.extend(
                run_on_thread(lambda: context.run(f.NotEmpty().apply, "")),
            )
            outcomes.extend(run_on_thread(lambda: context.run(self.apply, None)))
            return value

        def _apply_none(self) -> Any:
            return self._invalid_value(None, self.CODE_EXCEPTION)

    outcomes: list[Any] = []
    runner = f.FilterRunner(f.FilterMapper({"a": Threaded()}), {"a": "x"})

    assert runner.error_codes == {}
    assert [type(outcome) for outcome in outcomes] == [f.FilterError] * 3
    assert [outcome.context["key"] for outcome in outcomes] == ["t", "", ""]


def test_per_run_state_bound_callable_after_the_run() -> None:
    """A callable bound to a finished run reports nothing to it."""

    class Binds(f.BaseFilter[Any]):
        """Hands out a callable bound to its run."""

        def _apply(self, value: Any) -> Any:
            bound.append(self._bind_to_run(self._filter))
            return value

    bound: list[Callable[..., Any]] = []
    finished = f.FilterRunner(f.FilterMapper({"a": Binds()}), {"a": "x"})
    assert finished.is_valid()

    with pytest.raises(f.FilterError):
        bound[0]("", f.NotEmpty)

    assert finished.error_codes == {}


@pytest.mark.parametrize("through_filter", [False, True])
def test_per_run_state_runner_overrides_handler_of_self_applying_filter(
    through_filter: bool,
) -> None:
    """A runner gets a self-applying filter's errors at every depth."""

    class Nested(f.BaseFilter[Any]):
        """Rejects an empty string, at any depth of nested lists."""

        CODE_BAD = "bad"

        templates = {
            CODE_BAD: "Bad.",
        }

        def _apply(self, value: Any) -> Any:
            if isinstance(value, list):
                if through_filter:
                    return [self._filter(item, self) for item in value]

                return [self.apply(item) for item in value]

            return value if value else self._invalid_value(value, self.CODE_BAD)

    configured = f.MemoryHandler()
    runner = f.FilterRunner(Nested().set_handler(configured), ["x", [""]])

    assert runner.error_codes == {"": [Nested.CODE_BAD]}
    assert configured.messages == {}


def test_per_run_state_context_outliving_its_run() -> None:
    """A context copied during a finished run reports nothing to that run."""

    class Captures(f.BaseFilter[Any]):
        """Keeps a copy of the context it ran in, as a pool thread would."""

        def _apply(self, value: Any) -> Any:
            contexts.append(contextvars.copy_context())
            return value

    contexts: list[contextvars.Context] = []
    captures = Captures()
    finished = f.FilterRunner(f.FilterMapper({"a": captures}), {"a": "x"})
    assert finished.is_valid()

    with pytest.raises(f.FilterError) as exc_info:
        contexts[0].run(captures._filter, "", f.NotEmpty)

    assert exc_info.value.context["key"] == ""
    assert finished.error_codes == {}


def test_per_run_state_ancestor_filter_on_bound_thread() -> None:
    """A callback into an ancestor from a bound thread keeps its key."""

    class Outer(f.BaseFilter[Any]):
        """Applies ``Inner``, which calls back into this one from a thread."""

        def _apply(self, value: Any) -> Any:
            result = self._filter(value, Inner(self))
            flags.append(self._has_errors)
            return result

        def check(self, value: Any) -> Any:
            return self._filter(value, f.NotEmpty, sub_key="cb")

    class Inner(f.BaseFilter[Any]):
        """Runs the outer filter's check on another thread."""

        def __init__(self, outer: Outer) -> None:
            super().__init__()

            self.outer = outer

        def _apply(self, value: Any) -> Any:
            bound = self._bind_to_run(self.outer.check)
            run_on_thread(lambda: bound(value))
            return value

    flags: list[bool] = []
    runner = f.FilterRunner(f.FilterMapper({"a": Outer()}), {"a": ""})

    assert runner.error_codes == {"a.cb": [f.NotEmpty.CODE_EMPTY]}
    assert flags == [True]


@pytest.mark.parametrize("own_handler", [False, True])
def test_per_run_state_handler_beneath_reapplied_first_filter(
    own_handler: bool,
) -> None:
    """A nested handler gets the first filter's deeper errors either way."""

    class Rec(f.BaseFilter[Any]):
        """Rejects ``0``, and recurses into lists through ``Mid``."""

        CODE_BAD = "bad"

        templates = {
            CODE_BAD: "Bad.",
        }

        def _apply(self, value: Any) -> Any:
            if isinstance(value, list):
                return [self._filter(item, middle) for item in value]

            return value if value else self._invalid_value(value, self.CODE_BAD)

    class Mid(f.BaseFilter[Any]):
        """Applies ``Rec`` again, with a handler of its own set."""

        def _apply(self, value: Any) -> Any:
            return self._filter(value, rec)

    nested = f.MemoryHandler()
    unused = f.MemoryHandler()
    rec = Rec()
    middle = Mid().set_handler(nested)
    if own_handler:
        rec.set_handler(unused)

    runner = f.FilterRunner(rec, [1, 0])

    assert runner.error_codes == {}
    assert [m.code for m in nested.messages[""]] == [Rec.CODE_BAD]
    assert unused.messages == {}


def test_per_run_state_iter_inside_another_filter_own_errors() -> None:
    """A mapper consumed through iter() reports its own errors in the run."""

    class Iterates(f.BaseFilter[Any]):
        """Consumes a strict mapper through ``iter()``."""

        def _apply(self, value: Any) -> Any:
            mapper = f.FilterMapper({"x": f.NotEmpty}, allow_extra_keys=False)
            return dict(mapper.iter(value))

    runner = f.FilterRunner(
        f.FilterMapper({"a": Iterates()}),
        {"a": {"x": "", "y": 1}},
    )

    assert runner.error_codes == {
        "a.x": [f.NotEmpty.CODE_EMPTY],
        "a.y": [f.FilterMapper.CODE_EXTRA_KEY],
    }


def test_per_run_state_bound_to_frameless_filter_after_the_run() -> None:
    """A callable bound to a filter run through iter() ends with that call."""

    class Child(f.BaseFilter[Any]):
        """Hands out a callable bound to the repeater applying it."""

        def _apply(self, value: Any) -> Any:
            parent = self.parent
            assert parent is not None
            bound.append(parent._bind_to_run(parent._filter))
            return value

    class UsesIter(f.BaseFilter[Any]):
        """Consumes a repeater through ``iter()``."""

        def _apply(self, value: Any) -> Any:
            return list(f.FilterRepeater(Child()).iter(value))

    bound: list[Callable[..., Any]] = []
    finished = f.FilterRunner(f.FilterMapper({"a": UsesIter()}), {"a": ["v"]})
    assert finished.is_valid()

    with pytest.raises(f.FilterError):
        bound[0]("", f.NotEmpty, "late")

    assert finished.error_codes == {}


def test_per_run_state_parent_skips_the_filters_own_frames() -> None:
    """A filter that applies itself still has the filter above it as parent."""

    class Nested(f.BaseFilter[Any]):
        """Records its parent at each depth of nested lists."""

        def _apply(self, value: Any) -> Any:
            parents.append(self.parent)

            if isinstance(value, list):
                return [self.apply(item) for item in value]

            return value

    parents: list[Optional[f.BaseFilter[Any]]] = []
    mapper = f.FilterMapper({"a": Nested()})

    mapper.apply({"a": [1]})

    assert parents == [mapper, mapper]


def test_per_run_state_filter_uses_resolve_filter_override() -> None:
    """_filter() resolves a filter instance through a resolve_filter()."""

    class Wraps(f.BaseFilter[Any]):
        """Wraps every child it applies in ``Optional``."""

        @classmethod
        def resolve_filter(cls, the_filter: Any) -> Any:
            resolved = super().resolve_filter(the_filter)
            return None if resolved is None else resolved | f.Optional("default")

        def _apply(self, value: Any) -> Any:
            return self._filter(value, f.NoOp())

    assert Wraps().apply("") == "default"


def test_per_run_state_chain_keeps_falsy_filter() -> None:
    """A chain applies a filter that is falsy, as a mapper does."""

    class Sized(f.BaseFilter[Any]):
        """Rejects everything, and has a length of zero."""

        def __len__(self) -> int:
            return 0

        def _apply(self, value: Any) -> Any:
            return self._invalid_value(value, self.CODE_EXCEPTION)

    runner = f.FilterRunner(f.Unicode | Sized(), "x")

    assert runner.error_codes == {"": [Sized.CODE_EXCEPTION]}


def test_per_run_state_runner_reruns_after_escaped_exception() -> None:
    """A runner whose run an exception escaped runs again; it is not valid."""

    class Interrupted(f.BaseFilter[Any]):
        """Raises an exception that ``apply()`` does not catch."""

        def _apply(self, value: Any) -> Any:
            raise KeyboardInterrupt

    runner = f.FilterRunner(Interrupted(), "x")

    for _ in range(2):
        with pytest.raises(KeyboardInterrupt):
            runner.is_valid()
