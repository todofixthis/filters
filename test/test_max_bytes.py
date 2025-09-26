"""
Tests for the MaxBytes filter.
"""

from codecs import BOM_UTF16

import pytest

import filters as f


def test_max_bytes_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | MaxBytes`` if you want to reject null values.
    """
    assert_filter_passes(f.MaxBytes(max_bytes=1), None)


def test_max_bytes_pass_string_short(assert_filter_passes):
    """
    The incoming value is a string that is short enough.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(max_bytes=25),
        "Γειάσου Κόσμε",
        # The filter always returns bytes.
        "Γειάσου Κόσμε".encode("utf-8"),
    )


def test_max_bytes_pass_string_short_with_prefix(assert_filter_passes):
    """
    The filter is configured to apply a prefix to values that are too long,
    but the incoming value is a unicode string that is short enough.
    """
    # If we were to apply the prefix to the incoming string, it
    # would be too long to fit, but the filter will only apply
    # the prefix if the value needs to be truncated.
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=25,
            truncate=True,
            prefix="σφάλμα:",
        ),
        "Γειάσου Κόσμε",
        # The filter always returns bytes.
        "Γειάσου Κόσμε".encode("utf-8"),
    )


def test_max_bytes_pass_string_short_with_suffix(assert_filter_passes):
    """
    The filter is configured to apply a suffix to values that are too long,
    but the incoming value is a unicode string that is short enough.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=25,
            truncate=True,
            suffix=" (σφάλμα)",
        ),
        "Γειάσου Κόσμε",
        # The filter always returns bytes.
        "Γειάσου Κόσμε".encode("utf-8"),
    )


def test_max_bytes_fail_string_too_long(assert_filter_errors):
    """
    The incoming value is a string that is too long.
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        f.MaxBytes(max_bytes=24),
        "Γειάσου Κόσμε",
        [f.MaxBytes.CODE_TOO_LONG],
    )


def test_max_bytes_pass_string_truncated(assert_filter_passes):
    """
    The incoming value is a string that is too long, and the filter is
    configured to truncate it.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(max_bytes=24, truncate=True),
        "Γειάσου Κόσμε",
        # Note that the resulting value is truncated to 23 bytes
        # instead of 24, so as not to orphan a multibyte
        # sequence.
        b"\xce\x93\xce\xb5\xce\xb9\xce\xac\xcf\x83\xce\xbf"
        b"\xcf\x85 \xce\x9a\xcf\x8c\xcf\x83\xce\xbc",
    )


def test_max_bytes_pass_string_truncated_with_prefix(assert_filter_passes):
    """
    The incoming value is a string that is too long, and the filter is
    configured to apply a prefix before truncating.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(max_bytes=24, truncate=True, prefix="σφάλμα:"),
        "Γειάσου Κόσμε",
        # Note that the prefix reduces the number of bytes available when
        # truncating the value.
        expected_value=b"\xcf\x83\xcf\x86\xce\xac\xce\xbb\xce\xbc\xce\xb1:"  # Prefix
        b"\xce\x93\xce\xb5\xce\xb9\xce\xac\xcf\x83",
    )


def test_max_bytes_pass_string_truncated_with_suffix(assert_filter_passes):
    """
    The incoming value is a string that is too long, and the filter is
    configured to apply a suffix after truncating.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=30,
            truncate=True,
            suffix=" (อีก)",
        ),
        "หวัดดีชาวโลก",
        expected_value=b"\xe0\xb8\xab\xe0\xb8\xa7\xe0\xb8\xb1"
        b"\xe0\xb8\x94\xe0\xb8\x94\xe0\xb8\xb5"
        b" (\xe0\xb8\xad\xe0\xb8\xb5\xe0\xb8\x81)",  # Suffix
    )


def test_max_bytes_pass_string_truncated_max_bytes_param_too_small(
    assert_filter_passes,
):
    """
    The filter is configured with a ``max_bytes`` so tiny that it is
    impossible to fit any multibyte sequences into a truncated string.

    This will probably never happen outside of this unit test, but if
    there's one thing I've learned, it's that customers never walk into a
    bar and simply order a beer.
    """
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=2,
            truncate=True,
            prefix="更多",
            suffix="更多",
        ),
        "你好，世界！",
        # The filter returns an empty string, not `None`.
        expected_value=b"",
    )


def test_max_bytes_pass_string_truncated_max_bytes_param_almost_too_small(
    assert_filter_passes,
):
    """
    The filter is configured with ``max_bytes`` so tiny that it is
    impossible to fit any multibyte sequences into a truncated string...
    but just big enough to fit in some prefix+suffix.

    Why do I do this to myself?
    """
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=3,
            truncate=True,
            prefix="->",
            suffix="<-",
        ),
        "你好，世界！",
        # The suffix has priority over the prefix.
        # Because I had to pick one :shrug:
        expected_value=b"-<-",
    )


def test_max_bytes_pass_string_short_alt_encoding(assert_filter_passes):
    """
    The filter is configured to use an encoding other than UTF-8, and the
    incoming value is a string that is short enough.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=13,
            truncate=True,
            encoding="iso-8859-7",
        ),
        "Γειάσου Κόσμε",
        # The resulting value is encoded using ISO-8859-7 (Latin-1 Greek).
        b"\xc3\xe5\xe9\xdc\xf3\xef\xf5 \xca\xfc\xf3\xec\xe5",
    )


def test_max_bytes_fail_string_too_long_alt_encoding_has_bom(assert_filter_errors):
    """
    The filter is configured to use an encoding that uses a BOM, and the
    incoming value is a string that is too long.
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        f.MaxBytes(
            max_bytes=27,
            encoding="utf-16",
        ),
        "Γειάσου Κόσμε",
        [f.MaxBytes.CODE_TOO_LONG],
    )


def test_max_bytes_pass_string_truncated_alt_encoding_has_bom(assert_filter_passes):
    """
    The filter is configured to use an encoding that uses a BOM, and the
    incoming value is a string that will be truncated.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=13,
            truncate=True,
            encoding="utf-16",
        ),
        "Γειάσου Κόσμε",
        # End result is only 12 bytes instead of 13 because UTF-16 uses 2
        # bytes per character.
        expected_value=BOM_UTF16
        + b"\x93\x03\xb5\x03\xb9\x03\xac\x03\xc3\x03",  # Truncated string
    )


def test_max_bytes_pass_string_truncated_alt_encoding_has_bom_with_prefix(
    assert_filter_passes,
):
    """
    The filter is configured to use an encoding that uses a BOM, and to
    apply a prefix to truncated values.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=18,
            truncate=True,
            prefix="σφάλμα:",
            encoding="utf-16",
        ),
        "Γειάσου Κόσμε",
        # Note that the BOM is only applied once.
        expected_value=BOM_UTF16 +
        # Prefix:
        b"\xc3\x03\xc6\x03\xac\x03\xbb" b"\x03\xbc\x03\xb1\x03:\x00"
        # Truncated string:
        b"\x93\x03",
    )


def test_max_bytes_pass_string_truncated_alt_encoding_has_bom_with_suffix(
    assert_filter_passes,
):
    """
    The filter is configured to use an encoding that uses a BOM, and to
    apply a suffix to the truncated values.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=20,
            truncate=True,
            suffix=" (อีก)",
            encoding="utf-16",
        ),
        "หวัดดีชาวโลก",
        expected_value=BOM_UTF16 + b"+\x0e'\x0e1\x0e"  # Truncated string
        b" \x00(\x00-\x0e5\x0e\x01\x0e)\x00",  # Suffix
    )


def test_max_bytes_pass_string_truncated_alt_encoding_has_bom_with_prefix_and_suffix(
    assert_filter_passes,
):
    """
    Because my life wasn't hard enough already...
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=40,
            truncate=True,
            prefix="[अधिक] ",
            suffix=" (अधिक)",
            encoding="utf-16",
        ),
        "मैं अपने आप से ऐसा क्यों करता हूं?",
        expected_value=BOM_UTF16 + b"[\x00\x05\t'\t?\t\x15\t]\x00 \x00"  # Prefix
        b".\tH\t\x02\t \x00\x05\t"  # Truncated string
        b" \x00(\x00\x05\t'\t?\t\x15\t)\x00",  # Suffix
    )


def test_max_bytes_pass_string_truncated_max_bytes_param_almost_too_small_alt_encoding_has_bom(
    assert_filter_passes,
):
    """
    Unrealistically tiny ``max_bytes``, part 2: the revenge!
    """
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=4,
            truncate=True,
            prefix=">",
            suffix="<",
            encoding="utf-16",
        ),
        "你好，世界！",
        # The suffix has priority over the prefix.
        # Because I had to pick one :shrug:
        expected_value=BOM_UTF16 + b"<\x00",
    )


def test_max_bytes_pass_bytes_short(assert_filter_passes):
    """
    The incoming value is a byte string that is short enough.
    """
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=18,
        ),
        b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c" b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
    )


def test_max_bytes_fail_bytes_long(assert_filter_errors):
    """
    The incoming value is a byte string that is too long.
    """
    assert_filter_errors(
        f.MaxBytes(
            max_bytes=17,
        ),
        b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c" b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
        [f.MaxBytes.CODE_TOO_LONG],
    )


def test_max_bytes_pass_bytes_truncated(assert_filter_passes):
    """
    The incoming value is a byte string that is too long, and the filter is
    configured to truncate.
    """
    assert_filter_passes(
        f.MaxBytes(
            max_bytes=17,
            truncate=True,
        ),
        b"\xe4\xbd\xa0\xe5\xa5\xbd\xef\xbc\x8c" b"\xe4\xb8\x96\xe7\x95\x8c\xef\xbc\x81",
        # Note that the resulting value is truncated to 15 bytes instead of
        # 17, so as not to orphan a multibyte sequence.
        expected_value=b"\xe4\xbd\xa0\xe5\xa5\xbd\xef"
        b"\xbc\x8c\xe4\xb8\x96\xe7\x95\x8c",
    )


def test_max_bytes_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    assert_filter_errors(
        f.MaxBytes(max_bytes=32),
        ["foo", "bar"],
        [f.Type.CODE_WRONG_TYPE],
    )


def test_max_bytes_error_max_bytes_too_small():
    """
    ``max_bytes`` must be at least 1.
    """
    with pytest.raises(f.FilterError):
        f.MaxBytes(max_bytes=0)
