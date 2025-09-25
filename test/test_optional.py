from functools import partial

import filters as f
from .conftest import Lengthy


def test_optional_pass_none(assert_filter_passes):
    """
    It'd be pretty silly to name a filter "Optional" if it rejects
    ``None``, wouldn't it?
    """
    assert_filter_passes(f.Optional(), None)


def test_optional_pass_replace_none(assert_filter_passes):
    """
    The default replacement value is ``None``, but you can change it to
    something else.
    """
    assert_filter_passes(
        f.Optional(default="Hello, world!"),
        None,
        "Hello, world!",
    )


def test_optional_pass_replace_empty_string(assert_filter_passes):
    """
    The incoming value is an empty string.
    """
    assert_filter_passes(
        f.Optional(default="42"),
        "",
        "42",
    )


def test_optional_replace_empty_collection(assert_filter_passes):
    """
    The incoming value is a collection with length < 1.
    """
    # By default, the filter will replace empty values with `None`.
    assert_filter_passes(f.Optional(), [], None)
    assert_filter_passes(f.Optional(), {}, None)
    assert_filter_passes(f.Optional(), Lengthy(0), None)
    # etc.


def test_optional_pass_non_empty_string(assert_filter_passes):
    """
    The incoming value is a non-empty string.
    """
    assert_filter_passes(f.Optional(default="fail"), "Goodbye, world!")


def test_optional_pass_non_empty_collection(assert_filter_passes):
    """
    The incoming value is a collection with length > 0.
    """
    # The values inside the collection may be empty, but the collection
    # itself is not.
    assert_filter_passes(f.Optional(), ["", "", ""])
    assert_filter_passes(f.Optional(), {"": ""})
    assert_filter_passes(f.Optional(), Lengthy(12))
    # etc.


def test_optional_pass_non_collection(assert_filter_passes):
    """
    Any value that doesn't have a length is left alone.
    """
    test_obj = object()
    assert_filter_passes(
        f.Optional(default="fail"),
        test_obj,
    )


def test_optional_pass_zero_is_not_empty(assert_filter_passes):
    """
    PHP developers take note!
    """
    assert_filter_passes(
        f.Optional(default="fail"),
        0,
    )


def test_optional_pass_false_is_not_empty(assert_filter_passes):
    """
    The boolean value ``False`` is NOT considered empty because it
    represents SOME kind of value.
    """
    assert_filter_passes(
        f.Optional(default="fail"),
        False,
    )


def test_optional_pass_default_callable(assert_filter_passes):
    """
    The filter is configured with a callable value for ``default``.
    """
    runner1 = assert_filter_passes(
        f.Optional(default=list),
        None,
        [],
    )

    runner2 = assert_filter_passes(
        f.Optional(default=list),
        "",
        [],
    )

    # A new list is created each time.
    assert runner1.cleaned_data is not runner2.cleaned_data


def test_optional_pass_default_callable_partial(assert_filter_passes):
    """
    To pass args or kwargs to a callable ``default``, use a partial or a
    lambda.
    """

    def power_of_two(power):
        return pow(2, power)

    # Use a partial:
    assert_filter_passes(
        f.Optional(default=partial(power_of_two, power=8)),
        {},
        256,
    )

    # Or, use a lambda:
    assert_filter_passes(
        f.Optional(default=lambda: power_of_two(power=4)),
        [],
        16,
    )


def test_optional_pass_default_callable_but_do_not_call_it(assert_filter_passes):
    """
    The filter is configured to use ``default`` explicitly for replacement
    values.
    """
    runner1 = assert_filter_passes(
        f.Optional(default=list, call_default=False),
        None,
        list,
    )

    runner2 = assert_filter_passes(
        f.Optional(default=list, call_default=False),
        "",
        list,
    )

    assert runner1.cleaned_data is runner2.cleaned_data
