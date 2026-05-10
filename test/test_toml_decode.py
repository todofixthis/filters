"""
Tests for the TomlDecode filter.
"""

import filters as f


def test_toml_decode_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | TomlDecode`` if you want to reject null values.
    """
    assert_filter_passes(f.TomlDecode(), None)


def test_toml_decode_pass_valid_toml(assert_filter_passes):
    """
    The incoming value is a valid TOML string.
    """
    assert_filter_passes(
        f.TomlDecode(),
        '[server]\nhost = "localhost"\nport = 8080\n',
        {"server": {"host": "localhost", "port": 8080}},
    )


def test_toml_decode_pass_empty_document(assert_filter_passes):
    """
    An empty string is valid TOML (empty document).
    """
    assert_filter_passes(f.TomlDecode(), "", {})


def test_toml_decode_fail_invalid_toml(assert_filter_errors):
    """
    The incoming value is not valid TOML.
    """
    assert_filter_errors(
        f.TomlDecode(),
        "this is not = = valid toml",
        [f.TomlDecode.CODE_INVALID],
    )


def test_toml_decode_fail_bytes(assert_filter_errors):
    """
    Byte strings are not accepted; use a str instead.
    """
    assert_filter_errors(
        f.TomlDecode(),
        b'[server]\nhost = "localhost"\n',
        [f.Type.CODE_WRONG_TYPE],
    )


def test_toml_decode_fail_wrong_type(assert_filter_errors):
    """
    Non-string values are rejected.
    """
    assert_filter_errors(
        f.TomlDecode(),
        {"already": "a dict"},
        [f.Type.CODE_WRONG_TYPE],
    )
