"""
Pins the type-checker inference for ``complex.py``'s filters (issue #34).

Three of this module's four filters stay untyped -- their result type
depends on the runtime shape of the incoming value, not on anything visible
to a type checker -- leaving ``NamedTuple`` as its only ctor-typed case.
"""

from collections import namedtuple
from typing import Any, Optional, assert_type

import filters as f
from filters.base import FilterCompatible

Colour = namedtuple("Colour", ("r", "g", "b"))


def test_filter_mapper_repeater_switch_stay_untyped() -> None:
    """``FilterMapper``/``FilterRepeater``/``FilterSwitch`` all dispatch on
    the runtime shape of the incoming value, so their class parameter is
    explicit ``Any`` rather than inferred.
    """
    assert_type(f.FilterMapper({"a": f.Unicode}).apply({"a": "x"}), Optional[Any])
    assert_type(f.FilterRepeater(f.Unicode).apply(["x"]), Optional[Any])
    assert_type(
        f.FilterSwitch(str, {"x": f.Unicode}).apply("x"),
        Optional[Any],
    )


def test_filter_mapper_accepts_non_str_keys() -> None:
    """``FilterMapper``'s sequence mode (ADR 003) is selected by an all-int
    ``filter_map``, so the ctor must accept non-``str`` keys.

    ``filter_map`` is annotated ``Mapping[Any, ...]`` rather than
    ``Mapping[str | int, ...]`` because ``Mapping``'s key type is invariant:
    a union would reject the pre-typed ``dict[str, FilterCompatible]`` a
    caller passes below. Nothing here asserts a result type -- what it pins
    is that each ctor call type-checks at all.
    """
    f.FilterMapper({0: f.Unicode | f.Strip, 1: f.Int})
    f.FilterMapper({"name": f.Required | f.Unicode})

    str_keyed: dict[str, FilterCompatible] = {"name": f.Unicode}
    f.FilterMapper(str_keyed)

    int_keyed: dict[int, FilterCompatible] = {0: f.Unicode}
    f.FilterMapper(int_keyed)


def test_named_tuple_binds_type_from_ctor() -> None:
    """``NamedTuple`` is ctor-typed: its class parameter is bound from the
    ``type_`` argument.
    """
    assert_type(f.NamedTuple(Colour), f.NamedTuple[Colour])
    assert_type(f.NamedTuple(Colour).apply(("1", "2", "3")), Optional[Colour])
