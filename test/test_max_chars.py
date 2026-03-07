"""
Tests for the MaxChars filter.
"""

import pytest

import filters as f


def test_max_chars_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.
    """
    assert_filter_passes(f.MaxChars(max_chars=1), None)


def test_max_chars_pass_string_short(assert_filter_passes):
    """
    The string is short enough to fit within ``max_chars``.
    """
    assert_filter_passes(f.MaxChars(max_chars=13), "Hello, world!")


def test_max_chars_pass_string_short_with_prefix_and_suffix(assert_filter_passes):
    """
    Neither prefix nor suffix are applied when the incoming string is short
    enough.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=13,
            prefix="!",
            suffix="!",
        ),
        "Hello, world!",
    )


def test_max_chars_fail_string_too_long(assert_filter_errors):
    """
    The incoming string has too many characters.
    """
    assert_filter_errors(
        f.MaxChars(max_chars=12), "Hello, world!", [f.MaxChars.CODE_TOO_LONG]
    )


def test_max_chars_pass_string_truncated(assert_filter_passes):
    """
    The filter is configured to truncate too-long values.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=12,
            truncate=True,
        ),
        "Hello, world!",
        "Hello, world",
    )


def test_max_chars_pass_string_truncated_with_prefix(assert_filter_passes):
    """
    The filter is configured to apply a prefix to truncated values.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=12,
            truncate=True,
            prefix="[More] ",
        ),
        "Hello, world!",
        # Note that the prefix takes up some allowed characters.
        "[More] Hello",
    )


def test_max_chars_pass_string_truncated_with_suffix(assert_filter_passes):
    """
    The filter is configured to apply a suffix to truncated values.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=12,
            truncate=True,
            suffix="...",
        ),
        "Hello, world!",
        # Note that the suffix takes up some allowed characters.
        "Hello, wo...",
    )


def test_max_chars_pass_string_truncated_with_prefix_and_suffix(assert_filter_passes):
    """
    Putting it all together now.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxChars(
            # 'Hello world' in Vietnamese, according to the internet.
            max_chars=10,
            truncate=True,
            prefix=">> ",
            suffix="...",
        ),
        "Chào thế giới!",
        ">> Chào...",
    )


def test_max_chars_pass_string_truncated_with_prefix_max_chars_too_small(
    assert_filter_passes,
):
    """
    The filter is configured with a ``prefix`` and a ``max_chars`` value
    that is too small to fit it.

    This will probably never happen, but I've been wrong about this sort of
    thing before....
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=5,
            truncate=True,
            prefix="(more) ",
        ),
        "Hello, world!",
        "(more",
    )


def test_max_chars_pass_string_truncated_with_suffix_max_chars_too_small(
    assert_filter_passes,
):
    """
    The filter is configured with a ``suffix`` and a ``max_chars`` value
    that is too small to fit it.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=5,
            truncate=True,
            suffix=" (continued)",
        ),
        "Hello, world!",
        " (con",
    )


def test_max_chars_pass_string_truncated_with_prefix_and_suffix_max_chars_too_small(
    assert_filter_passes,
):
    """
    Because you know that SOMEONE is going to try it just to see what
    happens.
    """
    assert_filter_passes(
        f.MaxChars(
            max_chars=3,
            truncate=True,
            prefix="->",
            suffix="<-",
        ),
        "Hello, world!",
        # Suffix has priority over prefix.
        # Because I had to pick one :shrug:
        "-<-",
    )


def test_max_chars_fail_bytes(assert_filter_errors):
    """
    This filter does not accept byte strings (``bytes`` type).

    Chain with ``Unicode`` or use ``MaxBytes`` if you want to filter byte
    strings.
    """
    assert_filter_errors(
        f.MaxChars(max_chars=1000),
        b"Hello, world!",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_max_chars_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.MaxChars(max_chars=1000),
        ["foo", "bar", "baz"],
        [f.Type.CODE_WRONG_TYPE],
    )


def test_max_chars_error_max_chars_too_small():
    """
    ``max_chars`` must be at least 1.
    """
    with pytest.raises(f.FilterError):
        f.MaxChars(max_chars=0)
