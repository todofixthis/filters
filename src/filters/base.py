import typing
from abc import ABCMeta, abstractmethod as abstract_method
from copy import copy
from weakref import ProxyTypes, proxy

__all__ = [
    "BaseFilter",
    "BaseInvalidValueHandler",
    "ExceptionHandler",
    "FilterChain",
    "FilterError",
    "NoOp",
    "Type",
]

T = typing.TypeVar("T")
U = typing.TypeVar("U")


class BaseFilter(typing.Generic[T]):
    """
    Base functionality for all Filters, macros, etc.
    """

    CODE_EXCEPTION = "exception"

    templates: dict[str, str] = {
        CODE_EXCEPTION: "An error occurred while processing this value.",
    }

    def __init__(self) -> None:
        super().__init__()

        self._parent: BaseFilter[T] | None = None
        self._handler: BaseInvalidValueHandler | None = None
        self._key: str | None = None

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

    def __init_subclass__(cls, **kwargs: typing.Any) -> None:
        """
        Pre-compute some values to improve performance in derived classes.
        """
        if not hasattr(cls, "templates"):
            cls.templates = {}

        # Copy error templates from base class to derived class, but in the
        # event of a conflict, preserve the derived class' template.
        templates: dict[str, str] = {}
        for base in cls.__bases__:
            if issubclass(base, BaseFilter):
                templates.update(base.templates)

        if templates:
            templates.update(cls.templates)
            cls.templates = templates

    @classmethod
    def __copy__(cls, the_filter: "BaseFilter[T]") -> "BaseFilter[T]":
        """
        Creates a shallow copy of the object.
        """
        new_filter: BaseFilter[T] = type(the_filter)()

        new_filter._parent = the_filter._parent
        new_filter._key = the_filter._key
        new_filter._handler = the_filter._handler

        return new_filter

    def __or__(self, next_filter: "BaseFilter[U] | None") -> "FilterChain[U]":
        """
        Chains another filter with this one.
        """
        # Scrub type info from the chain, so we can modify it later.
        chain = FilterChain[typing.Any](self)

        #
        # Officially, we should return ``FilterChain(self) | next_filter``
        #
        # But that wastes some CPU cycles by creating an extra
        # FilterChain instance that gets thrown away almost
        # immediately. It's a bit faster just to create a single
        # FilterChain instance and modify it in-place.
        #
        # noinspection PyProtectedMember
        return typing.cast(FilterChain[U], chain._add(chain.resolve(next_filter)))

    def __str__(self) -> str:
        """
        Returns a string representation of the Filter.

        Note that the output of this method does not necessarily match
        the signature of the Filter's ``__init__`` method; rather,
        its purpose is to provide a snapshot of critical parts of
        the Filter's configuration for e.g., troubleshooting
        purposes.
        """
        return "{type}()".format(
            type=type(self).__name__,
        )

    @property
    def parent(self) -> "BaseFilter[typing.Any] | None":
        """
        Returns the parent Filter.
        """
        # Make sure `self._parent` hasn't gone away.
        try:
            # noinspection PyStatementEffect
            self._parent.__class__
        except ReferenceError:
            return None

        return self._parent

    @parent.setter
    def parent(self, parent: "BaseFilter[typing.Any]") -> None:
        """
        Sets the parent Filter.
        """
        # Create a weakref to the parent Filter to prevent annoying the
        # garbage collector.
        self._parent = (
            (parent if isinstance(parent, ProxyTypes) else proxy(parent))
            if parent
            else None
        )

    @property
    def key(self) -> str:
        """
        Returns the key associated with this filter.
        """
        return self._make_key(self._key_parts)

    @key.setter
    def key(self, key: str) -> None:
        """
        Sets the key associated with this filter.
        """
        self._key = key

    def sub_key(self, sub_key: str) -> str:
        """
        Returns a copy of this filter's key with an additional sub-key
        appended.
        """
        return self._make_key(self._key_parts + [sub_key])

    @property
    def _key_parts(self) -> list[str]:
        """
        Assembles each key part in the filter hierarchy.
        """
        key_parts: list[str] = []

        # Iterate up the parent chain and collect key parts.
        # Alternatively, we could just get ``self.parent._key_parts``,
        # but that is way less efficient.
        parent: BaseFilter[typing.Any] | None = self
        while parent:
            # As we move up the chain, push key parts onto the front of
            # the path (otherwise the key parts would be in reverse
            # order).
            if parent._key is not None:
                key_parts.insert(0, parent._key)
            parent = parent.parent

        return key_parts

    @property
    def handler(self) -> "BaseInvalidValueHandler":
        """
        Returns the invalid value handler for the filter.
        """
        if self._handler is None:
            # Attempt to return the parent filter's handler...
            if self.parent:
                return self.parent.handler
            else:
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
        """
        Sets the invalid value handler for the filter.
        """
        self._handler = handler

    def set_handler(self, handler: "BaseInvalidValueHandler") -> "BaseFilter[T]":
        """
        Cascading method for setting the filter's invalid value
        handler.
        """
        self.handler = handler
        return self

    def apply(self, value: typing.Any) -> T | None:
        """
        Applies the filter to a value.
        """
        self._has_errors = False

        try:
            return self._apply_none() if value is None else self._apply(value)
        except Exception as e:
            return self._invalid_value(value, e, exc_info=True)

    @abstract_method
    def _apply(self, value: typing.Any) -> T:
        """
        Applies filter-specific logic to a value.

        Note:  It is safe to assume that ``value`` is not ``None`` when
        this method is invoked.
        """
        raise NotImplementedError(
            "Not implemented in {cls}.".format(cls=type(self).__name__),
        )

    def _apply_none(self) -> None:
        """
        Applies filter-specific logic when the incoming value is ``None``.
        """
        return None

    def _filter(
        self,
        value: typing.Any,
        filter_chain: "BaseFilter[U]",
        sub_key: str | None = None,
    ) -> U:
        """
        Applies another filter to a value in the same context as the
        current filter.

        :param sub_key:
            Appended to the ``key`` value in the error message context
            (used by complex filters).
        """
        filter_chain = self.resolve(
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
        value: typing.Any,
        reason: typing.Union[str, Exception],
        replacement: typing.Any = None,
        exc_info: bool = False,
        context: typing.MutableMapping[str, typing.Any] | None = None,
        sub_key: str | None = None,
        template_vars: typing.Mapping[str, str] | None = None,
    ) -> T | None:
        """
        Handles an invalid value.

        This method works as both a logging method and an exception
        handler.

        :param replacement:
            The replacement value to use instead.

        :param sub_key:
            Appended to the ``key`` value in the error message context
            (used by complex filters).

        :return:
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
            context["exc"] = "[{mod}.{cls}] {msg}".format(
                mod=type(reason).__module__,
                cls=type(reason).__name__,
                msg=str(reason),
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
        template_vars: typing.Mapping[str, str],
    ) -> str:
        """
        Formats a message for the invalid value handler.
        """
        return self.templates[key].format(**template_vars)

    @classmethod
    def resolve(
        cls,
        the_filter: typing.Union[
            "BaseFilter[U]", typing.Callable[[], "BaseFilter[U]"], None
        ],
        parent: "BaseFilter[typing.Any] | None" = None,
        key: str | None = None,
    ) -> "BaseFilter[U]":
        """
        Converts a filter-compatible value into a consistent type.
        """
        if the_filter is not None:
            if isinstance(the_filter, BaseFilter):
                resolved = the_filter

            elif callable(the_filter):
                resolved = cls.resolve(the_filter())

            # Uhh... hm.
            else:
                raise TypeError(
                    f"{type(the_filter).__name__} {the_filter!r} "
                    f"is not compatible with {cls.__name__}."
                )

            if parent:
                resolved.parent = parent

            if key:
                resolved.key = key

            return resolved

        return NoOp[U]()

    @staticmethod
    def _make_key(key_parts: typing.Iterable[str]) -> str:
        """
        Assembles a dotted key value from its component parts.
        """
        return ".".join(filter(None, key_parts))


class FilterChain(BaseFilter[T]):
    """
    Allows you to chain multiple filters together so that they are
    treated as a single filter.
    """

    def __init__(self, start_filter: BaseFilter[T] | None = None) -> None:
        super().__init__()

        self._filters: list[BaseFilter[typing.Any]] = []

        self._add(start_filter)

    def __str__(self):
        return "{type}({filters})".format(
            type=type(self).__name__,
            filters=" | ".join(map(str, self._filters)),
        )

    @typing.overload
    def __or__(self, next_filter: None) -> "FilterChain[T]": ...

    def __or__(self, next_filter: BaseFilter[U]) -> "FilterChain[U]":
        """
        Chains a filter with this one.

        This method creates a new FilterChain object without modifying
        the current one.
        """
        resolved = self.resolve(next_filter)

        if resolved:
            new_chain: FilterChain[U] = copy(self)
            new_chain._add(next_filter)
            return new_chain
        else:
            return self

    @classmethod
    def __copy__(cls, the_filter: "FilterChain[T]") -> "FilterChain[T]":
        """
        Creates a shallow copy of the object.
        """
        new_filter = super().__copy__(the_filter)
        new_filter._filters = the_filter._filters[:]
        # noinspection PyTypeChecker
        return new_filter

    def _add(self, next_filter: BaseFilter[U]) -> "FilterChain[U]":
        """
        Adds a Filter to the collection directly.
        """
        resolved = self.resolve(next_filter, parent=self)
        if resolved:
            self._filters.append(resolved)

        return self

    def _apply(self, value):
        for f in self._filters:
            value = self._filter(value, f)

            # FilterChains stop at the first sign of trouble.
            # This is important because FilterChains have to behave
            # consistently regardless of whether the invalid value
            # handler raises an exception.
            if self._has_errors:
                break

        return value

    def _apply_none(self):
        return self._apply(None)


class BaseInvalidValueHandler(metaclass=ABCMeta):
    """
    Base functionality for classes that handle invalid values.
    """

    @abstract_method
    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: typing.MutableMapping[str, typing.Any],
    ) -> typing.Any:
        """
        Handles an invalid value.

        :param message:
            Error message.

        :param exc_info:
            Whether to include output from :py:func:``sys.exc_info``.

        :param context:
            Additional context values for the error.
        """
        raise NotImplementedError(
            "Not implemented in {cls}.".format(cls=type(self).__name__),
        )

    def handle_exception(self, message: str, exc: Exception) -> typing.Any:
        """
        Handles an uncaught exception.
        """
        return self.handle_invalid_value(
            message=message,
            exc_info=True,
            context=getattr(exc, "context", {}),
        )


class FilterError(ValueError):
    """
    Indicates that a parsed value could not be filtered because the
    value was invalid.
    """

    def __init__(self, *args, **kwargs):
        """
        Provides a container to include additional variables and other
        information to help troubleshoot errors.
        """
        # Exception kwargs are deprecated in Python 3, but keeping them
        # around for compatibility with Python 2.
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.context = {}


class ExceptionHandler(BaseInvalidValueHandler):
    """
    Invalid value handler that raises an exception.
    """

    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: typing.MutableMapping[str, typing.Any],
    ) -> None:
        error = FilterError(message)
        error.context = context
        raise error


class NoOp(BaseFilter[T]):
    """
    Filter that does nothing, used when you need a placeholder Filter in a
    FilterChain.
    """

    def _apply(self, value):
        return value


# This filter is used extensively by other filters.
# To avoid lots of needless "circular import" hacks, we'll put it in
# the base module.
class Type(BaseFilter):
    """
    Checks the type of the incoming value.
    """

    CODE_WRONG_TYPE = "wrong_type"

    templates = {
        CODE_WRONG_TYPE: "{incoming} is not valid (allowed types: {allowed}).",
    }

    def __init__(
        self,
        allowed_types: typing.Union[type, typing.Tuple[type, ...]],
        allow_subclass: bool = True,
    ) -> None:
        """
        :param allowed_types:
            The type (or types) that incoming values are allowed to
            have.

        :param allow_subclass:
            Whether to allow subclasses when checking for type matches.
        """
        super().__init__()

        # A pinch of syntactic sugar.
        self.allowed_types = (
            allowed_types if isinstance(allowed_types, tuple) else (allowed_types,)
        )
        self.allow_subclass = allow_subclass

    def __str__(self):
        return "{type}({allowed_types}, " "allow_subclass={allow_subclass!r})".format(
            type=type(self).__name__,
            allowed_types=self.allowed_types,
            allow_subclass=self.allow_subclass,
        )

    def _apply(self, value):
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
                    "allowed": self.allowed_types,
                },
            )

        return value

    @staticmethod
    def get_type_name(type_: type) -> str:
        """
        Returns the name of the specified type.
        """
        # Depending on the type, it may require a bit of creativity to
        # find the proper name.
        # https://bugs.python.org/issue34422
        possible_names = [
            getattr(type_, "_name", None),
            getattr(type_, "__name__", None),
            str(type_),
        ]

        return next(filter(None, possible_names))
