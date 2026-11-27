Getting Started
===============
The fastest way to get started with filters is to use the ``FilterRunner``
class.  This class provides an interface very similar to a Django form.

.. code-block:: python

   import datetime
   import filters as f

   # Incoming data.
   data = u'1879-03-14'

   # Initialise the FilterRunner.
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

Reusing FilterRunners
---------------------
If you want to run the same set of filters on different values, you can create
a single ``FilterRunner`` instance and call its ``apply()`` method:

.. code-block:: python

   import filters as f

   runner = f.FilterRunner(f.Choice({'foo', 'bar', 'baz', 'luhrmann'}))

   input_1 = 'foo'
   input_2 = 'foobie'

   runner.apply(input_1)
   assert runner.is_valid() is True
   assert runner.cleaned_data == 'foo'

   runner.apply(input_2)
   assert runner.is_valid() is False
   assert runner.cleaned_data is None

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

Using Filters From Several Threads
==================================
A filter keeps the state of the run in progress on the filter instance. That
is fine for one thread, however many times it reuses the instance. It matters
where several threads validate at the same time, as most web frameworks do
with synchronous code.

.. caution::

   **Two threads must not apply the same filter instance at the same time**

   Two threads that share an instance can swap errors: one run accepts an
   invalid value, and the other rejects a valid one.

Filters share an instance more often than it looks:

.. code-block:: python

   import filters as f

   Text = f.Unicode | f.Strip

   # These two chains hold the same ``Unicode`` and ``Strip`` instances.
   title = Text | f.MaxLength(50)
   body = Text | f.MaxLength(2000)

Every :py:class:`filters.FilterMapper` or :py:class:`filters.FilterRepeater`
that ``Text`` is nested in holds those two instances as well.

Where threads validate at the same time, do one of these:

* Build the filters inside the function that uses them, so each call has its
  own. No filter instance may come from outside that function: not a
  module-level chain, and not a child filter stored on a class.
* Hold one lock around every run in the process. A lock for each chain is not
  enough, because two chains can share filters. A
  :py:class:`filters.FilterRunner` runs when you first read ``is_valid()``,
  ``cleaned_data`` or ``errors``, not when you create it, so hold the lock
  across that read. Use a :py:class:`threading.RLock` if any of your filters
  starts a run of its own.

``phx-filters-pydantic`` locks each ``FilterField`` on its own, which is a lock
for each chain. Two fields built from the same filters, such as ``Text`` above,
still need one of the two measures.

This is tracked in
`issue #175 <https://github.com/todofixthis/filters/issues/175>`_.

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
the Filters library.

Be sure to pay special attention to :doc:`/complex_filters`, which lists filters
designed exclusively to work with other filters, allowing you to construct
powerful data schemas and transformation pipelines.

There are also several :doc:`/extension_filters` that you can install, to add
even more filters to work with.

Once you've gotten the hang of working with filters, you'll want to
:doc:`write your own filters and macros </writing_filters>`, so that you can
reduce code duplication and inject your own functionality into filter pipelines.

.. _Do One Thing, and Do It Well: https://en.wikipedia.org/wiki/Unix_philosophy#Do_One_Thing_and_Do_It_Well
