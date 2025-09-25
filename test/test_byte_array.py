import filters as f


def test_byte_array_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | ByteArray`` if you want to reject null values.
    """
    assert_filter_passes(f.ByteArray(), None)


def test_byte_array_pass_bytes(assert_filter_passes):
    """
    The incoming value is a byte string.
    """
    assert_filter_passes(
        f.ByteArray(),
        b"|\xa8\xc1.8\xbd4\xd5s\x1e\xa6%+\xea!6",
        # Note that "numeric" characters like "8" and "6" are NOT
        # interpreted literally (e.g., "8" is ASCII code point 58, so it
        # gets converted to ``58`` in the resulting ``bytearray``, not
        # ``8``).  This matches the behaviour of Python's built-in
        # ``bytearray`` type.
        bytearray(
            [
                124,
                168,
                193,
                46,
                56,
                189,
                52,
                213,
                115,
                30,
                166,
                37,
                43,
                234,
                33,
                54,
            ]
        ),
    )


def test_byte_array_pass_string(assert_filter_passes):
    """
    The incoming value is a string.

    This is generally not a recommended use for ByteArray, but sometimes
    it's unavoidable.
    """
    assert_filter_passes(
        f.ByteArray(),
        '\xccK\xdf\xb1\x8bM\xc7\x01\xf0B\xac":\xeb>\x85',
        bytearray(
            [
                195,
                140,
                75,
                195,
                159,
                194,
                177,
                194,
                139,
                77,
                195,
                135,
                1,
                195,
                176,
                66,
                194,
                172,
                34,
                58,
                195,
                171,
                62,
                194,
                133,
            ]
        ),
    )


def test_byte_array_pass_string_alternate_encoding(assert_filter_passes):
    """
    If you want to filter unicodes, you can specify the encoding to use.
    """
    assert_filter_passes(
        f.ByteArray(encoding="latin-1"),
        '\xccK\xdf\xb1\x8bM\xc7\x01\xf0B\xac":\xeb>\x85',
        bytearray(
            [
                204,
                75,
                223,
                177,
                139,
                77,
                199,
                1,
                240,
                66,
                172,
                34,
                58,
                235,
                62,
                133,
            ]
        ),
    )


def test_byte_array_pass_bytearray(assert_filter_passes):
    """
    The incoming value is already a bytearray.
    """
    assert_filter_passes(
        f.ByteArray(),
        bytearray(
            [
                84,
                234,
                48,
                177,
                119,
                69,
                36,
                147,
                214,
                13,
                54,
                12,
                56,
                168,
                107,
                2,
            ]
        ),
    )


def test_byte_array_pass_iterable(assert_filter_passes):
    """
    The incoming value is an iterable containing integers between 0 and
    255, inclusive.
    """
    assert_filter_passes(
        f.ByteArray(),
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233],
        bytearray([0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]),
    )


def test_byte_array_fail_iterable_wrong_types(assert_filter_errors):
    """
    The incoming value is an iterable, but the values are not integers.
    """
    assert_filter_errors(
        f.ByteArray(),
        # The first 2 values are valid.  None of the others are.
        # It's arguable whether booleans should be valid, but they are
        # technically ints, and Python's bytearray allows them, so the
        # filter does, too.
        [1, True, "1", b"1", 1.1, bytearray([1])],
        {
            #
            # String values inside an iterable are not considered valid.
            #
            # It's true that we do have a precedent for how to treat string
            # values (convert each character to its ordinal value), but
            # that only works for strings that can fit into a single byte.
            #
            # E.g., how would we convert `['11', 'foo']` into a bytearray?
            #
            # To keep things as consistent as possible, the filter will
            # treat strings inside of iterables the same way it treats
            # anything else that isn't an int.
            #
            "2": [f.Type.CODE_WRONG_TYPE],
            "3": [f.Type.CODE_WRONG_TYPE],
            # Floats are not allowed in bytearrays.  How would that even
            # work?
            "4": [f.Type.CODE_WRONG_TYPE],
            # Anything else that isn't an int is invalid, even if it
            # contains ints.
            # After all, you can't squeeze multiple bytes into a single
            # byte!
            "5": [f.Type.CODE_WRONG_TYPE],
        },
    )


def test_byte_array_fail_iterable_out_of_bounds(assert_filter_errors):
    """
    The incoming value is an iterable with integers, but it contains values
    outside the acceptable range.

    Each value inside a bytearray must fit within 1 byte, so its value must
    satisfy ``0 <= x < 2^8``.
    """
    assert_filter_errors(
        f.ByteArray(),
        [-1, 0, 1, 255, 256, 9001],
        {
            "0": [f.Min.CODE_TOO_SMALL],
            "4": [f.Max.CODE_TOO_BIG],
            "5": [f.Max.CODE_TOO_BIG],
        },
    )


def test_byte_array_fail_unencodable_unicode(
    assert_filter_passes, assert_filter_errors
):
    """
    The incoming value is a unicode that cannot be encoded using the
    specified encoding.
    """
    value = "\u043b\u0435\u0431\u044b\u0440"

    # The default encoding (utf-8) can handle this just fine.
    assert_filter_passes(
        f.ByteArray(),
        value,
        bytearray([208, 187, 208, 181, 208, 177, 209, 139, 209, 128]),
    )

    # However, if we switch to a single-byte encoding, we run into
    # serious problems.
    assert_filter_errors(
        f.ByteArray(encoding="latin-1"),
        value,
        [f.ByteArray.CODE_BAD_ENCODING],
    )
