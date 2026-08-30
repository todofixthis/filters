"""
Pins the type-checker inference for ``number.py``'s filters (issue #34).

Covers the transforming and pass-through cases against the real filters
rather than ``test_chain_inference.py``'s stand-ins, plus the ctor-typed
case (``Round``) that has no stand-in there.
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
    rather than ``test_chain_inference.py``'s stand-ins for both.
    """
    assert_type(f.Int() | f.Max(10), f.FilterChain[int])
