Upgrading to Filters v4
=======================

`Filters v4 <https://github.com/todofixthis/filters/releases/tag/4.0.0a2>`_ makes
every filter generic over its output type, so a type checker can follow a value
all the way through a chain. That part is free — your own filters need no
changes. But three changes can break code that worked in Filters v3, and one of
them fails silently. A few bug fixes also change results; see
:ref:`upgrade-v4-bug-fixes`. And if you run mypy, it checks your calls into
Filters for the first time, which can report errors in code you haven't
touched; see :ref:`upgrade-v4-type-parameters`.

.. note::

   This guide covers the v4 alpha. The typing surface may still shift before
   4.0.0 final.

Installing the alpha
--------------------
Pre-release versions aren't selected by default, so ask for this one
explicitly::

    pip install --pre 'phx-filters==4.0.0a2'

Or, with `uv <https://docs.astral.sh/uv/>`_::

    uv add 'phx-filters==4.0.0a2'

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
Ordered by how likely each is to affect your code, not by how loud the
failure is — the last one gives no warning at all, but tripping it takes a
subclass check on these specific filters, which most code never does:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Change
     - How it surfaces
     - How to find it
   * - :ref:`upgrade-v4-none`
     - :py:class:`TypeError` when the chain is *built*. For chains defined at
       module scope, that's on import — but only if your test suite imports
       that module.
     - A type checker flags every one immediately; if you don't have one,
       consider adopting one. Otherwise,
       ``rg -U 'f\.\w+(?:\([^)]*\))?\s*\|\s*None'`` catches chains built off
       the conventional ``import filters as f`` alias, though not one
       assembled through an intermediate variable.
   * - :ref:`upgrade-v4-split`
     - :py:class:`ValueError` when the filter is *constructed*. For one
       built at module scope, that's on import.
     - ``rg -U 'Split\([^)]*,'`` — a candidate list to eyeball; check each
       hit for a ``keys`` argument
   * - :ref:`upgrade-v4-siblings`
     - **Nothing.** No exception, no warning — a check silently returns
       ``False`` and your code takes the other branch.
     - ``rg -U '(?s)(isinstance|issubclass)\(.{0,120}?\b(ByteString|Date|Datetime|Unicode)\b'``

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

   chain = f.Unicode | f.NoOp | f.Strip

This most often shows up when a chain is assembled from parts that may
legitimately be absent:

Filters v3:

.. code-block:: python

   def build_chain(extra=None):
       return f.Unicode | extra

Filters v4:

.. code-block:: python

   def build_chain(extra=f.NoOp):
       return f.Unicode | extra

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

   ``f.Split(pattern, keys=[])`` — an empty ``keys``, not ``None`` — now
   raises :py:class:`ValueError` immediately::

      ValueError: keys must not be empty; pass None for list output instead.

Filters v3 branched on whether ``keys`` was *truthy*, so an empty ``keys`` fell
through to the list branch and returned a list. Filters v4 branches on
``keys is not None``, which is what the documented behaviour always described:
an empty ``keys`` caps the split at zero items, and nothing fits — so rather
than let every ``apply()`` call fail on that, it's rejected up front, where the
mistake was actually made.

.. note::

   Why not just fall back to a list, the way Filters v3 did? The two
   constructor overloads dispatch on the *type* of ``keys`` — ``None``
   versus ``Sequence[str]`` — not its value, and there is no way to type
   "a non-empty sequence" separately from "a sequence." For a *computed*
   ``keys``, a type checker can't know whether it will be empty at
   runtime, so it infers ``Split[dict[str, str]]`` for any non-``None``
   ``keys`` regardless. Falling back to a list on empty input would make
   that inference silently wrong: code trusting the dict type would only
   fail later, at whatever call site used the result — further from the
   mistake, and with no exception pointing back to it.

The :py:class:`ValueError` fires when the filter is *constructed*, not when it
runs, so a filter built at module scope raises on import.

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
   Filters v3 that quietly returned a list; it now raises as soon as that
   ``Split`` is built, which is the point.

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

.. _upgrade-v4-bug-fixes:

Bug Fixes That Change Results
-----------------------------
These bugs are present in Filters v3 too, so they don't break code that relied
on documented behaviour. But fixing them changes what some code observes, so
check your code if any of these apply:

* :py:class:`filters.Item` with a key that isn't a :py:class:`str`, such as an
  :py:class:`int` or a :py:class:`tuple`, missing from a mapping reported
  ``exception`` instead of ``missing``. A falsy key such as ``0`` reported
  ``missing`` but dropped out of the error's key. Every such key now reports
  ``missing`` under ``str(key)``: ``f.Item(42)`` on ``{'a': 1}`` gives
  ``{'42': ['missing']}`` where it gave ``{'': ['exception']}``.
* ``FilterRunner(None)`` failed with :py:class:`AttributeError` on first use.
  It now raises :py:class:`TypeError` as soon as it's constructed, even if the
  runner is never used. Use :py:class:`filters.NoOp` instead.
* A custom filter passing ``template_vars`` to ``_invalid_value()`` had that
  mapping mutated with the error context, and a read-only mapping made the
  filter report ``exception`` instead of its own error code. The mapping is
  now left untouched.
* With ``capture_exc_info=True``, ``exc_info`` on
  :py:class:`filters.MemoryHandler` and
  :py:class:`filters.FilterRunner` recorded ``sys.exc_info()``, which is
  ``(None, None, None)`` outside an ``except`` block. It now records the
  exception the filter reported. Where a custom filter catches one exception
  and reports another, it holds the reported one, whose traceback is ``None``
  unless it was raised.

.. _upgrade-v4-type-parameters:

Type Parameters
---------------
Now for the good news 😺

Chains and :py:class:`filters.FilterRunner` infer real types instead of
:py:obj:`~typing.Any`:

.. code-block:: python

   import filters as f

   # Inferred as ``int``, not ``Any``.
   f.FilterRunner(f.Int).cleaned_data

   # Inferred as ``str``.
   f.FilterRunner(f.Unicode | f.Strip | f.NotEmpty).cleaned_data

The library ships a ``py.typed`` marker, so you get this without installing a
separate stubs package.

.. warning::

   The marker also makes mypy check your own calls into Filters for the first
   time. Filters v3 had no marker, so mypy treated everything you imported from
   it as :py:obj:`~typing.Any`. A project that type-checked cleanly against
   Filters v3 can report new errors after you upgrade, without any change to
   its code. A common one is a :py:class:`filters.FilterMapper` spec held
   in a variable. Unless every value in the spec is a bare filter class, mypy
   infers ``dict[str, object]`` for the variable, then reports ``arg-type``
   where you pass it:

   .. code-block:: python

      spec = {"id": f.Int, "name": f.Unicode | f.Strip}

      # error: Argument 1 to "FilterMapper" has incompatible type
      # "dict[str, object]"
      f.FilterMapper(spec)

   Annotate the variable as ``dict[str, f.FilterCompatible]`` to clear the
   error, or pass the spec inline. pyright infers a usable type either way.

   These errors change nothing at runtime, where the code behaves as it did
   under Filters v3.

   If a ``# type: ignore`` comment on your ``import filters`` line silenced the
   missing marker, mypy's ``warn_unused_ignores`` reports that comment as
   unused, so remove it.

.. tip::

   To give each key a type of its own, try
   `phx-filters-pydantic <https://phx-filters-pydantic.readthedocs.io/>`_. A
   :py:class:`filters.FilterMapper` yields :py:obj:`~typing.Any`, so a type
   checker learns nothing about the values in its output. With
   ``phx-filters-pydantic``, you declare each key as a field of a
   `pydantic <https://docs.pydantic.dev/>`_ model and attach its chain to the
   field, so the checker knows the type of every field:

   .. code-block:: python

      from typing import Annotated

      import filters as f
      from filters_pydantic import FilterField
      from pydantic import BaseModel

      class Person(BaseModel):
          id: Annotated[int, FilterField(f.Int)]
          name: Annotated[str, FilterField(f.Unicode | f.Strip)]

      person = Person.model_validate({"id": "42", "name": " Phoenix "})

      # Inferred as ``int``.
      person.id

   A model is stricter than the mapper it replaces, so check these before you
   port a spec. A model rejects a missing key or a ``None`` value unless you
   declare the field as optional with a default, where a mapper passes
   ``None`` through. A model drops keys that it doesn't declare, where a mapper
   keeps them by default. And a model raises pydantic's ``ValidationError``,
   which carries each filter's message but not its error code.

   Its v1 is in alpha alongside Filters v4, so ask for the pre-release
   explicitly::

       pip install --pre phx-filters-pydantic

.. note::

   Not every filter can declare an output type. A validator that passes its
   input through — :py:class:`filters.NotEmpty`, :py:class:`filters.Required`,
   :py:class:`filters.Min` — leaves the chain's type alone, and
   :py:class:`filters.Optional` widens it to include its default's type. But a
   filter whose output shape is only known at runtime still yields
   :py:obj:`~typing.Any`, so a chain ending in one infers nothing:
   :py:class:`filters.JsonDecode`, :py:class:`filters.FilterMapper`,
   :py:class:`filters.FilterRepeater`, :py:class:`filters.FilterSwitch`,
   :py:class:`filters.Array`, :py:class:`filters.Item`,
   :py:class:`filters.Pick` and :py:class:`filters.Omit`.

   :py:class:`filters.Type`, :py:class:`filters.NamedTuple`,
   :py:class:`filters.Choice`, :py:class:`filters.Round` and
   :py:class:`filters.Call` take their output type from their constructor
   arguments, so they infer only when you instantiate them.

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

      # mypy infers ``types.UnionType``, so passing ``chain`` to a filter or
      # ``FilterRunner`` reports ``arg-type`` (``dict-item`` in a
      # ``FilterMapper``'s map), and the output is ``Any``.
      chain = f.Unicode | f.Strip | f.NotEmpty

   Passing a chain straight into a filter, as in the examples above, is
   unaffected. Where you do want to name it, either annotate the variable or
   instantiate any one of the filters:

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
* Filters checks its own code with mypy and pyright in strict mode, except for
  three rules: mypy's ``return-value`` and ``no-any-return``, and pyright's
  ``reportReturnType``. All three report the way a filter rejects a value,
  which the next item covers.
* A filter rejects a value by returning ``None``, which your ``_apply``'s return
  annotation doesn't include: subclass ``BaseFilter[str]``, annotate ``_apply``
  as returning :py:class:`str`, and ``return None`` reports ``return-value``
  under mypy and ``reportReturnType`` under pyright. Widening ``_apply`` to
  ``Optional[str]`` swaps that for an ``override`` error, so suppress the two
  rules on those lines, or disable them as Filters does for its own code.
  Leaving ``_apply`` without annotations doesn't avoid it under pyright, which
  infers the return type and reports ``reportIncompatibleMethodOverride`` on
  the ``def`` line at its default rules. Suppress that rule there. mypy
  doesn't check an unannotated ``_apply`` unless you run it in strict mode.
  ``return self._invalid_value(...)`` reports neither, because
  ``_invalid_value()`` returns :py:obj:`~typing.Any`. Under ``mypy --strict``
  it reports ``no-any-return`` instead; pyright has no matching rule. Suppress
  ``no-any-return`` on those lines, or disable it for the modules that hold
  your filters, as Filters does.
  ``mypy --strict`` reports ``no-any-return`` on ``return value`` after
  ``value = self._filter(value, ...)`` too, because ``value`` is still the
  :py:obj:`~typing.Any` parameter. To clear that one, assign the result of
  ``_filter()`` to a new name. That result is an :py:obj:`~typing.Optional`,
  so check ``if self._has_errors or result is None:`` after it to narrow the
  result.
  Filters will stop returning ``None`` to reject in
  `issue #121 <https://github.com/todofixthis/filters/issues/121>`_.
* A filter instance must not be applied from two threads at the same time.
  A filter keeps the state of the run in progress on the instance, so two
  threads that share one can swap errors: one run accepts an invalid value,
  and the other rejects a valid one. Filters share an instance more often than
  it looks. After ``Text = f.Unicode | f.Strip``, the chains
  ``Text | f.MaxLength(50)`` and ``Text | f.MaxLength(2000)`` hold the same
  ``Unicode`` and ``Strip`` instances, and so does every
  :py:class:`filters.FilterMapper` or :py:class:`filters.FilterRepeater` that
  ``Text`` is nested in. Where threads validate at the same time, as most web
  frameworks do with synchronous code, build each thread's filters inside a
  function it calls, with no filter object defined outside that function, or
  hold a lock around every run. Filters v3 has the same limitation. Tracked in
  `issue #175 <https://github.com/todofixthis/filters/issues/175>`_.
* There is no narrowing filter category yet, so :py:class:`filters.Required` and
  ``NotEmpty(allow_none=False)`` do not narrow ``T | None`` to ``T``. Tracked in
  `issue #122 <https://github.com/todofixthis/filters/issues/122>`_.
* The two checkers infer different types in three places, all covered above:
  an unannotated macro, a chain of bare classes assigned to a variable, and a
  :py:class:`filters.FilterMapper` spec assigned to a variable. pyright infers
  a usable type in each; mypy needs the annotation.

If you hit something this guide doesn't cover,
`post in the Filters issue tracker <https://github.com/todofixthis/filters/issues>`_
and I'll have a look 🙂
