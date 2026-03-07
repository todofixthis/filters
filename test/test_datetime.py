"""
Tests for the Datetime filter.
"""

from datetime import date, datetime

from dateutil.tz import tzoffset
from pytz import utc

import filters as f


def test_datetime_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use `Required | Datetime` if you want to reject null values.
    """
    assert_filter_passes(f.Datetime(), None)


def test_datetime_pass_naive_timestamp(assert_filter_passes):
    """
    The incoming value is a naive timestamp (does not include timezone
    info).
    """
    assert_filter_passes(
        f.Datetime(),
        "2015-05-11 14:56:58",
        datetime(2015, 5, 11, 14, 56, 58, tzinfo=utc),
    )


def test_datetime_pass_aware_timestamp(assert_filter_passes):
    """
    The incoming value is a timestamp that includes timezone info.
    """
    assert_filter_passes(
        f.Datetime(),
        # Note that the value we are parsing is 5 hours behind UTC.
        "2015-05-11T14:56:58-0500",
        datetime(2015, 5, 11, 19, 56, 58, tzinfo=utc),
    )


def test_datetime_pass_naive_timestamp_default_timezone(assert_filter_passes):
    """
    The incoming value is a naive timestamp, but the filter is configured
    not to treat naive timestamps as UTC.
    """
    assert_filter_passes(
        # The incoming value is a naive timestamp, and the filter is
        # configured to use UTC+8 by default.
        f.Datetime(timezone=tzoffset("UTC+8", 8 * 3600)),
        "2015-05-12 09:20:03",
        # The resulting datetime is still converted to UTC.
        datetime(2015, 5, 12, 1, 20, 3, tzinfo=utc),
    )


def test_datetime_pass_aware_timestamp_default_timezone(assert_filter_passes):
    """
    The filter's default timezone has no effect if the incoming value
    already contains timezone info.
    """
    assert_filter_passes(
        # The incoming value is UTC+4, but the filter is configured to use
        # UTC-1 by default.
        f.Datetime(timezone=tzoffset("UTC-1", -1 * 3600)),
        "2015-05-11T21:14:38+04:00",
        # The incoming values timezone info is used instead of the default.
        # Note that the resulting datetime is still converted to UTC.
        datetime(2015, 5, 11, 17, 14, 38, tzinfo=utc),
    )


def test_datetime_pass_alternate_timezone_syntax(assert_filter_passes):
    """
    When setting the default timezone for the filter, you can use an
    int/float offset (number of hours from UTC) instead of a tzoffset
    object.
    """
    assert_filter_passes(
        # Note that we use an int value instead of constructing a tzoffset
        # for ``timezone``.
        f.Datetime(timezone=3),
        "2015-05-11 21:14:38",
        datetime(2015, 5, 11, 18, 14, 38, tzinfo=utc),
    )


def test_datetime_pass_datetime_utc(assert_filter_passes):
    """
    The incoming value is a datetime object that is already set to UTC.
    """
    assert_filter_passes(f.Datetime(), datetime(2015, 6, 27, 10, 5, 48, tzinfo=utc))


def test_datetime_pass_datetime_non_utc(assert_filter_passes):
    """
    The incoming value is a datetime object that is already set to a
    non-UTC timezone.
    """
    assert_filter_passes(
        f.Datetime(),
        datetime(2015, 6, 27, 10, 6, 32, tzinfo=tzoffset("UTC-5", -5 * 3600)),
        datetime(2015, 6, 27, 15, 6, 32, tzinfo=utc),
    )


def test_datetime_naive(assert_filter_passes):
    """
    The incoming value is a datetime object that does not have timezone
    info.
    """
    assert_filter_passes(
        # The filter is configured to assume UTC-3 if the incoming value
        # has no timezone info.
        f.Datetime(timezone=-3),
        datetime(2015, 6, 27, 18, 7, 18),
        datetime(2015, 6, 27, 21, 7, 18, tzinfo=utc),
    )


def test_datetime_pass_date(assert_filter_passes):
    """
    The incoming value is a date object.
    """
    assert_filter_passes(
        # The filter is configured to assume UTC+12 if the incoming value
        # has no timezone info.
        f.Datetime(timezone=12),
        date(2015, 6, 27),
        datetime(2015, 6, 26, 12, 0, 0, tzinfo=utc),
    )


def test_datetime_return_naive_datetime(assert_filter_passes):
    """
    You can configure the filter to return a naive datetime object (e.g.,
    for storing in a database).

    Note that the datetime is still converted to UTC before its tzinfo is
    removed.
    """
    assert_filter_passes(
        f.Datetime(
            # Note that we pass `naive=True` to the filter's initialiser.
            naive=True,
        ),
        datetime(
            2015,
            7,
            1,
            9,
            22,
            10,
            tzinfo=tzoffset("UTC-5", -5 * 3600),
        ),
        # The resulting datetime is converted to UTC before its timezone
        # info is stripped.
        datetime(2015, 7, 1, 14, 22, 10, tzinfo=None),
    )


def test_datetime_fail_invalid_value(assert_filter_errors):
    """
    The incoming value cannot be parsed as a datetime.
    """
    assert_filter_errors(
        f.Datetime(),
        "this is not a datetime",  # nor is it a pipe
        [f.Datetime.CODE_INVALID],
    )
