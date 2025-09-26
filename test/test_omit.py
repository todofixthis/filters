"""
Tests for the Omit filter.
"""

import pytest

import filters as f


def test_omit_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Omit`` to reject ``None``.
    """
    assert_filter_passes(f.Omit(keys={"test"}), None)


def test_omit_pass_mapping(assert_filter_passes):
    """
    Incoming value is a mapping.
    """
    assert_filter_passes(
        f.Omit(keys={"actor", "age"}),
        {"name": "Indy", "job": "archaeologist", "actor": "Harrison"},
        {"name": "Indy", "job": "archaeologist"},
    )


def test_omit_pass_mapping_no_items_omitted(assert_filter_passes):
    """
    Incoming value is a mapping, and it doesn't have any of the keys to be
    omitted.
    """
    assert_filter_passes(
        f.Omit(keys=["profession", "surname"]),
        {"name": "Indy", "job": "archaeologist", "actor": "Harrison"},
    )


def test_omit_pass_mapping_empty(assert_filter_passes):
    """
    An empty mapping always passes this filter by default.

    Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
    empty mappings.
    """
    assert_filter_passes(
        f.Omit(keys=["foo", "bar", "baz", "luhrmann"]),
        {},
    )


def test_omit_pass_sequence(assert_filter_passes):
    """
    Incoming value is a sequence.
    """
    assert_filter_passes(
        f.Omit(keys=[1, 3]),
        ["Indy", "Marion", "Marcus"],
        ["Indy", "Marcus"],
    )


def test_omit_pass_sequence_no_items_omitted(assert_filter_passes):
    """
    Incoming value is a sequence, and it doesn't have any of the indices to
    be omitted.
    """
    assert_filter_passes(
        f.Omit(keys=[3, 4, 5]),
        ["Indy", "Marion", "Marcus"],
    )


def test_omit_pass_sequence_empty(assert_filter_passes):
    """
    An empty sequence always passes this filter by default.

    Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
    empty sequences.
    """
    assert_filter_passes(f.Omit(keys=[3, 4, 5, 6]), [])


def test_omit_fail_wrong_type(assert_filter_errors):
    """
    Incoming value is not a mapping nor sequence.
    """
    assert_filter_errors(
        f.Omit(keys=[0]),
        42,
        [f.Type.CODE_WRONG_TYPE],
    )


def test_omit_error_empty_keys():
    """
    The ``keys`` param must not be empty.
    """
    with pytest.raises(f.FilterError):
        f.Omit([])
