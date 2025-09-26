"""
Tests for the NamedTuple filter.
"""

from collections import namedtuple

import filters as f


Colour = namedtuple("Colour", ("r", "g", "b"))


def test_named_tuple_success_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Chain with :py:class:`f.Required` if you want to disallow null values.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_passes(filter_instance, None)


def test_named_tuple_success_namedtuple_correct_type(assert_filter_passes):
    """
    Incoming value is already a namedtuple of the expected type.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_passes(filter_instance, Colour(64, 128, 192))


def test_named_tuple_success_namedtuple_different_type(assert_filter_passes):
    """
    Incoming value is a namedtuple instance, but of a different type.

    Since namedtuples are still tuples, this has the same result as for any
    other incoming iterable.
    """
    filter_instance = f.NamedTuple(Colour)

    # Just to be tricky, we'll make it look very close to the expected
    # type.
    AltColour = namedtuple("AltColour", Colour._fields)

    # noinspection PyArgumentList
    runner = assert_filter_passes(
        filter_instance,
        AltColour(64, 128, 192),
        Colour(64, 128, 192),
    )

    assert isinstance(runner.cleaned_data, Colour)


def test_named_tuple_success_iterable(assert_filter_passes):
    """
    Incoming value is an iterable with correct values.
    """
    filter_instance = f.NamedTuple(Colour)

    value = [64, 128, 192]
    assert_filter_passes(filter_instance, value, Colour(*value))


def test_named_tuple_success_iterable_compat(assert_filter_passes):
    """
    Incoming value is an iterable, formatted for compatibility with
    Python < 3.6 (even though technically we don't support it anymore;
    don't tell anyone).
    """
    filter_instance = f.NamedTuple(Colour)

    value = [("b", 192), ("g", 128), ("r", 64)]
    assert_filter_passes(filter_instance, value, Colour(*value))


def test_named_tuple_success_mapping(assert_filter_passes):
    """
    Incoming value is a mapping with correct keys.
    """
    filter_instance = f.NamedTuple(Colour)

    value = {"r": 64, "g": 128, "b": 192}
    assert_filter_passes(filter_instance, value, Colour(**value))


def test_named_tuple_fail_incompatible_type(assert_filter_errors):
    """
    Incoming value has a type that we cannot work with.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_errors(filter_instance, 42, [f.Type.CODE_WRONG_TYPE])


def test_named_tuple_fail_iterable_too_short(assert_filter_errors):
    """
    Incoming value is an iterable that is missing one or more values.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_errors(
        filter_instance,
        (
            64,
            128,
        ),
        [f.MinLength.CODE_TOO_SHORT],
    )


def test_named_tuple_fail_iterable_too_long(assert_filter_errors):
    """
    Incoming value is an iterable that has too many values.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_errors(
        filter_instance,
        (64, 128, 192, 0.5),
        [f.MaxLength.CODE_TOO_LONG],
    )


def test_named_tuple_fail_mapping_missing_keys(assert_filter_errors):
    """
    Incoming value is a mapping that is missing one or more keys.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_errors(
        filter_instance,
        {},
        {
            "r": [f.FilterMapper.CODE_MISSING_KEY],
            "g": [f.FilterMapper.CODE_MISSING_KEY],
            "b": [f.FilterMapper.CODE_MISSING_KEY],
        },
    )


def test_named_tuple_fail_mapping_extra_keys(assert_filter_errors):
    """
    Incoming value is a mapping that has extra keys that we don't know what
    to do with.
    """
    filter_instance = f.NamedTuple(Colour)

    assert_filter_errors(
        filter_instance,
        {
            "r": 64,
            "g": 128,
            "b": 192,
            "a": 0.5,
        },
        {
            "a": [f.FilterMapper.CODE_EXTRA_KEY],
        },
    )


def test_named_tuple_success_filter_map(assert_filter_passes):
    """
    Applying a :py:class:`f.FilterMap` to the values in a namedtuple after
    converting (success case).
    """
    filter_instance = f.NamedTuple(
        Colour,
        {
            # For whatever reason, we decide not to filter ``r``.
            "g": f.Required | f.Int | f.Min(0) | f.Max(255),
            "b": f.Required | f.Int | f.Min(0) | f.Max(255),
        },
    )

    assert_filter_passes(
        filter_instance,
        ("64.0", "128", 192.0),
        Colour("64.0", 128, 192),
    )


def test_named_tuple_fail_filter_map(assert_filter_errors):
    """
    Applying a :py:class:`f.FilterMap` to the values in a namedtuple after
    converting (failure case).
    """
    filter_instance = f.NamedTuple(
        Colour,
        {
            # For whatever reason, we decide not to filter ``r``.
            "g": f.Required | f.Int | f.Min(0) | f.Max(255),
            "b": f.Required | f.Int | f.Min(0) | f.Max(255),
        },
    )

    assert_filter_errors(
        filter_instance,
        ["NaN", None, (42,)],
        {
            "g": [f.Required.CODE_EMPTY],
            "b": [f.Decimal.CODE_INVALID],
        },
    )
