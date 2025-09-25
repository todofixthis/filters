import filters as f


# Max Filter Tests


def test_max_pass_none(assert_filter_passes):
    """
    ``None`` always passes this Filter.

    Use ``Required | Max`` if you want to reject ``None``.
    """
    assert_filter_passes(f.Max(max_value=5), None)


def test_max_pass_lesser_value(assert_filter_passes):
    """
    The incoming value is smaller than the max value.
    """
    assert_filter_passes(f.Max(max_value=5), 3)


def test_max_pass_equal_value(assert_filter_passes):
    """
    The incoming value is equal to the max value.
    """
    assert_filter_passes(f.Max(max_value=5), 5)


def test_max_fail_equal_value_exclusive_comparison(assert_filter_errors):
    """
    The incoming value is equal to the max value, but the Filter is
    configured to use an exclusive comparison.

    This is useful for infinite-precision floats and other cases
    where it is impossible to specify the max value exactly.
    """
    # The Filter is configured to allow any float value that is
    # less than - but not equal to - 5.0.
    assert_filter_errors(
        f.Max(max_value=5.0, exclusive=True),
        5.0,
        [f.Max.CODE_TOO_BIG],
    )


def test_max_fail_greater_value(assert_filter_errors):
    """
    The incoming value is greater than the max value.
    """
    assert_filter_errors(
        f.Max(max_value=5),
        8,
        [f.Max.CODE_TOO_BIG],
    )


def test_max_string_comparison_oddness(assert_filter_errors):
    """
    If the filter is being used on strings, the comparison is case
    sensitive.

    Note:  due to the way ASCII works, this may yield unexpected
    results (lowercase > uppercase).  Also, watch out for
    Unicode oddness!

    Basically what I'm trying to say is, don't use this filter on
    string values.
    """
    # ord('F') => 70
    # ord('f') => 102
    assert_filter_errors(
        f.Max(max_value="Foo"),
        "foo",
        [f.Max.CODE_TOO_BIG],
    )
