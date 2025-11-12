import sys
from collections.abc import MutableMapping
from logging import ERROR, Logger, LoggerAdapter
from traceback import format_exc
from types import TracebackType
from typing import Any

from filters.base import BaseFilter, BaseInvalidValueHandler, FilterCompatible

__all__ = [
    "FilterMessage",
    "FilterRunner",
    "LogHandler",
    "MemoryHandler",
]


class LogHandler(BaseInvalidValueHandler):
    """Invalid value handler that sends the details to a logger."""

    def __init__(
        self,
        logger: Logger | LoggerAdapter,
        level: int = ERROR,
    ) -> None:
        """Initialises the LogHandler.

        Args:
            logger: The logger that log messages will get sent to.
            level: Level of the logged messages.
        """
        super().__init__()

        self.logger = logger
        self.level = level

    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: MutableMapping,
    ) -> None:
        self.logger.log(
            level=self.level, msg=message, exc_info=exc_info, extra={"context": context}
        )


class FilterMessage(object):
    """Provides a consistent API for messages sent to MemoryHandler."""

    def __init__(
        self,
        message: str,
        context: MutableMapping,
        exc_info: str | None = None,
    ) -> None:
        """Initialises the FilterMessage.

        Args:
            message: The error message.
            context: The context mapping.
            exc_info: Exception traceback (if applicable).
        """
        super().__init__()

        self.message = message
        self.context = context
        self.code = context.get("code") or message
        self.exc_info = exc_info

    def __repr__(self):
        return "{type}({message}, {context})".format(
            type=type(self).__name__,
            message=repr(self.message),
            context=repr(self.context),
        )

    def __str__(self):
        return self.message

    def as_dict(self, with_debug_info: bool = False) -> dict:
        """Returns a dict representation of the FilterMessage.

        Args:
            with_debug_info: Whether to include context and exception
                traceback in the result.

        Returns:
            Dict representation with code and message, and optionally
            context and exc_info if with_debug_info is True.
        """
        res = {
            "code": self.code,
            "message": self.message,
        }

        if with_debug_info:
            res["context"] = self.context
            res["exc_info"] = self.exc_info

        return res


class MemoryHandler(BaseInvalidValueHandler):
    """Invalid value handler that stores messages locally."""

    def __init__(self, capture_exc_info: bool = False) -> None:
        """Initialises the MemoryHandler.

        Args:
            capture_exc_info: Whether to capture `sys.exc_info` when
                handling an exception.

                This is turned off by default to reduce memory usage,
                but it is useful in certain cases (e.g., if you want to
                send exceptions to a logger that expect exc_info).

                Regardless, you can still check ``self.has_exceptions``
                to see if an exception occurred.
        """
        super().__init__()

        self.messages: dict[str, list[FilterMessage]] = {}
        self.has_exceptions = False
        self.capture_exc_info = capture_exc_info
        self.exc_info: list[tuple[type, Exception, TracebackType]] = []

    def handle_invalid_value(
        self,
        message: str,
        exc_info: bool,
        context: MutableMapping,
    ) -> None:
        key = context.get("key", "")
        msg = FilterMessage(
            message=message,
            context=context,
            exc_info=format_exc() if exc_info else None,
        )

        try:
            self.messages[key].append(msg)
        except KeyError:
            self.messages[key] = [msg]

    def handle_exception(
        self,
        message: str,
        exc: Exception,
    ) -> Any:
        self.has_exceptions = True

        if self.capture_exc_info:
            self.exc_info.append(sys.exc_info())

        return super().handle_exception(message, exc)


class FilterRunner(object):
    """Wrapper for a filter that provides an API similar to what you would
    expect from a Django form -- at least, when it comes to methods
    related to data validation :)
    """

    def __init__(
        self,
        starting_filter: FilterCompatible,
        incoming_data: Any = None,
        capture_exc_info: bool = False,
    ) -> None:
        """Initialises the FilterRunner.

        Args:
            starting_filter: The filter to run.
            incoming_data: E.g., ``request.POST``.
            capture_exc_info: Whether to capture ``sys.exc_info`` when
                handling an exception.

                This is turned off by default to reduce memory usage,
                but it is useful in certain cases (e.g., if you want to
                send exceptions to a logger).

                Regardless, you can still check ``self.has_exceptions``
                to see if an exception occurred.
        """
        super().__init__()

        self.filter_chain = BaseFilter.resolve_filter(starting_filter)
        self.data = incoming_data
        self.capture_exc_info = capture_exc_info

        self._cleaned_data = None
        self._handler: MemoryHandler | None = None

    def __str__(self):
        return str(self.filter_chain)

    def apply(self, incoming_data: Any):
        """Reruns the filter chain against a new value.

        Args:
            incoming_data: The new value to filter.
        """
        self.data = incoming_data

        self._cleaned_data = None
        self._handler = None

    @property
    def cleaned_data(self):
        """Returns the resulting value after applying the filter.

        Returns:
            The resulting value after applying the request filter.
        """
        self.full_clean()
        return self._cleaned_data

    @property
    def errors(self) -> dict[
        str,
        list[dict[str, str]],
    ]:
        """Returns a dict of error messages generated by the Filter.

        The format is suitable for inclusion in e.g., a 400 Bad Request
        response payload.

        Example::

            {
                'authToken': [
                    {
                        'code':     'not_found',
                        'message':
                            'No AuthToken found matching this value.',
                    },
                ],

                'data.foobar': [
                    {
                        'code':     'unexpected',
                        'message':  'Unexpected key "foobar".',
                    },
                ],

                # etc.
            }

        Returns:
            Dict mapping keys to lists of error dicts.
        """
        return self.get_errors()

    def get_errors(
        self,
        with_context: bool = False,
    ) -> dict[
        str,
        list[dict[str, str]],
    ]:
        """Returns a dict of error messages generated by the Filter.

        The format is suitable for inclusion in e.g., a 400 Bad Request
        response payload.

        Args:
            with_context: Whether to include the context object in the
                result (for debugging purposes).

                Note: context is usually not safe to expose to clients!

        Returns:
            Dict mapping keys to lists of error dicts.
        """
        return {
            key: [m.as_dict(with_context) for m in messages]
            for key, messages in self.filter_messages.items()
        }

    @property
    def error_codes(self) -> dict[
        str,
        list[str],
    ]:
        """Returns a dict of error codes generated by the Filter.

        Returns:
            Dict mapping keys to lists of error codes.
        """
        return {
            key: [m.code for m in messages]
            for key, messages in self.filter_messages.items()
        }

    @property
    def has_exceptions(self) -> bool:
        """Returns whether any unhandled exceptions occurred.

        Returns:
            Whether any unhandled exceptions occurred while filtering
            the value.
        """
        self.full_clean()
        return self._handler.has_exceptions

    @property
    def exc_info(self) -> list[tuple[type, Exception, TracebackType]]:
        """Returns tracebacks from any exceptions that were captured.

        Returns:
            List of exception info tuples (type, exception, traceback).
        """
        self.full_clean()
        return self._handler.exc_info

    @property
    def filter_messages(self) -> dict[
        str,
        list[FilterMessage],
    ]:
        """Returns the raw FilterMessages generated by the Filter.

        Returns:
            Dict mapping keys to lists of FilterMessage objects.
        """
        self.full_clean()
        return self._handler.messages

    def is_valid(self) -> bool:
        """Returns whether the payload successfully passed the Filter.

        Returns:
            True if no filter messages were generated, False otherwise.
        """
        return not self.filter_messages

    def full_clean(self):
        """Applies the filter to the request data."""
        if self._handler is None:
            self._handler = MemoryHandler(self.capture_exc_info)

            # Inject our own handler (temporarily) while the Filter runs, so we
            # can capture error messages.
            prev_handler = self.filter_chain.handler
            self.filter_chain.handler = self._handler
            try:
                self._cleaned_data = self.filter_chain.apply(self.data)
            finally:
                self.filter_chain.handler = prev_handler
