"""
Tests for the FilterSwitch filter.
"""

import filters as f


def test_filter_switch_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``f.Required | f.FilterSwitch`` to reject null values.
    """
    filter_instance = f.FilterSwitch(
        getter=lambda value: value["anything"],
        cases={},
    )

    assert_filter_passes(filter_instance, None)


def test_filter_switch_pass_match_case(assert_filter_passes):
    """
    The incoming value matches one of the switch cases.
    """
    filter_instance = f.FilterSwitch(
        getter=lambda value: value["name"],
        cases={
            "positive": f.FilterMapper({"value": f.Int | f.Min(0)}),
        },
    )

    assert_filter_passes(
        filter_instance,
        {"name": "positive", "value": 42},
    )


def test_filter_switch_fail_match_case(assert_filter_errors):
    """
    The incoming value matches one of the switch cases, but it is not
    valid, according to the corresponding filter.
    """
    filter_instance = f.FilterSwitch(
        getter=lambda value: value["name"],
        cases={
            "positive": f.FilterMapper({"value": f.Int | f.Min(0)}),
        },
    )

    assert_filter_errors(
        filter_instance,
        {"name": "positive", "value": -1},
        {"value": [f.Min.CODE_TOO_SMALL]},
        # The result is the exact same as if the value were passed directly
        # to the corresponding filter.
        expected_value={"name": "positive", "value": None},
    )


def test_filter_switch_pass_default(assert_filter_passes):
    """
    The incoming value does not match any of the switch cases, but we
    defined a default filter.
    """
    filter_instance = f.FilterSwitch(
        getter=lambda value: value["name"],
        cases={
            "positive": f.FilterMapper({"value": f.Int | f.Min(0)}),
        },
        default=f.FilterMapper({"value": f.Int | f.Max(0)}),
    )

    assert_filter_passes(
        filter_instance,
        {"name": "negative", "value": -42},
    )


def test_filter_switch_fail_no_default(assert_filter_errors):
    """
    The incoming value does not match any of the switch cases, and we did
    not define a default filter.
    """
    filter_instance = f.FilterSwitch(
        getter=lambda value: value["name"],
        cases={
            "positive": f.FilterMapper({"value": f.Int | f.Min(0)}),
        },
    )

    assert_filter_errors(
        filter_instance,
        {"name": "negative", "value": -42},
        [f.Choice.CODE_INVALID],
    )
