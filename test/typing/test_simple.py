"""
Pins the type-checker inference for ``simple.py``'s filters (issue #34).

This module holds ``Optional``, the package's only ``Widening`` filter
(its class parameter bound from the ``default`` argument). ``Date`` and
``Datetime`` are siblings under a shared private base rather than parent and
child, so each reports the type it actually produces -- both on a direct
call and through a chain. See
docs/adr/008-split-bytestring-and-date-into-siblings.md.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Optional, Union, assert_type

import filters as f


def _list_of_str() -> list[str]:
    """Stand-in for the ``default=list`` factory idiom, with a concrete
    return type both checkers spell the same way.
    """
    return []


def test_byte_array_apply_returns_optional_bytearray() -> None:
    """``ByteArray`` is transforming: its class parameter is fixed to
    ``bytearray``.
    """
    assert_type(f.ByteArray().apply(b"hello"), Optional[bytearray])


def test_byte_array_chains_with_pass_through() -> None:
    """A real transforming filter from this module chained onto a real
    pass-through filter from this module.
    """
    assert_type(f.ByteArray() | f.NoOp(), f.FilterChain[bytearray])


def test_datetime_apply_returns_optional_datetime() -> None:
    """``Datetime`` is transforming: its class parameter is fixed to
    ``datetime.datetime``.
    """
    assert_type(f.Datetime().apply("2000-01-01"), Optional[datetime])


def test_date_apply_returns_optional_date_not_datetime() -> None:
    """``Date`` is transforming: its class parameter is fixed to
    ``datetime.date``, which it now carries in its own right rather than
    inheriting ``Datetime``'s ``datetime``.
    """
    assert_type(f.Date().apply("2000-01-01"), Optional[date])


def test_date_chain_reports_date() -> None:
    """The payoff of the split: ``|`` dispatches on ``Date``'s own class
    parameter, so a chain through it reports what it returns.

    Before the split both assertions read ``FilterChain[datetime]``, so
    ``.hour`` on a chain's output type-checked and then raised.
    """
    assert_type(f.Date() | f.NoOp(), f.FilterChain[date])
    assert_type(f.Unicode() | f.Date(), f.FilterChain[date])


def test_empty_not_empty_and_length_filters_are_pass_through() -> None:
    """Checks that only validate, so their own ``apply`` reports
    ``PassThrough``'s fixed ``Any`` -- the input type only survives
    through a chain (see ``test_chain_with_real_transform_and_check``
    below).
    """
    assert_type(f.Empty().apply(""), Optional[Any])
    assert_type(f.NotEmpty().apply("x"), Optional[Any])
    assert_type(f.Required().apply("x"), Optional[Any])
    assert_type(f.Len(3).apply("abc"), Optional[Any])
    assert_type(f.Length(3).apply("abc"), Optional[Any])
    assert_type(f.MinLength(1).apply("abc"), Optional[Any])
    assert_type(f.MaxLength(3).apply("abc"), Optional[Any])
    assert_type(f.NoOp().apply("x"), Optional[Any])


def test_chain_with_real_transform_and_check() -> None:
    """A real transforming filter chained onto a real check, both from
    this module.
    """
    assert_type(f.ByteArray() | f.Required(), f.FilterChain[bytearray])


def test_call_binds_return_type_from_ctor() -> None:
    """``Call`` is ctor-typed: its class parameter is bound from
    ``callable_``'s return type.
    """
    assert_type(f.Call(str), f.Call[str])
    assert_type(f.Call(str).apply(5), Optional[str])
    assert_type(f.Call(str) | f.NotEmpty(), f.FilterChain[str])


def test_item_omit_pick_stay_untyped() -> None:
    """``Item``/``Omit``/``Pick`` depend on the runtime structure of the
    incoming value and an arbitrary key, so their class parameter is
    explicit ``Any`` rather than inferred.
    """
    assert_type(f.Item().apply({"a": 1}), Optional[Any])
    assert_type(f.Omit(["a"]).apply({"a": 1, "b": 2}), Optional[Any])
    assert_type(f.Pick(["a"]).apply({"a": 1, "b": 2}), Optional[Any])


def test_array_is_explicitly_type_any() -> None:
    """``Array`` subclasses the generic ``Type``, but is pinned to
    ``Type[Any]`` explicitly rather than letting its ``super().__init__()``
    call infer ``Type[Sequence[Any]]``, which would overstate the contract
    (``_apply`` rejects ``str``/``bytes``, themselves ``Sequence``s).
    """
    assert_type(f.Array().apply([1, 2]), Optional[Any])
    assert_type(f.Array() | f.NoOp(), f.FilterChain[Any])


def test_optional_binds_widened_type_from_default() -> None:
    """``Optional``'s class parameter is bound from its ``default``
    argument, defaulting to ``None``.
    """
    assert_type(f.Optional(), f.Optional[None])
    assert_type(f.Optional(0), f.Optional[int])


def test_optional_widens_a_chains_output_type() -> None:
    """The actual point of ``Widening``: an ``Optional`` with no default
    adds ``None`` to the chain's output type, while a same-typed default
    leaves it alone (``int | int`` is just ``int``).
    """
    assert_type(f.Int() | f.Optional(), f.FilterChain[Optional[int]])
    assert_type(f.Int() | f.Optional(0), f.FilterChain[int])


def test_optional_factory_default_widens_by_the_callable_type() -> None:
    """Pins a KNOWN LIMITATION, not correct behaviour.

    ``Optional``'s class parameter binds from ``default`` itself, so the
    documented factory idiom (``default=list``) widens the chain by the
    callable's type rather than by the type it constructs. At runtime the
    replacement here is a ``list[str]``; statically the chain reports the
    zero-argument callable.

    Spelled with a module-level function rather than ``list`` because the
    two checkers render a generic class object differently (mypy keeps
    the overloaded constructor signature, pyright reduces it to
    ``type[list[_T]]``), and ``assert_type`` needs one spelling both
    accept. The imprecision is identical either way.

    Delete this test if ``Optional`` ever learns to bind the constructed
    type -- see the class docstring for why that is not free.
    """
    assert_type(f.Optional(_list_of_str), f.Optional[Callable[[], list[str]]])
    assert_type(
        f.Unicode() | f.Optional(_list_of_str),
        f.FilterChain[Union[str, Callable[[], list[str]]]],
    )
