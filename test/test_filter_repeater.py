"""
Tests for the FilterRepeater filter.
"""

import filters as f


def test_filter_repeater_pass_none(assert_filter_passes):
    """
    For consistency with all the other Filter classes, `None` is
    considered a valid value to pass to a FilterRepeater, even
    though it is not iterable.
    """
    filter_instance = f.FilterRepeater(f.Int)

    assert_filter_passes(filter_instance, None)


def test_filter_repeater_pass_iterable(assert_filter_passes):
    """
    A FilterRepeater is applied to a list of valid values.
    """
    filter_instance = f.FilterRepeater(f.NotEmpty | f.Int)

    assert_filter_passes(
        filter_instance,
        ["1", 2, 0, None, "-12"],
        [1, 2, 0, None, -12],
    )


def test_filter_repeater_fail_iterable(assert_filter_errors):
    """
    A FilterRepeater is applied to a list that contains invalid
    values.
    """
    filter_instance = f.FilterRepeater(f.NotEmpty | f.Int)

    assert_filter_errors(
        filter_instance,
        # First element is valid (control group).
        # The rest fail miserably.
        [4, "NaN", 3.14, "FOO", ""],
        {
            "1": [f.Decimal.CODE_NON_FINITE],
            "2": [f.Int.CODE_DECIMAL],
            "3": [f.Decimal.CODE_INVALID],
            "4": [f.NotEmpty.CODE_EMPTY],
        },
        expected_value=[4, None, None, None, None],
    )


def test_filter_repeater_pass_mapping(assert_filter_passes):
    """
    A FilterRepeater is applied to a dict of valid values.
    """
    filter_instance = f.FilterRepeater(f.NotEmpty | f.Int)

    assert_filter_passes(
        filter_instance,
        {
            "foo": "1",
            "bar": 2,
            "baz": None,
            "luhrmann": "-12",
        },
        # The FilterRepeater applies the filter chain to the dict's
        # values.  Note that it completely ignores the keys.
        {
            "foo": 1,
            "bar": 2,
            "baz": None,
            "luhrmann": -12,
        },
    )


def test_filter_repeater_fail_mapping(assert_filter_errors):
    """
    A FilterRepeater is applied to a dict that contains invalid
    values.
    """
    filter_instance = f.FilterRepeater(f.NotEmpty | f.Int)

    assert_filter_errors(
        filter_instance,
        {
            # First element is valid (control group).
            # The rest fail miserably.
            "foo": 4,
            "bar": "NaN",
            "baz": 3.14,
            "luhrmann": "FOO",
        },
        {
            "bar": [f.Decimal.CODE_NON_FINITE],
            "baz": [f.Int.CODE_DECIMAL],
            "luhrmann": [f.Decimal.CODE_INVALID],
        },
        # Just as with collections, the invalid values in the
        # filtered value are replaced with `None`.
        expected_value={
            "foo": 4,
            "bar": None,
            "baz": None,
            "luhrmann": None,
        },
    )


def test_filter_repeater_restrict_keys(assert_filter_passes, assert_filter_errors):
    """
    A FilterRepeated is configured to restrict allowed keys in a
    mapping.
    """
    filter_instance = f.FilterRepeater(
        filter_chain=f.Int,
        restrict_keys={"ducks", "sea otters"},
    )

    # As long as you stick to the expected keys, everything's
    # hunky-dory.
    assert_filter_passes(
        filter_instance,
        {"ducks": "3", "sea otters": "4"},
        {"ducks": 3, "sea otters": 4},
    )

    # However, should you deviate from the marked path, we cannot
    # be held responsible for the consequences.
    assert_filter_errors(
        filter_instance,
        # Charlie shot first!
        {"ducks": "3", "hawks": "4"},
        {
            "hawks": [f.FilterRepeater.CODE_EXTRA_KEY],
        },
        # Invalid keys are not included in the filtered value.
        # This is very similar to how FilterMapper works.
        expected_value={
            "ducks": 3,
        },
    )


def test_filter_repeater_restrict_indexes(assert_filter_passes, assert_filter_errors):
    """
    A FilterRepeater CAN be configured to restrict keys for
    incoming Iterables, although it is probably the wrong tool
    for the job (MaxLength is probably a better fit).
    """
    #
    # Note that if `restrict_keys` contains non-integers and/or
    # starts with a value other than 0, the FilterRepeater will
    # reject EVERY Iterable it comes across!
    #
    # Really, you should just stick a MaxLength(2) in front of the
    # FilterRepeater and call it a day.  It's less likely to
    # introduce a logic bug and way easier for other devs to
    # interpret.
    #
    # noinspection PyTypeChecker
    filter_instance = f.FilterRepeater(
        filter_chain=f.Int,
        restrict_keys={0, 1, 3, 4},
    )

    assert_filter_passes(filter_instance, ["4", "3"], [4, 3])

    assert_filter_errors(
        filter_instance,
        ["50", "40", "30", "20", "10"],
        {
            # Index 2 was unexpected (the Filter is configured
            # only to allow indexes 0, 1, 3 and 4).
            "2": [f.FilterRepeater.CODE_EXTRA_KEY],
        },
        # To make things even more confusing, the invalid "keys"
        # (indexes) ARE included in the filtered value.  This is
        # because, unlike in mappings, it is not possible to
        # identify "missing" indexes.
        expected_value=[50, 40, None, 20, 10],
    )

    # The moral of the story is, don't use `restrict_keys` when
    # configuring a FilterRepeater that will operate on
    # collections.


def test_filter_repeater_fail_non_iterable_value(assert_filter_errors):
    """
    A FilterRepeater will reject any non-iterable value it comes
    across (except for `None`).
    """
    filter_instance = f.FilterRepeater(f.Int)

    assert_filter_errors(filter_instance, 42, [f.Type.CODE_WRONG_TYPE])


def test_filter_repeater_chained_with_repeater(
    assert_filter_passes, assert_filter_errors
):
    """
    Chaining two FilterRepeaters together has basically the same effect as
    combining their Filters, except for one very important difference:  The
    two sets of Filters are applied in sequence.

    That is, the second set of Filters only get applied if ALL the Filters
    in the first set pass!

    Generally, combining two FilterRepeaters into a single instance is much
    easier to read/maintain than chaining them, but should you ever come
    across a situation where you need to apply two FilterRepeaters in
    sequence, you can do so.
    """
    filter_instance = f.FilterRepeater(f.NotEmpty) | f.FilterRepeater(f.Int)

    # The values in this list pass through both FilterRepeaters
    # successfully.
    assert_filter_passes(
        filter_instance,
        ["1", 2, 0, None, "-12"],
        [1, 2, 0, None, -12],
    )

    # The values in this list fail one or more Filters in each
    # FilterRepeater.
    assert_filter_errors(
        filter_instance,
        ["", "NaN", 0, None, "FOO"],
        {
            # Fails the NotEmpty filter in the first FilterRepeater.
            "0": [f.NotEmpty.CODE_EMPTY],
            # IMPORTANT:  Because the first FilterRepeater had one or more
            # errors, the outer FilterChain stopped.
            # '1': [f.Decimal.CODE_NON_FINITE],
            # '4': [f.Int.CODE_INVALID],
        },
        # The result is the same as if we only ran the value through the
        # first FilterRepeater.
        expected_value=[None, "NaN", 0, None, "FOO"],
    )

    # The values in this list pass the first FilterRepeater but fail the
    # second one.
    assert_filter_errors(
        filter_instance,
        ["1", "NaN", 0, None, "FOO"],
        {
            "1": [f.Decimal.CODE_NON_FINITE],
            "4": [f.Decimal.CODE_INVALID],
        },
        expected_value=[1, None, 0, None, None],
    )


def test_filter_repeater_chained_with_filter(
    assert_filter_passes, assert_filter_errors
):
    """
    Chaining a Filter with a FilterRepeater causes the chained Filter to
    operate on the entire collection.
    """
    # This chain will apply NotEmpty to every item in the collection, and
    # then apply MaxLength to the collection as a whole.
    filter_instance = f.FilterRepeater(f.NotEmpty) | f.MaxLength(2)

    # The collection has a length of 2, so it passes the MaxLength filter.
    assert_filter_passes(filter_instance, ["foo", "bar"])

    # The collection has a length of 3, so it fails the MaxLength filter.
    assert_filter_errors(
        filter_instance,
        ["a", "b", "c"],
        [f.MaxLength.CODE_TOO_LONG],
    )


# noinspection SpellCheckingInspection
def test_filter_repeater_repeaterception(assert_filter_passes, assert_filter_errors):
    """
    FilterRepeaters can contain other FilterRepeaters.
    """
    filter_instance = (
        # Apply the following filters to each item in the incoming value:
        f.FilterRepeater(
            # 1. It must be a list.
            f.Type(list)
            # 2. Apply the Int filter to each of its items.
            | f.FilterRepeater(f.Int)
            # 3. It must have a length <= 3.
            | f.MaxLength(3)
        )
    )

    assert_filter_passes(
        filter_instance,
        #
        # Note that the INCOMING VALUE ITSELF does not have to be a list,
        # nor does it have to have a max length <= 3.
        #
        # These Filters are applied to the items INSIDE THE INCOMING VALUE
        # (because of the outer FilterRepeater).
        #
        {
            "foo": ["1", "2", "3"],
            "bar": [-20, 20],
            "baz": ["486"],
            "luhrmann": [None, None, None],
        },
        {
            "foo": [1, 2, 3],
            "bar": [-20, 20],
            "baz": [486],
            "luhrmann": [None, None, None],
        },
    )

    # The 1st item in this value is not a list, so it fails.
    assert_filter_errors(
        filter_instance,
        [
            [42],
            {"arch": 486},
        ],
        {
            "1": [f.Type.CODE_WRONG_TYPE],
        },
        expected_value=[[42], None],
    )

    # The 1st item in this value contains invalid ints.
    assert_filter_errors(
        filter_instance,
        [
            [42],
            ["NaN", 3.14, "FOO"],
        ],
        {
            #
            # The error keys are the dotted paths to the invalid values (in
            # this case, they are numeric because we are working with
            # lists).
            #
            # This way, we don't have to deal with nested dicts when
            # processing error codes.
            #
            "1.0": [f.Decimal.CODE_NON_FINITE],
            "1.1": [f.Int.CODE_DECIMAL],
            "1.2": [f.Decimal.CODE_INVALID],
        },
        expected_value=[[42], [None, None, None]],
    )

    # The 1st item in this value is too long.
    assert_filter_errors(
        filter_instance,
        [[42], [1, 2, 3, 4]],
        {
            "1": [f.MaxLength.CODE_TOO_LONG],
        },
        expected_value=[[42], None],
    )
