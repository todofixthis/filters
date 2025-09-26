"""
Tests for the JsonDecode filter.
"""

import filters as f


def test_json_decode_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | JsonDecode`` if you want to reject null values.
    """
    assert_filter_passes(f.JsonDecode(), None)


def test_json_decode_pass_valid_json(assert_filter_passes):
    """
    The incoming value is valid JSON.
    """
    assert_filter_passes(
        f.JsonDecode(),
        '{"foo": "bar", "baz": "luhrmann"}',
        {"foo": "bar", "baz": "luhrmann"},
    )


def test_json_decode_fail_invalid_json(assert_filter_errors):
    """
    The incoming value is not valid JSON.
    """
    assert_filter_errors(
        f.JsonDecode(),
        '{"almost_valid": true',
        [f.JsonDecode.CODE_INVALID],
    )


def test_json_decode_fail_empty_string(assert_filter_errors):
    """
    The incoming value is an empty string.

    Consider using ``NotEmpty | Json`` so that users get more meaningful
    feedback for empty strings.
    """
    assert_filter_errors(f.JsonDecode(), "", [f.JsonDecode.CODE_INVALID])


def test_json_decode_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(f.JsonDecode(), b'{"blends": false}', [f.Type.CODE_WRONG_TYPE])


def test_json_decode_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(f.JsonDecode(), {"foo": "bar"}, [f.Type.CODE_WRONG_TYPE])
