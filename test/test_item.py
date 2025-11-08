"""
Tests for the Item filter.
"""

import filters as f


def test_item_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Item`` if you want to reject null values.
    """
    assert_filter_passes(f.Item(), None)


def test_item_pass_mapping_default(assert_filter_passes):
    """
    By default, returns the first item in a mapping.
    """
    assert_filter_passes(
        f.Item(),
        {"foo": "bar", "baz": "luhrmann"},
        "bar",
    )


def test_item_fail_mapping_empty(assert_filter_errors):
    """
    The incoming value is an empty mapping, so no value to extract.
    """
    assert_filter_errors(f.Item(), {}, [f.NotEmpty.CODE_EMPTY])


def test_item_pass_mapping_specific_key(assert_filter_passes):
    """
    Specify the key to extract from a mapping.
    """
    assert_filter_passes(
        f.Item(key="baz"),
        {"foo": "bar", "baz": "luhrmann"},
        "luhrmann",
    )


def test_item_fail_mapping_specific_key_missing(assert_filter_errors):
    """
    The incoming mapping does not contain the specified key.
    """
    assert_filter_errors(
        f.Item(key="foobie"),
        {"foo": "bar", "baz": "luhrmann"},
        {"foobie": [f.Item.CODE_MISSING_KEY]},
    )


def test_item_pass_sequence_default(assert_filter_passes):
    """
    By default, returns the first item in a sequence.
    """
    assert_filter_passes(f.Item(), ["foo", "bar", "baz", "luhrmann"], "foo")


def test_item_fail_sequence_empty(assert_filter_errors):
    """
    The incoming value is an empty sequence, so no value to extract.
    """
    assert_filter_errors(f.Item(), [], [f.NotEmpty.CODE_EMPTY])


def test_item_pass_sequence_specific_index(assert_filter_passes):
    """
    Specify the index to extract from a mapping.
    """
    assert_filter_passes(
        f.Item(key=2),
        ["foo", "bar", "baz"],
        "baz",
    )


def test_item_fail_sequence_specific_index_missing(assert_filter_errors):
    """
    The incoming sequence does not contain the specified index.
    """
    assert_filter_errors(
        f.Item(key=42),
        ["foo", "bar", "baz"],
        {"42": [f.Item.CODE_MISSING_KEY]},
    )


def test_item_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a mapping nor sequence.
    """
    assert_filter_errors(f.Item(), 42, [f.Type.CODE_WRONG_TYPE])
