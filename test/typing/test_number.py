"""
Pins the type-checker inference for ``number.py``'s filters (issue #34).

Phase 2a annotates the real filters, replacing the Phase 1 stand-ins in
``test_chain_inference.py`` for the transforming/pass-through cases, and
adds the ctor-typed case (``Round``) that Phase 1 had no stand-in for.
"""

from decimal import Decimal as DecimalType
from typing import Any, Optional, assert_type

import filters as f


def test_int_apply_returns_optional_int() -> None:
    """``Int`` is transforming: its class parameter is fixed to ``int``."""
    assert_type(f.Int().apply(5), Optional[int])


def test_decimal_apply_returns_optional_decimal() -> None:
    """``Decimal`` is transforming: its class parameter is fixed to
    ``decimal.Decimal``.
    """
    assert_type(f.Decimal().apply(5), Optional[DecimalType])


def test_min_max_are_pass_through() -> None:
    """``Min``/``Max`` only validate, so their own ``apply`` reports
    ``PassThrough``'s fixed ``Any`` -- the input type only survives through
    a chain (see ``test_chain_with_real_transform_and_pass_through`` below).
    """
    assert_type(f.Min(0).apply(5), Optional[Any])
    assert_type(f.Max(10).apply(5), Optional[Any])


def test_round_binds_result_type_from_ctor() -> None:
    """``Round`` is ctor-typed: ``result_type`` determines the class
    parameter, defaulting to ``decimal.Decimal``.
    """
    assert_type(f.Round(), f.Round[DecimalType])
    assert_type(f.Round().apply(5), Optional[DecimalType])
    assert_type(f.Round(result_type=int), f.Round[int])
    assert_type(f.Round(result_type=int).apply(5), Optional[int])


def test_chain_with_real_transform_and_pass_through() -> None:
    """A real transforming filter chained onto a real pass-through filter,
    now that ``number.py`` supplies both instead of Phase 1's stand-ins.
    """
    assert_type(f.Int() | f.Max(10), f.FilterChain[int])
