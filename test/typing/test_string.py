"""
Pins the type-checker inference for ``string.py``'s filters (issue #34).

Phase 2b annotates the real filters, including the trickiest case in the
plan so far -- ``ByteString``, which still subclasses ``Unicode`` at
runtime (Phase 5's job to split) but returns ``bytes`` where ``Unicode``
returns ``str``.
"""

from typing import Any, Optional, assert_type
from uuid import UUID

import filters as f


def test_unicode_apply_returns_optional_str() -> None:
    """``Unicode`` is transforming: its class parameter is fixed to
    ``str``.
    """
    assert_type(f.Unicode().apply(b"hello"), Optional[str])


def test_uuid_apply_returns_optional_uuid() -> None:
    """``Uuid`` is transforming: its class parameter is fixed to
    ``uuid.UUID``.
    """
    assert_type(f.Uuid().apply("00000000-0000-0000-0000-000000000000"), Optional[UUID])


def test_byte_string_apply_returns_optional_bytes() -> None:
    """``ByteString`` still inherits ``Unicode`` at runtime, but its
    ``_apply`` override reports ``bytes`` -- the interim suppression this
    phase adds (see the comment on ``ByteString._apply``) keeps this
    accurate rather than falling back to ``Unicode``'s ``str``.
    """
    assert_type(f.ByteString().apply("hello"), Optional[bytes])


def test_byte_string_chain_still_reports_the_parent_type() -> None:
    """Pins a known-wrong inference, not correct behaviour.

    ``ByteString.apply``'s override fixes the direct call, but the ``|``
    overloads dispatch on the class parameter ``ByteString`` inherits from
    ``Unicode``, so a chain ending in ``ByteString`` reports ``str`` for a
    chain that returns ``bytes`` at runtime. Phase 5's split of the two
    filters is what fixes this; these assertions exist so that split has to
    update them deliberately rather than silently changing the answer.
    """
    assert_type(f.Unicode() | f.ByteString(), f.FilterChain[str])
    assert_type(f.Unicode() | f.Strip() | f.ByteString(), f.FilterChain[str])


def test_choice_binds_element_type_from_ctor() -> None:
    """``Choice`` is ctor-typed: its class parameter is bound from the
    ``choices`` argument, not fixed like a transforming filter.
    """
    assert_type(f.Choice(["a", "b"]).apply("a"), Optional[str])
    assert_type(f.Choice([1, 2]).apply(1), Optional[int])


def test_split_binds_container_shape_from_keys() -> None:
    """``Split`` is ctor-typed on whether ``keys`` is set: a list without
    it, a dict keyed by ``keys`` with it.
    """
    assert_type(f.Split("-"), f.Split[list[str]])
    assert_type(f.Split("-").apply("a-b"), Optional[list[str]])
    assert_type(f.Split("-", keys=["a", "b"]), f.Split[dict[str, str]])
    assert_type(f.Split("-", keys=["a", "b"]).apply("a-b"), Optional[dict[str, str]])


def test_json_decode_stays_untyped() -> None:
    """``JsonDecode`` is left bare -- its ``decoder`` defaults to
    ``json.loads``, which is untyped, so its class parameter defaults to
    ``Any`` rather than inventing one.
    """
    assert_type(f.JsonDecode().apply("{}"), Optional[Any])


def test_chain_with_real_string_filters() -> None:
    """A real transforming filter from this module chained onto another,
    now that ``string.py`` supplies both instead of Phase 1's stand-ins.
    """
    assert_type(f.Unicode() | f.MaxChars(10), f.FilterChain[str])
