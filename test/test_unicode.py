"""
Tests for the Unicode filter.
"""

from decimal import Decimal
from xml.etree.ElementTree import Element

import filters as f
from .conftest import Bytesy, Unicody


def test_unicode_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Unicode`` if you want to reject null values.
    """
    assert_filter_passes(f.Unicode(), None)


def test_unicode_pass_unicode(assert_filter_passes):
    """
    The incoming value is a unicode.
    """
    assert_filter_passes(f.Unicode(), r"┻━┻︵ \(°□°)/ ︵ ┻━┻ ")  # RAWR!


def test_unicode_pass_bytes_utf8(assert_filter_passes):
    """
    The incoming value is a byte string that is encoded as UTF-8.
    """
    assert_filter_passes(
        f.Unicode(),
        # You get used to it.
        # I don't even see the code.
        # All I see is, "blond"... "brunette"... "redhead"...
        # Hey, you uh... want a drink?
        b"\xe2\x99\xaa "
        b"\xe2\x94\x8f(\xc2\xb0.\xc2\xb0)\xe2\x94\x9b "
        b"\xe2\x94\x97(\xc2\xb0.\xc2\xb0)\xe2\x94\x93 "
        b"\xe2\x99\xaa",
        "♪ ┏(°.°)┛ ┗(°.°)┓ ♪",
    )


def test_unicode_fail_bytes_non_utf8(assert_filter_passes, assert_filter_errors):
    """
    The incoming value is a byte string that is encoded using a codec other
    than UTF-8.

    References:

      - https://docs.python.org/3/howto/unicode.html
    """
    # 'Apple' in Swedish.
    # :sigh: Come on, spellcheck; where's your sense of adventure?
    # noinspection SpellCheckingInspection
    incoming = b"\xc4pple"

    assert_filter_errors(
        f.Unicode(),
        incoming,
        [f.Unicode.CODE_DECODE_ERROR],
    )

    # In order for this to work, we have to tell the filter what encoding
    # to use:
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.Unicode(encoding="iso-8859-1"),
        incoming,
        "Äpple",
    )


def test_unicode_pass_string_like_object(assert_filter_passes):
    """
    The incoming value is an object that can be cast as a string.
    """
    value = "／人 ⌒ ‿‿ ⌒ 人＼"  # Squee!

    assert_filter_passes(
        f.Unicode(),
        Unicody(value),
        value,
    )


def test_unicode_pass_bytes_like_object(assert_filter_passes):
    """
    The incoming value is an object that can be cast as a byte string.
    """
    assert_filter_passes(
        f.Unicode(),
        Bytesy(b"(\xe2\x99\xa5\xe2\x80\xbf\xe2\x99\xa5)"),
        # I can almost hear the sappy music now.
        "(♥‿♥)",
    )


def test_unicode_pass_boolean(assert_filter_passes):
    """
    The incoming value is a boolean (treated as an int).
    """
    assert_filter_passes(f.Unicode(), True, "1")


def test_unicode_pass_decimal_with_scientific_notation(assert_filter_passes):
    """
    The incoming value is a Decimal that was parsed from scientific
    notation.
    """
    # Note that `str(Decimal('2.8E6'))` yields '2.8E+6', which is not what
    # we want!
    assert_filter_passes(
        f.Unicode(),
        Decimal("2.8E6"),
        "2800000",
    )


def test_unicode_pass_xml_element(assert_filter_passes):
    """
    The incoming value is an ElementTree XML Element.
    """
    assert_filter_passes(
        f.Unicode(),
        Element("foobar"),
        "<foobar />",
    )


def test_unicode_unicode_normalisation(assert_filter_passes):
    """
    The filter always returns the NFC form of the unicode string.

    References:

      - https://en.wikipedia.org/wiki/Unicode_equivalence
      - https://stackoverflow.com/q/16467479
    """
    # 'e'      = U+0065 LATIN SMALL LETTER E
    # '\u0301' = U+0301 COMBINING ACUTE ACCENT
    # (2 code points)
    decomposed = "Ame\u0301lie"

    # U+00E9 LATIN SMALL LETTER E WITH ACUTE
    # (1 code point)
    composed = "Am\xe9lie"

    assert_filter_passes(f.Unicode(), decomposed, composed)


def test_unicode_unicode_normalisation_disabled(assert_filter_passes):
    """
    You can force the filter not to perform normalisation.
    """
    decomposed = "Ame\u0301lie"

    assert_filter_passes(
        f.Unicode(normalize=False),
        decomposed,
        decomposed,
    )


def test_unicode_remove_non_printables(assert_filter_passes):
    """
    By default, this filter also removes non-printable characters (both
    ASCII and Unicode varieties).
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.Unicode(),
        # \x00-\x1f are ASCII control characters.
        # \xef\xbf\xbf is the Unicode control character \uffff, encoded as
        # UTF-8.
        b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
        "Hello, world!",
    )


def test_unicode_remove_non_printables_disabled(assert_filter_passes):
    """
    You can force the filter not to remove non-printable characters.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.Unicode(
            normalize=False,
        ),
        b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
        "\u0010Hell\u0000o,\u001f wor\uffffld!",
    )


def test_unicode_newline_normalisation(assert_filter_passes):
    """
    By default, any newlines in the string are automatically converted to
    unix-style ('\n').
    """
    assert_filter_passes(
        f.Unicode(),
        b"unix\n - windows\r\n - weird\r\r\n",
        "unix\n - windows\n - weird\n\n",
    )


def test_unicode_newline_normalisation_disabled(assert_filter_passes):
    """
    You can force the filter not to normalise line endings.
    """
    assert_filter_passes(
        f.Unicode(
            normalize=False,
        ),
        b"unix\n - windows\r\n - weird\r\r\n",
        "unix\n - windows\r\n - weird\r\r\n",
    )
