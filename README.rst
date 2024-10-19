.. image:: https://github.com/todofixthis/filters/actions/workflows/build.yml/badge.svg
   :target: https://github.com/todofixthis/filters/actions/workflows/build.yml
.. image:: https://readthedocs.org/projects/filters/badge/?version=latest
   :target: http://filters.readthedocs.io/

Filters
=======
The Filters library provides an easy and readable way to create complex
data validation and processing pipelines, including:

- Validating complex JSON structures in API requests or config files.
- Parsing timestamps and converting to UTC.
- Converting Unicode strings to NFC, normalizing line endings and removing
  unprintable characters.
- Decoding Base64, including URL-safe variants.

And much more!

The output from one filter can be piped into the input of another, enabling you
to chain filters together to quickly and easily create complex data schemas and
pipelines.


Examples
--------
Validate a latitude position and round to manageable precision:

.. code-block:: python

   (
       f.Required |
       f.Decimal |
       f.Min(Decimal(-90)) |
       f.Max(Decimal(90)) |
       f.Round(to_nearest='0.000001')
   ).apply('-12.0431842')

Parse an incoming value as a datetime, convert to UTC and strip tzinfo:

.. code-block:: python

   f.Datetime(naive=True).apply('2015-04-08T15:11:22-05:00')

Convert every value in an iterable (e.g., list) to unicode and strip
leading/trailing whitespace.
This also applies `Unicode normalization`_, strips unprintable characters and
normalizes line endings automatically.

.. code-block:: python

   f.FilterRepeater(f.Unicode | f.Strip).apply([
       b'\xe2\x99\xaa ',
       b'\xe2\x94\x8f(\xc2\xb0.\xc2\xb0)\xe2\x94\x9b ',
       b'\xe2\x94\x97(\xc2\xb0.\xc2\xb0)\xe2\x94\x93 ',
       b'\xe2\x99\xaa ',
   ])

Parse a JSON string and check that it has correct structure:

.. code-block:: python

   (
       f.JsonDecode |
       f.FilterMapper(
           {
               'birthday':  f.Date,
               'gender':    f.CaseFold | f.Choice(choices={'f', 'm', 'n'}),

               'utcOffset':
                   f.Decimal |
                   f.Min(Decimal('-15')) |
                   f.Max(Decimal('+15')) |
                   f.Round(to_nearest='0.25'),
           },

           allow_extra_keys   = False,
           allow_missing_keys = False,
       )
   ).apply('{"birthday":"1879-03-14", "gender":"M", "utcOffset":"1"}')


Requirements
------------
Filters is known to be compatible with the following Python versions:

- 3.13
- 3.12
- 3.11

.. note::
   I'm only one person, so to keep from getting overwhelmed, I'm only committing
   to supporting the 3 most recent versions of Python.

Installation
------------
Install the latest stable version via pip::

    pip install phx-filters


.. important::
   Make sure to install `phx-filters`, **not** `filters`.  I created the latter
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

#. `Install poetry <https://python-poetry.org/docs/#installation>`_ (only needs to be
   done once).

#. Run the following command to install additional dependencies::

      poetry install --with=dev

#. Activate pre-commit hook::

      poetry run autohooks activate --mode=poetry

Running Unit Tests and Type Checker
-----------------------------------
Run the tests for all supported versions of Python using
`tox <https://tox.readthedocs.io/>`_::

   poetry run tox -p

.. note::

   The first time this runs, it will take awhile, as mypy needs to build up its cache.
   Subsequent runs should be much faster.

If you just want to run unit tests in the current virtualenv (using
`pytest <https://docs.pytest.org>`_)::

   poetry run pytest

If you just want to run type checking in the current virtualenv (using
`mypy <https://mypy.readthedocs.io>`_)::

   poetry run mypy src test

Documentation
-------------
To build the documentation locally:

#. Switch to the ``docs`` directory::

    cd docs

#. Build the documentation::

    make html

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

    poetry build

#. The build artefacts will be located in the ``dist`` directory at the top level of the
   project.

2. Upload to PyPI
~~~~~~~~~~~~~~~~~
#. `Create a PyPI API token <https://pypi.org/manage/account/token/>`_ (you only have to
   do this once).
#. Increment the version number in ``pyproject.toml``.
#. Upload build artefacts to PyPI::

    poetry publish

3. Create GitHub Release
~~~~~~~~~~~~~~~~~~~~~~~~
#. Create a tag and push to GitHub::

      git tag <version>
      git push <version>

   ``<version>`` must match the updated version number in ``pyproject.toml``.

#. Go to the `Releases page for the repo`_.
#. Click ``Draft a new release``.
#. Select the tag that you created in step 1.
#. Specify the title of the release (e.g., ``{{ cookiecutter.project_name }} v1.2.3``).
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
