import filters as f


def test_base64_decode_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Base64Decode`` if you want to reject null values.
    """
    assert_filter_passes(f.Base64Decode(), None)


def test_base64_decode_pass_valid(assert_filter_passes):
    """
    The incoming value is Base64-encoded.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(f.Base64Decode(), b"SGVsbG8sIHdvcmxkIQ==", b"Hello, world!")


def test_base64_decode_pass_url_safe(assert_filter_passes):
    """
    The incoming value is Base64-encoded using a URL-safe variant.
    """
    assert_filter_passes(
        f.Base64Decode(),
        b"--___w==",
        b"\xfb\xef\xff\xff",
    )


def test_base64_decode_fail_mixed_dialects(assert_filter_errors):
    """
    The incoming value contains both URL-safe and URL-unsafe characters.
    """
    assert_filter_errors(f.Base64Decode(), b"+-_/_w==", [f.Base64Decode.CODE_INVALID])


def test_base64_decode_pass_whitespace(assert_filter_passes):
    """
    The incoming value includes whitespace characters.

    Technically, whitespace chars are not part of the Base64 alphabet.
    But, virtually every implementation includes support for whitespace, so
    we will, too.
    """
    assert_filter_passes(
        f.Base64Decode(),
        # Tab chars are especially weird, but eh, why not..
        b"SGV sbG 8sI\tHdv\ncmx\rkIQ\r\n",
        b"Hello, world!",
    )


def test_base64_decode_pass_padding_missing(assert_filter_passes):
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
    assert_filter_passes(f.Base64Decode(), b"SGVsbG8sIHdvcmxkIQ", b"Hello, world!")


def test_base64_decode_pass_padding_excessive(assert_filter_passes):
    """
    The incoming value is Base64-encoded, but for some reason it has too
    much padding.

    This is weird, but it doesn't prevent the filter from decoding the
    value, so the filter agrees to turn a conspiratorial blind eye.
    """
    # noinspection SpellCheckingInspection
    assert_filter_passes(f.Base64Decode(), b"SGVsbG8sIHdvcmxkIQ=====", b"Hello, world!")


def test_base64_decode_fail_invalid(assert_filter_errors):
    """
    The incoming value contains values that are not compatible with
    Base64.
    """
    assert_filter_errors(
        f.Base64Decode(),
        b"$Hello, world!===$",
        [f.Base64Decode.CODE_INVALID],
    )


def test_base64_decode_fail_string(assert_filter_errors):
    """
    For parity with :py:func:`codecs.decode`, unicode strings are not
    allowed; only binary strings can be decoded.

    To decode unicode strings, chain this filter with ``ByteString``:

    .. code-block:: python

       runner = f.FilterRunner(f.ByteString | f.Base64Decode)
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        f.Base64Decode(),
        "SGVsbG8sIHdvcmxkIQ==",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_base64_decode_fail_wrong_type(assert_filter_errors):
    """
    The incoming value is not a string.
    """
    # noinspection SpellCheckingInspection
    assert_filter_errors(
        f.Base64Decode(),
        [b"kB1ReXKFSE5xgu0sODTVrJWg4eYDz32iRLm+fATfsBQ="],
        [f.Type.CODE_WRONG_TYPE],
    )
