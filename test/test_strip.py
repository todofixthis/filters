"""
Tests for the Strip filter.
"""

import filters as f


def test_strip_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use `Required | Strip` if you want to reject null values.
    """
    assert_filter_passes(f.Strip(), None)


def test_strip_pass_happy_path(assert_filter_passes):
    """
    The filter strips away all leading/trailing whitespace and unprintables
    from the incoming value.
    """
    assert_filter_passes(
        f.Strip(),
        "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
        "Hello, world!",
    )


def test_strip_pass_leading_only(assert_filter_passes):
    """
    You can configure the filter to strip leading characters only.
    """
    assert_filter_passes(
        f.Strip(
            trailing=None,
        ),
        "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
        "Hello, world! \x00 \t  \n  ",
    )


def test_strip_pass_trailing_only(assert_filter_passes):
    """
    You can configure the filter to strip trailing characters only.
    """
    assert_filter_passes(
        f.Strip(
            leading=None,
        ),
        "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
        "  \r  \t \x00 Hello, world!",
    )


def test_strip_pass_unicode(assert_filter_passes):
    """
    Strip also catches non-ASCII characters that are classified as
    whitespace according to Unicode.
    """
    # U+2003 is an em space.
    assert_filter_passes(
        f.Strip(),
        "\u2003Hello, world!\u2003",
        "Hello, world!",
    )


def test_strip_pass_custom_regexes(assert_filter_passes):
    """
    You can also use regexes to specify which characters get removed.
    """
    assert_filter_passes(
        f.Strip(
            leading=r"\d",
            trailing=r"['a-z ]+",
        ),
        "54321 Hello, world! i think you ought to know i'm feeling very depressed ",
        "4321 Hello, world!",
    )


def test_strip_fail_bytes(assert_filter_errors):
    """
    For backwards-compatibility with previous versions of the library, byte
    strings are not allowed.
    """
    assert_filter_errors(
        f.Strip(),
        b"    but... but... look at all of my whitespace!    ",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_strip_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.Strip(),
        ["  lots  ", "  of  ", "  whitespace  ", "  here  "],
        [f.Type.CODE_WRONG_TYPE],
    )
