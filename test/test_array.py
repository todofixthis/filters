"""
Tests for the Array filter.
"""

import typing

import pytest

import filters as f


def test_array_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Array`` if you want to reject null values.
    """
    assert_filter_passes(f.Array(), None)


def test_array_pass_sequence(assert_filter_passes):
    """
    The incoming value is a sequence.
    """
    assert_filter_passes(f.Array(), tuple())
    assert_filter_passes(f.Array(), list())


def test_array_pass_custom_sequence_type(assert_filter_passes):
    """
    The incoming value has a type that extends Sequence.
    """

    class CustomSequence(typing.Sequence):
        """
        Technically, it's a Sequence. Technically.
        """

        def __len__(self):
            return 0

        def __getitem__(self, index):
            return None

    assert_filter_passes(f.Array(), CustomSequence())


@pytest.mark.parametrize("value", [bytes(), str()])
def test_array_fail_string(assert_filter_errors, value):
    """
    The incoming value is a string.
    """
    assert_filter_errors(f.Array(), value, [f.Array.CODE_WRONG_TYPE])


def test_array_fail_mapping(assert_filter_errors):
    """
    The incoming value is a mapping.
    """
    assert_filter_errors(f.Array(), dict(), [f.Array.CODE_WRONG_TYPE])


def test_array_fail_set(assert_filter_errors):
    """
    The incoming value is a set.
    """
    assert_filter_errors(f.Array(), set(), [f.Array.CODE_WRONG_TYPE])


def test_array_fail_custom_sequence_type(assert_filter_errors):
    """
    The incoming value looks like a Sequence, but it's not official.
    """

    class CustomSequence(object):
        """
        Walks, talks and quacks like a Sequence, but isn't.
        """

        def __len__(self):
            return 0

        def __getitem__(self, index):
            return None

    assert_filter_errors(f.Array(), CustomSequence(), [f.Array.CODE_WRONG_TYPE])

    # If you can't (or don't want) to modify the base class for your custom
    # sequence, you can ``register`` it.
    #
    # Note: Code included here for documentation purposes, but it's
    # commented out to avoid side effects; registering a subclass this way
    # is basically irreversible.
    #
    # Sequence.register(CustomSequence)
    # self.assertFilterPasses(CustomSequence())
