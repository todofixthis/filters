"""
Pins the type-checker inference for ``string.py``'s filters (issue #34).

Phase 2b annotated the real filters; Phase 5 then split ``ByteString`` off
``Unicode`` into siblings under a shared private base, so each reports the
type it actually produces -- both on a direct call and through a chain. See
docs/adr/008-split-bytestring-and-date-into-siblings.md.
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
    """``ByteString`` is transforming: its class parameter is fixed to
    ``bytes``, which it now carries in its own right rather than
    inheriting ``Unicode``'s ``str``.
    """
    assert_type(f.ByteString().apply("hello"), Optional[bytes])


def test_byte_string_chain_reports_bytes() -> None:
    """The payoff of the split: ``|`` dispatches on ``ByteString``'s own
    class parameter, so a chain ending in it reports what it returns.

    Before the split both assertions read ``FilterChain[str]``, because
    ``ByteString`` inherited ``Unicode``'s parameter and the overloads had
    no way past it.
    """
    assert_type(f.Unicode() | f.ByteString(), f.FilterChain[bytes])
    assert_type(f.Unicode() | f.Strip() | f.ByteString(), f.FilterChain[bytes])


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
