Upgrading to Filters v4
=======================

`Filters v4 <https://github.com/todofixthis/filters/releases/tag/4.0.0a1>`_ makes
every filter generic over its output type, so a type checker can follow a value
all the way through a chain. That part is free — your own filters need no
changes. But three changes can break code that worked in Filters v3, and one of
them fails silently.

.. note::

   This guide covers the v4 alpha. Runtime behaviour is settled; the typing
   surface may still shift before 4.0.0 final.

Installing the alpha
--------------------
Pre-release versions aren't selected by default, so ask for this one
explicitly::

    pip install --pre 'phx-filters==4.0.0a1'

Or, with `uv <https://docs.astral.sh/uv/>`_::

    uv add 'phx-filters==4.0.0a1'

If the alpha bites, going back is just as explicit::

    pip install 'phx-filters<4'

.. note::

   Filters v4 adds ``typing-extensions>=4.15.0`` as a runtime dependency. If you
   vendor your dependencies or install from a private mirror, add it before you
   upgrade.

.. note::

   The ``phx-filters[django]`` and ``phx-filters[iso]`` extras declare no upper
   bound on ``phx-filters``, so both install alongside v4 without a resolver
   conflict, and neither looks likely to trip the breaking changes below.
   Neither has been exercised against v4 in anger yet, though, so test in a
   throwaway environment before you rely on it.

At a Glance
-----------
Start with the change that gives you no warning at all:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Change
     - How it surfaces
     - How to find it
   * - :ref:`upgrade-v4-siblings`
     - **Nothing.** No exception, no warning — a check silently returns
       ``False`` and your code takes the other branch.
     - ``rg -U '(?s)(isinstance|issubclass)\(.{0,120}?\b(ByteString|Date|Datetime|Unicode)\b'``
   * - :ref:`upgrade-v4-none`
     - :py:class:`TypeError` when the chain is *built*. For chains defined at
       module scope, that's on import, so your test suite finds every one.
     - Don't search — ``| None`` matches every ``str | None`` annotation in
       your codebase. Let the :py:class:`TypeError` find them.
   * - :ref:`upgrade-v4-split`
     - ``FilterError`` on every input.
     - ``rg -U 'Split\([^)]*,'`` — a candidate list to eyeball; check each
       hit for a ``keys`` argument

.. _upgrade-v4-siblings:

ByteString and Date are no longer subclasses
--------------------------------------------
.. important::

   :py:class:`filters.ByteString` no longer subclasses
   :py:class:`filters.Unicode`, and :py:class:`filters.Date` no longer
   subclasses :py:class:`filters.Datetime`. Each pair is now two siblings
   sharing a private base class:

   .. code-block:: python

      >>> issubclass(f.ByteString, f.Unicode)
      False
      >>> isinstance(f.ByteString(), f.Unicode)
      False

**This is the one change nothing will tell you about.** There is no exception
and no warning: a check that used to be ``True`` is now ``False``, and whatever
branch depended on it quietly stops running. Search for ``ByteString`` and
``Date`` wherever you use ``isinstance()`` or ``issubclass()`` — both are
affected, so searching for only one of them will miss cases.

The subclass relationship was never meaningful — a
:py:class:`filters.ByteString` emits :py:class:`bytes` where a
:py:class:`filters.Unicode` emits :py:class:`str`, so it could not stand in for
its parent. Once each filter declared an output type, a type checker could see
the violation.

If you were testing for the concrete filter, name it directly:

.. code-block:: python

   # Unchanged, and now means what it says.
   isinstance(some_filter, f.ByteString)

If you were testing for "any decoder" or "any date-like filter", there is no
public replacement — the shared base classes are private. Test against the pair:

.. code-block:: python

   isinstance(some_filter, (f.Unicode, f.ByteString))
   isinstance(some_filter, (f.Datetime, f.Date))

.. note::

   Only the class hierarchy changed. Both filters accept the same input and
   produce the same output as they did in Filters v3, so code that simply *uses*
   them needs no changes.

.. _upgrade-v4-none:

Chaining with ``None``
----------------------
.. important::

   In Filters v3, ``some_filter | None`` silently did nothing. In Filters v4 it
   raises :py:class:`TypeError`::

      TypeError: None is not compatible with Int in a filter chain; use NoOp
      instead, or Optional[Int] in a type annotation.

The silent no-op hid a common typo, and it had no sensible type: a chain whose
next link might be absent can't be checked. Use :py:class:`filters.NoOp`
explicitly instead.

The :py:class:`TypeError` fires when the chain is *constructed*, not when it
runs, so a chain built at module scope raises on import.

Filters v3:

.. code-block:: python

   chain = f.Unicode | None | f.Strip

Filters v4:

.. code-block:: python

   chain = f.Unicode | f.NoOp() | f.Strip

This most often shows up when a chain is assembled from parts that may
legitimately be absent:

Filters v3:

.. code-block:: python

   def build_chain(extra=None):
       return f.Unicode | extra

Filters v4:

.. code-block:: python

   def build_chain(extra=None):
       return f.Unicode | (extra if extra is not None else f.NoOp())

.. note::

   Only the ``|`` operator is affected.
   :py:meth:`filters.BaseFilter.resolve_filter` and ``FilterCompatible`` still
   accept ``None``, so a filter that accepts ``None`` from its own caller keeps
   working.

   ``None`` on the *left* — ``None | f.Int()`` — raised :py:class:`TypeError` in
   Filters v3 as well, and is unchanged.

.. tip::

   The ``Optional`` named in the error message is :py:obj:`typing.Optional`,
   used in a type annotation — not the :py:class:`filters.Optional` filter.

.. _upgrade-v4-split:

Split with an empty ``keys``
----------------------------
.. important::

   ``f.Split(pattern, keys=[])`` — an empty ``keys``, not ``None`` — now rejects
   every input, including the empty string::

      FilterError: Value is too long (length must be < 0).

Filters v3 branched on whether ``keys`` was *truthy*, so an empty ``keys`` fell
through to the list branch and returned a list. Filters v4 branches on
``keys is not None``, which is what the documented behaviour always described:
an empty ``keys`` caps the split at zero items, and nothing fits.

If you were relying on the old behaviour, pass ``None`` — the default:

Filters v3:

.. code-block:: python

   >>> f.Split(":", keys=[]).apply("a:b")
   ['a', 'b']

Filters v4:

.. code-block:: python

   >>> f.Split(":").apply("a:b")
   ['a', 'b']

.. tip::

   This is most likely to bite where ``keys`` is computed rather than written
   out — ``keys=[k for k in fields if ...]`` that happens to select nothing. In
   Filters v3 that quietly returned a list; it now fails loudly, which is the
   point.

Type Parameters
---------------
Now for the good news 😺

Chains and :py:class:`filters.FilterRunner` infer real types instead of
:py:obj:`~typing.Any`:

.. code-block:: python

   import filters as f

   # Inferred as ``int``, not ``Any``.
   f.FilterRunner(f.Int()).cleaned_data

   # Inferred as ``str``.
   f.FilterRunner(f.Unicode | f.Strip | f.NotEmpty).cleaned_data

The library ships a ``py.typed`` marker, so you get this without installing a
separate stubs package.

**Your own filters need no changes.** The type parameter defaults to
:py:obj:`~typing.Any`, so a bare subclass keeps working exactly as before:

.. code-block:: python

   # Still valid; behaves as it did in Filters v3.
   class Pkcs7Pad(f.BaseFilter):
       ...

To opt into inference, declare what your filter emits:

.. code-block:: python

   # A chain ending in ``Pkcs7Pad`` now infers ``bytes``.
   class Pkcs7Pad(f.BaseFilter[bytes]):
       ...

.. tip::

   Some filters shouldn't declare a concrete output type — a validator that
   passes its input through unchanged, for example. See :doc:`writing_filters`
   for the base class to pick in each case.

Macros work differently. A :py:func:`filters.filter_macro` decorates a
*function*, so there is no base class to parameterise — annotate its return
type instead:

.. code-block:: python

   # mypy infers ``Any`` from this macro.
   @f.filter_macro
   def String():
       return f.Unicode | f.Strip

   # mypy infers ``str``.
   @f.filter_macro
   def String() -> f.BaseFilter[str]:
       return f.Unicode | f.Strip

.. note::

   pyright reads the function body and infers ``str`` either way; mypy reads
   only the annotation. Adding it costs nothing and satisfies both.

.. important::

   Assigning a chain of **bare classes** to a variable defeats inference under
   mypy, which reads ``Unicode | Strip`` as a :pep:`604` type alias rather than
   a chain:

   .. code-block:: python

      # mypy infers ``types.UnionType``, and the chain's output degrades to
      # ``Any``. There is no error — you just lose the type.
      chain = f.Unicode | f.Strip | f.NotEmpty

   Passing a chain straight into a filter, as in the examples above, is
   unaffected. Where you do want to name it, either annotate the variable or
   instantiate the first filter:

   .. code-block:: python

      chain: f.FilterChain[str] = f.Unicode | f.Strip | f.NotEmpty

      # Or, equivalently:
      chain = f.Unicode() | f.Strip | f.NotEmpty

   pyright infers ``FilterChain[str]`` in every one of these forms, and runtime
   behaviour is identical throughout.

While You're Here
-----------------
:py:class:`filters.FilterMapper` now accepts sequence input. Where every key in
``filter_map`` is a non-``bool`` :py:class:`int`, a :py:class:`list` or
:py:class:`tuple` is filtered by position and returned as a :py:class:`list`:

.. code-block:: python

   >>> runner = f.FilterRunner(
   ...     f.Split(":") | f.FilterMapper({0: f.Unicode | f.Strip, 1: f.Int})
   ... )
   >>> runner.apply("  name  :42")
   >>> runner.cleaned_data
   ['name', 42]

This lets :py:class:`filters.Split` chain straight into per-position validation,
with no list-to-dict filter in between. Such a mapper still accepts
:py:class:`~collections.abc.Mapping` input as well, and one with any other key —
a :py:class:`str`, ``bool`` keys, or an empty ``filter_map`` — is unchanged.

.. note::

   A :py:class:`filters.FilterMapper` picks its output shape from the runtime
   value, so it can't declare an output type: ``cleaned_data`` is
   :py:obj:`~typing.Any` here, whichever checker you run. The per-key chains
   inside it are still checked.

Known Limitations
-----------------
* Neither mypy nor pyright runs at full strictness yet, so some mistakes in your
  own filters go unreported. Progress is tracked in
  `issue #119 <https://github.com/todofixthis/filters/issues/119>`_.
* There is no narrowing filter category yet, so :py:class:`filters.Required` and
  ``NotEmpty(allow_none=False)`` do not narrow ``T | None`` to ``T``. Tracked in
  `issue #122 <https://github.com/todofixthis/filters/issues/122>`_.
* The two checkers disagree in two places, both covered above: an unannotated
  macro, and a chain of bare classes assigned to a variable. pyright infers the
  real type in each; mypy needs the annotation.

If you hit something this guide doesn't cover,
`post in the Filters issue tracker <https://github.com/todofixthis/filters/issues>`_
and I'll have a look 🙂
