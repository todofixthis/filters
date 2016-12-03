# coding=utf-8
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abc import ABCMeta, abstractmethod as abstract_method
from copy import copy
from functools import partial, WRAPPER_ASSIGNMENTS
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Text,
    Tuple,
    Union,
)
from weakref import ProxyTypes, proxy

from six import (
    binary_type,
    python_2_unicode_compatible,
    with_metaclass,
    text_type,
)

from filters import FilterCompatible
from filters.handlers import (
    BaseInvalidValueHandler,
    ExceptionHandler,
    FilterError,
)

__all__ = [
    'BaseFilter',
    'FilterChain',
    'Type',
    'filter_macro',
]


class FilterMeta(ABCMeta):
    """Metaclass for Filters."""
    # noinspection PyShadowingBuiltins
    def __init__(cls, what, bases=None, dict=None):
        super(FilterMeta, cls).__init__(what, bases, dict)

        if not hasattr(cls, 'templates'):
            cls.templates = {}

        # Copy error templates from base class to derived class, but
        #   in the event of a conflict, preserve the derived class'
        #   template.
        templates = {}
        for base in bases:
            if isinstance(base, FilterMeta):
                templates.update(base.templates)

        if templates:
            templates.update(cls.templates)
            cls.templates = templates

    def __or__(self, next_filter):
        # type: (FilterCompatible) -> FilterChain
        """
        Convenience alias for adding a Filter with default
            configuration to a FilterChain.

        E.g., the following statements do the same thing:

            Int | Max(32)   # FilterMeta.__or__
            Int() | Max(32) # Filter.__or__

        :see: http://stackoverflow.com/a/10773232
        """
        return FilterChain(self) | next_filter


@python_2_unicode_compatible
class BaseFilter(with_metaclass(FilterMeta)):
    """Base functionality for all Filters, macros, etc."""
    CODE_EXCEPTION = 'exception'

    templates = {
        CODE_EXCEPTION: 'An error occurred while processing this value.',
    }

    def __init__(self):
        super(BaseFilter, self).__init__()

        self._parent = None # type: BaseFilter
        self._handler = None # type: BaseInvalidValueHandler
        self._key = None # type: Text

        #
        # Indicates whether the Filter detected any invalid values.
        #   It gets reset every time `apply` gets called.
        #
        # Note that this attribute is intended to be used internally;
        #   external code should instead interact with invalid value
        #   handlers such as LogHandler and MemoryHandler.
        #
        # :see: importer.core.filters.handlers
        #
        self._has_errors = False

    @classmethod
    def __copy__(cls, the_filter):
        # type: (BaseFilter) -> BaseFilter
        """
        Creates a shallow copy of the object.
        :see: copy.copy
        """
        new_filter = type(the_filter)() # type: BaseFilter

        new_filter._parent  = the_filter._parent
        new_filter._key     = the_filter._key
        new_filter._handler = the_filter._handler

        return new_filter

    def __or__(self, next_filter):
        # type: (FilterCompatible) -> FilterChain
        """
        Chains a Filter with this one.
        """
        normalized = self._normalize(next_filter)

        if normalized:
            #
            # Officially, we should do this:
            # return FilterChain(self) | next_filter
            #
            # But that wastes some CPU cycles by creating an extra
            #   FilterChain instance that gets thrown away almost
            #   immediately. It's a bit faster just to create a single
            #   FilterChain instance and modify it in-place.
            #
            # noinspection PyProtectedMember
            return FilterChain(self)._add(next_filter)
        else:
            return self

    def __str__(self):
        """
        Returns a string representation of the Filter.

        Note that the output of this method does not necessarily match
            the signature of the Filter's `__init__` method; rather,
            its purpose is to provide a snapshot of critical parts of
            the Filter's configuration for e.g., troubleshooting
            purposes.
        """
        return '{type}()'.format(
            type = type(self).__name__,
        )

    @property
    def parent(self):
        # type: () -> Optional[BaseFilter]
        """Returns the parent Filter."""
        # Make sure `self._parent` hasn't gone away.
        try:
            self._parent.__class__
        except ReferenceError:
            return None

        return self._parent

    @parent.setter
    def parent(self, parent):
        # type: (BaseFilter) -> None
        """Sets the parent Filter."""
        # Create a weakref to the parent Filter to prevent annoying the
        #   garbage collector.
        self._parent = (
            (parent if isinstance(parent, ProxyTypes) else proxy(parent))
                if parent
                else None
        )

    @property
    def key(self):
        # type: () -> Text
        """Returns the key associated with this Filter."""
        return self._make_key(self._key_parts)

    @key.setter
    def key(self, key):
        # type: (Text) -> None
        """Sets the key associated with this Filter."""
        self._key = key

    def sub_key(self, sub_key):
        # type: (Text) -> Text
        """
        Returns a copy of this Filter's key with an additional sub-key
            appended.
        """
        return self._make_key(self._key_parts + [sub_key])

    @property
    def _key_parts(self):
        # type: () -> List[Text]
        """Assembles each key part in the Filter hierarchy."""
        key_parts = []

        # Iterate up the parent chain and collect key parts.
        # Alternatively, we could just get `self.parent._key_parts`,
        #   but that is way less efficient.
        parent = self
        while parent:
            # As we move up the chain, push key parts onto the front of
            #   the path (otherwise the key parts would be in reverse
            #   order).
            key_parts.insert(0, parent._key)
            parent = parent.parent

        return key_parts

    @property
    def handler(self):
        # type: () -> BaseInvalidValueHandler
        """Returns the invalid value handler for the filter."""
        if self._handler is None:
            # Attempt to return the parent filter's handler...
            try:
                return self.parent.handler
            except AttributeError:
                #
                # ... unless this filter has no parent, in which case
                #   it should use the default.
                #
                # Note that we do not set `self._handler`, in case the
                #   filter later gets added to e.g., a FilterChain that
                #   has a different invalid value handler set.
                #
                return ExceptionHandler()

        return self._handler

    @handler.setter
    def handler(self, handler):
        # type: (BaseInvalidValueHandler) -> None
        """Sets the invalid value handler for the filter."""
        self._handler = handler

    def set_handler(self, handler):
        # type: (BaseInvalidValueHandler) -> BaseFilter
        """
        Cascading method for setting the filter's invalid value
            handler.
        """
        self.handler = handler
        return self

    def apply(self, value):
        """
        Applies the Filter to a value.

        :param value: The value to check, before any transformations
            have been applied to it.

        :return: The value after the Filter is applied (usually the
            same value that was passed in).
        """
        self._has_errors = False

        try:
            return self._apply_none() if value is None else self._apply(value)
        except Exception as e:
            return self._invalid_value(value, e, exc_info=True)

    @abstract_method
    def _apply(self, value):
        """
        Applies Filter-specific logic to a value.

        Note:  It is safe to assume that `value` is not None when this
            method is invoked.
        """
        raise NotImplementedError(
            'Not implemented in {cls}.'.format(cls=type(self).__name__),
        )

    def _apply_none(self):
        """Applies Filter-specific logic when the value is `None`."""
        return None

    def _filter(self, value, filter_chain, sub_key=None):
        # type: (Any, FilterCompatible) -> Any
        """
        Applies a Filter to a value in the same context as the current
            Filter.

        :param sub_key: Appended to the `key` value in the error
            message context (used by complex Filters).

        :see: _invalid_value
        """
        filter_chain = self._normalize(filter_chain, parent=self, key=sub_key)

        # In rare cases, `filter_chain` may be `None`.
        # :see: importer.core.filters.complex.FilterMapper#__init__
        if filter_chain:
            try:
                filtered = filter_chain.apply(value)
            except Exception as e:
                return self._invalid_value(value, e, exc_info=True)
            else:
                self._has_errors = self._has_errors or filter_chain._has_errors
                return filtered
        else:
            return value

    def _invalid_value(
            self,
            value,
            reason,
            replacement     = None,
            exc_info        = False,
            context         = None,
            sub_key         = None,
            template_vars   = None,
    ):
        # type: (Any, Union[Text, Exception], Any, bool, Optional[dict], Optional[Text], Optional[dict]) -> Any
        """
        Handles an invalid value.

        This method works as both a logging method and an exception
            handler.

        :param replacement: The replacement value to use instead.

        :param sub_key: Appended to the `key` value in the error
            message context (used by complex Filters).

        :return: Alternate value to use (not applicable if this method
            raises an exception).
        """
        handler = self.handler

        if isinstance(reason, FilterError):
            # FilterErrors should be sent directly to the handler.
            # This allows complex Filters to properly catch and handle
            #   FilterErrors raised by the Filters they control.
            return handler.handle_invalid_value(
                message     = text_type(reason),
                exc_info    = True,
                context     = getattr(reason, 'context', {}),
            )

        self._has_errors = True

        if not context:
            context = {}

        context['value']        = value
        context['filter']       = text_type(self)
        context['key']          = self.sub_key(sub_key)
        context['replacement']  = replacement

        if not template_vars:
            template_vars = {}

        template_vars.update(context)

        if isinstance(reason, Exception):
            # Store the error code in the context so that the caller
            #   can identify the error type without having to parse the
            #   rendered error message template.
            context['code'] = self.CODE_EXCEPTION

            # Store exception details in the context so that they are
            #   accessible to devs but hidden from end users.
            # Note that the traceback gets processed separately,
            context['exc'] = '[{mod}.{cls}] {msg}'.format(
                mod = type(reason).__module__,
                cls = type(reason).__name__,
                msg = text_type(reason),
            )

            # Add the context to the exception object so that loggers
            #   can use it.
            if not hasattr(reason, 'context'):
                reason.context = {}
            reason.context.update(context)

            handler.handle_exception(
                message = self._format_message(context['code'], template_vars),
                exc     = reason,
            )
        else:
            # Store the error code in the context so that the caller
            #   can identify the error type without having to parse the
            #   rendered error message template.
            context['code'] = reason

            handler.handle_invalid_value(
                message     = self._format_message(reason, template_vars),
                exc_info    = exc_info,
                context     = context,
            )

        return replacement

    def _format_message(self, key, template_vars):
        # type: (Text, Dict[Text, Text]) -> Text
        """Formats a message for the invalid value handler."""
        return self.templates[key].format(**template_vars)

    @classmethod
    def _normalize(cls, the_filter, parent=None, key=None):
        # type: (FilterCompatible, Optional[BaseFilter], Optional[Text]) -> Optional[FilterChain]
        """
        Converts a Filter-compatible value into a consistent type.
        """
        if the_filter is not None:
            if isinstance(the_filter, BaseFilter):
                normalized = the_filter

            elif callable(the_filter):
                normalized = cls._normalize(the_filter())

            # Uhh... hm.
            else:
                raise TypeError(
                    '{type} {value!r} is not '
                    'compatible with {target}.'.format(
                        type    = type(the_filter).__name__,
                        value   = the_filter,
                        target  = cls.__name__,
                    ),
                )

            if parent:
                normalized.parent = parent

            if key:
                normalized.key = key

            return normalized

    @staticmethod
    def _make_key(key_parts):
        # type: (Iterable[Text]) -> Text
        """Assembles a dotted key value from its component parts."""
        return '.'.join(filter(None, key_parts))


@python_2_unicode_compatible
class FilterChain(BaseFilter):
    """
    Allows you to chain multiple Filters together so that they are
        treated as a single Filter.
    """
    def __init__(self, start_filter=None):
        # type: (FilterCompatible) -> None
        super(FilterChain, self).__init__()

        self._filters = [] # type: List[BaseFilter]

        self._add(start_filter)

    def __str__(self):
        return '{type}({filters})'.format(
            type    = type(self).__name__,
            filters = ' | '.join(map(text_type, self._filters)),
        )

    def __or__(self, next_filter):
        # type: (FilterCompatible) -> FilterChain
        """
        Chains a Filter with this one.

        This method creates a new FilterChain object without modifying
            the current one.

        :see: importer.core.filters.FilterChain#add
        """
        normalized = self._normalize(next_filter)

        if normalized:
            new_chain = copy(self) # type: FilterChain
            new_chain._add(next_filter)
            return new_chain
        else:
            return self

    @classmethod
    def __copy__(cls, the_filter):
        # type: (FilterChain) -> FilterChain
        """
        Creates a shallow copy of the object.

        :see: copy.copy
        """
        new_filter = super(FilterChain, cls).__copy__(the_filter) # type: FilterChain
        new_filter._filters = the_filter._filters[:]
        return new_filter

    def _add(self, next_filter):
        # type: (FilterCompatible) -> FilterChain
        """
        Adds a Filter to the collection directly.

        :see: importer.core.filters.Filter#__or__
        """
        normalized = self._normalize(next_filter, parent=self)
        if normalized:
            self._filters.append(normalized)

        return self

    def _apply(self, value):
        for f in self._filters:
            value = self._filter(value, f)

            # FilterChains stop at the first sign of trouble.
            # This is important because FilterChains have to behave
            #   consistently regardless of whether the invalid value
            #   handler raises an exception.
            if self._has_errors:
                break

        return value

    def _apply_none(self):
        return self._apply(None)


def filter_macro(func, *args, **kwargs):
    """
    Promotes a function that returns a Filter into its own Filter type.

    Example:

        @filter_macro
        def String():
            return Unicode | Strip | NotEmpty

        # You can now use `String` anywhere you would use a regular Filter:
        (String | Split(':')).apply('...')

    You can also use `filter_macro` to create partials, allowing you to
        preset one or more initialization arguments:

        Minor = filter_macro(Max, max_value=18, inclusive=False)
        Minor.apply(42)
    """
    filter_partial = partial(func, *args, **kwargs)

    class FilterMacroMeta(FilterMeta):
        @staticmethod
        def __new__(mcs, name, bases, attrs):
            # This is as close as we can get to running
            #   `update_wrapper` on a type.
            for attr in WRAPPER_ASSIGNMENTS:
                if hasattr(func, attr):
                    attrs[attr] = getattr(func, attr)

            # Note that we ignore the `name` argument, passing in
            #   `func.__name__` instead.
            return super(FilterMacroMeta, mcs)\
                .__new__(mcs, func.__name__, bases, attrs)

        def __call__(cls, *runtime_args, **runtime_kwargs):
            return filter_partial(*runtime_args, **runtime_kwargs)

    class FilterMacro(with_metaclass(FilterMacroMeta, BaseFilter)):
        # This method will probably never get called due to overloaded
        #   `__call__` in the metaclass, but just in case, we'll
        #   include it because it is an abstract method in `BaseFilter`.
        def _apply(self, value):
            return self.__class__()._apply(value)

    return FilterMacro


# Used by Type to use JSON data types instead of Python type names in
#   error messages.
# :see: Type.__init__
JSON_ALIASES = {
    # Builtins
    bool:           'Boolean',
    dict:           'Object',
    float:          'Number',
    int:            'Number',
    list:           'Array',

    # Compat
    binary_type:    'String',
    text_type:      'String',

    # Typing
    Mapping:        'Array',
    Sequence:       'Array',
}


# This filter is used extensively by other filters.
# To avoid lots of needless "circular import" hacks, we'll put it in
#   the base module.
@python_2_unicode_compatible
class Type(BaseFilter):
    """Checks the type of a value."""
    CODE_WRONG_TYPE = 'wrong_type'

    templates = {
        CODE_WRONG_TYPE:
            '{incoming} is not valid (allowed types: {allowed}).',
    }

    def __init__(self, allowed_types, allow_subclass=True, aliases=None):
        # type: (Union[type, Tuple[type]], bool, Optional[Mapping[type, Text]]) -> None
        """
        :param allowed_types: The type (or types) that filtered values
            are allowed to have.

        :param allow_subclass: Whether to allow subclasses when
            checking for type matches.

        :param aliases: Aliases to use for type names in error
            messages.  This is useful for providing more context-
            appropriate names to end users and/or masking native Python
            type names.
        """
        super(Type, self).__init__()

        # A pinch of syntactic sugar.
        self.allowed_types  = (
            allowed_types
                if isinstance(allowed_types, tuple)
                else (allowed_types,)
        )
        self.allow_subclass = allow_subclass

        self.aliases = aliases or {}

    def __str__(self):
        return (
            '{type}({allowed_types}, '
            'allow_subclass={allow_subclass!r})'.format(
                type            = type(self).__name__,
                allowed_types   = self.get_allowed_type_names(aliased=False),
                allow_subclass  = self.allow_subclass,
            )
        )

    def _apply(self, value):
        valid = (
            isinstance(value, self.allowed_types)
                if self.allow_subclass
                else (type(value) in self.allowed_types)
        )

        if not valid:
            return self._invalid_value(
                value   = value,
                reason  = self.CODE_WRONG_TYPE,

                template_vars = {
                    'incoming': self.get_type_name(type(value)),
                    'allowed':  self.get_allowed_type_names(),
                },
            )

        return value

    def get_allowed_type_names(self, aliased=True):
        # type: (bool) -> Text
        """Returns a string with all the allowed types."""
        # Note that we cast as a set in the middle, to ferret out
        #   duplicates.
        return ', '.join(sorted({
            self.get_type_name(t, aliased)
                for t in self.allowed_types
        }))

    def get_type_name(self, type_, aliased=True):
        # type: (type, bool) -> Text
        """Returns the name of the specified type."""
        return (
            (self.aliases.get(type_) or type_.__name__)
                if aliased
                else type_.__name__
        )
