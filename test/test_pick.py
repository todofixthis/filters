"""
Tests for the Pick filter.
"""

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

import pytest

import filters as f
from filters.handlers import FilterRunner


def test_pick_pass_none(assert_filter_passes: Callable[..., FilterRunner[Any]]) -> None:
    """
    ``None`` always passes this filter.

    Use ``Required | Pick`` to reject ``None``.
    """
    assert_filter_passes(
        f.Pick(keys={"test"}),
        None,
    )


def test_pick_pass_mapping(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Using the filter to pick specific keys from a mapping.
    """
    assert_filter_passes(
        f.Pick(keys={"foo"}),
        {"foo": "bar", "baz": "luhrmann"},
        {"foo": "bar"},
    )


def test_pick_pass_mapping_exact_match(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming contains only the keys to be picked.
    """
    assert_filter_passes(
        f.Pick(keys={"foo", "baz"}),
        {"foo": "bar", "baz": "luhrmann"},
    )


def test_pick_pass_mapping_ordered_keys(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    When keys are provided in an ordered collection, the order of keys
    determines the order of the items in the result.
    """
    runner = assert_filter_passes(
        f.Pick(keys=("actor", "name", "job")),
        {"name": "Indy", "job": "archaeologist", "actor": "Harrison"},
        {"actor": "Harrison", "name": "Indy", "job": "archaeologist"},
    )

    assert list(runner.cleaned_data.keys()) == ["actor", "name", "job"]


def test_pick_pass_mapping_missing_values(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Any keys not present in the incoming value are set to ``None``.
    """
    assert_filter_passes(
        f.Pick(keys=["foo", "foobie"]),
        {"foo": "bar", "baz": "luhrmann"},
        {"foo": "bar", "foobie": None},
    )


def test_pick_pass_mapping_empty(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    An empty mapping always passes this filter by default.

    Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
    empty mappings, or set ``allow_missing_keys`` when initialising the
    filter.
    """
    assert_filter_passes(
        f.Pick(keys=["foo", "baz"]),
        {},
        {"foo": None, "baz": None},
    )


def test_pick_pass_mapping_match_type(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Whenever practical, the filter will try to return the same type of
    value that it received.
    """
    runner = assert_filter_passes(
        f.Pick(keys=("baz",)),
        OrderedDict(foo="bar", baz="luhrmann"),
        OrderedDict(baz="luhrmann"),
    )

    assert isinstance(runner.cleaned_data, OrderedDict)


def test_pick_fail_mapping_allow_missing_keys_false(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Incoming value is missing one or more requested keys, and the filter
    was initialised with ``allow_missing_keys=False``.
    """
    assert_filter_errors(
        f.Pick(
            keys=["foo", "foobie", "foobar"],
            allow_missing_keys=False,
        ),
        {"foo": "bar", "baz": "luhrmann"},
        {
            "foobie": [f.Pick.CODE_MISSING_KEY],
            "foobar": [f.Pick.CODE_MISSING_KEY],
        },
        {"foo": "bar", "foobie": None, "foobar": None},
    )


def test_pick_pass_mapping_allow_missing_keys_iterable(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    An incoming value is missing one or more requested keys, but they are
    allowed to be missing because of ``allow_missing_keys``.
    """
    assert_filter_passes(
        f.Pick(
            keys=["foo", "foobie", "foobar"],
            allow_missing_keys={"foobie", "foobar"},
        ),
        {"foo": "bar", "baz": "luhrmann"},
        {"foo": "bar", "foobie": None, "foobar": None},
    )


def test_pick_pass_sequence(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Using the filter to pick specific indices from a sequence.
    """
    assert_filter_passes(
        f.Pick(keys=[0, 2]),
        ["foo", "bar", "baz"],
        ["foo", "baz"],
    )


def test_pick_pass_sequence_exact_match(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming sequence contains only the indices to be picked.
    """
    assert_filter_passes(f.Pick(keys=[0, 1, 2]), ["foo", "bar", "baz"])


def test_pick_pass_sequence_ordered_keys(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    When keys are provided in an ordered collection, the order of keys
    determines the order of the items in the result.
    """
    assert_filter_passes(
        f.Pick(keys=[1, 0, 2]),
        ["Indiana", "Marion", "Marcus"],
        ["Marion", "Indiana", "Marcus"],
    )


def test_pick_pass_sequence_missing_values(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Any indices not present in the incoming value are set to ``None``.
    """
    assert_filter_passes(
        f.Pick(keys=[0, 2, 4]),
        ["foo", "bar", "baz"],
        ["foo", "baz", None],
    )


def test_pick_pass_sequence_empty(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    An empty sequence always passes this filter.

    Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
    empty sequences, or set ``allow_missing_keys`` when initialising the
    filter.
    """
    assert_filter_passes(
        f.Pick(keys=[1]),
        [],
        [None],
    )


def test_pick_pass_sequence_match_type(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Whenever practical, the filter will try to return the same type of
    value that it received.
    """
    runner = assert_filter_passes(
        f.Pick(keys=(1,)),
        ("foo", "bar", "baz"),
        ("bar",),
    )

    assert isinstance(runner.cleaned_data, tuple)


def test_pick_fail_sequence_allow_missing_keys_false(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    Incoming value is missing one or more requested indices, and the filter
    was initialised with ``allow_missing_keys=False``.
    """
    assert_filter_errors(
        f.Pick(
            keys={0, 2, 4},
            allow_missing_keys=False,
        ),
        ["foo", "bar"],
        {
            "2": [f.Pick.CODE_MISSING_KEY],
            "4": [f.Pick.CODE_MISSING_KEY],
        },
        ["foo", None, None],
    )


def test_pick_pass_sequence_allow_missing_keys_iterable(
    assert_filter_passes: Callable[..., FilterRunner[Any]],
) -> None:
    """
    An incoming value is missing one or more requested indices, but they
    are allowed to be missing because of ``allow_missing_keys``.
    """
    assert_filter_passes(
        f.Pick(
            keys={0, 2, 4},
            allow_missing_keys={2, 4},
        ),
        ["foo", "bar"],
        ["foo", None, None],
    )


def test_pick_fail_wrong_type(
    assert_filter_errors: Callable[..., FilterRunner[Any]],
) -> None:
    """
    The incoming value is neither a mapping nor a sequence.
    """
    assert_filter_errors(
        f.Pick(keys={0}),
        42,
        [f.Type.CODE_WRONG_TYPE],
    )


def test_pick_error_empty_keys() -> None:
    """
    The ``keys`` param must not be empty.
    """
    with pytest.raises(f.FilterError):
        f.Pick([])
