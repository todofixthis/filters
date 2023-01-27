Getting Started
===============
The fastest way to get started with filters is to use the ``FilterRunner``
class.  This class provides an interface very similar to a Django form.

.. code-block:: python

   import datetime
   import filters as f

   # Incoming data.
   data = u'1879-03-14'

   # Initialize the FilterRunner.
   runner = f.FilterRunner(f.Date, data)

   if runner.is_valid():
     # Input is valid; do something with the filtered data.
     cleaned_data = runner.cleaned_data
     assert cleaned_data == datetime.date(1879, 3, 14)

   else:
     # Input is not valid; display error message(s) for each incoming value.
     for key, errors in runner.errors.items():
       print('{key}:'.format(key=key))
       for error in errors:
         print('  - ({error[code]}) {error[message]}'.format(error=error))

``FilterRunner`` provides a few key attributes to make it easy to apply filters:

* ``is_valid()``:  Returns whether the value is valid.
* ``cleaned_data``:  If the value is valid, this property holds the filtered
  value(s).
* ``errors``:  If the value is not valid, this property holds the validation
  errors.

Chaining Filters
================
The filters library conforms to the unix philosophy of,
"`Do One Thing, and Do It Well`_".

Each filter provides a specific transformation and/or validation feature.  This
alone can be useful, but the real power of the filters library lies in its
ability to "chain" filters together.

By using the ``|`` operator, you can "pipe" the output of one filter directly
into the input of another.  This allows you to quickly and easily create complex
data pipelines.

Here's an example:

.. code-block:: python

   import filters as f

   # Convert to unicode, strip leading and trailing whitespace, reject empty
   # string, fold case and split into words.
   filter_ = f.Unicode | f.Strip | f.NotEmpty | f.CaseFold | f.Split(r'\W+')

   runner = f.FilterRunner(filter_, '   Остерегайтесь Дуга   ')
   assert runner.is_valid() is True
   assert runner.cleaned_data == ['остерегайтесь', 'дуга']

   runner = f.FilterRunner(filter_, '\r\n')
   assert runner.is_valid() is False

.. _none-is-special:

Much Ado About None
===================
``None`` is a special value to the Filters library.  By default, it passes every
filter, no matter how strictly configured.

For example:

.. code-block:: python

   import filters as f

   # Convert to unicode, strip leading and trailing whitespace, reject empty
   # string, fold case and split into words.
   filter_ = f.Unicode | f.Strip | f.NotEmpty | f.CaseFold | f.Split(r'\W+')

   runner = f.FilterRunner(filter_, None)
   assert runner.is_valid() is True
   assert runner.cleaned_data is None

If you want to reject ``None``, add the ``Required`` filter to your chain:

.. code-block:: python

   import filters as f

   # Note that we replace ``NotEmpty`` with ``Required``.
   filter_ = f.Unicode | f.Strip | f.Required | f.CaseFold | f.Split(r'\W+')

   runner = f.FilterRunner(filter_, None)

   assert runner.is_valid() is False

Next Steps
==========
See :doc:`/simple_filters` for a list of all the filters that come bundled with
the Filters library (and its official extensions).

Be sure to pay special attention to :doc:`/complex_filters`, which lists filters
designed exclusively to work with other filters, allowing you to construct
powerful data schemas and transformation pipelines.

There are also several :doc:`/extension_filters` that you can install, to add
even more filters to work with.

Once you've gotten the hang of working with filters, you'll want to
:doc:`write your own filters and macros </writing_filters>`, so that you can
reduce code duplication and inject your own functionality into filter pipelines.

.. _Do One Thing, and Do It Well: https://en.wikipedia.org/wiki/Unix_philosophy#Do_One_Thing_and_Do_It_Well
