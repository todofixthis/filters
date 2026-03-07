"""
Tests for the FilterMapper filter.
"""

import filters as f


def test_filter_mapper_pass_none(assert_filter_passes):
    """
    For consistency with all the other Filter classes, ``None`` is
    considered a valid value to pass to a FilterMapper, even though it is
    not iterable.
    """
    filter_instance = f.FilterMapper({"id": f.Int})

    assert_filter_passes(filter_instance, None)


def test_filter_mapper_pass_mapping(assert_filter_passes):
    """
    A FilterRepeater is applied to a dict containing valid values.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    runner = assert_filter_passes(
        filter_instance,
        {
            "subject": "Hello, world!",
            "id": "42",
        },
        {
            "id": 42,
            "subject": "Hello, world!",
        },
    )

    # Key order matches the filter map passed to the filter initialiser.
    assert list(runner.cleaned_data.keys()) == ["id", "subject"]


def test_filter_mapper_fail_mapping(assert_filter_errors):
    """
    A FilterRepeater is applied to a dict containing invalid values.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    assert_filter_errors(
        filter_instance,
        {
            "id": None,
            "subject": "Antidisestablishmentarianism",
        },
        {
            "id": [f.Required.CODE_EMPTY],
            "subject": [f.MaxLength.CODE_TOO_LONG],
        },
        expected_value={
            "id": None,
            "subject": None,
        },
    )


def test_filter_mapper_extra_keys_allowed(assert_filter_passes):
    """
    By default, FilterMappers pass-thru extra keys.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    runner = assert_filter_passes(
        filter_instance,
        {
            "cat": "felix",
            "subject": "Hello, world!",
            "id": "42",
            "fox": "fennecs",
            "bird": "phoenix",
        },
        {
            "subject": "Hello, world!",
            "id": 42,
            "bird": "phoenix",
            "cat": "felix",
            "fox": "fennecs",
        },
    )

    # Filtered keys are always first, followed by extra keys in
    # alphabetical order.
    assert list(runner.cleaned_data.keys()) == ["id", "subject", "bird", "cat", "fox"]


def test_filter_mapper_extra_keys_disallowed(assert_filter_errors):
    """
    FilterMappers can be configured to treat any extra key as an invalid
    value.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        },
        # Treat all extra keys as invalid values.s
        allow_extra_keys=False,
    )

    assert_filter_errors(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "extra": "ignored",
        },
        {
            "extra": [f.FilterMapper.CODE_EXTRA_KEY],
        },
        # The valid fields were still included in the return value, but the
        # invalid field was removed.
        expected_value={
            "id": 42,
            "subject": "Hello, world!",
        },
    )


def test_filter_mapper_extra_keys_specified(assert_filter_passes, assert_filter_errors):
    """
    FilterMappers can be configured only to allow certain extra keys.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        },
        allow_extra_keys={"message", "extra"},
    )

    # As long as the extra keys are in the FilterMapper's
    # ``allow_extra_keys`` setting, everything is fine.
    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "extra": "ignored",
        },
        {
            "id": 42,
            "subject": "Hello, world!",
            "extra": "ignored",
        },
    )

    # But, add a key that isn't in ``allow_extra_keys``, and you've got a
    # problem.
    assert_filter_errors(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "attachment": {
                "type": "image/jpeg",
                "data": "...",
            },
        },
        {
            "attachment": [f.FilterMapper.CODE_EXTRA_KEY],
        },
        expected_value={
            "id": 42,
            "subject": "Hello, world!",
        },
    )


def test_filter_mapper_missing_keys_allowed(assert_filter_passes, assert_filter_errors):
    """
    By default, FilterMappers treat missing keys as `None`.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    # 'subject' allows null values, so no errors are generated.
    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
        },
        {
            "id": 42,
            "subject": None,
        },
    )

    # However, 'id' has Required in its FilterChain, so a missing 'id' is
    # still an error.
    assert_filter_errors(
        filter_instance,
        {
            "subject": "Hello, world!",
        },
        {
            "id": [f.Required.CODE_EMPTY],
        },
        expected_value={
            "id": None,
            "subject": "Hello, world!",
        },
    )


def test_filter_mapper_missing_keys_disallowed(assert_filter_errors):
    """
    FilterMappers can be configured to treat missing keys as invalid
    values.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        },
        # Treat missing keys as invalid values.
        allow_missing_keys=False,
    )

    assert_filter_errors(
        filter_instance,
        {},
        {
            "id": [f.FilterMapper.CODE_MISSING_KEY],
            "subject": [f.FilterMapper.CODE_MISSING_KEY],
        },
        expected_value={
            "id": None,
            "subject": None,
        },
    )


def test_filter_mapper_missing_keys_specified(
    assert_filter_passes, assert_filter_errors
):
    """
    FilterMappers can be configured to allow some missing keys but not
    others.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        },
        allow_missing_keys={"subject"},
    )

    # The FilterMapper is configured to treat missing 'subject' as if it
    # were set to `None`.
    assert_filter_passes(
        filter_instance,
        {"id": "42"},
        {
            "id": 42,
            "subject": None,
        },
    )

    # However, 'id' is still required.
    assert_filter_errors(
        filter_instance,
        {
            "subject": "Hello, world!",
        },
        {
            "id": [f.FilterMapper.CODE_MISSING_KEY],
        },
        expected_value={
            "id": None,
            "subject": "Hello, world!",
        },
    )


def test_filter_mapper_pass_thru_key(assert_filter_passes, assert_filter_errors):
    """
    If you want to make a key required but do not want to run any Filters
    on it, set its FilterChain to `None`.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": None,
        },
        # If you configure a FilterMapper with pass-thru keys(s), you
        # generally also want to disallow missing keys.
        allow_missing_keys=False,
    )

    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
        },
        {
            "id": 42,
            "subject": "Hello, world!",
        },
    )

    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": None,
        },
        {
            "id": 42,
            "subject": None,
        },
    )

    assert_filter_errors(
        filter_instance,
        {
            "id": "42",
        },
        {
            "subject": [f.FilterMapper.CODE_MISSING_KEY],
        },
        expected_value={
            "id": 42,
            "subject": None,
        },
    )


def test_filter_mapper_fail_non_mapping(assert_filter_errors):
    """
    The incoming value is not a mapping.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    assert_filter_errors(
        filter_instance,
        # Nope; it's gotta be an explicit mapping.
        (("id", "42"), ("subject", "Hello, world!")),
        [f.Type.CODE_WRONG_TYPE],
    )


def test_filter_mapper_chained_with_mapper(assert_filter_passes, assert_filter_errors):
    """
    Chaining two FilterMappers together has basically the same effect as
    combining their Filters.

    Generally, combining two FilterMappers into a single instance is much
    easier to read/maintain than chaining them, but in a few cases it may
    be unavoidable (for example, if you need each FilterMapper to handle
    extra and/or missing keys differently).
    """
    fm1 = f.FilterMapper(
        {
            "id": f.Int | f.Min(1),
        },
        allow_missing_keys=True,
        allow_extra_keys=True,
    )

    fm2 = f.FilterMapper(
        {
            "id": f.Required | f.Max(256),
            "subject": f.NotEmpty | f.MaxLength(16),
        },
        allow_missing_keys=False,
        allow_extra_keys=False,
    )

    filter_instance = fm1 | fm2

    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
        },
        {
            "id": 42,
            "subject": "Hello, world!",
        },
    )

    assert_filter_errors(
        filter_instance,
        {},
        {
            # ``fm1`` allows missing keys, so it sets 'id' to ``None``.
            # However, ``fm2`` does not allow ``None`` for 'id' (because of
            # the ``Required`` filter).
            "id": [f.Required.CODE_EMPTY],
            # `fm1` does not care about `subject`, but `fm2` expects it to
            # be there.
            "subject": [f.FilterMapper.CODE_MISSING_KEY],
        },
        expected_value={
            "id": None,
            "subject": None,
        },
    )


def test_filter_mapper_chained_with_filter(assert_filter_passes, assert_filter_errors):
    """
    Chaining a Filter with a FilterMapper causes the chained Filter to
    operate on the entire mapping.
    """
    fm = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
        }
    )

    filter_instance = fm | f.MaxLength(3)

    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "extra": "ignored",
        },
        {
            "id": 42,
            "subject": "Hello, world!",
            "extra": "ignored",
        },
    )

    assert_filter_errors(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "extra": "ignored",
            "attachment": None,
        },
        # The incoming value has 4 items, which fails the MaxLength filter.
        [f.MaxLength.CODE_TOO_LONG],
    )


# noinspection SpellCheckingInspection
def test_filter_mapper_mapperception(assert_filter_passes, assert_filter_errors):
    """
    Want to filter dicts that contain other dicts?  We need to go deeper.
    """
    filter_instance = f.FilterMapper(
        {
            "id": f.Required | f.Int | f.Min(1),
            "subject": f.NotEmpty | f.MaxLength(16),
            "attachment": f.FilterMapper(
                {
                    "type": f.Required | f.Choice(choices={"image/jpeg", "image/png"}),
                    "data": f.Required | f.Base64Decode,
                },
                allow_extra_keys=False,
                allow_missing_keys=False,
            ),
        },
        allow_extra_keys=False,
        allow_missing_keys=False,
    )

    # Valid mapping is valid.
    assert_filter_passes(
        filter_instance,
        {
            "id": "42",
            "subject": "Hello, world!",
            "attachment": {
                "type": "image/jpeg",
                "data": b"R0lGODlhDwAPAKECAAAAzMzM/////wAAACwAAAAAD"
                b"wAPAAACIISPeQHsrZ5ModrLlN48CXF8m2iQ3YmmKq"
                b"VlRtW4MLwWACH+EVRIRSBDQUtFIElTIEEgTElFOw==",
            },
        },
        {
            "id": 42,
            "subject": "Hello, world!",
            "attachment": {
                "type": "image/jpeg",
                "data": b"GIF89a\x0f\x00\x0f\x00\xa1\x02\x00\x00\x00"
                b"\xcc\xcc\xcc\xff\xff\xff\xff\x00\x00\x00,\x00"
                b"\x00\x00\x00\x0f\x00\x0f\x00\x00\x02 \x84\x8f"
                b"y\x01\xec\xad\x9eL\xa1\xda\xcb\x94\xde<\tq|"
                b"\x9bh\x90\xdd\x89\xa6*\xa5eF\xd5\xb80\xbc\x16"
                b"\x00!\xfe\x11THE CAKE IS A LIE;",
            },
        },
    )

    # Invalid mapping... not so much.
    assert_filter_errors(
        filter_instance,
        {
            "id": "NaN",
            "attachment": {
                "type": "foo",
                "data": False,
            },
        },
        {
            # The error keys are the dotted paths to the invalid values.
            # This way, we don't have to deal with nested dicts when
            # processing error codes.
            "id": [f.Decimal.CODE_NON_FINITE],
            "subject": [f.FilterMapper.CODE_MISSING_KEY],
            "attachment.type": [f.Choice.CODE_INVALID],
            "attachment.data": [f.Type.CODE_WRONG_TYPE],
        },
        # The resulting value has the expected structure, but it's a ghost
        # town.
        expected_value={
            "id": None,
            "subject": None,
            "attachment": {
                "type": None,
                "data": None,
            },
        },
    )
