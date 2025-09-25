import filters as f


def test_type_pass_none(assert_filter_passes):
    """
    ``None`` always passes this filter.

    Use ``Required | Type`` if you want to reject null values.
    """
    assert_filter_passes(
        f.Type(allowed_types=str),
        None,
    )


def test_type_pass_matching_type(assert_filter_passes):
    """
    The incoming value has the expected type.
    """
    assert_filter_passes(
        f.Type(allowed_types=str),
        "Hello, world!",
    )


def test_type_fail_non_matching_type(assert_filter_errors):
    """
    The incoming value does not have the expected type.
    """
    assert_filter_errors(
        f.Type(allowed_types=str),
        b"Not a string, sorry.",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_type_multiple_allowed_types(assert_filter_passes, assert_filter_errors):
    """
    You can configure the filter to allow multiple types.
    """
    assert_filter_passes(
        f.Type(allowed_types=(str, int)),
        "Hello, world!",
    )

    assert_filter_passes(
        f.Type(allowed_types=(str, int)),
        42,
    )

    assert_filter_errors(
        f.Type(allowed_types=(str, int)),
        b"Not a unicode.",
        [f.Type.CODE_WRONG_TYPE],
    )


def test_type_pass_subclass_allowed(assert_filter_passes):
    """
    The incoming value's type is a subclass of an allowed type.
    """
    assert_filter_passes(
        # bool is a subclass of int.
        f.Type(allowed_types=int),
        True,
    )


def test_type_fail_subclass_not_allowed(assert_filter_errors):
    """
    You can configure the filter to require exact type matches.
    """
    assert_filter_errors(
        f.Type(allowed_types=int, allow_subclass=False),
        True,
        [f.Type.CODE_WRONG_TYPE],
    )


def test_type_fail_types_are_not_instances(assert_filter_errors):
    """
    The filter checks that the value is an INSTANCE of its allowed type(s).
    It will reject the type(s) themselves.
    """
    assert_filter_errors(
        f.Type(allowed_types=str),
        str,
        [f.Type.CODE_WRONG_TYPE],
    )
