Writing Your Own Filters
========================
Although the Filters library comes with
:doc:`lots of built-in filters </simple_filters>`, oftentimes it is useful to
be able to write your own.

There are three ways that you can create new filters:

* Macros
* Partials
* Custom Filters

Macros
------
If you find yourself using a particular filter chain over and over, you can
create a macro to save yourself some typing.

To create a macro, define a function that returns a filter chain, then decorate
it with the ``filters.filter_macro`` decorator:

.. code-block:: python

   import filters as f

   @f.filter_macro
   def String(allowed_types=None):
     return f.Type(allowed_types or str) | f.Unicode | f.Strip

You can now use your filter macro just like any other filter:

.. code-block:: python

   runner = f.FilterRunner(String | f.Required, '   Hello, world!    ')
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'Hello, world!'


Partials
--------
A partial is a special kind of macro.  Instead of returning a filter chain,
it returns a single filter, but with different configuration values.

Here's an example of a partial that can be used to validate datetimes from New
Zealand, convert to UTC, and strip ``tzinfo`` from the result:

.. code-block:: python

   import filters as f

   # Create a partial for ``f.Datetime(timezone=13, naive=True)``.
   NZ_Datetime = f.filter_macro(f.Datetime, timezone=13, naive=True)

Just like with macros, you can use a partial anywhere you can use a regular
filter:

.. code-block:: python

   from datetime import datetime

   runner = f.FilterRunner(NZ_Datetime | f.Required, '2016-12-11 15:00:00')
   assert runner.is_valid() is True
   assert runner.cleaned_data == datetime(2016, 12, 11, 2, 0, 0, tzinfo=None)

Additionally, partials act just like :py:func:`functools.partial` objects; you
can invoke them with different parameters if you want:

.. code-block:: python

   from pytz import utc

   # Override the ``naive`` parameter for the ``NZ_Datetime`` partial.
   filter_ = NZ_Datetime(naive=False) | f.Required

   runner = f.FilterRunner(filter_, '2016-12-11 15:00:00')
   assert runner.is_valid() is True
   assert runner.cleaned_data == datetime(2016, 12, 11, 2, 0, 0, tzinfo=utc)


Custom Filters
--------------
Sometimes you just can't get what you want by assembling existing filters, and
you need to write your own.

To create a new filter, write a class that extends
:py:class:`filters.BaseFilter` and implement the ``_apply`` method:

.. code-block:: python

   import filters as f

   class Pkcs7Pad(f.BaseFilter):
     block_size = 16

     def _apply(self, value):
        extra_bytes = self.block_size - (len(value) % self.block_size)
        return value + bytes([extra_bytes] * extra_bytes)


Validation
^^^^^^^^^^
To implement validation in your filter, add the following:

* Define a unique code for each validation error.
* Define an error message template for each validation error.
* Add the logic to the filter's ``_apply`` method.

Here's the ``Pkcs7Pad`` filter with a little bit of validation logic:

.. code-block:: python

   import filters as f

   class Pkcs7Pad(f.BaseFilter):
     CODE_INVALID_TYPE = 'invalid_type'

     templates = {
       CODE_INVALID_TYPE = 'Binary string required.',
     }

     block_size = 16

     def _apply(self, value):
        if not isinstance(value, bytes):
          return self._invalid_value(value, self.CODE_INVALID_TYPE)

        extra_bytes = self.block_size - (len(value) % self.block_size)
        return value + bytes([extra_bytes] * extra_bytes)

Invoking Other Filters
^^^^^^^^^^^^^^^^^^^^^^
You can also invoke other filters in your custom filters by calling the
``self._filter`` method.

For example, we can simplify the implementation of ``Pkcs7Pad`` by incorporating
the :py:class:`filters.ByteString` filter:

.. code-block:: python

   import filters as f

   class Pkcs7Pad(f.BaseFilter):
     block_size = 16

     def _apply(self, value):
        # The incoming value must be a byte string.
        value = self._filter(value, f.Type(bytes))
        if self._has_errors:
            return None

        extra_bytes = self.block_size - (len(value) % self.block_size)
        return value + bytes([extra_bytes] * extra_bytes)

.. important::

   ``self._filter`` will not raise an exception if the value is invalid; your
   filter *must* check ``self._has_errors`` after calling ``self._filter(...)``!

Unit Tests
^^^^^^^^^^
The Filters library ships test helpers for both pytest and unittest.

pytest (recommended)
""""""""""""""""""""
When ``phx-filters`` is installed, pytest automatically registers a plugin that
injects two fixtures into your test suite — no imports or configuration
required:

* ``assert_filter_passes(filter_instance, test_value, expected_value=unmodified)``:
  Asserts that the filter returns the expected value without errors.
* ``assert_filter_errors(filter_instance, test_value, expected_codes, expected_value=None)``:
  Asserts that the filter generates the expected error codes.

Here's how to test ``Pkcs7Pad`` with pytest:

.. code-block:: python

   import filters as f

   def test_pass_none(assert_filter_passes):
       """``None`` always passes this filter."""
       assert_filter_passes(f.Pkcs7Pad(), None)

   def test_pass_padding(assert_filter_passes):
       """Padding a value to the correct length."""
       assert_filter_passes(
           f.Pkcs7Pad(),
           b'Hello, world!',
           b'Hello, world!\x03\x03\x03',
       )

   def test_fail_wrong_type(assert_filter_errors):
       """The incoming value is not a byte string."""
       assert_filter_errors(
           f.Pkcs7Pad(),
           'Hello, world!',
           [f.Type.CODE_WRONG_TYPE],
       )

The fixtures return the :py:class:`~filters.FilterRunner` instance, so you can
make further assertions on ``runner.cleaned_data`` if needed.

Two sentinel classes are available for advanced cases — import them explicitly:

.. code-block:: python

   from filters.pytest import skip_value_check, unmodified

* ``unmodified``: Pass as ``expected_value`` to assert the value passes through
  unchanged (the default behaviour of ``assert_filter_passes``).
* ``skip_value_check``: Pass as ``expected_value`` to skip the value assertion
  entirely and add your own checks instead.

unittest
""""""""
For projects using unittest, the :py:class:`filters.test.BaseFilterTestCase`
helper class is still fully supported.  Set ``filter_type`` on the class and
use the provided methods:

* ``assertFilterPasses``: Asserts the filter returns an expected value without
  errors.
* ``assertFilterErrors``: Asserts the filter generates the expected error codes.

.. code-block:: python

   import filters as f
   from filters.test import BaseFilterTestCase

   class Pkcs7PadTestCase(BaseFilterTestCase):
       # Specify your filter as ``filter_type``.
       filter_type = Pkcs7Pad

       def test_pass_none(self):
           """``None`` always passes this filter."""
           self.assertFilterPasses(None)

       def test_pass_padding(self):
           """Padding a value to the correct length."""
           # Use ``self.assertFilterPasses`` to check the result of filtering a
           # valid value.
           self.assertFilterPasses(
               # If this is the input...
               b'Hello, world!',
               # ... this is the expected result.
               b'Hello, world!\x03\x03\x03'
           )

       def test_fail_wrong_type(self):
           """The incoming value is not a byte string."""
           # Use ``self.assertFilterErrors`` to check the errors from filtering
           # an invalid value.
           self.assertFilterErrors(
               # If this is the input...
               'Hello, world!',
               # ... these are the expected filter errors.
               [f.Type.CODE_WRONG_TYPE],
           )


Registering Your Filters (Optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once you've packaged up your filters, you can register them with the Extensions
framework to add them to the (nearly) top-level ``filters.ext`` namespace.

This is an optional step; it may make your filters easier to use, though there
are some trade-offs.

See :doc:`/extensions` for more information.
