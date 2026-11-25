"""
Tests for the NoOp filter.
"""

from collections.abc import Callable
from typing import Any

import filters as f
from filters.handlers import FilterRunner


def test_no_op_pass_any_value(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    You can pass any value you want to a NoOp, and it will pass.
    """
    assert_filter_passes(
        f.NoOp(),
        "supercalafragalisticexpialadoshus",
    )
