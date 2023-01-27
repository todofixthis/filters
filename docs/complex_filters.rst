Complex Filters
===============
Complex filters are filters that work in tandem with other filters, allowing you
to create complex data schemas and transformation pipelines.

FilterMapper
------------
Applies filters to an incoming mapping (e.g., ``dict``).

When initialising the filter, you must provide a dict that tells the
FilterMapper which filters to apply to each key in the incoming dict.

.. code-block:: python

   import filters as f

   filter_ = f.FilterMapper({
       'id':      f.Int,
       'subject': f.Unicode | f.NotEmpty | f.MaxLength(16),
   })

   runner = f.FilterRunner(filter_, {
       'id':      '42',
       'subject': 'Hello, world!',
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'id':      42,
       'subject': 'Hello, world!',
   }

   runner = f.FilterRunner(filter_, {
       'id':      [3, 14],
       'subject': 'Did you know that Albert Einstein was born on Pi Day?',
   })
   assert runner.is_valid() is False

By default, the FilterMapper will ignore missing/unexpected keys, but you can
configure this via the filter initialiser as well.

.. code-block:: python

   import filters as f

   filter_ = f.FilterMapper(
       {
           'id':      f.Int,
           'subject': f.Unicode | f.NotEmpty | f.MaxLength(16),
       },

       # Only allow keys that we are expecting.
       allow_extra_keys = False,

       # All keys are required.
       allow_missing_keys = False,
   )

   runner = f.FilterRunner(filter_, {
       'id':      '42',
       'subject': 'Hello, world!',
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'id':      42,
       'subject': 'Hello, world!',
   }

   runner = f.FilterRunner(filter_, {
       'id':          -1,
       'attachment':  'virus.exe',
   })
   assert runner.is_valid() is False

You can also provide explicit key names for allowed extra/missing parameters:

.. code-block:: python

   import filters as f

   filter_ = f.FilterMapper(
       {
           'id':      f.Int,
           'subject': f.Unicode | f.NotEmpty | f.MaxLength(16),
       },

       # Ignore `attachment` if present,
       # but other extra keys are invalid.
       allow_extra_keys = {'attachment'},

       # Only `subject` is optional.
       allow_missing_keys = {'subject'},
   )

   runner = f.FilterRunner(filter_, {
       'id': 42,
       'attachment': 'signature.asc',
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'id': 42,
       'subject': None,
       'attachment': 'signature.asc',
   }

   runner = f.FilterRunner(filter_, {
       'from':        'admin@facebook.com',
       'attachment':  'virus.exe',
   })
   assert runner.is_valid() is False

.. tip::

   This filter is often chained with :py:class:`filters.JsonDecode`, when
   parsing a JSON object into a ``dict``.

FilterRepeater
--------------
Applies filters to every value in an incoming iterable (e.g., ``list``).

Invalid values in the iterable will be replaced with ``None``.

.. code-block:: python

   import filters as f

   filter_ = f.FilterRepeater(f.Int | f.Required)

   runner = f.FilterRunner(filter_, ['42', 86.0, 99])
   assert runner.is_valid() is True
   assert runner.cleaned_data == [42, 86, 99]

   runner = f.FilterRunner(
       filter_,
       ['42', 98.6, 'not even close', 99, {12, 34}, None],
   )
   assert runner.is_valid() is False
   assert runner.cleaned_data ==\
       [42, None, None, 99, None, None]

``FilterRepeater`` can also process mappings (e.g., ``dict``); it will apply the
filters to every value in the mapping, preserving the keys.

Invalid values in the mapping will be replaced with ``None``.

.. code-block:: python

   import filters as f

   filter_ = f.FilterRepeater(f.Int | f.Required)

   runner = f.FilterRunner(filter_, {
       'alpha':   '42',
       'bravo':   86.0,
       'charlie': 99,
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'alpha':   42,
       'bravo':   86,
       'charlie': 99,
   }

   runner = f.FilterRunner(filter_, {
       'alpha':   None,
       'bravo':   86.1,
       'charlie': 99
   })
   assert runner.is_valid() is False
   assert runner.cleaned_data == {
       'alpha':   None,
       'bravo':   None,
       'charlie': 99,
   }

FilterSwitch
------------
Conditionally invokes a filter based on the output of a function.

``FilterSwitch`` takes 2-3 parameters:

* ``getter: Callable[[Any], Hashable]`` - a function that extracts the
  comparison value from the incoming value.  Whatever this function returns
  will be matched against the keys in ``cases``.
* ``cases: Mapping[Hashable, FilterCompatible]`` - a mapping of valid comparison
  values and their corresponding filters.
* ``default: Optional[FilterCompatible]`` - if specified, this is the filter
  that will be used if the comparison value doesn't match any cases.  If not
  specified, then the incoming value will be considered invalid if the
  comparison value doesn't match any cases.

Example of a ``FilterSwitch`` that selects the correct filter to use based upon
the incoming value's ``name`` item:

.. code-block:: python

   import filters as f
   from operator import itemgetter

   filter_ = f.FilterSwitch(
       # This function will extract the comparison value.
       getter=itemgetter('name'),

       # These are the cases that the comparison value might
       # match.
       cases={
           'price': f.FilterMapper({'value': f.Int | f.Min(0)}),
           'colour': f.FilterMapper({'value': f.Choice({'r', 'g', 'b'})}),
           # etc.
       },

       # This is the filter that will be used if none of the cases match.
       default=f.FilterMapper({'value': f.Unicode}),
   )

   # Applies the 'price' filter:
   runner = f.FilterRunner(filter_, {'name': 'price', 'value': '995'})
   assert runner.is_valid() is True
   assert runner.cleaned_data == {'name': 'price', 'value': 995}

   # Applies the 'colour' filter:
   runner = f.FilterRunner(filter_, {'name': 'colour', 'value': 'b'})
   assert runner.is_valid() is True
   assert runner.cleaned_data == {'name': 'colour', 'value': 'b'}

   # Applies the default filter:
   runner = f.FilterRunner(filter_, {'name': 'size', 'value': 42})
   assert runner.is_valid() is True
   assert runner.cleaned_data == {'name': 'size', 'value': '42'}

.. _filterception:

Filterception
^^^^^^^^^^^^^
Just like any other filter, complex filters can be chained with other filters.

For example, to decode a JSON string that describes an address book card, the
filter chain might look like this:

.. code-block:: python

   import filters as f

   filter_ =\
      f.Unicode | f.Required | f.JsonDecode | f.Type(dict) | f.FilterMapper(
          {
              'name': f.Unicode | f.Strip | f.Required,
              'type': f.Unicode | f.Strip | f.Optional('person') |
                  f.Choice({'business', 'person'}),

              # Each person may have multiple phone numbers, which must be
              # structured a particular way.
              'phone_numbers': f.Array | f.FilterRepeater(
                  f.FilterMapper(
                      {
                          'label': f.Unicode | f.Required,
                          'country_code': f.Int,
                          'number': f.Int | f.Required,
                      },
                      allow_extra_keys=False,
                      allow_missing_keys=('country_code',),
                  ),
              ),
          },
          allow_extra_keys=False,
          allow_missing_keys=False,
      )

   runner = f.FilterRunner(
       filter_,
       '{"name": "Ghostbusters", "type": "business", "phone_numbers": '
       '[{"label": "office", "number": 5552368}]}'
   )
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'name': 'Ghostbusters',
       'type': 'business',
       'phone_numbers': [
           {'label': 'office', 'country_code': None, 'number': 5552368},
       ],
   }
