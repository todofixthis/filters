from abc import ABCMeta, abstractmethod as abstract_method
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from copy import copy
from typing import Any, Generic, Optional, Union, overload
from weakref import ProxyTypes, proxy

from typing_extensions import TypeAliasType, TypeVar

__all__ = [
    "BaseFilter",
    "BaseInvalidValueHandler",
    "ExceptionHandler",
    "FilterChain",
    "FilterCompatible",
    "FilterError",
    "FilterMeta",
    "PassThrough",
    "T_out",
    "Type",
    "Widening",
]

# ``default=Any`` (PEP 696) keeps ``class Country(BaseFilter)`` — no type
# argument — valid even under mypy's ``disallow_any_generics`` and pyright's
# ``reportMissingTypeArgument``. Imported from ``typing_extensions`` because
# ``default=`` is native only from Python 3.13, and this package supports
# 3.12. See docs/adr/005-parameterise-filters-on-one-output-type.md.
T_out = TypeVar("T_out", default=Any)
"""The type a filter produces."""

T_widened = TypeVar("T_widened", default=Any)
"""The type a :py:class:`Widening` filter adds to a chain's output."""

T_next = TypeVar("T_next")
"""The output type of the filter being chained onto another."""

T_filtered = TypeVar("T_filtered")
"""The output type of the filter :py:meth:`BaseFilter._filter` applies."""

T_resolved = TypeVar("T_resolved")
"""The output type of the filter :py:meth:`BaseFilter.resolve_filter` returns."""

T_allowed1 = TypeVar("T_allowed1")
"""The first type a :py:class:`Type` filter accepts."""

T_allowed2 = TypeVar("T_allowed2")
"""The second type a :py:class:`Type` filter accepts."""

T_allowed3 = TypeVar("T_allowed3")
"""The third type a :py:class:`Type` filter accepts."""

TF = TypeVar("TF", bound="BaseFilter[Any]")
"""The filter :py:meth:`BaseFilter.__copy__` was handed, and returns."""

TFC = TypeVar("TFC", bound="FilterChain[Any]")
"""The chain :py:meth:`FilterChain.__copy__` was handed, and returns."""

# Note: Using typing.Optional/Union instead of PEP 604 syntax (X | Y) for
# forward references to avoid Sphinx autodoc warnings. Sphinx cannot parse
# the | operator when combined with string forward references like "BaseFilter".
#
# Built via TypeAliasType rather than a plain assignment so that
# ``type_params`` declares its genericity explicitly: a Union built from
# string forward references carries no ``__parameters__`` of its own
# (they're inside unevaluated ForwardRef objects), so a plain assignment
# left this unsubscriptable at runtime and broke ``get_type_hints()`` on
# every signature that names it. ``type_params=(T_out,)`` fixes both,
# reusing ``T_out``'s own ``default=Any`` so bare ``FilterCompatible``
# still works exactly as it did before.
FilterCompatible = TypeAliasType(
    "FilterCompatible",
    Optional[
        Union[
            "BaseFilter[T_out]",
            "type[BaseFilter[T_out]]",
            Callable[[], "BaseFilter[T_out]"],
        ]
    ],
    type_params=(T_out,),
)
"""Used in PEP-484 type hints to indicate a value that can be
normalised into an instance of a BaseFilter subclass.
"""


class FilterMeta(ABCMeta):
    """Metaclass for filters."""

    # noinspection PyShadowingBuiltins
    def __init__(cls, what, bases=None, dict=None, **kwargs):
        # noinspection PyArgumentList
        super().__init__(what, bases, dict, **kwargs)

        if not hasattr(cls, "templates"):
            cls.templates = {}

        # Copy error templates from base class to derived class, but
        # in the event of a conflict, preserve the derived class'
        # template.
        templates = {}
        for base in bases:
            if isinstance(base, FilterMeta):
                templates.update(base.templates)

        if templates:
            templates.update(cls.templates)
            cls.templates = templates

    #
    # The ``cls: "type[BaseFilter[T_out]]"`` self-type is what lets
    # ``Unicode | NotEmpty`` infer ``FilterChain[str]`` rather than
    # collapsing to ``types.UnionType``. mypy reports ``misc`` against it
    # because the annotation is not the metaclass itself; both checkers
    # nonetheless resolve the chain type correctly, so the suppression is
    # for mypy's structural objection, not for a wrong result.
    #
    # Overload order matters: PassThrough and Widening are BaseFilter
    # subclasses, so the general overloads below would swallow them. The
    # callable overload comes last for the same reason in reverse — a
    # filter *class* is itself a zero-argument callable returning a
    # filter, so placing it any earlier would swallow every ``type[...]``
    # overload above it.
    # See docs/adr/006-distinguish-filter-categories-by-marker-base-class.md.
    #
    # There is deliberately no ``None`` arm: ``FilterCompatible`` still
    # admits ``None``, but ``|`` does not — see
    # docs/adr/009-drop-none-as-an-operand-of-the-chaining-operator.md.
    #
    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "type[PassThrough]",
    ) -> "FilterChain[T_out]": ...

    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "PassThrough",
    ) -> "FilterChain[T_out]": ...

    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "Union[Widening[T_widened], type[Widening[T_widened]]]",
    ) -> "FilterChain[Union[T_out, T_widened]]": ...

    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "type[BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "BaseFilter[T_next]",
    ) -> "FilterChain[T_next]": ...

    @overload
    def __or__(  # type: ignore[misc]
        cls: "type[BaseFilter[T_out]]",
        next_filter: "Callable[[], BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    def __or__(cls, next_filter: "FilterCompatible[Any]") -> "FilterChain[Any]":
        """Convenience alias for adding a Filter with default config.

        E.g., the following statements do the same thing::

            Int | Max(32)   # FilterMeta.__or__
            Int() | Max(32) # Filter.__or__

        Note:
            Reference: http://stackoverflow.com/a/10773232

        Raises:
            TypeError: if ``next_filter`` is (or resolves to) ``None``.
        """
        # Checked here, naming ``cls``, rather than left to the
        # ``FilterChain(cls) | next_filter`` delegation below: that
        # raises the same error but names the wrapping ``FilterChain``
        # instead of the class the caller actually wrote.
        if cls.resolve_filter(next_filter) is None:
            raise TypeError(
                f"None is not compatible with {cls.__name__} in a "
                f"filter chain; use NoOp instead.",
            )

        return FilterChain(cls) | next_filter


class BaseFilter(Generic[T_out], metaclass=FilterMeta):
    """Base functionality for all Filters, macros, etc."""

    CODE_EXCEPTION = "exception"

    templates = {
        CODE_EXCEPTION: "An error occurred while processing this value.",
    }

    def __init__(self) -> None:
        super().__init__()

        self._parent: Optional[BaseFilter[Any]] = None
        self._handler: Optional[BaseInvalidValueHandler] = None
        self._key: Optional[str] = None

        #
        # Indicates whether the Filter detected any invalid values.
        # It gets reset every time `apply` gets called.
        #
        # Note that this attribute is intended to be used internally;
        # external code should instead interact with invalid value
        # handlers such as LogHandler and MemoryHandler.
        #
        # References:
        #   - :py:mod:`importer.core.filters.handlers`
        #
        self._has_errors = False

    # noinspection PyProtectedMember
    @classmethod
    def __copy__(cls, the_filter: TF) -> TF:
        """Creates a shallow copy of the object."""
        new_filter: TF = type(the_filter)()

        new_filter._parent = the_filter._parent
        new_filter._key = the_filter._key
        new_filter._handler = the_filter._handler

        return new_filter

    # The same six overloads as FilterMeta.__or__, in the same order, so
    # that chaining behaves identically whether the left operand is a
    # filter class or a filter instance.
    @overload
    def __or__(self, next_filter: "type[PassThrough]") -> "FilterChain[T_out]": ...

    @overload
    def __or__(self, next_filter: "PassThrough") -> "FilterChain[T_out]": ...

    @overload
    def __or__(
        self,
        next_filter: "Union[Widening[T_widened], type[Widening[T_widened]]]",
    ) -> "FilterChain[Union[T_out, T_widened]]": ...

    @overload
    def __or__(
        self,
        next_filter: "type[BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    @overload
    def __or__(self, next_filter: "BaseFilter[T_next]") -> "FilterChain[T_next]": ...

    @overload
    def __or__(
        self,
        next_filter: "Callable[[], BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    def __or__(self, next_filter: "FilterCompatible[Any]") -> "FilterChain[Any]":
        """Chains another filter with this one.

        Raises:
            TypeError: if ``next_filter`` is (or resolves to) ``None``.
        """
        # ``resolve_filter`` returns ``None`` only for a ``None`` operand,
        # directly or via a zero-argument callable that returns one. That
        # used to be a silent no-op.
        if self.resolve_filter(next_filter) is None:
            raise TypeError(
                f"None is not compatible with {type(self).__name__} in a "
                f"filter chain; use NoOp instead.",
            )

        #
        # Officially, we should do this:
        # return ``FilterChain(self) | next_filter``
        #
        # But that wastes some CPU cycles by creating an extra
        # FilterChain instance that gets thrown away almost
        # immediately. It's a bit faster just to create a single
        # FilterChain instance and modify it in-place.
        #
        # noinspection PyProtectedMember
        return FilterChain(self)._add(next_filter)

    def __str__(self):
        """Returns a string representation of the Filter.

        Note:
            The output of this method does not necessarily match the
            signature of the Filter's ``__init__`` method; rather, its
            purpose is to provide a snapshot of critical parts of the
            Filter's configuration for e.g., troubleshooting purposes.
        """
        return f"{type(self).__name__}()"

    @property
    def parent(
        self,
    ) -> Optional["BaseFilter[Any]"]:  # Use Optional for Sphinx compat
        """Returns the parent Filter."""
        # Make sure `self._parent` hasn't gone away.
        try:
            # noinspection PyStatementEffect
            self._parent.__class__
        except ReferenceError:
            return None

        return self._parent

    @parent.setter
    def parent(self, parent: "BaseFilter[Any]") -> None:
        """Sets the parent Filter."""
        # Create a weakref to the parent Filter to prevent annoying the
        # garbage collector.
        self._parent = (
            (parent if isinstance(parent, ProxyTypes) else proxy(parent))
            if parent
            else None
        )

    @property
    def key(self) -> str:
        """Returns the key associated with this filter."""
        return self._make_key(self._key_parts)

    @key.setter
    def key(self, key: str) -> None:
        """Sets the key associated with this filter."""
        self._key = key

    def sub_key(self, sub_key: str) -> str:
        """Returns a copy of this filter's key with an additional
        sub-key appended.
        """
        return self._make_key(self._key_parts + [sub_key])

    @property
    def _key_parts(self) -> list[str]:
        """Assembles each key part in the filter hierarchy."""
        key_parts = []

        # Iterate up the parent chain and collect key parts.
        # Alternatively, we could just get ``self.parent._key_parts``,
        # but that is way less efficient.
        parent = self
        while parent:
            # As we move up the chain, push key parts onto the front of
            # the path (otherwise the key parts would be in reverse
            # order).
            key_parts.insert(0, parent._key)
            parent = parent.parent

        return key_parts

    @property
    def handler(self) -> "BaseInvalidValueHandler":
        """Returns the invalid value handler for the filter."""
        if self._handler is None:
            # Attempt to return the parent filter's handler...
            try:
                return self.parent.handler
            except AttributeError:
                #
                # ... unless this filter has no parent, in which case
                # it should use the default.
                #
                # Note that we do not set ``self._handler``, in case
                # the filter later gets added to e.g., a FilterChain
                # that has a different invalid value handler set.
                #
                return ExceptionHandler()

        return self._handler

    @handler.setter
    def handler(self, handler: "BaseInvalidValueHandler") -> None:
        """Sets the invalid value handler for the filter."""
        self._handler = handler

    def set_handler(self, handler: "BaseInvalidValueHandler") -> "BaseFilter[T_out]":
        """Cascading method for setting the filter's invalid value
        handler.
        """
        self.handler = handler
        return self

    def apply(self, value: Any) -> Optional[T_out]:
        """Applies the filter to a value.

        Note:
            The result is ``Optional`` because every rejection path runs
            through :py:meth:`_invalid_value`, which returns its
            ``replacement`` (``None`` unless the caller overrode it)
            whenever the invalid value handler does not raise.
        """
        self._has_errors = False

        try:
            return self._apply_none() if value is None else self._apply(value)
        except Exception as e:
            return self._invalid_value(value, e, exc_info=True)

    @abstract_method
    def _apply(self, value: Any) -> T_out:
        """Applies filter-specific logic to a value.

        Note:
            It is safe to assume that ``value`` is not ``None`` when
            this method is invoked.
        """
        raise NotImplementedError(
            f"Not implemented in {type(self).__name__}.",
        )

    def _apply_none(self) -> Optional[T_out]:
        """Applies filter-specific logic when the value is ``None``."""
        return None

    def _filter(
        self,
        value: Any,
        filter_chain: "FilterCompatible[T_filtered]",
        sub_key: Optional[str] = None,
    ) -> Optional[T_filtered]:
        """Applies another filter to a value in the same context as
        the current filter.

        Note that the result is parameterised on ``filter_chain``, not on
        the calling filter — this method reports what the filter it was
        handed produces.

        Args:
            sub_key: Appended to the ``key`` value in the error message
                context (used by complex filters).
        """
        filter_chain = self.resolve_filter(
            filter_chain,
            parent=self,
            key=sub_key,
        )

        # In rare cases, ``filter_chain`` may be ``None``.
        # :py:meth:`filters.complex.FilterMapper.__init__`
        if filter_chain:
            try:
                filtered = filter_chain.apply(value)
            except Exception as e:
                return self._invalid_value(value, e, exc_info=True)
            else:
                # noinspection PyProtectedMember
                self._has_errors = self._has_errors or filter_chain._has_errors
                return filtered
        else:
            return value

    def _invalid_value(
        self,
        value: Any,
        reason: Union[str, Exception],
        replacement: Optional[Any] = None,
        exc_info: bool = False,
        context: Optional[MutableMapping] = None,
        sub_key: Optional[str] = None,
        template_vars: Optional[Mapping] = None,
    ) -> Any:
        """Handles an invalid value.

        This method works as both a logging method and an exception
        handler.

        Args:
            replacement: The replacement value to use instead.
            sub_key: Appended to the ``key`` value in the error message
                context (used by complex filters).

        Returns:
            Replacement value to use instead of the invalid value
            (usually ``None``).
        """
        handler = self.handler

        if isinstance(reason, FilterError):
            # FilterErrors should be sent directly to the handler.
            # This allows complex Filters to properly catch and handle
            # FilterErrors raised by the Filters they control.
            return handler.handle_invalid_value(
                message=str(reason),
                exc_info=True,
                context=getattr(reason, "context", {}),
            )

        self._has_errors = True

        if not context:
            context = {}

        context["value"] = value
        context["filter"] = str(self)
        context["key"] = self.sub_key(sub_key)
        context["replacement"] = replacement

        if not template_vars:
            template_vars = {}

        template_vars.update(context)

        if isinstance(reason, Exception):
            # Store the error code in the context so that the caller
            # can identify the error type without having to parse the
            # rendered error message template.
            context["code"] = self.CODE_EXCEPTION

            # Store exception details in the context so that they are
            # accessible to devs but hidden from end users.
            # Note that the traceback gets processed separately,
            context["exc"] = (
                f"[{type(reason).__module__}.{type(reason).__name__}] {reason}"
            )

            # Add the context to the exception object so that loggers
            # can use it.
            if not hasattr(reason, "context"):
                reason.context = {}
            reason.context.update(context)

            handler.handle_exception(
                message=self._format_message(context["code"], template_vars),
                exc=reason,
            )
        else:
            # Store the error code in the context so that the caller
            # can identify the error type without having to parse the
            # rendered error message template.
            context["code"] = reason

            handler.handle_invalid_value(
                message=self._format_message(reason, template_vars),
                exc_info=exc_info,
                context=context,
            )

        return replacement

    def _format_message(
        self,
        key: str,
        template_vars: Mapping[str, str],
    ) -> str:
        """Formats a message for the invalid value handler."""
        return self.templates[key].format(**template_vars)

    @classmethod
    def resolve_filter(
        cls,
        the_filter: "FilterCompatible[T_resolved]",
        # Use Optional for Sphinx compat
        parent: Optional["BaseFilter[Any]"] = None,
        key: Optional[str] = None,
    ) -> Optional["BaseFilter[T_resolved]"]:  # Use Optional for Sphinx compat
        """Converts a filter-compatible value into a consistent type."""
        if the_filter is not None:
            resolved: Optional[BaseFilter[T_resolved]]

            if isinstance(the_filter, BaseFilter):
                resolved = the_filter

            elif callable(the_filter):
                resolved = cls.resolve_filter(the_filter())

                # A callable is free to hand back ``None``; without this
                # guard the ``parent``/``key`` assignments below would
                # raise ``AttributeError`` on it.
                if resolved is None:
                    return None

            # Uhh... hm.
            else:
                raise TypeError(
                    f"{type(the_filter).__name__} {the_filter!r} is not "
                    f"compatible with {cls.__name__}.",
                )

            if parent:
                resolved.parent = parent

            if key:
                resolved.key = key

            return resolved

        return None

    @staticmethod
    def _make_key(key_parts: Iterable[str]) -> str:
        """Assembles a dotted key value from its component parts."""
        return ".".join(filter(None, key_parts))


class PassThrough(BaseFilter[Any]):
    """Marks a filter that returns its input unchanged, so that chaining
    it leaves the chain's output type alone.

    This class adds no runtime behaviour: it exists so that the overloads
    on ``|`` can tell a check (``NotEmpty``, ``Min``, ``Len``) apart from
    a transformation. Nothing does an ``isinstance`` check against it.

    Note:
        See docs/adr/006-distinguish-filter-categories-by-marker-base-class.md.
    """


class Widening(BaseFilter[Any], Generic[T_widened]):
    """Marks a filter that adds ``T_widened`` to the chain's output type
    rather than replacing it — ``Optional``, whose ``T_widened`` is the
    type of its default.

    Like :py:class:`PassThrough`, this is a static-typing device with no
    runtime behaviour of its own.
    """


class FilterChain(BaseFilter[T_out]):
    """Allows you to chain multiple filters together so that they are
    treated as a single filter.
    """

    def __init__(self, start_filter: "FilterCompatible[T_out]" = None) -> None:
        super().__init__()

        self._filters: list[BaseFilter[Any]] = []

        self._add(start_filter)

    def __str__(self):
        return f"{type(self).__name__}({' | '.join(map(str, self._filters))})"

    #
    # This override exists for a runtime reason — chaining onto a chain
    # copies rather than mutating — but it is also what makes the third
    # copy of the overloads necessary: every ``|`` after the first
    # dispatches here, and an override without them collapses a
    # three-filter chain to ``FilterChain[Any]`` on both checkers.
    #
    # Same order as the other two sets: markers first, callable last, and
    # no ``None`` arm.
    #
    @overload
    def __or__(self, next_filter: "type[PassThrough]") -> "FilterChain[T_out]": ...

    @overload
    def __or__(self, next_filter: "PassThrough") -> "FilterChain[T_out]": ...

    @overload
    def __or__(
        self,
        next_filter: "Union[Widening[T_widened], type[Widening[T_widened]]]",
    ) -> "FilterChain[Union[T_out, T_widened]]": ...

    @overload
    def __or__(
        self,
        next_filter: "type[BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    @overload
    def __or__(self, next_filter: "BaseFilter[T_next]") -> "FilterChain[T_next]": ...

    @overload
    def __or__(
        self,
        next_filter: "Callable[[], BaseFilter[T_next]]",
    ) -> "FilterChain[T_next]": ...

    def __or__(self, next_filter: "FilterCompatible[Any]") -> "FilterChain[Any]":
        """Chains a filter with this one.

        This method creates a new FilterChain object without modifying
        the current one.

        Raises:
            TypeError: if ``next_filter`` is (or resolves to) ``None``.
        """
        if self.resolve_filter(next_filter) is None:
            raise TypeError(
                f"None is not compatible with {type(self).__name__} in a "
                f"filter chain; use NoOp instead.",
            )

        new_chain: FilterChain[Any] = copy(self)
        new_chain._add(next_filter)
        return new_chain

    @classmethod
    def __copy__(cls, the_filter: TFC) -> TFC:
        """Creates a shallow copy of the object."""
        new_filter = super().__copy__(the_filter)
        new_filter._filters = the_filter._filters[:]
        # noinspection PyTypeChecker
        return new_filter

    def _add(self, next_filter: "FilterCompatible[Any]") -> "FilterChain[T_out]":
        """Adds a Filter to the collection directly."""
        resolved = self.resolve_filter(next_filter, parent=self)
        if resolved:
            self._filters.append(resolved)

        return self

    def _apply(self, value: Any) -> T_out:
        for f in self._filters:
            value = self._filter(value, f)

            # FilterChains stop at the first sign of trouble.
            # This is important because FilterChains have to behave
            # consistently regardless of whether the invalid value
            # handler raises an exception.
            if self._has_errors:
                break

        return value

    def _apply_none(self) -> Optional[T_out]:
        return self._apply(None)


class BaseInvalidValueHandler(metaclass=ABCMeta):
    """Base functionality for classes that handle invalid values."""

    @abstract_method
    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: MutableMapping,
    ) -> Any:
        """Handles an invalid value.

        Args:
            message: Error message.
            exc_info: Whether to include output from
                :py:func:``sys.exc_info``.
            context: Additional context values for the error.
        """
        raise NotImplementedError(
            f"Not implemented in {type(self).__name__}.",
        )

    def handle_exception(self, message: str, exc: Exception) -> Any:
        """Handles an uncaught exception."""
        return self.handle_invalid_value(
            message=message,
            exc_info=True,
            context=getattr(exc, "context", {}),
        )


class FilterError(ValueError):
    """Indicates that a parsed value could not be filtered because the
    value was invalid.
    """

    def __init__(self, *args, **kwargs):
        """Provides a container to include additional variables and
        other information to help troubleshoot errors.
        """
        # Exception kwargs are deprecated in Python 3, but keeping them
        # around for compatibility with Python 2.
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.context = {}


class ExceptionHandler(BaseInvalidValueHandler):
    """Invalid value handler that raises an exception."""

    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: MutableMapping,
    ) -> None:
        error = FilterError(message)
        error.context = context
        raise error


# This filter is used extensively by other filters.
# To avoid lots of needless "circular import" hacks, we'll put it in
# the base module.
class Type(BaseFilter[T_out]):
    """Checks the type of a value."""

    CODE_WRONG_TYPE = "wrong_type"

    templates = {
        CODE_WRONG_TYPE: "{incoming} is not valid (allowed types: {allowed}).",
    }

    #
    # Each of the two useful forms — a single type, and a 2-tuple of them
    # — is paired with a bare-``type`` fallback resolving to ``Type[Any]``.
    # The fallbacks are what let an abstract base class through: mypy
    # rejects one against ``type[T]`` with ``type-abstract``, and this
    # package passes ABCs to ``Type`` in ``simple.py`` and ``complex.py``.
    #
    # pyright reaches the same conclusion from the first overload alone,
    # so it reports the fallback as unreachable; it is not, for mypy.
    #
    # Tuples stop at three. ``Type((str, int, float, bool))`` resolves to
    # ``Type[Any]``, which is an accepted limit rather than a defect —
    # neither ``src`` nor ``test`` passes a 4-tuple today. A TypeVarTuple
    # can't replace these individual overloads: neither mypy nor pyright
    # allows unpacking one into a ``Union`` (confirmed against both), so
    # supporting an arbitrary size would still mean one overload per
    # arity, same as this list, just longer.
    #
    @overload
    def __init__(
        self: "Type[T_allowed1]",
        allowed_types: type[T_allowed1],
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None: ...

    @overload
    def __init__(  # pyright: ignore[reportOverlappingOverload]
        self: "Type[Any]",
        allowed_types: type,
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: "Type[Union[T_allowed1, T_allowed2]]",
        allowed_types: tuple[type[T_allowed1], type[T_allowed2]],
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: "Type[Union[T_allowed1, T_allowed2, T_allowed3]]",
        allowed_types: tuple[type[T_allowed1], type[T_allowed2], type[T_allowed3]],
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None: ...

    @overload
    def __init__(
        self: "Type[Any]",
        allowed_types: tuple[type, ...],
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None: ...

    def __init__(
        self,
        allowed_types: Union[type, tuple[type, ...]],
        allow_subclass: bool = True,
        aliases: Optional[Mapping[type, str]] = None,
    ) -> None:
        """Initialises the filter.

        Args:
            allowed_types: The type (or types) that incoming values are
                allowed to have.
            allow_subclass: Whether to allow subclasses when checking for
                type matches.
            aliases: Aliases to use for type names in error messages.

                This is useful for providing more context-appropriate
                names to end users and/or masking native Python type
                names.
        """
        super().__init__()

        # A pinch of syntactic sugar.
        self.allowed_types = (
            allowed_types if isinstance(allowed_types, tuple) else (allowed_types,)
        )
        self.allow_subclass = allow_subclass

        self.aliases = aliases or {}

    def __str__(self):
        return (
            f"{type(self).__name__}({self.get_allowed_type_names(aliased=False)}, "
            f"allow_subclass={self.allow_subclass!r})"
        )

    def _apply(self, value: Any) -> T_out:
        valid = (
            isinstance(value, self.allowed_types)
            if self.allow_subclass
            else (type(value) in self.allowed_types)
        )

        if not valid:
            return self._invalid_value(
                value=value,
                reason=self.CODE_WRONG_TYPE,
                template_vars={
                    "incoming": self.get_type_name(type(value)),
                    "allowed": self.get_allowed_type_names(),
                },
            )

        return value

    def get_allowed_type_names(self, aliased: bool = True) -> str:
        """Returns a string with all the allowed types."""
        # Note that we cast as a set in the middle, to ferret out
        # duplicates.
        return ", ".join(
            sorted({self.get_type_name(t, aliased) for t in self.allowed_types})
        )

    def get_type_name(self, type_: type, aliased: bool = True) -> str:
        """Returns the name of the specified type.

        Note:
            Reference: https://bugs.python.org/issue34422
        """
        # Depending on the type, it may require a bit of creativity to
        # find the proper name.
        # https://bugs.python.org/issue34422
        possible_names = [
            getattr(type_, "_name", None),
            getattr(type_, "__name__", None),
            str(type_),
        ]

        if aliased:
            possible_names.insert(0, self.aliases.get(type_))

        return next(filter(None, possible_names))
