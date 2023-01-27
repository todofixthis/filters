Official Extensions
===================
The following filters are provided by the
:doc:`Extensions framework </extensions>` as official add-ons to the Filters
library.

Note that extension filters are located in a different namespace; use
``filters.ext`` to access them instead of ``filters``.  For example:

.. code-block:: python

   import filters as f

   # Standard filter
   f.Unicode().apply('foo')

   # Extension filter - note `f.ext`.
   f.ext.Country().apply('pe')

Django Filters
--------------
Adds filters for Django-specific features.  To install this extension::

   pip install filters[django]

Model
^^^^^
Attempts to find a database record that matches the incoming value.

The filter initialiser accepts a few arguments:

* ``model`` (required) The Django model that will be queried.
* ``field`` (optional) The name of the field that will be matched against.  If
  not provided, the default is ``pk``.

You may also provide "predicates" to the initialiser that will allow you to
further filter/customise the query as desired.

Here's an example:

.. code-block:: python

   import filters as f

   filter_ = f.ext.Model(
     # Find a Post record with a ``slug`` that matches the input.
     model = Post,
     field = 'slug',

     # Add predicates to the query.
     filter={'published': True},
     exclude={'comments__isnull': True'},
     select_related=('author', 'comments'),
   )

   runner = f.FilterRunner(filter_, 'introducing-filters-library')

Any method in ``QuerySet`` can be used as a predicate so long as that method
returns a ``QuerySet`` object (e.g., ``filter`` and ``select_related`` are
valid predicates, but ``count`` and ``update`` are not).

Refer to the `QuerySet API`_ for more information.

ISO Filters
-----------
Adds filters for interpreting standard codes and identifiers.  To install this
extension::

   pip install filters[iso]

Country
^^^^^^^
Interprets the incoming value as an
`ISO 3166-1 alpha-2 or alpha-3 country code`_.

The resulting value is a :py:class:`iso3166.Country` object (provided by the
`iso3166 library`_).

.. code-block:: python

   import filters as f
   from iso3166 import Country

   runner = f.FilterRunner(f.ext.Country, 'nz')
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Country) is True
   assert runner.cleaned_data.name == 'New Zealand'
   assert runner.cleaned_data.alpha2 == 'NZ'
   assert runner.cleaned_data.alpha3 == 'NZL'
   assert runner.cleaned_data.numeric == '554'
   assert runner.cleaned_data.apolitical_name == 'New Zealand'

   runner = f.FilterRunner(f.ext.Country, 'nzl')
   assert runner.is_valid() is True
   assert runner.cleaned_data.name == 'New Zealand'

   runner = f.FilterRunner(f.ext.Country, 'xxxx')
   assert runner.is_valid() is False

   # Only ISO codes are accepted.
   runner = f.FilterRunner(f.ext.Country, 'New Zealand')
   assert runner.is_valid() is False

Currency
^^^^^^^^
Interprets the incoming value as an `ISO 4217 currency code`_.

The resulting value is a :py:class:`moneyed.Currency` object (provided by
the `py-moneyed library`_).

.. code-block:: python

   import filters as f
   from moneyed import Currency

   runner = f.FilterRunner(f.ext.Currency, 'nzd')
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Currency) is True
   assert runner.cleaned_data.name == 'New Zealand Dollar'

   runner = f.FilterRunner(f.ext.Currency, 'xxxx')
   assert runner.is_valid() is False

   # Only ISO codes are accepted.
   runner = f.FilterRunner(f.ext.Currency, 'New Zealand Dollar')
   assert runner.is_valid() is False

Locale
^^^^^^
Interprets the incoming value as an `IETF Language Tag`_ (also known as BCP
47).

The resulting value is a :py:class:`language_tags.Tag.Tag` object (provided
by the `language_tags library`_).

.. code-block:: python

   import filters as f
   from language_tags.Tag import Tag

   runner = f.FilterRunner(f.ext.Locale, 'en-nz')
   assert runner.is_valid() is True
   assert isinstance(runner.cleaned_data, Tag) is True
   assert runner.cleaned_data.format == 'en-NZ'

   runner = f.FilterRunner(f.ext.Locale, 'xx-XX')
   assert runner.is_valid() is False

   # Only ISO codes are accepted.
   runner = f.FilterRunner(f.ext.Locale, 'English')
   assert runner.is_valid() is False

.. _IETF Language Tag: https://en.wikipedia.org/wiki/IETF_language_tag
.. _ISO 3166-1 alpha-2 or alpha-3 country code: https://en.wikipedia.org/wiki/ISO_3166-1
.. _ISO 4217 currency code: https://en.wikipedia.org/wiki/ISO_4217
.. _iso3166 library: https://pypi.python.org/pypi/iso3166
.. _py-moneyed library: https://pypi.python.org/pypi/py-moneyed
.. _QuerySet API: https://docs.djangoproject.com/en/4.1/ref/models/querysets/#methods-that-return-new-querysets
.. _language_tags library: https://pypi.python.org/pypi/language-tags
