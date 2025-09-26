"""
Tests for the NoOp filter.
"""

import filters as f


def test_no_op_pass_any_value(assert_filter_passes):
    """
    You can pass any value you want to a NoOp, and it will pass.
    """
    assert_filter_passes(
        f.NoOp(),
        "supercalafragalisticexpialadoshus",
    )
