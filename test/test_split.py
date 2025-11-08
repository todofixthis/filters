"""
Tests for the Split filter.
"""

import re

import regex

import filters as f


def test_split_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Split`` if you want to reject null values.
    """
    assert_filter_passes(
        f.Split(pattern="test"),
        None,
    )


def test_split_pass_char_split(assert_filter_passes):
    """
    Simplest use case is to split a string by a single character.
    """
    assert_filter_passes(
        f.Split(pattern=":"),
        "foo:bar:baz",
        ["foo", "bar", "baz"],
    )


def test_split_pass_pattern_split(assert_filter_passes):
    """
    You can also use a regex to split the string.
    """
    assert_filter_passes(
        f.Split(pattern=r"[-\d]+"),
        "foo-12-bar-34-baz",
        ["foo", "bar", "baz"],
    )


def test_split_pass_pattern_split_with_groups(assert_filter_passes):
    """
    If you include capturing parentheses in the pattern, the matched groups
    are included in the resulting list.
    """
    assert_filter_passes(
        # Note grouping parentheses in the regex.
        f.Split(pattern=r"([-\d]+)"),
        "foo-12-bar-34-baz",
        ["foo", "-12-", "bar", "-34-", "baz"],
    )


def test_split_pass_no_split(assert_filter_passes):
    """
    A string that does not match the regex at all is also considered valid.

    Use ``Split | MinLength`` if you want to require a minimum number of
    parts.
    """
    assert_filter_passes(
        f.Split(pattern=r"[-\d]+"),
        "foo:bar:baz",
        ["foo:bar:baz"],
    )


def test_split_pass_keys(assert_filter_passes):
    """
    If desired, you can map a collection of keys onto the resulting list,
    which creates a dict.
    """
    runner = assert_filter_passes(
        f.Split(
            pattern=":",
            keys=(
                "a",
                "b",
                "c",
            ),
        ),
        "foo:bar:baz",
        {
            "a": "foo",
            "b": "bar",
            "c": "baz",
        },
    )

    # The order of keys is also preserved, just in case.
    assert list(runner.cleaned_data.keys()) == ["a", "b", "c"]


# noinspection SpellCheckingInspection
def test_split_pass_precompiled_regex(assert_filter_passes):
    """
    You can alternatively provide a precompiled regex to the filter instead
    of a string pattern.
    """
    # Compile our own pattern so that we can specify the ``IGNORECASE``
    # flag.
    # Note that you are responsible for adding the ``UNICODE`` flag to your
    # compiled regex!
    # noinspection SpellCheckingInspection
    pattern = re.compile(r"\btest\b", re.IGNORECASE | re.UNICODE)

    assert_filter_passes(
        f.Split(pattern=pattern),
        "test march of the TEST penguins",
        ["", " march of the ", " penguins"],
    )


def test_split_pass_regex_library_support(assert_filter_passes):
    """
    The Regex filter also supports precompiled patterns using the ``regex``
    library.
    """
    # "Hi, there!" in Burmese, according to the internet :innocent:
    word = "\u101f\u102d\u102f\u1004\u103a\u1038!"

    # Note that :py:func:`regex.compile` automatically adds the ``UNICODE``
    # flag for you when the pattern is a unicode.
    pattern = regex.compile(r"\w+")

    assert_filter_passes(
        f.Split(pattern=pattern),
        word,
        ["", "!"],
    )


def test_split_fail_too_long(assert_filter_errors):
    """
    The incoming value has too many parts to assign a key to each one, so
    it fails validation.
    """
    assert_filter_errors(
        f.Split(
            pattern=":",
            keys=(
                "a",
                "b",
            ),
        ),
        "foo:bar:baz",
        [f.MaxLength.CODE_TOO_LONG],
    )


def test_split_pass_too_short(assert_filter_passes):
    """
    The incoming value does not have enough parts to use all the keys, so
    extra ``None`` values are inserted.

    If you want to ensure that the incoming value has exactly the right
    number of values, add a MinLength filter to the chain (you do not have
    to chain a MaxLength; the Split filter does that automatically).
    """
    assert_filter_passes(
        f.Split(
            pattern=":",
            keys=(
                "a",
                "b",
                "c",
                "d",
            ),
        ),
        "foo:bar:baz",
        {
            "a": "foo",
            "b": "bar",
            "c": "baz",
            "d": None,
        },
    )


def test_split_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(
        f.Split(pattern=""),
        b"foo bar baz",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_split_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.Split(pattern=""),
        ["foo", "bar", "baz"],
        [f.Type.CODE_WRONG_TYPE],
    )
