Writing Your Own Filters
========================
Although the Filters library comes with
:doc:`lots of built-in filters </simple_filters>`, oftentimes it is useful to
be able to write your own.

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
To help you unit test your custom filters, the Filters library provides a helper
class called :py:class:`filters.test.BaseFilterTestCase`.

This class defines two methods that you can use to test your filter:

* ``assertFilterPasses``: Given an input value, asserts that the filter returns
  an expected value when applied.
* ``assertFilterErrors``: Given an input value, asserts that the filter
  generates the expected filter error messages when applied.

Here's a starter test case for ``Pkcs7Pad``:

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
