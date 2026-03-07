.. image:: https://github.com/todofixthis/filters/actions/workflows/build.yml/badge.svg
   :target: https://github.com/todofixthis/filters/actions/workflows/build.yml
.. image:: https://readthedocs.org/projects/filters/badge/?version=latest
   :target: https://filters.readthedocs.io/

Filters
=======
The Filters library provides an easy and readable way to create complex
data validation and processing pipelines, including:

- Validating complex JSON structures in API requests or config files.
- Parsing timestamps and converting to UTC.
- Converting Unicode strings to NFC, normalising line endings and removing
  unprintable characters.
- Decoding Base64, including URL-safe variants.

And much more!

The output from one filter can be piped into the input of another, enabling you
to chain filters together to quickly and easily create complex data schemas and
pipelines.


Philosophy
----------
Filters applies the UNIX philosophy to data validation: **do one thing well,
and compose small tools together**.

Each filter performs a single, focused task. Chain them using the ``|`` operator
to build sophisticated validation pipelines that are easy to read and maintain.

**Type-safe**: Full type hint support for IDE autocomplete and static analysis.

**Opinionated**: Makes deliberate choices to handle common issues automatically
(Unicode normalisation, UTC conversion, etc.) so you write less boilerplate.


Quick Start
-----------
Install via pip::

    pip install phx-filters

Create a validation schema:

.. code-block:: python

   import filters as f
   from decimal import Decimal

   # Define your schema
   schema = f.FilterRunner(
       f.FilterMapper({
           "lat": f.Required | f.Decimal | f.Min(Decimal(-90)) | f.Max(Decimal(90)),
           "lon": f.Required | f.Decimal | f.Min(Decimal(-180)) | f.Max(Decimal(180)),
           "name": f.Required | f.Unicode | f.Strip,
       })
   )

   # Validate data
   result = schema.apply({"lat": "42.36", "lon": "-71.06", "name": "  Boston  "})

   if result.is_valid():
       clean_data = result.value
       # clean_data = {
       #     "lat": Decimal("42.36"),
       #     "lon": Decimal("-71.06"),
       #     "name": "Boston"
       # }
   else:
       errors = result.error_messages
       # errors = {"lat": ["Decimal value is too small (minimum is -90)."]}

``FilterRunner`` provides a familiar interface similar to Django forms, making
it easy to integrate into web applications.


Examples
--------

Validate API Request Data
~~~~~~~~~~~~~~~~~~~~~~~~~~
When building APIs, you need to validate request payloads and handle errors
gracefully. FilterRunner makes this straightforward:

.. code-block:: python

   from decimal import Decimal
   import filters as f

   # Define validation for a user registration endpoint
   user_schema = f.FilterRunner(
       f.FilterMapper(
           {
               "email": f.Required | f.Unicode | f.Strip | f.MaxLength(254),
               "age": f.Required | f.Int | f.Min(13) | f.Max(120),
               "timezone": f.Decimal | f.Min(Decimal("-15")) | f.Max(Decimal("15")),
           },
           allow_extra_keys=False,
       )
   )

   # Validate incoming data
   result = user_schema.apply(request_data)

   if result.is_valid():
       # Save to database
       user = User.create(**result.value)
   else:
       # Return validation errors to client
       return {"errors": result.error_messages}, 400


Parse Complex JSON Structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Filters excels at validating nested data structures with complex constraints:

.. code-block:: python

   schema = f.FilterRunner(
       f.JsonDecode |
       f.FilterMapper(
           {
               "birthday": f.Date,
               "gender": f.CaseFold | f.Choice(choices={"f", "m", "n"}),
               "utcOffset": (
                   f.Decimal |
                   f.Min(Decimal("-15")) |
                   f.Max(Decimal("15")) |
                   f.Round(to_nearest="0.25")
               ),
           },
           allow_extra_keys=False,
           allow_missing_keys=False,
       )
   )

   result = schema.apply('{"birthday":"1879-03-14", "gender":"M", "utcOffset":"1"}')


Process Lists of Data
~~~~~~~~~~~~~~~~~~~~~~
Use ``FilterRepeater`` to apply validation to every item in a collection:

.. code-block:: python

   # Clean a list of user-generated strings
   schema = f.FilterRunner(
       f.FilterRepeater(f.Unicode | f.Strip | f.MaxLength(100))
   )

   result = schema.apply([
       "  some text  ",
       b"\xe2\x99\xaa unicode bytes ",
       "another string",
   ])

For more examples and detailed documentation, visit https://filters.readthedocs.io/


Features
--------
- **Composable**: Chain filters using the ``|`` operator
- **Type-safe**: Full type hint support for IDE autocomplete and mypy
- **Familiar API**: ``FilterRunner`` provides Django-form-like interface
- **Extensible**: Create custom filters by extending ``BaseFilter``
- **Battle-tested**: Used in production applications for years
- **Well-documented**: Comprehensive docs at https://filters.readthedocs.io/


Requirements
------------
Filters is known to be compatible with the following Python versions:

- 3.14
- 3.13
- 3.12

.. note::
   I'm only one person, so to keep from getting overwhelmed, I'm only committing
   to supporting the 3 most recent versions of Python.

Installation
------------
Install the latest stable version via pip::

    pip install phx-filters


.. important::
   Make sure to install ``phx-filters``, **not** ``filters``.  I created the latter
   at a previous job years ago, and after I left they never touched that project
   again and stopped responding to my emails — so in the end I had to fork it 🤷

Extensions
~~~~~~~~~~
The following extensions are available:

- `Django Filters`_: Adds filters designed to work with Django applications.
  To install::

      pip install phx-filters[django]

- `ISO Filters`_: Adds filters for interpreting standard codes and identifiers.
  To install::

      pip install phx-filters[iso]

.. tip::
   To install multiple extensions, separate them with commas, e.g.::

      pip install phx-filters[django,iso]

Maintainers
-----------
To install the distribution for local development, some additional setup is required:

#. `Install uv <https://docs.astral.sh/uv/getting-started/installation/>`_ (only needs
   to be done once).

#. Run the following command to install additional dependencies::

      uv sync --group=dev

#. Activate pre-commit hook::

      uv run autohooks activate --mode=pythonpath

Running Unit Tests and Type Checker
-----------------------------------
Run the tests for all supported versions of Python using
`tox <https://tox.readthedocs.io/>`_::

   uv run tox -p

.. note::

   The first time this runs, it will take awhile, as mypy needs to build up its cache.
   Subsequent runs should be much faster.

If you just want to run unit tests in the current virtualenv (using
`pytest <https://docs.pytest.org>`_)::

   uv run pytest

If you just want to run type checking in the current virtualenv (using
`mypy <https://mypy.readthedocs.io>`_)::

   uv run mypyc src test

Documentation
-------------
To build the documentation locally:

#. Switch to the ``docs`` directory::

    cd docs

#. Build the documentation::

    uv run make html

Releases
--------
Steps to build releases are based on
`Packaging Python Projects Tutorial <https://packaging.python.org/en/latest/tutorials/packaging-projects/>`_.

.. important::

   Make sure to build releases off of the ``main`` branch, and check that all changes
   from ``develop`` have been merged before creating the release!

1. Build the Project
~~~~~~~~~~~~~~~~~~~~
#. Delete artefacts from previous builds, if applicable::

    rm dist/*

#. Run the build::

    uv build

#. The build artefacts will be located in the ``dist`` directory at the top level of the
   project.

2. Upload to PyPI
~~~~~~~~~~~~~~~~~
#. One-time setup — install keyring and store your PyPI token::

    uv tool install keyring
    uv tool update-shell
    keyring set https://upload.pypi.org/legacy/ __token__

#. Bump the version (updates ``pyproject.toml`` and re-locks ``uv.lock``)::

    uv version <version>

#. Upload build artefacts to PyPI::

    uv publish --username __token__

3. Create GitHub Release
~~~~~~~~~~~~~~~~~~~~~~~~
#. Create an annotated tag and push to GitHub::

      git tag -a <version> -m "Release <version>"
      git push origin <version>

   ``<version>`` must match the version set in step 2 above.

#. Go to the `Releases page for the repo`_.
#. Click ``Draft a new release``.
#. Select the tag that you created in step 1.
#. Specify the title of the release (e.g., ``Filters v1.2.3``).
#. Write a description for the release.  Make sure to include:
   - Credit for code contributed by community members.
   - Significant functionality that was added/changed/removed.
   - Any backwards-incompatible changes and/or migration instructions.
   - SHA256 hashes of the build artefacts.
#. GPG-sign the description for the release (ASCII-armoured).
#. Attach the build artefacts to the release.
#. Click ``Publish release``.

.. _Django Filters: https://pypi.python.org/pypi/phx-filters-django
.. _ISO Filters: https://pypi.python.org/pypi/phx-filters-iso
.. _Releases page for the repo: https://github.com/todofixthis/filters/releases
.. _Unicode normalization: https://en.wikipedia.org/wiki/Unicode_equivalence
