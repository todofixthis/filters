import typing
from collections import OrderedDict
from datetime import date, datetime
from functools import partial

from dateutil.tz import tzoffset
from pytz import utc

import filters as f
from filters.test import BaseFilterTestCase


class Lengthy(typing.Sized):
    """
    A class that defines ``__len__``, used to test filters that check for
    object length.
    """

    def __init__(self, length):
        super().__init__()
        self.length = length

    def __len__(self):
        return self.length


# noinspection SpellCheckingInspection
class Bytesy(object):
    """
    A class that defines ``__bytes__``, used to test filters that convert
    values into byte strings.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __bytes__(self):
        return bytes(self.value)


# noinspection SpellCheckingInspection
class Unicody(object):
    """
    A class that defines ``__str__``, used to test filters that convert values
    into unicodes.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return str(self.value)


class ArrayTestCase(BaseFilterTestCase):
    filter_type = f.Array

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Array`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_sequence(self):
        """
        The incoming value is a sequence.
        """
        self.assertFilterPasses(tuple())
        self.assertFilterPasses(list())

    def test_pass_custom_sequence_type(self):
        """
        The incoming value has a type that extends Sequence.
        """

        class CustomSequence(typing.Sequence):
            """
            Technically, it's a Sequence. Technically.
            """

            def __len__(self): return 0

            def __getitem__(self, index): return None

        self.assertFilterPasses(CustomSequence())

    def test_fail_string(self):
        """
        The incoming value is a string.
        """
        self.assertFilterErrors(bytes(), [f.Array.CODE_WRONG_TYPE])
        self.assertFilterErrors(str(), [f.Array.CODE_WRONG_TYPE])

    def test_fail_mapping(self):
        """
        The incoming value is a mapping.
        """
        self.assertFilterErrors(dict(), [f.Array.CODE_WRONG_TYPE])

    def test_fail_set(self):
        """
        The incoming value is a set.
        """
        self.assertFilterErrors(set(), [f.Array.CODE_WRONG_TYPE])

    def test_fail_custom_sequence_type(self):
        """
        The incoming value looks like a Sequence, but it's not official.
        """

        class CustomSequence(object):
            """
            Walks, talks and quacks like a Sequence, but isn't.
            """

            def __len__(self): return 0

            def __getitem__(self, index): return None

        self.assertFilterErrors(CustomSequence(), [f.Array.CODE_WRONG_TYPE])

        # If you can't (or don't want) to modify the base class for your custom
        # sequence, you can ``register`` it.
        #
        # Note: Code included here for documentation purposes, but it's
        # commented out to avoid side effects; registering a subclass this way
        # is basically irreversible.
        #
        # Sequence.register(CustomSequence)
        # self.assertFilterPasses(CustomSequence())


class ByteArrayTestCase(BaseFilterTestCase):
    filter_type = f.ByteArray

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | ByteArray`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_bytes(self):
        """
        The incoming value is a byte string.
        """
        self.assertFilterPasses(
            b'|\xa8\xc1.8\xbd4\xd5s\x1e\xa6%+\xea!6',

            # Note that "numeric" characters like "8" and "6" are NOT
            # interpreted literally (e.g., "8" is ASCII code point 58, so it
            # gets converted to ``58`` in the resulting ``bytearray``, not
            # ``8``).  This matches the behaviour of Python's built-in
            # ``bytearray`` type.
            bytearray([
                124, 168, 193, 46, 56, 189, 52, 213,
                115, 30, 166, 37, 43, 234, 33, 54,
            ]),
        )

    def test_pass_string(self):
        """
        The incoming value is a string.

        This is generally not a recommended use for ByteArray, but sometimes
        it's unavoidable.
        """
        self.assertFilterPasses(
            u'\xccK\xdf\xb1\x8bM\xc7\x01\xf0B\xac":\xeb>\x85',

            bytearray([
                195, 140, 75, 195, 159, 194, 177, 194, 139, 77, 195, 135,
                1, 195, 176, 66, 194, 172, 34, 58, 195, 171, 62, 194, 133,
            ]),
        )

    def test_pass_string_alternate_encoding(self):
        """
        If you want to filter unicodes, you can specify the encoding to use.
        """
        self.assertFilterPasses(
            self._filter(
                u'\xccK\xdf\xb1\x8bM\xc7\x01\xf0B\xac":\xeb>\x85',
                encoding='latin-1',
            ),

            bytearray([
                204, 75, 223, 177, 139, 77, 199, 1,
                240, 66, 172, 34, 58, 235, 62, 133,
            ]),
        )

    def test_pass_bytearray(self):
        """
        The incoming value is already a bytearray.
        """
        self.assertFilterPasses(
            bytearray([
                84, 234, 48, 177, 119, 69, 36, 147,
                214, 13, 54, 12, 56, 168, 107, 2,
            ])
        )

    def test_pass_iterable(self):
        """
        The incoming value is an iterable containing integers between 0 and
        255, inclusive.
        """
        self.assertFilterPasses(
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233],
            bytearray([0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233])
        )

    def test_fail_iterable_wrong_types(self):
        """
        The incoming value is an iterable, but the values are not integers.
        """
        self.assertFilterErrors(
            # The first 2 values are valid.  None of the others are.
            # It's arguable whether booleans should be valid, but they are
            # technically ints, and Python's bytearray allows them, so the
            # filter does, too.
            [1, True, '1', b'1', 1.1, bytearray([1])],

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
                '2': [f.Type.CODE_WRONG_TYPE],
                '3': [f.Type.CODE_WRONG_TYPE],

                # Floats are not allowed in bytearrays.  How would that even
                # work?
                '4': [f.Type.CODE_WRONG_TYPE],

                # Anything else that isn't an int is invalid, even if it
                # contains ints.
                # After all, you can't squeeze multiple bytes into a single
                # byte!
                '5': [f.Type.CODE_WRONG_TYPE],
            },
        )

    def test_fail_iterable_out_of_bounds(self):
        """
        The incoming value is an iterable with integers, but it contains values
        outside the acceptable range.

        Each value inside a bytearray must fit within 1 byte, so its value must
        satisfy ``0 <= x < 2^8``.
        """
        self.assertFilterErrors(
            [-1, 0, 1, 255, 256, 9001],

            {
                '0': [f.Min.CODE_TOO_SMALL],
                '4': [f.Max.CODE_TOO_BIG],
                '5': [f.Max.CODE_TOO_BIG],
            },
        )

    def test_fail_unencodable_unicode(self):
        """
        The incoming value is a unicode that cannot be encoded using the
        specified encoding.
        """
        value = '\u043b\u0435\u0431\u044b\u0440'

        # The default encoding (utf-8) can handle this just fine.
        self.assertFilterPasses(
            value,
            bytearray([208, 187, 208, 181, 208, 177, 209, 139, 209, 128]),
        )

        # However, if we switch to a single-byte encoding, we run into
        # serious problems.
        self.assertFilterErrors(
            self._filter(value, encoding='latin-1'),
            [f.ByteArray.CODE_BAD_ENCODING],
        )


class CallTestCase(BaseFilterTestCase):
    filter_type = f.Call

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Call`` if you want to reject null values.
        """

        def always_fail(value):
            raise ValueError('{value} is not valid!'.format(value=value))

        self.assertFilterPasses(
            self._filter(None, always_fail)
        )

    def test_pass_successful_execution(self):
        """
        The callable runs successfully.
        """

        def is_odd(value):
            return value % 2

        self.assertFilterPasses(
            self._filter(6, is_odd),

            # Note that ANY value returned by the callable is considered valid;
            # if you want custom handling of some values, you're better off
            # creating a custom filter type (it's super easy!).
            False,
        )

    def test_fail_filter_error(self):
        """
        The callable raises a :py:class:`FilterError`.
        """

        def even_only(value):
            if value % 2:
                raise f.FilterError('value is not even!')
            return value

        self.assertFilterErrors(
            self._filter(5, even_only),
            ['value is not even!']
        )

    def test_fail_filter_error_custom_code(self):
        """
        The callable raises a :py:class:`FilterError` with a custom error code.
        """

        def even_only(value):
            if value % 2:
                # If you find yourself doing this, you would probably be better
                # served by creating a custom filter instead.
                error = f.FilterError('value is not even!')
                error.context = {'code': 'not_even'}
                raise error
            return value

        self.assertFilterErrors(
            self._filter(5, even_only),
            ['not_even'],
        )

    def test_error_exception(self):
        """
        The callable raises an exception other than a :py:class:`FilterError`.
        """

        def even_only(value):
            if value % 2:
                raise ValueError('{value} is not even!')
            return value

        filter_ = self._filter(5, even_only)

        # :py:class:`Call` assumes that any exception other than a
        # :py:class:`FilterError` represents an error in the code.
        self.assertTrue(filter_.has_exceptions)


class DateTestCase(BaseFilterTestCase):
    filter_type = f.Date

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use `Required | Date` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_naive_timestamp(self):
        """
        The incoming value is a naive timestamp (no timezone info).
        """
        self.assertFilterPasses(
            '2015-05-11 14:56:58',
            date(2015, 5, 11),
        )

    def test_pass_aware_timestamp(self):
        """
        The incoming value includes timezone info.
        """
        self.assertFilterPasses(
            # Note that the value we are parsing is 5 hours behind UTC.
            '2015-05-11T19:56:58-05:00',

            # The resulting date appears to occur 1 day later because that's
            # the date according to UTC.
            date(2015, 5, 12)
        )

    def test_pass_naive_timestamp_default_timezone(self):
        """
        The incoming value is a naive timestamp, but the filter is configured
        not to treat naive timestamps as UTC.
        """
        self.assertFilterPasses(
            self._filter(
                '2015-05-12 03:20:03',

                # The filter is configured to parse naive timestamps as if they
                # are UTC+8.
                timezone=tzoffset('UTC+8', 8 * 3600)
            ),

            # The resulting date appears to occur 1 day earlier because the
            # filter subtracted 8 hours to convert the value to UTC.
            date(2015, 5, 11),
        )

    def test_pass_aware_timestamp_default_timezone(self):
        """
        The filter's default timezone has no effect if the incoming value
        already contains timezone info.
        """
        self.assertFilterPasses(
            # The incoming timestamp is from UTC+4, but the filter is
            # configured to use UTC-11 by default.
            self._filter(
                '2015-05-11T03:14:38+04:00',
                timezone=tzoffset('UTC-11', -11 * 3600)
            ),

            # Because the incoming timestamp has timezone info, the filter uses
            # that instead of the default value.  Note that this test will fail
            # if the filter uses the UTC-11 timezone (the result will be 1 day
            # ahead).
            date(2015, 5, 10),
        )

    def test_pass_alternate_timezone_syntax(self):
        """
        When setting the default timezone for the filter, you can use an
        int/float offset (number of hours from UTC) instead of a tzoffset
        object.
        """
        self.assertFilterPasses(
            # Note that we use an int value instead of constructing a tzoffset
            # for `timezone`.
            self._filter('2015-05-11 21:14:38', timezone=-8),
            date(2015, 5, 12),
        )

    def test_pass_datetime_utc(self):
        """
        The incoming value is a datetime object that is already set to UTC.
        """
        self.assertFilterPasses(
            datetime(2015, 6, 27, 10, 5, 48, tzinfo=utc),
            date(2015, 6, 27),
        )

    def test_pass_datetime_non_utc(self):
        """
        The incoming value is a datetime object with a non-UTC timezone.
        """
        self.assertFilterPasses(
            datetime(
                2015, 6, 27, 22, 6, 32,
                tzinfo=tzoffset('UTC-5', -5 * 3600),
            ),

            # As you probably already guessed, the datetime gets converted to
            # UTC before it is converted to a date.
            date(2015, 6, 28),
        )

    def test_pass_datetime_naive(self):
        """
        The incoming value is a datetime object without timezone info.
        """
        self.assertFilterPasses(
            # The filter will assume that this datetime is UTC-3 by default.
            self._filter(datetime(2015, 6, 27, 23, 7, 18), timezone=-3),

            # The datetime is converted from UTC-3 to UTC before it is
            # converted to a date.
            date(2015, 6, 28),
        )

    def test_pass_date(self):
        """
        The incoming value is a date object.
        """
        self.assertFilterPasses(date(2015, 6, 27))

    def test_fail_invalid_value(self):
        """
        The incoming value cannot be interpreted as a date.

        Insert socially-awkward nerd joke here.
        """
        self.assertFilterErrors(
            'this is not a date',  # it's a space station
            [f.Date.CODE_INVALID],
        )


class DatetimeTestCase(BaseFilterTestCase):
    filter_type = f.Datetime

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use `Required | Datetime` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_naive_timestamp(self):
        """
        The incoming value is a naive timestamp (does not include timezone
        info).
        """
        self.assertFilterPasses(
            '2015-05-11 14:56:58',
            datetime(2015, 5, 11, 14, 56, 58, tzinfo=utc),
        )

    def test_pass_aware_timestamp(self):
        """
        The incoming value is a timestamp that includes timezone info.
        """
        self.assertFilterPasses(
            # Note that the value we are parsing is 5 hours behind UTC.
            '2015-05-11T14:56:58-0500',

            datetime(2015, 5, 11, 19, 56, 58, tzinfo=utc)
        )

    def test_pass_naive_timestamp_default_timezone(self):
        """
        The incoming value is a naive timestamp, but the filter is configured
        not to treat naive timestamps as UTC.
        """
        self.assertFilterPasses(
            # The incoming value is a naive timestamp, and the filter is
            # configured to use UTC+8 by default.
            self._filter(
                '2015-05-12 09:20:03',
                timezone=tzoffset('UTC+8', 8 * 3600),
            ),

            # The resulting datetime is still converted to UTC.
            datetime(2015, 5, 12, 1, 20, 3, tzinfo=utc),
        )

    def test_pass_aware_timestamp_default_timezone(self):
        """
        The filter's default timezone has no effect if the incoming value
        already contains timezone info.
        """
        self.assertFilterPasses(
            # The incoming value is UTC+4, but the filter is configured to use
            # UTC-1 by default.
            self._filter(
                '2015-05-11T21:14:38+04:00',
                timezone=tzoffset('UTC-1', -1 * 3600)
            ),

            # The incoming values timezone info is used instead of the default.
            # Note that the resulting datetime is still converted to UTC.
            datetime(2015, 5, 11, 17, 14, 38, tzinfo=utc),
        )

    def test_pass_alternate_timezone_syntax(self):
        """
        When setting the default timezone for the filter, you can use an
        int/float offset (number of hours from UTC) instead of a tzoffset
        object.
        """
        self.assertFilterPasses(
            # Note that we use an int value instead of constructing a tzoffset
            # for ``timezone``.
            self._filter('2015-05-11 21:14:38', timezone=3),

            datetime(2015, 5, 11, 18, 14, 38, tzinfo=utc),
        )

    def test_pass_datetime_utc(self):
        """
        The incoming value is a datetime object that is already set to UTC.
        """
        self.assertFilterPasses(datetime(2015, 6, 27, 10, 5, 48, tzinfo=utc))

    def test_pass_datetime_non_utc(self):
        """
        The incoming value is a datetime object that is already set to a
        non-UTC timezone.
        """
        self.assertFilterPasses(
            datetime(2015, 6, 27, 10, 6, 32,
                tzinfo=tzoffset('UTC-5', -5 * 3600)),
            datetime(2015, 6, 27, 15, 6, 32, tzinfo=utc),
        )

    def test_datetime_naive(self):
        """
        The incoming value is a datetime object that does not have timezone
        info.
        """
        self.assertFilterPasses(
            # The filter is configured to assume UTC-3 if the incoming value
            # has no timezone info.
            self._filter(datetime(2015, 6, 27, 18, 7, 18), timezone=-3),

            datetime(2015, 6, 27, 21, 7, 18, tzinfo=utc),
        )

    def test_pass_date(self):
        """
        The incoming value is a date object.
        """
        self.assertFilterPasses(
            # The filter is configured to assume UTC+12 if the incoming value
            # has no timezone info.
            self._filter(date(2015, 6, 27), timezone=12),

            datetime(2015, 6, 26, 12, 0, 0, tzinfo=utc),
        )

    def test_return_naive_datetime(self):
        """
        You can configure the filter to return a naive datetime object (e.g.,
        for storing in a database).

        Note that the datetime is still converted to UTC before its tzinfo is
        removed.
        """
        self.assertFilterPasses(
            self._filter(
                datetime(
                    2015, 7, 1, 9, 22, 10,
                    tzinfo=tzoffset('UTC-5', -5 * 3600),
                ),

                # Note that we pass `naive=True` to the filter's initialiser.
                naive=True,
            ),

            # The resulting datetime is converted to UTC before its timezone
            # info is stripped.
            datetime(2015, 7, 1, 14, 22, 10, tzinfo=None),
        )

    def test_fail_invalid_value(self):
        """
        The incoming value cannot be parsed as a datetime.
        """
        self.assertFilterErrors(
            'this is not a datetime',  # it's a pipe
            [f.Datetime.CODE_INVALID],
        )


class EmptyTestCase(BaseFilterTestCase):
    filter_type = f.Empty

    def test_pass_none(self):
        """
        ``None`` shall pass.

        What?

        ``None`` shall pass!
        """
        self.assertFilterPasses(None)

    def test_pass_empty_string(self):
        """
        The incoming value is an empty string.
        """
        self.assertFilterPasses('')

    def test_pass_empty_collection(self):
        """
        The incoming value is a collection with length < 1.
        """
        self.assertFilterPasses([])
        self.assertFilterPasses({})
        self.assertFilterPasses(Lengthy(0))
        # etc.

    def test_fail_non_empty_string(self):
        """
        The incoming value is a non-empty string.
        """
        self.assertFilterErrors(
            'Goodbye world!',
            [f.Empty.CODE_NOT_EMPTY],
        )

    def test_fail_non_empty_collection(self):
        """
        The incoming value is a collection with length > 0.
        """
        # The values inside the collection may be empty, but the collection
        # itself is not.
        self.assertFilterErrors(['', '', ''], [f.Empty.CODE_NOT_EMPTY])
        self.assertFilterErrors({'': ''}, [f.Empty.CODE_NOT_EMPTY])
        self.assertFilterErrors(Lengthy(1), [f.Empty.CODE_NOT_EMPTY])
        # etc.

    def test_fail_non_collection(self):
        """
        The incoming value does not have a length.
        """
        # The filter can't determine the length of this object, so it assumes
        # that it is not empty.
        self.assertFilterErrors(object(), [f.Empty.CODE_NOT_EMPTY])

    def test_zero_is_not_empty(self):
        """
        PHP developers take note!
        """
        self.assertFilterErrors(0, [f.Empty.CODE_NOT_EMPTY])

    def test_false_is_not_empty(self):
        """
        The boolean value ``False`` is NOT considered empty because it
        represents SOME kind of value.
        """
        self.assertFilterErrors(False, [f.Empty.CODE_NOT_EMPTY])


class ItemTestCase(BaseFilterTestCase):
    filter_type = f.Item

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Item`` if you want to reject null values.
        """
        self.assertFilterPasses(None)

    def test_pass_mapping_default(self):
        """
        By default, returns the first item in a mapping.
        """
        self.assertFilterPasses(
            {'foo': 'bar', 'baz': 'luhrmann'},
            'bar',
        )

    def test_fail_mapping_empty(self):
        """
        The incoming value is an empty mapping, so no value to extract.
        """
        self.assertFilterErrors({}, [f.NotEmpty.CODE_EMPTY])

    def test_pass_mapping_specific_key(self):
        """
        Specify the key to extract from a mapping.
        """
        self.assertFilterPasses(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, key='baz'),
            'luhrmann',
        )

    def test_fail_mapping_specific_key_missing(self):
        """
        The incoming mapping does not contain the specified key.
        """
        self.assertFilterErrors(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, key='foobie'),
            {'foobie': [f.Item.CODE_MISSING_KEY]},
        )

    def test_pass_sequence_default(self):
        """
        By default, returns the first item in a sequence.
        """
        self.assertFilterPasses(['foo', 'bar', 'baz', 'luhrmann'], 'foo')

    def test_fail_sequence_empty(self):
        """
        The incoming value is an empty sequence, so no value to extract.
        """
        self.assertFilterErrors([], [f.NotEmpty.CODE_EMPTY])

    def test_pass_sequence_specific_index(self):
        """
        Specify the index to extract from a mapping.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz'], key=2),
            'baz',
        )

    def test_fail_sequence_specific_index_missing(self):
        """
        The incoming sequence does not contain the specified index.
        """
        self.assertFilterErrors(
            self._filter(['foo', 'bar', 'baz'], key=42),
            {'42': [f.Item.CODE_MISSING_KEY]},
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is not a mapping nor sequence.
        """
        self.assertFilterErrors(42, [f.Type.CODE_WRONG_TYPE])


class MaxLengthTestCase(BaseFilterTestCase):
    filter_type = f.MaxLength

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | MaxLength`` if you want to reject null values.
        """
        self.assertFilterPasses(
            self._filter(None, max_length=0),
        )

    def test_pass_short(self):
        """
        The incoming value is shorter than the max length.
        """
        self.assertFilterPasses(
            self._filter('Hello', max_length=6),
        )

    def test_pass_max_length(self):
        """
        The incoming value has the max allowed length.
        """
        self.assertFilterPasses(
            self._filter('World', max_length=5),
        )

    def test_fail_long(self):
        """
        The incoming value is longer than the max length.
        """
        self.assertFilterErrors(
            self._filter('Goodbye', max_length=5),
            [f.MaxLength.CODE_TOO_LONG],
        )

    def test_pass_truncated(self):
        """
        The filter is configured to truncate values that are too long.
        """
        self.assertFilterPasses(
            self._filter(
                ['foo', 'bar', 'baz', 'luhrmann'],
                max_length=3,
                truncate=True,
            ),
            ['foo', 'bar', 'baz'],
        )

    def test_multi_byte_characters(self):
        """
        Multibyte characters are treated differently depending on whether you
        pass in a unicode or a byte string.
        """
        # "Hello world" in Chinese:
        decoded_value = '\u4f60\u597d\u4e16\u754c'
        encoded_value = decoded_value.encode('utf-8')

        # The string version of the string contains 4 code points.
        self.assertFilterPasses(
            self._filter(decoded_value, max_length=4),
        )

        # The bytes version of the string contains 12 bytes.
        self.assertFilterErrors(
            self._filter(encoded_value, max_length=4),
            [f.MaxLength.CODE_TOO_LONG],
        )

    def test_pass_short_collection(self):
        """
        The incoming value is a collection with length less than or equal to
        the max length.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz', 'luhrmann'], max_length=4),
        )

        self.assertFilterPasses(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, max_length=3),
        )

        self.assertFilterPasses(
            self._filter(Lengthy(4), max_length=4),
        )

        # etc.

    def test_fail_long_collection(self):
        """
        The incoming value is a collection with length greater than the max
        length.
        """
        self.assertFilterErrors(
            self._filter(['foo', 'bar', 'baz', 'luhrmann'], max_length=3),
            [f.MaxLength.CODE_TOO_LONG],
        )

        self.assertFilterErrors(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, max_length=1),
            [f.MaxLength.CODE_TOO_LONG],
        )

        self.assertFilterErrors(
            self._filter(Lengthy(4), max_length=3),
            [f.MaxLength.CODE_TOO_LONG],
        )

        # etc.


class MinLengthTestCase(BaseFilterTestCase):
    filter_type = f.MinLength

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use `Required | MinLength` if you want to reject null values.
        """
        self.assertFilterPasses(
            self._filter(None, min_length=5),
        )

    def test_pass_long(self):
        """
        The incoming value has length greater than the minimum value.
        """
        self.assertFilterPasses(
            self._filter('Hello', min_length=2),
        )

    def test_pass_min_length(self):
        """
        The incoming value has length equal to the minimum value.
        """
        self.assertFilterPasses(
            self._filter('World', min_length=5),
        )

    def test_fail_short(self):
        """
        The incoming value has length less than the minimum value.
        """
        self.assertFilterErrors(
            self._filter('Goodbye', min_length=10),
            [f.MinLength.CODE_TOO_SHORT],
        )

    def test_multi_byte_characters(self):
        """
        Multibyte characters are treated differently depending on whether you
        pass in a unicode or a byte string.
        """
        # "Hello world" in Chinese:
        decoded_value = '\u4f60\u597d\u4e16\u754c'
        encoded_value = decoded_value.encode('utf-8')

        # The string version of the string contains 4 code points.
        self.assertFilterErrors(
            self._filter(decoded_value, min_length=12),
            [f.MinLength.CODE_TOO_SHORT],
        )

        # The bytes version of the string contains 12 bytes.
        self.assertFilterPasses(
            self._filter(encoded_value, min_length=12),
        )

    def test_pass_long_collection(self):
        """
        The incoming value is a collection with length greater than or equal to
        the minimum value.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz', 'luhrmann'], min_length=3),
        )

        self.assertFilterPasses(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, min_length=1),
        )

        self.assertFilterPasses(
            self._filter(Lengthy(6), min_length=5),
        )

        # etc.

    def test_fail_short_collection(self):
        """
        The incoming value is a collection with length less than the minimum
        value.
        """
        self.assertFilterErrors(
            self._filter(['foo', 'bar', 'baz', 'luhrmann'], min_length=5),
            [f.MinLength.CODE_TOO_SHORT],
        )

        self.assertFilterErrors(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, min_length=3),
            [f.MinLength.CODE_TOO_SHORT],
        )

        self.assertFilterErrors(
            self._filter(Lengthy(6), min_length=7),
            [f.MinLength.CODE_TOO_SHORT],
        )

        # etc.


class NoOpTestCase(BaseFilterTestCase):
    filter_type = f.NoOp

    def test_pass_any_value(self):
        """
        You can pass any value you want to a NoOp, and it will pass.
        """
        self.assertFilterPasses('supercalafragalisticexpialadoshus')


class NotEmptyTestCase(BaseFilterTestCase):
    filter_type = f.NotEmpty

    def test_pass_none(self):
        """
        By default, :py:class:`f.NotEmpty` will treat ``None`` as valid, just
        like every other filter.

        Unlike every other filter, however, the strategy for rejecting null
        values is a wee bit different, as we'll see in the next test.
        """
        self.assertFilterPasses(None)

    def test_fail_none(self):
        """
        You can configure the filter to reject null values.
        """
        self.assertFilterErrors(
            self._filter(None, allow_none=False),
            [f.NotEmpty.CODE_EMPTY],
        )

    def test_pass_non_empty_string(self):
        """
        The incoming value is a non-empty string.
        """
        self.assertFilterPasses('Hello, world!')

    def test_pass_non_empty_collection(self):
        """
        The incoming value is a collection with length > 0.
        """
        # The values in the collection may be empty, but the collection itself
        # is not.
        self.assertFilterPasses(['', '', ''])
        self.assertFilterPasses({'': ''})
        self.assertFilterPasses(Lengthy(1))
        # etc.

    def test_pass_non_collection(self):
        """
        The incoming value does not have a length.
        """
        self.assertFilterPasses(object())

    def test_fail_empty_string(self):
        """
        The incoming value is an empty string.
        """
        self.assertFilterErrors('', [f.NotEmpty.CODE_EMPTY])

    def test_fail_empty_collection(self):
        """
        The incoming value is a collection with length < 1.
        """
        self.assertFilterErrors([], [f.NotEmpty.CODE_EMPTY])
        self.assertFilterErrors({}, [f.NotEmpty.CODE_EMPTY])
        self.assertFilterErrors(Lengthy(0), [f.NotEmpty.CODE_EMPTY])
        # etc.

    def test_zero_is_not_empty(self):
        """
        PHP developers take note!
        """
        self.assertFilterPasses(0)

    def test_false_is_not_empty(self):
        """
        The boolean value ``False`` is NOT considered empty because it
        represents SOME kind of value.
        """
        self.assertFilterPasses(False)


class OmitTestCase(BaseFilterTestCase):
    filter_type = f.Omit

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Omit`` to reject ``None``.
        """
        self.assertFilterPasses(self._filter(None, keys={'test'}))

    def test_pass_mapping(self):
        """
        Incoming value is a mapping.
        """
        self.assertFilterPasses(
            self._filter(
                {'name': 'Indy', 'job': 'archaeologist', 'actor': 'Harrison'},
                keys={'actor', 'age'},
            ),
            {'name': 'Indy', 'job': 'archaeologist'},
        )

    def test_pass_mapping_no_items_omitted(self):
        """
        Incoming value is a mapping, and it doesn't have any of the keys to be
        omitted.
        """
        self.assertFilterPasses(
            self._filter(
                {'name': 'Indy', 'job': 'archaeologist', 'actor': 'Harrison'},
                keys=['profession', 'surname']
            )
        )

    def test_pass_mapping_empty(self):
        """
        An empty mapping always passes this filter by default.

        Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
        empty mappings.
        """
        self.assertFilterPasses(
            self._filter({}, keys=['foo', 'bar', 'baz', 'luhrmann'])
        )

    def test_pass_sequence(self):
        """
        Incoming value is a sequence.
        """
        self.assertFilterPasses(
            self._filter(
                ['Indy', 'Marion', 'Marcus'],
                keys=[1, 3]
            ),
            ['Indy', 'Marcus'],
        )

    def test_pass_sequence_no_items_omitted(self):
        """
        Incoming value is a sequence, and it doesn't have any of the indices to
        be omitted.
        """
        self.assertFilterPasses(
            self._filter(
                ['Indy', 'Marion', 'Marcus'],
                keys=[3, 4, 5]
            )
        )

    def test_pass_sequence_empty(self):
        """
        An empty sequence always passes this filter by default.

        Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
        empty sequences.
        """
        self.assertFilterPasses(
            self._filter([], keys=[3, 4, 5, 6])
        )

    def test_fail_wrong_type(self):
        """
        Incoming value is not a mapping nor sequence.
        """
        self.assertFilterErrors(
            self._filter(42, keys=[0]),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_error_empty_keys(self):
        """
        The ``keys`` param must not be empty.
        """
        self.assertRaises(f.FilterError, lambda: self.filter_type([]))


class OptionalTestCase(BaseFilterTestCase):
    filter_type = f.Optional

    def test_pass_none(self):
        """
        It'd be pretty silly to name a filter "Optional" if it rejects
        ``None``, wouldn't it?
        """
        self.assertFilterPasses(None)

    def test_pass_replace_none(self):
        """
        The default replacement value is ``None``, but you can change it to
        something else.
        """
        self.assertFilterPasses(
            self._filter(None, default='Hello, world!'),
            'Hello, world!',
        )

    def test_pass_replace_empty_string(self):
        """
        The incoming value is an empty string.
        """
        self.assertFilterPasses(
            self._filter('', default='42'),
            '42',
        )

    def test_replace_empty_collection(self):
        """
        The incoming value is a collection with length < 1.
        """
        # By default, the filter will replace empty values with `None`.
        self.assertFilterPasses([], None)
        self.assertFilterPasses({}, None)
        self.assertFilterPasses(Lengthy(0), None)
        # etc.

    def test_pass_non_empty_string(self):
        """
        The incoming value is a non-empty string.
        """
        self.assertFilterPasses(
            self._filter('Goodbye, world!', default='fail')
        )

    def test_pass_non_empty_collection(self):
        """
        The incoming value is a collection with length > 0.
        """
        # The values inside the collection may be empty, but the collection
        # itself is not.
        self.assertFilterPasses(['', '', ''])
        self.assertFilterPasses({'': ''})
        self.assertFilterPasses(Lengthy(12))
        # etc.

    def test_pass_non_collection(self):
        """
        Any value that doesn't have a length is left alone.
        """
        self.assertFilterPasses(
            self._filter(object(), default='fail'),
        )

    def test_pass_zero_is_not_empty(self):
        """
        PHP developers take note!
        """
        self.assertFilterPasses(
            self._filter(0, default='fail'),
        )

    def test_pass_false_is_not_empty(self):
        """
        The boolean value ``False`` is NOT considered empty because it
        represents SOME kind of value.
        """
        self.assertFilterPasses(
            self._filter(False, default='fail'),
        )

    def test_pass_default_callable(self):
        """
        The filter is configured with a callable value for ``default``.
        """
        runner1 = self.assertFilterPasses(
            self._filter(None, default=list),
            [],
        )

        runner2 = self.assertFilterPasses(
            self._filter("", default=list),
            [],
        )

        # A new list is created each time.
        self.assertIsNot(runner1.cleaned_data, runner2.cleaned_data)

    def test_pass_default_callable_partial(self):
        """
        To pass args or kwargs to a callable ``default``, use a partial or a
        lambda.
        """

        def power_of_two(power):
            return pow(2, power)

        # Use a partial:
        self.assertFilterPasses(
            self._filter({}, partial(power_of_two, power=8)),
            256,
        )

        # Or, use a lambda:
        self.assertFilterPasses(
            self._filter([], lambda: power_of_two(power=4)),
            16,
        )

    def test_pass_default_callable_but_do_not_call_it(self):
        """
        The filter is configured to use ``default`` explicitly for replacement
        values.
        """
        runner1 = self.assertFilterPasses(
            self._filter(None, default=list, call_default=False),
            list,
        )

        runner2 = self.assertFilterPasses(
            self._filter("", default=list, call_default=False),
            list,
        )

        self.assertIs(runner1.cleaned_data, runner2.cleaned_data)


class PickTestCase(BaseFilterTestCase):
    filter_type = f.Pick

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Pick`` to reject ``None``.
        """
        self.assertFilterPasses(
            self._filter(None, keys={'test'}),
        )

    def test_pass_mapping(self):
        """
        Using the filter to pick specific keys from a mapping.
        """
        self.assertFilterPasses(
            self._filter({'foo': 'bar', 'baz': 'luhrmann'}, keys={'foo'}),
            {'foo': 'bar'},
        )

    def test_pass_mapping_exact_match(self):
        """
        The incoming contains only the keys to be picked.
        """
        self.assertFilterPasses(
            self._filter(
                {'foo': 'bar', 'baz': 'luhrmann'},
                keys={'foo', 'baz'},
            )
        )

    def test_pass_mapping_ordered_keys(self):
        """
        When keys are provided in an ordered collection, the order of keys
        determines the order of the items in the result.
        """
        runner = self.assertFilterPasses(
            self._filter(
                {'name': 'Indy', 'job': 'archaeologist', 'actor': 'Harrison'},
                keys=('actor', 'name', 'job'),
            ),
            {'actor': 'Harrison', 'name': 'Indy', 'job': 'archaeologist'},
        )

        self.assertListEqual(
            list(runner.cleaned_data.keys()),
            ['actor', 'name', 'job'],
        )

    def test_pass_mapping_missing_values(self):
        """
        Any keys not present in the incoming value are set to ``None``.
        """
        self.assertFilterPasses(
            self._filter(
                {'foo': 'bar', 'baz': 'luhrmann'},
                keys=['foo', 'foobie'],
            ),
            {'foo': 'bar', 'foobie': None},
        )

    def test_pass_mapping_empty(self):
        """
        An empty mapping always passes this filter by default.

        Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
        empty mappings, or set ``allow_missing_keys`` when initialising the
        filter.
        """
        self.assertFilterPasses(
            self._filter({}, keys=['foo', 'baz']),
            {'foo': None, 'baz': None},
        )

    def test_pass_mapping_match_type(self):
        """
        Whenever practical, the filter will try to return the same type of
        value that it received.
        """
        runner = self.assertFilterPasses(
            self._filter(
                OrderedDict(foo='bar', baz='luhrmann'),
                keys=('baz',)
            ),
            OrderedDict(baz='luhrmann')
        )

        self.assertIsInstance(runner.cleaned_data, OrderedDict)

    def test_fail_mapping_allow_missing_keys_false(self):
        """
        Incoming value is missing one or more requested keys, and the filter
        was initialised with ``allow_missing_keys=False``.
        """
        self.assertFilterErrors(
            self._filter(
                {'foo': 'bar', 'baz': 'luhrmann'},
                keys=['foo', 'foobie', 'foobar'],
                allow_missing_keys=False,
            ),
            {
                'foobie': [f.Pick.CODE_MISSING_KEY],
                'foobar': [f.Pick.CODE_MISSING_KEY],
            },
            {'foo': 'bar', 'foobie': None, 'foobar': None},
        )

    def test_pass_mapping_allow_missing_keys_iterable(self):
        """
        An incoming value is missing one or more requested keys, but they are
        allowed to be missing because of ``allow_missing_keys``.
        """
        self.assertFilterPasses(
            self._filter(
                {'foo': 'bar', 'baz': 'luhrmann'},
                keys=['foo', 'foobie', 'foobar'],
                allow_missing_keys={'foobie', 'foobar'},
            ),
            {'foo': 'bar', 'foobie': None, 'foobar': None},
        )

    def test_pass_sequence(self):
        """
        Using the filter to pick specific indices from a sequence.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz'], keys=[0, 2]),
            ['foo', 'baz'],
        )

    def test_pass_sequence_exact_match(self):
        """
        The incoming sequence contains only the indices to be picked.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz'], keys=[0, 1, 2])
        )

    def test_pass_sequence_ordered_keys(self):
        """
        When keys are provided in an ordered collection, the order of keys
        determines the order of the items in the result.
        """
        self.assertFilterPasses(
            self._filter(
                ['Indiana', 'Marion', 'Marcus'],
                keys=[1, 0, 2],
            ),
            ['Marion', 'Indiana', 'Marcus'],
        )

    def test_pass_sequence_missing_values(self):
        """
        Any indices not present in the incoming value are set to ``None``.
        """
        self.assertFilterPasses(
            self._filter(['foo', 'bar', 'baz'], keys=[0, 2, 4]),
            ['foo', 'baz', None],
        )

    def test_pass_sequence_empty(self):
        """
        An empty sequence always passes this filter.

        Chain with :py:class:`MinLength` or :py:class:`NotEmpty` to reject
        empty sequences, or set ``allow_missing_keys`` when initialising the
        filter.
        """
        self.assertFilterPasses(
            self._filter([], keys=[1]),
            [None],
        )

    def test_pass_sequence_match_type(self):
        """
        Whenever practical, the filter will try to return the same type of
        value that it received.
        """
        runner = self.assertFilterPasses(
            self._filter(('foo', 'bar', 'baz'), keys=(1,)),
            ('bar',),
        )

        self.assertIsInstance(runner.cleaned_data, tuple)

    def test_fail_sequence_allow_missing_keys_false(self):
        """
        Incoming value is missing one or more requested indices, and the filter
        was initialised with ``allow_missing_keys=False``.
        """
        self.assertFilterErrors(
            self._filter(
                ['foo', 'bar'],
                keys={0, 2, 4},
                allow_missing_keys=False,
            ),
            {
                '2': [f.Pick.CODE_MISSING_KEY],
                '4': [f.Pick.CODE_MISSING_KEY],
            },
            ['foo', None, None],
        )

    def test_pass_sequence_allow_missing_keys_iterable(self):
        """
        An incoming value is missing one or more requested indices, but they
        are allowed to be missing because of ``allow_missing_keys``.
        """
        self.assertFilterPasses(
            self._filter(
                ['foo', 'bar'],
                keys={0, 2, 4},
                allow_missing_keys={2, 4},
            ),
            ['foo', None, None],
        )

    def test_fail_wrong_type(self):
        """
        The incoming value is neither a mapping nor a sequence.
        """
        self.assertFilterErrors(
            self._filter(42, keys={0}),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_error_empty_keys(self):
        """
        The ``keys`` param must not be empty.
        """
        self.assertRaises(f.FilterError, lambda: self.filter_type([]))


class RequiredTestCase(BaseFilterTestCase):
    filter_type = f.Required

    def test_fail_none(self):
        """
        :py:class:`f.Required` is the only filter that does not allow null
        values.
        """
        self.assertFilterErrors(None, [f.Required.CODE_EMPTY])

    def test_pass_non_empty_string(self):
        """
        The incoming value is a non-empty string.
        """
        self.assertFilterPasses('Hello, world!')

    def test_pass_non_empty_collection(self):
        """
        The incoming value is a collection with length > 0.
        """
        # The values in the collection may be empty, but the collection itself
        # is not.
        self.assertFilterPasses(['', '', ''])
        self.assertFilterPasses({'': ''})
        self.assertFilterPasses(Lengthy(1))
        # etc.

    def test_pass_non_collection(self):
        """
        Any value that does not have a length is assumed to be not empty.
        """
        self.assertFilterPasses(object())

    def test_fail_empty_string(self):
        """
        The incoming value is an empty string.
        """
        self.assertFilterErrors('', [f.Required.CODE_EMPTY])

    def test_fail_empty_collection(self):
        """
        The incoming value is a collection with length < 1.
        """
        self.assertFilterErrors([], [f.Required.CODE_EMPTY])
        self.assertFilterErrors({}, [f.Required.CODE_EMPTY])
        self.assertFilterErrors(Lengthy(0), [f.Required.CODE_EMPTY])
        # etc.

    def test_zero_is_not_empty(self):
        """
        PHP developers take note!
        """
        self.assertFilterPasses(0)

    def test_false_is_not_empty(self):
        """
        The boolean value ``False`` is NOT considered empty because it
        represents SOME kind of value.
        """
        self.assertFilterPasses(False)


class TypeTestCase(BaseFilterTestCase):
    filter_type = f.Type

    def test_pass_none(self):
        """
        ``None`` always passes this filter.

        Use ``Required | Type`` if you want to reject null values.
        """
        self.assertFilterPasses(
            self._filter(None, allowed_types=str),
        )

    def test_pass_matching_type(self):
        """
        The incoming value has the expected type.
        """
        self.assertFilterPasses(
            self._filter('Hello, world!', allowed_types=str),
        )

    def test_fail_non_matching_type(self):
        """
        The incoming value does not have the expected type.
        """
        self.assertFilterErrors(
            self._filter(b'Not a string, sorry.', allowed_types=str),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_multiple_allowed_types(self):
        """
        You can configure the filter to allow multiple types.
        """
        self.assertFilterPasses(
            self._filter('Hello, world!', allowed_types=(str, int)),
        )

        self.assertFilterPasses(
            self._filter(42, allowed_types=(str, int)),
        )

        self.assertFilterErrors(
            self._filter(b'Not a unicode.', allowed_types=(str, int)),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_pass_subclass_allowed(self):
        """
        The incoming value's type is a subclass of an allowed type.
        """
        self.assertFilterPasses(
            # bool is a subclass of int.
            self._filter(True, allowed_types=int),
        )

    def test_fail_subclass_not_allowed(self):
        """
        You can configure the filter to require exact type matches.
        """
        self.assertFilterErrors(
            self._filter(True, allowed_types=int, allow_subclass=False),
            [f.Type.CODE_WRONG_TYPE],
        )

    def test_fail_types_are_not_instances(self):
        """
        The filter checks that the value is an INSTANCE of its allowed type(s).
        It will reject the type(s) themselves.
        """
        self.assertFilterErrors(
            self._filter(str, allowed_types=str),
            [f.Type.CODE_WRONG_TYPE],
        )
