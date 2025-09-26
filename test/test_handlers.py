"""
Tests for the error handlers.
"""

import logging
import sys
import typing
from logging import WARNING, getLevelName
from traceback import format_exc, format_exception

import pytest

import filters as f
from filters.base import ExceptionHandler


def test_filter_runner_apply():
    """
    Calling a FilterRunner's ``apply()`` method reruns its filter chain
    against the specified input.
    """
    runner = f.FilterRunner(f.Int)
    assert runner.is_valid()
    assert runner.error_codes == {}
    assert runner.cleaned_data is None

    runner.apply("42")
    assert runner.is_valid()
    assert runner.error_codes == {}
    assert runner.cleaned_data == 42

    runner.apply("Not an int")
    assert not runner.is_valid()
    assert runner.error_codes == {"": [f.Decimal.CODE_INVALID]}

    # One more; make sure that the error messages from the invalid value
    # also get cleared out.
    runner.apply(86.0)
    assert runner.is_valid()
    assert runner.error_codes == {}
    assert runner.cleaned_data == 86


def test_exception_handler_invalid_value():
    """
    Sends an invalid value to the handler.
    """
    handler = ExceptionHandler()
    message = "Needs more cowbell."
    context = {
        "key": "test",
        "value": "(Don't Fear) The Reaper",
    }

    # When ExceptionHandler encounters an invalid value, it raises
    # an exception.
    # The exception always has the same type (FilterError) so that
    # the caller can capture it.
    with pytest.raises(f.FilterError) as exc:
        handler.handle_invalid_value(message, False, context)

    assert str(exc.value) == message
    assert exc.value.context == context


def test_exception_handler_exception():
    """
    Sends an exception to the handler.
    """
    handler = ExceptionHandler()
    message = "An exception occurred!"
    context = {
        "key": "test",
        "value": "(Don't Fear) The Reaper",
    }

    #
    # ExceptionHandler converts any exception it encounters into a
    # FilterError.
    # The exception always has the same type (FilterError) so that
    # the caller can capture it.
    #
    # Note that the FilterError completely replaces the original
    # exception, but it leaves the traceback intact.
    # To make things more convenient, Filters add the exception
    # info to the context dict, but you can still use
    # `sys.exc_info()[2]` to inspect the original exception's
    # stack.
    #
    # :see: importer.core.f.BaseFilter._invalid_value
    #
    try:
        # Raise an exception so that the handler has a traceback to
        # work with.
        # Note that the ValueError's message will get replaced (but
        # it can still be accessed via the traceback).
        exc = ValueError("Needs more cowbell.")
        exc.context = context
        raise exc
    except ValueError as e:
        with pytest.raises(f.FilterError) as ar_context:
            handler.handle_exception(message, e)

        assert str(ar_context.value) == message
        assert ar_context.value.context == context


class MemoryLogHandler(logging.Handler):
    """
    A log handler that retains all of its records in a list in memory,
    so that we can test :py:class:`LogHandler`.

    This class is similar in function (though not in purpose) to
    BufferingHandler.

    References:
      - :py:class:`logging.handlers.BufferingHandler`
    """

    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level)

        self._records = []  # type: typing.List[logging.LogRecord]
        self.max_level_emitted = logging.NOTSET

    def __getitem__(self, index: int) -> logging.LogRecord:
        """
        Returns the log message at the specified index.
        """
        return self._records[index]

    def __iter__(self) -> typing.Iterator[logging.LogRecord]:
        """
        Creates an iterator for the collected records.
        """
        return iter(self._records)

    def __len__(self):
        """
        Returns the number of log records collected.
        """
        return len(self._records)

    @property
    def records(self) -> typing.List[logging.LogRecord]:
        """
        Returns all log messages that the handler has collected.
        """
        return self._records[:]

    def clear(self):
        """
        Removes all log messages that this handler has collected.
        """
        del self._records[:]

    def emit(self, record: logging.LogRecord) -> None:
        """
        Records the log message.
        """
        # Remove `exc_info` to reclaim memory.
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = "".join(format_exception(*record.exc_info))

            record.exc_info = None

        self._records.append(record)
        self.max_level_emitted = max(self.max_level_emitted, record.levelno)


@pytest.fixture
def log_handler_setup():
    """Set up logger and handler for LogHandler tests."""
    logs = MemoryLogHandler()
    logger = logging.getLogger(__name__)
    logger.addHandler(logs)
    logger.setLevel(logging.DEBUG)
    handler = f.LogHandler(logger, WARNING)

    yield logs, handler

    # Cleanup
    logger.removeHandler(logs)


def test_log_handler_invalid_value(log_handler_setup):
    """
    Sends an invalid value to the handler.
    """
    logs, handler = log_handler_setup
    message = "Needs more cowbell."
    context = {
        "key": "test",
        "value": "(Don't Fear) The Reaper",
    }

    handler.handle_invalid_value(message, False, context)

    assert len(logs.records) == 1
    assert logs[0].msg == message
    assert getattr(logs[0], "context") == context

    # The log message level is set in the handler's initializer.
    assert logs[0].levelname == getLevelName(WARNING)

    # No exception info for invalid values (by default).
    assert logs[0].exc_text is None


def test_log_handler_exception(log_handler_setup):
    """
    Sends an exception to the handler.
    """
    logs, handler = log_handler_setup
    message = "An exception occurred!"
    context = {
        "key": "test",
        "value": "(Don't Fear) The Reaper",
    }

    try:
        # Raise an exception so that the handler has a traceback to
        # work with.
        # Note that the ValueError's message will get replaced (but
        # it can still be accessed via the traceback).
        exc = ValueError("Needs more cowbell.")
        exc.context = context
        raise exc
    except ValueError as e:
        original_traceback = format_exc()

        handler.handle_exception(message, e)

        assert len(logs.records) == 1
        assert logs[0].msg == message
        assert getattr(logs[0], "context") == context

        # The log message level is set in the handler's
        # initializer.
        # Note that both invalid values and exceptions have the
        # same log level.
        assert logs[0].levelname == getLevelName(WARNING)

        # Traceback is captured for exceptions.
        assert logs[0].exc_text == original_traceback


def test_memory_handler_invalid_value():
    """
    Sends an invalid value to the handler.
    """
    handler = f.MemoryHandler()
    code = "foo"
    key = "test"
    message = "Needs more cowbell."
    context = {
        "code": code,
        "key": key,
        "value": "(Don't Fear) The Reaper",
    }

    handler.handle_invalid_value(message, False, context)

    # Add a couple of additional messages, just to make sure the
    # handler stores them correctly.
    handler.handle_invalid_value(
        message="Test message 1",
        exc_info=False,
        context={"key": key},
    )
    handler.handle_invalid_value("Test message 2", False, {})

    # As filter messages are captured, they are sorted according to
    # their contexts' ``key`` values.
    # If a message doesn't have a ``key`` value, an empty string is
    # used.
    assert sorted(handler.messages.keys()) == ["", key]

    filter_message_0 = handler.messages[key][0]
    assert isinstance(filter_message_0, f.FilterMessage)
    assert filter_message_0.code == code
    assert filter_message_0.message == message
    assert filter_message_0.context == context
    assert filter_message_0.exc_info is None

    filter_message_1 = handler.messages[key][1]
    assert isinstance(filter_message_1, f.FilterMessage)
    assert filter_message_1.code == "Test message 1"
    assert filter_message_1.message == "Test message 1"
    assert filter_message_1.context == {"key": key}
    assert filter_message_1.exc_info is None

    filter_message_blank = handler.messages[""][0]
    assert isinstance(filter_message_blank, f.FilterMessage)
    assert filter_message_blank.code == "Test message 2"
    assert filter_message_blank.message == "Test message 2"
    assert filter_message_blank.context == {}
    assert filter_message_blank.exc_info is None

    assert not handler.has_exceptions
    assert handler.exc_info == []


def test_memory_handler_exception():
    """
    Sends an exception to the handler.
    """
    handler = f.MemoryHandler()
    code = "error"
    key = "test"
    message = "An exception occurred!"
    context = {
        "code": code,
        "key": key,
        "value": "(Don't Fear) The Reaper",
    }

    try:
        # Raise an exception so that the handler has a traceback to
        # work with.
        # Note that the ValueError's message will get replaced (but
        # it can still be accessed via the traceback).
        exc = ValueError("Needs more cowbell.")
        exc.context = context
        raise exc
    except ValueError as e:
        original_traceback = format_exc()

        handler.handle_exception(message, e)

        assert list(handler.messages.keys()) == [key]

        filter_message_0 = handler.messages[key][0]
        assert isinstance(filter_message_0, f.FilterMessage)
        assert filter_message_0.code == code
        assert filter_message_0.message == message
        assert filter_message_0.context == context

        # Exception traceback is captured automatically.
        assert filter_message_0.exc_info == original_traceback

        assert handler.has_exceptions

        # By default, the handler does NOT keep the traceback
        # object.
        # :see: test_capture_exc_info
        assert handler.exc_info == []


def test_memory_handler_capture_exc_info():
    """
    The handler is configured to capture :py:func:`sys.exc_info` in
    the event of an exception.

    This is generally turned off because the filter already
    captures a formatted traceback in the event of an
    exception, so there is no need to store the raw traceback
    object.

    However, there are a few cases where it is useful to collect
    this, such as when you want to send exceptions to a logger
    that expects `sys.exc_info()`.
    """
    handler = f.MemoryHandler()
    handler.capture_exc_info = True

    try:
        # Raise an exception so that the handler has a traceback to
        # work with.
        raise ValueError("I gotta have more cowbell, baby!")
    except ValueError as e:
        handler.handle_exception("An exception occurred!", e)

        assert handler.has_exceptions
        assert handler.exc_info == [sys.exc_info()]
