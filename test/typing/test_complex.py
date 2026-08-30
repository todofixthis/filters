"""
Pins the type-checker inference for ``complex.py``'s filters (issue #34).

Phase 2d annotates the real filters, closing out Phase 2. Three of the four
stay untyped -- their result type depends on the runtime shape of the
incoming value, not on anything visible to a type checker -- leaving
``NamedTuple`` as this module's only ctor-typed case.
"""

from collections import namedtuple
from typing import Any, Optional, assert_type

import filters as f

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


def test_named_tuple_binds_type_from_ctor() -> None:
    """``NamedTuple`` is ctor-typed: its class parameter is bound from the
    ``type_`` argument.
    """
    assert_type(f.NamedTuple(Colour), f.NamedTuple[Colour])
    assert_type(f.NamedTuple(Colour).apply(("1", "2", "3")), Optional[Colour])
