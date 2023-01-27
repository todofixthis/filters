Simple Filters
==============
Simple filters perform validations and transformations on individual values.

.. tip::

   The filters library has extensive `unit tests`_ that are thoroughly
   documented and designed to be easy for humans to read.  If you have any
   questions about how individual filters are meant to be used that aren't
   answered in the documentation, there's a good chance that you can find the
   answers in the `unit tests`_ 😺

.. _array:

Array
-----
Checks that a value is a ``Sequence`` type, but not a string.

For example, ``list`` or any class that extends ``typing.Sequence`` will
pass, but any string type (or subclass thereof) will fail.

.. code-block:: python

   import filters as f
   from typing import Sequence

   runner = f.FilterRunner(f.Array, ['foo', 'bar', 'baz'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz']

   runner = f.FilterRunner(f.Array, 'foo, bar, baz')
   assert runner.is_valid() is False

   # Don't use ``Type(Sequence)`` unless you also want to allow strings!
   runner = f.FilterRunner(f.Type(Sequence), 'foo, bar, baz')
   assert runner.is_valid() is True

Base64Decode
------------
Decodes a byte string (``bytes`` type) that is encoded using
`Base 64 <https://en.wikipedia.org/wiki/Base64>`_.

Automatically handles URL-safe variant and incorrect/missing padding.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Base64Decode, b'SGVsbG8sIHdvcmxkIQ==')
   assert runner.is_valid() is True
   assert runner.cleaned_data == b'Hello, world!'

.. note::

   This filter operates on (and returns) byte strings, not unicode strings!

   If the incoming value could be a unicode string, chain a
   :py:class:`filters.ByteString` in front of :py:class:`filters.Base64Decode`:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(
          f.ByteString | f.Base64Decode,
          'SGVsbG8sIHdvcmxkIQ==',
      )
      assert runner.is_valid() is True
      assert runner.cleaned_data == b'Hello, world!'

   If you want the resulting value to be a unicode string as well, add
   :py:class:`filters.Unicode` to the end of the chain:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(
          f.ByteString | f.Base64Decode | f.Unicode,
          'SGVsbG8sIHdvcmxkIQ==',
      )
      assert runner.is_valid() is True
      assert runner.cleaned_data == 'Hello, world!'

ByteArray
---------
Attempts to convert a value into a ``bytearray``.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(
       f.ByteArray,
       b'|\xa8\xc1.8\xbd4\xd5s\x1e\xa6%+\xea!6',
   )
   # Note that "numeric" characters like "8" and "6" are NOT interpreted
   # literally (e.g., "8" is ASCII code point 58, so it gets converted to
   # ``58`` in the resulting ``bytearray``, not ``8``).  This matches the
   # behaviour of Python's built-in ``bytearray`` type.
   assert runner.is_valid() is True
   assert runner.cleaned_data == bytearray([
       124, 168, 193, 46, 56, 189, 52, 213,
       115, 30, 166, 37, 43, 234, 33, 54,
   ])

If the incoming value is a unicode string, it is first converted into ``bytes``
using the UTF-8 encoding by default.  If you want it to use a different
encoding, you can provide it to the filter's initialiser:

.. code-block:: python

   import filters as f

   # Unicode string is encoded using UTF-8 by default.
   runner = f.FilterRunner(f.ByteArray, 'Iñtërnâtiônàlizætiøn')
   assert runner.is_valid() is True
   assert runner.cleaned_data == bytearray([
       73, 195, 177, 116, 195, 171, 114, 110, 195, 162, 116, 105, 195,
       180, 110, 195, 160, 108, 105, 122, 195, 166, 116, 105, 195, 184, 110,
   ])

   # You can specify a different encoding.
   runner = f.FilterRunner(f.ByteArray('iso-8859-1'), 'Iñtërnâtiônàlizætiøn')
   assert runner.is_valid() is True
   assert runner.cleaned_data == bytearray([
       73, 241, 116, 235, 114, 110, 226, 116, 105, 244,
       110, 224, 108, 105, 122, 230, 116, 105, 248, 110,
   ])

ByteString
----------
Converts a value into a byte string (``bytes`` type).

By default, this filter encodes the result using UTF-8, but you can change this
via the ``encoding`` parameter in the filter initialiser.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.ByteString, 'Iñtërnâtiônàlizætiøn')
   assert runner.is_valid() is True
   # 'Iñtërnâtiônàlizætiøn' encoded as bytes using utf-8:
   assert runner.cleaned_data ==\
       b'I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3' \
       b'\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n'

Call
----
Calls an arbitrary function on the incoming value.

.. note::

   This filter is almost always inferior to :doc:`/writing_filters`, but it can
   be useful for quickly injecting a function into a filter chain, just to see
   if it will work.

.. code-block:: python

   import filters as f

   def div_two(value):
       if value % 2:
           raise f.FilterError('value is not even!')
       return value / 2

   runner = f.FilterRunner(f.Call(div_two), 42)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 21

   runner = f.FilterRunner(f.Call(div_two), 43)
   assert runner.is_valid() is False

.. important::
   The function must raise a :py:class:`filters.FilterError` to indicate that
   the incoming value is not valid.

   If the function returns any value (including `False`, `None`, etc.) then
   the incoming value will be considered valid.

   .. code-block:: python

      def div_two(value):
          return False if value % 2 else value / 2

      runner = f.FilterRunner(f.Call(div_two), 43)
      assert runner.is_valid() is True
      assert runner.cleaned_data is False

CaseFold
--------
Applies
`case folding <https://en.wikipedia.org/wiki/Letter_case#Case_folding>`_ to a
string value.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.CaseFold, 'Weißkopfseeadler')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'weisskopfseeadler'

   # Note that case-folded does not necessarily mean ASCII-compatible!
   runner = f.FilterRunner(f.CaseFold, 'İstanbul')
   assert runner.cleaned_data == 'i\u0307stanbul'

Choice
------
Requires the incoming value to match one of the values specified in the filter's
initialiser.

.. code-block:: python

   import filters as f

   filter_ = f.Choice(choices=('Moe', 'Larry', 'Curly'))

   runner = f.FilterRunner(filter_, 'Curly')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Curly'

   runner = f.FilterRunner(filter_, 'Shemp')
   assert runner.is_valid() is False

.. note::

   The comparison is case-sensitive; chain this filter with
   :py:class:`filters.CaseFold` for case-insensitive comparison (but note that
   this will modify the resulting value).

Date
----
Interprets a string as a date.  The result is a ``datetime.date`` instance.

.. code-block:: python

   import filters as f
   from datetime import date

   runner = f.FilterRunner(f.Date, '2015-05-11')
   assert runner.is_valid() is True
   assert runner.cleaned_data == date(2015, 5, 11)

.. note::

   If the incoming value appears to be a datetime with tzinfo, it is first
   converted to UTC.  In some cases, this can make the resulting date appear to
   be off by 1 day.

   .. code-block:: python

      import filters as f
      from datetime import date

      runner = f.FilterRunner(f.Date, '2015-05-11T19:56:58-05:00')
      assert runner.is_valid() is True
      # The resulting date appears to occur 1 day later that the original
      # value because it gets converted to UTC.
      assert runner.cleaned_data == date(2015, 5, 12)

   By default, the filter assumes that naive timestamps are UTC; if you need to
   change this, you can pass an optional ``timezone`` argument to the filter's
   initialiser:

   .. code-block:: python

      import filters as f
      from datetime import date
      from dateutil.tz import tzoffset

      # The filter is configured to interpret naive timestamps as if they are
      # UTC+8.
      filter_ = f.Date(timezone=tzoffset('UTC+8', 8 * 3600))

      runner = f.FilterRunner(filter_, '2015-05-12 03:20:03')
      assert runner.is_valid() is True
      # The resulting date appears to occur 1 day earlier because the filter
      # subtracted 8 hours to convert the value to UTC.
      assert runner.cleaned_data == date(2015, 5, 11)

      # Note that non-native timestamps are NOT coerced!
      runner = f.FilterRunner(filter_, '2015-05-12T03:20:03+01:00')
      assert runner.is_valid() is True
      assert runner.cleaned_data == date(2015, 5, 12)

Datetime
--------
Interprets a string as a datetime.  The result is a ``datetime.datetime``
instance with ``tzinfo=utc``.

If the incoming value includes a timezone indicator, it is automatically
converted to UTC.  Otherwise, it is assumed to already be UTC (this can be
configured via the filter initialiser).

.. code-block:: python

   import filters as f
   from datetime import datetime
   from pytz import utc

   runner = f.FilterRunner(f.Datetime, '2015-05-11 14:56:58')
   assert runner.is_valid() is True
   assert runner.cleaned_data == datetime(2015, 5, 11, 14, 56, 58, tzinfo=utc)

.. important::

   The resulting datetime **always** has ``tzinfo=utc``.

   Like :py:class:`filters.Date`, :py:class:`filters.Datetime` assumes that
   incoming naive timestamps are UTC; you can change this by providing a
   ``timezone`` argument to the filter initializer.  The filter will use this
   value when converting naive timestamps to UTC.

   This is really important (and potentially confusing 😇): the filter
   **always** returns a UTC ``datetime``!  The ``timezone`` argument tells the
   filter how to interpret naive timestamps, **not** which timezone to use for
   the resulting ``datetime`` values!

   Example:

   .. code-block:: python

      import filters as f
      from datetime import datetime
      from dateutil.tz import tzoffset
      from pytz import utc

      # Interpret naive timestamps as UTC+8.
      filter_ = f.Datetime(timezone=tzoffset('UTC+8', 8 * 3600))

      # Naive timestamps are assumed to be UTC+8 and converted to UTC.
      runner = f.FilterRunner(filter_, '2015-05-12 09:20:03')
      assert runner.is_valid() is True
      assert runner.cleaned_data == datetime(2015, 5, 12, 1, 20, 3, tzinfo=utc)

      # Non-naive timestamp tzinfo is respected by the filter, and the result is
      # still converted to UTC for consistency.
      runner = f.FilterRunner(filter_, '2015-05-11T21:14:38+04:00')
      assert runner.is_valid() is True
      assert runner.cleaned_data ==\
          datetime(2015, 5, 11, 17, 14, 38, tzinfo=utc)

Decimal
-------
Interprets the incoming value as a ``decimal.Decimal``.

Virtually any value that can be passed to ``decimal.Decimal.__init__`` is
accepted (including scientific notation), with a few exceptions:

   - Non-finite values (e.g., ``NaN``, ``+Inf``, etc.) are not allowed.
   - Tuple/list values (e.g., ``(0, (4, 2), -1)``) are allowed by default,
     but you can disallow these values in the filter initialiser.

.. code-block:: python

   import filters as f
   from decimal import Decimal

   runner = f.FilterRunner(f.Decimal, '3.1415926')
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Decimal)
   assert runner.cleaned_data == Decimal('3.1415926')

The filter initialiser also accepts a parameter to set max precision.  If
specified, the resulting values will be *rounded* to the specified number
of decimal places.

.. code-block:: python

   import filters as f
   from decimal import Decimal

   runner = f.FilterRunner(f.Decimal(3), '3.1415926')
   assert runner.is_valid() is True
   assert runner.cleaned_data == Decimal('3.142')

.. tip::

   If you want to control how the rounding is applied (e.g., always round
   down), chain this filter with :py:class:`filters.Round`:

   .. code-block:: python

      import filters as f
      from decimal import Decimal, ROUND_FLOOR

      runner = f.FilterRunner(
          f.Decimal | f.Round('0.001', ROUND_FLOOR),
          '3.1415926',
      )
      assert runner.is_valid() is True
      # Value will always be rounded down.
      assert runner.cleaned_data == Decimal('3.141')

Empty
-----
Requires that a value have a length of zero.

Values that are not ``Sized`` (i.e., do not have ``__len__``) are considered
to be not empty.  In particular, this means that ``0`` and ``False`` are
*not* considered empty in this context.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Empty, [])
   assert runner.is_valid() is True
   assert runner.cleaned_data == []

   runner = f.FilterRunner(f.Empty, ['foo', 'bar', 'baz', 'luhrmann'])
   assert runner.is_valid() is False

This filter also works on strings, as well as anything else that has a
length (i.e., whose type implements ``typing.Sized``):

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Empty, '')
   assert runner.is_valid() is True
   assert runner.cleaned_data == ''

   runner = f.FilterRunner(f.Empty, 'Hello, world!')
   assert runner.is_valid() is False

Int
---
Interprets the incoming value as an int.

Strings and other compatible types will be converted transparently:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Int, '42')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 42

Floats are valid only if they have an empty fpart:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Int, '42.000000000000000000')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 42

   runner = f.FilterRunner(f.Int, '42.000000000000000001')
   assert runner.is_valid() is False

IpAddress
---------
Validates the incoming value as an IP address.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.IpAddress, '127.0.0.1')
   assert runner.is_valid() is True
   assert runner.cleaned_data == '127.0.0.1'

   runner = f.FilterRunner(f.IpAddress, 'localhost')
   assert runner.is_valid() is False

By default, this filter only accepts IPv4 addresses, but you can configure the
filter to also/only accept IPv6 addresses via its initialiser.

For IPv6 addresses, the result is always converted to its `short form`_.

.. code-block:: python

   import filters as f

   # Accept IPv6 addresses only.
   filter_ = f.IpAddress(ipv4=False, ipv6=True)

   runner = f.FilterRunner(filter_, '0:0:0:0:0:0:0:1')
   assert runner.is_valid() is True
   assert runner.cleaned_data == '::1'

   runner = f.FilterRunner(filter_, '1027.0.0.1')
   assert runner.is_valid() is False

JsonDecode
----------
Decodes a string that is JSON-encoded.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.JsonDecode, '{"foo": "bar", "baz": "luhrmann"}')
   assert runner.is_valid() is True
   assert runner.cleaned_data == {'foo': 'bar', 'baz': 'luhrmann'}

Note that this filter can be chained with other filters.  For example, you can
use ``f.JsonDecode | f.FilterMapper(...)`` to apply filters to a JSON-encoded
dict:

.. code-block:: python

   import filters as f
   from datetime import date

   runner = f.FilterRunner(
       f.JsonDecode |
       f.FilterMapper({
           'birthday':  f.Date,
           'gender':    f.CaseFold | f.Choice(choices={'m', 'f', 'x'}),
       }),
       '{"birthday":"1879-03-14", "gender":"M"}'
   )
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'birthday': date(1879, 3, 14),
       'gender': 'm',
   }

Check out :ref:`filterception` for more fun examples 😺

Length
------
Requires that a value's length matches the value specified in the filter
initialiser.

Values that are not ``Sized`` (i.e., do not have ``__len__``) automatically
fail.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Length(3), ['foo', 'bar', 'baz'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz']

   runner = f.FilterRunner(f.Length(3), ['foo', 'bar', 'baz', 'luhrmann'])
   assert runner.is_valid() is False

This filter also works on strings, as well as anything else that has a
length (i.e., whose type implements ``typing.Sized``):

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Length(23), 'Kia ora e te ao whānui!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Kia ora e te ao whānui!'

   runner = f.FilterRunner(f.Length(23), '¡Hola, mundo!')
   assert runner.is_valid() is False

.. note::

   :py:class:`filters.Length` requires the incoming value to have *exactly*
   the specified length; if you want to check that the incoming value has a
   minimum or maximum length, use :py:class:`filters.MinLength` or
   :py:class:`filters.MaxLength`, respectively.

Max
---
Requires that the value be less than [or equal to] the value specified in the
filter initialiser.

.. code-block:: python

   import filters as f

   # Incoming value is less than max.
   runner = f.FilterRunner(f.Max(5), 4)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 4

   # Incoming value is equal to max.
   runner = f.FilterRunner(f.Max(5), 5)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 5

   # Incoming value is greater than max.
   runner = f.FilterRunner(f.Max(5), 6)
   assert runner.is_valid() is False

If you only want to allow incoming values that are less than (not equal to) the
max value, set ``exclusive=True`` in the filter's initialiser:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Max(5, exclusive=True), 5)
   assert runner.is_valid() is False

MaxBytes
--------
Truncates a unicode string to a max number of bytes.  When converting to a
multibyte encoding (e.g., UTF-8), the filter will truncate additional bytes as
needed to avoid orphaned sequences (see example below).

.. important::

   The resulting value will be a byte string (``bytes`` type), not a unicode
   string!

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.MaxBytes(24), 'Γειάσου Κόσμε')
   # Value is too long, so ``is_valid()`` returns ``False``.
   assert runner.is_valid() is False
   # Note that the resulting value is truncated to 23 bytes instead of 24, so
   # as not to orphan a multibyte sequence.
   assert runner.cleaned_data ==\
       b'\xce\x93\xce\xb5\xce\xb9\xce\xac\xcf\x83\xce\xbf' \
       b'\xcf\x85 \xce\x9a\xcf\x8c\xcf\x83\xce\xbc'

.. tip::

   If you just want to validate the length of the input and don't need to
   waste CPU cycles truncating too-long values, you can provide `truncate=False`
   to the filter's initialiser:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(f.MaxBytes(24, truncate=False), 'Γειάσου Κόσμε')
      assert runner.is_valid() is False
      assert runner.cleaned_data is None

MaxLength
---------
Requires that a value's length is less than or equal to the value specified in
the filter initialiser.

Values that are not ``Sized`` (i.e., do not have ``__len__``) automatically
fail.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.MaxLength(3), ['foo', 'bar', 'baz'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz']

   runner = f.FilterRunner(f.MaxLength(3), ['foo', 'bar', 'baz', 'luhrmann'])
   assert runner.is_valid() is False

This filter also works on strings, as well as anything else that has a length
(i.e., whose type implements ``typing.Sized``):

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.MaxLength(20), '¡Hola, mundo!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == '¡Hola, mundo!'

   runner = f.FilterRunner(f.MaxLength(20), 'Kia ora e te ao whānui!')
   assert runner.is_valid() is False

Min
---
Requires that the value be greater than [or equal to] the value specified in the
filter initialiser.

.. code-block:: python

   import filters as f

   # Incoming value is greater than min.
   runner = f.FilterRunner(f.Min(5), 6)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 6

   # Incoming value is equal to min.
   runner = f.FilterRunner(f.Min(5), 5)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 5

   # Incoming value is less than min.
   runner = f.FilterRunner(f.Min(5), 4)
   assert runner.is_valid() is False

If you only want to allow incoming values that are greater than (not equal to)
the min value, set ``exclusive=True`` in the filter's initialiser:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Min(5, exclusive=True), 5)
   assert runner.is_valid() is False

:py:class:`filters.Round`
Rounds the incoming value to the nearest integer or fraction specified in
the filter initialiser.

The result is always a ``decimal.Decimal`` instance, to avoid issues with
`floating-point precision`_.

.. code-block:: python

   import filters as f
   from decimal import Decimal

   runner = f.FilterRunner(f.Round('5'), 42)
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Decimal)
   assert runner.cleaned_data == Decimal('40')

   runner = f.FilterRunner(f.Round('5'), 43)
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Decimal)
   assert runner.cleaned_data == Decimal('45')

.. important::

   When specifying a decimal value to round to, use a string value, in order
   to prevent aforementioned issues with `floating-point precision`_.

   .. code-block:: python

      import filters as f

      # NO: Potentially unsafe; don't do this!
      runner = f.FilterRunner(f.Round(0.001), '3.1415926')

      # YES: Do this instead:
      runner = f.FilterRunner(f.Round('0.001'), '3.1415926')

You can also control the rounding behaviour by specifying a `rounding mode`_:

.. code-block:: python

   import filters as f
   from decimal import ROUND_CEILING, ROUND_FLOOR

   # Always round up:
   runner = f.FilterRunner(f.Round('0.25', ROUND_CEILING), '0.26')
   assert runner.is_valid() is True
   assert runner.cleaned_data == Decimal('0.5')

   # Always round down:
   runner = f.FilterRunner(f.Round('0.25', ROUND_FLOOR), '0.49')
   assert runner.is_valid() is True
   assert runner.cleaned_data == Decimal('0.25')

MinLength
---------
Requires that a value's length is greater than or equal to the value specified
in the filter initialiser.

Values that are not ``Sized`` (i.e., do not have ``__len__``) automatically
fail.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.MinLength(3), ['foo', 'bar', 'baz'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz']

   runner = f.FilterRunner(f.MinLength(3), ['foo', 'bar'])
   assert runner.is_valid() is False

This filter also works on strings, as well as anything else that has a length
(i.e., whose type implements ``typing.Sized``):

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.MinLength(20), 'Kia ora e te ao whānui!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Kia ora e te ao whānui!'

   runner = f.FilterRunner(f.MinLength(20), '¡Hola, mundo!')
   assert runner.is_valid() is False

NamedTuple
----------
Converts the incoming value into a named tuple

Initialize this filter with the type of named tuple that you want to use for
conversions.

.. code-block:: python

   import filters as f
   from collections import namedtuple

   Colour = namedtuple('Colour', ('r', 'g', 'b', 'a'))

   runner = f.FilterRunner(f.NamedTuple(Colour), [65, 105, 225, 1])
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Colour)
   assert runner.cleaned_data == Colour(65, 105, 225, 1)

.. tip::

   You can also provide an optional filter map, which will be applied to the
   values in the resulting named tuple.

   .. code-block:: python

      import filters as f
      from collections import namedtuple
      from decimal import Decimal

      Colour = namedtuple('Colour', ('r', 'g', 'b', 'a'))

      runner = f.FilterRunner(
          f.NamedTuple(Colour, {
              'r': f.Required | f.Int | f.Min(0) | f.Max(255),
              'g': f.Required | f.Int | f.Min(0) | f.Max(255),
              'b': f.Required | f.Int | f.Min(0) | f.Max(255),
              'a': f.Optional(default=1) | f.Decimal | f.Min(0) | f.Max(1),
          }),
          ["65", "105", "225", "0.75"],
      )
      assert runner.is_valid() is True
      assert isinstance(runner.cleaned_data, Colour)
      assert runner.cleaned_data == Colour(65, 105, 225, Decimal('0.75'))

NoOp
----
This filter returns the incoming value unmodified.

It can be useful in cases where you need a function to return a filter
instance, even in cases where no filtering is needed.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.NoOp, 'literally anything')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'literally anything'

.. tip::

   In many contexts, you can safely substitute ``None`` for
   :py:class:`filters.NoOp`:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(
         f.Unicode | None | f.NotEmpty,
         'literally anything',
      )
      assert runner.is_valid() is True
      assert runner.cleaned_data == 'literally anything'

   An example of a case where you might need to use :py:class:`NoOp` is if you
   want to make the first filter in a chain dynamic, e.g.:

   .. code-block:: python

      import filters as f
      from decimal import Decimal

      @f.filter_macro
      def Number(strip_sign: bool = False):
          # Can't return ``None`` here, or else an error will occur when we
          # try to chain it with ``f.Min`` below, so we have to use ``f.NoOp``
          # instead.
          return f.Strip(r'-') if strip_sign else f.NoOp | f.Decimal

      runner = f.FilterRunner(Number | f.Min(42), '-100')
      assert runner.is_valid() is False

NotEmpty
--------
Requires that a value have a length greater than zero.

Values that are not ``Sized`` (i.e., do *not* have ``__len__``) are
considered to be **not empty**.  In particular, this means that ``0`` and
``False`` are *not* considered empty in this context.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.NotEmpty, ['foo', 'bar', 'baz', 'luhrmann'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz', 'luhrmann']

   runner = f.FilterRunner(f.NotEmpty, [])
   assert runner.is_valid() is False

This filter also works on strings, as well as anything else that has a
length (i.e., whose type implements ``typing.Sized``):

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.NotEmpty, 'Hello, world!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Hello, world!'

   runner = f.FilterRunner(f.NotEmpty, '')
   assert runner.is_valid() is False

.. important::

   ``None`` always passes this filter (see :ref:`none-is-special` for more
   information).  Use :py:class:`filters.Required` to reject ``None``:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(f.NotEmpty, None)
      assert runner.is_valid() is True

      runner = f.FilterRunner(f.Required, None)
      assert runner.is_valid() is False

Optional
--------
Provides a default value that will be returned if the incoming value is
``None`` or empty (has a length of zero or is ``None``).

Values that are not ``Sized`` (i.e., do not have ``__len__``) are considered
to be *not* empty.  In particular, this means that ``0`` and ``False`` are
*not* considered empty in this context.

.. code-block:: python

   import filters as f

   filter_ = f.Optional('t') | f.Choice({'t', 'f'})

   runner = f.FilterRunner(filter_, 'f')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'f'

   runner = f.FilterRunner(filter_, '')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 't'

   # Also returns the default when the incoming value is ``None``:
   runner = f.FilterRunner(filter_, None)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 't'

.. important::

   :py:class:`filters.FilterRunner` stops processing filters as soon as a
   value is determined to be invalid, so putting this filter at the end of
   a chain very likely will not do what you expect.

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(f.Choice({'t', 'f'}) | f.Optional('t'), '')
      # Incoming value ``''`` does not match any valid choices, so the runner
      # stops before it gets to the ``Optional`` filter!
      assert runner.is_valid() is False
      assert runner.cleaned_data is None

Regex
-----
Executes a regular expression against a string value.  The regex must match in
order for the string to be considered valid.

This filter returns a list of matches.

.. important::

   The result is **always** a list, even if there is only a single match.

   Groups are not included in the result.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Regex(r'\d+'), '42-86-99')
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['42', '86', '99']

.. tip::

   You can chain :py:class:`filters.Regex` with
   :py:class:`filters.FilterRepeater` to apply filters to the matched values:

   .. code-block:: python

      import filters as f

      runner = f.FilterRunner(
          f.Regex(r'\d+') | f.FilterRepeater(f.Int),
          '42-86-99',
      )
      assert runner.is_valid() is True
      assert runner.cleaned_data == [42, 86, 99]

Required
--------
Basically the same as :py:class:`NotEmpty`, except it also rejects ``None``.

This filter is the only exception to the "``None`` always passes" rule (see
:ref:`none-is-special` for more information).

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Required, ['foo', 'bar', 'baz', 'luhrmann'])
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz', 'luhrmann']

   runner = f.FilterRunner(f.Required, [])
   assert runner.is_valid() is False

   runner = f.FilterRunner(f.Required, None)
   assert runner.is_valid() is False

   # Note that every other filter allows ``None``!
   runner = f.FilterRunner(f.NotEmpty, None)
   assert runner.is_valid() is True
   assert runner.cleaned_data is None

Split
-----
Uses a regular expression to split a string value into chunks.

The result is always a list.  If the regular expression doesn't match anything
in an incoming value, then that value is returned as a single-item list
(see example below).

.. code-block:: python

   import filters as f

   filter_ = f.Split(r':+')

   runner = f.FilterRunner(filter_, 'foo:bar::baz:::')
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo', 'bar', 'baz', '']

   runner = f.FilterRunner(filter_, 'foo bar baz')
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['foo bar baz']

Strip
-----
Removes whitespace from the start and end of a string.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Strip, '\r  \t \x00 Hello, world! \x00 \t  \n')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Hello, world!'

Alternatively, you can use regular expressions to control what the filter strips
from incoming values:

.. code-block:: python

  import filters as f

  runner = f.FilterRunner(
      f.Strip(leading=r'\d', trailing=r"['a-z ]+"),
      "54321 A long time ago... in a galaxy far far away ",
  )
  assert runner.is_valid() is True
  assert runner.cleaned_data == '4321 A long time ago...'

Type
----
Requires that the incoming value have the type(s) specified in the filter
initialiser.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Type(str), 'Hello, world!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Hello, world!'

   runner = f.FilterRunner(f.Type(str), 42)
   assert runner.is_valid() is False

You can specify a tuple of types, the same as you would for ``isinstance``:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Type((str, int)), 'Hello, world!')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Hello, world!'

   runner = f.FilterRunner(f.Type((str, int)), 42)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 42

   runner = f.FilterRunner(f.Type((str, int)), ['Hello, world!', 42])
   assert runner.is_valid() is False

By default, the filter permits subclasses, but you can configure it via the
initialiser to require an exact type match:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Type(int, allow_subclass=False), 1)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 1

   runner = f.FilterRunner(f.Type(int, allow_subclass=False), True)
   assert runner.is_valid() is False

   # Default behaviour is to allow subclasses.
   runner = f.FilterRunner(f.Type(int), True)
   assert runner.is_valid() is True
   assert runner.cleaned_data is True

.. tip::

   If you want to check that an incoming value is a list or other sequence, use
   :ref:`array` instead of ``Type(Sequence)``:

   .. code-block:: python

      import filters as f
      from typing import Sequence

      # Works as expected for lists...
      runner = f.FilterRunner(f.Type(Sequence), ['foo', 'bar', 'baz'])
      assert runner.is_valid() is True

      # ... but strings are also sequences!
      runner = f.FilterRunner(f.Type(Sequence), 'foo, bar, baz')
      assert runner.is_valid() is True

      # To avoid this issue, use ``f.Array`` instead.
      runner = f.FilterRunner(f.Array, ['foo', 'bar', 'baz'])
      assert runner.is_valid() is True

      runner = f.FilterRunner(f.Array, 'foo, bar, baz')
      assert runner.is_valid() is False

Unicode
-------
Converts a value to a unicode string (``str`` type).

By default the filter also applies the following transformations:

- Convert to `NFC form`_.
- Remove non-printable characters.
- Convert line endings to unix style (e.g., ``\r\n`` => ``\n``).

If desired, you can disable these extra transformations by passing
``normalize=False`` (note American spelling) to the filter initialiser.

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(
       f.Unicode,

       # You get used to it.  I don't even see the code; all I see is,
       # "blond"... "brunette"... "redhead"...
       # Hey, you uh... want a drink?
       b'\xe2\x99\xaa '
       b'\xe2\x94\x8f(\xc2\xb0.\xc2\xb0)\xe2\x94\x9b '
       b'\xe2\x94\x97(\xc2\xb0.\xc2\xb0)\xe2\x94\x93 '
       b'\xe2\x99\xaa',
   )
   assert runner.is_valid() is True
   assert runner.cleaned_data == '♪ ┏(°.°)┛ ┗(°.°)┓ ♪'

The filter expects the incoming value to be encoded using UTF-8.  If you need to
use a different encoding, provide it to the filter's initialiser:

.. code-block:: python

   import filters as f

   # Incoming value is not valid UTF-8.
   runner = f.FilterRunner(f.Unicode, b'\xc4pple')
   assert runner.is_valid() is False

   # Tell the filter to decode using Latin-1 instead.
   runner = f.FilterRunner(f.Unicode('iso-8859-1'), b'\xc4pple')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Äpple'

Uuid
----
Converts a string value into a :py:class:`uuid.UUID` object.

.. code-block:: python

   import filters as f
   from uuid import UUID

   runner = f.FilterRunner(f.Uuid, '3466c56a-2ebc-449d-97d2-9b119721ff0f')
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, UUID)
   assert runner.cleaned_data.hex == '3466c56a2ebc449d97d29b119721ff0f'
   assert runner.cleaned_data.version == 4

By default, any UUID version is allowed, but you can specify the required
version in the filter initialiser:

.. code-block:: python

   import filters as f

   filter_ = f.Uuid(version=4)

   runner = f.FilterRunner(filter_, '3466c56a-2ebc-449d-97d2-9b119721ff0f')
   assert runner.is_valid() is True

   runner = f.FilterRunner(filter_, '2830f705596911e59628e0f8470933c8')
   # Incoming value is a v1 UUID, but we're expecting a v4.
   assert runner.is_valid() is False

.. note::

   UUIDs can be provided in several different formats; the following values are
   all considered to be correct representations of the same UUID:

   - ``3466c56a-2ebc-449d-97d2-9b119721ff0f``
   - ``3466c56a2ebc449d97d29b119721ff0f``
   - ``{3466c56a2ebc449d97d29b119721ff0f}``
   - ``urn:uuid:3466c56a-2ebc-449d-97d2-9b119721ff0f``

   This flexibility is baked into `Python's UUID class`_; if for some reason you
   do not want to allow alternative formats, chain the filter with
   :py:class:`filters.Regex`:

   .. code-block:: python

      import filters as f
      from uuid import UUID

      # Adapted from https://stackoverflow.com/a/6640851
      uuid_regex =\
          r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$'

      # Regex filter returns an array, so we have to use FilterRepeater.
      filter_ = f.Regex(uuid_regex) | f.FilterRepeater(f.Uuid)

      runner = f.FilterRunner(filter_, '3466c56a-2ebc-449d-97d2-9b119721ff0f')
      assert runner.is_valid() is True
      assert runner.cleaned_data ==\
          [UUID('3466c56a-2ebc-449d-97d2-9b119721ff0f')]

      runner = f.FilterRunner(
          filter_,
          'urn:uuid:3466c56a-2ebc-449d-97d2-9b119721ff0f'
      )
      assert runner.is_valid() is False

.. _floating-point precision: https://en.wikipedia.org/wiki/Floating_point#Accuracy_problems
.. _NFC form: https://en.wikipedia.org/wiki/Unicode_equivalence
.. _Python's UUID class: https://docs.python.org/3/library/uuid.html#uuid.UUID
.. _rounding mode: https://docs.python.org/3/library/decimal.html#rounding-modes
.. _short form: https://en.wikipedia.org/wiki/IPv6_address#Representation
.. _unit tests: https://github.com/todofixthis/filters/tree/master/test
