import re
from codecs import BOM_UTF16
from decimal import Decimal
from uuid import UUID
from xml.etree.ElementTree import Element

import regex

import filters as f
from filters.base import FilterError
from filters.test import BaseFilterTestCase
from test.test_simple import Bytesy, Unicody


class Base64DecodeTestCase(BaseFilterTestCase):
    filter_type = f.Base64Decode

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Base64Decode`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_valid(self):
        """
        The incoming value is Base64-encoded.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(b"SGVsbG8sIHdvcmxkIQ==", b"Hello, world!")

    def test_pass_url_safe(self):
        """
        The incoming value is Base64-encoded using a URL-safe variant.
        """
        self.assertFilterPasses(
            b"--___w==",
            b"\xfb\xef\xff\xff",
        )

    def test_fail_mixed_dialects(self):
        """
        The incoming value contains both URL-safe and URL-unsafe characters.
        """
        self.assertFilterErrors(b"+-_/_w==", [f.Base64Decode.CODE_INVALID])

    def test_pass_whitespace(self):
        """
        The incoming value includes whitespace characters.

        Technically, whitespace chars are not part of the Base64 alphabet.
        But, virtually every implementation includes support for whitespace, so
        we will, too.
        """
        self.assertFilterPasses(
            # Tab chars are especially weird, but eh, why not..
            b"SGV sbG 8sI\tHdv\ncmx\rkIQ\r\n",
            b"Hello, world!",
        )

    def test_pass_padding_missing(self):
        """
        The incoming value is Base64-encoded, but it has the wrong length.

        Base64 works by splitting up the string into chunks of 3 bytes (24
        bits) each, then dividing each chunk into 4 smaller chunks of 6 bits
        each.  If the string's length is not divisible by 3, then the last
        chunk will have too few bytes, so we have to pad it out.

        References:
          - https://en.wikipedia.org/wiki/Base64#Padding
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(b"SGVsbG8sIHdvcmxkIQ", b"Hello, world!")

    def test_pass_padding_excessive(self):
        """
        The incoming value is Base64-encoded, but for some reason it has too
        much padding.

        This is weird, but it doesn't prevent the filter from decoding the
        value, so the filter agrees to turn a conspiratorial blind eye.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(b"SGVsbG8sIHdvcmxkIQ=====", b"Hello, world!")

    def test_fail_invalid(self):
        """
        The incoming value contains values that are not compatible with
        Base64.
        """
        self.assertFilterErrors(
            b"$Hello, world!===$",
            [f.Base64Decode.CODE_INVALID],
        )

    def test_fail_string(self):
        """
        For parity with :py:func:`codecs.decode`, unicode strings are not
        allowed; only binary strings can be decoded.

        To decode unicode strings, chain this filter with ``ByteString``:

        .. code-block:: python

           runner = f.FilterRunner(f.ByteString | f.Base64Decode)
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            "SGVsbG8sIHdvcmxkIQ==",
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            [b"kB1ReXKFSE5xgu0sODTVrJWg4eYDz32iRLm+fATfsBQ="],
            [f.Type.CODE_WRONG_TYPE],
        )


class ByteStringTestCase(BaseFilterTestCase):
    filter_type = f.ByteString

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | ByteString`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_unicode(self):
        """
        The incoming value is a unicode.
        """
        self.assertFilterPasses(
            "Iñtërnâtiônàlizætiøn",
            # 'Iñtërnâtiônàlizætiøn' encoded as bytes using utf-8:
            b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3"
            b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n",
        )

    def test_pass_bytes_utf8(self):
        """
        The incoming value is a byte string, already encoded as UTF-8.
        """
        self.assertFilterPasses(
            b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3" b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n"
        )

    def test_fail_bytes_non_utf8(self):
        """
        The incoming value is a byte string, but encoded using a different
        codec.
        """
        # 'Iñtërnâtiônàlizætiøn' encoded as bytes using ISO-8859-1:
        incoming = b"I\xf1t\xebrn\xe2ti\xf4n\xe0liz\xe6ti\xf8n"

        self.assertFilterErrors(
            incoming,
            [f.ByteString.CODE_DECODE_ERROR],
        )

        # In order for this to work, we have to tell the filter what encoding
        # to use:
        self.assertFilterPasses(
            self._filter(incoming, encoding="iso-8859-1"),
            # The result is re-encoded using UTF-8.
            b"I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3"
            b"\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n",
        )

    def test_pass_string_like_object(self):
        """
        The incoming value is an object that can be cast as a unicode.
        """
        self.assertFilterPasses(
            Unicody("༼ つ ◕_◕ ༽つ"),
            # Stoned Kirby?  Jigglypuff in dance mode?
            # I have no idea what this is.
            b"\xe0\xbc\xbc \xe3\x81\xa4 \xe2\x97\x95_"
            b"\xe2\x97\x95 \xe0\xbc\xbd\xe3\x81\xa4",
        )

    def test_pass_bytes_like_object(self):
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

        self.assertFilterPasses(Bytesy(value), value)

    def test_pass_boolean(self):
        """
        The incoming value is a boolean (treated as an int).
        """
        self.assertFilterPasses(True, b"1")

    def test_pass_decimal_with_scientific_notation(self):
        """
        The incoming value is a Decimal that was parsed from scientific
        notation.
        """
        # Note that ``bytes(Decimal("2.8E6"))`` yields b"2.8E+6", which is not
        # what we want!
        self.assertFilterPasses(
            Decimal("2.8E6"),
            b"2800000",
        )

    def test_pass_xml_element(self):
        """
        The incoming value is an ElementTree XML Element.
        """
        self.assertFilterPasses(
            Element("foobar"),
            b"<foobar />",
        )

    def test_unicode_normalization_off_by_default(self):
        """
        By default, the filter does not apply normalization before encoding.

        References:
          - https://en.wikipedia.org/wiki/Unicode_equivalence
          - https://stackoverflow.com/q/16467479
        """
        self.assertFilterPasses(
            # 'e'      = U+0065 LATIN SMALL LETTER E
            # '\u0301' = U+0301 COMBINING ACUTE ACCENT
            # (2 code points)
            "Ame\u0301lie",
            # Result is the same string, encoded using UTF-8.
            b"Ame\xcc\x81lie",
        )

    def test_unicode_normalization_forced(self):
        """
        You can force the filter to apply normalization before encoding.

        References:
          - https://en.wikipedia.org/wiki/Unicode_equivalence
          - https://stackoverflow.com/q/16467479
        """
        self.assertFilterPasses(
            self._filter(
                # Same decomposed sequence from previous test...
                "Ame\u0301lie",
                # ... but this time we tell the filter to normalize the value
                # before encoding it.
                normalize=True,
            ),
            # U+00E9 LATIN SMALL LETTER E WITH ACUTE
            # (1 code point, encoded as bytes)
            b"Am\xc3\xa9lie",
        )

    def test_remove_non_printables_off_by_default(self):
        """
        By default, the filter does not remove non-printable characters.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            # \u0000-\u001f are ASCII control characters.
            # \uffff is a Unicode control character.
            "\u0010Hell\u0000o,\u001f wor\uffffld!",
            b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
        )

    def test_remove_non_printables_forced(self):
        """
        You can force the filter to remove non-printable characters before
        encoding.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "\u0010Hell\u0000o,\u001f wor\uffffld!",
                normalize=True,
            ),
            b"Hello, world!",
        )

    def test_newline_normalization_off_by_default(self):
        """
        By default, the filter does not normalize line endings.
        """
        self.assertFilterPasses(
            "unix\n - windows\r\n - weird\r\r\n",
            b"unix\n - windows\r\n - weird\r\r\n",
        )

    def test_newline_normalization_forced(self):
        """
        You can force the filter to normalize line endings.
        """
        self.assertFilterPasses(
            self._filter("unix\n - windows\r\n - weird\r\r\n", normalize=True),
            b"unix\n - windows\n - weird\n\n",
        )


class CaseFoldTestCase(BaseFilterTestCase):
    filter_type = f.CaseFold

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | CaseFold`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_ascii(self):
        """
        The incoming value is ASCII.
        """
        self.assertFilterPasses("FOO bar BAZ", "foo bar baz")

    def test_pass_unicode(self):
        """
        The incoming value is not ASCII.
        """
        # For some reason, the internet really loves to use ß to test case
        # folding functionality.
        # noinspection SpellCheckingInspection
        self.assertFilterPasses("Weißkopfseeadler", "weisskopfseeadler")

        # Note that case-folded does not necessarily mean ASCII-compatible!
        # noinspection SpellCheckingInspection
        self.assertFilterPasses("İstanbul", "i\u0307stanbul")

    def test_pass_unfoldable(self):
        """
        There are some Unicode characters that look foldable but actually
        aren't.

        Spotify learned this the hard way:
        https://labs.spotify.com/2013/06/18/creative-usernames/
        """
        self.assertFilterPasses("\u1d2e\u1d35\u1d33\u1d2e\u1d35\u1d3f\u1d30")

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(
            b"look im already folded anyway",
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            ["Weißkopfseeadler", "İstanbul"],
            [f.Type.CODE_WRONG_TYPE],
        )


class ChoiceTestCase(BaseFilterTestCase):
    filter_type = f.Choice

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Choice`` if you want to reject null values.
        """
        self.assertFilterPasses(
            self._filter(None, choices=("anything",)),
        )

    def test_pass_valid(self):
        """
        The incoming value matches one of the choices.
        """
        self.assertFilterPasses(
            self._filter("Curly", choices=("Moe", "Larry", "Curly")),
        )

    def test_fail_invalid(self):
        """
        The incoming value does not match any of the choices.
        """
        self.assertFilterErrors(
            self._filter("Shemp", choices=("Moe", "Larry", "Curly")),
            [f.Choice.CODE_INVALID],
        )

    def test_pass_case_insensitive_valid(self):
        """
        The incoming value matches a choice using case-insensitive comparison.
        """
        self.assertFilterPasses(
            self._filter(
                "mOE",
                choices=("Moe", "Larry", "Curly"),
                case_sensitive=False,
            ),
            # The ``choices`` passed to the filter initialiser define the
            # canonical choices.
            "Moe",
        )

    def test_fail_case_insensitive_type_mismatch(self):
        """
        The incoming value has a different type, so it does not match.
        """
        self.assertFilterErrors(
            self._filter(42, choices=("42",), case_sensitive=False),
            [f.Choice.CODE_INVALID],
        )

    def test_error_choices_empty(self):
        """
        The filter must be configured with at least one valid choice.
        """
        self.assertRaises(FilterError, lambda: self.filter_type(choices=[]))


class IpAddressTestCase(BaseFilterTestCase):
    filter_type = f.IpAddress

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | IpAddress`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_ipv4_success_happy_path(self):
        """
        The incoming value is a valid IPv4 address.
        """
        self.assertFilterPasses("127.0.0.1")

    def test_ipv4_error_invalid(self):
        """
        The incoming value is not a valid IPv4 address.
        """
        self.assertFilterErrors("127.0.0.1/32", [f.IpAddress.CODE_INVALID])
        self.assertFilterErrors("256.0.0.1", [f.IpAddress.CODE_INVALID])
        self.assertFilterErrors("-1.0.0.1", [f.IpAddress.CODE_INVALID])

    def test_ipv4_error_too_short(self):
        """
        Technically, an IPv4 address can contain less than 4 octets, but this
        filter always expects exactly 4.
        """
        self.assertFilterErrors("127.1", [f.IpAddress.CODE_INVALID])

    def test_ipv4_error_too_long(self):
        """
        The incoming value looks like an IPv4 address, except it contains too
        many octets.
        """
        self.assertFilterErrors("127.0.0.1.32", [f.IpAddress.CODE_INVALID])

    def test_ipv4_error_ipv6(self):
        """
        By default, this filter does not accept IPv6 addresses.
        """
        self.assertFilterErrors(
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            [f.IpAddress.CODE_INVALID],
        )

    def test_ipv6_success_happy_path(self):
        """
        The incoming value is a valid IPv6 address.
        """
        self.assertFilterPasses(
            self._filter(
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                # You must explicitly configure the filter to accept IPv6
                # addresses.
                ipv4=False,
                ipv6=True,
            ),
            # Note that the resulting value is automatically abbreviated, if
            # possible.
            # https://en.wikipedia.org/wiki/IPv6_address#Presentation
            "2001:db8:85a3::8a2e:370:7334",
        )

    def test_ipv6_success_case_insensitive(self):
        """
        The incoming value uses mixed case for hex characters.
        """
        self.assertFilterPasses(
            self._filter(
                "2001:0DB8:85A3:0000:0000:8a2e:0370:7334",
                ipv4=False,
                ipv6=True,
            ),
            "2001:db8:85a3::8a2e:370:7334",
        )

    def test_ipv6_success_truncated_zeroes(self):
        """
        IPv6 supports truncating leading zeroes.
        """
        self.assertFilterPasses(
            self._filter(
                "2001:db8:85a3:0:0:8a2e:370:7334",
                ipv4=False,
                ipv6=True,
            ),
            "2001:db8:85a3::8a2e:370:7334",
        )

    def test_ipv6_success_truncated_groups(self):
        """
        Empty groups (all zeroes) can be omitted entirely.
        """
        self.assertFilterPasses(
            self._filter(
                "2001:db8:85a3::8a2e:370:7334",
                ipv4=False,
                ipv6=True,
            ),
        )

    def test_ipv6_success_dotted_quad(self):
        """
        IPv6 supports "dotted quad" notation for IPv4 addresses that are
        mid-transition.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter("::ffff:192.0.2.128", ipv4=False, ipv6=True),
        )

    def test_ipv6_error_invalid(self):
        """
        Invalid IPv6 address is invalid.
        """
        self.assertFilterErrors(
            self._filter("not even close", ipv4=False, ipv6=True),
            [f.IpAddress.CODE_INVALID],
        )

    def test_ipv6_error_too_long(self):
        """
        If the incoming value has too many groups to be IPv6, it is invalid.
        """
        self.assertFilterErrors(
            self._filter(
                # Oops; one group too many!
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334:1234",
                ipv4=False,
                ipv6=True,
            ),
            [f.IpAddress.CODE_INVALID],
        )

    def test_ipv6_error_ipv4(self):
        """
        If the filter is configured only to accept IPv6 addresses, IPv4
        addresses are invalid.
        """
        self.assertFilterErrors(
            self._filter("127.0.0.1", ipv4=False, ipv6=True),
            [f.IpAddress.CODE_INVALID],
        )

    def test_pass_allow_ipv4_and_ipv6(self):
        """
        You can configure the filter to accept both IPv4 and IPv6 addresses.
        """
        self.assertFilterPasses(
            self._filter("127.0.0.1", ipv4=True, ipv6=True),
        )

        self.assertFilterPasses(
            self._filter(
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                ipv4=True,
                ipv6=True,
            ),
            "2001:db8:85a3::8a2e:370:7334",
        )

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(b"127.0.0.1", [f.Type.CODE_WRONG_TYPE])

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            ["127.0.0.1", "192.168.1.1"],
            [f.Type.CODE_WRONG_TYPE],
        )


class JsonDecodeTestCase(BaseFilterTestCase):
    filter_type = f.JsonDecode

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | JsonDecode`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_valid_json(self):
        """
        The incoming value is valid JSON.
        """
        self.assertFilterPasses(
            '{"foo": "bar", "baz": "luhrmann"}',
            {"foo": "bar", "baz": "luhrmann"},
        )

    def test_fail_invalid_json(self):
        """
        The incoming value is not valid JSON.
        """
        self.assertFilterErrors(
            '{"almost_valid": true',
            [f.JsonDecode.CODE_INVALID],
        )

    def test_fail_empty_string(self):
        """
        The incoming value is an empty string.

        Consider using ``NotEmpty | Json`` so that users get more meaningful
        feedback for empty strings.
        """
        self.assertFilterErrors("", [f.JsonDecode.CODE_INVALID])

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(b'{"blends": false}', [f.Type.CODE_WRONG_TYPE])

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors({"foo": "bar"}, [f.Type.CODE_WRONG_TYPE])


class MaxBytesTestCase(BaseFilterTestCase):
    filter_type = f.MaxBytes

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | MaxBytes`` if you want to reject null values.
        """
        self.assertFilterPasses(self._filter(None, max_bytes=1))

    def test_pass_string_short(self):
        """
        The incoming value is a string that is short enough.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter("Γειάσου Κόσμε", max_bytes=25),
            # The filter always returns bytes.
            "Γειάσου Κόσμε".encode("utf-8"),
        )

    def test_pass_string_short_with_prefix(self):
        """
        The filter is configured to apply a prefix to values that are too long,
        but the incoming value is a unicode string that is short enough.
        """
        # If we were to apply the prefix to the incoming string, it
        # would be too long to fit, but the filter will only apply
        # the prefix if the value needs to be truncated.
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=25,
                truncate=True,
                prefix="σφάλμα:",
            ),
            # The filter always returns bytes.
            "Γειάσου Κόσμε".encode("utf-8"),
        )

    def test_pass_string_short_with_suffix(self):
        """
        The filter is configured to apply a suffix to values that are too long,
        but the incoming value is a unicode string that is short enough.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=25,
                truncate=True,
                suffix=" (σφάλμα)",
            ),
            # The filter always returns bytes.
            "Γειάσου Κόσμε".encode("utf-8"),
        )

    def test_fail_string_too_long(self):
        """
        The incoming value is a string that is too long.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            self._filter("Γειάσου Κόσμε", max_bytes=24),
            [f.MaxBytes.CODE_TOO_LONG],
        )

    def test_pass_string_truncated(self):
        """
        The incoming value is a string that is too long, and the filter is
        configured to truncate it.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter("Γειάσου Κόσμε", max_bytes=24, truncate=True),
            # Note that the resulting value is truncated to 23 bytes
            # instead of 24, so as not to orphan a multibyte
            # sequence.
            b"\xce\x93\xce\xb5\xce\xb9\xce\xac\xcf\x83\xce\xbf"
            b"\xcf\x85 \xce\x9a\xcf\x8c\xcf\x83\xce\xbc",
        )

    def test_pass_string_truncated_with_prefix(self):
        """
        The incoming value is a string that is too long, and the filter is
        configured to apply a prefix before truncating.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε", max_bytes=24, truncate=True, prefix="σφάλμα:"
            ),
            # Note that the prefix reduces the number of bytes available when
            # truncating the value.
            expected_value=b"\xcf\x83\xcf\x86\xce\xac\xce\xbb\xce\xbc\xce\xb1:"  # Prefix
                           b"\xce\x93\xce\xb5\xce\xb9\xce\xac\xcf\x83",
        )

    def test_pass_string_truncated_with_suffix(self):
        """
        The incoming value is a string that is too long, and the filter is
        configured to apply a suffix after truncating.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "หวัดดีชาวโลก",
                max_bytes=30,
                truncate=True,
                suffix=" (อีก)",
            ),
            expected_value=b"\xe0\xb8\xab\xe0\xb8\xa7\xe0\xb8\xb1"
                           b"\xe0\xb8\x94\xe0\xb8\x94\xe0\xb8\xb5"
                           b" (\xe0\xb8\xad\xe0\xb8\xb5\xe0\xb8\x81)",  # Suffix
        )

    def test_pass_string_truncated_max_bytes_param_too_small(self):
        """
        The filter is configured with a ``max_bytes`` so tiny that it is
        impossible to fit any multibyte sequences into a truncated string.

        This will probably never happen outside of this unit test, but if
        there's one thing I've learned, it's that customers never walk into a
        bar and simply order a beer.
        """
        self.assertFilterPasses(
            self._filter(
                "你好，世界！",
                max_bytes=2,
                truncate=True,
                prefix="更多",
                suffix="更多",
            ),
            # The filter returns an empty string, not `None`.
            expected_value=b"",
        )

    def test_pass_string_truncated_max_bytes_param_almost_too_small(self):
        """
        The filter is configured with ``max_bytes`` so tiny that it is
        impossible to fit any multibyte sequences into a truncated string...
        but just big enough to fit in some prefix+suffix.

        Why do I do this to myself?
        """
        self.assertFilterPasses(
            self._filter(
                "你好，世界！",
                max_bytes=3,
                truncate=True,
                prefix="->",
                suffix="<-",
            ),
            # The suffix has priority over the prefix.
            # Because I had to pick one :shrug:
            expected_value=b"-<-",
        )

    def test_pass_string_short_alt_encoding(self):
        """
        The filter is configured to use an encoding other than UTF-8, and the
        incoming value is a string that is short enough.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=13,
                truncate=True,
                encoding="iso-8859-7",
            ),
            # The resulting value is encoded using ISO-8859-7 (Latin-1 Greek).
            b"\xc3\xe5\xe9\xdc\xf3\xef\xf5 \xca\xfc\xf3\xec\xe5",
        )

    def test_fail_string_too_long_alt_encoding_has_bom(self):
        """
        The filter is configured to use an encoding that uses a BOM, and the
        incoming value is a string that is too long.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=27,
                encoding="utf-16",
            ),
            [f.MaxBytes.CODE_TOO_LONG],
        )

    def test_pass_string_truncated_alt_encoding_has_bom(self):
        """
        The filter is configured to use an encoding that uses a BOM, and the
        incoming value is a string that will be truncated.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=13,
                truncate=True,
                encoding="utf-16",
            ),
            # End result is only 12 bytes instead of 13 because UTF-16 uses 2
            # bytes per character.
            expected_value=BOM_UTF16
                           + b"\x93\x03\xb5\x03\xb9\x03\xac\x03\xc3\x03",
            # Truncated string
        )

    def test_pass_string_truncated_alt_encoding_has_bom_with_prefix(self):
        """
        The filter is configured to use an encoding that uses a BOM, and to
        apply a prefix to truncated values.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "Γειάσου Κόσμε",
                max_bytes=18,
                truncate=True,
                prefix="σφάλμα:",
                encoding="utf-16",
            ),
            # Note that the BOM is only applied once.
            expected_value=BOM_UTF16 +
                           # Prefix:
                           b"\xc3\x03\xc6\x03\xac\x03\xbb" b"\x03\xbc\x03\xb1\x03:\x00"
                           # Truncated string:
                           b"\x93\x03",
        )

    def test_pass_string_truncated_alt_encoding_has_bom_with_suffix(self):
        """
        The filter is configured to use an encoding that uses a BOM, and to
        apply a suffix to the truncated values.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "หวัดดีชาวโลก",
                max_bytes=20,
                truncate=True,
                suffix=" (อีก)",
                encoding="utf-16",
            ),
            expected_value=BOM_UTF16 + b"+\x0e'\x0e1\x0e"  # Truncated string
                                       b" \x00(\x00-\x0e5\x0e\x01\x0e)\x00",  # Suffix
        )

    def test_pass_string_truncated_alt_encoding_has_bom_with_prefix_and_suffix(self):
        """
        Because my life wasn't hard enough already...
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                "मैं अपने आप से ऐसा क्यों करता हूं?",
                max_bytes=40,
                truncate=True,
                prefix="[अधिक] ",
                suffix=" (अधिक)",
                encoding="utf-16",
            ),
            expected_value=BOM_UTF16 + b"[\x00\x05\t'\t?\t\x15\t]\x00 \x00"  # Prefix
                                       b".\tH\t\x02\t \x00\x05\t"  # Truncated string
                                       b" \x00(\x00\x05\t'\t?\t\x15\t)\x00",  # Suffix
        )

    def test_pass_string_truncated_max_bytes_param_almost_too_small_alt_encoding_has_bom(
        self,
    ):
        """
        Unrealistically tiny ``max_bytes``, part 2: the revenge!
        """
        self.assertFilterPasses(
            self._filter(
                "你好，世界！",
                max_bytes=4,
                truncate=True,
                prefix=">",
                suffix="<",
                encoding="utf-16",
            ),
            # The suffix has priority over the prefix.
            # Because I had to pick one :shrug:
            expected_value=BOM_UTF16 + b"<\x00",
        )

    def test_pass_bytes_short(self):
        """
        The incoming value is a byte string that is short enough.
        """
        self.assertFilterPasses(
            self._filter(
                b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c"
                b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
                max_bytes=18,
            ),
        )

    def test_fail_bytes_long(self):
        """
        The incoming value is a byte string that is too long.
        """
        self.assertFilterErrors(
            self._filter(
                b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c"
                b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
                max_bytes=17,
            ),
            [f.MaxBytes.CODE_TOO_LONG],
        )

    def test_pass_bytes_truncated(self):
        """
        The incoming value is a byte string that is too long, and the filter is
        configured to truncate.
        """
        self.assertFilterPasses(
            self._filter(
                b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c"
                b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
                max_bytes=17,
                truncate=True,
            ),
            # Note that the resulting value is truncated to 15 bytes instead of
            # 17, so as not to orphan a multibyte sequence.
            expected_value=b"\xe4\xbd\xa0\xe5\xa5\xbd\xef"
                           b"\xbc\x8c\xe4\xb8\x96\xe7\x95\x8c",
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            self._filter(["foo", "bar"], max_bytes=32),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_error_max_bytes_too_small(self):
        """
        ``max_bytes`` must be at least 1.
        """
        self.assertRaises(FilterError, lambda: self.filter_type(max_bytes=0))


class MaxCharsTestCase(BaseFilterTestCase):
    filter_type = f.MaxChars

    def test_pass_none(self):
        """
        ``None`` always passes this filter.
        """
        self.assertFilterPasses(self._filter(None, max_chars=1))

    def test_pass_string_short(self):
        """
        The string is short enough to fit within ``max_chars``.
        """
        self.assertFilterPasses(self._filter("Hello, world!", max_chars=13))

    def test_pass_string_short_with_prefix_and_suffix(self):
        """
        Neither prefix nor suffix are applied when the incoming string is short
        enough.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=13,
                prefix="!",
                suffix="!",
            ),
        )

    def test_fail_string_too_long(self):
        """
        The incoming string has too many characters.
        """
        self.assertFilterErrors(
            self._filter("Hello, world!", max_chars=12), [f.MaxChars.CODE_TOO_LONG]
        )

    def test_pass_string_truncated(self):
        """
        The filter is configured to truncate too-long values.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=12,
                truncate=True,
            ),
            "Hello, world",
        )

    def test_pass_string_truncated_with_prefix(self):
        """
        The filter is configured to apply a prefix to truncated values.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=12,
                truncate=True,
                prefix="[More] ",
            ),
            # Note that the prefix takes up some allowed characters.
            "[More] Hello",
        )

    def test_pass_string_truncated_with_suffix(self):
        """
        The filter is configured to apply a suffix to truncated values.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=12,
                truncate=True,
                suffix="...",
            ),
            # Note that the suffix takes up some allowed characters.
            "Hello, wo...",
        )

    def test_pass_string_truncated_with_prefix_and_suffix(self):
        """
        Putting it all together now.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                # 'Hello world' in Vietnamese, according to the internet.
                "Chào thế giới!",
                max_chars=10,
                truncate=True,
                prefix=">> ",
                suffix="...",
            ),
            ">> Chào...",
        )

    def test_pass_string_truncated_with_prefix_max_chars_too_small(self):
        """
        The filter is configured with a ``prefix`` and a ``max_chars`` value
        that is too small to fit it.

        This will probably never happen, but I've been wrong about this sort of
        thing before....
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=5,
                truncate=True,
                prefix="(more) ",
            ),
            "(more",
        )

    def test_pass_string_truncated_with_suffix_max_chars_too_small(self):
        """
        The filter is configured with a ``suffix`` and a ``max_chars`` value
        that is too small to fit it.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=5,
                truncate=True,
                suffix=" (continued)",
            ),
            " (con",
        )

    def test_pass_string_truncated_with_prefix_and_suffix_max_chars_too_small(self):
        """
        Because you know that SOMEONE is going to try it just to see what
        happens.
        """
        self.assertFilterPasses(
            self._filter(
                "Hello, world!",
                max_chars=3,
                truncate=True,
                prefix="->",
                suffix="<-",
            ),
            # Suffix has priority over prefix.
            # Because I had to pick one :shrug:
            "-<-",
        )

    def test_fail_bytes(self):
        """
        This filter does not accept byte strings (``bytes`` type).

        Chain with ``Unicode`` or use ``MaxBytes`` if you want to filter byte
        strings.
        """
        self.assertFilterErrors(
            self._filter(b"Hello, world!", max_chars=1000),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            self._filter(["foo", "bar", "baz"], max_chars=1000),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_error_max_chars_too_small(self):
        """
        ``max_chars`` must be at least 1.
        """
        self.assertRaises(FilterError, lambda: self.filter_type(max_chars=0))


class RegexTestCase(BaseFilterTestCase):
    filter_type = f.Regex

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Regex`` if you want to reject null values.
        """
        self.assertFilterPasses(self._filter(None, pattern=r"."))

    def test_pass_happy_path(self):
        """
        The incoming value matches the regex pattern.
        """
        self.assertFilterPasses(
            # Note: regexes are case-sensitive by default.
            self._filter(
                "test march of the TEST penguins",
                pattern=r"\btest\b",
            ),
            ["test"],
        )

    def test_fail_no_match(self):
        """
        The incoming value does not match the regex pattern.
        """
        self.assertFilterErrors(
            self._filter(
                "contested march of the tester penguins",
                pattern=r"\btest\b",
            ),
            [f.Regex.CODE_INVALID],
        )

    def test_pass_unicode_character_class(self):
        """
        By default, character classes like ``\\w`` will take unicode into
        account.
        """
        # "Hi, there!" in Japanese, according to the internet :innocent:
        word = "\u304a\u306f\u3088\u3046"

        self.assertFilterPasses(
            self._filter(word, pattern=r"\w+"),
            [word],
        )

    # noinspection SpellCheckingInspection
    def test_pass_precompiled_regex(self):
        """
        You can alternatively provide a precompiled regex to the filter instead
        of a string pattern.
        """
        # Compile our own pattern so that we can specify the ``IGNORECASE``
        # flag.
        # Note that you are responsible for adding the ``UNICODE`` flag to your
        # compiled regex!
        pattern = re.compile(r"\btest\b", re.IGNORECASE | re.UNICODE)

        self.assertFilterPasses(
            self._filter("test march of the TEST penguins", pattern=pattern),
            ["test", "TEST"],
        )

    def test_pass_regex_library_support(self):
        """
        The Regex filter also supports precompiled patterns using the ``regex``
        library.
        """
        # "Hi, there!" in Burmese, according to the internet :innocent:
        word = "\u101f\u102d\u102f\u1004\u103a\u1038"

        # Note that :py:func:`regex.compile` automatically adds the ``UNICODE``
        # flag for you when the pattern is a unicode.
        pattern = regex.compile(r"\w+")

        self.assertFilterPasses(
            self._filter(word, pattern=pattern),
            [word],
        )

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(
            self._filter(b"Aw, come on; it'll be fun!", pattern=r"."),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            self._filter(["totally", "valid", "right?"], pattern=r"."),
            [f.Type.CODE_WRONG_TYPE],
        )


class SplitTestCase(BaseFilterTestCase):
    filter_type = f.Split

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Split`` if you want to reject null values.
        """
        self.assertFilterPasses(
            self._filter(None, pattern="test"),
        )

    def test_pass_char_split(self):
        """
        Simplest use case is to split a string by a single character.
        """
        self.assertFilterPasses(
            self._filter("foo:bar:baz", pattern=":"),
            ["foo", "bar", "baz"],
        )

    def test_pass_pattern_split(self):
        """
        You can also use a regex to split the string.
        """
        self.assertFilterPasses(
            self._filter("foo-12-bar-34-baz", pattern=r"[-\d]+"),
            ["foo", "bar", "baz"],
        )

    def test_pass_pattern_split_with_groups(self):
        """
        If you include capturing parentheses in the pattern, the matched groups
        are included in the resulting list.
        """
        self.assertFilterPasses(
            # Note grouping parentheses in the regex.
            self._filter("foo-12-bar-34-baz", pattern=r"([-\d]+)"),
            ["foo", "-12-", "bar", "-34-", "baz"],
        )

    def test_pass_no_split(self):
        """
        A string that does not match the regex at all is also considered valid.

        Use ``Split | MinLength`` if you want to require a minimum number of
        parts.
        """
        self.assertFilterPasses(
            self._filter("foo:bar:baz", pattern=r"[-\d]+"),
            ["foo:bar:baz"],
        )

    def test_pass_keys(self):
        """
        If desired, you can map a collection of keys onto the resulting list,
        which creates a dict.
        """
        runner = self.assertFilterPasses(
            self._filter(
                "foo:bar:baz",
                pattern=":",
                keys=(
                    "a",
                    "b",
                    "c",
                ),
            ),
            {
                "a": "foo",
                "b": "bar",
                "c": "baz",
            },
        )

        # The order of keys is also preserved, just in case.
        self.assertListEqual(
            list(runner.cleaned_data.keys()),
            ["a", "b", "c"],
        )

    # noinspection SpellCheckingInspection
    def test_pass_precompiled_regex(self):
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

        self.assertFilterPasses(
            self._filter("test march of the TEST penguins", pattern=pattern),
            ["", " march of the ", " penguins"],
        )

    def test_pass_regex_library_support(self):
        """
        The Regex filter also supports precompiled patterns using the ``regex``
        library.
        """
        # "Hi, there!" in Burmese, according to the internet :innocent:
        word = "\u101f\u102d\u102f\u1004\u103a\u1038!"

        # Note that :py:func:`regex.compile` automatically adds the ``UNICODE``
        # flag for you when the pattern is a unicode.
        pattern = regex.compile(r"\w+")

        self.assertFilterPasses(
            self._filter(word, pattern=pattern),
            ["", "!"],
        )

    def test_fail_too_long(self):
        """
        The incoming value has too many parts to assign a key to each one, so
        it fails validation.
        """
        self.assertFilterErrors(
            self._filter(
                "foo:bar:baz",
                pattern=":",
                keys=(
                    "a",
                    "b",
                ),
            ),
            [f.MaxLength.CODE_TOO_LONG],
        )

    def test_pass_too_short(self):
        """
        The incoming value does not have enough parts to use all the keys, so
        extra ``None`` values are inserted.

        If you want to ensure that the incoming value has exactly the right
        number of values, add a MinLength filter to the chain (you do not have
        to chain a MaxLength; the Split filter does that automatically).
        """
        self.assertFilterPasses(
            self._filter(
                "foo:bar:baz",
                pattern=":",
                keys=(
                    "a",
                    "b",
                    "c",
                    "d",
                ),
            ),
            {
                "a": "foo",
                "b": "bar",
                "c": "baz",
                "d": None,
            },
        )

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(
            self._filter(b"foo bar baz", pattern=""),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            self._filter(["foo", "bar", "baz"], pattern=""),
            [f.Type.CODE_WRONG_TYPE],
        )


class StripTestCase(BaseFilterTestCase):
    filter_type = f.Strip

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use `Required | Strip` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_happy_path(self):
        """
        The filter strips away all leading/trailing whitespace and unprintables
        from the incoming value.
        """
        self.assertFilterPasses(
            "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
            "Hello, world!",
        )

    def test_pass_leading_only(self):
        """
        You can configure the filter to strip leading characters only.
        """
        self.assertFilterPasses(
            self._filter(
                "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
                trailing=None,
            ),
            "Hello, world! \x00 \t  \n  ",
        )

    def test_pass_trailing_only(self):
        """
        You can configure the filter to strip trailing characters only.
        """
        self.assertFilterPasses(
            self._filter(
                "  \r  \t \x00 Hello, world! \x00 \t  \n  ",
                leading=None,
            ),
            "  \r  \t \x00 Hello, world!",
        )

    def test_pass_unicode(self):
        """
        Strip also catches non-ASCII characters that are classified as
        whitespace according to Unicode.
        """
        # U+2003 is an em space.
        self.assertFilterPasses(
            "\u2003Hello, world!\u2003",
            "Hello, world!",
        )

    def test_pass_custom_regexes(self):
        """
        You can also use regexes to specify which characters get removed.
        """
        self.assertFilterPasses(
            self._filter(
                "54321 Hello, world! "
                "i think you ought to know i'm feeling very depressed ",
                leading=r"\d",
                trailing=r"['a-z ]+",
            ),
            "4321 Hello, world!",
        )

    def test_fail_bytes(self):
        """
        For backwards-compatibility with previous versions of the library, byte
        strings are not allowed.
        """
        self.assertFilterErrors(
            b"    but... but... look at all of my whitespace!    ",
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a string.
        """
        self.assertFilterErrors(
            ["  lots  ", "  of  ", "  whitespace  ", "  here  "],
            [f.Type.CODE_WRONG_TYPE],
        )


class UuidTestCase(BaseFilterTestCase):
    filter_type = f.Uuid

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Uuid`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_uuid_value(self):
        """
        The incoming value can be interpreted as a UUID.
        """
        filtered = self._filter("3466c56a-2ebc-449d-97d2-9b119721ff0f")

        self.assertFilterPasses(filtered, self.skip_value_check)

        uuid = filtered.cleaned_data
        self.assertIsInstance(uuid, UUID)

        self.assertEqual(uuid.hex, "3466c56a2ebc449d97d29b119721ff0f")
        self.assertEqual(uuid.version, 4)

    def test_pass_hex(self):
        """
        You can omit the dashes when specifying a UUID value.
        """
        filtered = self._filter("3466c56a2ebc449d97d29b119721ff0f")

        self.assertFilterPasses(filtered, self.skip_value_check)

        uuid = filtered.cleaned_data
        self.assertIsInstance(uuid, UUID)

        self.assertEqual(uuid.hex, "3466c56a2ebc449d97d29b119721ff0f")
        self.assertEqual(uuid.version, 4)

    # noinspection SpellCheckingInspection
    def test_pass_curly_hex(self):
        """
        You can include curly braces around hex values.

        Use ``Regex(r'^[\\da-f]+$') | Uuid`` if you only want to allow plain
        hex.
        """
        filtered = self._filter("{54d6ebf8a3f55ed59becdedfb3b0773f}")

        self.assertFilterPasses(filtered, self.skip_value_check)

        uuid = filtered.cleaned_data
        self.assertIsInstance(uuid, UUID)

        self.assertEqual(uuid.hex, "54d6ebf8a3f55ed59becdedfb3b0773f")
        self.assertEqual(uuid.version, 5)

    def test_pass_urn(self):
        """
        You can also specify a URN.  The term (and format) is somewhat
        antiquated, but still valid.

        If you want to prohibit URNs, chain this filter with
        ``Regex(r'^[\\da-f]+$')``.

        References:

          - https://en.wikipedia.org/wiki/Uniform_resource_name
        """
        filtered = self._filter(
            "urn:uuid:2830f705-5969-11e5-9628-e0f8470933c8",
        )

        self.assertFilterPasses(filtered, self.skip_value_check)

        uuid = filtered.cleaned_data
        self.assertIsInstance(uuid, UUID)

        self.assertEqual(uuid.hex, "2830f705596911e59628e0f8470933c8")
        self.assertEqual(uuid.version, 1)

    def test_fail_wrong_version(self):
        """
        Configuring the filter to only accept a specific UUID version.
        """
        self.assertFilterErrors(
            # Incoming value is a v1 UUID, but we're expecting a v4.
            self._filter("2830f705596911e59628e0f8470933c8", version=4),
            [f.Uuid.CODE_WRONG_VERSION],
        )

    def test_fail_int(self):
        """
        The incoming value must be a HEX representation of a UUID. Decimal
        values are not valid.
        """
        self.assertFilterErrors(
            "306707680894066278898485957190279549189",
            [f.Uuid.CODE_INVALID],
        )

    def test_fail_wrong_type(self):
        """
        Attempting to filter anything other than a string value fails rather
        spectacularly.
        """
        self.assertFilterErrors(
            [
                "e6bdc02c9d004991986d3c7c0730d105",
                "2830f705596911e59628e0f8470933c8",
            ],
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_pass_uuid_object(self):
        """
        The incoming value is already a UUID object.
        """
        self.assertFilterPasses(UUID("e6bdc02c9d004991986d3c7c0730d105"))

    def test_fail_uuid_object_wrong_version(self):
        """
        The incoming value is already a UUID object, but its version doesn't
        match the expected one.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterErrors(
            # Incoming value is a v5 UUID, but we're expecting a v4.
            self._filter(UUID("54d6ebf8a3f55ed59becdedfb3b0773f"), version=4),
            [f.Uuid.CODE_WRONG_VERSION],
        )


class UnicodeTestCase(BaseFilterTestCase):
    filter_type = f.Unicode

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Unicode`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_unicode(self):
        """
        The incoming value is a unicode.
        """
        self.assertFilterPasses(r"┻━┻︵ \(°□°)/ ︵ ┻━┻ ")  # RAWR!

    def test_pass_bytes_utf8(self):
        """
        The incoming value is a byte string that is encoded as UTF-8.
        """
        self.assertFilterPasses(
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

    def test_fail_bytes_non_utf8(self):
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

        self.assertFilterErrors(
            incoming,
            [f.Unicode.CODE_DECODE_ERROR],
        )

        # In order for this to work, we have to tell the filter what encoding
        # to use:
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(incoming, encoding="iso-8859-1"),
            "Äpple",
        )

    def test_pass_string_like_object(self):
        """
        The incoming value is an object that can be cast as a string.
        """
        value = "／人 ⌒ ‿‿ ⌒ 人＼"  # Squee!

        self.assertFilterPasses(
            Unicody(value),
            value,
        )

    def test_pass_bytes_like_object(self):
        """
        The incoming value is an object that can be cast as a byte string.
        """
        self.assertFilterPasses(
            Bytesy(b"(\xe2\x99\xa5\xe2\x80\xbf\xe2\x99\xa5)"),
            # I can almost hear the sappy music now.
            "(♥‿♥)",
        )

    def test_pass_boolean(self):
        """
        The incoming value is a boolean (treated as an int).
        """
        self.assertFilterPasses(True, "1")

    def test_pass_decimal_with_scientific_notation(self):
        """
        The incoming value is a Decimal that was parsed from scientific
        notation.
        """
        # Note that `str(Decimal('2.8E6'))` yields '2.8E+6', which is not what
        # we want!
        self.assertFilterPasses(
            Decimal("2.8E6"),
            "2800000",
        )

    def test_pass_xml_element(self):
        """
        The incoming value is an ElementTree XML Element.
        """
        self.assertFilterPasses(
            Element("foobar"),
            "<foobar />",
        )

    def test_unicode_normalization(self):
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

        self.assertFilterPasses(decomposed, composed)

    def test_unicode_normalization_disabled(self):
        """
        You can force the filter not to perform normalization.
        """
        decomposed = "Ame\u0301lie"

        self.assertFilterPasses(
            self._filter(decomposed, normalize=False),
            decomposed,
        )

    def test_remove_non_printables(self):
        """
        By default, this filter also removes non-printable characters (both
        ASCII and Unicode varieties).
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            # \x00-\x1f are ASCII control characters.
            # \xef\xbf\xbf is the Unicode control character \uffff, encoded as
            # UTF-8.
            b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
            "Hello, world!",
        )

    def test_remove_non_printables_disabled(self):
        """
        You can force the filter not to remove non-printable characters.
        """
        # noinspection SpellCheckingInspection
        self.assertFilterPasses(
            self._filter(
                b"\x10Hell\x00o,\x1f wor\xef\xbf\xbfld!",
                normalize=False,
            ),
            "\u0010Hell\u0000o,\u001f wor\uffffld!",
        )

    def test_newline_normalization(self):
        """
        By default, any newlines in the string are automatically converted to
        unix-style ("\\n").
        """
        self.assertFilterPasses(
            b"unix\n - windows\r\n - weird\r\r\n",
            "unix\n - windows\n - weird\n\n",
        )

    def test_newline_normalization_disabled(self):
        """
        You can force the filter not to normalize line endings.
        """
        self.assertFilterPasses(
            self._filter(
                b"unix\n - windows\r\n - weird\r\r\n",
                normalize=False,
            ),
            "unix\n - windows\r\n - weird\r\r\n",
        )
