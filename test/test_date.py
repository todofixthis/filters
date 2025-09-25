from datetime import date, datetime

from dateutil.tz import tzoffset
from pytz import utc

import filters as f


def test_date_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use `Required | Date` if you want to reject null values.
    """
    assert_filter_passes(f.Date(), None)


def test_date_pass_naive_timestamp(assert_filter_passes):
    """
    The incoming value is a naive timestamp (no timezone info).
    """
    assert_filter_passes(
        f.Date(),
        "2015-05-11 14:56:58",
        date(2015, 5, 11),
    )


def test_date_pass_aware_timestamp(assert_filter_passes):
    """
    The incoming value includes timezone info.
    """
    assert_filter_passes(
        f.Date(),
        # Note that the value we are parsing is 5 hours behind UTC.
        "2015-05-11T19:56:58-05:00",
        # The resulting date appears to occur 1 day later because that's
        # the date according to UTC.
        date(2015, 5, 12),
    )


def test_date_pass_naive_timestamp_default_timezone(assert_filter_passes):
    """
    The incoming value is a naive timestamp, but the filter is configured
    not to treat naive timestamps as UTC.
    """
    assert_filter_passes(
        f.Date(
            # The filter is configured to parse naive timestamps as if they
            # are UTC+8.
            timezone=tzoffset("UTC+8", 8 * 3600),
        ),
        "2015-05-12 03:20:03",
        # The resulting date appears to occur 1 day earlier because the
        # filter subtracted 8 hours to convert the value to UTC.
        date(2015, 5, 11),
    )


def test_date_pass_aware_timestamp_default_timezone(assert_filter_passes):
    """
    The filter's default timezone has no effect if the incoming value
    already contains timezone info.
    """
    assert_filter_passes(
        # The incoming timestamp is from UTC+4, but the filter is
        # configured to use UTC-11 by default.
        f.Date(timezone=tzoffset("UTC-11", -11 * 3600)),
        "2015-05-11T03:14:38+04:00",
        # Because the incoming timestamp has timezone info, the filter uses
        # that instead of the default value.  Note that this test will fail
        # if the filter uses the UTC-11 timezone (the result will be 1 day
        # ahead).
        date(2015, 5, 10),
    )


def test_date_pass_alternate_timezone_syntax(assert_filter_passes):
    """
    When setting the default timezone for the filter, you can use an
    int/float offset (number of hours from UTC) instead of a tzoffset
    object.
    """
    assert_filter_passes(
        # Note that we use an int value instead of constructing a tzoffset
        # for `timezone`.
        f.Date(timezone=-8),
        "2015-05-11 21:14:38",
        date(2015, 5, 12),
    )


def test_date_pass_datetime_utc(assert_filter_passes):
    """
    The incoming value is a datetime object that is already set to UTC.
    """
    assert_filter_passes(
        f.Date(),
        datetime(2015, 6, 27, 10, 5, 48, tzinfo=utc),
        date(2015, 6, 27),
    )


def test_date_pass_datetime_non_utc(assert_filter_passes):
    """
    The incoming value is a datetime object with a non-UTC timezone.
    """
    assert_filter_passes(
        f.Date(),
        datetime(
            2015,
            6,
            27,
            22,
            6,
            32,
            tzinfo=tzoffset("UTC-5", -5 * 3600),
        ),
        # As you probably already guessed, the datetime gets converted to
        # UTC before it is converted to a date.
        date(2015, 6, 28),
    )


def test_date_pass_datetime_naive(assert_filter_passes):
    """
    The incoming value is a datetime object without timezone info.
    """
    assert_filter_passes(
        # The filter will assume that this datetime is UTC-3 by default.
        f.Date(timezone=-3),
        datetime(2015, 6, 27, 23, 7, 18),
        # The datetime is converted from UTC-3 to UTC before it is
        # converted to a date.
        date(2015, 6, 28),
    )


def test_date_pass_date(assert_filter_passes):
    """
    The incoming value is a date object.
    """
    assert_filter_passes(f.Date(), date(2015, 6, 27))


def test_date_fail_invalid_value(assert_filter_errors):
    """
    The incoming value cannot be interpreted as a date.

    Insert socially-awkward nerd joke here.
    """
    assert_filter_errors(
        f.Date(),
        "that's no date",  # it's a space station
        [f.Date.CODE_INVALID],
    )
