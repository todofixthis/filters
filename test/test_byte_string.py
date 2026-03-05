"""
Tests for the ByteString filter.
"""

from decimal import Decimal
from xml.etree.ElementTree import Element

import filters as f
from .conftest import Bytesy, Unicody


def test_byte_string_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | ByteString`` if you want to reject null values.
    """
    assert_filter_passes(f.ByteString(), None)


def test_byte_string_pass_unicode(assert_filter_passes):
    """
    The incoming value is a unicode.
    """
    assert_filter_passes(
        f.ByteString(),
        "Iñtërnâtiônàlizætiøn",
        # 'Iñtërnâtiônàlizætiøn' encoded as bytes using utf-8:
        b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3" b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n",
    )


def test_byte_string_pass_bytes_utf8(assert_filter_passes):
    """
    The incoming value is a byte string, already encoded as UTF-8.
    """
    assert_filter_passes(
        f.ByteString(),
        b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3" b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n",
    )


def test_byte_string_fail_bytes_non_utf8(assert_filter_passes, assert_filter_errors):
    """
    The incoming value is a byte string, but encoded using a different
    codec.
    """
    # 'Iñtërnâtiônàlizætiøn' encoded as bytes using ISO-8859-1:
    incoming = b"I\xf1t\xebrn\xe2ti\xf4n\xe0liz\xe6ti\xf8n"

    assert_filter_errors(
        f.ByteString(),
        incoming,
        [f.ByteString.CODE_DECODE_ERROR],
    )

    # In order for this to work, we have to tell the filter what encoding
    # to use:
    assert_filter_passes(
        f.ByteString(encoding="iso-8859-1"),
        incoming,
        # The result is re-encoded using UTF-8.
        b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3" b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n",
    )


def test_byte_string_pass_string_like_object(assert_filter_passes):
    """
    The incoming value is an object that can be cast as a unicode.
    """
    assert_filter_passes(
        f.ByteString(),
        Unicody("༼ つ ◕_◕ ༽つ"),
        # Stoned Kirby?  Jigglypuff in dance mode?
        # I have no idea what this is.
        b"\xe0\xbc\xbc \xe3\x81\xa4 \xe2\x97\x95_"
        b"\xe2\x97\x95 \xe0\xbc\xbd\xe3\x81\xa4",
    )


def test_byte_string_pass_bytes_like_object(assert_filter_passes):
    """
    The incoming value is an object that can be cast as a byte string.
    """
    value = (
        # Person
        b"(\xe2\x95\xaf\xc2\xb0\xe2\x96\xa1\xc2\xb0)"
        # Particle Effects
        b"\xe2\x95\xaf\xef\xb8\xb5 "
        # Table
        b"\xe2\x94\xbb\xe2\x94\x81\xe2\x94\xbb"
    )

    assert_filter_passes(f.ByteString(), Bytesy(value), value)


def test_byte_string_pass_boolean(assert_filter_passes):
    """
    The incoming value is a boolean (treated as an int).
    """
    assert_filter_passes(f.ByteString(), True, b"1")


def test_byte_string_pass_decimal_with_scientific_notation(assert_filter_passes):
    """
    The incoming value is a Decimal that was parsed from scientific
    notation.
    """
    # Note that ``bytes(Decimal('2.8E6'))`` yields b'2.8E+6', which is not
    # what we want!
    assert_filter_passes(
        f.ByteString(),
        Decimal("2.8E6"),
        b"2800000",
    )


def test_byte_string_pass_xml_element(assert_filter_passes):
    """
    The incoming value is an ElementTree XML Element.
    """
    assert_filter_passes(
        f.ByteString(),
        Element("foobar"),
        b"<foobar />",
    )


def test_byte_string_unicode_normalisation_off_by_default(assert_filter_passes):
    """
    By default, the filter does not apply normalisation before encoding.

    References:
      - https://en.wikipedia.org/wiki/Unicode_equivalence
      - https://stackoverflow.com/q/16467479
    """
    assert_filter_passes(
        f.ByteString(),
        # 'e'      = U+0065 LATIN SMALL LETTER E
        # '\u0301' = U+0301 COMBINING ACUTE ACCENT
        # (2 code points)
        "Ame\u0301lie",
        # Result is the same string, encoded using UTF-8.
        b"Ame\xcc\x81lie",
    )


def test_byte_string_unicode_normalisation_forced(assert_filter_passes):
    """
    You can force the filter to apply normalisation before encoding.

    References:
      - https://en.wikipedia.org/wiki/Unicode_equivalence
      - https://stackoverflow.com/q/16467479
    """
    assert_filter_passes(
        f.ByteString(
            # Same decomposed sequence from previous test...
            # ... but this time we tell the filter to normalise the value
            # before encoding it.
            normalize=True,
        ),
        "Ame\u0301lie",
        # U+00E9 LATIN SMALL LETTER E WITH ACUTE
        # (1 code point, encoded as bytes)
        b"Am\xc3\xa9lie",
    )


def test_byte_string_remove_non_printables_off_by_default(assert_filter_passes):
    """
    By default, the filter does not remove non-printable characters.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.ByteString(),
        # \u0000-\u001f are ASCII control characters.
        # \uffff is a Unicode control character.
        "\u0010Hell\u0000o,\u001f wor\uffffld!",
        b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
    )


def test_byte_string_remove_non_printables_forced(assert_filter_passes):
    """
    You can force the filter to remove non-printable characters before
    encoding.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.ByteString(
            normalize=True,
        ),
        "\u0010Hell\u0000o,\u001f wor\uffffld!",
        b"Hello, world!",
    )


def test_byte_string_newline_normalisation_off_by_default(assert_filter_passes):
    """
    By default, the filter does not normalise line endings.
    """
    assert_filter_passes(
        f.ByteString(),
        "unix\n - windows\r\n - weird\r\r\n",
        b"unix\n - windows\r\n - weird\r\r\n",
    )


def test_byte_string_newline_normalisation_forced(assert_filter_passes):
    """
    You can force the filter to normalise line endings.
    """
    assert_filter_passes(
        f.ByteString(normalize=True),
        "unix\n - windows\r\n - weird\r\r\n",
        b"unix\n - windows\n - weird\n\n",
    )
