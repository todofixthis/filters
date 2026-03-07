"""
Tests for the Choice filter.
"""

import pytest

import filters as f


def test_choice_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Choice`` if you want to reject null values.
    """
    assert_filter_passes(
        f.Choice(choices=("anything")),
        None,
    )


def test_choice_pass_valid(assert_filter_passes):
    """
    The incoming value matches one of the choices.
    """
    assert_filter_passes(
        f.Choice(choices=("Moe", "Larry", "Curly")),
        "Curly",
    )


def test_choice_fail_invalid(assert_filter_errors):
    """
    The incoming value does not match any of the choices.
    """
    assert_filter_errors(
        f.Choice(choices=("Moe", "Larry", "Curly")),
        "Shemp",
        [f.Choice.CODE_INVALID],
    )


def test_choice_pass_case_insensitive_valid(assert_filter_passes):
    """
    The incoming value matches a choice using case-insensitive comparison.
    """
    assert_filter_passes(
        f.Choice(
            choices=("Moe", "Larry", "Curly"),
            case_sensitive=False,
        ),
        "mOE",
        # The ``choices`` passed to the filter initialiser define the
        # canonical choices.
        "Moe",
    )


def test_choice_fail_case_insensitive_type_mismatch(assert_filter_errors):
    """
    The incoming value has a different type, so it does not match.
    """
    assert_filter_errors(
        f.Choice(choices=("42",), case_sensitive=False),
        42,
        [f.Choice.CODE_INVALID],
    )


def test_choice_error_choices_empty():
    """
    The filter must be configured with at least one valid choice.
    """
    with pytest.raises(f.FilterError):
        f.Choice(choices=[])
