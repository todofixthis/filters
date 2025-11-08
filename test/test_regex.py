"""
Tests for the Regex filter.
"""

import re

import regex

import filters as f


def test_regex_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Regex`` if you want to reject null values.
    """
    assert_filter_passes(f.Regex(pattern=r"."), None)


def test_regex_pass_happy_path(assert_filter_passes):
    """
    The incoming value matches the regex pattern.
    """
    assert_filter_passes(
        # Note: regexes are case-sensitive by default.
        f.Regex(
            pattern=r"\btest\b",
        ),
        "test march of the TEST penguins",
        ["test"],
    )


def test_regex_fail_no_match(assert_filter_errors):
    """
    The incoming value does not match the regex pattern.
    """
    assert_filter_errors(
        f.Regex(
            pattern=r"\btest\b",
        ),
        "contested march of the tester penguins",
        [f.Regex.CODE_INVALID],
    )


def test_regex_pass_unicode_character_class(assert_filter_passes):
    """
    By default, character classes like ``\\w`` will take unicode into
    account.
    """
    # "Hi, there!" in Japanese, according to the internet :innocent:
    word = "\u304a\u306f\u3088\u3046"

    assert_filter_passes(
        f.Regex(pattern=r"\w+"),
        word,
        [word],
    )


# noinspection SpellCheckingInspection
def test_regex_pass_precompiled_regex(assert_filter_passes):
    """
    You can alternatively provide a precompiled regex to the filter instead
    of a string pattern.
    """
    # Compile our own pattern so that we can specify the ``IGNORECASE``
    # flag.
    # Note that you are responsible for adding the ``UNICODE`` flag to your
    # compiled regex!
    pattern = re.compile(r"\btest\b", re.IGNORECASE | re.UNICODE)

    assert_filter_passes(
        f.Regex(pattern=pattern),
        "test march of the TEST penguins",
        ["test", "TEST"],
    )


def test_regex_pass_regex_library_support(assert_filter_passes):
    """
    The Regex filter also supports precompiled patterns using the ``regex``
    library.
    """
    # "Hi, there!" in Burmese, according to the internet :innocent:
    word = "\u101f\u102d\u102f\u1004\u103a\u1038"

    # Note that :py:func:`regex.compile` automatically adds the ``UNICODE``
    # flag for you when the pattern is a unicode.
    pattern = regex.compile(r"\w+")

    assert_filter_passes(
        f.Regex(pattern=pattern),
        word,
        [word],
    )


def test_regex_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(
        f.Regex(pattern=r"."),
        b"Aw, come on; it'll be fun!",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_regex_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.Regex(pattern=r"."),
        ["totally", "valid", "right?"],
        [f.Type.CODE_WRONG_TYPE],
    )
