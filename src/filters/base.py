import typing
from abc import ABC, abstractmethod as abstract_method
from weakref import ProxyTypes, proxy

__all__ = [
    "BaseFilter",
    "BaseFilterError",
    "FilterChain",
    "FilterError",
    "FilterHarness",
    "NoOp",
    "Type",
    "UncaughtException",
]


class BaseFilter[T](ABC):
    """
    Base functionality for all Filters, macros, etc.
    """

    CODE_EXCEPTION = "exception"

    templates: dict[str, str] = {
        CODE_EXCEPTION: "An error occurred while processing this value.",
    }

    def __init__(self) -> None:
        super().__init__()

        self._harness: FilterHarness | None = None
        self._key: str | None = None
        self._parent: BaseFilter[typing.Any] | None = None

    def __init_subclass__(cls, **kwargs: typing.Any) -> None:
        """
        Pre-compute some values to improve performance in derived classes.
        """
        if not hasattr(cls, "templates"):
            cls.templates = {}

        # Copy error templates from base class to derived class, but if there's a
        # conflict, preserve the derived class' template.
        templates: dict[str, str] = {}
        for base in cls.__bases__:
            if issubclass(base, BaseFilter):
                templates.update(base.templates)

        if templates:
            templates.update(cls.templates)
            cls.templates = templates

    @typing.overload
    def __or__(self, next_filter: None) -> "FilterChain[T]": ...

    @typing.overload
    def __or__[U](self, next_filter: "BaseFilter[U]") -> "FilterChain[U]": ...

    def __or__[U](
        self, next_filter: "BaseFilter[U] | None"
    ) -> "FilterChain[T] | FilterChain[U]":
        """
        Chains another filter with this one.
        """
        # Scrub type info from the chain, so we can modify it later.
        chain = FilterChain[typing.Any](self)

        # Officially, we should return ``FilterChain(self) | next_filter``
        #
        # But that wastes some CPU cycles by creating an extra :py:cls:`FilterChain`
        # instance that gets thrown away almost immediately. It's a bit faster just to
        # create a single :py:cls:`FilterChain` instance and modify it in-place.
        #
        # noinspection PyProtectedMember
        return typing.cast(FilterChain[U], chain._add(chain.resolve(next_filter)))

    def __str__(self) -> str:
        """
        Returns a string representation of the Filter.

        Note that the output of this method does not necessarily match the signature of
        the Filter's ``__init__`` method; rather, its purpose is to provide a snapshot
        of the Filter's configuration for e.g., troubleshooting purposes.
        """
        return "{type}()".format(
            type=type(self).__name__,
        )

    @property
    def harness(self) -> "FilterHarness | None":
        """
        Returns the harness in which this filter is running (if applicable).
        """
        return self._harness

    @harness.setter
    def harness(self, harness: "FilterHarness") -> None:
        """
        Sets up a new harness for this filter.
        """
        self._harness = harness

    @property
    def parent(self) -> "BaseFilter[typing.Any] | None":
        """
        Returns the parent Filter.
        """
        # Make sure `self._parent` hasn't gone away (we use weakref to avoid circular
        # references).
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
        # Create a weakref to the parent Filter to avoid annoying the garbage collector.
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
        Returns a copy of this filter's key with an additional subkey appended.
        """
        return self._make_key(self._key_parts + [sub_key])

    @property
    def _key_parts(self) -> list[str]:
        """
        Assembles each key part in the filter hierarchy.
        """
        key_parts: list[str] = []

        # Iterate up the parent chain and collect key parts.
        # Alternatively, we could just get ``self.parent._key_parts``, but that is way
        # less efficient.
        parent: BaseFilter[typing.Any] | None = self
        while parent:
            # As we move up the chain, push key parts onto the *front* of the path
            # (otherwise the key parts would be in reverse order).
            if parent._key is not None:
                key_parts.insert(0, parent._key)
            parent = parent.parent

        return key_parts

    def apply(self, value: typing.Any) -> T | None:
        """
        Applies the filter to a value.
        """
        try:
            if value is None:
                self._apply_none()
                return None

            return self._apply(value)
        except FilterError as e:
            if harness := self.harness:
                harness.handle_filter_error(e)
                return None
            raise
        except Exception as e:
            if harness := self.harness:
                harness.handle_exception(UncaughtException(self, value, e))
                return None
            raise

    @abstract_method
    def _apply(self, value: typing.Any) -> T:
        """
        Applies filter-specific logic to a value.

        .. Note::
           It is safe to assume that ``value`` is not ``None`` when this method is
           invoked.
        """
        raise NotImplementedError(
            "Not implemented in {cls}.".format(cls=type(self).__name__),
        )

    def _apply_none(self) -> None:
        """
        Applies filter-specific logic when the incoming value is ``None``.

        .. note::
           The return value from this method is ignored.
        """
        pass

    def _filter[U](
        self,
        value: typing.Any,
        filter_: "BaseFilter[U]",
        sub_key: str | None = None,
    ) -> U | None:
        """
        Applies another filter to a value in the same context as the current filter.

        :param sub_key:
            Appended to the ``key`` value in the error message context (used by complex
            filters).
        """
        filter_ = self.resolve(filter_, parent=self, key=sub_key)

        # In rare cases, ``filter_`` may be ``None``.
        # :see: :py:meth:`filters.complex.FilterMapper.__init__`
        if filter_:
            return filter_.apply(value)

        # If we get here, assume that ``value`` is valid.
        return typing.cast(U, value)

    @classmethod
    def resolve[U](
        cls,
        the_filter: "BaseFilter[U] | typing.Callable[[], BaseFilter[U]] | None",
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
        Assembles a dotted key value from its parts.
        """
        return ".".join(filter(None, key_parts))


class FilterChain[T](BaseFilter[T]):
    """
    Allows chaining multiple filters together so that they are treated as a single
    filter.
    """

    def __init__(self, start_filter: BaseFilter[T] | None = None) -> None:
        super().__init__()

        self._filters: list[BaseFilter[typing.Any]] = []

        self._add(start_filter)

    def __str__(self) -> str:
        return "{type}({filters})".format(
            type=type(self).__name__,
            filters=" | ".join(map(str, self._filters)),
        )

    @typing.overload
    def __or__(self, next_filter: None) -> "FilterChain[T]": ...

    @typing.overload
    def __or__[U](self, next_filter: BaseFilter[U]) -> "FilterChain[U]": ...

    def __or__[U](
        self, next_filter: "BaseFilter[U] | None"
    ) -> "FilterChain[T] | FilterChain[U]":
        """
        Chains a filter with this one.

        This method creates a new FilterChain object without modifying the current one.
        """
        resolved = self.resolve(next_filter)

        if resolved:
            new_chain = FilterChain[U]()

            # Copy internal properties
            new_chain._harness = self._harness
            new_chain._key = self._key
            new_chain._parent = self._parent

            new_chain._add(next_filter)
            return new_chain
        else:
            return self

    def _add[U](self, next_filter: BaseFilter[U] | None) -> "FilterChain[U]":
        """
        Adds a Filter to the collection directly.
        """
        resolved = self.resolve(next_filter, parent=self)
        if resolved:
            self._filters.append(resolved)

        return typing.cast(FilterChain[U], self)

    def _apply(self, value: typing.Any) -> T:
        for f in self._filters:
            value = self._filter(value, f)

        # If we get here, the incoming value should have been transformed to the correct
        # type.
        return typing.cast(T, value)

    def _apply_none(self) -> None:
        self._apply(None)


class BaseFilterError(ValueError):
    """
    Base class for errors that occur when filtering values.
    """

    def __init__(
        self,
        filter_: BaseFilter[typing.Any],
        value: typing.Any,
        code: str,
        context: typing.Mapping[str, typing.Any] | None = None,
    ):
        """
        :param filter_:
            The filter that raised the error.

        :param value:
            The value provided to the filter.

        :param code:
            Corresponding error code. Should match one of the keys in
            ``filter_.templates``.

        :param context:
            Additional values that could be useful for troubleshooting cases where the
            filter is incorrectly rejecting values.
        """
        super().__init__()

        self.filter: BaseFilter[typing.Any] = filter_
        self.value: typing.Any = value
        self.reason: str = code

        self.context: dict[str, typing.Any] = {}
        self.context.update(context or {})

    def __str__(self) -> str:
        """
        Returns formatted error message.
        """
        try:
            return self.filter.templates[self.reason]
        except KeyError:
            return self.reason


class FilterError(BaseFilterError):
    """
    Indicates that a given value could not be filtered because it failed validation or
    was otherwise invalid, rather than because of a problem with the filter code itself.

    Think of a ``FilterError`` like an HTTP 400 response.
    """

    def __init__(
        self,
        filter_: BaseFilter[typing.Any],
        value: typing.Any,
        code: str,
        context: typing.Mapping[str, typing.Any] | None = None,
        template_vars: typing.Mapping[str, str] | None = None,
    ):
        """
        :param filter_:
            The filter that raised the error.

        :param value:
            The value provided to the filter.

        :param code:
            Corresponding error code. Should match one of the keys in
            ``filter_.templates``.

        :param context:
            Additional values that could be useful for troubleshooting cases where the
            filter is incorrectly rejecting values.

        :param template_vars:
            If ``reason`` contains interpolation placeholders, this parameter contains
            the corresponding values to insert.
        """
        super().__init__(filter_, value, code, context)

        self.template_vars: dict[str, str] = {}
        self.template_vars.update(template_vars or {})

    def __str__(self) -> str:
        """
        Returns the formatted error message.
        """
        try:
            message = self.filter.templates[self.reason]
        except KeyError:
            message = self.reason

        return message.format(**self.template_vars)


class UncaughtException(BaseFilterError):
    """
    Indicates that a given value could not be filtered because of a problem with the
    filter code itself.

    Thin of ``UncaughtException`` like an HTTP 500 response.
    """

    def __init__(
        self,
        filter_: BaseFilter[typing.Any],
        value: typing.Any,
        e: Exception,
        context: typing.Mapping[str, typing.Any] | None = None,
    ):
        """
        :param filter_:
            The filter that raised the error.

        :param value:
            The value provided to the filter.

        :param e:
            The exception object.

        :param context:
            Additional values that could be useful for troubleshooting the error.
        """
        # Include context vars attached to the exception if applicable, and anything in
        # ``context`` trumps all.
        context_: dict[str, typing.Any] = {}
        context_.update(getattr(e, "context", {}))
        context_.update(context or {})

        super().__init__(
            filter_=filter_,
            value=value,
            code=BaseFilter.CODE_EXCEPTION,
            context=context_,
        )


class FilterHarness(ABC):
    """
    Runs filters within a harness, so that it can catch and handle errors.
    """

    @abstract_method
    def handle_filter_error(self, e: BaseFilterError) -> typing.Any:
        """
        Handles a filter error (i.e. invalid incoming value).

        :return: Replacement value that the filter should return (usually ``None``).
        """
        raise NotImplementedError(
            "Not implemented in {cls}.".format(cls=type(self).__name__),
        )

    def handle_exception(self, e: UncaughtException) -> typing.Any:
        """
        Handles an uncaught exception that occurred when the filter ran.

        :return: Replacement value that the filter should return (usually ``None``).
        """
        raise


class NoOp[T](BaseFilter[T]):
    """
    Filter that does nothing, used when you need a placeholder Filter in a FilterChain.
    """

    def _apply(self, value: typing.Any) -> T:
        # Assume that whatever got passed in is valid.
        return typing.cast(T, value)


# This filter is used extensively by other filters.
# To avoid lots of needless circular import hacks, we'll put it in the base module.
class Type[T](BaseFilter[T]):
    """
    Checks the type of the incoming value.
    """

    CODE_WRONG_TYPE = "wrong_type"

    templates = {
        CODE_WRONG_TYPE: "{incoming} is not valid (allowed types: {allowed}).",
    }

    def __init__(
        self,
        allowed_types: type | tuple[type, ...],
        allow_subclass: bool = True,
    ) -> None:
        """
        :param allowed_types:
            The type (or types) that incoming values are allowed to have.

        :param allow_subclass:
            Whether to allow subclasses when checking for type matches.
        """
        super().__init__()

        # A pinch of syntactic sugar.
        self.allowed_types = (
            allowed_types if isinstance(allowed_types, tuple) else (allowed_types,)
        )
        self.allow_subclass = allow_subclass

    def __str__(self) -> str:
        return "{type}({allowed_types}, allow_subclass={allow_subclass!r})".format(
            type=type(self).__name__,
            allowed_types=self.allowed_types,
            allow_subclass=self.allow_subclass,
        )

    def _apply(self, value: typing.Any) -> T:
        valid = (
            isinstance(value, self.allowed_types)
            if self.allow_subclass
            else (type(value) in self.allowed_types)
        )

        if not valid:
            raise FilterError(
                filter_=self,
                value=value,
                code=self.CODE_WRONG_TYPE,
                template_vars={
                    "incoming": self.get_type_name(type(value)),
                    "allowed": ", ".join(map(self.get_type_name, self.allowed_types)),
                },
            )

        return typing.cast(T, value)

    @staticmethod
    def get_type_name(type_: type) -> str:
        """
        Returns the name of the specified type.
        """
        # Depending on the type, it may require a bit of creativity to find the proper
        # name.
        # https://bugs.python.org/issue34422
        possible_names = [
            getattr(type_, "_name", None),
            getattr(type_, "__name__", None),
            str(type_),
        ]

        return next(filter(None, possible_names))
