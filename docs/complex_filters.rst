Complex Filters
===============
Complex filters are filters that work in tandem with other filters, allowing you
to create complex data schemas and transformation pipelines.

FilterMapper
------------
Applies filters to an incoming mapping (e.g., ``dict``).

When initialising the FilterMapper, provide a dict that assigns a filter chain
to apply to each item.

When the FilterMapper gets applied to a mapping, the filter chain for each key
is applied to the corresponding value in the mapping.  A new mapping is returned
containing the filtered values.

Invalid values in the result will be replaced with ``None`` (with a few
exceptions, such as :py:class:`filters.MaxBytes` which can be configured to
return a truncated version of the incoming string instead of ``None``).

.. code-block:: python

   import filters as f

   filter_ = f.FilterMapper({
       'id':      f.Int,
       'subject': f.Unicode | f.NotEmpty | f.MaxLength(16),
   })

   # Incoming value is 100% valid.
   runner = f.FilterRunner(filter_, {
       'id':      '42',
       'subject': 'Hello, world!',
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'id':      42,
       'subject': 'Hello, world!',
   }

   # Incoming value contains invalid items.
   runner = f.FilterRunner(filter_, {
       'id':      '42',
       'subject': 'Did you know that Albert Einstein was born on Pi Day?',
   })
   assert runner.is_valid() is False
   assert runner.cleaned_data == {
       'id':      42,
       'subject': None,
   }

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

   # Incoming value is valid.
   runner = f.FilterRunner(filter_, {
       'id':      '42',
       'subject': 'Hello, world!',
   })
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'id':      42,
       'subject': 'Hello, world!',
   }

   # Incoming value is missing required key and contains unexpected extra key.
   runner = f.FilterRunner(filter_, {
       'id':          -1,
       'attachment':  'virus.exe',
   })
   assert runner.is_valid() is False
   assert runner.cleaned_data == {
       'id':      -1,
       'subject': None,
   }

You can also provide explicit key names for allowed extra/missing parameters:

.. code-block:: python

   import filters as f

   filter_ = f.FilterMapper(
       {
           'id':      f.Int,
           'subject': f.Unicode | f.NotEmpty | f.MaxLength(16),
       },

       # Ignore `attachment` if present; any other extra keys are invalid.
       allow_extra_keys = {'attachment'},

       # Only `subject` is optional.
       allow_missing_keys = {'subject'},
   )

   # Incoming value is valid.
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

   # Incoming value is missing required key and contains unexpected extra key.
   runner = f.FilterRunner(filter_, {
       'from':        'admin@facebook.com',
       'attachment':  'virus.exe',
   })
   assert runner.is_valid() is False
   assert runner.cleaned_data == {
       'id':         None,
       'subject':    None,
       'attachment': 'virus.exe'
   }

.. tip::

   This filter is often chained with :py:class:`filters.JsonDecode`, when
   parsing a JSON object into a ``dict``.

FilterRepeater
--------------
Applies a filter chain to every value in an incoming iterable (e.g., ``list``)
or mapping (e.g., ``dict``).

When initialising the FilterRepeater, provide a filter chain to apply to each
item.

When the FilterRepeater gets applied to an iterable or mapping, the filter chain
gets applied to each value, and a new iterable or mapping of the same type is
returned which contains the filtered values.

Invalid values in the result will be replaced with ``None`` (with a few
exceptions, such as :py:class:`filters.MaxBytes` which can be configured to
return a truncated version of the incoming string instead of ``None``).

.. code-block:: python

   import filters as f

   filter_ = f.FilterRepeater(f.Int | f.Required)

   # Incoming value is 100% valid.
   runner = f.FilterRunner(filter_, ['42', 86.0, 99])
   assert runner.is_valid() is True
   assert runner.cleaned_data == [42, 86, 99]

   # Incoming value contains invalid values.
   runner = f.FilterRunner(
       filter_,
       ['42', 98.6, 'not even close', 99, {12, 34}, None],
   )
   assert runner.is_valid() is False
   assert runner.cleaned_data == [42, None, None, 99, None, None]

``FilterRepeater`` can also process mappings (e.g., ``dict``); it will apply the
filters to every value in the mapping, preserving the keys.

.. code-block:: python

   import filters as f

   filter_ = f.FilterRepeater(f.Int | f.Required)

   # Incoming value is 100% valid.
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

   # Incoming value contains invalid values.
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

.. note::

   Note how this differs from :py:class:`filters.FilterMapper` —
   ``FilterRepeater`` will apply the **same** filter chain to each item in the
   mapping, whereas ``FilterMapper`` allows you to specify a **different**
   filter chain to apply to each item based on its key.

FilterSwitch
------------
Conditionally invokes a filter based on the output of a function.

``FilterSwitch`` takes 2-3 parameters:

* ``getter: Callable[[Any], Hashable]`` - a function that extracts the
  comparison value from the incoming value.  Whatever this function returns
  will be matched against the keys in ``cases``.
* ``cases: Mapping[Hashable, FilterCompatible]`` - a mapping of possible return
  values from ``getter`` and the corresponding filter chains.
* ``default: Optional[FilterCompatible]`` - Filter chain that will be used if
  the return value from ``getter`` doesn't match any keys in ``cases``.

When a ``FilterSwitch`` is applied to an incoming ``value``:

1. The ``getter`` will be called and ``value`` will be passed in.
2. The return value from ``getter`` will be compared against the keys in
   ``cases``:

   * If a match is found, the corresponding filter chain will be applied to
     ``value``.

     .. important::

        Note that the actual ``value`` gets passed to the filter chain, **not**
        the result from calling ``getter``; the latter is **only** used to
        figure out which filter chain to use!

   * If no match is found, the ``FilterSwitch`` will check to see if it has a
     ``default`` filter chain:

     * If there is a ``default`` filter chain, that chain gets applied to the
       ``value``.
     * If not, then the incoming value is invalid.

Example of a ``FilterSwitch`` that selects the correct filter to use based upon
the incoming value's ``name`` item:

.. code-block:: python

   import filters as f
   from operator import itemgetter

   filter_ = f.FilterSwitch(
       # This function will extract the comparison value.
       getter=itemgetter('name'),

       # These are the cases that the comparison value might match.
       cases={
           # If ``value.name == 'price'`` use this filter:
           'price': f.FilterMapper({'value': f.Int | f.Min(0)}),

           # If ``value.name == 'colour'`` use this filter instead:
           'colour': f.FilterMapper({'value': f.Choice({'r', 'g', 'b'})}),
       },

       # (optional) If none of the above cases match, use this filter instead.
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

.. important::

   Note in the above example that the entire incoming dict gets passed to the
   corresponding filter chain, **not** the result of calling
   ``itemgetter('name')``!

.. _filterception:

Filterception
=============
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
                          'number': f.Unicode | f.Required,
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
       '[{"label": "office", "number": "555-2368"}]}'
   )
   assert runner.is_valid() is True
   assert runner.cleaned_data == {
       'name': 'Ghostbusters',
       'type': 'business',
       'phone_numbers': [
           {'label': 'office', 'country_code': None, 'number': '555-2368'},
       ],
   }
