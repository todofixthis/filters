"""
Tests for the CaseFold filter.
"""

import pytest

import filters as f


def test_case_fold_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | CaseFold`` if you want to reject null values.
    """
    assert_filter_passes(f.CaseFold(), None)


def test_case_fold_pass_ascii(assert_filter_passes):
    """
    The incoming value is ASCII.
    """
    assert_filter_passes(f.CaseFold(), "FOO bar BAZ", "foo bar baz")


@pytest.mark.parametrize(
    "value,expected",
    [
        # For some reason, the internet really loves to use ß to test case folding functionality.
        # noinspection SpellCheckingInspection
        ("Weißkopfseeadler", "weisskopfseeadler"),
        # Note that case-folded does not necessarily mean ASCII-compatible!
        # noinspection SpellCheckingInspection
        ("İstanbul", "i\u0307stanbul"),
    ],
)
def test_case_fold_pass_unicode(assert_filter_passes, value, expected):
    """
    The incoming value is not ASCII.
    """
    assert_filter_passes(f.CaseFold(), value, expected)


def test_case_fold_pass_unfoldable(assert_filter_passes):
    """
    There are some Unicode characters that look foldable but actually
    aren't.

    Spotify learned this the hard way:
    https://labs.spotify.com/2013/06/18/creative-usernames/
    """
    assert_filter_passes(f.CaseFold(), "\u1d2e\u1d35\u1d33\u1d2e\u1d35\u1d3f\u1d30")


def test_case_fold_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(
        f.CaseFold(),
        b"look im already folded anyway",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_case_fold_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        f.CaseFold(),
        ["Weißkopfseeadler", "İstanbul"],
        [f.Type.CODE_WRONG_TYPE],
    )
